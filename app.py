import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date

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

st.set_page_config(page_title="Gestor Financeiro Multi-Perfil", page_icon=APP_ICON, layout=APP_LAYOUT, initial_sidebar_state="expanded")
inject_css()

if not is_authenticated():
    show_auth_page()
    st.stop()

user = get_current_user()
profile = get_profile()
user_id = user["id"]
display_name = profile.get("display_name", "Usuário") if profile else "Usuário"
ja_info = get_joint_account_info()
joint_id = ja_info["id"] if ja_info else None
membros_conjuntos = get_joint_members()

mapa_nomes = {m["id"]: m.get("display_name", "Membro") for m in membros_conjuntos} if membros_conjuntos else {user_id: display_name}
opcoes_comprador = {m.get("display_name", "Membro"): m["id"] for m in membros_conjuntos} if membros_conjuntos else {display_name: user_id}
nomes_compradores = list(opcoes_comprador.keys())
idx_atual = nomes_compradores.index(display_name) if display_name in nomes_compradores else 0

supabase = get_supabase_client()

# -------------------------------------------------------------
# CARREGAMENTO DE DADOS 
# -------------------------------------------------------------
def load_all_data():
    r_bancos = supabase.table("contas_bancos").select("*").execute()
    r_gastos = supabase.table("gastos").select("*").order("data_registro", desc=True).execute()
    r_rendas = supabase.table("rendas").select("*").order("data_registro", desc=True).execute()
    r_inv = supabase.table("investimentos").select("*").order("id").execute()
    
    df_b = pd.DataFrame(r_bancos.data) if r_bancos.data else pd.DataFrame(columns=["id", "nome_banco", "limite_credito", "dia_fechamento", "dia_vencimento", "profile_id", "shared"])
    df_g = pd.DataFrame(r_gastos.data) if r_gastos.data else pd.DataFrame(columns=["id", "descricao", "valor_total", "valor_parcela", "parcelas_pagas", "parcelas_totais", "metodo_pagamento", "categoria", "banco_vinculado", "natureza", "destino", "data_registro", "profile_id", "shared"])
    df_r = pd.DataFrame(r_rendas.data) if r_rendas.data else pd.DataFrame(columns=["id", "origem", "valor", "tipo", "data_registro", "profile_id"])
    df_i = pd.DataFrame(r_inv.data) if r_inv.data else pd.DataFrame(columns=["id", "ativo", "categoria", "valor_acumulado", "aporte_mensal_planejado", "taxa_anual_estimada", "profile_id", "shared"])
    
    return df_b, df_g, df_r, df_i

df_bancos, df_gastos, df_rendas, df_inv = load_all_data()
lista_bancos = df_bancos["nome_banco"].unique().tolist() if not df_bancos.empty else ["Nenhum / Dinheiro"]
hoje = date.today()

# -------------------------------------------------------------
# HEADER & SELETOR DE VISÃO 
# -------------------------------------------------------------
col_title, col_user = st.columns([4, 1])
with col_title:
    st.title(APP_TITLE)
    if ja_info:
        st.caption(f"🤝 Conta Conjunta Ativa: **{ja_info['nome']}**")
with col_user:
    st.markdown(f'<div style="text-align:right; padding-top:12px;"><span class="badge-info">👤 {display_name}</span></div>', unsafe_allow_html=True)
    if st.button("🚪 Sair", key="btn_logout", use_container_width=True):
        logout()

if ja_info:
    visao = st.radio("👁️ Visão do Painel:", ["🌍 Geral (Tudo)", "👤 Meu Pessoal (Privado)", "🤝 Conta Conjunta"], horizontal=True)
    if visao == "👤 Meu Pessoal (Privado)":
        if not df_gastos.empty: df_gastos = df_gastos[(df_gastos["shared"] == False) & (df_gastos["profile_id"] == user_id)]
        if not df_bancos.empty: df_bancos = df_bancos[(df_bancos["shared"] == False) & (df_bancos["profile_id"] == user_id)]
        if not df_inv.empty: df_inv = df_inv[(df_inv["shared"] == False) & (df_inv["profile_id"] == user_id)]
        if not df_rendas.empty: df_rendas = df_rendas[df_rendas["profile_id"] == user_id]
    elif visao == "🤝 Conta Conjunta":
        if not df_gastos.empty: df_gastos = df_gastos[df_gastos["shared"] == True]
        if not df_bancos.empty: df_bancos = df_bancos[df_bancos["shared"] == True]
        if not df_inv.empty: df_inv = df_inv[df_inv["shared"] == True]

