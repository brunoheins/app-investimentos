import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils import ler_planilha, obter_cotacoes, extrair_numero_br, formata_br

def render():
    st.title("📈 Evolução do Patrimônio")
    st.markdown("Acompanhe o crescimento dos seus aportes mensais e compare com a marcação a mercado atual.")

    with st.spinner("Processando histórico de compras..."):
        df_invest = ler_planilha("Investimentos")
        
        if df_invest.empty or 'Email' not in df_invest.columns:
            st.info("A aba 'Investimentos' está vazia ou não configurada corretamente.")
            return
            
        df_invest['Email'] = df_invest['Email'].astype(str).str.strip().str.lower()
        df_user_invest = df_invest[df_invest['Email'] == st.session_state.email].copy()
        
        if df_user_invest.empty:
            st.info("Você ainda não possui investimentos cadastrados.")
            return

        # Validação amigável da nova coluna DataCompra
        if 'DataCompra' not in df_user_invest.columns:
            st.error("⚠️ Coluna 'DataCompra' não encontrada na aba 'Investimentos'. Atualize sua planilha com a estrutura exata: **Email | DataCompra | Categoria | Ativo | Quantidade | PrecoMedio | PrecoAtual**")
            return

        # --- 1. PREPARAÇÃO DOS DADOS ---
        df_user_invest['Ativo'] = df_user_invest['Ativo'].astype(str).str.strip().str.upper()
        df_user_invest['Quantidade'] = df_user_invest['Quantidade'].apply(extrair_numero_br)
        df_user_invest['PrecoMedio'] = df_user_invest['PrecoMedio'].apply(extrair_numero_br)
        df_user_invest['PrecoAtual_Planilha'] = df_user_invest['PrecoAtual'].apply(extrair_numero_br)
        
        # Cotações ao Vivo do Dicionário
        cotacoes_dict = obter_cotacoes()
        df_user_invest['PrecoCotacao'] = df_user_invest['Ativo'].map(cotacoes_dict)
        df_user_invest['PrecoLive'] = pd.to_numeric(df_user_invest['PrecoCotacao']).combine_first(df_user_invest['PrecoAtual_Planilha']).fillna(0)

        # --- 2. CÁLCULO GERAL (HOJE) ---
        live_investido = (df_user_invest['Quantidade'] * df_user_invest['PrecoMedio']).sum()
        live_atual = (df_user_invest['Quantidade'] * df_user_invest['PrecoLive']).sum()

        # --- 3. PROCESSAMENTO DO HISTÓRICO (AGRUPADO POR MÊS) ---
        # Converte DataCompra para datetime (Identifica o padrão BR: DD/MM/AAAA)
        df_user_invest['DataCompra'] = pd.to_datetime(df_user_invest['DataCompra'], dayfirst=True, errors='coerce')
        
        # Remove linhas que não tenham uma data de compra válida
        df_hist = df_user_invest.dropna(subset=['DataCompra']).copy()
        
        if df_hist.empty:
            st.warning("Nenhuma data de compra válida foi encontrada. Use o formato DD/MM/AAAA na coluna DataCompra.")
            return

        # Calcula o custo daquela compra específica
        df_hist['ValorAportado'] = df_hist['Quantidade'] * df_hist['PrecoMedio']
        
        # Ordena cronologicamente e extrai o Ano-Mês para fazer o agrupamento
        df_hist = df_hist.sort_values('DataCompra')
        df_hist['MesAno_Sort'] = df_hist['DataCompra'].dt.strftime('%Y-%m')
        
        # Agrupa tudo que foi comprado no mesmo mês
        df_agrupado = df_hist.groupby('MesAno_Sort')['ValorAportado'].sum().reset_index()
        df_agrupado = df_agrupado.sort_values('MesAno_Sort')
        
        # O pulo do gato: Calcula a SOMA ACUMULADA dos aportes ao longo do tempo
        df_agrupado['Total_Investido_Acumulado'] = df_agrupado['ValorAportado'].cumsum()
        
        # Formata a data para ficar bonita no gráfico (Mês/Ano)
        df_agrupado['MesExibicao'] = pd.to_datetime(df_agrupado['MesAno_Sort'], format='%Y-%m').dt.strftime('%m/%Y')

    # --- 4. CARDS DE RESUMO ---
    lucro_rs = live_atual - live_investido
    lucro_pct = (lucro_rs / live_investido * 100) if live_investido > 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Investido (Custo)", formata_br(live_investido))
    col2.metric("Saldo Atual (Mercado)", formata_br(live_atual))
    col3.metric("Resultado (Lucro/Prejuízo)", formata_br(lucro_rs), f"{lucro_pct:+.2f}%".replace('.', ','))
    
    st.markdown("---")

    # --- 5. RENDERIZAÇÃO DO GRÁFICO (PLOTLY) ---
    hoje_str = "Hoje"
    
    # Eixo X e Y do Total Investido (inclui a data de hoje para ancorar a linha)
    x_investido = df_agrupado['MesExibicao'].tolist() + [hoje_str]
    y_investido = df_agrupado['Total_Investido_Acumulado'].tolist() + [live_investido]

    fig = go.Figure()

    # TRACE 1: Curva de Aportes Acumulados (Área)
    fig.add_trace(go.Scatter(
        x=x_investido, 
        y=y_investido,
        mode='lines+markers',
        name='Total Investido (Custo)',
        line=dict(color='#8c92ac', width=3),
        fill='tozeroy',
        fillcolor='rgba(140, 146, 172, 0.15)',
        hovertemplate="Período: %{x}<br>Aportado Acumulado: R$ %{y:,.2f}<extra></extra>"
    ))

    # TRACE 2: Ponto isolado indicando o Valor Atual do Patrimônio (Só existe "Hoje")
    cor_saldo = '#00cc96' if live_atual >= live_investido else '#ef553b'
    
    fig.add_trace(go.Scatter(
        x=[hoje_str], 
        y=[live_atual],
        mode='markers',
        name='Valor de Mercado (Hoje)',
        marker=dict(color=cor_saldo, size=14, symbol='diamond'),
        hovertemplate="Hoje<br>Valor de Mercado: R$ %{y:,.2f}<extra></extra>"
    ))

    # TRACE 3: Linha pontilhada conectando Custo vs Mercado (Mostra o tamanho do lucro/preju)
    fig.add_trace(go.Scatter(
        x=[hoje_str, hoje_str],
        y=[live_investido, live_atual],
        mode='lines',
        name='Resultado Real',
        line=dict(color=cor_saldo, width=2, dash='dot'),
        hoverinfo='skip',
        showlegend=False
    ))

    # Formatação do layout para monitor 14"
    fig.update_layout(
        height=450,
        margin=dict(l=0, r=0, t=30, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
        xaxis=dict(showgrid=False),
        yaxis=dict(tickformat=",.2f")
    )
    
    st.plotly_chart(fig, use_container_width=True)
