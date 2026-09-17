import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from supabase import create_client, Client

st.set_page_config(
    page_title="Gestão Financeira & Blindagem",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Conexão com Supabase
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "https://gquwpdkgzbbjgaqoktcx.supabase.co")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "SUA_CHAVE_JWT_AQUI")

@st.cache_resource
def get_db_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    supabase = get_db_client()
except Exception:
    st.error("Erro ao conectar ao banco de dados Supabase.")
    st.stop()

# -------------------------------------------------------------
# CARREGAMENTO DE DADOS
# -------------------------------------------------------------
def load_all_data():
    r_bancos = supabase.table("contas_bancos").select("*").order("nome_banco").execute()
    r_gastos = supabase.table("gastos_v2").select("*").order("data_registro", desc=True).execute()
    r_rendas = supabase.table("rendas_v2").select("*").order("data_registro", desc=True).execute()
    r_inv = supabase.table("investimentos").select("*").order("id").execute()
    
    df_b = pd.DataFrame(r_bancos.data) if r_bancos.data else pd.DataFrame(columns=["id", "nome_banco", "limite_credito", "saldo_atual", "emprestimo_ativo", "financiamento_ativo"])
    df_g = pd.DataFrame(r_gastos.data) if r_gastos.data else pd.DataFrame(columns=["id", "descricao", "valor_total", "valor_parcela", "parcelas_pagas", "parcelas_totais", "metodo_pagamento", "categoria", "banco_vinculado", "natureza", "destino", "data_registro"])
    df_r = pd.DataFrame(r_rendas.data) if r_rendas.data else pd.DataFrame(columns=["id", "origem", "valor", "tipo", "data_registro"])
    df_i = pd.DataFrame(r_inv.data) if r_inv.data else pd.DataFrame(columns=["id", "ativo", "categoria", "valor_acumulado", "aporte_mensal_planejado", "taxa_anual_estimada"])
    
    return df_b, df_g, df_r, df_i

df_bancos, df_gastos, df_rendas, df_inv = load_all_data()

# Lista para selects
lista_bancos = df_bancos["nome_banco"].tolist() if not df_bancos.empty else ["Nenhum / Dinheiro em Espécie"]

