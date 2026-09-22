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

supabase = get_supabase_client()

# -------------------------------------------------------------
# CARREGAMENTO DE DADOS 
# -------------------------------------------------------------
def load_all_data():
    r_bancos = supabase.table("contas_bancos").select("*").execute()
    r_gastos = supabase.table("gastos").select("*").order("data_registro", desc=True).execute()
    r_rendas = supabase.table("rendas").select("*").order("data_registro", desc=True).execute()
    r_inv = supabase.table("investimentos").select("*").order("id").execute()
    r_perfis_ext = supabase.table("perfis_cartao").select("*").execute()
    
    df_b = pd.DataFrame(r_bancos.data) if r_bancos.data else pd.DataFrame(columns=["id", "nome_banco", "limite_credito", "dia_fechamento", "dia_vencimento", "profile_id", "shared"])
    df_g = pd.DataFrame(r_gastos.data) if r_gastos.data else pd.DataFrame(columns=["id", "descricao", "valor_total", "valor_parcela", "parcelas_pagas", "parcelas_totais", "metodo_pagamento", "categoria", "banco_vinculado", "natureza", "destino", "data_registro", "profile_id", "shared", "comprador_externo"])
    df_r = pd.DataFrame(r_rendas.data) if r_rendas.data else pd.DataFrame(columns=["id", "origem", "valor", "tipo", "data_registro", "profile_id"])
    df_i = pd.DataFrame(r_inv.data) if r_inv.data else pd.DataFrame(columns=["id", "ativo", "categoria", "valor_acumulado", "aporte_mensal_planejado", "taxa_anual_estimada", "profile_id", "shared"])
    df_pe = pd.DataFrame(r_perfis_ext.data) if r_perfis_ext.data else pd.DataFrame(columns=["id", "nome", "profile_id"])
    
    if "comprador_externo" not in df_g.columns:
        df_g["comprador_externo"] = None
        
    return df_b, df_g, df_r, df_i, df_pe

df_bancos, df_gastos, df_rendas, df_inv, df_perfis_ext = load_all_data()
lista_bancos = df_bancos["nome_banco"].unique().tolist() if not df_bancos.empty else ["Nenhum / Dinheiro"]
hoje = date.today()

# -------------------------------------------------------------
# MAPEAMENTO DINÂMICO DE PERFIS E DEPENDENTES
# -------------------------------------------------------------
mapa_nomes = {m["id"]: m.get("display_name", "Membro") for m in membros_conjuntos} if membros_conjuntos else {user_id: display_name}
opcoes_comprador = {m.get("display_name", "Membro"): m["id"] for m in membros_conjuntos} if membros_conjuntos else {display_name: user_id}

if not df_perfis_ext.empty:
    for _, row in df_perfis_ext.iterrows():
        opcoes_comprador[f"{row['nome']} (Dependente)"] = f"EXT_{row['nome']}"

nomes_compradores = list(opcoes_comprador.keys())
idx_atual = nomes_compradores.index(display_name) if display_name in nomes_compradores else 0

