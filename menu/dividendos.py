import streamlit as st
import pandas as pd
import yfinance as yf
from dateutil.relativedelta import relativedelta
import re
from utils import ler_planilha, extrair_numero_br, formata_br

# Mágica do Cache: Guarda os dados por 1 hora para a tela abrir instantaneamente!
@st.cache_data(ttl=3600, show_spinner=False)
def buscar_historico_dividendos(df_transacoes):
    hoje = pd.Timestamp.today().tz_localize(None)
    um_ano_atras = hoje - relativedelta(months=12)
    
    dados_dividendos = []
    ativos_com_erro = []

    # Certifica que a Data das transações é interpretada corretamente (DD/MM/YYYY)
    df_transacoes['Data'] = pd.to_datetime(df_transacoes['Data'], format='%d/%m/%Y', errors='coerce')
    df_transacoes = df_transacoes.dropna(subset=['Data'])

    ativos = df_transacoes['Ativo'].unique()

    for ativo in ativos:
        # Filtra apenas as movimentações deste ativo específico
        df_ativo_tx = df_transacoes[df_transacoes['Ativo'] == ativo]

        # Normaliza o ticker para a B3
        ticker_yf = ativo
        if "." not in ticker_yf and re.search(r'\d+$', ticker_yf):
            ticker_yf = f"{ticker_yf}.SA"

        try:
            ticker = yf.Ticker(ticker_yf)
            divs = ticker.dividends # Puxa histórico de dividendos do ativo
            
            if not divs.empty:
                # Remove o fuso horário para não dar erro na comparação de datas
                divs.index = divs.index.tz_localize(None)
                # Filtra apenas os últimos 12 meses
                divs = divs[divs.index >= um_ano_atras]
                
                for data_div, valor_por_cota in divs.items():
                    # MÁGICA HISTÓRICA: Soma as cotas compradas ANTES ou NO DIA da Data Com (ex-dividend)
                    qtd_na_data = df_ativo_tx[df_ativo_tx['Data'] <= data_div]['Quantidade'].sum()
                    
                    # Só registra o dividendo se você tinha o ativo na carteira naquela época!
                    if qtd_na_data > 0:
                        dados_dividendos.append({
                            'Data': data_div,
                            'Mês_Sort': data_div.strftime('%Y-%m'),
                            'Ativo': ativo,
                            'Valor por Cota': valor_por_cota,
                            'Total Recebido': valor_por_cota * qtd_na_data
                        })
        except Exception:
            ativos_com_erro.append(ativo)
            
    return pd.DataFrame(dados_dividendos), ativos_com_erro


def render():
    st.title("💸 Dashboard de Dividendos")
    st.markdown("Acompanhe os dividendos **reais** que caíram na sua conta nos últimos 12 meses, calculados de acordo com a data exata das suas compras.")

    email_usuario = st.session_state.email.strip().lower()

    with st.spinner("Cruzando o histórico das suas compras com a base de proventos da Bolsa..."):
        # 1. Puxar a carteira do usuário
        df_invest = ler_planilha("Investimentos")
        if df_invest.empty or 'Email' not in df_invest.columns:
            st.info("Você ainda não possui investimentos cadastrados para calcular dividendos.")
            return

        df_invest['Email'] = df_invest['Email'].astype(str).str.strip().str.lower()
        meus_invest = df_invest[df_invest['Email'] == email_usuario].copy()

        if meus_invest.empty:
            st.info("Você ainda não possui investimentos cadastrados para calcular dividendos.")
            return

        # Prepara os dados brutos (não agrupa mais por ativo, pois precisamos da linha do tempo)
        meus_invest['Ativo'] = meus_invest['Ativo'].astype(str).str.strip().str.upper()
        meus_invest['Quantidade'] = meus_invest['Quantidade'].apply(extrair_numero_br)

        # 2. Busca os dividendos cruzando a linha do tempo (Função com Cache)
        df_divs, ativos_com_erro = buscar_historico_dividendos(meus_invest)

        if df_divs.empty:
            st.warning("Nenhum pagamento de dividendos foi encontrado para a sua carteira (considerando as datas em que você possuía os ativos) nos últimos 12 meses.")
            return

        # 3. Processar os dados para o Gráfico
        resumo_mensal = df_divs.groupby('Mês_Sort')['Total Recebido'].sum().reset_index()
        # Formata o mês para ficar bonito no gráfico (ex: 08/2026)
        resumo_mensal['Mês'] = pd.to_datetime(resumo_mensal['Mês_Sort']).dt.strftime('%m/%Y')
        
        total_12m = resumo_mensal['Total Recebido'].sum()
        media_mensal = total_12m / len(resumo_mensal) if not resumo_mensal.empty else 0
        melhor_mes = resumo_mensal['Total Recebido'].max()

        # --- KPI's (Destaques no topo) ---
        col1, col2, col3 = st.columns(3)
        col1.metric("💰 Total Real em 12 Meses", formata_br(total_12m))
        col2.metric("📅 Média Mensal", formata_br(media_mensal))
        col3.metric("🚀 Melhor Mês", formata_br(melhor_mes))

        st.markdown("---")
        st.subheader("📈 Evolução da Renda Passiva (Últimos 12 Meses)")

        # Gráfico de Barras Nativo do Streamlit (Lindo e automático)
        st.bar_chart(resumo_mensal.set_index('Mês')['Total Recebido'], color="#00C851")

        # --- Tabela de Detalhamento ---
        st.markdown("### 📝 Quais ativos te pagaram enquanto você os possuía?")
        
        # Agrupa os dados
        resumo_ativo = df_divs.groupby('Ativo').agg({
            'Valor por Cota': 'sum',
            'Total Recebido': 'sum'
        }).reset_index().sort_values('Total Recebido', ascending=False)
        
        resumo_ativo.rename(columns={'Valor por Cota': 'Total 12 Meses / Cota'}, inplace=True)
        
        col_tabela, col_vazia = st.columns([1.5, 1])
        
        with col_tabela:
            st.dataframe(
                resumo_ativo.style.format({
                    "Total 12 Meses / Cota": lambda x: formata_br(x),
                    "Total Recebido": lambda x: formata_br(x)
                })
                .bar(subset=['Total Recebido'], color='#00C851', vmin=0),
                use_container_width=True, 
                hide_index=True
            )
        
        if ativos_com_erro:
            st.caption(f"⚠️ **Aviso:** Não foi possível encontrar dados de proventos para os seguintes ativos (eles podem ser de Renda Fixa ou não listados no Yahoo): {', '.join(ativos_com_erro)}")
