import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import yfinance as yf
import re
import io

def extrair_numero_br(valor):
    """Converte strings de planilhas para float lidando com formatos BR e US automaticamente"""
    if pd.isna(valor) or valor == '' or valor is None:
        return 0.0
    
    if isinstance(valor, (int, float)):
        return float(valor)
        
    v = str(valor).upper().replace('R$', '').replace('%', '').strip()
    
    if not v:
        return 0.0
        
    if '.' in v and ',' in v:
        if v.rfind(',') > v.rfind('.'):
            v = v.replace('.', '').replace(',', '.')
        else:
            v = v.replace(',', '')
            
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
        
        valores = sheet.get_all_values()
        if not valores:
            return pd.DataFrame()
        
        df = pd.DataFrame(valores[1:], columns=valores[0])
        
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
            email, 
            float(dados_dict['RF']), float(dados_dict['RV']), 
            float(dados_dict['RV_Brasil']), float(dados_dict['RV_Exterior']), 
            float(dados_dict['BR_Acoes']), float(dados_dict['BR_FIIs']), 
            float(dados_dict['EX_Stocks']), float(dados_dict['EX_REITs']), float(dados_dict['EX_ETFs'])
        ]
        
        if not df.empty and email in df['Email'].astype(str).str.strip().str.lower().values:
            idx = df[df['Email'].astype(str).str.strip().str.lower() == email].index[0]
            row_num = idx + 2
            try:
                sheet.update(range_name=f"A{row_num}:J{row_num}", values=[row_values], value_input_option='USER_ENTERED')
            except TypeError:
                sheet.update(f"A{row_num}:J{row_num}", [row_values], value_input_option='USER_ENTERED')
        else:
            sheet.append_row(row_values, value_input_option='USER_ENTERED')
            
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar na planilha: {e}")
        return False

# ==========================================
# BUSCA AUTOMÁTICA DE SETORES
# ==========================================
@st.cache_data(ttl=86400, show_spinner=False)
def buscar_setor_yahoo(ativo, categoria):
    if categoria == "Renda Fixa": return "Renda Fixa"
    t_clean = str(ativo).upper().replace(".SA", "").strip()
    if categoria == "FIIs":
        fiis_papel = ["MXRF11", "KNCR11", "KNIP11", "CPTS11", "IRDM11", "RECR11", "VGIR11", "VRTA11", "HCTR11", "DEVA11", "VGHF11", "MCCI11", "CVBI11", "HGCR11", "KNSC11", "RBRR11", "URPR11", "HABT11", "VCJR11", "ARRI11", "RBRY11", "OUJP11", "CACR11", "NCHB11", "KNHY11", "SNCI11", "RZAK11", "BARI11"]
        fiis_logistica = ["HGLG11", "BTLG11", "XPLG11", "VILG11", "BRCO11", "LVBI11", "GGRC11", "HSLG11", "RBRL11", "SDIL11", "TRXF11", "GALG11", "GARE11", "HLG11", "FIIB11", "VTLG11", "PATL11"]
        fiis_shoppings = ["XPML11", "VISC11", "HSML11", "MALL11", "HGBS11", "WPLZ11", "GSFI11", "CPSH11", "MALS11"]
        fiis_lajes = ["HGRE11", "BRCR11", "PVBI11", "JSRE11", "VINO11", "RECT11", "TEPP11", "RCRB11", "RBED11", "CBOP11", "HOFC11", "VLOL11"]
        fiis_hibridos = ["KNRI11", "ALZR11", "TGAR11", "HGRU11", "KFOF11", "MAXR11", "TRXF11", "RBVA11", "MCHY11"]
        fiis_fof = ["BCFF11", "HFOF11", "KISU11", "RBRF11", "MGFF11", "CPFF11", "XPFN11", "HGFF11", "KFOF11", "BLMG11", "RZFO11"]
        fiis_agro = ["VGIA11", "RZAG11", "SNAG11", "KNCA11", "RURA11", "EGAF11", "FGAA11", "GCRA11", "VCRA11", "XPCA11", "DCRA11", "AGRX11"]
        if t_clean in fiis_papel: return "Papel (TVM)"
        if t_clean in fiis_logistica: return "Logística"
        if t_clean in fiis_shoppings: return "Shoppings"
        if t_clean in fiis_lajes: return "Lajes Corporativas"
        if t_clean in fiis_hibridos: return "Híbrido"
        if t_clean in fiis_fof: return "Fundo de Fundos (FOF)"
        if t_clean in fiis_agro: return "Fiagro"

    ticker = ativo
    if categoria in ["Ações", "FIIs"] and "." not in ticker and re.search(r'\d+$', ticker): ticker = f"{ticker}.SA"
    try:
        info = yf.Ticker(ticker).info
        setor = info.get('sector', '')
        if not setor or str(setor).lower() in ['none', 'nan', '']: setor = info.get('industry', 'Não Classificado')
        traducao = {
            "Financial Services": "Financeiro", "Utilities": "Utilidade Pública",
            "Basic Materials": "Materiais Básicos", "Industrials": "Industrial",
            "Consumer Defensive": "Consumo Não-Cíclico", "Consumer Cyclical": "Consumo Cíclico",
            "Healthcare": "Saúde", "Technology": "Tecnologia", "Communication Services": "Comunicações",
            "Energy": "Energia", "Real Estate": "Imobiliário"
        }
        return traducao.get(setor, setor if setor else "Não Classificado")
    except: return "Não Classificado"