def get_comprador_nome(row):
    if pd.notna(row.get("comprador_externo")) and row.get("comprador_externo"):
        return f"{row['comprador_externo']} (Dependente)"
    return mapa_nomes.get(row["profile_id"], "Desconhecido")

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
# SIDEBAR: OPERAÇÕES E LANÇAMENTOS UNIFICADOS
# -------------------------------------------------------------
with st.sidebar:
    st.header("⚡ Gestão Financeira")
    
    with st.expander("💵 Nova Renda", expanded=False):
        with st.form("form_rendas", clear_on_submit=True):
            st.markdown("### 📥 Adicionar Entrada")
            origem = st.text_input("Fonte Pagadora", placeholder="Ex: Salário da Empresa X")
            valor_renda = st.number_input("Valor Líquido (R$)", min_value=0.0, step=100.0, format="%.2f")
            tipo_renda = st.selectbox("Modalidade", TIPOS_RENDA)
            data_r = st.date_input("Data do Recebimento", value=hoje)
            quem_recebeu = st.selectbox("Titular da Renda", nomes_compradores, index=idx_atual)
            is_shared_r = st.checkbox("Visível na Conta Conjunta?", value=False, key="chk_r")
            
            if st.form_submit_button("Salvar Entrada") and origem.strip():
                perfil_sel = opcoes_comprador[quem_recebeu]
                real_id = user_id if str(perfil_sel).startswith("EXT_") else perfil_sel
                if real_id != user_id: is_shared_r = True
                
                supabase.table("rendas").insert({
                    "profile_id": real_id, "origem": origem.strip(), "valor": float(valor_renda), 
                    "tipo": tipo_renda, "data_registro": str(data_r), "joint_account_id": joint_id if is_shared_r else None
                }).execute()
                st.rerun()

    with st.expander("💸 Novo Lançamento (Gasto)", expanded=False):
        with st.form("form_gasto_unificado", clear_on_submit=True):
            st.markdown("### 🛒 Registro de Despesa")
            desc_gasto = st.text_input("Descrição", placeholder="Ex: Mercado, Uber, Netflix...")
            
            tipo_gasto = st.selectbox("Modalidade", ["Gasto à vista", "Cartão - Parcelado", "Cartão - Recorrente/Assinatura"])
            
            if tipo_gasto == "Gasto à vista":
                val_total = st.number_input("Valor Pago (R$)", min_value=0.0, step=10.0, format="%.2f")
                metodo = st.selectbox("Forma de Pagamento", ["Pix", "Débito", "Dinheiro", "Crédito (1x)"])
                tot_p, pagas_p, val_parc = 1, (1 if metodo != "Crédito (1x)" else 0), val_total
                if metodo == "Crédito (1x)": metodo = "Crédito"
            elif tipo_gasto == "Cartão - Parcelado":
                val_total = st.number_input("Valor Total da Compra (R$)", min_value=0.0, step=50.0, format="%.2f")
                c1, c2 = st.columns(2)
                with c1: tot_p = st.number_input("Total de Parcelas", min_value=2, value=2)
                with c2: pagas_p = st.number_input("Parcelas Já Pagas", min_value=0, value=0)
                val_parc = val_total / tot_p if tot_p > 0 else 0
                metodo = "Crédito"
            else:
                val_parc = st.number_input("Mensalidade Atual (R$)", min_value=0.0, step=10.0, format="%.2f")
                val_total, tot_p, pagas_p = val_parc, 999, 0
                metodo = "Crédito"

            banco_vinculado = st.selectbox("Conta / Cartão Utilizado", lista_bancos)
            quem_comprou = st.selectbox("Responsável (Quem gastou?)", nomes_compradores, index=idx_atual)
            cat_gasto = st.selectbox("Categoria", CATEGORIAS)
            dest_gasto = st.selectbox("Destino", DESTINOS)
            is_shared_g = st.checkbox("Visível na Conta Conjunta?", value=False, key="chk_g_uni")

            if st.form_submit_button("Registrar Lançamento") and desc_gasto.strip():
                comprador_sel = opcoes_comprador[quem_comprou]
                
                # Desacoplamento para perfis dependentes (sem login)
                if str(comprador_sel).startswith("EXT_"):
                    real_profile_id = user_id
                    comp_externo = comprador_sel.replace("EXT_", "")
                    if ja_info: is_shared_g = True
                else:
                    real_profile_id = comprador_sel
                    comp_externo = None
                    if real_profile_id != user_id: is_shared_g = True
                
                supabase.table("gastos").insert({
                    "profile_id": real_profile_id, "joint_account_id": joint_id if is_shared_g else None,
                    "comprador_externo": comp_externo, "descricao": desc_gasto.strip(), 
                    "valor_total": float(val_total), "valor_parcela": float(val_parc),
                    "parcelas_pagas": int(pagas_p), "parcelas_totais": int(tot_p), "metodo_pagamento": metodo,
                    "categoria": cat_gasto, "banco_vinculado": banco_vinculado, "natureza": "Essencial", 
                    "destino": dest_gasto, "shared": is_shared_g, "data_registro": str(hoje)
                }).execute()
                st.rerun()

    with st.expander("👥 Adicionar Perfil Dependente (S/ Login)"):
        st.caption("Cadastre familiares (ex: Filho) que utilizam seus cartões compartilhados, mas não acessarão o app.")
        with st.form("form_novo_dependente", clear_on_submit=True):
            nome_dep = st.text_input("Nome do Dependente", placeholder="Ex: Lucas, Letícia...")
            if st.form_submit_button("Criar Perfil Local") and nome_dep.strip():
                supabase.table("perfis_cartao").insert({
                    "profile_id": user_id, "joint_account_id": joint_id, "nome": nome_dep.strip()
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
                is_shared_b = st.checkbox("Cartão da Casa (Conjunto)?", value=False, key="chk_bnc")
                if st.form_submit_button("Registrar Instituição") and nome_b.strip():
                    supabase.table("contas_bancos").insert({
                        "profile_id": user_id, "joint_account_id": joint_id if is_shared_b else None,
                        "nome_banco": nome_b.strip(), "limite_credito": float(lim_b),
                        "dia_fechamento": int(dia_f), "dia_vencimento": int(dia_v), 
                        "emprestimo_ativo": 0.0, "financiamento_ativo": 0.0, "shared": is_shared_b
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
            nome_ativo = st.text_input("Ativo", placeholder="Ex: Caixinha Reserva...")
            cat_inv = st.selectbox("Classe", ["Caixinha", "Renda Fixa / CDI", "Tesouro Direto", "Ações / FIIs"])
            val_acum = st.number_input("Saldo Atual (R$)", min_value=0.0, step=100.0, format="%.2f")
            aporte_plano = st.number_input("Aporte Mensal (R$)", min_value=0.0, step=50.0, format="%.2f")
            is_shared_inv = st.checkbox("Reserva Conjunta?", value=False, key="chk_inv")
            if st.form_submit_button("Adicionar à Carteira") and nome_ativo.strip():
                supabase.table("investimentos").insert({
                    "profile_id": user_id, "joint_account_id": joint_id if is_shared_inv else None,
                    "ativo": nome_ativo.strip(), "categoria": cat_inv,
                    "valor_acumulado": float(val_acum), "aporte_mensal_planejado": float(aporte_plano),
                    "taxa_anual_estimada": 10.0, "shared": is_shared_inv
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
k3.metric("🏦 Saldo de Caixa Livre", f"R$ {saldo_livre:,.2f}", delta="Superávit Operacional" if saldo_livre >= 0 else "Déficit Detectado", delta_color="normal" if saldo_livre >= 0 else "inverse")
st.markdown("---")

# -------------------------------------------------------------
# ABAS DO APLICATIVO
# -------------------------------------------------------------
tab_bancos, tab_extrato, tab_graficos, tab_simulador, tab_perfis = st.tabs([
    "🏦 Cartões & Limites", "📝 Extrato Analítico", "📊 BI & Divisão", "📈 Simulador de Caixinhas", "👥 Perfis & Redes"
])

with tab_bancos:
    st.subheader("Painel de Cartões de Crédito")
    if not df_bancos.empty:
        colunas = st.columns(2)
        dia_atual = hoje.day

        for idx, (_, b) in enumerate(df_bancos.iterrows()):
            compras_banco = df_gastos[(df_gastos["banco_vinculado"] == b["nome_banco"]) & (df_gastos["metodo_pagamento"] == "Crédito")]
            fatura_mes, limite_preso = 0.0, 0.0
            
            gastos_por_usuario = {nome: 0.0 for nome in mapa_nomes.values()}
            if not df_perfis_ext.empty:
                for _, r_dep in df_perfis_ext.iterrows():
                    gastos_por_usuario[f"{r_dep['nome']} (Dependente)"] = 0.0

            if not compras_banco.empty:
                for _, row_g in compras_banco.iterrows():
                    comprador = get_comprador_nome(row_g)
                    if comprador not in gastos_por_usuario:
                        gastos_por_usuario[comprador] = 0.0
                        
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
                if fatura_mes > 0:
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

with tab_extrato:
    aba_gastos, aba_rendas = st.tabs(["💸 Lançamentos de Saída", "💵 Entradas e Receitas"])
    
    with aba_gastos:
        if not df_gastos.empty:
            df_display = df_gastos.copy()
            df_display["Comprador"] = df_display.apply(get_comprador_nome, axis=1)
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
            df_r_disp["Recebedor"] = df_r_disp.apply(get_comprador_nome, axis=1)
            
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

with tab_graficos:
    st.subheader("Business Intelligence & Custos")
    if not df_gastos.empty:
        df_graficos = df_gastos.copy()
        df_graficos["Comprador"] = df_graficos.apply(get_comprador_nome, axis=1)
        
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

with tab_simulador:
    st.subheader("Ativos e Patrimônio Acumulado")
    if not df_inv.empty:
        df_inv_disp = df_inv.copy()
        df_inv_disp["Dono"] = df_inv_disp.apply(get_comprador_nome, axis=1)
        
        max_val = float(df_inv_disp["valor_acumulado"].max() * 1.5) if not df_inv_disp.empty else 10000.0
        
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
    st.subheader("📈 Projeção Estratégica Baseada no CDI")
    
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

with tab_perfis:
    st.subheader("Gerenciar Perfis Secundários (Dependentes)")
    if not df_perfis_ext.empty:
        for _, dep in df_perfis_ext.iterrows():
            col_d1, col_d2, col_d3 = st.columns([5, 2, 2])
            with col_d1: st.markdown(f"**{dep['nome']}**")
            with col_d2:
                with st.popover("✏️ Editar"):
                    novo_nome_dep = st.text_input("Novo nome", value=dep["nome"], key=f"edit_dep_{dep['id']}")
                    if st.button("Salvar", key=f"btn_edit_dep_{dep['id']}"):
                        supabase.table("perfis_cartao").update({"nome": novo_nome_dep}).eq("id", dep['id']).execute()
                        st.rerun()
            with col_d3:
                if st.button("🗑️ Remover", key=f"del_dep_{dep['id']}"):
                    supabase.table("perfis_cartao").delete().eq("id", dep['id']).execute()
                    st.rerun()
    else:
        st.info("Nenhum dependente cadastrado no momento.")

    st.markdown("---")
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