# -------------------------------------------------------------
# SIDEBAR: LANÇAMENTOS E MODALIDADES SEPARADAS
# -------------------------------------------------------------
with st.sidebar:
    st.title("⚙️ Operações")

    # 1. Rendas: Salário vs Extra
    with st.expander("💵 Nova Renda (Salário / Extra)", expanded=False):
        with st.form("form_rendas", clear_on_submit=True):
            origem = st.text_input("Origem (ex: Salário Fixo, Venda, Freelance)")
            valor_renda = st.number_input("Valor Líquido (R$)", min_value=1.0, step=50.0, format="%.2f")
            tipo_renda = st.selectbox("Tipo de Entrada", ["Salário Fixo", "Dinheiro Extra"])
            if st.form_submit_button("Salvar Entrada") and origem.strip():
                supabase.table("rendas_v2").insert({
                    "origem": origem.strip(),
                    "valor": float(valor_renda),
                    "tipo": tipo_renda,
                    "data_registro": str(date.today())
                }).execute()
                st.success("Renda salva!")
                st.rerun()

    # 2. Gastos Rápidos do Dia a Dia (Pix, Dinheiro, Débito)
    with st.expander("☕ Gasto Rápido (Dia a Dia)", expanded=False):
        with st.form("form_dia_a_dia", clear_on_submit=True):
            desc_dia = st.text_input("O que comprou? (ex: Lanche, Cinema, Mercado)")
            val_dia = st.number_input("Valor Pago (R$)", min_value=0.10, step=2.0, format="%.2f")
            metodo_dia = st.selectbox("Forma de Pagamento", ["Pix", "Débito", "Dinheiro em Espécie"])
            banco_dia = st.selectbox("Conta / Banco Utilizado", lista_bancos)
            destino_dia = st.selectbox("Destino", ["Pessoal", "Namorada / Casal", "Casa"])
            if st.form_submit_button("Lançar Gasto") and desc_dia.strip():
                supabase.table("gastos_v2").insert({
                    "descricao": desc_dia.strip(),
                    "valor_total": float(val_dia),
                    "valor_parcela": float(val_dia),
                    "parcelas_pagas": 1,
                    "parcelas_totais": 1,
                    "metodo_pagamento": metodo_dia,
                    "categoria": "Dia a Dia",
                    "banco_vinculado": banco_dia,
                    "natureza": "Não Essencial" if destino_dia == "Namorada / Casal" else "Essencial",
                    "destino": destino_dia,
                    "data_registro": str(date.today())
                }).execute()
                st.success("Gasto lançado!")
                st.rerun()

    # 3. Cartão de Crédito e Parcelamentos
    with st.expander("💳 Compra no Cartão / Parcelados", expanded=False):
        with st.form("form_cartao", clear_on_submit=True):
            desc_c = st.text_input("Descrição da Compra / Fatura")
            val_total_c = st.number_input("Valor Total da Compra (R$)", min_value=1.0, step=20.0, format="%.2f")
            col_parc1, col_parc2 = st.columns(2)
            with col_parc1:
                tot_p = st.number_input("Total de Parcelas", min_value=1, value=1, step=1)
            with col_parc2:
                pagas_p = st.number_input("Parcelas Já Pagas", min_value=0, value=1, step=1)
            
            val_parcela_c = val_total_c / tot_p if tot_p > 0 else val_total_c
            st.caption(f"Valor estimado da parcela: **R$ {val_parcela_c:.2f}**")

            banco_c = st.selectbox("Cartão do Banco", lista_bancos)
            nat_c = st.selectbox("Natureza", ["Não Essencial", "Essencial"])
            dest_c = st.selectbox("Destino", ["Pessoal", "Namorada / Casal", "Casa"])

            if st.form_submit_button("Salvar no Cartão") and desc_c.strip():
                supabase.table("gastos_v2").insert({
                    "descricao": desc_c.strip(),
                    "valor_total": float(val_total_c),
                    "valor_parcela": float(val_parcela_c),
                    "parcelas_pagas": int(pagas_p),
                    "parcelas_totais": int(tot_p),
                    "metodo_pagamento": "Crédito",
                    "categoria": "Cartão de Crédito",
                    "banco_vinculado": banco_c,
                    "natureza": nat_c,
                    "destino": dest_c,
                    "data_registro": str(date.today())
                }).execute()
                st.success("Registrado no Cartão!")
                st.rerun()

    # 4. Gestão de Contas Bancárias & Limites
    with st.expander("🏦 Gerenciar Bancos & Limites", expanded=False):
        tab_b1, tab_b2 = st.tabs(["Cadastrar", "Excluir"])
        with tab_b1:
            with st.form("form_novo_banco", clear_on_submit=True):
                nome_b = st.text_input("Nome da Instituição (ex: Nubank, Inter, Caixa)")
                lim_b = st.number_input("Limite do Cartão de Crédito (R$)", min_value=0.0, step=100.0, format="%.2f")
                emp_b = st.number_input("Empréstimo Ativo neste Banco (R$)", min_value=0.0, step=100.0, format="%.2f")
                fin_b = st.number_input("Financiamento Ativo (ex: Carro) (R$)", min_value=0.0, step=100.0, format="%.2f")
                if st.form_submit_button("Adicionar Banco") and nome_b.strip():
                    supabase.table("contas_bancos").insert({
                        "nome_banco": nome_b.strip(),
                        "limite_credito": float(lim_b),
                        "emprestimo_ativo": float(emp_b),
                        "financiamento_ativo": float(fin_b)
                    }).execute()
                    st.success("Banco cadastrado!")
                    st.rerun()
        with tab_b2:
            if not df_bancos.empty:
                b_remover = st.selectbox("Escolha o banco para remover", options=df_bancos["nome_banco"].tolist())
                if st.button("Remover Banco"):
                    supabase.table("contas_bancos").delete().eq("nome_banco", b_remover).execute()
                    st.success("Banco removido!")
                    st.rerun()

    # 5. Gestão de Investimentos Ativos
    with st.expander("📈 Cadastrar Investimento / Ativo", expanded=False):
        with st.form("form_novo_inv", clear_on_submit=True):
            nome_ativo = st.text_input("Nome do Ativo (ex: CDB 100% CDI, Tesouro Selic)")
            cat_inv = st.selectbox("Classe", ["Renda Fixa / Pós-Fixado", "Tesouro Direto", "Ações / FIIs", "Caixinha"])
            val_acum = st.number_input("Valor Atual Guardado (R$)", min_value=0.0, step=50.0, format="%.2f")
            aporte_plano = st.number_input("Aporte Mensal Planejado (R$)", min_value=0.0, step=25.0, format="%.2f")
            taxa_anual_est = st.number_input("Taxa Anual Média (% a.a.)", value=10.5, step=0.5)
            if st.form_submit_button("Registrar Investimento") and nome_ativo.strip():
                supabase.table("investimentos").insert({
                    "ativo": nome_ativo.strip(),
                    "categoria": cat_inv,
                    "valor_acumulado": float(val_acum),
                    "aporte_mensal_planejado": float(aporte_plano),
                    "taxa_anual_estimada": float(taxa_anual_est)
                }).execute()
                st.success("Ativo registrado!")
                st.rerun()