def salvar_ativos_categoria(email, categoria, df_ativos):
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = json.loads(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        
        try:
            sheet = client.open("App_Investimentos").worksheet("Ativos_Config")
        except:
            sheet = client.open("App_Investimentos").add_worksheet(title="Ativos_Config", rows=100, cols=5)
            sheet.append_row(["Email", "Categoria", "Ativo", "Peso", "Setor"])
            
        valores = sheet.get_all_values()
        if valores:
            df_all = pd.DataFrame(valores[1:], columns=valores[0])
        else:
            df_all = pd.DataFrame(columns=["Email", "Categoria", "Ativo", "Peso", "Setor"])
            
        if 'Setor' not in df_all.columns:
            df_all['Setor'] = ""
        
        if not df_all.empty and 'Email' in df_all.columns:
            df_all['Email'] = df_all['Email'].astype(str).str.strip().str.lower()
            df_all['Categoria'] = df_all['Categoria'].astype(str).str.strip()
            df_filtered = df_all[~((df_all['Email'] == email) & (df_all['Categoria'] == categoria))]
        else:
            df_filtered = pd.DataFrame(columns=["Email", "Categoria", "Ativo", "Peso", "Setor"])
            
        novas_linhas = []
        for _, row in df_ativos.iterrows():
            ativo = str(row.get('Ativo', '')).strip().upper()
            col_peso = 'Peso' if 'Peso' in df_ativos.columns else 'Peso (%)'
            val_peso = row.get(col_peso, 0)
            peso = float(val_peso) if pd.notna(val_peso) and str(val_peso).strip() != '' else 0.0
            
            setor = str(row.get('Setor', '')).strip()
            if not setor or setor.lower() in ['nan', 'none', 'não classificado', 'nao classificado']:
                setor = buscar_setor_yahoo(ativo, categoria)
            
            if ativo and ativo != "NAN":
                novas_linhas.append([email, categoria, ativo, float(peso), setor])
                
        dados_finais = [["Email", "Categoria", "Ativo", "Peso", "Setor"]]
        
        if not df_filtered.empty:
            for _, r in df_filtered.iterrows():
                setor_r = str(r.get('Setor', '')).strip()
                if not setor_r or setor_r.lower() in ['nan', 'none']: setor_r = "Não Classificado"
                
                peso_str = str(r.get('Peso', '0')).replace(',', '.')
                try:
                    peso_real = float(peso_str)
                except:
                    peso_real = 0.0
                
                dados_finais.append([r['Email'], r['Categoria'], r['Ativo'], peso_real, setor_r])
                
        for nl in novas_linhas:
            dados_finais.append(nl)
            
        sheet.clear()
        
        try:
            sheet.update(range_name="A1", values=dados_finais, value_input_option="USER_ENTERED")
        except TypeError:
            sheet.update("A1", dados_finais, value_input_option="USER_ENTERED")
        
        st.cache_data.clear() 
        return True
    except Exception as e:
        st.error(f"Erro ao salvar ativos: {e}")
        return False

# ==========================================
# COTAÇÕES EM TEMPO REAL (NOVO MOTOR V3)
# ==========================================
@st.cache_data(ttl=300, show_spinner=False)
def obter_cotacoes(email_usuario=None):
    """
    Busca os preços em tempo real usando Python (Últimos 5 dias para fugir de FDS/Feriados).
    """
    cotacoes, ativos_buscados = {}, set()
    try:
        # Define o e-mail: Se não for passado na função, pega do session_state
        if email_usuario is None and 'email' in st.session_state:
            email_usuario = st.session_state.email.strip().lower()
        elif email_usuario:
            email_usuario = email_usuario.strip().lower()
            
        if not email_usuario: return cotacoes
            
        # Lê os ativos já comprados para pré-popular o fallback de Preço Médio
        df_invest = ler_planilha("Investimentos")
        df_config = ler_planilha("Ativos_Config")
        
        if not df_invest.empty and 'Email' in df_invest.columns:
            for _, row in df_invest[df_invest['Email'].astype(str).str.lower() == email_usuario].iterrows():
                ativo = str(row.get('Ativo', '')).strip().upper()
                if ativo and ativo not in ["NAN", "NONE", ""]:
                    ativos_buscados.add(ativo)
                    # Fallback (Preço Médio) se não achar a cotação
                    pm = extrair_numero_br(row.get('PrecoMedio', row.get('Preco', 0)))
                    if pm > 0 and ativo not in cotacoes: cotacoes[ativo] = pm

        if not df_config.empty and 'Email' in df_config.columns:
            for _, row in df_config[df_config['Email'].astype(str).str.lower() == email_usuario].iterrows():
                ativo = str(row.get('Ativo', '')).strip().upper()
                if ativo and ativo not in ["NAN", "NONE", ""]: ativos_buscados.add(ativo)

        if not ativos_buscados: return cotacoes
        
        # -----------------------------------
        # BUSCA TESOURO DIRETO
        # -----------------------------------
        titulos_tesouro = []
        try:
            df_td = pd.read_csv("https://www.tesourodireto.com.br/documents/d/guest/rendimento-resgatar-csv?download=true", sep=';', encoding='utf-8-sig', storage_options={'User-Agent': 'Mozilla/5.0'})
            df_td.columns = [str(c).strip().upper() for c in df_td.columns]
            col_titulo = next((col for col in df_td.columns if 'TÍTULO' in col), df_td.columns[0])
            col_preco = next((col for col in df_td.columns if 'RESGATE' in col or 'PREÇO' in col), df_td.columns[2])
            for _, row in df_td.iterrows():
                nome_limpo = " ".join(str(row[col_titulo]).upper().split())
                if nome_limpo and nome_limpo != "NAN": titulos_tesouro.append({"nome": nome_limpo, "valor": extrair_numero_br(row[col_preco])})
        except:
            pass

        mapa_ativos = {" ".join(a.upper().split()): a for a in ativos_buscados}
        ativos_ja_encontrados = set()
        for titulo in titulos_tesouro:
            if titulo["nome"] in mapa_ativos:
                nome_original = mapa_ativos[titulo["nome"]]
                cotacoes[nome_original] = titulo["valor"]
                ativos_ja_encontrados.add(nome_original)

        ativos_buscados = ativos_buscados - ativos_ja_encontrados
        
        # -----------------------------------
        # BUSCA YAHOO FINANCE (NOVO MOTOR V3)
        # -----------------------------------
        if ativos_buscados:
            tickers_yf, mapa_tickers, tem_exterior = [], {}, False
            
            for ativo in ativos_buscados:
                ticker = ativo
                # REGRA UNIVERSAL: Se não tem ponto e termina com número (ex: BOVA11, CPFE3), é do Brasil. 
                if "." not in ticker and re.search(r'\d+$', ticker): 
                    ticker = f"{ticker}.SA"
                    
                if not ticker.endswith(".SA"): tem_exterior = True
                    
                tickers_yf.append(ticker)
                mapa_tickers[ticker] = ativo 

            if tem_exterior: tickers_yf.append("BRL=X")
            
            try:
                # 5 dias para garantir que pulamos feriados e finais de semana
                df_raw = yf.download(list(set(tickers_yf)), period="5d", progress=False, ignore_tz=True)
                
                if not df_raw.empty:
                    # Pega a última linha válida (último pregão fechado preenchendo buracos)
                    s_last = df_raw.ffill().iloc[-1]
                    
                    # Passo 1: Descobrir o preço do Dólar
                    cotacao_dolar = 1.0
                    if tem_exterior:
                        for p_col in ['Close', 'Adj Close']:
                            if isinstance(s_last.index, pd.MultiIndex):
                                if (p_col, "BRL=X") in s_last.index:
                                    cotacao_dolar = float(s_last[(p_col, "BRL=X")])
                                    break
                                elif ("BRL=X", p_col) in s_last.index:
                                    cotacao_dolar = float(s_last[("BRL=X", p_col)])
                                    break
                            else:
                                if "BRL=X" in tickers_yf and len(set(tickers_yf)) == 1:
                                    cotacao_dolar = float(s_last.get(p_col, 1.0))
                                    break

                    # Passo 2: Descobrir o preço dos Ativos
                    for ticker in tickers_yf:
                        if ticker == "BRL=X": continue
                        
                        preco = None
                        for p_col in ['Close', 'Adj Close']:
                            if isinstance(s_last.index, pd.MultiIndex):
                                if (p_col, ticker) in s_last.index:
                                    preco = s_last[(p_col, ticker)]
                                    break
                                elif (ticker, p_col) in s_last.index:
                                    preco = s_last[(ticker, p_col)]
                                    break
                            else:
                                ativos_pedidos = set([t for t in tickers_yf if t != "BRL=X"])
                                if len(ativos_pedidos) == 1:
                                    preco = s_last.get(p_col)
                                    break
                        
                        # Se encontrou o preço e não é nulo, atualiza o dicionário principal
                        if preco is not None and not pd.isna(preco):
                            preco_float = float(preco)
                            # Se for exterior (não tem .SA no final), multiplica pelo dólar
                            if not ticker.endswith(".SA"):
                                preco_float = preco_float * cotacao_dolar
                                
                            cotacoes[mapa_tickers[ticker]] = preco_float
                            
            except Exception as e: 
                print(f"Alerta na API YF: {e}")
                
        return cotacoes
    except Exception as e:
        print(f"Erro geral: {e}")
        return cotacoes

@st.cache_data(ttl=300, show_spinner=False)
def obter_ativos_por_categoria(email_usuario):
    cat_dict = {"Renda Fixa": [], "Ações": [], "FIIs": [], "Stocks": [], "REITs": [], "ETFs": []}
    try:
        df_config = ler_planilha("Ativos_Config")
        if not df_config.empty and 'Email' in df_config.columns:
            for _, row in df_config[df_config['Email'].astype(str).str.lower() == email_usuario.strip().lower()].iterrows():
                categoria_bruta, ativo = str(row.get('Categoria', '')).strip().upper(), str(row.get('Ativo', '')).strip().upper()
                categoria = ""
                if categoria_bruta in ["AÇÕES", "ACOES", "AÇÃO", "ACAO"]: categoria = "Ações"
                elif categoria_bruta in ["FIIS", "FII"]: categoria = "FIIs"
                elif categoria_bruta in ["IPCA", "RENDA FIXA", "RF"]: categoria = "Renda Fixa"
                elif categoria_bruta in ["STOCKS", "STOCK"]: categoria = "Stocks"
                elif categoria_bruta in ["REITS", "REIT"]: categoria = "REITs"
                elif categoria_bruta in ["ETFS", "ETF"]: categoria = "ETFs"
                if ativo and ativo != "NAN" and categoria and ativo not in cat_dict[categoria]: cat_dict[categoria].append(ativo)
        try:
            res_td = requests.get("https://tesouro.gabriso.com/bonds", headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            if res_td.status_code == 200:
                for bond in res_td.json().get("bonds", []):
                    nome = str(bond.get("name", "")).strip().upper()
                    if any(p in nome for p in ["IPCA+", "SELIC", "PREFIXADO"]) and not any(p in nome for p in ["EDUCA", "APOSENTADORIA"]):
                        if nome not in cat_dict["Renda Fixa"]: cat_dict["Renda Fixa"].append(nome)
        except: pass
        for cat in cat_dict: cat_dict[cat].sort()
        return {categoria: ativos for categoria, ativos in cat_dict.items() if len(ativos) > 0}
    except: return {categoria: ativos for categoria, ativos in cat_dict.items() if len(ativos) > 0}

# ==========================================
# REGISTRAR DEPÓSITOS E COMPRAS
# ==========================================
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
            
        valor_br = f"{float(valor):.2f}".replace('.', ',')
        sheet.append_row([email, data, valor_br], value_input_option='USER_ENTERED')
        
        st.cache_data.clear() 
        return True
    except Exception as e:
        st.error(f"Erro ao salvar depósito: {e}")
        return False

def registrar_compra(email, data, categoria, ativo, quantidade, preco_medio, observacao=""):
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = json.loads(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open("App_Investimentos").worksheet("Investimentos")
        
        qtd_br = f"{float(quantidade):.8f}".replace('.', ',').rstrip('0').rstrip(',')
        if not qtd_br: 
            qtd_br = "0"
            
        preco_br = f"{float(preco_medio):.4f}".replace('.', ',')
        
        sheet.append_row(
            [email, data, categoria, ativo, qtd_br, preco_br, observacao], 
            value_input_option='USER_ENTERED'
        )
        
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar compra: {e}")
        return False

# ==========================================
# AUTENTICAÇÃO E PERFIL
# ==========================================
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
        
        st.cache_data.clear()
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
                    st.cache_data.clear()
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
                
                st.cache_data.clear()
                return True, "✅ Perfil atualizado com sucesso!"
                
        return False, "Usuário não encontrado."
    except Exception as e:
        return False, f"Erro ao atualizar perfil: {e}"

# ==========================================
# 8. AUDITORIA E BACKUP
# ==========================================
def atualizar_historico_usuario(email, nome_aba, df_editado):
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
        
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        chave_gcp = st.secrets["gcp_service_account"]
        chave_dict = json.loads(chave_gcp) if isinstance(chave_gcp, str) else dict(chave_gcp)
        creds = Credentials.from_service_account_info(chave_dict, scopes=scopes)
        client = gspread.authorize(creds)
        
        planilha = client.open("App_Investimentos")
        aba = planilha.worksheet(nome_aba)
        
        aba.clear()
        dados_salvar = [df_final.columns.values.tolist()] + df_final.fillna("").values.tolist()
        aba.update(dados_salvar)
        
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar edição: {e}")
        return False

def deletar_registros_usuario(nome_aba, email):
    try:
        NOME_PLANILHA = "App_Investimentos" 
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        chave_gcp = st.secrets["gcp_service_account"]
        chave_dict = json.loads(chave_gcp) if isinstance(chave_gcp, str) else dict(chave_gcp)
        creds = Credentials.from_service_account_info(chave_dict, scopes=scopes)
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
            
        st.cache_data.clear()
        return True, "Sucesso"
    except Exception as e:
        return False, f"Erro ao apagar dados do Google Sheets: {str(e)}"

def inserir_lote_registros(nome_aba, df):
    if df.empty:
        return True, "Planilha vazia, nada a inserir."
    try:
        NOME_PLANILHA = "App_Investimentos"
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        chave_gcp = st.secrets["gcp_service_account"]
        chave_dict = json.loads(chave_gcp) if isinstance(chave_gcp, str) else dict(chave_gcp)
        creds = Credentials.from_service_account_info(chave_dict, scopes=scopes)
        client = gspread.authorize(creds)
        
        aba = client.open(NOME_PLANILHA).worksheet(nome_aba)
        
        df_limpo = df.astype(str).replace(["nan", "NaT", "None", "<NA>"], "")
        dados = df_limpo.values.tolist()
        
        aba.append_rows(dados, value_input_option='USER_ENTERED')
        
        st.cache_data.clear()
        return True, "Sucesso"
    except Exception as e:
        return False, f"Erro ao salvar no Google Sheets: {str(e)}"

# ==========================================
# 9. PAINEL DE ADMINISTRADOR
# ==========================================
def listar_todos_usuarios():
    """Busca a lista de todos os usuários cadastrados na planilha para o Painel Admin"""
    try:
        df_usuarios = ler_planilha("Usuarios")
        if df_usuarios.empty:
            return []
        
        df_usuarios.columns = [str(c).strip() for c in df_usuarios.columns]
        
        usuarios_lista = []
        for _, row in df_usuarios.iterrows():
            email = str(row.get('Email', '')).strip().lower()
            nome = str(row.get('Nome', 'Sem Nome')).strip()
            
            if email:
                usuarios_lista.append({"email": email, "nome": nome})
                
        return usuarios_lista
    except Exception as e:
        print(f"Erro ao listar usuários: {e}")
        return []