st.markdown("---")

# -------------------------------------------------------------
# SIDEBAR: OPERAÇÕES E LANÇAMENTOS
# -------------------------------------------------------------
with st.sidebar:
    st.header("⚡ Gestão Financeira")
    
    with st.expander("💵 Adicionar Renda", expanded=False):
        with st.form("form_rendas", clear_on_submit=True):
            st.markdown("### 📥 Nova Entrada")
            origem = st.text_input("Fonte Pagadora", placeholder="Ex: Salário da Empresa X")
            valor_renda = st.number_input("Valor Líquido (R$)", min_value=0.0, step=100.0, format="%.2f")
            tipo_renda = st.selectbox("Modalidade", TIPOS_RENDA)
            data_r = st.date_input("Data do Recebimento", value=hoje)
            quem_recebeu = st.selectbox("Titular da Renda", nomes_compradores, index=idx_atual)
            
            if st.form_submit_button("Salvar Entrada") and origem.strip():
                supabase.table("rendas").insert({"profile_id": opcoes_comprador[quem_recebeu], "origem": origem.strip(), "valor": float(valor_renda), "tipo": tipo_renda, "data_registro": str(data_r)}).execute()
                st.rerun()

    with st.expander("☕ Gasto Avulso (Débito/Pix)", expanded=False):
        with st.form("form_dia_a_dia", clear_on_submit=True):
            st.markdown("### 🛒 Pagamento Imediato")
            desc_dia = st.text_input("Descrição", placeholder="Ex: Uber, Almoço Ifood...")
            val_dia = st.number_input("Valor (R$)", min_value=0.0, step=10.0, format="%.2f")
            c_d1, c_d2 = st.columns(2)
            with c_d1: metodo_dia = st.selectbox("Via", ["Pix", "Débito", "Dinheiro"])
            with c_d2: quem_comprou_dia = st.selectbox("Responsável", nomes_compradores, index=idx_atual)
            banco_dia = st.selectbox("Conta de Origem", lista_bancos)
            cat_dia = st.selectbox("Categoria", CATEGORIAS)
            dest_dia = st.selectbox("Destino", DESTINOS)
            is_shared = st.checkbox("Visível na Conta Conjunta?", value=bool(ja_info))
            
            if st.form_submit_button("Registrar Gasto") and desc_dia.strip():
                comprador_id = opcoes_comprador[quem_comprou_dia]
                # TRAVA INTELIGENTE: Se lançar no nome do outro, força a ser compartilhado para não quebrar a segurança RLS
                if comprador_id != user_id:
                    is_shared = True
                
                supabase.table("gastos").insert({
                    "profile_id": comprador_id, "joint_account_id": joint_id if is_shared else None,
                    "descricao": desc_dia.strip(), "valor_total": float(val_dia), "valor_parcela": float(val_dia),
                    "parcelas_pagas": 1, "parcelas_totais": 1, "metodo_pagamento": metodo_dia,
                    "categoria": cat_dia, "banco_vinculado": banco_dia, "natureza": "Essencial", "destino": dest_dia, 
                    "shared": is_shared, "data_registro": str(hoje)
                }).execute()
                st.rerun()

    with st.expander("💳 Compra no Cartão (Crédito)", expanded=False):
        is_recorrente = st.checkbox("🔁 É assinatura mensal?")
        with st.form("form_cartao", clear_on_submit=True):
            st.markdown("### 🛍️ Lançamento de Crédito")
            desc_c = st.text_input("Descrição", placeholder="Ex: Netflix, Celular...")
            if is_recorrente:
                val_mensal = st.number_input("Mensalidade (R$)", min_value=0.0, step=10.0, format="%.2f")
                tot_p, pagas_p, val_total_c, val_parcela_c = 999, 0, val_mensal, val_mensal
            else:
                val_total_c = st.number_input("Valor Total (R$)", min_value=0.0, step=50.0, format="%.2f")
                c_p1, c_p2 = st.columns(2)
                with c_p1: tot_p = st.number_input("Parcelas", min_value=1, value=1)
                with c_p2: pagas_p = st.number_input("Pagas", min_value=0, value=0)
                val_parcela_c = val_total_c / tot_p if tot_p > 0 else val_total_c
            
            c_c1, c_c2 = st.columns(2)
            with c_c1: banco_c = st.selectbox("Cartão", lista_bancos)
            with c_c2: quem_comprou_c = st.selectbox("Responsável", nomes_compradores, index=idx_atual)
            cat_c = st.selectbox("Categoria", CATEGORIAS)
            dest_c = st.selectbox("Destino", DESTINOS)
            is_shared_c = st.checkbox("Visível na Conta Conjunta?", value=bool(ja_info), key="chk_shared_c")

            if st.form_submit_button("Lançar na Fatura") and desc_c.strip():
                comprador_id_c = opcoes_comprador[quem_comprou_c]
                # TRAVA INTELIGENTE
                if comprador_id_c != user_id:
                    is_shared_c = True
                    
                supabase.table("gastos").insert({
                    "profile_id": comprador_id_c, "joint_account_id": joint_id if is_shared_c else None,
                    "descricao": desc_c.strip(), "valor_total": float(val_total_c), "valor_parcela": float(val_parcela_c),
                    "parcelas_pagas": int(pagas_p), "parcelas_totais": int(tot_p), "metodo_pagamento": "Crédito",
                    "categoria": cat_c, "banco_vinculado": banco_c, "natureza": "Essencial", "destino": dest_c, 
                    "shared": is_shared_c, "data_registro": str(hoje)
                }).execute()
                st.rerun()

    with st.expander("🏦 Gerenciar Cartões & Contas"):
        tab_b1, tab_b2, tab_b3 = st.tabs(["Novo", "Editar", "Excluir"])
        with tab_b1:
            with st.form("form_novo_banco", clear_on_submit=True):
                nome_b = st.text_input("Instituição", placeholder="Ex: Nubank, Itaú...")
                lim_b = st.number_input("Limite (R$)", min_value=0.0, step=500.0, format="%.2f")
                d1, d2 = st.columns(2)
                with d1: dia_f = st.number_input("Fechamento", min_value=1, max_value=31, value=1)
                with d2: dia_v = st.number_input("Vencimento", min_value=1, max_value=31, value=10)
                is_shared_b = st.checkbox("Cartão da Casa (Conjunto)?", value=bool(ja_info), key="chk_bnc")
                if st.form_submit_button("Registrar Instituição") and nome_b.strip():
                    supabase.table("contas_bancos").insert({
                        "profile_id": user_id, "joint_account_id": joint_id if is_shared_b else None,
                        "nome_banco": nome_b.strip(), "limite_credito": float(lim_b),
                        "dia_fechamento": int(dia_f), "dia_vencimento": int(dia_v), "shared": is_shared_b
                    }).execute()
                    st.rerun()
        with tab_b2:
            if not df_bancos.empty:
                banco_ed = st.selectbox("Alterar Instituição:", options=df_bancos["nome_banco"].tolist(), key="sb_ed_b")
                dados_atuais = df_bancos[df_bancos["nome_banco"] == banco_ed].iloc[0]
                with st.form("form_ed_banco"):
                    novo_lim = st.number_input("Novo Limite (R$)", value=float(dados_atuais["limite_credito"]), step=500.0, format="%.2f")
                    c_ed1, c_ed2 = st.columns(2)
                    with c_ed1: novo_f = st.number_input("Dia Fechamento", value=int(dados_atuais["dia_fechamento"]), min_value=1, max_value=31)
                    with c_ed2: novo_v = st.number_input("Dia Vencimento", value=int(dados_atuais["dia_vencimento"]), min_value=1, max_value=31)
                    if st.form_submit_button("Atualizar Dados"):
                        supabase.table("contas_bancos").update({"limite_credito": float(novo_lim), "dia_fechamento": int(novo_f), "dia_vencimento": int(novo_v)}).eq("id", dados_atuais["id"]).execute()
                        st.rerun()
        with tab_b3:
            if not df_bancos.empty:
                banco_del = st.selectbox("Instituição a remover:", options=df_bancos["nome_banco"].tolist(), key="sb_del_b")
                if st.button("Remover Definitivamente"):
                    supabase.table("contas_bancos").delete().eq("nome_banco", banco_del).execute()
                    st.rerun()

    with st.expander("📈 Caixinhas & Investimentos"):
        with st.form("form_novo_inv", clear_on_submit=True):
            st.markdown("### 🏦 Novo Ativo")
            nome_ativo = st.text_input("Ativo", placeholder="Ex: Caixinha Viagem, CDB...")
            cat_inv = st.selectbox("Classe", ["Caixinha", "Renda Fixa / CDI", "Tesouro Direto", "Ações / FIIs"])
            val_acum = st.number_input("Saldo Atual (R$)", min_value=0.0, step=100.0, format="%.2f")
            aporte_plano = st.number_input("Aporte Mensal (R$)", min_value=0.0, step=50.0, format="%.2f")
            is_shared_inv = st.checkbox("Reserva Conjunta?", value=bool(ja_info))
            if st.form_submit_button("Adicionar à Carteira") and nome_ativo.strip():
                supabase.table("investimentos").insert({
                    "profile_id": user_id, "joint_account_id": joint_id if is_shared_inv else None,
                    "ativo": nome_ativo.strip(), "categoria": cat_inv,
                    "valor_acumulado": float(val_acum), "aporte_mensal_planejado": float(aporte_plano),
                    "shared": is_shared_inv
                }).execute()
                st.rerun()

