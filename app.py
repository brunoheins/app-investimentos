import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
import plotly.express as px

st.set_page_config(page_title="App Investimentos v1.0", layout="wide")

# Função para ler os dados do Google Sheets
def ler_planilha(aba_nome):
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
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
    if st.sidebar.button("Sair do App"):
        st.session_state.logado = False
        st.rerun()

    st.title("📊 Seu Painel de Investimentos")

    aba1, aba2, aba3 = st.tabs(["💼 Resumo da Aplicação", "📈 Evolução do Saldo", "🎯 Guia de Aportes"])

    # 1ª TELA: RESUMO DA APLICAÇÃO (COM AGREGAÇÃO E PREÇO MÉDIO PONDERADO)
    with aba1:
        st.header("Resumo Geral da Carteira")
        
        df_invest = ler_planilha("Investimentos")
        if not df_invest.empty:
            df_invest['Email'] = df_invest['Email'].astype(str).str.strip().str.lower()
            dados_usuario = df_invest[df_invest['Email'] == st.session_state.email].copy()
            
            if not dados_usuario.empty:
                # Normalização de strings para evitar duplicidade por erro de digitação
                dados_usuario['Ativo'] = dados_usuario['Ativo'].astype(str).str.strip().str.upper()
                dados_usuario['Categoria'] = dados_usuario['Categoria'].astype(str).str.strip()
                
                # Conversão segura para números
                dados_usuario['Quantidade'] = pd.to_numeric(dados_usuario['Quantidade'], errors='coerce').fillna(0)
                dados_usuario['PrecoMedio'] = pd.to_numeric(dados_usuario['PrecoMedio'], errors='coerce').fillna(0)
                dados_usuario['PrecoAtual'] = pd.to_numeric(dados_usuario['PrecoAtual'], errors='coerce').fillna(0)
                
                # Cálculos financeiros no nível da linha antes de agrupar
                dados_usuario['TotalInvestido'] = dados_usuario['Quantidade'] * dados_usuario['PrecoMedio']
                dados_usuario['TotalAtual'] = dados_usuario['Quantidade'] * dados_usuario['PrecoAtual']
                
                # --- PROCESSAMENTO DOS DADOS (AGREGAÇÃO POR ATIVO E CATEGORIA) ---
                carteira_agrupada = dados_usuario.groupby(['Ativo', 'Categoria']).agg({
                    'Quantidade': 'sum',
                    'TotalInvestido': 'sum',
                    'TotalAtual': 'sum',
                    'PrecoAtual': 'first'  # O preço atual do GOOGLEFINANCE tende a ser idêntico para o mesmo ativo
                }).reset_index()
                
                # Cálculo do Preço Médio Ponderado da Carteira (Total Investido / Quantidade Total)
                carteira_agrupada['PrecoMedio'] = carteira_agrupada['TotalInvestido'] / carteira_agrupada['Quantidade'].replace(0, 1)
                carteira_agrupada.loc[carteira_agrupada['Quantidade'] == 0, 'PrecoMedio'] = 0
                
                # Cálculo da Evolução Percentual baseada no novo preço médio ponderado
                carteira_agrupada['EvolucaoPct'] = ((carteira_agrupada['PrecoAtual'] - carteira_agrupada['PrecoMedio']) / carteira_agrupada['PrecoMedio'].replace(0, 1)) * 100
                carteira_agrupada.loc[carteira_agrupada['PrecoMedio'] == 0, 'EvolucaoPct'] = 0
                
                # --- VISÃO GLOBAL DA CARTEIRA ---
                total_carteira_investido = carteira_agrupada['TotalInvestido'].sum()
                total_carteira_atual = carteira_agrupada['TotalAtual'].sum()
                evolucao_total_carteira = ((total_carteira_atual - total_carteira_investido) / total_carteira_investido if total_carteira_investido > 0 else 0) * 100
                
                # Exibição de Cards com Resumo Geral
                col_c1, col_c2, col_c3 = st.columns(3)
                col_c1.metric("Total Investido na Carteira", f"R$ {total_carteira_investido:,.2f}")
                col_c2.metric("Valor Atual da Carteira", f"R$ {total_carteira_atual:,.2f}")
                col_c3.metric("Evolução Global", f"{evolucao_total_carteira:+.2f}%")
                
                st.markdown("---")
                
                # --- GRÁFICO DE PIZZA (DISTRIBUIÇÃO POR CATEGORIA) ---
                st.subheader("Distribuição do Patrimônio por Categoria")
                df_categoria = carteira_agrupada.groupby('Categoria')['TotalAtual'].sum().reset_index()
                
                fig = px.pie(
                    df_categoria, 
                    values='TotalAtual', 
                    names='Categoria', 
                    hole=0.4,
                    color_discrete_sequence=px.colors.qualitative.Safe
                )
                st.plotly_chart(fig, use_container_width=True)
                
                st.markdown("---")
                
                # --- SEÇÕES SEPARADAS POR CATEGORIA ---
                st.subheader("Detalhamento por Categorias e Ativos")
                
                categorias_unicas = carteira_agrupada['Categoria'].unique()
                
                for cat in categorias_unicas:
                    nome_categoria = cat if str(cat).strip() != "" else "Sem Categoria"
                    with st.expander(f"📁 Categoria: {nome_categoria}", expanded=True):
                        df_filtrado = carteira_agrupada[carteira_agrupada['Categoria'] == cat].copy()
                        
                        invest_cat = df_filtrado['TotalInvestido'].sum()
                        atual_cat = df_filtrado['TotalAtual'].sum()
                        evol_cat = ((atual_cat - invest_cat) / invest_cat if invest_cat > 0 else 0) * 100
                        
                        col_sub1, col_sub2, col_sub3 = st.columns(3)
                        col_sub1.write(f"**Investido:** R$ {invest_cat:,.2f}")
                        col_sub2.write(f"**Valor Atual:** R$ {atual_cat:,.2f}")
                        col_sub3.write(f"**Evolução:** {evol_cat:+.2f}%")
                        
                        # Preparação da tabela para exibição
                        df_exibicao = df_filtrado[['Ativo', 'Quantidade', 'PrecoMedio', 'PrecoAtual', 'TotalInvestido', 'TotalAtual', 'EvolucaoPct']].copy()
                        
                        # Formatações visuais
                        df_exibicao['Quantidade'] = df_exibicao['Quantidade'].map('{:,.2f}'.format)
                        df_exibicao['PrecoMedio'] = df_exibicao['PrecoMedio'].map('R$ {:,.2f}'.format)
                        df_exibicao['PrecoAtual'] = df_exibicao['PrecoAtual'].map('R$ {:,.2f}'.format)
                        df_exibicao['TotalInvestido'] = df_exibicao['TotalInvestido'].map('R$ {:,.2f}'.format)
                        df_exibicao['TotalAtual'] = df_exibicao['TotalAtual'].map('R$ {:,.2f}'.format)
                        df_exibicao['EvolucaoPct'] = df_exibicao['EvolucaoPct'].map('{:+.2f}%'.format)
                        
                        st.dataframe(df_exibicao, use_container_width=True)
            else:
                st.info("Nenhum investimento cadastrado na planilha para este e-mail.")
        else:
            st.error("Erro ao ler os dados da aba 'Investimentos'.")

    # ABA 2: EVOLUÇÃO DO SALDO
    with aba2:
        st.header("Histórico de Evolução do Saldo")
        df_saldo = ler_planilha("Saldo")
        if not df_saldo.empty:
            df_saldo['Email'] = df_saldo['Email'].astype(str).str.strip().str.lower()
            dados_usuario = df_saldo[df_saldo['Email'] == st.session_state.email]
            if not dados_usuario.empty:
                st.line_chart(dados_usuario.set_index('Data')['Valor'])
                st.dataframe(dados_usuario[['Data', 'Valor']], use_container_width=True)
            else:
                st.info("Nenhum histórico de saldo encontrado.")

    # ABA 3: GUIA DE APORTES
    with aba3:
        st.header("Estratégia e Guia de Aportes")
        df_aportes = ler_planilha("Aportes")
        if not df_aportes.empty:
            df_aportes['Email'] = df_aportes['Email'].astype(str).str.strip().str.lower()
            dados_usuario = df_aportes[df_aportes['Email'] == st.session_state.email]
            if not dados_usuario.empty:
                st.dataframe(dados_usuario[['MetaAtivo', 'PorcentagemMeta']], use_container_width=True)
            else:
                st.info("Nenhuma meta de aporte configurada.")
