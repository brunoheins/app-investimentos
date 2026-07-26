import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json

def ler_planilha(aba_nome):
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = json.loads(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open("App_Investimentos").worksheet(aba_nome)
        return pd.DataFrame(sheet.get_all_records())
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
            
        df_all = pd.DataFrame(sheet.get_all_records())
        
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

def extrair_numero_br(valor_str):
    """Lê números do Sheets no padrão BR e converte para Float do Python"""
    if pd.isna(valor_str):
        return 0.0
    if isinstance(valor_str, (int, float)):
        return float(valor_str)
    
    v = str(valor_str).replace('R$', '').replace('%', '').strip()
    if v == '' or v.lower() == 'nan':
        return 0.0
        
    # Se tem vírgula, é padrão brasileiro (ex: 1.500,50)
    if ',' in v:
        v = v.replace('.', '')    # Remove os pontos de milhar
        v = v.replace(',', '.')   # Transforma a vírgula em ponto (padrão Python)
        
    try:
        return float(v)
    except:
        return 0.0

def formata_br(valor):
    """Recebe um float do Python e devolve uma string R$ no padrão BR (ex: R$ 1.500,50)"""
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

def obter_cotacoes():
    """Lê a aba Cotacao e retorna um dicionário com todos os preços unificados"""
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = json.loads(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open("App_Investimentos").worksheet("Cotacao")
        
        # get_all_values() lê a planilha como uma matriz, evitando erros com colunas de mesmo nome
        valores = sheet.get_all_values()
        
        cotacoes = {}
        if len(valores) > 1:
            for linha in valores[1:]: # Pula o cabeçalho (linha 0)
                
                # Leitura Colunas A (0) e B (1) -> Ações, FIIs, Stocks, etc.
                if len(linha) >= 2:
                    ativo = str(linha[0]).strip().upper()
                    preco = extrair_numero_br(linha[1])
                    if ativo and preco > 0:
                        cotacoes[ativo] = preco
                
                # Leitura Colunas E (4) e F (5) -> IPCA / Títulos
                if len(linha) >= 6:
                    ipca_titulo = str(linha[4]).strip().upper()
                    preco_ipca = extrair_numero_br(linha[5])
                    if ipca_titulo and preco_ipca > 0:
                        cotacoes[ipca_titulo] = preco_ipca
                        
        return cotacoes
    except Exception as e:
        # Retorna vazio silenciosamente para não travar o app se a aba ainda não existir
        return {}
