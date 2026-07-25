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
        st.error(f"Erro de conexão ao ler aba '{aba_nome}': {e}")
        return pd.DataFrame()

# NOVA FUNÇÃO: Salvar ou Atualizar as configurações do usuário na planilha
def salvar_configuracao(email, dados_dict):
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = json.loads(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open("App_Investimentos").worksheet("Configuracao")
        
        df = pd.DataFrame(sheet.get_all_records())
        row_values = [
            email, dados_dict['RF'], dados_dict['RV'], 
            dados_dict['RV_Brasil'], dados_dict['RV_Exterior'], 
            dados_dict['BR_Acoes'], dados_dict['BR_FIIs'], 
            dados_dict['EX_Stocks'], dados_dict['EX_REITs'], dados_dict['EX_ETFs']
        ]
        
        # Se o usuário já tiver uma configuração salva, atualiza a linha correspondente
        if not df.empty and email in df['Email'].astype(str).str.strip().str.lower().values:
            idx = df[df['Email'].astype(str).str.strip().str.lower() == email].index[0]
            row_num = idx + 2 # +2 porque o pandas ignora o cabeçalho e é índice 0
            sheet.update(f"A{row_num}:J{row_num}", [row_values])
        else:
            # Se for um usuário novo, adiciona uma linha no final
            sheet.append_row(row_values)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar na planilha: {e}")
        return False

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
    # --- CONFIGURAÇÃO DA BARRA LATERAL (SIDEBAR) ---
    st.sidebar.write(f"👤 Usuário: **{st.session_state.nome}**")
    st.sidebar.markdown("---")
    
    # Atualizado: Adicionado o painel de configurações no menu lateral
    menu_selecionado = st.sidebar.radio(
        "Navegação / Painéis:",
        ["💼 Resumo da Aplicação", "📈 Evolução do Saldo", "🎯 Guia de Aportes", "⚙️ Configuração da Carteira"]
    )
    
    st.sidebar.markdown("---")
    if st.sidebar.button("Sair do App"):
        st.session_state.logado = False
        st.rerun()

    # --- CONTROLE DE TELAS DINÂMICO ---

    # TELA 1: RESUMO DA APLICAÇÃO
    if menu_selecionado == "💼 Resumo da Aplicação":
        st.title("📊 Resumo Geral da Carteira")
        
        df_invest = ler_planilha("Investimentos")
        if not df_invest.empty:
            df_invest['Email'] = df_invest['Email'].astype(str).str.strip().str.lower()
            dados_usuario = df_invest[df_invest['Email'] == st.session_state.email].copy()
            
            if not dados_usuario.empty:
                dados_usuario['Ativo'] = dados_usuario['Ativo'].astype(str).str.strip().str.upper()
                dados_usuario['Categoria'] = dados_usuario['Categoria'].astype(str).str.strip()
                
                dados_usuario['Quantidade'] = pd.to_numeric(dados_usuario['Quantidade'], errors='coerce').fillna(0)
                dados_usuario['PrecoMedio'] = pd.to_numeric(dados_usuario['PrecoMedio'], errors='coerce').fillna(0)
                dados_usuario['PrecoAtual'] = pd.to_numeric(dados_usuario['PrecoAtual'], errors='coerce').fillna(0)
                
                dados_usuario['TotalInvestido'] = dados_usuario['Quantidade'] * dados_usuario['PrecoMedio']
                dados_usuario['TotalAtual'] = dados_usuario['Quantidade'] * dados_usuario['PrecoAtual']
                
                carteira_agrupada = dados_usuario.groupby(['Ativo', 'Categoria']).agg({
                    'Quantidade': 'sum',
                    'TotalInvestido': 'sum',
                    'TotalAtual': 'sum',
                    'PrecoAtual': 'first'
                }).reset_index()
                
                carteira_agrupada['PrecoMedio'] = carteira_agrupada['TotalInvestido'] / carteira_agrupada['Quantidade'].replace(0, 1)
                carteira_agrupada.loc[carteira_agrupada['Quantidade'] == 0, 'PrecoMedio'] = 0
                
                carteira_agrupada['EvolucaoPct'] = ((carteira_agrupada['PrecoAtual'] - carteira_agrupada['PrecoMedio']) / carteira_agrupada['PrecoMedio'].replace(0, 1)) * 100
                carteira_agrupada.loc[carteira_agrupada['PrecoMedio'] == 0, 'EvolucaoPct'] = 0
                
                total_carteira_investido = carteira_agrupada['TotalInvestido'].sum()
                total_carteira_atual = carteira_agrupada['TotalAtual'].sum()
                evolucao_total_carteira = ((total_carteira_atual - total_carteira_investido) / total_carteira_investido if total_carteira_investido > 0 else 0) * 100
                
                col_c1, col_c2, col_c3 = st.columns(3)
                col_c1.metric("Total Investido na Carteira", f"R$ {total_carteira_investido:,.2f}")
                col_c2.metric("Valor Atual da Carteira", f"R$ {total_carteira_atual:,.2f}")
                col_c3.metric("Evolução Global", f"{evolucao_total_carteira:+.2f}%")
                
                st.markdown("---")
                
                st.subheader("Distribuição do Patrimônio por Categoria")
                df_categoria = carteira_agrupada.groupby('Categoria')['TotalAtual'].sum().reset_index()
                
                fig = px.pie(df_categoria, values='TotalAtual', names='Categoria', hole=0.4, color_discrete_sequence=px.colors.qualitative.Safe)
                st.plotly_chart(fig, use_container_width=True)
                
                st.markdown("---")
                
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
                        
                        df_exibicao = df_filtrado[['Ativo', 'Quantidade', 'PrecoMedio', 'PrecoAtual', 'TotalInvestido', 'TotalAtual', 'EvolucaoPct']].copy()
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

    # TELA 2: EVOLUÇÃO DO SALDO
    elif menu_selecionado == "📈 Evolução do Saldo":
        st.title("📈 Histórico de Evolução do Saldo")
        df_saldo = ler_planilha("Saldo")
        if not df_saldo.empty:
            df_saldo['Email'] = df_saldo['Email'].astype(str).str.strip().str.lower()
            dados_usuario = df_saldo[df_saldo['Email'] == st.session_state.email]
            if not dados_usuario.empty:
                st.line_chart(dados_usuario.set_index('Data')['Valor'])
                st.dataframe(dados_usuario[['Data', 'Valor']], use_container_width=True)
            else:
                st.info("Nenhum histórico de saldo encontrado.")

    # TELA 3: GUIA DE APORTES
    elif menu_selecionado == "🎯 Guia de Aportes":
        st.title("🎯 Estratégia e Guia de Aportes")
        df_aportes = ler_planilha("Aportes")
        if not df_aportes.empty:
            df_aportes['Email'] = df_aportes['Email'].astype(str).str.strip().str.lower()
            dados_usuario = df_aportes[df_aportes['Email'] == st.session_state.email]
            if not dados_usuario.empty:
                st.dataframe(dados_usuario[['MetaAtivo', 'PorcentagemMeta']], use_container_width=True)
            else:
                st.info("Nenhuma meta de aporte configurada.")

    # TELA 4: CONFIGURAÇÃO DA CARTEIRA (NOVA SEÇÃO SOLICITADA)
    elif menu_selecionado == "⚙️ Configuração da Carteira":
        st.title("⚙️ Definição de Metas de Alocação (Asset Allocation)")
        st.markdown("Estipule seus objetivos percentuais para cada classe de ativo. O sistema exige a validação de 100% por nível hierárquico antes de salvar.")
        
        # Tenta buscar as configurações salvas do usuário atual
        df_conf = ler_planilha("Configuracao")
        user_conf = {}
        if not df_conf.empty:
            df_conf['Email'] = df_conf['Email'].astype(str).str.strip().str.lower()
            row = df_conf[df_conf['Email'] == st.session_state.email]
            if not row.empty:
                user_conf = row.iloc[0].to_dict()
        
        # Definição de valores padrão (recuperados da planilha ou 0 se vazios)
        rf_def = float(user_conf.get('RF', 50.0))
        rv_def = float(user_conf.get('RV', 50.0))
        rv_br_def = float(user_conf.get('RV_Brasil', 50.0))
        rv_ex_def = float(user_conf.get('RV_Exterior', 50.0))
        br_ac_def = float(user_conf.get('BR_Acoes', 50.0))
        br_fii_def = float(user_conf.get('BR_FIIs', 50.0))
        ex_st_def = float(user_conf.get('EX_Stocks', 40.0))
        ex_re_def = float(user_conf.get('EX_REITs', 30.0))
        ex_et_def = float(user_conf.get('EX_ETFs', 30.0))
        
        # --- NÍVEL 1: MACRO ---
        st.subheader("Nível 1: Macro Alocação da Carteira")
        col1, col2 = st.columns(2)
        rf = col1.number_input("Renda Fixa (RF) %", min_value=0.0, max_value=100.0, value=rf_def, step=1.0)
        rv = col2.number_input("Renda Variável (RV) %", min_value=0.0, max_value=100.0, value=rv_def, step=1.0)
        
        soma_n1 = rf + rv
        n1_valido = (soma_n1 == 100.0)
        if not n1_valido:
            st.warning(f"⚠️ A soma de **RF + RV** é {soma_n1}%. Deve ser exatamente 100%.")
            
        # --- NÍVEL 2: RENDA VARIÁVEL ---
        st.markdown("---")
        st.subheader("Nível 2: Distribuição Geográfica (Dentro de Renda Variável)")
        col3, col4 = st.columns(2)
        rv_br = col3.number_input("Brasil %", min_value=0.0, max_value=100.0, value=rv_br_def, step=1.0)
        rv_ex = col4.number_input("Exterior %", min_value=0.0, max_value=100.0, value=rv_ex_def, step=1.0)
        
        soma_n2 = rv_br + rv_ex
        n2_valido = (soma_n2 == 100.0)
        if not n2_valido:
            st.warning(f"⚠️ A soma de **Brasil + Exterior** é {soma_n2}%. Deve ser exatamente 100%.")
            
        # --- NÍVEL 3: SUBCLASSES ---
        st.markdown("---")
        col_bloco1, col_bloco2 = st.columns(2)
        
        with col_bloco1:
            st.subheader("Nível 3A: Detalhe Brasil")
            br_ac = st.number_input("Ações %", min_value=0.0, max_value=100.0, value=br_ac_def, step=1.0)
            br_fii = st.number_input("FIIs %", min_value=0.0, max_value=100.0, value=br_fii_def, step=1.0)
            
            soma_n3_br = br_ac + br_fii
            n3_br_valido = (soma_n3_br == 100.0)
            if not n3_br_valido:
                st.warning(f"⚠️ A soma de **Ações + FIIs** é {soma_n3_br}%. Deve ser exatamente 100%.")
                
        with col_bloco2:
            st.subheader("Nível 3B: Detalhe Exterior")
            ex_st = st.number_input("Stocks %", min_value=0.0, max_value=100.0, value=ex_st_def, step=1.0)
            ex_re = st.number_input("REITs %", min_value=0.0, max_value=100.0, value=ex_re_def, step=1.0)
            ex_et = st.number_input("ETFs %", min_value=0.0, max_value=100.0, value=ex_et_def, step=1.0)
            
            soma_n3_ex = ex_st + ex_re + ex_et
            n3_ex_valido = (soma_n3_ex == 100.0)
            if not n3_ex_valido:
                st.warning(f"⚠️ A soma de **Stocks + REITs + ETFs** é {soma_n3_ex}%. Deve ser exatamente 100%.")
                
        # --- MOTOR DE VALIDAÇÃO E ENVIO ---
        st.markdown("---")
        telas_validas = n1_valido and n2_valido and n3_br_valido and n3_ex_valido
        
        if telas_validas:
            st.success("✅ Todas as árvores de distribuição estão consistentes e somam 100%!")
        else:
            st.error("❌ A gravação está bloqueada. Por favor, ajuste os percentuais para que as somas de cada seção totalizem 100%.")
            
        # O botão fica desativado nativamente pelo Streamlit caso a soma falhe
        if st.button("Salvar Configuração da Carteira", disabled=not telas_validas):
            dados_para_salvar = {
                'RF': rf, 'RV': rv, 'RV_Brasil': rv_br, 'RV_Exterior': rv_ex,
                'BR_Acoes': br_ac, 'BR_FIIs': br_fii, 'EX_Stocks': ex_st, 'EX_REITs': ex_re, 'EX_ETFs': ex_et
            }
            if salvar_configuracao(st.session_state.email, dados_para_salvar):
                st.success("Configurações persistidas com sucesso na planilha Google!")
                st.rerun()