# -------------------------------------------------------------
# CÁLCULOS E TOTALIZADORES
# -------------------------------------------------------------
salario_fixo = df_rendas[df_rendas["tipo"] == "Salário Fixo"]["valor"].sum() if not df_rendas.empty else 0.0
dinheiro_extra = df_rendas[df_rendas["tipo"] == "Dinheiro Extra"]["valor"].sum() if not df_rendas.empty else 0.0
renda_total = salario_fixo + dinheiro_extra

# Gastos do mês considerando o valor da parcela corrente
saidas_mes = df_gastos["valor_parcela"].sum() if not df_gastos.empty else 0.0
total_investido_acumulado = df_inv["valor_acumulado"].sum() if not df_inv.empty else 0.0
aporte_planejado_mes = df_inv["aporte_mensal_planejado"].sum() if not df_inv.empty else 0.0

saldo_em_conta = renda_total - saidas_mes - aporte_planejado_mes

# -------------------------------------------------------------
# PAINEL CENTRAL DE INDICADORES
# -------------------------------------------------------------
st.title("🛡️ Centro de Controle Financeiro")

k1, k2, k3, k4 = st.columns(4)
k1.metric("Salário Fixo Líquido", f"R$ {salario_fixo:,.2f}", delta=f"+ R$ {dinheiro_extra:,.2f} Extras")
k2.metric("Saídas do Mês (Despesas)", f"R$ {saidas_mes:,.2f}", delta=f"{(saidas_mes/renda_total*100 if renda_total else 0):.1f}% da Renda", delta_color="inverse")
k3.metric("Aporte Investimentos (Mês)", f"R$ {aporte_planejado_mes:,.2f}", delta=f"Patrimônio: R$ {total_investido_acumulado:,.2f}")
k4.metric("Saldo Livre Real", f"R$ {saldo_em_conta:,.2f}", delta="Superávit" if saldo_em_conta >= 0 else "Déficit", delta_color="normal" if saldo_em_conta >= 0 else "inverse")

st.markdown("---")

