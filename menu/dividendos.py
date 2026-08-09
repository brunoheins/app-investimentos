import streamlit as st
import pandas as pd
import yfinance as yf
from dateutil.relativedelta import relativedelta
import re
from utils import ler_planilha, extrair_numero_br, formata_br

# Mágica do Cache: Guarda os dados por 1 hora para a tela abrir instantaneamente!
@st.cache_data(ttl=3600, show_spinner=False)
def buscar_historico_dividendos(df_carteira):
    hoje = pd.Timestamp.today().tz_localize(None)
    um_ano_atras = hoje - relativedelta(months=12)
    
    dados_dividendos = []
    ativos_com_erro = []

    for _, row in df_carteira.iterrows():
        ativo = row['Ativo']
        qtd = row['Quantidade']

        # Normaliza o ticker para a B3
        ticker_yf = ativo
        if "." not in ticker_yf and re.search(r'\d+$', ticker_yf):
            ticker_yf = f"{ticker_yf}.SA"

        try:
            ticker = yf.Ticker(ticker_yf)
            divs = ticker.dividends # Puxa todo o histórico de dividendos do ativo
            
            if not divs.empty:
                # Remove o fuso horário para não dar erro na comparação de datas
                divs.index = divs.index.tz_localize(None)
                # Filtra apenas os últimos 12 meses
                divs = divs[divs.index >= um_ano_atras]
                
                for data, valor_por_cota in divs.items():
                    dados_dividendos.append({
                        'Data': data,
                        'Mês_Sort': data.strftime('%Y-%m'),
                        'Ativo': ativo,
                        'Valor por Cota': valor_por_cota,
                        'Total Recebido': valor_por_cota * qtd # Multiplica pela sua posição
                    })
        except Exception:
            ativos_com_erro.append(ativo)
            
    return pd.DataFrame(dados_dividendos), ativos_com_erro

def render():
    st.title("💸 Dashboard de Dividendos")
    st.markdown("Acompanhe a estimativa de renda passiva gerada pela sua carteira nos últimos 12 meses, com base na sua posição atual.")

    email_usuario = st.session_state.email.strip().lower()

    with st.spinner("Buscando histórico de proventos na B3 e no Exterior... Isso pode levar alguns segundos na primeira vez."):
        # 1. Puxar a carteira atual do usuário
        df_invest = ler_planilha("Investimentos")
        if df_invest.empty or 'Email' not in df_invest.columns:
            st.info("Você ainda não possui investimentos cadastrados para calcular dividendos.")
            return

        df_invest['Email'] = df_invest['Email'].astype(str).str.strip().str.lower()
        meus_invest = df_invest[df_invest['Email'] == email_usuario].copy()

        if meus_invest.empty:
            st.info("Você ainda não possui investimentos cadastrados para calcular dividendos.")
            return

        # Prepara os dados (Soma tudo que ele tem de cada ativo)
        meus_invest['Ativo'] = meus_invest['Ativo'].astype(str).str.strip().upper()
        meus_invest['Quantidade'] = meus_invest['Quantidade'].apply(extrair_numero_br)
        carteira_agrupada = meus_invest.groupby('Ativo')['Quantidade'].sum().reset_index()
        carteira_agrupada = carteira_agrupada[carteira_agrupada['Quantidade'] > 0]

        # 2. Busca os dividendos usando a função com Cache
        df_divs, ativos_com_erro = buscar_historico_dividendos(carteira_agrupada)

        if df_divs.empty:
            st.warning("Nenhum pagamento de dividendos foi encontrado para os seus ativos nos últimos 12 meses.")
            return

        # 3. Processar os dados para o Gráfico
        resumo_mensal = df_divs.groupby('Mês_Sort')['Total Recebido'].sum().reset_index()
        # Formata o mês para ficar bonito no gráfico (ex: 08/2023)
        resumo_mensal['Mês'] = pd.to_datetime(resumo_mensal['Mês_Sort']).dt.strftime('%m/%Y')
        
        total_12m = resumo_mensal['Total Recebido'].sum()
        media_mensal = total_12m / len(resumo_mensal) if not resumo_mensal.empty else 0
        melhor_mes = resumo_mensal['Total Recebido'].max()

        # --- KPI's (Destaques no topo) ---
        col1, col2, col3 = st.columns(3)
        col1.metric("💰 Total em 12 Meses", formata_br(total_12m))
        col2.metric("📅 Média Mensal", formata_br(media_mensal))
        col3.metric("🚀 Melhor Mês", formata_br(melhor_mes))

        st.markdown("---")
        st.subheader("📈 Evolução da Renda Passiva (Últimos 12 Meses)")

        # Gráfico de Barras Nativo do Streamlit (Lindo e automático)
        st.bar_chart(resumo_mensal.set_index('Mês')['Total Recebido'], color="#00C851")

        # --- Tabela de Detalhamento ---
        st.markdown("### 📝 Quais ativos mais te pagaram?")
        resumo_ativo = df_divs.groupby('Ativo')['Total Recebido'].sum().reset_index().sort_values('Total Recebido', ascending=False)
        
        # Cria uma visualização estilizada
        st.dataframe(
            resumo_ativo.style.format({"Total Recebido": lambda x: formata_br(x)})
            .bar(subset=['Total Recebido'], color='#00C851', vmin=0),
            use_container_width=True, 
            hide_index=True
        )
        
        if ativos_com_erro:
            st.caption(f"⚠️ **Aviso:** Não foi possível encontrar dados de proventos para os seguintes ativos (eles podem ser de Renda Fixa ou não listados no Yahoo): {', '.join(ativos_com_erro)}")