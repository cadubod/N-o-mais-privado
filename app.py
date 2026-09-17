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

# Conexão Supabase
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "https://gquwpdkgzbbjgaqoktcx.supabase.co")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdxdXdwZGtnemJiamdhcW9rdGN4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODk2NDY5MDYsImV4cCI6MjEwNTIyMjkwNn0.aqFg8SSiGmD5sic9oJ2gdDjn_gC3EEoYicB_MmiLG-U")

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
    
    df_b = pd.DataFrame(r_bancos.data) if r_bancos.data else pd.DataFrame(columns=["id", "nome_banco", "limite_credito", "saldo_atual", "emprestimo_ativo", "financiamento_ativo", "dia_fechamento", "dia_vencimento"])
    df_g = pd.DataFrame(r_gastos.data) if r_gastos.data else pd.DataFrame(columns=["id", "descricao", "valor_total", "valor_parcela", "parcelas_pagas", "parcelas_totais", "metodo_pagamento", "categoria", "banco_vinculado", "natureza", "destino", "data_registro"])
    df_r = pd.DataFrame(r_rendas.data) if r_rendas.data else pd.DataFrame(columns=["id", "origem", "valor", "tipo", "data_registro"])
    df_i = pd.DataFrame(r_inv.data) if r_inv.data else pd.DataFrame(columns=["id", "ativo", "categoria", "valor_acumulado", "aporte_mensal_planejado", "taxa_anual_estimada"])
    
    if "dia_fechamento" not in df_b.columns:
        df_b["dia_fechamento"] = 1
    if "dia_vencimento" not in df_b.columns:
        df_b["dia_vencimento"] = 10

    return df_b, df_g, df_r, df_i

df_bancos, df_gastos, df_rendas, df_inv = load_all_data()
lista_bancos = df_bancos["nome_banco"].tolist() if not df_bancos.empty else ["Nenhum / Dinheiro em Espécie"]
hoje = date.today()

