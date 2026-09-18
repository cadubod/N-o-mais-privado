"""
styles.py — CSS customizado para o Gestor Financeiro.
Injete no app com: st.markdown(get_custom_css(), unsafe_allow_html=True)
"""

import streamlit as st


def get_custom_css() -> str:
    """Retorna o bloco <style> completo para injeção."""
    return """
<style>
/* ====== IMPORTAÇÃO DE FONTE ====== */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* ====== RESET / BASE ====== */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* ====== HEADER PRINCIPAL ====== */
.main .block-container {
    padding-top: 1.5rem;
    padding-bottom: 1rem;
    max-width: 1200px;
}

h1 {
    background: linear-gradient(135deg, #1B998B 0%, #118AB2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-weight: 700 !important;
    letter-spacing: -0.5px;
}

/* ====== CARDS DE MÉTRICA ====== */
div[data-testid="stMetric"] {
    background: linear-gradient(145deg, #1e2130 0%, #262b40 100%);
    border: 1px solid rgba(27, 153, 139, 0.25);
    border-radius: 14px;
    padding: 18px 22px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3),
                inset 0 1px 0 rgba(255, 255, 255, 0.05);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}

div[data-testid="stMetric"]:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 30px rgba(27, 153, 139, 0.25),
                inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

div[data-testid="stMetric"] label {
    color: #8D99AE !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}

div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-size: 1.6rem !important;
    font-weight: 700 !important;
    color: #FAFAFA !important;
}

/* ====== TABS ====== */
.stTabs [data-baseweb="tab-list"] {
    gap: 6px;
    background: rgba(14, 17, 23, 0.6);
    border-radius: 12px;
    padding: 4px;
}

.stTabs [data-baseweb="tab"] {
    border-radius: 10px;
    padding: 10px 20px;
    font-weight: 500;
    color: #8D99AE;
    transition: all 0.25s ease;
}

.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #1B998B 0%, #118AB2 100%) !important;
    color: #FAFAFA !important;
    font-weight: 600;
    box-shadow: 0 2px 12px rgba(27, 153, 139, 0.3);
}

/* ====== SIDEBAR ====== */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #12141c 0%, #1a1d2e 100%);
    border-right: 1px solid rgba(27, 153, 139, 0.15);
}

section[data-testid="stSidebar"] .stMarkdown h1,
section[data-testid="stSidebar"] .stMarkdown h2,
section[data-testid="stSidebar"] .stMarkdown h3 {
    color: #1B998B !important;
}

/* ====== BOTÕES ====== */
.stButton > button {
    background: linear-gradient(135deg, #1B998B 0%, #118AB2 100%);
    color: white;
    border: none;
    border-radius: 10px;
    padding: 8px 22px;
    font-weight: 600;
    letter-spacing: 0.3px;
    transition: all 0.3s ease;
    box-shadow: 0 2px 8px rgba(27, 153, 139, 0.3);
}

.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(27, 153, 139, 0.4);
    filter: brightness(1.1);
}

.stButton > button:active {
    transform: translateY(0);
}

/* ====== FORM SUBMIT BUTTON ====== */
.stFormSubmitButton > button {
    background: linear-gradient(135deg, #06D6A0 0%, #1B998B 100%);
    width: 100%;
    border-radius: 10px;
    font-weight: 600;
    padding: 10px;
    transition: all 0.3s ease;
}

.stFormSubmitButton > button:hover {
    box-shadow: 0 6px 20px rgba(6, 214, 160, 0.35);
    filter: brightness(1.1);
}

/* ====== INPUTS ====== */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stDateInput > div > div > input {
    border-radius: 10px !important;
    border: 1px solid rgba(27, 153, 139, 0.3) !important;
    background: rgba(30, 33, 48, 0.8) !important;
    transition: border-color 0.2s ease;
}

.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus {
    border-color: #1B998B !important;
    box-shadow: 0 0 0 2px rgba(27, 153, 139, 0.15) !important;
}

.stSelectbox > div > div {
    border-radius: 10px !important;
}

/* ====== PROGRESS BAR (metas) ====== */
.stProgress > div > div > div {
    background: linear-gradient(90deg, #1B998B, #06D6A0) !important;
    border-radius: 20px;
    transition: width 0.6s ease-in-out;
}

.stProgress > div > div {
    background: rgba(30, 33, 48, 0.6) !important;
    border-radius: 20px;
}

/* ====== EXPANDER ====== */
.streamlit-expanderHeader {
    border-radius: 10px;
    font-weight: 600;
    color: #FAFAFA;
    transition: background 0.2s ease;
}

.streamlit-expanderHeader:hover {
    background: rgba(27, 153, 139, 0.1);
}

/* ====== DATAFRAME / TABELAS ====== */
.stDataFrame {
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.2);
}

/* ====== ALERTAS (warning/success/info) ====== */
.stAlert {
    border-radius: 12px;
    border-left: 4px solid;
}

/* ====== DIVIDER ====== */
hr {
    border-color: rgba(27, 153, 139, 0.2) !important;
}

/* ====== ANIMAÇÃO FADE-IN PARA CONTEÚDO ====== */
@keyframes fadeInUp {
    from {
        opacity: 0;
        transform: translateY(15px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.main .block-container > div {
    animation: fadeInUp 0.4s ease-out;
}

/* ====== BADGE / TAG (helper class para st.markdown) ====== */
.badge-positive {
    display: inline-block;
    background: linear-gradient(135deg, #06D6A0, #1B998B);
    color: #fff;
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.3px;
}

.badge-negative {
    display: inline-block;
    background: linear-gradient(135deg, #FF6B6B, #EF476F);
    color: #fff;
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.3px;
}

.badge-info {
    display: inline-block;
    background: linear-gradient(135deg, #118AB2, #073B4C);
    color: #fff;
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 600;
}

/* ====== AUTH CONTAINER ====== */
.auth-container {
    max-width: 420px;
    margin: 4rem auto;
    padding: 2.5rem;
    background: linear-gradient(145deg, #1e2130, #262b40);
    border-radius: 20px;
    border: 1px solid rgba(27, 153, 139, 0.2);
    box-shadow: 0 8px 40px rgba(0, 0, 0, 0.4);
}

.auth-title {
    text-align: center;
    font-size: 1.8rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
    background: linear-gradient(135deg, #1B998B, #118AB2);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.auth-subtitle {
    text-align: center;
    color: #8D99AE;
    font-size: 0.9rem;
    margin-bottom: 1.5rem;
}

/* ====== PROFILE CARD ====== */
.profile-card {
    background: linear-gradient(145deg, #1e2130, #262b40);
    border: 1px solid rgba(27, 153, 139, 0.2);
    border-radius: 14px;
    padding: 20px;
    margin: 8px 0;
    display: flex;
    align-items: center;
    gap: 14px;
    transition: transform 0.2s ease;
}

.profile-card:hover {
    transform: translateY(-2px);
}

.profile-avatar {
    width: 48px;
    height: 48px;
    border-radius: 50%;
    background: linear-gradient(135deg, #1B998B, #118AB2);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.3rem;
    color: white;
    font-weight: 700;
    flex-shrink: 0;
}

.profile-info h4 {
    margin: 0;
    color: #FAFAFA;
    font-size: 1rem;
}

.profile-info p {
    margin: 0;
    color: #8D99AE;
    font-size: 0.82rem;
}

/* ====== INVITE CODE BOX ====== */
.invite-code {
    background: rgba(27, 153, 139, 0.12);
    border: 2px dashed rgba(27, 153, 139, 0.4);
    border-radius: 12px;
    padding: 16px;
    text-align: center;
    margin: 12px 0;
}

.invite-code code {
    font-size: 1.6rem;
    font-weight: 700;
    letter-spacing: 3px;
    color: #1B998B;
}

/* ====== GAUGE WRAPPER ====== */
.gauge-wrapper {
    text-align: center;
    padding: 10px;
}

/* ====== RESPONSIVIDADE MOBILE ====== */
@media (max-width: 768px) {
    .main .block-container {
        padding: 0.8rem 0.6rem;
    }

    div[data-testid="stMetric"] {
        padding: 12px 14px;
        border-radius: 10px;
    }

    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size: 1.2rem !important;
    }

    h1 {
        font-size: 1.4rem !important;
    }

    .stTabs [data-baseweb="tab"] {
        padding: 8px 12px;
        font-size: 0.82rem;
    }

    .auth-container {
        margin: 1.5rem auto;
        padding: 1.5rem;
    }
}
</style>
"""


def inject_css():
    """Atalho para injetar o CSS no app Streamlit."""
    st.markdown(get_custom_css(), unsafe_allow_html=True)
