"""
app.py — Painel Financeiro Multi-Perfil
Aplicação principal com autenticação, contas conjuntas, gráficos avançados e UI polida.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, datetime

from config import (
    get_supabase_client, CATEGORIAS, TIPOS_GASTO, TIPOS_RENDA,
    NATUREZAS, DESTINOS, CHART_PALETTE, COLORS,
    APP_TITLE, APP_ICON, APP_LAYOUT,
)
from styles import inject_css
from auth import (
    is_authenticated, show_auth_page, get_current_user, get_profile,
    logout, get_joint_members, get_joint_account_info,
    create_joint_account, join_joint_account, leave_joint_account,
    update_display_name,
)

# ──────────────────────────────────────────────
# CONFIGURAÇÃO DA PÁGINA
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="Gestor Financeiro Multi-Perfil",
    page_icon=APP_ICON,
    layout=APP_LAYOUT,
    initial_sidebar_state="collapsed",
)

# Injetar CSS customizado
inject_css()

# ──────────────────────────────────────────────
# GUARD DE AUTENTICAÇÃO
# ──────────────────────────────────────────────
if not is_authenticated():
    show_auth_page()
    st.stop()

# Usuário autenticado — pegar dados
user = get_current_user()
profile = get_profile()
user_id = user["id"]
display_name = profile.get("display_name", "Usuário") if profile else "Usuário"

supabase = get_supabase_client()

# ──────────────────────────────────────────────
# FUNÇÕES DE DADOS (CRUD com profile_id)
# ──────────────────────────────────────────────

@st.cache_data(ttl=30)
def carregar_gastos(_user_id: str, mes_filtro: str | None = None) -> pd.DataFrame:
    """Carrega gastos do perfil (e compartilhados da conta conjunta via RLS)."""
    query = supabase.table("gastos").select("*").order("data_registro", desc=True)
    if mes_filtro:
        # Filtra pelo mês selecionado (YYYY-MM)
        start = f"{mes_filtro}-01"
        # Último dia do mês
        year, month = map(int, mes_filtro.split("-"))
        if month == 12:
            end = f"{year + 1}-01-01"
        else:
            end = f"{year}-{month + 1:02d}-01"
        query = query.gte("data_registro", start).lt("data_registro", end)
    res = query.execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()


@st.cache_data(ttl=30)
def carregar_rendas(_user_id: str) -> pd.DataFrame:
    query = supabase.table("rendas").select("*").order("id", desc=True)
    res = query.execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()


@st.cache_data(ttl=30)
def carregar_metas(_user_id: str) -> pd.DataFrame:
    query = supabase.table("metas").select("*").order("id")
    res = query.execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()


def invalidar_cache():
    """Limpa caches de dados para recarregar."""
    carregar_gastos.clear()
    carregar_rendas.clear()
    carregar_metas.clear()


# ──────────────────────────────────────────────
# FILTRO GLOBAL: Mês/Ano
# ──────────────────────────────────────────────
hoje = date.today()
meses_opcoes = []
for delta in range(12):
    m = hoje.month - delta
    y = hoje.year
    while m <= 0:
        m += 12
        y -= 1
    meses_opcoes.append(f"{y}-{m:02d}")

# ──────────────────────────────────────────────
# HEADER
# ──────────────────────────────────────────────
col_title, col_user = st.columns([4, 1])

with col_title:
    st.title(APP_TITLE)
    st.caption("Sincronização em nuvem • Multi-perfil • Celular & PC")

with col_user:
    st.markdown(f"""
    <div style="text-align:right; padding-top:12px;">
        <span class="badge-info">👤 {display_name}</span>
    </div>
    """, unsafe_allow_html=True)
    if st.button("🚪 Sair", key="btn_logout", use_container_width=True):
        logout()

st.markdown("---")

# ──────────────────────────────────────────────
# FILTROS GLOBAIS
# ──────────────────────────────────────────────
col_f1, col_f2, col_f3 = st.columns([2, 2, 2])

with col_f1:
    mes_selecionado = st.selectbox(
        "📅 Mês de Referência",
        options=["Todos"] + meses_opcoes,
        index=1,  # Mês atual por padrão
    )

mes_filtro = mes_selecionado if mes_selecionado != "Todos" else None

with col_f2:
    filtro_categoria = st.multiselect(
        "🏷️ Filtrar por Categoria",
        options=CATEGORIAS,
        default=[],
        placeholder="Todas as categorias",
    )

with col_f3:
    filtro_natureza = st.selectbox(
        "⚡ Natureza",
        options=["Todas", "Essencial", "Não Essencial"],
    )

# ──────────────────────────────────────────────
# CARREGAR DADOS
# ──────────────────────────────────────────────
df_gastos = carregar_gastos(user_id, mes_filtro)
df_rendas = carregar_rendas(user_id)
df_metas = carregar_metas(user_id)

# Aplicar filtros adicionais
if not df_gastos.empty and filtro_categoria:
    df_gastos = df_gastos[df_gastos["categoria"].isin(filtro_categoria)]
if not df_gastos.empty and filtro_natureza != "Todas":
    df_gastos = df_gastos[df_gastos["natureza"] == filtro_natureza]

# ──────────────────────────────────────────────
# SIDEBAR: LANÇAMENTOS
# ──────────────────────────────────────────────
with st.sidebar:
    st.header("⚡ Lançamentos")

    # --- Novo Gasto ---
    with st.expander("➕ Novo Gasto", expanded=True):
        with st.form("form_gasto", clear_on_submit=True):
            desc = st.text_input("Descrição", placeholder="Ex: Almoço, Parcela Carro")
            valor = st.number_input("Valor (R$)", min_value=0.01, step=5.0, format="%.2f")
            tipo = st.selectbox("Forma / Tipo", TIPOS_GASTO)

            c_p1, c_p2 = st.columns(2)
            with c_p1:
                p_atual = st.number_input("Parcela", min_value=1, value=1, step=1)
            with c_p2:
                p_total = st.number_input("Total Parc.", min_value=1, value=1, step=1)

            categoria = st.selectbox("Categoria", CATEGORIAS)
            natureza = st.selectbox("Natureza", NATUREZAS)
            destino = st.selectbox("Destino", DESTINOS)

            c_d1, c_d2 = st.columns(2)
            with c_d1:
                data_gasto = st.date_input("Data", value=date.today())
            with c_d2:
                is_shared = st.checkbox("Gasto compartilhado", value=False,
                                        help="Marque para que outros membros da conta conjunta vejam este gasto")

            btn_gasto = st.form_submit_button("💾 Salvar Despesa", use_container_width=True)
            if btn_gasto and desc.strip():
                parcelas_txt = f"{int(p_atual)}/{int(p_total)}" if p_total > 1 else "À vista"
                supabase.table("gastos").insert({
                    "profile_id": user_id,
                    "descricao": desc.strip(),
                    "valor": float(valor),
                    "tipo": tipo,
                    "natureza": natureza,
                    "destino": destino,
                    "categoria": categoria,
                    "parcelas": parcelas_txt,
                    "shared": is_shared,
                    "data_registro": str(data_gasto),
                }).execute()
                st.success("✅ Gasto registrado!")
                invalidar_cache()
                st.rerun()

    # --- Nova Renda ---
    with st.expander("➕ Nova Renda"):
        with st.form("form_renda", clear_on_submit=True):
            origem = st.text_input("Fonte / Origem", placeholder="Ex: Salário, Freelance")
            valor_renda = st.number_input("Valor Líquido (R$)", min_value=1.0, step=50.0, format="%.2f")
            tipo_r = st.selectbox("Tipo", TIPOS_RENDA)
            mes_ref = st.text_input("Mês Referência", value=f"{hoje.year}-{hoje.month:02d}",
                                    help="Formato: YYYY-MM")
            btn_renda = st.form_submit_button("💾 Salvar Renda", use_container_width=True)
            if btn_renda and origem.strip():
                supabase.table("rendas").insert({
                    "profile_id": user_id,
                    "origem": origem.strip(),
                    "valor": float(valor_renda),
                    "tipo": tipo_r,
                    "mes_ref": mes_ref.strip(),
                }).execute()
                st.success("✅ Renda salva!")
                invalidar_cache()
                st.rerun()

    # --- Teto Casal ---
    st.markdown("---")
    teto_casal = st.number_input(
        "🔒 Teto Mensal Casal (R$)", min_value=0.0, value=300.0, step=25.0,
        help="Alerta quando gastos 'Namorada / Casal' ultrapassarem este valor",
    )

# ──────────────────────────────────────────────
# KPIs / TOTALIZADORES
# ──────────────────────────────────────────────
total_renda = df_rendas["valor"].sum() if not df_rendas.empty else 0.0
total_gastos = df_gastos["valor"].sum() if not df_gastos.empty else 0.0
saldo_livre = total_renda - total_gastos

# Gastos do perfil (meus)
meus_gastos = 0.0
if not df_gastos.empty:
    meus = df_gastos[df_gastos["profile_id"] == user_id]
    meus_gastos = meus["valor"].sum()

gastos_casal = 0.0
if not df_gastos.empty:
    gastos_casal = df_gastos[df_gastos["destino"] == "Namorada / Casal"]["valor"].sum()

# KPI Cards
col1, col2, col3, col4 = st.columns(4)

col1.metric("💰 Renda Total", f"R$ {total_renda:,.2f}")
col2.metric(
    "📉 Despesas",
    f"R$ {total_gastos:,.2f}",
    delta=f"{(total_gastos / total_renda * 100 if total_renda else 0):.1f}% gasto",
    delta_color="inverse",
)

saldo_badge = "badge-positive" if saldo_livre >= 0 else "badge-negative"
col3.metric("🏦 Saldo Disponível", f"R$ {saldo_livre:,.2f}")
col4.metric(
    "💑 Gasto Casal",
    f"R$ {gastos_casal:,.2f}",
    delta=f"Teto: R$ {teto_casal:,.2f}",
    delta_color="normal" if gastos_casal <= teto_casal else "inverse",
)

if teto_casal > 0 and gastos_casal > teto_casal:
    st.warning(f"⚠️ Gastos do casal ultrapassaram o teto em R$ {gastos_casal - teto_casal:,.2f}!")

# Barra de progresso do orçamento
if total_renda > 0:
    pct_orcamento = min(total_gastos / total_renda, 1.0)
    st.markdown(f"**Orçamento consumido: {pct_orcamento * 100:.1f}%**")
    st.progress(pct_orcamento)
    if pct_orcamento > 0.9:
        st.error("🔴 Você já consumiu mais de 90% da renda!")
    elif pct_orcamento > 0.7:
        st.warning("🟡 Atenção: mais de 70% da renda consumida.")

st.markdown("---")

# ──────────────────────────────────────────────
# TABS PRINCIPAIS
# ──────────────────────────────────────────────
tab_gastos, tab_graficos, tab_metas, tab_simulador, tab_perfis = st.tabs([
    "📋 Histórico & Edição",
    "📊 Análise Visual",
    "🎯 Caixinhas",
    "📈 Projeções",
    "👥 Perfis & Conta Conjunta",
])

# ══════════════════════════════════════════════
# TAB 1: HISTÓRICO E EDIÇÃO
# ══════════════════════════════════════════════
with tab_gastos:
    st.subheader("Despesas Cadastradas")
    if not df_gastos.empty:
        # Resolver nomes dos perfis
        display_cols = ["id", "data_registro", "descricao", "valor", "categoria",
                        "natureza", "destino", "parcelas", "shared"]
        available_cols = [c for c in display_cols if c in df_gastos.columns]
        st.dataframe(
            df_gastos[available_cols],
            use_container_width=True,
            hide_index=True,
            column_config={
                "valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f"),
                "shared": st.column_config.CheckboxColumn("Compartilhado"),
                "data_registro": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
            },
        )

        with st.expander("🗑️ Excluir Lançamento"):
            # Só pode excluir gastos próprios
            meus_ids = df_gastos[df_gastos["profile_id"] == user_id]["id"].tolist()
            if meus_ids:
                id_remover = st.selectbox("Selecione o ID do gasto", options=meus_ids)
                if st.button("Confirmar Exclusão", type="primary"):
                    supabase.table("gastos").delete().eq("id", id_remover).execute()
                    st.success(f"Gasto #{id_remover} excluído.")
                    invalidar_cache()
                    st.rerun()
            else:
                st.info("Nenhum gasto seu para excluir.")
    else:
        st.info("🔍 Nenhuma despesa encontrada para o período selecionado.")

    st.markdown("---")

    st.subheader("Rendas Cadastradas")
    if not df_rendas.empty:
        st.dataframe(
            df_rendas[["id", "origem", "valor", "tipo", "mes_ref"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f"),
            },
        )
        with st.expander("🗑️ Excluir Renda"):
            meus_renda_ids = df_rendas[df_rendas["profile_id"] == user_id]["id"].tolist() if "profile_id" in df_rendas.columns else df_rendas["id"].tolist()
            if meus_renda_ids:
                id_renda_remover = st.selectbox("Selecione o ID da renda", options=meus_renda_ids)
                if st.button("Remover Renda", type="primary"):
                    supabase.table("rendas").delete().eq("id", id_renda_remover).execute()
                    st.success("Renda removida.")
                    invalidar_cache()
                    st.rerun()
    else:
        st.info("Nenhuma renda cadastrada.")

# ══════════════════════════════════════════════
# TAB 2: ANÁLISE VISUAL (6+ gráficos)
# ══════════════════════════════════════════════
with tab_graficos:
    if not df_gastos.empty:
        # Configuração padrão de layout Plotly
        layout_cfg = dict(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, sans-serif", color="#FAFAFA"),
            margin=dict(t=50, b=30, l=30, r=30),
        )

        # ── Linha 1: Donut Essencial/Não Essencial + Donut por Destino ──
        st.subheader("📊 Distribuição de Gastos")
        c_g1, c_g2 = st.columns(2)

        with c_g1:
            fig_nat = px.pie(
                df_gastos, names="natureza", values="valor",
                title="Essencial vs. Não Essencial",
                hole=0.5, color_discrete_sequence=CHART_PALETTE,
            )
            fig_nat.update_layout(**layout_cfg)
            fig_nat.update_traces(textinfo="percent+label", pull=[0.03, 0.03])
            st.plotly_chart(fig_nat, use_container_width=True)

        with c_g2:
            fig_dest = px.pie(
                df_gastos, names="destino", values="valor",
                title="Gastos por Destino",
                hole=0.5, color_discrete_sequence=CHART_PALETTE[2:],
            )
            fig_dest.update_layout(**layout_cfg)
            fig_dest.update_traces(textinfo="percent+label", pull=[0.03, 0.03, 0.03])
            st.plotly_chart(fig_dest, use_container_width=True)

        # ── Linha 2: Treemap por Categoria + Barras Top 10 ──
        st.markdown("---")
        st.subheader("🗂️ Categorias e Maiores Gastos")
        c_g3, c_g4 = st.columns(2)

        with c_g3:
            if "categoria" in df_gastos.columns:
                fig_tree = px.treemap(
                    df_gastos, path=["categoria", "descricao"], values="valor",
                    title="Distribuição Hierárquica",
                    color="valor",
                    color_continuous_scale=["#118AB2", "#1B998B", "#06D6A0", "#FFD166", "#FF6B6B"],
                )
                fig_tree.update_layout(**layout_cfg)
                st.plotly_chart(fig_tree, use_container_width=True)
            else:
                st.info("Adicione categorias aos gastos para ver o treemap.")

        with c_g4:
            top10 = df_gastos.nlargest(10, "valor")[["descricao", "valor"]].sort_values("valor")
            fig_top = px.bar(
                top10, x="valor", y="descricao",
                orientation="h",
                title="🏆 Top 10 Maiores Gastos",
                text="valor",
                color="valor",
                color_continuous_scale=["#1B998B", "#FF6B6B"],
            )
            fig_top.update_layout(**layout_cfg, showlegend=False)
            fig_top.update_traces(texttemplate="R$ %{text:,.2f}", textposition="outside")
            st.plotly_chart(fig_top, use_container_width=True)

        # ── Linha 3: Evolução Diária + Gauge de Orçamento ──
        st.markdown("---")
        st.subheader("📈 Evolução e Saúde Financeira")
        c_g5, c_g6 = st.columns(2)

        with c_g5:
            if "data_registro" in df_gastos.columns:
                df_daily = df_gastos.copy()
                df_daily["data_registro"] = pd.to_datetime(df_daily["data_registro"])
                df_daily = df_daily.groupby("data_registro")["valor"].sum().reset_index()
                df_daily = df_daily.sort_values("data_registro")
                df_daily["acumulado"] = df_daily["valor"].cumsum()

                fig_area = px.area(
                    df_daily, x="data_registro", y="acumulado",
                    title="📅 Gastos Acumulados no Período",
                    labels={"data_registro": "Data", "acumulado": "Acumulado (R$)"},
                )
                fig_area.update_layout(**layout_cfg)
                fig_area.update_traces(
                    fill="tozeroy",
                    line=dict(color="#1B998B", width=2.5),
                    fillcolor="rgba(27,153,139,0.15)",
                )
                st.plotly_chart(fig_area, use_container_width=True)

        with c_g6:
            # Gauge de orçamento
            pct = (total_gastos / total_renda * 100) if total_renda > 0 else 0
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=pct,
                number={"suffix": "%", "font": {"size": 36, "color": "#FAFAFA"}},
                delta={"reference": 70, "increasing": {"color": "#FF6B6B"}, "decreasing": {"color": "#06D6A0"}},
                title={"text": "% do Orçamento Consumido", "font": {"size": 16, "color": "#8D99AE"}},
                gauge={
                    "axis": {"range": [0, 100], "tickwidth": 2, "tickcolor": "#8D99AE"},
                    "bar": {"color": "#1B998B", "thickness": 0.3},
                    "bgcolor": "rgba(30,33,48,0.6)",
                    "borderwidth": 0,
                    "steps": [
                        {"range": [0, 50], "color": "rgba(6,214,160,0.2)"},
                        {"range": [50, 70], "color": "rgba(255,209,102,0.2)"},
                        {"range": [70, 90], "color": "rgba(255,107,107,0.15)"},
                        {"range": [90, 100], "color": "rgba(239,71,111,0.25)"},
                    ],
                    "threshold": {
                        "line": {"color": "#FF6B6B", "width": 3},
                        "thickness": 0.8,
                        "value": 90,
                    },
                },
            ))
            fig_gauge.update_layout(
                **layout_cfg,
                height=320,
            )
            st.plotly_chart(fig_gauge, use_container_width=True)

        # ── Linha 4: Comparativo por Perfil (conta conjunta) ──
        members = get_joint_members()
        if len(members) > 1 and "profile_id" in df_gastos.columns:
            st.markdown("---")
            st.subheader("👥 Comparativo entre Perfis")

            # Mapear profile_id → display_name
            name_map = {m["id"]: m.get("display_name", "Membro") for m in members}
            df_comp = df_gastos.copy()
            df_comp["perfil"] = df_comp["profile_id"].map(name_map).fillna("Desconhecido")

            fig_comp = px.bar(
                df_comp.groupby("perfil")["valor"].sum().reset_index(),
                x="perfil", y="valor",
                title="Gastos por Membro da Conta Conjunta",
                color="perfil",
                color_discrete_sequence=CHART_PALETTE,
                text="valor",
            )
            fig_comp.update_layout(**layout_cfg)
            fig_comp.update_traces(texttemplate="R$ %{text:,.2f}", textposition="outside")
            st.plotly_chart(fig_comp, use_container_width=True)

            # Barras agrupadas por categoria
            if "categoria" in df_gastos.columns:
                fig_comp_cat = px.bar(
                    df_comp.groupby(["perfil", "categoria"])["valor"].sum().reset_index(),
                    x="categoria", y="valor", color="perfil",
                    barmode="group",
                    title="Gastos por Categoria — Comparativo entre Perfis",
                    color_discrete_sequence=CHART_PALETTE,
                )
                fig_comp_cat.update_layout(**layout_cfg)
                st.plotly_chart(fig_comp_cat, use_container_width=True)

    else:
        st.info("📊 Lance despesas para gerar os gráficos de análise.")

# ══════════════════════════════════════════════
# TAB 3: CAIXINHAS / METAS
# ══════════════════════════════════════════════
with tab_metas:
    st.subheader("🎯 Metas e Caixinhas de Compra")

    if not df_metas.empty:
        for _, m in df_metas.iterrows():
            alvo = float(m["alvo"]) if m["alvo"] else 1
            atual = float(m["atual"]) if m["atual"] else 0
            prog = min(1.0, atual / alvo) if alvo > 0 else 0.0

            # Identificar se é meta conjunta
            is_joint = bool(m.get("joint_account_id"))
            tag = " 👥" if is_joint else ""

            col_info, col_pct = st.columns([4, 1])
            with col_info:
                st.markdown(f"**{m['nome']}{tag}** — R\$ {atual:,.2f} de R\$ {alvo:,.2f}")
            with col_pct:
                color = "#06D6A0" if prog >= 1.0 else ("#FFD166" if prog >= 0.5 else "#FF6B6B")
                st.markdown(f'<span style="color:{color}; font-weight:700; font-size:1.1rem;">{prog * 100:.0f}%</span>', unsafe_allow_html=True)

            st.progress(prog)

            # Aporte rápido
            col_m1, col_m2 = st.columns([3, 1])
            with col_m1:
                novo_deposito = st.number_input(
                    f"Aportar em {m['nome']}", min_value=0.0, step=20.0, key=f"dep_{m['id']}"
                )
            with col_m2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("➕ Atualizar", key=f"btn_{m['id']}"):
                    if novo_deposito > 0:
                        supabase.table("metas").update(
                            {"atual": atual + float(novo_deposito)}
                        ).eq("id", m["id"]).execute()
                        st.success("Aporte registrado!")
                        invalidar_cache()
                        st.rerun()

            st.markdown("<br>", unsafe_allow_html=True)

    else:
        st.info("Nenhuma meta criada ainda. Crie sua primeira caixinha abaixo!")

    # Nova meta
    with st.expander("➕ Nova Caixinha"):
        with st.form("form_meta", clear_on_submit=True):
            nome_meta = st.text_input("Objetivo", placeholder="Ex: Reserva de Emergência, Viagem")
            alvo_meta = st.number_input("Valor Final Alvo (R$)", min_value=1.0, step=100.0)
            atual_meta = st.number_input("Valor Já Guardado (R$)", min_value=0.0, step=50.0)

            ja_info = get_joint_account_info()
            is_joint_meta = False
            if ja_info:
                is_joint_meta = st.checkbox(
                    "🤝 Meta conjunta (visível a todos da conta)",
                    value=False,
                )

            if st.form_submit_button("🎯 Criar Meta", use_container_width=True) and nome_meta.strip():
                meta_data = {
                    "profile_id": user_id,
                    "nome": nome_meta.strip(),
                    "alvo": float(alvo_meta),
                    "atual": float(atual_meta),
                }
                if is_joint_meta and ja_info:
                    meta_data["joint_account_id"] = ja_info["id"]

                supabase.table("metas").insert(meta_data).execute()
                st.success("✅ Meta criada!")
                invalidar_cache()
                st.rerun()

# ══════════════════════════════════════════════
# TAB 4: PROJEÇÕES / SIMULADOR
# ══════════════════════════════════════════════
with tab_simulador:
    st.subheader("📈 Simulador de Aportes Mensais")

    c_s1, c_s2, c_s3 = st.columns(3)
    with c_s1:
        aporte_sim = st.number_input(
            "Aporte Mensal (R$)", value=max(0.0, float(saldo_livre)), step=25.0, format="%.2f"
        )
    with c_s2:
        taxa_ano = st.number_input("Taxa Anual (% a.a.)", value=10.0, step=0.5)
    with c_s3:
        meses_sim = st.slider("Prazo (meses)", min_value=6, max_value=120, value=36, step=6)

    if aporte_sim > 0:
        taxa_m = (1 + taxa_ano / 100) ** (1 / 12) - 1
        saldo_proj = 0.0
        investido_proj = 0.0
        linhas = []
        marcos = {}

        for m_idx in range(1, meses_sim + 1):
            saldo_proj = (saldo_proj + aporte_sim) * (1 + taxa_m)
            investido_proj += aporte_sim
            linhas.append({
                "Mês": m_idx,
                "Total Investido": round(investido_proj, 2),
                "Montante com Juros": round(saldo_proj, 2),
                "Rendimento": round(saldo_proj - investido_proj, 2),
            })
            if m_idx in (6, 12, 24, 36, 60, 120):
                marcos[m_idx] = {"investido": investido_proj, "montante": saldo_proj}

        df_proj = pd.DataFrame(linhas)

        # Gráfico Plotly (ao invés de st.line_chart)
        fig_proj = go.Figure()
        fig_proj.add_trace(go.Scatter(
            x=df_proj["Mês"], y=df_proj["Total Investido"],
            name="Total Investido",
            line=dict(color="#118AB2", width=2.5, dash="dot"),
            fill="tonexty" if len(df_proj) > 1 else None,
        ))
        fig_proj.add_trace(go.Scatter(
            x=df_proj["Mês"], y=df_proj["Montante com Juros"],
            name="Montante com Juros",
            line=dict(color="#06D6A0", width=3),
            fill="tonexty",
            fillcolor="rgba(6,214,160,0.1)",
        ))
        fig_proj.add_trace(go.Scatter(
            x=df_proj["Mês"], y=df_proj["Rendimento"],
            name="Rendimento Acumulado",
            line=dict(color="#FFD166", width=2, dash="dash"),
        ))
        fig_proj.update_layout(
            title="Projeção de Patrimônio",
            xaxis_title="Meses",
            yaxis_title="Valor (R$)",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, sans-serif", color="#FAFAFA"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode="x unified",
        )
        st.plotly_chart(fig_proj, use_container_width=True)

        # Marcos resumidos
        st.subheader("📍 Marcos de Prazo")
        marco_cols = st.columns(min(len(marcos), 4))
        for i, (mes, vals) in enumerate(marcos.items()):
            with marco_cols[i % len(marco_cols)]:
                rend = vals["montante"] - vals["investido"]
                st.metric(
                    f"{mes} meses",
                    f"R$ {vals['montante']:,.2f}",
                    delta=f"Rend: R$ {rend:,.2f}",
                )

        st.markdown("---")
        st.markdown(
            f"**💰 Total aportado:** R\$ {investido_proj:,.2f} &nbsp;|&nbsp; "
            f"**📈 Montante final:** R\$ {saldo_proj:,.2f} &nbsp;|&nbsp; "
            f"**✨ Rendimento:** R\$ {saldo_proj - investido_proj:,.2f}"
        )
    else:
        st.info("Configure um aporte mensal maior que zero para ver a projeção.")

# ══════════════════════════════════════════════
# TAB 5: PERFIS & CONTA CONJUNTA
# ══════════════════════════════════════════════
with tab_perfis:
    st.subheader("👤 Meu Perfil")

    # Editar nome
    col_p1, col_p2 = st.columns([3, 1])
    with col_p1:
        new_name = st.text_input(
            "Nome de exibição",
            value=display_name,
            key="edit_display_name",
        )
    with col_p2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("✏️ Atualizar Nome"):
            if new_name.strip() and new_name.strip() != display_name:
                update_display_name(new_name.strip())
                st.success("Nome atualizado!")
                st.rerun()

    st.markdown(f"**E-mail:** {user.get('email', '—')}")

    st.markdown("---")

    # ── Conta Conjunta ──
    st.subheader("🤝 Conta Conjunta")

    ja_info = get_joint_account_info()
    members = get_joint_members()

    if ja_info:
        st.success(f"Você faz parte da conta conjunta: **{ja_info['nome']}**")

        # Código de convite
        st.markdown(f"""
        <div class="invite-code">
            <p style="color:#8D99AE; margin-bottom:6px; font-size:0.85rem;">
                Compartilhe este código para convidar membros:
            </p>
            <code>{ja_info['invite_code']}</code>
        </div>
        """, unsafe_allow_html=True)

        # Membros
        st.markdown("**Membros da conta:**")
        for member in members:
            is_me = member["id"] == user_id
            initial = (member.get("display_name") or "?")[0].upper()
            name = member.get("display_name", "Membro")
            badge = ' <span class="badge-info">Você</span>' if is_me else ""
            st.markdown(f"""
            <div class="profile-card">
                <div class="profile-avatar">{initial}</div>
                <div class="profile-info">
                    <h4>{name}{badge}</h4>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪 Sair da Conta Conjunta", type="secondary"):
            leave_joint_account()
            st.success("Você saiu da conta conjunta.")
            st.rerun()

    else:
        st.info("Você não está em nenhuma conta conjunta.")
        st.markdown("Crie uma nova ou entre em uma existente usando um código de convite.")

        col_ja1, col_ja2 = st.columns(2)

        with col_ja1:
            st.markdown("**🆕 Criar Nova Conta**")
            with st.form("form_create_ja", clear_on_submit=True):
                ja_nome = st.text_input("Nome da Conta", placeholder="Ex: Casa do Casal")
                if st.form_submit_button("Criar Conta Conjunta", use_container_width=True):
                    if ja_nome.strip():
                        result = create_joint_account(ja_nome.strip())
                        if result:
                            st.success(f"Conta '{ja_nome}' criada! Código: **{result['invite_code']}**")
                            st.rerun()

        with col_ja2:
            st.markdown("**🔗 Entrar com Código**")
            with st.form("form_join_ja", clear_on_submit=True):
                invite_input = st.text_input("Código de Convite", placeholder="Ex: a1b2c3d4")
                if st.form_submit_button("Ingressar", use_container_width=True):
                    if invite_input.strip():
                        if join_joint_account(invite_input.strip()):
                            st.rerun()

# ──────────────────────────────────────────────
# FOOTER
# ──────────────────────────────────────────────
st.markdown("---")
st.markdown(
    '<p style="text-align:center; color:#8D99AE; font-size:0.8rem;">'
    '💳 Gestor Financeiro Multi-Perfil &nbsp;•&nbsp; Dados sincronizados em nuvem via Supabase'
    '</p>',
    unsafe_allow_html=True,
)
