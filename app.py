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
        # Se a aba Ativos_Config não existir ainda, retorna vazio sem travar
        if aba_nome == "Ativos_Config":
            return pd.DataFrame(columns=['Email', 'Categoria', 'Ativo', 'Peso'])
        st.error(f"Erro de conexão ao ler aba '{aba_nome}': {e}")
        return pd.DataFrame()

# Função para Salvar ou Atualizar as configurações macro
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
        
        if not df.empty and email in df['Email'].astype(str).str.strip().str.lower().values:
            idx = df[df['Email'].astype(str).str.strip().str.lower() == email].index[0]
            row_num = idx + 2
            sheet.update(f"A{row_num}:J{row_num}", [row_values])
        else:
            sheet.append_row(row_values)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar na planilha: {e}")
        return False

# Função para Salvar os ativos de uma categoria específica (Corrigida)
def salvar_ativos_categoria(email, categoria, df_ativos):
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = json.loads(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        
        # Tenta abrir ou criar a aba Ativos_Config se não existir
        try:
            sheet = client.open("App_Investimentos").worksheet("Ativos_Config")
        except:
            sheet = client.open("App_Investimentos").add_worksheet(title="Ativos_Config", rows=100, cols=4)
            sheet.append_row(["Email", "Categoria", "Ativo", "Peso"])
            
        df_all = pd.DataFrame(sheet.get_all_records())
        
        # Remove registros anteriores deste usuário e categoria para substituir pelos novos
        if not df_all.empty and 'Email' in df_all.columns:
            df_all['Email'] = df_all['Email'].astype(str).str.strip().str.lower()
            df_all['Categoria'] = df_all['Categoria'].astype(str).str.strip()
            df_filtered = df_all[~((df_all['Email'] == email) & (df_all['Categoria'] == categoria))]
        else:
            df_filtered = pd.DataFrame(columns=["Email", "Categoria", "Ativo", "Peso"])
            
        # Adiciona as novas linhas da tabela editada
        novas_linhas = []
        for _, row in df_ativos.iterrows():
            ativo = str(row.get('Ativo', '')).strip().upper()
            
            # Identifica dinamicamente se a coluna se chama 'Peso' ou 'Peso (%)'
            col_peso = 'Peso' if 'Peso' in df_ativos.columns else 'Peso (%)'
            val_peso = row.get(col_peso, 0)
            peso = float(val_peso) if pd.notna(val_peso) and str(val_peso).strip() != '' else 0.0
            
            if ativo and ativo != "NAN":
                novas_linhas.append([email, categoria, ativo, peso])
                
        # Reconstrói a planilha inteira no Sheets
        dados_finais = [["Email", "Categoria", "Ativo", "Peso"]]
        if not df_filtered.empty:
            for _, r in df_filtered.iterrows():
                dados_finais.append([r['Email'], r['Categoria'], r['Ativo'], r['Peso']])
        for nl in novas_linhas:
            dados_finais.append(nl)
            
        sheet.clear()
        sheet.update("A1", dados_finais)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar ativos: {e}")
        return False

# Controle de estado do Login
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
    st.sidebar.markdown("---")
    
    menu_selecionado = st.sidebar.radio(
        "Navegação / Painéis:",
        ["💼 Resumo da Aplicação", "📈 Evolução do Saldo", "🎯 Guia de Aportes", "⚙️ Configuração da Carteira"]
    )
    
    st.sidebar.markdown("---")
    if st.sidebar.button("Sair do App"):
        st.session_state.logado = False
        st.session_state.pop('config_inicializada', None)
        st.rerun()

    # --- TELA 1: RESUMO DA APLICAÇÃO ---
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
                col_c1.metric("Total Investido", f"R$ {total_carteira_investido:,.2f}")
                col_c2.metric("Valor Atual", f"R$ {total_carteira_atual:,.2f}")
                col_c3.metric("Evolução", f"{evolucao_total_carteira:+.2f}%")
                
                st.markdown("---")
                
                st.subheader("Distribuição por Categoria")
                df_categoria = carteira_agrupada.groupby('Categoria')['TotalAtual'].sum().reset_index()
                fig = px.pie(df_categoria, values='TotalAtual', names='Categoria', hole=0.4)
                fig.update_traces(textinfo='label+percent')
                st.plotly_chart(fig, use_container_width=True)
                
                st.markdown("---")
                st.subheader("Detalhamento por Ativos")
                for cat in carteira_agrupada['Categoria'].unique():
                    with st.expander(f"📁 {cat}", expanded=True):
                        df_exibicao = carteira_agrupada[carteira_agrupada['Categoria'] == cat][['Ativo', 'Quantidade', 'PrecoMedio', 'PrecoAtual', 'TotalAtual', 'EvolucaoPct']].copy()
                        df_exibicao['PrecoMedio'] = df_exibicao['PrecoMedio'].map('R$ {:,.2f}'.format)
                        df_exibicao['PrecoAtual'] = df_exibicao['PrecoAtual'].map('R$ {:,.2f}'.format)
                        df_exibicao['TotalAtual'] = df_exibicao['TotalAtual'].map('R$ {:,.2f}'.format)
                        df_exibicao['EvolucaoPct'] = df_exibicao['EvolucaoPct'].map('{:+.2f}%'.format)
                        st.dataframe(df_exibicao, use_container_width=True)
            else:
                st.info("Nenhum investimento encontrado.")
        else:
            st.error("Erro ao ler aba 'Investimentos'.")

    # --- TELA 2: EVOLUÇÃO DO SALDO ---
    elif menu_selecionado == "📈 Evolução do Saldo":
        st.title("📈 Histórico de Saldo")
        df_saldo = ler_planilha("Saldo")
        if not df_saldo.empty:
            df_saldo['Email'] = df_saldo['Email'].astype(str).str.strip().str.lower()
            dados = df_saldo[df_saldo['Email'] == st.session_state.email]
            if not dados.empty:
                st.line_chart(dados.set_index('Data')['Valor'])
            else:
                st.info("Sem histórico.")

    # --- TELA 3: GUIA DE APORTES ---
    elif menu_selecionado == "🎯 Guia de Aportes":
        st.title("🎯 Guia de Aportes")
        st.info("Em breve: Esta tela irá calcular onde aportar baseado na Configuração da Carteira e dos Ativos!")

    # --- TELA 4: CONFIGURAÇÃO DA CARTEIRA ---
    elif menu_selecionado == "⚙️ Configuração da Carteira":
        st.title("⚙️ Central de Configuração da Carteira")
        
        # Abas principais da página de Configuração
        aba_metas, aba_ativos = st.tabs(["🎯 Metas de Alocação", "📋 Ativos e Pesos por Categoria"])

        # ==========================================
        # ABA 1: METAS DE ALOCAÇÃO (O que já tínhamos)
        # ==========================================
        with aba_metas:
            st.markdown("Ajuste seus percentuais macro. O sistema compensa automaticamente para a soma sempre cravar **100%**.")

            if 'config_inicializada' not in st.session_state:
                df_conf = ler_planilha("Configuracao")
                user_conf = {}
                if not df_conf.empty:
                    df_conf['Email'] = df_conf['Email'].astype(str).str.strip().str.lower()
                    row = df_conf[df_conf['Email'] == st.session_state.email]
                    if not row.empty:
                        user_conf = row.iloc[0].to_dict()
                
                st.session_state.rf_val = float(user_conf.get('RF', 50.0))
                st.session_state.rv_val = float(user_conf.get('RV', 50.0))
                st.session_state.rv_br_val = float(user_conf.get('RV_Brasil', 50.0))
                st.session_state.rv_ex_val = float(user_conf.get('RV_Exterior', 50.0))
                st.session_state.br_ac_val = float(user_conf.get('BR_Acoes', 50.0))
                st.session_state.br_fii_val = float(user_conf.get('BR_FIIs', 50.0))
                st.session_state.ex_st_val = float(user_conf.get('EX_Stocks', 40.0))
                st.session_state.ex_re_val = float(user_conf.get('EX_REITs', 30.0))
                st.session_state.ex_et_val = float(user_conf.get('EX_ETFs', 30.0))
                st.session_state.config_inicializada = True

            def ajusta_macro(modificado):
                if modificado == 'rf': st.session_state.rv_val = round(100.0 - st.session_state.rf_val, 2)
                else: st.session_state.rf_val = round(100.0 - st.session_state.rv_val, 2)

            def ajusta_rv(modificado):
                if modificado == 'br': st.session_state.rv_ex_val = round(100.0 - st.session_state.rv_br_val, 2)
                else: st.session_state.rv_br_val = round(100.0 - st.session_state.rv_ex_val, 2)

            def ajusta_br(modificado):
                if modificado == 'ac': st.session_state.br_fii_val = round(100.0 - st.session_state.br_ac_val, 2)
                else: st.session_state.br_ac_val = round(100.0 - st.session_state.br_fii_val, 2)

            def ajusta_ex(modificado):
                if modificado == 'st':
                    novo_et = round(100.0 - st.session_state.ex_st_val - st.session_state.ex_re_val, 2)
                    if novo_et < 0:
                        st.session_state.ex_et_val = 0.0
                        st.session_state.ex_re_val = round(100.0 - st.session_state.ex_st_val, 2)
                    else: st.session_state.ex_et_val = novo_et
                elif modificado == 're':
                    novo_et = round(100.0 - st.session_state.ex_st_val - st.session_state.ex_re_val, 2)
                    if novo_et < 0:
                        st.session_state.ex_et_val = 0.0
                        st.session_state.ex_st_val = round(100.0 - st.session_state.ex_re_val, 2)
                    else: st.session_state.ex_et_val = novo_et
                elif modificado == 'et':
                    novo_st = round(100.0 - st.session_state.ex_et_val - st.session_state.ex_re_val, 2)
                    if novo_st < 0:
                        st.session_state.ex_st_val = 0.0
                        st.session_state.ex_re_val = round(100.0 - st.session_state.ex_et_val, 2)
                    else: st.session_state.ex_st_val = novo_st

            col_esquerda, col_direita = st.columns([2, 1], gap="large")

            with col_esquerda:
                st.subheader("Nível 1: Macro Alocação")
                c1, c2 = st.columns(2)
                c1.number_input("Renda Fixa (RF) %", min_value=0.0, max_value=100.0, step=1.0, key="rf_val", on_change=ajusta_macro, args=('rf',))
                c2.number_input("Renda Variável (RV) %", min_value=0.0, max_value=100.0, step=1.0, key="rv_val", on_change=ajusta_macro, args=('rv',))
                
                st.markdown("---")
                st.subheader("Nível 2: Renda Variável")
                c3, c4 = st.columns(2)
                c3.number_input("Brasil %", min_value=0.0, max_value=100.0, step=1.0, key="rv_br_val", on_change=ajusta_rv, args=('br',))
                c4.number_input("Exterior %", min_value=0.0, max_value=100.0, step=1.0, key="rv_ex_val", on_change=ajusta_rv, args=('ex',))
                
                st.markdown("---")
                c_b1, c_b2 = st.columns(2)
                with c_b1:
                    st.subheader("Nível 3A: Brasil")
                    st.number_input("Ações %", min_value=0.0, max_value=100.0, step=1.0, key="br_ac_val", on_change=ajusta_br, args=('ac',))
                    st.number_input("FIIs %", min_value=0.0, max_value=100.0, step=1.0, key="br_fii_val", on_change=ajusta_br, args=('fii',))
                        
                with c_b2:
                    st.subheader("Nível 3B: Exterior")
                    st.number_input("Stocks %", min_value=0.0, max_value=100.0, step=1.0, key="ex_st_val", on_change=ajusta_ex, args=('st',))
                    st.number_input("REITs %", min_value=0.0, max_value=100.0, step=1.0, key="ex_re_val", on_change=ajusta_ex, args=('re',))
                    st.number_input("ETFs %", min_value=0.0, max_value=100.0, step=1.0, key="ex_et_val", on_change=ajusta_ex, args=('et',))

                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Salvar Configuração Macro", use_container_width=True):
                    dados_para_salvar = {
                        'RF': st.session_state.rf_val, 'RV': st.session_state.rv_val, 
                        'RV_Brasil': st.session_state.rv_br_val, 'RV_Exterior': st.session_state.rv_ex_val,
                        'BR_Acoes': st.session_state.br_ac_val, 'BR_FIIs': st.session_state.br_fii_val, 
                        'EX_Stocks': st.session_state.ex_st_val, 'EX_REITs': st.session_state.ex_re_val, 'EX_ETFs': st.session_state.ex_et_val
                    }
                    if salvar_configuracao(st.session_state.email, dados_para_salvar):
                        st.success("✅ Metas atualizadas e persistidas com sucesso!")

            with col_direita:
                st.subheader("🎯 Resumo do Objetivo")
                st.markdown("Distribuição real sobre o **patrimônio total**:")
                
                rf_final = st.session_state.rf_val
                peso_rv = st.session_state.rv_val / 100.0
                peso_br = st.session_state.rv_br_val / 100.0
                peso_ex = st.session_state.rv_ex_val / 100.0
                
                acoes_final = peso_rv * peso_br * st.session_state.br_ac_val
                fiis_final  = peso_rv * peso_br * st.session_state.br_fii_val
                stocks_final = peso_rv * peso_ex * st.session_state.ex_st_val
                reits_final  = peso_rv * peso_ex * st.session_state.ex_re_val
                etfs_final   = peso_rv * peso_ex * st.session_state.ex_et_val
                
                df_resumo = pd.DataFrame({
                    "Categoria": ["Renda Fixa", "Ações", "FIIs", "Stocks", "REITs", "ETFs"],
                    "% Alvo Final": [rf_final, acoes_final, fiis_final, stocks_final, reits_final, etfs_final]
                })
                
                df_resumo_grafico = df_resumo[df_resumo["% Alvo Final"] > 0]
                df_resumo['% Alvo Final'] = df_resumo['% Alvo Final'].map('{:.2f}%'.format)
                
                st.dataframe(df_resumo, use_container_width=True, hide_index=True)
                
                fig_resumo = px.pie(
                    df_resumo_grafico, 
                    values='% Alvo Final', 
                    names="Categoria", 
                    hole=0.5
                )
                fig_resumo.update_traces(textinfo='label+percent')
                fig_resumo.update_layout(margin=dict(t=0, b=0, l=0, r=0), showlegend=False)
                st.plotly_chart(fig_resumo, use_container_width=True)

        # ==========================================
        # ABA 2: ATIVOS E PESOS POR CATEGORIA
        # ==========================================
        with aba_ativos:
            st.subheader("📋 Composição de Ativos por Categoria")
            st.markdown("Adicione os ativos (tickers) e defina a porcentagem interna de cada um. **A soma de cada categoria deve fechar exatamente 100%.**")

            # Categorias disponíveis para sub-distribuição
            categorias_lista = ["Ações", "FIIs", "Stocks", "REITs", "ETFs", "Renda Fixa"]
            cat_tabs = st.tabs(categorias_lista)

            # Lê os ativos já cadastrados do usuário na planilha
            df_ativos_existentes = ler_planilha("Ativos_Config")
            if not df_ativos_existentes.empty and 'Email' in df_ativos_existentes.columns:
                df_ativos_existentes['Email'] = df_ativos_existentes['Email'].astype(str).str.strip().str.lower()
                df_ativos_existentes['Categoria'] = df_ativos_existentes['Categoria'].astype(str).str.strip()
                df_ativos_user = df_ativos_existentes[df_ativos_existentes['Email'] == st.session_state.email]
            else:
                df_ativos_user = pd.DataFrame(columns=['Email', 'Categoria', 'Ativo', 'Peso'])

            for i, cat_nome in enumerate(categorias_lista):
                with cat_tabs[i]:
                    st.markdown(f"### Ativos da Categoria: **{cat_nome}**")
                    
                    # Filtra os dados salvos para esta categoria específica
                    df_cat_salvo = df_ativos_user[df_ativos_user['Categoria'] == cat_nome][['Ativo', 'Peso']].copy()
                    
                    if df_cat_salvo.empty:
                        # Tabela inicial vazia para o usuário preencher
                        df_inicial = pd.DataFrame({"Ativo": [""], "Peso (%)": [100.0]})
                    else:
                        df_cat_salvo.rename(columns={'Peso': 'Peso (%)'}, inplace=True)
                        df_inicial = df_cat_salvo

                    # Editor de dados interativo (tipo Excel)
                    df_editado = st.data_editor(
                        df_inicial,
                        num_rows="dynamic",
                        use_container_width=True,
                        key=f"editor_cat_{i}"
                    )

                    # Cálculo em tempo real da soma dos pesos
                    soma_pesos = pd.to_numeric(df_editado['Peso (%)'], errors='coerce').sum()
                    
                    col_info, col_btn = st.columns([2, 1])
                    with col_info:
                        if abs(soma_pesos - 100.0) < 0.01:
                            st.success(f"✅ Soma total: **{soma_pesos:.2f}%** (Perfeito!)")
                        else:
                            st.warning(f"⚠️ Soma total: **{soma_pesos:.2f}%** (Atenção: o ideal é que feche exatamente 100%).")
                    
                    with col_btn:
                        if st.button(f"Salvar {cat_nome}", key=f"btn_save_{i}", use_container_width=True):
                            # Prepara dataframe para salvar
                            df_para_salvar = df_editado.copy()
                            df_para_salvar.rename(columns={'Peso (%)': 'Peso'}, inplace=True)
                            if salvar_ativos_categoria(st.session_state.email, cat_nome, df_para_salvar):
                                st.success(f"Ativos de {cat_nome} salvos!")
                                st.rerun()
