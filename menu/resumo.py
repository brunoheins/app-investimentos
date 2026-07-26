import streamlit as st
import pandas as pd
import plotly.express as px
from utils import ler_planilha, obter_cotacoes

def render():
    st.title("📊 Resumo Geral da Carteira")
    
    df_invest = ler_planilha("Investimentos")
    if not df_invest.empty:
        df_invest['Email'] = df_invest['Email'].astype(str).str.strip().str.lower()
        dados_usuario = df_invest[df_invest['Email'] == st.session_state.email].copy()
        
        if not dados_usuario.empty:
            dados_usuario['Ativo'] = dados_usuario['Ativo'].astype(str).str.strip().str.upper()
            dados_usuario['Categoria'] = dados_usuario['Categoria'].astype(str).str.strip()
            
            dados_usuario['Quantidade'] = pd.to_numeric(dados_usuario['Quantidade'], errors='coerce').fillna(0)
            dados_usuario['PrecoMedio'] = pd.to_numeric(dados_usuario['PrecoMedio'], errors='coerce').fillna(0)
            dados_usuario['PrecoAtual'] = pd.to_numeric(dados_usuario['PrecoAtual'], errors='coerce').fillna(0)

            # --- NOVO: BUSCANDO COTAÇÕES AO VIVO ---
            cotacoes_dict = obter_cotacoes()
            dados_usuario['PrecoCotacao'] = dados_usuario['Ativo'].map(cotacoes_dict)
            # Combina: usa a cotação da aba "Cotacao", se não achar, usa o PrecoAtual antigo, se não, 0.
            dados_usuario['PrecoAtual'] = pd.to_numeric(dados_usuario['PrecoCotacao']).combine_first(dados_usuario['PrecoAtual']).fillna(0)
            # --------------------------------------

            dados_usuario['TotalInvestido'] = dados_usuario['Quantidade'] * dados_usuario['PrecoMedio']
            dados_usuario['TotalAtual'] = dados_usuario['Quantidade'] * dados_usuario['PrecoAtual']
            
            carteira_agrupada = dados_usuario.groupby(['Ativo', 'Categoria']).agg({
                'Quantidade': 'sum',
                'TotalInvestido': 'sum',
                'TotalAtual': 'sum',
                'PrecoAtual': 'first'
            }).reset_index()
            
            carteira_agrupada['PrecoMedio'] = carteira_agrupada['TotalInvestido'] / carteira_agrupada['Quantidade'].replace(0, 1)
            carteira_agrupada.loc[carteira_agrupada['Quantidade'] == 0, 'PrecoMedio'] = 0
            
            carteira_agrupada['EvolucaoPct'] = ((carteira_agrupada['PrecoAtual'] - carteira_agrupada['PrecoMedio']) / carteira_agrupada['PrecoMedio'].replace(0, 1)) * 100
            carteira_agrupada.loc[carteira_agrupada['PrecoMedio'] == 0, 'EvolucaoPct'] = 0
            
            total_carteira_investido = carteira_agrupada['TotalInvestido'].sum()
            total_carteira_atual = carteira_agrupada['TotalAtual'].sum()
            evolucao_total_carteira = ((total_carteira_atual - total_carteira_investido) / total_carteira_investido if total_carteira_investido > 0 else 0) * 100
            
            col_c1, col_c2, col_c3 = st.columns(3)
            col_c1.metric("Total Investido", f"R$ {total_carteira_investido:,.2f}")
            col_c2.metric("Valor Atual", f"R$ {total_carteira_atual:,.2f}")
            col_c3.metric("Evolução", f"{evolucao_total_carteira:+.2f}%")
            
            st.markdown("---")
            
            col_grafico, col_tabelas = st.columns([1, 1.5], gap="large")
            
            with col_grafico:
                st.subheader("Distribuição")
                df_categoria = carteira_agrupada.groupby('Categoria')['TotalAtual'].sum().reset_index()
                fig = px.pie(df_categoria, values='TotalAtual', names='Categoria', hole=0.4)
                fig.update_traces(textinfo='label+percent')
                fig.update_layout(height=350, margin=dict(t=20, b=20, l=0, r=0))
                st.plotly_chart(fig, use_container_width=True)
            
            with col_tabelas:
                st.subheader("Detalhamento por Ativos")
                for cat in carteira_agrupada['Categoria'].unique():
                    with st.expander(f"📁 {cat}", expanded=False): 
                        df_exibicao = carteira_agrupada[carteira_agrupada['Categoria'] == cat][['Ativo', 'Quantidade', 'PrecoMedio', 'PrecoAtual', 'TotalAtual', 'EvolucaoPct']].copy()
                        df_exibicao['PrecoMedio'] = df_exibicao['PrecoMedio'].map('R$ {:,.2f}'.format)
                        df_exibicao['PrecoAtual'] = df_exibicao['PrecoAtual'].map('R$ {:,.2f}'.format)
                        df_exibicao['TotalAtual'] = df_exibicao['TotalAtual'].map('R$ {:,.2f}'.format)
                        df_exibicao['EvolucaoPct'] = df_exibicao['EvolucaoPct'].map('{:+.2f}%'.format)
                        st.dataframe(df_exibicao, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum investimento encontrado.")
    else:
        st.error("Erro ao ler aba 'Investimentos'.")