# -------------------------------------------------------------
# SIDEBAR: OPERAÇÕES
# -------------------------------------------------------------
with st.sidebar:
    st.title("⚙️ Operações")

    # 1. Rendas: Salário vs Extra
    with st.expander("💵 Nova Renda (Salário / Extra)", expanded=False):
        with st.form("form_rendas", clear_on_submit=True):
            origem = st.text_input("Origem (ex: Salário Fixo, Freelance)")
            valor_renda = st.number_input("Valor Líquido (R$)", min_value=1.0, step=50.0, format="%.2f")
            tipo_renda = st.selectbox("Tipo de Entrada", ["Salário Fixo", "Dinheiro Extra"])
            data_r = st.date_input("Data do Recebimento", value=hoje)
            if st.form_submit_button("Salvar Entrada") and origem.strip():
                supabase.table("rendas_v2").insert({
                    "origem": origem.strip(),
                    "valor": float(valor_renda),
                    "tipo": tipo_renda,
                    "data_registro": str(data_r)
                }).execute()
                st.success("Renda registrada!")
                st.rerun()

    # 2. Gastos Rápidos do Dia a Dia (Pix, Dinheiro, Débito)
    with st.expander("☕ Gasto Rápido (Dia a Dia)", expanded=False):
        with st.form("form_dia_a_dia", clear_on_submit=True):
            desc_dia = st.text_input("Descrição (ex: Almoço, Padaria)")
            val_dia = st.number_input("Valor (R$)", min_value=0.10, step=2.0, format="%.2f")
            metodo_dia = st.selectbox("Forma de Pagamento", ["Pix", "Débito", "Dinheiro em Espécie"])
            banco_dia = st.selectbox("Conta / Banco de Origem", lista_bancos)
            destino_dia = st.selectbox("Destino", ["Pessoal", "Namorada / Casal", "Casa"])
            data_dia = st.date_input("Data do Pagamento", value=hoje)
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
                    "data_registro": str(data_dia)
                }).execute()
                st.success("Gasto lançado!")
                st.rerun()

    # 3. Cartão de Crédito e Recorrentes
    with st.expander("💳 Cartão: Parcelados & Recorrentes", expanded=False):
        is_recorrente = st.checkbox("🔁 É gasto recorrente? (Faculdade, Streaming, etc.)")
        with st.form("form_cartao", clear_on_submit=True):
            desc_c = st.text_input("Descrição (ex: Faculdade, Celular Parcelado)")
            data_compra_c = st.date_input("Data da Compra / Cobrança", value=hoje)
            
            if is_recorrente:
                val_mensal_rec = st.number_input("Valor da Mensalidade (R$)", min_value=1.0, step=10.0, format="%.2f")
                tot_p = 999
                pagas_p = 0
                val_total_c = val_mensal_rec
                val_parcela_c = val_mensal_rec
            else:
                val_total_c = st.number_input("Valor Total (R$)", min_value=1.0, step=20.0, format="%.2f")
                c_p1, c_p2 = st.columns(2)
                with c_p1:
                    tot_p = st.number_input("Total Parcelas", min_value=1, value=1, step=1)
                with c_p2:
                    pagas_p = st.number_input("Parcelas Pagas", min_value=0, value=0, step=1)
                val_parcela_c = val_total_c / tot_p if tot_p > 0 else val_total_c
                st.caption(f"Valor mensal da parcela: **R$ {val_parcela_c:.2f}**")

            banco_c = st.selectbox("Cartão Emissor", lista_bancos)
            nat_c = st.selectbox("Natureza", ["Essencial", "Não Essencial"])
            dest_c = st.selectbox("Destino", ["Pessoal", "Namorada / Casal", "Casa"])

            if st.form_submit_button("Salvar no Cartão") and desc_c.strip():
                categoria_final = "Recorrente / Assinatura" if is_recorrente else "Cartão de Crédito"
                supabase.table("gastos_v2").insert({
                    "descricao": desc_c.strip(),
                    "valor_total": float(val_total_c),
                    "valor_parcela": float(val_parcela_c),
                    "parcelas_pagas": int(pagas_p),
                    "parcelas_totais": int(tot_p),
                    "metodo_pagamento": "Crédito",
                    "categoria": categoria_final,
                    "banco_vinculado": banco_c,
                    "natureza": nat_c,
                    "destino": dest_c,
                    "data_registro": str(data_compra_c)
                }).execute()
                st.success("Cadastrado com sucesso!")
                st.rerun()

    # 4. Gerenciamento de Bancos: Cadastro, Edição de Datas/Limites e Exclusão
    with st.expander("🏦 Gerenciar Bancos, Limites & Datas", expanded=False):
        tab_b1, tab_b2, tab_b3 = st.tabs(["Cadastrar", "✏️ Editar Datas", "Excluir"])
        
        with tab_b1:
            with st.form("form_novo_banco", clear_on_submit=True):
                nome_b = st.text_input("Nome da Instituição (ex: Nubank, Inter)")
                lim_b = st.number_input("Limite Total do Cartão (R$)", min_value=0.0, step=100.0, format="%.2f")
                c_d1, c_d2 = st.columns(2)
                with c_d1:
                    dia_f = st.number_input("Dia Fechamento", min_value=1, max_value=31, value=1, step=1)
                with c_d2:
                    dia_v = st.number_input("Dia Vencimento", min_value=1, max_value=31, value=10, step=1)
                emp_b = st.number_input("Empréstimo Ativo (R$)", min_value=0.0, step=100.0, format="%.2f")
                fin_b = st.number_input("Financiamento Ativo (R$)", min_value=0.0, step=100.0, format="%.2f")
                if st.form_submit_button("Salvar Banco") and nome_b.strip():
                    supabase.table("contas_bancos").insert({
                        "nome_banco": nome_b.strip(),
                        "limite_credito": float(lim_b),
                        "dia_fechamento": int(dia_f),
                        "dia_vencimento": int(dia_v),
                        "emprestimo_ativo": float(emp_b),
                        "financiamento_ativo": float(fin_b)
                    }).execute()
                    st.success("Banco salvo!")
                    st.rerun()

        # ABA NOVA: Alteração direta de datas e limite sem recriar
        with tab_b2:
            if not df_bancos.empty:
                banco_para_editar = st.selectbox("Selecione o banco para alterar:", options=df_bancos["nome_banco"].tolist(), key="sb_edit_banco")
                dados_atuais = df_bancos[df_bancos["nome_banco"] == banco_para_editar].iloc[0]
                
                with st.form("form_editar_banco"):
                    novo_lim = st.number_input("Limite do Cartão (R$)", min_value=0.0, value=float(dados_atuais["limite_credito"]), step=100.0, format="%.2f")
                    col_ed1, col_ed2 = st.columns(2)
                    with col_ed1:
                        novo_fech = st.number_input("Novo Fechamento", min_value=1, max_value=31, value=int(dados_atuais["dia_fechamento"]), step=1)
                    with col_ed2:
                        novo_venc = st.number_input("Novo Vencimento", min_value=1, max_value=31, value=int(dados_atuais["dia_vencimento"]), step=1)
                    
                    if st.form_submit_button("Atualizar Informações"):
                        supabase.table("contas_bancos").update({
                            "limite_credito": float(novo_lim),
                            "dia_fechamento": int(novo_fech),
                            "dia_vencimento": int(novo_venc)
                        }).eq("id", dados_atuais["id"]).execute()
                        st.success(f"Dados do {banco_para_editar} atualizados!")
                        st.rerun()
            else:
                st.info("Nenhum banco cadastrado para editar.")

        with tab_b3:
            if not df_bancos.empty:
                b_remover = st.selectbox("Escolha o banco:", options=df_bancos["nome_banco"].tolist(), key="sb_del_banco")
                if st.button("Remover Banco"):
                    supabase.table("contas_bancos").delete().eq("nome_banco", b_remover).execute()
                    st.success("Banco removido!")
                    st.rerun()

    # 5. Gestão de Investimentos
    with st.expander("📈 Cadastrar Investimento", expanded=False):
        with st.form("form_novo_inv", clear_on_submit=True):
            nome_ativo = st.text_input("Nome do Ativo (ex: Tesouro Selic, CDB)")
            cat_inv = st.selectbox("Classe", ["Renda Fixa / CDI", "Tesouro Direto", "Ações / FIIs", "Caixinha"])
            val_acum = st.number_input("Valor Guardado (R$)", min_value=0.0, step=50.0, format="%.2f")
            aporte_plano = st.number_input("Aporte Mensal (R$)", min_value=0.0, step=25.0, format="%.2f")
            taxa_anual_est = st.number_input("Taxa Anual Média (% a.a.)", value=10.5, step=0.5)
            if st.form_submit_button("Registrar") and nome_ativo.strip():
                supabase.table("investimentos").insert({
                    "ativo": nome_ativo.strip(),
                    "categoria": cat_inv,
                    "valor_acumulado": float(val_acum),
                    "aporte_mensal_planejado": float(aporte_plano),
                    "taxa_anual_estimada": float(taxa_anual_est)
                }).execute()
                st.success("Investimento salvo!")
                st.rerun()