# -------------------------------------------------------------
# ABAS DE CONTROLE, PROJEÇÕES E CARTÕES
# -------------------------------------------------------------
tab_bancos_view, tab_gastos_view, tab_proj_dividas, tab_proj_inv = st.tabs([
    "🏦 Bancos & Limites de Crédito",
    "📝 Extrato & Parcelas Faltantes",
    "📉 Projeção de Parcelas & Financiamentos",
    "📈 Projeção de Investimentos"
])

# --- ABA 1: BANCOS E LIMITES ---
with tab_bancos_view:
    st.subheader("Uso de Limite e Contas Bancárias")
    if not df_bancos.empty:
        colunas_cards = st.columns(len(df_bancos))
        for idx, (_, b) in enumerate(df_bancos.iterrows()):
            # Calcular gastos em aberto no crédito deste banco
            gastos_banco = df_gastos[(df_gastos["banco_vinculado"] == b["nome_banco"]) & (df_gastos["metodo_pagamento"] == "Crédito")]
            limite_usado = gastos_banco["valor_parcela"].sum() if not gastos_banco.empty else 0.0
            limite_total = float(b["limite_credito"])
            limite_disponivel = max(0.0, limite_total - limite_usado)

            with colunas_cards[idx % len(colunas_cards)]:
                st.markdown(f"### {b['nome_banco']}")
                st.write(f"💳 **Limite Total:** R$ {limite_total:,.2f}")
                st.write(f"🔴 **Usado este mês:** R$ {limite_usado:,.2f}")
                st.write(f"🟢 **Disponível:** R$ {limite_disponivel:,.2f}")
                if limite_total > 0:
                    st.progress(min(1.0, limite_usado / limite_total))
                if float(b["financiamento_ativo"]) > 0 or float(b["emprestimo_ativo"]) > 0:
                    st.caption(f"🚗 Financiamento: R$ {float(b['financiamento_ativo']):,.2f} | 🏦 Empréstimo: R$ {float(b['emprestimo_ativo']):,.2f}")
    else:
        st.info("Nenhum banco cadastrado. Adicione seus bancos na barra lateral.")

# --- ABA 2: EXTRATO COM CONTROLE DE PARCELAS ---
with tab_gastos_view:
    st.subheader("Detalhamento de Compras e Parcelamentos")
    if not df_gastos.empty:
        # Calcular parcelas restantes
        df_display = df_gastos.copy()
        df_display["parcelas_restantes"] = df_display["parcelas_totais"] - df_display["parcelas_pagas"]
        df_display["saldo_devedor"] = df_display["parcelas_restantes"] * df_display["valor_parcela"]

        st.dataframe(
            df_display[[
                "id", "descricao", "categoria", "metodo_pagamento", "banco_vinculado",
                "valor_parcela", "parcelas_pagas", "parcelas_totais", "parcelas_restantes",
                "saldo_devedor", "destino"
            ]],
            use_container_width=True,
            hide_index=True
        )

        # Atualizador rápido de parcelas pagas
        with st.expander("⏩ Pagar Parcela (Avançar 1 mês)"):
            gasto_selecionado = st.selectbox("Selecione o gasto para registrar pagamento da parcela:", options=df_display["id"].tolist())
            if st.button("Confirmar Pagamento de 1 Parcela"):
                item = df_display[df_display["id"] == gasto_selecionado].iloc[0]
                if item["parcelas_pagas"] < item["parcelas_totais"]:
                    nova_paga = int(item["parcelas_pagas"]) + 1
                    supabase.table("gastos_v2").update({"parcelas_pagas": nova_paga}).eq("id", gasto_selecionado).execute()
                    st.success("Parcela atualizada com sucesso!")
                    st.rerun()
                else:
                    st.warning("Todas as parcelas deste item já foram quitadas!")

        with st.expander("🗑️ Excluir Lançamento"):
            del_id = st.selectbox("ID para remover", options=df_display["id"].tolist())
            if st.button("Remover Definitivamente"):
                supabase.table("gastos_v2").delete().eq("id", del_id).execute()
                st.success("Registro removido!")
                st.rerun()
    else:
        st.info("Nenhum gasto cadastrado.")

