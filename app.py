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

# Mapeamento rápido de IDs para Nomes
mapa_nomes = {m["id"]: m.get("display_name", "Membro") for m in membros_conjuntos} if membros_conjuntos else {user_id: display_name}

supabase = get_supabase_client()

# -------------------------------------------------------------
# CARREGAMENTO DE DADOS (RLS garante a segurança automática)
# -------------------------------------------------------------
def load_all_data():
    r_bancos = supabase.table("contas_bancos").select("*").execute()
    r_gastos = supabase.table("gastos").select("*").order("data_registro", desc=True).execute()
    r_rendas = supabase.table("rendas").select("*").order("data_registro", desc=True).execute()
    r_inv = supabase.table("investimentos").select("*").order("id").execute()
    
    df_b = pd.DataFrame(r_bancos.data) if r_bancos.data else pd.DataFrame(columns=["id", "nome_banco", "limite_credito", "dia_fechamento", "dia_vencimento", "profile_id"])
    df_g = pd.DataFrame(r_gastos.data) if r_gastos.data else pd.DataFrame(columns=["id", "descricao", "valor_parcela", "parcelas_pagas", "parcelas_totais", "metodo_pagamento", "categoria", "banco_vinculado", "natureza", "destino", "data_registro", "profile_id"])
    df_r = pd.DataFrame(r_rendas.data) if r_rendas.data else pd.DataFrame(columns=["id", "origem", "valor", "tipo", "data_registro", "profile_id"])
    df_i = pd.DataFrame(r_inv.data) if r_inv.data else pd.DataFrame(columns=["id", "ativo", "categoria", "valor_acumulado", "aporte_mensal_planejado", "taxa_anual_estimada", "profile_id"])
    
    return df_b, df_g, df_r, df_i

df_bancos, df_gastos, df_rendas, df_inv = load_all_data()
lista_bancos = df_bancos["nome_banco"].unique().tolist() if not df_bancos.empty else ["Nenhum / Dinheiro"]
hoje = date.today()

# -------------------------------------------------------------
# HEADER
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
st.markdown("---")

