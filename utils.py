import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def extrair_numero_br(valor):
    """Converte strings de planilhas para float lidando com formatos BR e US automaticamente"""
    if pd.isna(valor) or valor == '' or valor is None:
        return 0.0
    
    if isinstance(valor, (int, float)):
        return float(valor)
        
    # Limpa R$, símbolos e espaços em branco
    v = str(valor).upper().replace('R$', '').replace('%', '').strip()
    
    if not v:
        return 0.0
        
    # Se o número tem Ponto e Vírgula (ex: 1.250,50 ou 1,250.50)
    if '.' in v and ',' in v:
        if v.rfind(',') > v.rfind('.'):
            # Formato Brasileiro (1.250,50) -> Remove ponto, troca vírgula por ponto
            v = v.replace('.', '').replace(',', '.')
        else:
            # Formato Americano (1,250.50) -> Remove vírgula
            v = v.replace(',', '')
            
    # Se só tem Vírgula (ex: 295,17) -> Assume que é decimal brasileiro
    elif ',' in v:
        v = v.replace(',', '.')
        
    try:
        return float(v)
    except ValueError:
        return 0.0

def formata_br(valor):
    """Gera visualização de dinheiro no padrão BR"""
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

# ==========================================
# MÁGICA DO CACHE: Salva na RAM por 5 minutos
# ==========================================
@st.cache_data(ttl=300, show_spinner=False)
def ler_planilha(aba_nome):
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = json.loads(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open("App_Investimentos").worksheet(aba_nome)
        
        # Lê o texto exato para evitar que a biblioteca americana engula nossas vírgulas
        valores = sheet.get_all_values()
        if not valores:
            return pd.DataFrame()
        
        # Constrói a tabela
        df = pd.DataFrame(valores[1:], columns=valores[0])
        
        # Força a conversão BR apenas nas colunas que sabemos que são números
        colunas_numericas = [
            'Quantidade', 'PrecoMedio', 'PrecoAtual', 'Valor', 'Peso', 'Peso (%)',
            'RF', 'RV', 'RV_Brasil', 'RV_Exterior', 
            'BR_Acoes', 'BR_FIIs', 'EX_Stocks', 'EX_REITs', 'EX_ETFs'
        ]
        
        for col in df.columns:
            if col in colunas_numericas:
                df[col] = df[col].apply(extrair_numero_br)
                
        return df
    except Exception as e:
        if aba_nome == "Ativos_Config":
            return pd.DataFrame(columns=['Email', 'Categoria', 'Ativo', 'Peso'])
        st.error(f"Erro de conexão ao ler aba '{aba_nome}': {e}")
        return pd.DataFrame()

def salvar_configuracao(email, dados_dict):
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = json.loads(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open("App_Investimentos").worksheet("Configuracao")
        
        valores = sheet.get_all_values()
        df = pd.DataFrame(valores[1:], columns=valores[0]) if len(valores) > 1 else pd.DataFrame(columns=["Email"])
        
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
            
        st.cache_data.clear() # Limpa a memória após escrever
        return True
    except Exception as e:
        st.error(f"Erro ao salvar na planilha: {e}")
        return False

def salvar_ativos_categoria(email, categoria, df_ativos):
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = json.loads(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        
        try:
            sheet = client.open("App_Investimentos").worksheet("Ativos_Config")
        except:
            sheet = client.open("App_Investimentos").add_worksheet(title="Ativos_Config", rows=100, cols=4)
            sheet.append_row(["Email", "Categoria", "Ativo", "Peso"])
            
        valores = sheet.get_all_values()
        if valores:
            df_all = pd.DataFrame(valores[1:], columns=valores[0])
        else:
            df_all = pd.DataFrame(columns=["Email", "Categoria", "Ativo", "Peso"])
        
        if not df_all.empty and 'Email' in df_all.columns:
            df_all['Email'] = df_all['Email'].astype(str).str.strip().str.lower()
            df_all['Categoria'] = df_all['Categoria'].astype(str).str.strip()
            df_filtered = df_all[~((df_all['Email'] == email) & (df_all['Categoria'] == categoria))]
        else:
            df_filtered = pd.DataFrame(columns=["Email", "Categoria", "Ativo", "Peso"])
            
        novas_linhas = []
        for _, row in df_ativos.iterrows():
            ativo = str(row.get('Ativo', '')).strip().upper()
            col_peso = 'Peso' if 'Peso' in df_ativos.columns else 'Peso (%)'
            val_peso = row.get(col_peso, 0)
            peso = float(val_peso) if pd.notna(val_peso) and str(val_peso).strip() != '' else 0.0
            
            if ativo and ativo != "NAN":
                novas_linhas.append([email, categoria, ativo, peso])
                
        dados_finais = [["Email", "Categoria", "Ativo", "Peso"]]
        if not df_filtered.empty:
            for _, r in df_filtered.iterrows():
                dados_finais.append([r['Email'], r['Categoria'], r['Ativo'], r['Peso']])
        for nl in novas_linhas:
            dados_finais.append(nl)
            
        sheet.clear()
        sheet.update("A1", dados_finais)
        
        st.cache_data.clear() # Limpa a memória após escrever
        return True
    except Exception as e:
        st.error(f"Erro ao salvar ativos: {e}")
        return False

# ==========================================
# COTAÇÕES EM TEMPO REAL (YFINANCE + TESOURO)
# ==========================================
@st.cache_data(ttl=300, show_spinner=False)
def obter_cotacoes():
    """
    Busca os preços em tempo real usando Python, ignorando as fórmulas do Google Sheets.
    Usa 'requests' para Tesouro Direto e 'yfinance' para Ações/FIIs/Stocks.
    """
    import yfinance as yf
    import requests
    import streamlit as st
    import pandas as pd
    import re

    cotacoes = {}
    ativos_buscados = set()
    
    try:
        # --- 1. DESCOBRIR QUAIS ATIVOS O USUÁRIO TEM ---
        if 'email' in st.session_state:
            email_usuario = st.session_state.email.strip().lower()
            
            # Lê os ativos já comprados
            df_invest = ler_planilha("Investimentos")
            if not df_invest.empty and 'Email' in df_invest.columns:
                meus_invest = df_invest[df_invest['Email'].astype(str).str.strip().str.lower() == email_usuario]
                for _, row in meus_invest.iterrows():
                    ativo = str(row.get('Ativo', '')).strip().upper()
                    if ativo and ativo not in ["NAN", "NONE", ""]:
                        ativos_buscados.add(ativo)
                        
                        # Trava de Segurança: Pré-carrega o custo médio para o dinheiro não sumir se a API falhar
                        preco_custo = 0.0
                        if 'PrecoMedio' in row and pd.notnull(row['PrecoMedio']):
                            preco_custo = extrair_numero_br(row['PrecoMedio'])
                        elif 'Preco' in row and pd.notnull(row['Preco']):
                            preco_custo = extrair_numero_br(row['Preco'])
                        if preco_custo > 0 and ativo not in cotacoes:
                            cotacoes[ativo] = preco_custo

            # Lê os ativos que o usuário cadastrou nas metas (mesmo se ainda não comprou)
            df_config = ler_planilha("Ativos_Config")
            if not df_config.empty and 'Email' in df_config.columns:
                meus_configs = df_config[df_config['Email'].astype(str).str.strip().str.lower() == email_usuario]
                for _, row in meus_configs.iterrows():
                    ativo = str(row.get('Ativo', '')).strip().upper()
                    if ativo and ativo not in ["NAN", "NONE", ""]:
                        ativos_buscados.add(ativo)

        if not ativos_buscados:
            return cotacoes

        # --- 2. BUSCAR TESOURO DIRETO (API) ---
        try:
            url_td = "https://tesouro.gabriso.com/bonds"
            headers = {"User-Agent": "Mozilla/5.0"}
            res_td = requests.get(url_td, headers=headers, timeout=10)
            
            if res_td.status_code == 200:
                data_td = res_td.json()
                palavras_permitidas = ["IPCA+", "SELIC", "PREFIXADO"]
                palavras_nao_permitidas = ["EDUCA", "APOSENTADORIA"]
                
                for bond in data_td.get("bonds", []):
                    nome = str(bond.get("name", "")).strip().upper()
                    valor = float(bond.get("unitary_redemption_value", 0.0))
                    
                    tem_permitida = any(p in nome for p in palavras_permitidas)
                    tem_proibida = any(p in nome for p in palavras_nao_permitidas)
                    
                    # Se o título bater com a regra OU se for um título que o usuário já possui na carteira
                    if (tem_permitida and not tem_proibida) or (nome in ativos_buscados):
                        if nome in ativos_buscados:
                            cotacoes[nome] = valor
                            ativos_buscados.remove(nome) # Tira da lista para não mandar pro Yahoo Finance
        except Exception as e:
            print(f"Aviso: Falha na API do Tesouro Direto: {e}")

        # --- 3. BUSCAR AÇÕES / FIIs / STOCKS NO YAHOO FINANCE ---
        if ativos_buscados:
            tickers_yf = []
            mapa_tickers = {}
            
            for ativo in ativos_buscados:
                ticker = ativo
                # Mágica de Reconhecimento: Se o ativo tem um número no final (ex: ITUB4, MXRF11) 
                # e não tem ponto na string, é um ativo brasileiro. Adicionamos o ".SA" nativo do Yahoo.
                if "." not in ticker and re.search(r'\d+$', ticker):
                    ticker = f"{ticker}.SA"
                
                tickers_yf.append(ticker)
                mapa_tickers[ticker] = ativo # Guarda a referência para devolver o nome limpo

            try:
                # Faz o download em lote de todos os preços de uma vez só (Super Rápido!)
                dados_yf = yf.download(tickers_yf, period="1d", progress=False)
                
                if not dados_yf.empty and 'Close' in dados_yf:
                    if len(tickers_yf) == 1:
                        # Quando é apenas 1 ticker, o DataFrame tem um formato simples
                        preco = float(dados_yf['Close'].iloc[-1])
                        if pd.notna(preco):
                            cotacoes[mapa_tickers[tickers_yf[0]]] = preco
                    else:
                        # Multi-tickers retorna colunas aninhadas
                        for ticker in tickers_yf:
                            try:
                                preco = float(dados_yf['Close'][ticker].iloc[-1])
                                if pd.notna(preco):
                                    cotacoes[mapa_tickers[ticker]] = preco
                            except:
                                pass
            except Exception as e:
                print(f"Aviso: Falha no Yahoo Finance: {e}")

        return cotacoes
    except Exception as e:
        print(f"Erro geral ao ler cotações: {e}")
        return cotacoes

# ==========================================
# MÁGICA DO CACHE: Agrupamento também na RAM
# ==========================================
@st.cache_data(ttl=300, show_spinner=False)
def obter_ativos_por_categoria():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = json.loads(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open("App_Investimentos").worksheet("Cotacao")
        
        valores = sheet.get_all_values()
        cat_dict = {}
        
        if len(valores) > 1:
            cabecalhos = valores[0]
            mapa_colunas = {}
            
            for i, col in enumerate(cabecalhos):
                c = str(col).strip().upper()
                if c in ["AÇÕES", "ACOES", "AÇÃO", "ACAO"]: mapa_colunas[i] = "Ações"
                elif c in ["FIIS", "FII"]: mapa_colunas[i] = "FIIs"
                elif c in ["IPCA", "RENDA FIXA", "RF"]: mapa_colunas[i] = "Renda Fixa"
                elif c in ["STOCKS", "STOCK"]: mapa_colunas[i] = "Stocks"
                elif c in ["REITS", "REIT"]: mapa_colunas[i] = "REITs"
                elif c in ["ETFS", "ETF"]: mapa_colunas[i] = "ETFs"
            
            for cat in mapa_colunas.values():
                cat_dict[cat] = []
                
            for linha in valores[1:]:
                for idx, cat in mapa_colunas.items():
                    if len(linha) > idx:
                        ativo = str(linha[idx]).strip().upper()
                        if ativo and ativo != "NAN" and ativo not in cat_dict[cat]:
                            cat_dict[cat].append(ativo)
                            
            for cat in cat_dict:
                cat_dict[cat].sort()
                
        return cat_dict
    except Exception as e:
        return {}

def registrar_deposito(email, data, valor):
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = json.loads(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        
        try:
            sheet = client.open("App_Investimentos").worksheet("Depositos")
        except:
            sheet = client.open("App_Investimentos").add_worksheet(title="Depositos", rows=100, cols=3)
            sheet.append_row(["Email", "Data", "Valor"])
            
        valor_str = f"{valor:.2f}".replace('.', ',')
        sheet.append_row([email, data, valor_str])
        
        st.cache_data.clear() # Limpa a memória após escrever
        return True
    except Exception as e:
        st.error(f"Erro ao salvar depósito: {e}")
        return False

def registrar_compra(email, data, categoria, ativo, quantidade, preco_medio):
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = json.loads(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open("App_Investimentos").worksheet("Investimentos")
        
        qtd_str = f"{quantidade:.4f}".replace('.', ',').rstrip('0').rstrip(',')
        preco_str = f"{preco_medio:.4f}".replace('.', ',')
        
        sheet.append_row([email, data, categoria, ativo, qtd_str, preco_str, ""])
        
        st.cache_data.clear() # Limpa a memória após escrever
        return True
    except Exception as e:
        st.error(f"Erro ao salvar compra: {e}")
        return False

def conectar_planilha(aba):
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open("App_Investimentos").worksheet(aba)

def registrar_novo_usuario(nome, email, senha):
    try:
        sheet = conectar_planilha("Usuarios")
        valores = sheet.get_all_values()
        if not valores: return False, "A aba Usuarios está vazia."
        
        cabecalho = [str(c).strip().lower() for c in valores[0]]
        if 'email' not in cabecalho: return False, "Coluna 'Email' não encontrada na planilha."
        
        idx_email = cabecalho.index('email')
        email_lower = email.strip().lower()
        
        if len(valores) > 1:
            for linha in valores[1:]:
                if len(linha) > idx_email and str(linha[idx_email]).strip().lower() == email_lower:
                    return False, "⚠️ Este e-mail já está cadastrado. Caso não se recorde da senha, vá na aba 'Esqueci a Senha' para recuperá-la."
                    
        nova_linha = [""] * len(cabecalho)
        
        if 'nome' in cabecalho: nova_linha[cabecalho.index('nome')] = nome.strip()
        if 'email' in cabecalho: nova_linha[cabecalho.index('email')] = email_lower
        if 'senha' in cabecalho: nova_linha[cabecalho.index('senha')] = senha
        if 'status' in cabecalho: nova_linha[cabecalho.index('status')] = "Pendente"
        
        sheet.append_row(nova_linha)
        
        st.cache_data.clear() # Limpa a memória após novo cadastro
        return True, "✅ Cadastro enviado com sucesso! Aguarde a liberação do administrador."
    except Exception as e:
        return False, f"Erro ao cadastrar: {e}"

def verificar_email_cadastrado(email):
    try:
        sheet = conectar_planilha("Usuarios")
        valores = sheet.get_all_values()
        if not valores: return False
        
        cabecalho = [str(c).strip().lower() for c in valores[0]]
        if 'email' not in cabecalho: return False
        
        idx_email = cabecalho.index('email')
        email_lower = email.strip().lower()
        
        for linha in valores[1:]:
            if len(linha) > idx_email and str(linha[idx_email]).strip().lower() == email_lower:
                return True
        return False
    except:
        return False

def enviar_codigo_email(email_destino, codigo):
    try:
        remetente = st.secrets["email"]["endereco"]
        senha_app = st.secrets["email"]["senha_app"]
        
        msg = MIMEMultipart()
        msg['From'] = remetente
        msg['To'] = email_destino
        msg['Subject'] = "🔒 Código de Recuperação de Senha - App Investimentos"
        
        corpo = f"Olá!\n\nVocê solicitou a recuperação de senha no seu App de Investimentos.\n\nSeu código de segurança é: {codigo}\n\nSe você não solicitou esta alteração, apenas ignore este e-mail."
        msg.attach(MIMEText(corpo, 'plain'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(remetente, senha_app)
        server.send_message(msg)
        server.quit()
        
        return True, "E-mail enviado com sucesso!"
    except Exception as e:
        return False, f"Erro ao enviar o e-mail. Verifique as configurações (secrets): {e}"

def redefinir_senha_aprovada(email, nova_senha):
    try:
        sheet = conectar_planilha("Usuarios")
        valores = sheet.get_all_values()
        if not valores: return False, "A aba Usuarios está vazia."
        
        cabecalho = [str(c).strip().lower() for c in valores[0]]
        idx_email = cabecalho.index('email')
        idx_senha = cabecalho.index('senha')
        email_lower = email.strip().lower()
        
        for i, linha in enumerate(valores[1:], start=2): 
            if len(linha) > max(idx_email, idx_senha):
                if str(linha[idx_email]).strip().lower() == email_lower:
                    sheet.update_cell(i, idx_senha + 1, nova_senha) 
                    st.cache_data.clear() # Limpa a memória após escrever
                    return True, "✅ Senha alterada com sucesso! Você já pode fazer login."
        return False, "Usuário não encontrado."
    except Exception as e:
        return False, f"Erro ao gravar nova senha: {e}"

def atualizar_dados_perfil(email, novo_nome, nova_senha):
    try:
        sheet = conectar_planilha("Usuarios")
        valores = sheet.get_all_values()
        if not valores: return False, "A aba Usuarios está vazia."
        
        cabecalho = [str(c).strip().lower() for c in valores[0]]
        idx_email = cabecalho.index('email')
        email_lower = email.strip().lower()
        
        for i, linha in enumerate(valores[1:], start=2):
            if len(linha) > idx_email and str(linha[idx_email]).strip().lower() == email_lower:
                if novo_nome and 'nome' in cabecalho:
                    sheet.update_cell(i, cabecalho.index('nome') + 1, novo_nome)
                if nova_senha and 'senha' in cabecalho:
                    sheet.update_cell(i, cabecalho.index('senha') + 1, nova_senha)
                
                st.cache_data.clear() # Limpa a memória após escrever
                return True, "✅ Perfil atualizado com sucesso!"
                
        return False, "Usuário não encontrado."
    except Exception as e:
        return False, f"Erro ao atualizar perfil: {e}"

def atualizar_historico_usuario(email, nome_aba, df_editado):
    import pandas as pd
    import streamlit as st
    try:
        df_full = ler_planilha(nome_aba)
        
        if not df_full.empty and 'Email' in df_full.columns:
            df_full['Email'] = df_full['Email'].astype(str).str.strip().str.lower()
            df_outros = df_full[df_full['Email'] != email].copy()
        else:
            df_outros = pd.DataFrame()
            
        df_novo_usuario = df_editado.copy()
        if not df_novo_usuario.empty:
            df_novo_usuario['Email'] = email
            
        df_final = pd.concat([df_outros, df_novo_usuario], ignore_index=True)
        
        cabecalho_original = df_full.columns.tolist() if not df_full.empty else df_final.columns.tolist()
        for col in cabecalho_original:
            if col not in df_final.columns:
                df_final[col] = ""
        df_final = df_final[cabecalho_original]
        
        from oauth2client.service_account import ServiceAccountCredentials
        import gspread
        
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        client = gspread.authorize(creds)
        
        planilha = client.open("App_Investimentos")
        aba = planilha.worksheet(nome_aba)
        
        aba.clear()
        dados_salvar = [df_final.columns.values.tolist()] + df_final.fillna("").values.tolist()
        aba.update(dados_salvar)
        
        st.cache_data.clear() # Limpa a memória após edição de massa
        return True
    except Exception as e:
        st.error(f"Erro ao salvar edição: {e}")
        return False

def deletar_registros_usuario(nome_aba, email):
    import streamlit as st
    from oauth2client.service_account import ServiceAccountCredentials
    import gspread
    import json

    try:
        NOME_PLANILHA = "App_Investimentos" 
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        chave_gcp = st.secrets["gcp_service_account"]
        if isinstance(chave_gcp, str):
            chave_dict = json.loads(chave_gcp)
        else:
            chave_dict = dict(chave_gcp)
            
        creds = ServiceAccountCredentials.from_json_keyfile_dict(chave_dict, scope)
        client = gspread.authorize(creds)
        
        aba = client.open(NOME_PLANILHA).worksheet(nome_aba)
        registros = aba.get_all_values()
        
        if not registros or len(registros) < 2:
            return True, "Nada a deletar."
            
        cabecalho = [str(c).strip() for c in registros[0]]
        if "Email" not in cabecalho:
            return False, f"Coluna 'Email' não encontrada na aba {nome_aba}."
            
        idx_email = cabecalho.index("Email")
        linhas_mantidas = [registros[0]] 
        teve_exclusao = False
        
        for linha in registros[1:]:
            if len(linha) > idx_email and linha[idx_email].strip().lower() == email.strip().lower():
                teve_exclusao = True
            else:
                linhas_mantidas.append(linha)
                
        if teve_exclusao:
            aba.clear() 
            if len(linhas_mantidas) > 0:
                aba.append_rows(linhas_mantidas, value_input_option='USER_ENTERED')
            
        st.cache_data.clear() # Limpa a memória após exclusão
        return True, "Sucesso"
    except Exception as e:
        return False, f"Erro ao apagar dados do Google Sheets: {str(e)}"

def inserir_lote_registros(nome_aba, df):
    import streamlit as st
    from oauth2client.service_account import ServiceAccountCredentials
    import gspread
    import json

    if df.empty:
        return True, "Planilha vazia, nada a inserir."

    try:
        NOME_PLANILHA = "App_Investimentos"
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        chave_gcp = st.secrets["gcp_service_account"]
        if isinstance(chave_gcp, str):
            chave_dict = json.loads(chave_gcp)
        else:
            chave_dict = dict(chave_gcp)
            
        creds = ServiceAccountCredentials.from_json_keyfile_dict(chave_dict, scope)
        client = gspread.authorize(creds)
        
        aba = client.open(NOME_PLANILHA).worksheet(nome_aba)
        
        df_limpo = df.astype(str).replace(["nan", "NaT", "None", "<NA>"], "")
        dados = df_limpo.values.tolist()
        
        aba.append_rows(dados, value_input_option='USER_ENTERED')
        
        st.cache_data.clear() # Limpa a memória após inserção em massa
        return True, "Sucesso"
    except Exception as e:
        return False, f"Erro ao salvar no Google Sheets: {str(e)}"