# --- ABA 3: PROJEÇÃO DE DÍVIDAS E PARCELAS ---
with tab_proj_dividas:
    st.subheader("📉 Horizonte de Quitação de Dívidas")
    st.caption("Visão da redução gradativa das suas parcelas e saldo devedor.")

    if not df_gastos.empty:
        dividas_parceladas = df_gastos[df_gastos["parcelas_totais"] > 1].copy()
        dividas_parceladas["faltam"] = dividas_parceladas["parcelas_totais"] - dividas_parceladas["parcelas_pagas"]
        max_meses = int(dividas_parceladas["faltam"].max()) if not dividas_parceladas.empty and dividas_parceladas["faltam"].max() > 0 else 1

        projecao_divida = []
        for mes in range(1, max_meses + 1):
            parcelas_ativas = dividas_parceladas[dividas_parceladas["faltam"] >= mes]
            custo_mes = parcelas_ativas["valor_parcela"].sum()
            projecao_divida.append({"Mês": f"+{mes} Mês", "Comprometimento (R$)": custo_mes})

        df_proj_div = pd.DataFrame(projecao_divida)
        if not df_proj_div.empty:
            fig_div = px.bar(df_proj_div, x="Mês", y="Comprometimento (R$)", title="Carga de Parcelas nos Próximos Meses", text_auto=True)
            st.plotly_chart(fig_div, use_container_width=True)

        total_saldo_devedor = (dividas_parceladas["faltam"] * dividas_parceladas["valor_parcela"]).sum()
        st.metric("Saldo Devedor Total Consolidado (Parcelados)", f"R$ {total_saldo_devedor:,.2f}")
    else:
        st.info("Cadastre parcelamentos para projetar o cronograma de quitação.")

# --- ABA 4: PROJEÇÃO DE INVESTIMENTOS ---
with tab_proj_inv:
    st.subheader("📈 Projeção Patrimonial e Juros Compostos")
    st.caption("Simulação baseada na sua carteira de investimentos cadastrada.")

    if not df_inv.empty:
        c_i1, c_i2 = st.columns(2)
        with c_i1:
            meses_inv = st.slider("Horizonte de Tempo (Meses)", min_value=6, max_value=120, value=36, step=6)
        with c_i2:
            taxa_padrao = st.number_input("Taxa Média da Carteira (% a.a.)", value=10.5, step=0.5)

        taxa_m = (1 + taxa_padrao / 100) ** (1 / 12) - 1
        saldo_proj = float(total_investido_acumulado)
        total_aportado = float(total_investido_acumulado)
        historico_inv = []

        for m in range(1, meses_inv + 1):
            saldo_proj = (saldo_proj + float(aporte_planejado_mes)) * (1 + taxa_m)
            total_aportado += float(aporte_planejado_mes)
            historico_inv.append({
                "Mês": m,
                "Total Investido do Bolso": round(total_aportado, 2),
                "Montante com Rendimentos": round(saldo_proj, 2),
                "Juros Acumulados": round(saldo_proj - total_aportado, 2)
            })

        df_chart_inv = pd.DataFrame(historico_inv)
        st.line_chart(df_chart_inv.set_index("Mês")[["Total Investido do Bolso", "Montante com Rendimentos"]])

        col_f1, col_f2, col_f3 = st.columns(3)
        col_f1.metric("Aporte Mensal Previsto", f"R$ {aporte_planejado_mes:,.2f}")
        col_f2.metric("Total Poupado do Bolso", f"R$ {total_aportado:,.2f}")
        col_f3.metric("Patrimônio Projetado", f"R$ {saldo_proj:,.2f}", delta=f"+ R$ {saldo_proj - total_aportado:,.2f} Juros")
    else:
        st.info("Cadastre seus ativos na barra lateral para gerar a projeção.")