# -------------------------------------------------------------
# SIDEBAR: OPERAÇÕES E LANÇAMENTOS
# -------------------------------------------------------------
with st.sidebar:
    st.header("⚡ Lançamentos")
    
    # 1. Rendas
    with st.expander("💵 Nova Renda", expanded=False):
        with st.form("form_rendas", clear_on_submit=True):
            origem = st.text_input("Origem")
            valor_renda = st.number_input("Valor Líquido (R$)", min_value=1.0, step=50.0)
            tipo_renda = st.selectbox("Tipo de Entrada", TIPOS_RENDA)
            data_r = st.date_input("Data do Recebimento", value=hoje)
            if st.form_submit_button("Salvar Entrada") and origem.strip():
                supabase.table("rendas").insert({"profile_id": user_id, "origem": origem.strip(), "valor": float(valor_renda), "tipo": tipo_renda, "data_registro": str(data_r)}).execute()
                st.rerun()

    # 2. Dia a Dia
    with st.expander("☕ Gasto Rápido (Dia a Dia)", expanded=False):
        with st.form("form_dia_a_dia", clear_on_submit=True):
            desc_dia = st.text_input("O que comprou?")
            val_dia = st.number_input("Valor Pago (R$)", min_value=0.10, step=2.0)
            metodo_dia = st.selectbox("Pagamento", ["Pix", "Débito", "Dinheiro"])
            banco_dia = st.selectbox("Conta", lista_bancos)
            cat_dia = st.selectbox("Categoria", CATEGORIAS)
            dest_dia = st.selectbox("Destino", DESTINOS)
            is_shared = st.checkbox("Gasto compartilhado (Conta Conjunta)?", value=bool(ja_info))
            if st.form_submit_button("Lançar Gasto") and desc_dia.strip():
                supabase.table("gastos").insert({
                    "profile_id": user_id, "joint_account_id": joint_id if is_shared else None,
                    "descricao": desc_dia.strip(), "valor_total": float(val_dia), "valor_parcela": float(val_dia),
                    "parcelas_pagas": 1, "parcelas_totais": 1, "metodo_pagamento": metodo_dia,
                    "categoria": cat_dia, "banco_vinculado": banco_dia, "destino": dest_dia, "shared": is_shared, "data_registro": str(hoje)
                }).execute()
                st.rerun()

    # 3. Cartão de Crédito
    with st.expander("💳 Cartão: Parcelados & Recorrentes", expanded=False):
        is_recorrente = st.checkbox("🔁 Gasto recorrente mensal?")
        with st.form("form_cartao", clear_on_submit=True):
            desc_c = st.text_input("Descrição")
            if is_recorrente:
                val_mensal = st.number_input("Valor Mensalidade (R$)", min_value=1.0, step=10.0)
                tot_p, pagas_p, val_total_c, val_parcela_c = 999, 0, val_mensal, val_mensal
            else:
                val_total_c = st.number_input("Valor Total (R$)", min_value=1.0, step=20.0)
                c_p1, c_p2 = st.columns(2)
                with c_p1: tot_p = st.number_input("Total Parcelas", min_value=1, value=1)
                with c_p2: pagas_p = st.number_input("Já Pagas", min_value=0, value=0)
                val_parcela_c = val_total_c / tot_p if tot_p > 0 else val_total_c
                st.caption(f"Parcela: **R$ {val_parcela_c:.2f}**")

            banco_c = st.selectbox("Cartão", lista_bancos)
            cat_c = st.selectbox("Categoria", CATEGORIAS)
            dest_c = st.selectbox("Destino", DESTINOS)
            is_shared_c = st.checkbox("Visível para a Conta Conjunta?", value=bool(ja_info))

            if st.form_submit_button("Salvar no Cartão") and desc_c.strip():
                supabase.table("gastos").insert({
                    "profile_id": user_id, "joint_account_id": joint_id if is_shared_c else None,
                    "descricao": desc_c.strip(), "valor_total": float(val_total_c), "valor_parcela": float(val_parcela_c),
                    "parcelas_pagas": int(pagas_p), "parcelas_totais": int(tot_p), "metodo_pagamento": "Crédito",
                    "categoria": cat_c, "banco_vinculado": banco_c, "destino": dest_c, "shared": is_shared_c, "data_registro": str(hoje)
                }).execute()
                st.rerun()

    # 4. Bancos & Investimentos
    with st.expander("🏦 Gerenciar Bancos & Limites"):
        with st.form("form_banco", clear_on_submit=True):
            nome_b = st.text_input("Nome do Cartão/Banco")
            lim_b = st.number_input("Limite (R$)", min_value=0.0, step=100.0)
            d1, d2 = st.columns(2)
            with d1: dia_f = st.number_input("Fechamento", min_value=1, max_value=31, value=1)
            with d2: dia_v = st.number_input("Vencimento", min_value=1, max_value=31, value=10)
            is_shared_b = st.checkbox("Cartão Compartilhado?", value=bool(ja_info))
            if st.form_submit_button("Salvar Banco") and nome_b.strip():
                supabase.table("contas_bancos").insert({
                    "profile_id": user_id, "joint_account_id": joint_id if is_shared_b else None,
                    "nome_banco": nome_b.strip(), "limite_credito": float(lim_b),
                    "dia_fechamento": int(dia_f), "dia_vencimento": int(dia_v), "shared": is_shared_b
                }).execute()
                st.rerun()

# -------------------------------------------------------------
# KPIs
# -------------------------------------------------------------
renda_total = df_rendas["valor"].sum() if not df_rendas.empty else 0.0
saidas_mes = df_gastos["valor_parcela"].sum() if not df_gastos.empty else 0.0
saldo_livre = renda_total - saidas_mes

k1, k2, k3 = st.columns(3)
k1.metric("💰 Renda Total", f"R$ {renda_total:,.2f}")
k2.metric("📉 Saídas do Mês", f"R$ {saidas_mes:,.2f}", delta=f"{(saidas_mes/renda_total*100 if renda_total else 0):.1f}% da Renda", delta_color="inverse")
k3.metric("🏦 Saldo Livre Real", f"R$ {saldo_livre:,.2f}", delta="Superávit" if saldo_livre >= 0 else "Déficit", delta_color="normal" if saldo_livre >= 0 else "inverse")
st.markdown("---")