# -------------------------------------------------------------
# CÁLCULOS E TOTALIZADORES
# -------------------------------------------------------------
salario_fixo = df_rendas[df_rendas["tipo"] == "Salário Fixo"]["valor"].sum() if not df_rendas.empty else 0.0
dinheiro_extra = df_rendas[df_rendas["tipo"] == "Dinheiro Extra"]["valor"].sum() if not df_rendas.empty else 0.0
renda_total = salario_fixo + dinheiro_extra

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
k2.metric("Saídas do Mês (Faturas/Fixos)", f"R$ {saidas_mes:,.2f}", delta=f"{(saidas_mes/renda_total*100 if renda_total else 0):.1f}% da Renda", delta_color="inverse")
k3.metric("Aporte Investimentos (Mês)", f"R$ {aporte_planejado_mes:,.2f}", delta=f"Patrimônio: R$ {total_investido_acumulado:,.2f}")
k4.metric("Saldo Livre Real", f"R$ {saldo_em_conta:,.2f}", delta="Superávit" if saldo_em_conta >= 0 else "Déficit", delta_color="normal" if saldo_em_conta >= 0 else "inverse")

st.markdown("---")

# -------------------------------------------------------------
# ABAS DO APLICATIVO
# -------------------------------------------------------------
tab_bancos_view, tab_gastos_view, tab_proj_dividas, tab_proj_inv = st.tabs([
    "🏦 Bancos, Vencimentos & Pagar Fatura",
    "📝 Extrato & Datas de Lançamento",
    "📉 Projeção de Dívidas",
    "📈 Projeção de Investimentos"
])