# -------------------------------------------------------------
# KPIs
# -------------------------------------------------------------
renda_total = df_rendas["valor"].sum() if not df_rendas.empty else 0.0
saidas_mes = df_gastos["valor_parcela"].sum() if not df_gastos.empty else 0.0
saldo_livre = renda_total - saidas_mes

k1, k2, k3 = st.columns(3)
k1.metric("💰 Receitas Consolidadas", f"R$ {renda_total:,.2f}")
k2.metric("📉 Despesas Projetadas", f"R$ {saidas_mes:,.2f}", delta=f"{(saidas_mes/renda_total*100 if renda_total else 0):.1f}% do Orçamento", delta_color="inverse")
k3.metric("🏦 Saldo de Caixa Libre", f"R$ {saldo_livre:,.2f}", delta="Superávit Operacional" if saldo_livre >= 0 else "Déficit Detectado", delta_color="normal" if saldo_livre >= 0 else "inverse")
st.markdown("---")

# -------------------------------------------------------------
# ABAS DO APLICATIVO
# -------------------------------------------------------------
tab_bancos, tab_extrato, tab_graficos, tab_simulador, tab_perfis = st.tabs([
    "🏦 Cartões & Limites", "📝 Extrato Analítico", "📊 BI & Divisão", "📈 Simulador de Caixinhas", "👥 Autenticação"
])

