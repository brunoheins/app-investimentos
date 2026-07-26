import streamlit as st
import pandas as pd
from utils import ler_planilha

# Configuração da página e CSS global DEVEM ser as primeiras coisas
st.set_page_config(page_title="App Investimentos v1.0", layout="wide")

st.markdown("""
    <style>
        .block-container { padding-top: 2rem; padding-bottom: 2rem; }
        h1 { font-size: 1.8rem !important; padding-bottom: 0.5rem !important; }
        h2 { font-size: 1.5rem !important; }
        h3 { font-size: 1.2rem !important; }
        p { font-size: 0.95rem !important; }
    </style>
""", unsafe_allow_html=True)

# Importando as telas moduladas
from menu import resumo, saldo, aportes, configuracao

# Controle de estado do Login
if 'logado' not in st.session_state:
    st.session_state.logado = False
    st.session_state.email = ""
    st.session_state.nome = ""

# --- TELA DE LOGIN ---
if not st.session_state.logado:
    st.title("🔑 Acesso ao Sistema de Investimentos")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        email_input = st.text_input("E-mail")
        senha_input = st.text_input("Senha", type="password")
        
        if st.button("Entrar", use_container_width=True):
            df_usuarios = ler_planilha("Usuarios")
            if not df_usuarios.empty:
                df_usuarios['Email'] = df_usuarios['Email'].astype(str).str.strip().str.lower()
                df_usuarios['Senha'] = df_usuarios['Senha'].astype(str).str.strip()
                
                email_valido = email_input.strip().lower()
                senha_valida = senha_input.strip()
                
                usuario = df_usuarios[(df_usuarios['Email'] == email_valido) & (df_usuarios['Senha'] == senha_valida)]
                
                if not usuario.empty:
                    status_usuario = str(usuario.iloc[0]['Status']).strip()
                    if status_usuario == 'Ativo':
                        st.session_state.logado = True
                        st.session_state.email = email_valido
                        st.session_state.nome = usuario.iloc[0]['Nome']
                        st.rerun()
                    else:
                        st.error("Seu acesso foi revogado pelo administrador.")
                else:
                    st.error("Usuário ou senha incorretos.")
            else:
                st.error("Erro ao acessar base de usuários.")

# --- APP AUTENTICADO ---
else:
    st.sidebar.write(f"👤 Usuário: **{st.session_state.nome}**")
    st.sidebar.markdown("---")
    
    menu_selecionado = st.sidebar.radio(
        "Navegação / Painéis:",
        ["💼 Resumo da Aplicação", "📈 Evolução do Saldo", "🎯 Guia de Aportes", "⚙️ Configuração da Carteira"]
    )
    
    st.sidebar.markdown("---")
    if st.sidebar.button("Sair do App"):
        st.session_state.clear()
        st.rerun()

    # Roteamento (Exibição da tela escolhida)
    if menu_selecionado == "💼 Resumo da Aplicação":
        resumo.render()
    
    elif menu_selecionado == "📈 Evolução do Saldo":
        saldo.render()
        
    elif menu_selecionado == "🎯 Guia de Aportes":
        aportes.render()
        
    elif menu_selecionado == "⚙️ Configuração da Carteira":
        configuracao.render()