# --- ABA 1: BANCOS COM ALERTAS E BOTÃO GERAL DE PAGAR FATURA ---
with tab_bancos_view:
    st.subheader("Faturas, Vencimentos e Limite de Crédito")
    
    if not df_bancos.empty:
        colunas_cards = st.columns(len(df_bancos))
        dia_atual = hoje.day

        for idx, (_, b) in enumerate(df_bancos.iterrows()):
            compras_banco = df_gastos[(df_gastos["banco_vinculado"] == b["nome_banco"]) & (df_gastos["metodo_pagamento"] == "Crédito")].copy()
            
            limite_bloqueado_total = 0.0
            fatura_mes_atual = 0.0
            
            if not compras_banco.empty:
                for _, row_g in compras_banco.iterrows():
                    if row_g["parcelas_totais"] == 999:
                        fatura_mes_atual += float(row_g["valor_parcela"])
                        limite_bloqueado_total += float(row_g["valor_parcela"])
                    else:
                        restantes = max(0, int(row_g["parcelas_totais"]) - int(row_g["parcelas_pagas"]))
                        if restantes > 0:
                            fatura_mes_atual += float(row_g["valor_parcela"])
                        limite_bloqueado_total += restantes * float(row_g["valor_parcela"])

            limite_total = float(b["limite_credito"])
            limite_disponivel = max(0.0, limite_total - limite_bloqueado_total)

            dia_fech = int(b.get("dia_fechamento", 1))
            dia_venc = int(b.get("dia_vencimento", 10))

            with colunas_cards[idx % len(colunas_cards)]:
                st.markdown(f"### {b['nome_banco']}")
                
                # Alertas Inteligentes
                if dia_atual < dia_fech:
                    st.info(f"🟢 Fatura Aberta (Fecha dia {dia_fech:02d})")
                elif dia_atual >= dia_fech and dia_atual <= dia_venc:
                    dias_restantes = dia_venc - dia_atual
                    st.warning(f"⚠️ Fatura Fechada! Vence dia {dia_venc:02d} ({dias_restantes} dias restantes)")
                else:
                    st.error(f"🚨 Vencida dia {dia_venc:02d}! Pague para liberar o limite.")

                st.write(f"🧾 **Fatura Atual a Pagar:** :red[R$ {fatura_mes_atual:,.2f}]")
                st.write(f"💳 **Limite Contratado:** R$ {limite_total:,.2f}")
                st.write(f"🔒 **Limite Preso:** R$ {limite_bloqueado_total:,.2f}")
                st.write(f"🟢 **Limite Disponível:** R$ {limite_disponivel:,.2f}")
                
                if limite_total > 0:
                    st.progress(min(1.0, limite_bloqueado_total / limite_total))

                st.markdown("---")
                if fatura_mes_atual > 0:
                    if st.button(f"✅ Pagar Fatura {b['nome_banco']} (R$ {fatura_mes_atual:,.2f})", key=f"pay_btn_{b['id']}"):
                        for _, row_g in compras_banco.iterrows():
                            if row_g["parcelas_totais"] != 999:
                                if row_g["parcelas_pagas"] < row_g["parcelas_totais"]:
                                    nova_paga = int(row_g["parcelas_pagas"]) + 1
                                    supabase.table("gastos_v2").update({"parcelas_pagas": nova_paga}).eq("id", row_g["id"]).execute()
                        
                        st.success(f"Fatura do {b['nome_banco']} quitada! Parcelas avançadas e limite liberado.")
                        st.rerun()
                else:
                    st.success("Fatura zerada / Sem pendências.")
    else:
        st.info("Cadastre seus bancos na barra lateral.")

