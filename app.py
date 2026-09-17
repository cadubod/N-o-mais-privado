import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from supabase import create_client, Client

# Configuração de tela responsiva (Mobile + PC)
st.set_page_config(
    page_title="Gestor Financeiro Pessoal",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Conexão com Supabase (pode ler de st.secrets se hospedado no Streamlit Cloud)
SUPABASE_URL = "https://gquwpdkgzbbjgaqoktcx.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdxdXdwZGtnemJiamdhcW9rdGN4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODk2NDY5MDYsImV4cCI6MjEwNTIyMjkwNn0.aqFg8SSiGmD5sic9oJ2gdDjn_gC3EEoYicB_MmiLG-U"  # Cole aqui o código completo da Publishable key que você copiou

@st.cache_resource
def get_db_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    supabase = get_db_client()
except Exception as e:
    st.error("Erro ao conectar ao banco de dados. Verifique as credenciais do Supabase.")
    st.stop()

# -------------------------------------------------------------
# FUNÇÕES DE BANCO DE DADOS (CRUD)
# -------------------------------------------------------------
def carregar_dados():
    res_rendas = supabase.table("rendas").select("*").order("id", desc=True).execute()
    res_gastos = supabase.table("gastos").select("*").order("data_registro", desc=True).execute()
    res_metas = supabase.table("metas").select("*").order("id").execute()
    return (
        pd.DataFrame(res_rendas.data),
        pd.DataFrame(res_gastos.data),
        pd.DataFrame(res_metas.data)
    )

df_rendas, df_gastos, df_metas = carregar_dados()

st.title("🛡️ Painel Financeiro Diário")
st.caption("Sincronização em nuvem em tempo real (Acessível no celular e PC).")

# -------------------------------------------------------------
# SIDEBAR: LANÇAMENTOS E ATUALIZAÇÕES
# -------------------------------------------------------------
with st.sidebar:
    st.header("⚡ Lançamentos")

    # 1. Inserir Gasto Diário
    with st.expander("➕ Novo Gasto", expanded=True):
        with st.form("form_gasto", clear_on_submit=True):
            desc = st.text_input("Descrição (ex: Almoço, Parcela Carro, Cinema)")
            valor = st.number_input("Valor (R$)", min_value=0.01, step=5.0, format="%.2f")
            tipo = st.selectbox("Forma / Tipo", ["Momentâneo (À vista)", "Fixo Recorrente", "Parcelado Cartão"])
            
            c_p1, c_p2 = st.columns(2)
            with c_p1:
                p_atual = st.number_input("Parcela", min_value=1, value=1, step=1)
            with c_p2:
                p_total = st.number_input("Total Parc.", min_value=1, value=1, step=1)

            natureza = st.selectbox("Natureza", ["Essencial", "Não Essencial"])
            destino = st.selectbox("Destino", ["Pessoal", "Namorada / Casal", "Casa / Família"])
            data_gasto = st.date_input("Data do Gasto", value=date.today())

            btn_gasto = st.form_submit_button("Salvar Despesa")
            if btn_gasto and desc.strip():
                parcelas_txt = f"{int(p_atual)}/{int(p_total)}" if p_total > 1 else "À vista"
                supabase.table("gastos").insert({
                    "descricao": desc.strip(),
                    "valor": float(valor),
                    "tipo": tipo,
                    "natureza": natureza,
                    "destino": destino,
                    "parcelas": parcelas_txt,
                    "data_registro": str(data_gasto)
                }).execute()
                st.success("Gasto registrado na nuvem!")
                st.rerun()

    # 2. Inserir Renda
    with st.expander("➕ Nova Renda"):
        with st.form("form_renda", clear_on_submit=True):
            origem = st.text_input("Fonte / Origem (ex: Salário, Extra)")
            valor_renda = st.number_input("Valor Líquido (R$)", min_value=1.0, step=50.0, format="%.2f")
            tipo_r = st.selectbox("Tipo", ["Principal", "Extra", "Conjunta"])
            btn_renda = st.form_submit_button("Salvar Renda")
            if btn_renda and origem.strip():
                supabase.table("rendas").insert({
                    "origem": origem.strip(),
                    "valor": float(valor_renda),
                    "tipo": tipo_r
                }).execute()
                st.success("Renda salva!")
                st.rerun()

    # 3. Teto / Limite de Alerta para Casal
    st.markdown("---")
    teto_casal = st.number_input("Teto Mensal Casal/Namorada (R$)", min_value=0.0, value=300.0, step=25.0)

# -------------------------------------------------------------
# TOTALIZADORES E KPIs
# -------------------------------------------------------------
total_renda = df_rendas["valor"].sum() if not df_rendas.empty else 0.0
total_gastos = df_gastos["valor"].sum() if not df_gastos.empty else 0.0
saldo_livre = total_renda - total_gastos

gastos_casal = 0.0
if not df_gastos.empty:
    gastos_casal = df_gastos[df_gastos["destino"] == "Namorada / Casal"]["valor"].sum()

# KPIs responsivos
col1, col2 = st.columns(2)
col1.metric("Renda Total", f"R$ {total_renda:,.2f}")
col2.metric("Despesas Totais", f"R$ {total_gastos:,.2f}", delta=f"{(total_gastos/total_renda*100 if total_renda else 0):.1f}% gasto", delta_color="inverse")

col3, col4 = st.columns(2)
col3.metric("Saldo Disponível", f"R$ {saldo_livre:,.2f}", delta="Positivo" if saldo_livre >= 0 else "Negativo")
col4.metric("Gasto Casal", f"R$ {gastos_casal:,.2f}", delta=f"Teto: R$ {teto_casal:,.2f}", delta_color="normal" if gastos_casal <= teto_casal else "inverse")

if teto_casal > 0 and gastos_casal > teto_casal:
    st.warning(f"⚠️ Atenção: Os gastos destinados ao casal ultrapassaram o teto em R$ {gastos_casal - teto_casal:,.2f}!")

st.markdown("---")

# -------------------------------------------------------------
# VISUALIZAÇÃO E EDIÇÃO EM TEMPO REAL
# -------------------------------------------------------------
tab_gastos, tab_graficos, tab_metas, tab_simulador = st.tabs([
    "📋 Histórico & Edição", "📊 Análise Visual", "🎯 Caixinhas", "📈 Projeções"
])

with tab_gastos:
    st.subheader("Despesas Cadastradas")
    if not df_gastos.empty:
        # Tabela editável: alterações feitas aqui podem ser salvas ou excluídas
        st.dataframe(
            df_gastos[["id", "data_registro", "descricao", "valor", "natureza", "destino", "parcelas"]],
            use_container_width=True,
            hide_index=True
        )
        
        # Exclusão rápida por ID
        with st.expander("🗑️ Excluir Lançamento"):
            id_remover = st.selectbox("Selecione o ID do gasto para apagar", options=df_gastos["id"].tolist())
            if st.button("Confirmar Exclusão"):
                supabase.table("gastos").delete().eq("id", id_remover).execute()
                st.success(f"Gasto #{id_remover} excluído.")
                st.rerun()
    else:
        st.info("Nenhuma despesa registrada até o momento.")

    st.subheader("Rendas Cadastradas")
    if not df_rendas.empty:
        st.dataframe(df_rendas[["id", "origem", "valor", "tipo"]], use_container_width=True, hide_index=True)
        with st.expander("🗑️ Excluir Renda"):
            id_renda_remover = st.selectbox("Selecione o ID da renda", options=df_rendas["id"].tolist())
            if st.button("Remover Renda"):
                supabase.table("rendas").delete().eq("id", id_renda_remover).execute()
                st.success("Renda removida.")
                st.rerun()

with tab_graficos:
    if not df_gastos.empty:
        c_g1, c_g2 = st.columns(2)
        with c_g1:
            fig1 = px.pie(df_gastos, names="natureza", values="valor", title="Essencial vs. Não Essencial", hole=0.45)
            st.plotly_chart(fig1, use_container_width=True)
        with c_g2:
            fig2 = px.pie(df_gastos, names="destino", values="valor", title="Gastos por Destino", hole=0.45)
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Lance despesas para gerar os gráficos.")

with tab_metas:
    st.subheader("Metas e Caixinhas de Compra")
    if not df_metas.empty:
        for _, m in df_metas.iterrows():
            prog = min(1.0, float(m["atual"]) / float(m["alvo"])) if float(m["alvo"]) > 0 else 0.0
            st.write(f"**{m['nome']}** — R$ {float(m['atual']):,.2f} de R$ {float(m['alvo']):,.2f} ({prog*100:.1f}%)")
            st.progress(prog)
            
            # Aporte rápido na caixinha
            col_m1, col_m2 = st.columns([3, 1])
            with col_m1:
                novo_deposito = st.number_input(f"Aportar em {m['nome']}", min_value=0.0, step=20.0, key=f"dep_{m['id']}")
            with col_m2:
                if st.button("Atualizar", key=f"btn_{m['id']}"):
                    supabase.table("metas").update({"atual": float(m["atual"]) + float(novo_deposito)}).eq("id", m["id"]).execute()
                    st.success("Aporte registrado!")
                    st.rerun()
    
    with st.expander("➕ Nova Caixinha"):
        with st.form("form_meta", clear_on_submit=True):
            nome_meta = st.text_input("Objetivo (ex: Reserva, Entrada de Carro)")
            alvo_meta = st.number_input("Valor Final Alvo (R$)", min_value=1.0, step=100.0)
            atual_meta = st.number_input("Valor Guardado Atualmente (R$)", min_value=0.0, step=50.0)
            if st.form_submit_button("Criar Meta") and nome_meta.strip():
                supabase.table("metas").insert({
                    "nome": nome_meta.strip(),
                    "alvo": float(alvo_meta),
                    "atual": float(atual_meta)
                }).execute()
                st.success("Meta criada!")
                st.rerun()

with tab_simulador:
    st.subheader("Simulador de Aportes Mensais")
    c_s1, c_s2, c_s3 = st.columns(3)
    with c_s1:
        aporte_sim = st.number_input("Aporte Mensal Previsto (R$)", value=max(0.0, float(saldo_livre)), step=25.0)
    with c_s2:
        taxa_ano = st.number_input("Taxa Anual Líquida (% a.a.)", value=10.0, step=0.5)
    with c_s3:
        meses_sim = st.slider("Prazo em Meses", min_value=6, max_value=120, value=36, step=6)

    if aporte_sim > 0:
        taxa_m = (1 + taxa_ano / 100) ** (1 / 12) - 1
        saldo_proj = 0.0
        investido_proj = 0.0
        linhas = []
        for m in range(1, meses_sim + 1):
            saldo_proj = (saldo_proj + aporte_sim) * (1 + taxa_m)
            investido_proj += aporte_sim
            linhas.append({"Mês": m, "Total Investido": round(investido_proj, 2), "Montante com Juros": round(saldo_proj, 2)})

        df_proj = pd.DataFrame(linhas)
        st.line_chart(df_proj.set_index("Mês"))
        st.write(f"**Total poupado do bolso:** R$ {investido_proj:,.2f} | **Montante final com rendimento:** R$ {saldo_proj:,.2f}")