# --- ABA 1: BANCOS E CARTÕES COMPARTILHADOS ---
with tab_bancos:
    st.subheader("Painel de Cartões de Crédito")
    if not df_bancos.empty:
        colunas = st.columns(2)
        dia_atual = hoje.day

        for idx, (_, b) in enumerate(df_bancos.iterrows()):
            compras_banco = df_gastos[(df_gastos["banco_vinculado"] == b["nome_banco"]) & (df_gastos["metodo_pagamento"] == "Crédito")]
            fatura_mes, limite_preso = 0.0, 0.0
            gastos_por_usuario = {nome: 0.0 for nome in mapa_nomes.values()}

            if not compras_banco.empty:
                for _, row_g in compras_banco.iterrows():
                    comprador = mapa_nomes.get(row_g["profile_id"], "Desconhecido")
                    if row_g["parcelas_totais"] == 999:
                        fatura_mes += float(row_g["valor_parcela"])
                        limite_preso += float(row_g["valor_parcela"])
                        gastos_por_usuario[comprador] += float(row_g["valor_parcela"])
                    else:
                        restantes = max(0, int(row_g["parcelas_totais"]) - int(row_g["parcelas_pagas"]))
                        if restantes > 0:
                            fatura_mes += float(row_g["valor_parcela"])
                            gastos_por_usuario[comprador] += float(row_g["valor_parcela"])
                        limite_preso += restantes * float(row_g["valor_parcela"])

            limite_total = float(b["limite_credito"])
            limite_disp = max(0.0, limite_total - limite_preso)
            dia_f, dia_v = int(b["dia_fechamento"]), int(b["dia_vencimento"])

            with colunas[idx % 2]:
                st.markdown(f"### {b['nome_banco']} {'(Compartilhado 🤝)' if b['shared'] else ''}")
                if dia_atual < dia_f: st.info(f"🟢 Fatura em Aberto (Fecha dia {dia_f:02d})")
                elif dia_atual <= dia_v: st.warning(f"⚠️ Fatura Fechada (Vence dia {dia_v:02d})")
                else: st.error(f"🚨 Fatura em Atraso (Venceu dia {dia_v:02d})")

                st.write(f"🧾 **Fatura Atual:** :red[R$ {fatura_mes:,.2f}]")
                if b['shared'] and fatura_mes > 0:
                    for nome, valor in gastos_por_usuario.items():
                        if valor > 0: st.caption(f"👤 {nome}: R$ {valor:,.2f} ({(valor/fatura_mes)*100:.1f}%)")

                st.write(f"💳 Limite: R$ {limite_total:,.2f} | 🟢 Disp: R$ {limite_disp:,.2f}")
                if limite_total > 0: st.progress(min(1.0, limite_preso / limite_total))
                
                if fatura_mes > 0 and st.button(f"✅ Registrar Pagamento - {b['nome_banco']}", key=f"pay_{b['id']}"):
                    for _, row_g in compras_banco.iterrows():
                        if row_g["parcelas_totais"] != 999 and row_g["parcelas_pagas"] < row_g["parcelas_totais"]:
                            supabase.table("gastos").update({"parcelas_pagas": int(row_g["parcelas_pagas"]) + 1}).eq("id", row_g["id"]).execute()
                    st.rerun()
                st.markdown("---")
    else:
        st.info("Nenhuma instituição financeira cadastrada.")

