import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from utils import ler_planilha, obter_cotacoes, extrair_numero_br, formata_br

def render():
    st.title("📈 Evolução Real do Patrimônio")
    st.markdown("Compare o **Dinheiro Novo Aportado** (Depositos) com o **Valor de Mercado**. A diferença é a sua Rentabilidade Real (Valorização + Dividendos).")

    with st.spinner("Construindo linha do tempo da sua carteira..."):
        # 1. LER DEPÓSITOS (Dinheiro do Bolso)
        df_dep = ler_planilha("Depositos")
        df_dep_mensal = pd.DataFrame(columns=['MesAno_Sort', 'Valor'])
        
        if not df_dep.empty and 'Email' in df_dep.columns:
            df_dep['Email'] = df_dep['Email'].astype(str).str.strip().str.lower()
            df_user_dep = df_dep[df_dep['Email'] == st.session_state.email].copy()
            if not df_user_dep.empty:
                df_user_dep['Data'] = pd.to_datetime(df_user_dep['Data'], dayfirst=True, errors='coerce')
                df_user_dep['Valor'] = df_user_dep['Valor'].apply(extrair_numero_br)
                df_user_dep = df_user_dep.dropna(subset=['Data'])
                df_user_dep['MesAno_Sort'] = df_user_dep['Data'].dt.strftime('%Y-%m')
                df_dep_mensal = df_user_dep.groupby('MesAno_Sort')['Valor'].sum().reset_index()

        # 2. LER INVESTIMENTOS (Compras de Ativos)
        df_invest = ler_planilha("Investimentos")
        df_inv_mensal = pd.DataFrame()
        
        if not df_invest.empty and 'Email' in df_invest.columns:
            df_invest['Email'] = df_invest['Email'].astype(str).str.strip().str.lower()
            df_user_invest = df_invest[df_invest['Email'] == st.session_state.email].copy()
            
            if not df_user_invest.empty and 'DataCompra' in df_user_invest.columns:
                df_user_invest['Ativo'] = df_user_invest['Ativo'].astype(str).str.strip().str.upper()
                df_user_invest['Quantidade'] = df_user_invest['Quantidade'].apply(extrair_numero_br)
                df_user_invest['PrecoAtual_Planilha'] = df_user_invest['PrecoAtual'].apply(extrair_numero_br)
                
                # Cotações ao Vivo
                cotacoes_dict = obter_cotacoes()
                df_user_invest['PrecoLive'] = df_user_invest['Ativo'].map(cotacoes_dict)
                df_user_invest['PrecoLive'] = pd.to_numeric(df_user_invest['PrecoLive']).combine_first(df_user_invest['PrecoAtual_Planilha']).fillna(0)
                
                df_user_invest['DataCompra'] = pd.to_datetime(df_user_invest['DataCompra'], dayfirst=True, errors='coerce')
                df_user_invest = df_user_invest.dropna(subset=['DataCompra'])
                df_user_invest['MesAno_Sort'] = df_user_invest['DataCompra'].dt.strftime('%Y-%m')
                
                df_inv_mensal = df_user_invest.groupby(['MesAno_Sort', 'Ativo']).agg({
                    'Quantidade': 'sum',
                    'PrecoLive': 'first'
                }).reset_index()

        # Se ambos estiverem vazios, não tem gráfico
        if df_dep_mensal.empty and df_inv_mensal.empty:
            st.info("Registre depósitos e compras na aba '📝 Lançamentos' para ver a evolução.")
            return

        # 3. UNIFICAR A LINHA DO TEMPO (Mescla meses de depósito e de compra)
        meses_dep = df_dep_mensal['MesAno_Sort'].unique().tolist() if not df_dep_mensal.empty else []
        meses_inv = df_inv_mensal['MesAno_Sort'].unique().tolist() if not df_inv_mensal.empty else []
        todos_meses = sorted(list(set(meses_dep + meses_inv)))

        linha_tempo = []
        acumulado_ativos = {}
        total_depositado_acumulado = 0.0

        for mes in todos_meses:
            # Soma depósitos do mês
            if not df_dep_mensal.empty:
                dep_mes = df_dep_mensal[df_dep_mensal['MesAno_Sort'] == mes]['Valor'].sum()
                total_depositado_acumulado += dep_mes
            
            # Soma compras do mês (Acúmulo de Cotas)
            if not df_inv_mensal.empty:
                compras_mes = df_inv_mensal[df_inv_mensal['MesAno_Sort'] == mes]
                for _, row in compras_mes.iterrows():
                    ativo = row['Ativo']
                    if ativo not in acumulado_ativos:
                        acumulado_ativos[ativo] = {'qtd': 0.0, 'preco_live': row['PrecoLive']}
                    acumulado_ativos[ativo]['qtd'] += row['Quantidade']
                    acumulado_ativos[ativo]['preco_live'] = row['PrecoLive'] # Atualiza o último preço

            # Valor de mercado é Quantidade Total Acumulada * Preço Hoje
            total_mercado_mes = sum(dados['qtd'] * dados['preco_live'] for dados in acumulado_ativos.values())

            linha_tempo.append({
                'MesAno': mes,
                'TotalAportado': total_depositado_acumulado,
                'ValorMercado': total_mercado_mes
            })

        df_timeline = pd.DataFrame(linha_tempo)
        df_timeline['MesExibicao'] = pd.to_datetime(df_timeline['MesAno'], format='%Y-%m').dt.strftime('%m/%Y')

        # Adiciona "Hoje" se for necessário
        mes_atual_str = datetime.now().strftime('%Y-%m')
        if todos_meses[-1] != mes_atual_str:
            df_timeline.loc[len(df_timeline)] = {
                'MesAno': mes_atual_str,
                'TotalAportado': df_timeline.iloc[-1]['TotalAportado'],
                'ValorMercado': df_timeline.iloc[-1]['ValorMercado'],
                'MesExibicao': "Hoje"
            }
        else:
            df_timeline.loc[df_timeline.index[-1], 'MesExibicao'] = "Hoje"

        # --- 4. CARDS DE RESUMO ---
        live_aportado = df_timeline.iloc[-1]['TotalAportado']
        live_atual = df_timeline.iloc[-1]['ValorMercado']
        
        lucro_rs = live_atual - live_aportado
        lucro_pct = (lucro_rs / live_aportado * 100) if live_aportado > 0 else 0

        col1, col2, col3 = st.columns(3)
        col1.metric("Dinheiro do Bolso (Depósitos)", formata_br(live_aportado))
        col2.metric("Saldo Atual (Mercado)", formata_br(live_atual))
        col3.metric("Rentabilidade Real", formata_br(lucro_rs), f"{lucro_pct:+.2f}%".replace('.', ','))
        
        st.markdown("---")

        # --- 5. GRÁFICO PLOTLY ---
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=df_timeline['MesExibicao'], y=df_timeline['TotalAportado'],
            mode='lines+markers', name='Dinheiro Aportado',
            line=dict(color='#8c92ac', width=3, dash='dot'),
            fill='tozeroy', fillcolor='rgba(140, 146, 172, 0.1)',
            hovertemplate="Aportado Acumulado: R$ %{y:,.2f}<extra></extra>"
        ))

        cor_saldo = '#00cc96' if live_atual >= live_aportado else '#ef553b'
        cor_area = 'rgba(0, 204, 150, 0.25)' if live_atual >= live_aportado else 'rgba(239, 85, 59, 0.25)'
        
        fig.add_trace(go.Scatter(
            x=df_timeline['MesExibicao'], y=df_timeline['ValorMercado'],
            mode='lines+markers', name='Valor Corrigido de Mercado',
            line=dict(color=cor_saldo, width=3),
            fill='tonexty', fillcolor=cor_area,
            hovertemplate="Corrigido Mercado: R$ %{y:,.2f}<extra></extra>"
        ))

        fig.update_layout(
            height=450, margin=dict(l=0, r=0, t=30, b=0),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode="x unified", xaxis=dict(showgrid=False), yaxis=dict(tickformat=",.2f")
        )
        
        st.plotly_chart(fig, use_container_width=True)