# -------------------------------------------------------------
# ABAS DO APLICATIVO
# -------------------------------------------------------------
tab_bancos, tab_extrato, tab_perfis = st.tabs(["🏦 Cartões Compartilhados & Limites", "📝 Extrato Analítico", "👥 Perfis & Autenticação"])

# --- ABA 1: BANCOS E CARTÕES COMPARTILHADOS ---
with tab_bancos:
    st.subheader("Cartões, Vencimentos e Divisão de Fatura")
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
                
                if dia_atual < dia_f: st.info(f"🟢 Fatura Aberta (Fecha dia {dia_f:02d})")
                elif dia_atual <= dia_v: st.warning(f"⚠️ Fatura Fechada! Vence dia {dia_v:02d}")
                else: st.error(f"🚨 Atrasada! Venceu dia {dia_v:02d}")

                st.write(f"🧾 **Fatura Atual:** :red[R$ {fatura_mes:,.2f}]")
                
                # Exibe quem gastou o quê na fatura!
                if b['shared'] and fatura_mes > 0:
                    for nome, valor in gastos_por_usuario.items():
                        if valor > 0:
                            st.caption(f"👤 {nome}: R$ {valor:,.2f} ({(valor/fatura_mes)*100:.1f}%)")

                st.write(f"💳 Limite: R$ {limite_total:,.2f} | 🟢 Disp: R$ {limite_disp:,.2f}")
                if limite_total > 0: st.progress(min(1.0, limite_preso / limite_total))
                
                if fatura_mes > 0 and st.button(f"✅ Quitar Fatura {b['nome_banco']}", key=f"pay_{b['id']}"):
                    for _, row_g in compras_banco.iterrows():
                        if row_g["parcelas_totais"] != 999 and row_g["parcelas_pagas"] < row_g["parcelas_totais"]:
                            supabase.table("gastos").update({"parcelas_pagas": int(row_g["parcelas_pagas"]) + 1}).eq("id", row_g["id"]).execute()
                    st.success("Fatura quitada! Limites liberados.")
                    st.rerun()
                st.markdown("---")

# --- ABA 2: EXTRATO ---
with tab_extrato:
    if not df_gastos.empty:
        df_display = df_gastos.copy()
        df_display["Comprador"] = df_display["profile_id"].map(mapa_nomes).fillna("Desconhecido")
        df_display["Progresso"] = df_display.apply(lambda r: "Recorrente" if r["parcelas_totais"]==999 else f"{r['parcelas_pagas']}/{r['parcelas_totais']}", axis=1)
        
        st.dataframe(
            df_display[["data_registro", "Comprador", "descricao", "banco_vinculado", "valor_parcela", "Progresso", "destino"]],
            use_container_width=True, hide_index=True
        )
        
        del_id = st.selectbox("ID para excluir:", df_display["id"].tolist())
        if st.button("🗑️ Remover Registro"):
            supabase.table("gastos").delete().eq("id", del_id).execute()
            st.rerun()

# --- ABA 3: PERFIS ---
with tab_perfis:
    st.subheader("Configurações de Conta Conjunta")
    if ja_info:
        st.success(f"Você está na conta: **{ja_info['nome']}**")
        st.code(f"Código Convite: {ja_info['invite_code']}")
        st.write("Membros:")
        for m in membros_conjuntos:
            st.write(f"- {m.get('display_name', 'Membro')}")
        if st.button("Sair da Conta Conjunta"):
            leave_joint_account()
            st.rerun()
    else:
        c1, c2 = st.columns(2)
        with c1:
            novo_nome = st.text_input("Criar Nova Conta Conjunta")
            if st.button("Criar"):
                create_joint_account(novo_nome)
                st.rerun()
        with c2:
            codigo = st.text_input("Entrar com Código")
            if st.button("Ingressar"):
                join_joint_account(codigo)
                st.rerun()
