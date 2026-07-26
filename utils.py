import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json

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

def ler_planilha(aba_nome):
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = json.loads(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open("App_Investimentos").worksheet(aba_nome)
        
        # SOLUÇÃO: Lê o texto exato para evitar que a biblioteca americana engula nossas vírgulas
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
        
        # Proteção extra na hora de ler para encontrar o usuário
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
            
        # Proteção na leitura dos ativos velhos
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
        return True
    except Exception as e:
        st.error(f"Erro ao salvar ativos: {e}")
        return False

def obter_cotacoes():
    """Lê a aba Cotacao de forma inteligente, caçando os cabeçalhos das categorias"""
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = json.loads(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open("App_Investimentos").worksheet("Cotacao")
        
        valores = sheet.get_all_values()
        cotacoes = {}
        if len(valores) > 1:
            cabecalhos = valores[0]
            indices_ativos = []
            
            # 1. Procura em quais colunas os nomes dos ativos estão escritos
            for i, col in enumerate(cabecalhos):
                c = str(col).strip().upper()
                if c in ["AÇÕES", "ACOES", "AÇÃO", "ACAO", "FIIS", "FII", "IPCA", "RENDA FIXA", "STOCKS", "REITS", "ETFS"]:
                    indices_ativos.append(i)
            
            # 2. Puxa o ativo da coluna encontrada, e o preço obrigatoriamente da coluna ao lado (i + 1)
            for linha in valores[1:]:
                for idx_ativo in indices_ativos:
                    idx_preco = idx_ativo + 1
                    if len(linha) > idx_preco:
                        ativo = str(linha[idx_ativo]).strip().upper()
                        preco = extrair_numero_br(linha[idx_preco])
                        if ativo and preco > 0:
                            cotacoes[ativo] = preco
                            
        return cotacoes
    except Exception as e:
        return {}

def obter_ativos_por_categoria():
    """Lê a aba Cotacao e agrupa os ativos dinamicamente, sem depender da posição da coluna"""
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
            
            # Mapeia dinamicamente qual categoria está em qual coluna
            for i, col in enumerate(cabecalhos):
                c = str(col).strip().upper()
                if c in ["AÇÕES", "ACOES", "AÇÃO", "ACAO"]: mapa_colunas[i] = "Ações"
                elif c in ["FIIS", "FII"]: mapa_colunas[i] = "FIIs"
                elif c in ["IPCA", "RENDA FIXA", "RF"]: mapa_colunas[i] = "Renda Fixa"
                elif c in ["STOCKS", "STOCK"]: mapa_colunas[i] = "Stocks"
                elif c in ["REITS", "REIT"]: mapa_colunas[i] = "REITs"
                elif c in ["ETFS", "ETF"]: mapa_colunas[i] = "ETFs"
            
            # Prepara a lista vazia para as categorias que ele encontrou
            for cat in mapa_colunas.values():
                cat_dict[cat] = []
                
            # Popula as listas
            for linha in valores[1:]:
                for idx, cat in mapa_colunas.items():
                    if len(linha) > idx:
                        ativo = str(linha[idx]).strip().upper()
                        if ativo and ativo != "NAN" and ativo not in cat_dict[cat]:
                            cat_dict[cat].append(ativo)
                            
            # Ordem alfabética para facilitar a busca no menu
            for cat in cat_dict:
                cat_dict[cat].sort()
                
        return cat_dict
    except Exception as e:
        return {}

def registrar_deposito(email, data, valor):
    """Salva um novo aporte financeiro na aba Depositos"""
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
            
        # Formata o valor numérico para salvar no formato BR (ex: 1500,50)
        valor_str = f"{valor:.2f}".replace('.', ',')
        sheet.append_row([email, data, valor_str])
        return True
    except Exception as e:
        st.error(f"Erro ao salvar depósito: {e}")
        return False

def registrar_compra(email, data, categoria, ativo, quantidade, preco_medio):
    """Salva uma nova compra de ativo na aba Investimentos"""
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = json.loads(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open("App_Investimentos").worksheet("Investimentos")
        
        qtd_str = f"{quantidade:.4f}".replace('.', ',').rstrip('0').rstrip(',')
        preco_str = f"{preco_medio:.4f}".replace('.', ',')
        
        # O último campo em branco é o PrecoAtual (que agora buscamos automático da aba Cotacao)
        sheet.append_row([email, data, categoria, ativo, qtd_str, preco_str, ""])
        return True
    except Exception as e:
        st.error(f"Erro ao salvar compra: {e}")
        return False