# --- ABA 2: EXTRATO COMPLETO (Gastos e Rendas) ---
with tab_extrato:
    aba_gastos, aba_rendas = st.tabs(["💸 Lançamentos de Saída", "💵 Entradas e Receitas"])
    
    with aba_gastos:
        if not df_gastos.empty:
            df_display = df_gastos.copy()
            df_display["Comprador"] = df_display["profile_id"].map(mapa_nomes).fillna("Desconhecido")
            df_display["Progresso"] = df_display.apply(lambda r: "Recorrente" if r["parcelas_totais"]==999 else f"{r['parcelas_pagas']}/{r['parcelas_totais']}", axis=1)
            
            st.dataframe(
                df_display[["data_registro", "Comprador", "descricao", "banco_vinculado", "valor_parcela", "Progresso", "categoria", "id"]],
                use_container_width=True, hide_index=True,
                column_config={
                    "data_registro": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                    "Comprador": st.column_config.TextColumn("Responsável", width="small"),
                    "descricao": st.column_config.TextColumn("Descrição", width="medium"),
                    "banco_vinculado": st.column_config.TextColumn("Cartão/Conta", width="small"),
                    "valor_parcela": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                    "Progresso": st.column_config.TextColumn("Status"),
                    "categoria": st.column_config.TextColumn("Categoria"),
                    "id": st.column_config.TextColumn("Cód.", width="small")
                }
            )
            
            c_ed1, c_ed2 = st.columns(2)
            with c_ed1:
                with st.expander("✏️ Editar Linha Selecionada"):
                    id_editar = st.selectbox("Código do Registro:", df_display["id"].tolist(), key="sb_edit_gasto")
                    item_atual = df_display[df_display["id"] == id_editar].iloc[0]
                    with st.form("form_edit_extrato"):
                        novo_desc = st.text_input("Descrição", value=item_atual["descricao"])
                        novo_val = st.number_input("Valor Corrigido (R$)", value=float(item_atual["valor_parcela"]), step=10.0, format="%.2f")
                        if st.form_submit_button("Aplicar Correção"):
                            supabase.table("gastos").update({"descricao": novo_desc, "valor_parcela": float(novo_val), "valor_total": float(novo_val)}).eq("id", id_editar).execute()
                            st.rerun()
            with c_ed2:
                with st.expander("🗑️ Remoção Permanente"):
                    del_id = st.selectbox("Código a deletar:", df_display["id"].tolist(), key="sb_del_gasto")
                    if st.button("Confirmar Exclusão"):
                        supabase.table("gastos").delete().eq("id", del_id).execute()
                        st.rerun()
        else:
            st.info("O livro de registros está limpo.")

    with aba_rendas:
        if not df_rendas.empty:
            df_r_disp = df_rendas.copy()
            df_r_disp["Recebedor"] = df_r_disp["profile_id"].map(mapa_nomes).fillna("Desconhecido")
            
            st.dataframe(
                df_r_disp[["data_registro", "Recebedor", "origem", "valor", "tipo", "id"]],
                use_container_width=True, hide_index=True,
                column_config={
                    "data_registro": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                    "Recebedor": st.column_config.TextColumn("Beneficiário", width="small"),
                    "origem": st.column_config.TextColumn("Fonte Geradora", width="medium"),
                    "valor": st.column_config.NumberColumn("Liquidez Declarada", format="R$ %.2f"),
                    "tipo": st.column_config.TextColumn("Modalidade"),
                    "id": st.column_config.TextColumn("Cód.", width="small")
                }
            )
            
            cr1, cr2 = st.columns(2)
            with cr1:
                with st.expander("✏️ Editar Entrada"):
                    id_r = st.selectbox("Código do Registro:", df_r_disp["id"].tolist(), key="sb_edit_r")
                    item_r = df_r_disp[df_r_disp["id"] == id_r].iloc[0]
                    with st.form("form_edit_r"):
                        n_origem = st.text_input("Origem", value=item_r["origem"])
                        n_val_r = st.number_input("Novo Valor (R$)", value=float(item_r["valor"]), step=50.0, format="%.2f")
                        if st.form_submit_button("Aplicar Ajuste"):
                            supabase.table("rendas").update({"origem": n_origem, "valor": float(n_val_r)}).eq("id", id_r).execute()
                            st.rerun()
            with cr2:
                with st.expander("🗑️ Excluir Entrada"):
                    del_id_r = st.selectbox("Código a deletar:", df_r_disp["id"].tolist(), key="sb_del_r")
                    if st.button("Remover Valor"):
                        supabase.table("rendas").delete().eq("id", del_id_r).execute()
                        st.rerun()
        else:
            st.info("Nenhuma entrada consolidada.")

