import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json

st.set_page_config(page_title="App Investimentos v1.0", layout="wide")

# Função para ler os dados do Google Sheets
def ler_planilha(aba_nome):
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        # Mudança: Lendo a credencial de forma segura a partir das configurações da nuvem
        creds_dict = json.loads(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open("App_Investimentos").worksheet(aba_nome)
        return pd.DataFrame(sheet.get_all_records())
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        return pd.DataFrame()

# Controle de estado do Login (Sessão)
if 'logado' not in st.session_state:
    st.session_state.logado = False
    st.session_state.email = ""
    st.session_state.nome = ""

# --- TELA DE LOGIN ---
if not st.session_state.logado:
    st.title("🔑 Acesso ao Sistema de Investimentos")
    email_input = st.text_input("E-mail")
    senha_input = st.text_input("Senha", type="password")
    
    if st.button("Entrar"):
        df_usuarios = ler_planilha("Usuarios")
        if not df_usuarios.empty:
            usuario = df_usuarios[(df_usuarios['Email'] == email_input) & (df_usuarios['Senha'] == str(senha_input))]
            if not usuario.empty:
                if usuario.iloc[0]['Status'] == 'Ativo':
                    st.session_state.logado = True
                    st.session_state.email = email_input
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
    if st.sidebar.button("Sair do App"):
        st.session_state.logado = False
        st.rerun()

    st.title("📊 Seu Painel de Investimentos")

    aba1, aba2, aba3 = st.tabs(["📈 Evolução do Saldo", "💼 Controle de Investimentos", "🎯 Guia de Aportes"])

    # ABA 1: EVOLUÇÃO DO SALDO
    with aba1:
        st.header("Histórico de Evolução do Saldo")
        df_saldo = ler_planilha("Saldo")
        if not df_saldo.empty:
            dados_usuario = df_saldo[df_saldo['Email'] == st.session_state.email]
            if not dados_usuario.empty:
                st.line_chart(dados_usuario.set_index('Data')['Valor'])
                st.dataframe(dados_usuario[['Data', 'Valor']], use_container_width=True)
            else:
                st.info("Nenhum histórico de saldo encontrado.")

    # ABA 2: CONTROLE DE INVESTIMENTOS
    with aba2:
        st.header("Meus Ativos Atualizados")
        df_invest = ler_planilha("Investimentos")
        if not df_invest.empty:
            dados_usuario = df_invest[df_invest['Email'] == st.session_state.email]
            if not dados_usuario.empty:
                st.dataframe(dados_usuario[['Ativo', 'Quantidade', 'PrecoMedio']], use_container_width=True)
            else:
                st.info("Nenhum ativo cadastrado ainda.")

    # ABA 3: GUIA DE APORTES
    with aba3:
        st.header("Estratégia e Guia de Aportes")
        df_aportes = ler_planilha("Aportes")
        if not df_aportes.empty:
            dados_usuario = df_aportes[df_aportes['Email'] == st.session_state.email]
            if not dados_usuario.empty:
                st.dataframe(dados_usuario[['MetaAtivo', 'PorcentagemMeta']], use_container_width=True)
            else:
                st.info("Nenhuma meta de aporte configurada.")