# --- ABA 2: EXTRATO COM DATAS DE LANÇAMENTO ---
with tab_gastos_view:
    st.subheader("Histórico Completo de Gastos e Lançamentos")
    if not df_gastos.empty:
        df_display = df_gastos.copy()
        
        df_display["parcelas_restantes"] = df_display.apply(
            lambda row: "Recorrente" if row["parcelas_totais"] == 999 else max(0, int(row["parcelas_totais"]) - int(row["parcelas_pagas"])),
            axis=1
        )
        df_display["progresso_parcela"] = df_display.apply(
            lambda row: "Recorrente" if row["parcelas_totais"] == 999 else f"{row['parcelas_pagas']}/{row['parcelas_totais']}",
            axis=1
        )
        df_display["saldo_devedor"] = df_display.apply(
            lambda row: "Contínuo" if row["parcelas_totais"] == 999 else f"R$ {(max(0, int(row['parcelas_totais']) - int(row['parcelas_pagas'])) * float(row['valor_parcela'])):,.2f}",
            axis=1
        )

        st.dataframe(
            df_display[[
                "id", "data_registro", "descricao", "categoria", "metodo_pagamento", "banco_vinculado",
                "valor_parcela", "progresso_parcela", "parcelas_restantes", "saldo_devedor", "destino"
            ]],
            use_container_width=True,
            hide_index=True
        )

        c_ajuste1, c_ajuste2, c_ajuste3 = st.columns(3)

        with c_ajuste1:
            with st.expander("💲 Reajustar Valor Mensal"):
                id_reajuste = st.selectbox("Selecione o gasto:", options=df_display["id"].tolist(), key="sb_reajuste")
                novo_valor_mensal = st.number_input("Novo Valor Mensal (R$)", min_value=0.10, step=5.0, format="%.2f")
                if st.button("Atualizar Valor"):
                    supabase.table("gastos_v2").update({
                        "valor_parcela": float(novo_valor_mensal),
                        "valor_total": float(novo_valor_mensal)
                    }).eq("id", id_reajuste).execute()
                    st.success("Valor reajustado!")
                    st.rerun()

        with c_ajuste2:
            with st.expander("⏩ Pagar Parcela Individual"):
                gastos_parcelados = df_display[df_display["parcelas_totais"] != 999]
                if not gastos_parcelados.empty:
                    id_parc = st.selectbox("Gasto Parcelado:", options=gastos_parcelados["id"].tolist(), key="sb_pagar")
                    if st.button("Pagar 1 Parcela"):
                        item = df_display[df_display["id"] == id_parc].iloc[0]
                        if item["parcelas_pagas"] < item["parcelas_totais"]:
                            nova_paga = int(item["parcelas_pagas"]) + 1
                            supabase.table("gastos_v2").update({"parcelas_pagas": nova_paga}).eq("id", id_parc).execute()
                            st.success("Parcela avançada!")
                            st.rerun()
                        else:
                            st.warning("Gasto já quitado.")
                else:
                    st.caption("Sem compras parceladas.")

        with c_ajuste3:
            with st.expander("🗑️ Excluir Registro"):
                del_id = st.selectbox("ID para remover:", options=df_display["id"].tolist(), key="sb_del")
                if st.button("Remover Definitivamente"):
                    supabase.table("gastos_v2").delete().eq("id", del_id).execute()
                    st.success("Registro removido!")
                    st.rerun()
    else:
        st.info("Nenhum gasto cadastrado.")

# --- ABA 3: PROJEÇÃO DE DÍVIDAS ---
with tab_proj_dividas:
    st.subheader("📉 Horizonte de Quitação (Compras Parceladas)")
    if not df_gastos.empty:
        dividas_fin = df_gastos[(df_gastos["parcelas_totais"] > 1) & (df_gastos["parcelas_totais"] != 999)].copy()
        if not dividas_fin.empty:
            dividas_fin["faltam"] = dividas_fin["parcelas_totais"] - dividas_fin["parcelas_pagas"]
            max_meses = int(dividas_fin["faltam"].max()) if dividas_fin["faltam"].max() > 0 else 1

            projecao_divida = []
            for mes in range(1, max_meses + 1):
                parcelas_ativas = dividas_fin[dividas_fin["faltam"] >= mes]
                custo_mes = parcelas_ativas["valor_parcela"].sum()
                projecao_divida.append({"Mês": f"+{mes} Mês", "Comprometimento (R$)": custo_mes})

            df_proj_div = pd.DataFrame(projecao_divida)
            fig_div = px.bar(df_proj_div, x="Mês", y="Comprometimento (R$)", title="Carga de Parcelas Finitas nos Próximos Meses", text_auto=True)
            st.plotly_chart(fig_div, use_container_width=True)

            total_saldo_devedor = (dividas_fin["faltam"] * dividas_fin["valor_parcela"]).sum()
            st.metric("Saldo Devedor Preso no Crédito", f"R$ {total_saldo_devedor:,.2f}")
        else:
            st.info("Sem dívidas com parcelamento finito em aberto.")
    else:
        st.info("Cadastre lançamentos para gerar projeções.")

# --- ABA 4: PROJEÇÃO DE INVESTIMENTOS ---
with tab_proj_inv:
    st.subheader("📈 Projeção Patrimonial e Juros Compostos")
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
