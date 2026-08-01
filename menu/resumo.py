import streamlit as st
import pandas as pd
import plotly.express as px
from utils import ler_planilha, obter_cotacoes, extrair_numero_br, formata_br

def render():
    st.title("📊 Resumo Geral da Carteira")
    
    df_invest = ler_planilha("Investimentos")
    if not df_invest.empty:
        df_invest['Email'] = df_invest['Email'].astype(str).str.strip().str.lower()
        dados_usuario = df_invest[df_invest['Email'] == st.session_state.email].copy()
        
        if not dados_usuario.empty:
            dados_usuario['Ativo'] = dados_usuario['Ativo'].astype(str).str.strip().str.upper()
            dados_usuario['Categoria'] = dados_usuario['Categoria'].astype(str).str.strip()
            
            # Aplica a inteligência de conversão brasileira APENAS nas colunas que existem
            dados_usuario['Quantidade'] = dados_usuario['Quantidade'].apply(extrair_numero_br)
            dados_usuario['PrecoMedio'] = dados_usuario['PrecoMedio'].apply(extrair_numero_br)
            
            # --- CORREÇÃO: CRIA O PREÇO ATUAL DIRETO DA ABA COTAÇÃO COM FALLBACK DE SEGURANÇA ---
            cotacoes_dict = obter_cotacoes()
            
            # Mapeia o nome do ativo para o preço ao vivo. Se não encontrar, preenche com zero.
            dados_usuario['PrecoLive'] = dados_usuario['Ativo'].map(cotacoes_dict).fillna(0.0)
            
            # REGRA MESTRA: Se achou o preço online, usa. Se não achou (ex: CDB), usa o Preço Médio (Custo).
            dados_usuario['PrecoAtual'] = dados_usuario.apply(
                lambda row: row['PrecoLive'] if row['PrecoLive'] > 0 else row['PrecoMedio'], axis=1
            )
            # ------------------------------------------------------------
            
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
            
            # --- CORREÇÃO: PUXA O TOTAL INVESTIDO REAL (DINHEIRO DEPOSITADO) ---
            df_depositos = ler_planilha("Depositos")
            total_carteira_investido = 0.0
            
            if not df_depositos.empty and 'Email' in df_depositos.columns:
                df_depositos['Email'] = df_depositos['Email'].astype(str).str.strip().str.lower()
                meus_depositos = df_depositos[df_depositos['Email'] == st.session_state.email].copy()
                
                if not meus_depositos.empty:
                    # Usa a função nativa do sistema para evitar erros de casa decimal
                    meus_depositos['Valor'] = meus_depositos['Valor'].apply(extrair_numero_br)
                    total_carteira_investido = meus_depositos['Valor'].sum()
            # -------------------------------------------------------------------
            
            total_carteira_atual = carteira_agrupada['TotalAtual'].sum()
            
            # A Evolução agora compara o Patrimônio Atual contra o Dinheiro que saiu do seu bolso
            evolucao_total_carteira = ((total_carteira_atual - total_carteira_investido) / total_carteira_investido if total_carteira_investido > 0 else 0) * 100
            
            col_c1, col_c2, col_c3 = st.columns(3)
            # Aplica a formatação BR visual nos grandes números
            col_c1.metric("Total Investido", formata_br(total_carteira_investido))
            col_c2.metric("Valor Atual", formata_br(total_carteira_atual))
            
            # Formata a porcentagem trocando o ponto pela vírgula (ex: +2,50%)
            col_c3.metric("Evolução", f"{evolucao_total_carteira:+.2f}%".replace('.', ','))
            
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
                        
                        # Formata a tabela no padrão brasileiro
                        df_exibicao['Quantidade'] = df_exibicao['Quantidade'].map('{:,.4f}'.format).str.replace(',', 'X').str.replace('.', ',').str.replace('X', '.').str.rstrip('0').str.rstrip(',')
                        df_exibicao['PrecoMedio'] = df_exibicao['PrecoMedio'].apply(formata_br)
                        df_exibicao['PrecoAtual'] = df_exibicao['PrecoAtual'].apply(formata_br)
                        df_exibicao['TotalAtual'] = df_exibicao['TotalAtual'].apply(formata_br)
                        df_exibicao['EvolucaoPct'] = df_exibicao['EvolucaoPct'].map('{:+.2f}%'.format).str.replace('.', ',')
                        
                        st.dataframe(df_exibicao, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum investimento encontrado.")
    else:
        st.error("Erro ao ler aba 'Investimentos'.")
