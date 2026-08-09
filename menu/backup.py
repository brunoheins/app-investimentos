import streamlit as st
import pandas as pd
import tempfile
import os
from utils import ler_planilha, deletar_registros_usuario, inserir_lote_registros

def render():
    st.title("📊 Importar e Exportar Dados (Excel)")
    st.markdown("Faça o backup completo ou a restauração dos seus dados utilizando planilhas do Excel (.xlsx).")
    
    # ==========================================
    # MÁGICA VISUAL: TRANSFORMANDO ABAS EM BOTÕES
    # ==========================================
    st.markdown("""
        <style>
            /* Estilo base para as abas (Inativas) */
            button[data-baseweb="tab"] {
                border: 1px solid #4B4C54 !important;
                border-radius: 6px !important;
                padding: 10px 24px !important;
                margin-right: 10px !important;
                background-color: transparent !important;
            }
            
            /* Estilo da aba ATIVA (Cor principal vermelha do seu tema) */
            button[data-baseweb="tab"][aria-selected="true"] {
                background-color: #FF4B4B !important;
                color: white !important;
                border: 1px solid #FF4B4B !important;
            }
            
            /* Remove a linha sublinhada que o Streamlit coloca por padrão */
            div[data-baseweb="tab-highlight"] {
                display: none !important;
            }
        </style>
    """, unsafe_allow_html=True)
    
    email_logado = st.session_state.email.strip().lower()
    
    tab_export, tab_import = st.tabs(["📤 Exportar para Excel", "📥 Importar do Excel"])
    
    # ... (O restante do código continua exatamente igual a partir daqui) ...