# --- ABA 3: GRÁFICOS E DIVISÃO MULTI-PERFIL ---
with tab_graficos:
    st.subheader("Business Intelligence & Custos")
    if not df_gastos.empty:
        df_graficos = df_gastos.copy()
        df_graficos["Comprador"] = df_graficos["profile_id"].map(mapa_nomes).fillna("Desconhecido")
        
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            fig_comp = px.pie(df_graficos, names="Comprador", values="valor_parcela", title="Composição de Responsabilidade Financeira", hole=0.4, color_discrete_sequence=CHART_PALETTE)
            fig_comp.update_traces(textinfo="percent+label")
            fig_comp.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#FAFAFA"))
            st.plotly_chart(fig_comp, use_container_width=True)
            
        with col_g2:
            fig_cat = px.pie(df_graficos, names="categoria", values="valor_parcela", title="Consumo Categorizado", hole=0.4, color_discrete_sequence=CHART_PALETTE[::-1])
            fig_cat.update_traces(textposition='inside', textinfo='percent+label')
            fig_cat.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#FAFAFA"), showlegend=False)
            st.plotly_chart(fig_cat, use_container_width=True)
            
        st.markdown("---")
        fig_bar = px.bar(df_graficos.groupby(["Comprador", "categoria"])["valor_parcela"].sum().reset_index(), x="categoria", y="valor_parcela", color="Comprador", barmode="group", text_auto=".2f", title="Volume de Capital por Setor", color_discrete_sequence=CHART_PALETTE)
        fig_bar.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#FAFAFA"))
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("Aguardando volume de dados para consolidação analítica.")

