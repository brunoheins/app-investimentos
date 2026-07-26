import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from utils import ler_planilha, obter_cotacoes, extrair_numero_br, formata_br

def render():
    st.title("📈 Evolução do Patrimônio")
    st.markdown("Acompanhe o acúmulo dos seus aportes mensais e compare com o valor de mercado.")

    with st.spinner("Calculando evolução histórica da carteira..."):
        df_invest = ler_planilha("Investimentos")
        
        if df_invest.empty or 'Email' not in df_invest.columns:
            st.info("A aba 'Investimentos' está vazia ou não configurada corretamente.")
            return
            
        df_invest['Email'] = df_invest['Email'].astype(str).str.strip().str.lower()
        df_user_invest = df_invest[df_invest['Email'] == st.session_state.email].copy()
        
        if df_user_invest.empty:
            st.info("Você ainda não possui investimentos cadastrados.")
            return

        if 'DataCompra' not in df_user_invest.columns:
            st.error("⚠️ Coluna 'DataCompra' não encontrada na aba 'Investimentos'. Atualize sua planilha.")
            return

        # --- 1. PREPARAÇÃO DOS DADOS BÁSICOS ---
        df_user_invest['Ativo'] = df_user_invest['Ativo'].astype(str).str.strip().str.upper()
        df_user_invest['Quantidade'] = df_user_invest['Quantidade'].apply(extrair_numero_br)
        df_user_invest['PrecoMedio'] = df_user_invest['PrecoMedio'].apply(extrair_numero_br)
        df_user_invest['PrecoAtual_Planilha'] = df_user_invest['PrecoAtual'].apply(extrair_numero_br)
        
        # Busca Cotações
        cotacoes_dict = obter_cotacoes()
        df_user_invest['PrecoCotacao'] = df_user_invest['Ativo'].map(cotacoes_dict)
        df_user_invest['PrecoLive'] = pd.to_numeric(df_user_invest['PrecoCotacao']).combine_first(df_user_invest['PrecoAtual_Planilha']).fillna(0)

        # Trata as datas
        df_user_invest['DataCompra'] = pd.to_datetime(df_user_invest['DataCompra'], dayfirst=True, errors='coerce')
        df_hist = df_user_invest.dropna(subset=['DataCompra']).copy()
        
        if df_hist.empty:
            st.warning("Nenhuma data de compra válida foi encontrada. Use o formato DD/MM/AAAA.")
            return

        df_hist['ValorAportado'] = df_hist['Quantidade'] * df_hist['PrecoMedio']
        df_hist['MesAno_Sort'] = df_hist['DataCompra'].dt.strftime('%Y-%m')

        # --- 2. MOTOR MATEMÁTICO: RECONSTRUÇÃO DA LINHA DO TEMPO ---
        # Agrupa compras que aconteceram no mesmo mês para o mesmo ativo
        df_mensal = df_hist.groupby(['MesAno_Sort', 'Ativo']).agg({
            'Quantidade': 'sum',
            'ValorAportado': 'sum',
            'PrecoLive': 'first' # O preço atual de mercado do ativo
        }).reset_index()

        meses_unicos = sorted(df_hist['MesAno_Sort'].unique())
        
        linha_tempo = []
        acumulado_ativos = {} # Guarda o "cofre" virtual da carteira crescendo a cada mês
        
        for mes in meses_unicos:
            compras_do_mes = df_mensal[df_mensal['MesAno_Sort'] == mes]
            
            # Adiciona as compras do mês no acumulado geral
            for _, row in compras_do_mes.iterrows():
                ativo = row['Ativo']
                if ativo not in acumulado_ativos:
                    acumulado_ativos[ativo] = {'qtd': 0.0, 'custo': 0.0, 'preco_live': row['PrecoLive']}
                
                acumulado_ativos[ativo]['qtd'] += row['Quantidade']
                acumulado_ativos[ativo]['custo'] += row['ValorAportado']
                
            # Fecha a "fotografia" do mês
            total_custo_mes = sum(dados['custo'] for dados in acumulado_ativos.values())
            # Multiplica as cotas acumuladas até aquele mês pelo preço que elas valem *hoje*
            total_mercado_mes = sum(dados['qtd'] * dados['preco_live'] for dados in acumulado_ativos.values())
            
            linha_tempo.append({
                'MesAno': mes,
                'TotalInvestido': total_custo_mes,
                'ValorMercado': total_mercado_mes
            })
            
        df_timeline = pd.DataFrame(linha_tempo)
        df_timeline['MesExibicao'] = pd.to_datetime(df_timeline['MesAno'], format='%Y-%m').dt.strftime('%m/%Y')

        # Verifica se o último mês analisado é o mês atual. Se não for, adicionamos "Hoje" copiando a última foto.
        mes_atual_str = datetime.now().strftime('%Y-%m')
        if meses_unicos[-1] != mes_atual_str:
            df_timeline.loc[len(df_timeline)] = {
                'MesAno': mes_atual_str,
                'TotalInvestido': df_timeline.iloc[-1]['TotalInvestido'],
                'ValorMercado': df_timeline.iloc[-1]['ValorMercado'],
                'MesExibicao': "Hoje"
            }
        else:
            df_timeline.loc[df_timeline.index[-1], 'MesExibicao'] = "Hoje"

        # --- 3. CARDS DE RESUMO ---
        live_investido = df_timeline.iloc[-1]['TotalInvestido']
        live_atual = df_timeline.iloc[-1]['ValorMercado']
        
        lucro_rs = live_atual - live_investido
        lucro_pct = (lucro_rs / live_investido * 100) if live_investido > 0 else 0

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Investido (Custo)", formata_br(live_investido))
        col2.metric("Saldo Atual (Mercado)", formata_br(live_atual))
        col3.metric("Resultado (Lucro/Prejuízo)", formata_br(lucro_rs), f"{lucro_pct:+.2f}%".replace('.', ','))
        
        st.markdown("---")

        # --- 4. RENDERIZAÇÃO DO GRÁFICO (DUAS LINHAS) ---
        fig = go.Figure()

        # Linha 1: Total Investido (Cinza, área preenchida leve)
        fig.add_trace(go.Scatter(
            x=df_timeline['MesExibicao'], 
            y=df_timeline['TotalInvestido'],
            mode='lines+markers',
            name='Total Investido (Custo)',
            line=dict(color='#8c92ac', width=3, dash='dot'),
            fill='tozeroy',
            fillcolor='rgba(140, 146, 172, 0.1)',
            hovertemplate="Custo Acumulado: R$ %{y:,.2f}<extra></extra>"
        ))

        # Linha 2: Valor Corrigido de Mercado (Colorida)
        cor_saldo = '#00cc96' if live_atual >= live_investido else '#ef553b'
        cor_area = 'rgba(0, 204, 150, 0.25)' if live_atual >= live_investido else 'rgba(239, 85, 59, 0.25)'
        
        fig.add_trace(go.Scatter(
            x=df_timeline['MesExibicao'], 
            y=df_timeline['ValorMercado'],
            mode='lines+markers',
            name='Valor de Mercado Corrigido',
            line=dict(color=cor_saldo, width=3),
            fill='tonexty', # Preenche apenas o espaço entre a linha do mercado e a linha de custo
            fillcolor=cor_area,
            hovertemplate="Corrigido Mercado: R$ %{y:,.2f}<extra></extra>"
        ))

        # Ajustes visuais (Hover unificado para mostrar os dois valores juntos)
        fig.update_layout(
            height=450,
            margin=dict(l=0, r=0, t=30, b=0),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode="x unified",
            xaxis=dict(showgrid=False),
            yaxis=dict(tickformat=",.2f")
        )
        
        st.plotly_chart(fig, use_container_width=True)
