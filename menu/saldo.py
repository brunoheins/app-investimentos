import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from utils import ler_planilha, obter_cotacoes, extrair_numero_br, formata_br

def render():
    st.title("📈 Evolução Real do Patrimônio")
    st.markdown("Compare o **Dinheiro Novo Aportado** (Depósitos) com o **Valor de Mercado**. A diferença é a sua Rentabilidade Real (Valorização + Dividendos).")

    with st.spinner("Construindo linha do tempo da sua carteira..."):
        
        # --- 1. LER E TRATAR DEPÓSITOS ---
        df_dep = ler_planilha("Depositos")
        if not df_dep.empty and 'Email' in df_dep.columns:
            df_dep['Email'] = df_dep['Email'].astype(str).str.strip().str.lower()
            df_user_dep = df_dep[df_dep['Email'] == st.session_state.email].copy()
            
            if not df_user_dep.empty:
                df_user_dep['Data'] = pd.to_datetime(df_user_dep['Data'], dayfirst=True, errors='coerce')
                df_user_dep = df_user_dep.dropna(subset=['Data'])
                df_user_dep['Valor'] = df_user_dep['Valor'].apply(extrair_numero_br)
                df_user_dep['MesAno'] = df_user_dep['Data'].dt.strftime('%Y-%m')
                # Soma todos os depósitos feitos dentro do mesmo mês
                df_dep_agrupado = df_user_dep.groupby('MesAno')['Valor'].sum().reset_index()
            else:
                df_dep_agrupado = pd.DataFrame(columns=['MesAno', 'Valor'])
        else:
            df_dep_agrupado = pd.DataFrame(columns=['MesAno', 'Valor'])

        # --- 2. LER E TRATAR COMPRAS (ESTOQUE DE ATIVOS) ---
        df_invest = ler_planilha("Investimentos")
        if not df_invest.empty and 'Email' in df_invest.columns:
            df_invest['Email'] = df_invest['Email'].astype(str).str.strip().str.lower()
            df_user_inv = df_invest[df_invest['Email'] == st.session_state.email].copy()
            
            if not df_user_inv.empty and 'DataCompra' in df_user_inv.columns:
                df_user_inv['DataCompra'] = pd.to_datetime(df_user_inv['DataCompra'], dayfirst=True, errors='coerce')
                df_user_inv = df_user_inv.dropna(subset=['DataCompra'])
                
                df_user_inv['Ativo'] = df_user_inv['Ativo'].astype(str).str.strip().str.upper()
                df_user_inv['Quantidade'] = df_user_inv['Quantidade'].apply(extrair_numero_br)
                df_user_inv['PrecoAtual_Planilha'] = df_user_inv['PrecoAtual'].apply(extrair_numero_br)
                
                cotacoes_dict = obter_cotacoes()
                df_user_inv['PrecoLive'] = df_user_inv['Ativo'].map(cotacoes_dict)
                df_user_inv['PrecoLive'] = pd.to_numeric(df_user_inv['PrecoLive']).combine_first(df_user_inv['PrecoAtual_Planilha']).fillna(0)
                
                df_user_inv['MesAno'] = df_user_inv['DataCompra'].dt.strftime('%Y-%m')
                df_inv_agrupado = df_user_inv.groupby(['MesAno', 'Ativo']).agg({
                    'Quantidade': 'sum',
                    'PrecoLive': 'first'
                }).reset_index()
            else:
                df_inv_agrupado = pd.DataFrame(columns=['MesAno', 'Ativo', 'Quantidade', 'PrecoLive'])
        else:
            df_inv_agrupado = pd.DataFrame(columns=['MesAno', 'Ativo', 'Quantidade', 'PrecoLive'])

        # Se não tiver dados de nenhum dos dois, encerra para não dar erro
        if df_dep_agrupado.empty and df_inv_agrupado.empty:
            st.info("Registre depósitos e compras na aba '📝 Lançamentos' para ver a evolução do seu patrimônio ao longo do tempo.")
            return

        # --- 3. CRIAR A LINHA DO TEMPO CONTÍNUA (SEM BURACOS) ---
        meses_dep = df_dep_agrupado['MesAno'].unique().tolist() if not df_dep_agrupado.empty else []
        meses_inv = df_inv_agrupado['MesAno'].unique().tolist() if not df_inv_agrupado.empty else []
        
        todos_meses = sorted(list(set(meses_dep + meses_inv)))
        mes_inicial = todos_meses[0]
        mes_atual = datetime.now().strftime('%Y-%m')
        
        # Garante que vai do primeiro mês de registro até o mês atual sem pular NENHUM mês!
        range_meses = pd.date_range(start=f"{mes_inicial}-01", end=f"{mes_atual}-01", freq='MS').strftime('%Y-%m').tolist()
        df_timeline = pd.DataFrame({'MesAno': range_meses})
        
        # --- 4. CALCULAR DEPÓSITOS ACUMULADOS ---
        # Junta o calendário com os depósitos (onde não teve depósito fica nulo)
        df_timeline = pd.merge(df_timeline, df_dep_agrupado, on='MesAno', how='left')
        
        # Troca os "nulos" por Zero
        df_timeline['Valor'] = df_timeline['Valor'].fillna(0)
        
        # A MÁGICA: cumsum() faz a soma escadinha (Mês 1 + Mês 2 + Mês 3...)
        df_timeline['TotalAportado'] = df_timeline['Valor'].cumsum()

        # --- 5. CALCULAR VALOR DE MERCADO ACUMULADO ---
        linha_mercado = []
        estoque_ativos = {} # Guarda a quantidade de cotas que você acumulou na vida
        
        for mes in range_meses:
            # Pega as compras feitas especificamente neste mês
            compras_mes = df_inv_agrupado[df_inv_agrupado['MesAno'] == mes]
            
            for _, row in compras_mes.iterrows():
                ativo = row['Ativo']
                if ativo not in estoque_ativos:
                    estoque_ativos[ativo] = {'qtd': 0.0, 'preco_live': row['PrecoLive']}
                
                estoque_ativos[ativo]['qtd'] += row['Quantidade']
                estoque_ativos[ativo]['preco_live'] = row['PrecoLive'] # Atualiza cotação
            
            # Multiplica todo o seu estoque acumulado ATÉ ESSE MÊS pelo preço da aba Cotacao
            valor_mercado_mes = sum(d['qtd'] * d['preco_live'] for d in estoque_ativos.values())
            linha_mercado.append(valor_mercado_mes)
            
        df_timeline['ValorMercado'] = linha_mercado
        
        # --- 6. FORMATAÇÃO FINAL PARA EXIBIÇÃO ---
        df_timeline['MesExibicao'] = pd.to_datetime(df_timeline['MesAno'], format='%Y-%m').dt.strftime('%m/%Y')
        df_timeline.loc[df_timeline.index[-1], 'MesExibicao'] = "Hoje"

        # --- 7. CARDS DE RESUMO ---
        live_aportado = df_timeline.iloc[-1]['TotalAportado']
        live_atual = df_timeline.iloc[-1]['ValorMercado']
        
        lucro_rs = live_atual - live_aportado
        lucro_pct = (lucro_rs / live_aportado * 100) if live_aportado > 0 else 0

        col1, col2, col3 = st.columns(3)
        col1.metric("Dinheiro do Bolso (Depósitos)", formata_br(live_aportado))
        col2.metric("Saldo Atual (Mercado)", formata_br(live_atual))
        col3.metric("Rentabilidade Real", formata_br(lucro_rs), f"{lucro_pct:+.2f}%".replace('.', ','))
        
        st.markdown("---")

        # --- 8. GRÁFICO PLOTLY ---
        fig = go.Figure()

        # Linha 1: Depósitos Acumulados
        fig.add_trace(go.Scatter(
            x=df_timeline['MesExibicao'], 
            y=df_timeline['TotalAportado'],
            mode='lines+markers', 
            name='Dinheiro Aportado',
            line=dict(color='#8c92ac', width=3, dash='dot'),
            fill='tozeroy', 
            fillcolor='rgba(140, 146, 172, 0.1)',
            hovertemplate="Aportado Acumulado: R$ %{y:,.2f}<extra></extra>"
        ))

        # Linha 2: Valor de Mercado Corrigido
        cor_saldo = '#00cc96' if live_atual >= live_aportado else '#ef553b'
        cor_area = 'rgba(0, 204, 150, 0.25)' if live_atual >= live_aportado else 'rgba(239, 85, 59, 0.25)'
        
        fig.add_trace(go.Scatter(
            x=df_timeline['MesExibicao'], 
            y=df_timeline['ValorMercado'],
            mode='lines+markers', 
            name='Valor de Mercado',
            line=dict(color=cor_saldo, width=3),
            fill='tonexty', 
            fillcolor=cor_area,
            hovertemplate="Valor de Mercado: R$ %{y:,.2f}<extra></extra>"
        ))

        fig.update_layout(
            height=450, 
            margin=dict(l=0, r=0, t=30, b=0),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode="x unified", 
            xaxis=dict(showgrid=False), 
            yaxis=dict(tickformat=",.2f")
        )
        
        st.plotly_chart(fig, use_container_width=True)