# --- ABA 4: CAIXINHAS E SIMULADOR ---
with tab_simulador:
    st.subheader("Ativos e Patrimônio Acumulado")
    if not df_inv.empty:
        df_inv_disp = df_inv.copy()
        df_inv_disp["Dono"] = df_inv_disp["profile_id"].map(mapa_nomes).fillna("Desconhecido")
        max_val = df_inv_disp["valor_acumulado"].max() * 1.5 if not df_inv_disp.empty else 10000
        
        st.dataframe(
            df_inv_disp[["Dono", "ativo", "categoria", "valor_acumulado", "aporte_mensal_planejado", "id"]],
            hide_index=True, use_container_width=True,
            column_config={
                "Dono": st.column_config.TextColumn("Titular"),
                "ativo": st.column_config.TextColumn("Nomenclatura do Ativo"),
                "categoria": st.column_config.TextColumn("Segmento"),
                "valor_acumulado": st.column_config.ProgressColumn("Capital Guardado", format="R$ %.2f", min_value=0, max_value=max_val),
                "aporte_mensal_planejado": st.column_config.NumberColumn("Meta Mensal", format="R$ %.2f"),
                "id": st.column_config.TextColumn("Cód.", width="small")
            }
        )
        
        c_i1, c_i2 = st.columns(2)
        with c_i1:
            with st.expander("✏️ Ajustar Ativo"):
                id_i = st.selectbox("Código do Ativo:", df_inv_disp["id"].tolist(), key="sb_edit_i")
                item_i = df_inv_disp[df_inv_disp["id"] == id_i].iloc[0]
                with st.form("form_edit_i"):
                    n_ativo = st.text_input("Identificador", value=item_i["ativo"])
                    n_val_i = st.number_input("Valor Reavaliado (R$)", value=float(item_i["valor_acumulado"]), step=100.0, format="%.2f")
                    n_aporte = st.number_input("Nova Meta Mensal (R$)", value=float(item_i["aporte_mensal_planejado"]), step=50.0, format="%.2f")
                    if st.form_submit_button("Sincronizar Posição"):
                        supabase.table("investimentos").update({"ativo": n_ativo, "valor_acumulado": float(n_val_i), "aporte_mensal_planejado": float(n_aporte)}).eq("id", id_i).execute()
                        st.rerun()
        with c_i2:
            with st.expander("🗑️ Liquidar Ativo (Remover)"):
                del_id_i = st.selectbox("Código a liquidar:", df_inv_disp["id"].tolist(), key="sb_del_i")
                if st.button("Confirmar Liquidação"):
                    supabase.table("investimentos").delete().eq("id", del_id_i).execute()
                    st.rerun()
    else:
        st.info("Portfólio vazio.")

    st.markdown("---")
    st.subheader("📈 Projeção Estratégica Baseada no CDI (10.5% a.a.)")
    
    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1: aporte_sim = st.number_input("Aporte Consistente (R$)", min_value=10.0, value=max(50.0, float(saldo_livre)), step=100.0, format="%.2f")
    with col_s2: meses_sim = st.slider("Horizonte de Tempo (Meses)", min_value=6, max_value=120, value=36, step=6)
    with col_s3: cdi_percent = st.selectbox("Performance do Ativo", ["Caixinha Base: 100% do CDI (~10.5% a.a.)", "CDB Especial: 110% do CDI (~11.5% a.a.)", "LCI/LCA: 115% do CDI (~12% a.a.)"], index=0)
    
    taxa_ano = 10.5 if "100%" in cdi_percent else (11.5 if "110%" in cdi_percent else 12.0)
    taxa_m = (1 + taxa_ano / 100) ** (1 / 12) - 1
    saldo_proj, investido_proj = 0.0, 0.0
    linhas = []

    for m_idx in range(1, meses_sim + 1):
        saldo_proj = (saldo_proj + aporte_sim) * (1 + taxa_m)
        investido_proj += aporte_sim
        linhas.append({"Mês": m_idx, "Esforço Pessoal": round(investido_proj, 2), "Patrimônio Total": round(saldo_proj, 2)})

    fig_proj = px.area(pd.DataFrame(linhas), x="Mês", y=["Esforço Pessoal", "Patrimônio Total"], title="Efeito dos Juros Compostos", color_discrete_sequence=["#FFD166", "#06D6A0"])
    fig_proj.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#FAFAFA"))
    st.plotly_chart(fig_proj, use_container_width=True)

    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("Capital Imobilizado", f"R$ {investido_proj:,.2f}")
    col_m2.metric("Rendimento Bruto", f"R$ {(saldo_proj - investido_proj):,.2f}")
    col_m3.metric("Valuation Final", f"R$ {saldo_proj:,.2f}")

# --- ABA 5: PERFIS ---
with tab_perfis:
    st.subheader("Gestão de Acesso e Sociedade")
    if ja_info:
        st.success(f"Conta Sincronizada: **{ja_info['nome']}**")
        st.code(f"Token de Acesso: {ja_info['invite_code']}")
        st.write("Usuários com acesso ao painel compartilhado:")
        for m in membros_conjuntos: st.write(f"- {m.get('display_name', 'Membro')}")
        if st.button("Desconectar desta Rede"):
            leave_joint_account()
            st.rerun()
    else:
        c1, c2 = st.columns(2)
        with c1:
            novo_nome = st.text_input("Nova Rede Conjunta")
            if st.button("Estabelecer Sociedade"):
                create_joint_account(novo_nome)
                st.rerun()
        with c2:
            codigo = st.text_input("Autenticar com Token")
            if st.button("Sincronizar"):
                join_joint_account(codigo)
                st.rerun()
