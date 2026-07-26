import streamlit as st
import pandas as pd
from utils import ler_planilha

# Função auxiliar para formatar moeda no padrão BR
def formata_br(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def render():
    st.title("🎯 Guia de Aportes Inteligente")
    st.markdown("Descubra exatamente onde alocar seu dinheiro para manter a carteira alinhada aos seus objetivos.")

    # --- TELA DE INPUT ---
    st.markdown("### 1. Dados do Aporte")
    col1, col2 = st.columns([1, 1], gap="large")
    
    with col1:
        valor_aporte = st.number_input("💸 Valor do Aporte (R$)", min_value=0.0, value=1000.0, step=100.0)
    
    with col2:
        num_compras = st.pills(
            "Dividir em até quantas compras?", 
            options=[1, 2, 3], 
            default=1
        )

    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("🚀 Calcular Onde Aportar", use_container_width=True):
        if valor_aporte <= 0:
            st.warning("Insira um valor maior que zero para o aporte.")
            return

        email = st.session_state.email

        # --- 2. CARREGAR DADOS ---
        with st.spinner("Analisando sua carteira e metas..."):
            df_conf = ler_planilha("Configuracao")
            df_ativos_conf = ler_planilha("Ativos_Config")
            df_invest = ler_planilha("Investimentos")

            # Validações de segurança
            if df_conf.empty or email not in df_conf['Email'].astype(str).str.strip().str.lower().values:
                st.error("⚠️ Você ainda não definiu suas Metas de Alocação Macro. Vá em Configuração da Carteira.")
                return
            if df_ativos_conf.empty or email not in df_ativos_conf['Email'].astype(str).str.strip().str.lower().values:
                st.error("⚠️ Você ainda não cadastrou seus Ativos e Pesos. Vá em Configuração da Carteira.")
                return

            # --- 3. PROCESSAR METAS MACRO (Categorias) ---
            df_conf['Email'] = df_conf['Email'].astype(str).str.strip().str.lower()
            user_conf = df_conf[df_conf['Email'] == email].iloc[0].to_dict()

            peso_rv = float(user_conf.get('RV', 50)) / 100.0
            peso_br = float(user_conf.get('RV_Brasil', 50)) / 100.0
            peso_ex = float(user_conf.get('RV_Exterior', 50)) / 100.0

            cat_targets = {
                "Renda Fixa": float(user_conf.get('RF', 50)) / 100.0,
                "Ações": peso_rv * peso_br * (float(user_conf.get('BR_Acoes', 50)) / 100.0),
                "FIIs": peso_rv * peso_br * (float(user_conf.get('BR_FIIs', 50)) / 100.0),
                "Stocks": peso_rv * peso_ex * (float(user_conf.get('EX_Stocks', 40)) / 100.0),
                "REITs": peso_rv * peso_ex * (float(user_conf.get('EX_REITs', 30)) / 100.0),
                "ETFs": peso_rv * peso_ex * (float(user_conf.get('EX_ETFs', 30)) / 100.0),
            }

            # --- 4. PROCESSAR METAS MICRO (Ativos) ---
            df_ativos_conf['Email'] = df_ativos_conf['Email'].astype(str).str.strip().str.lower()
            df_user_ativos = df_ativos_conf[df_ativos_conf['Email'] == email].copy()

            ativos_alvos = []
            for _, row in df_user_ativos.iterrows():
                cat = str(row['Categoria']).strip()
                ativo = str(row['Ativo']).strip().upper()
                # Compatibilidade com nome da coluna ('Peso' ou 'Peso (%)')
                val_peso = row.get('Peso') if pd.notna(row.get('Peso')) else row.get('Peso (%)', 0)
                peso_interno = float(val_peso) / 100.0
                
                # O Peso Global do ativo na carteira é (Peso da Categoria * Peso Interno do Ativo)
                peso_global = cat_targets.get(cat, 0) * peso_interno
                
                if ativo and ativo != "NAN":
                    ativos_alvos.append({'Categoria': cat, 'Ativo': ativo, 'PesoGlobal': peso_global})

            df_alvos = pd.DataFrame(ativos_alvos)

            # --- 5. LER CARTEIRA ATUAL ---
            df_carteira = pd.DataFrame(columns=['Categoria', 'Ativo', 'TotalAtual', 'PrecoAtual'])
            if not df_invest.empty:
                df_invest['Email'] = df_invest['Email'].astype(str).str.strip().str.lower()
                df_user_invest = df_invest[df_invest['Email'] == email].copy()
                if not df_user_invest.empty:
                    df_user_invest['Ativo'] = df_user_invest['Ativo'].astype(str).str.strip().str.upper()
                    df_user_invest['Categoria'] = df_user_invest['Categoria'].astype(str).str.strip()
                    df_user_invest['Quantidade'] = pd.to_numeric(df_user_invest['Quantidade'], errors='coerce').fillna(0)
                    df_user_invest['PrecoAtual'] = pd.to_numeric(df_user_invest['PrecoAtual'], errors='coerce').fillna(0)
                    df_user_invest['TotalAtual'] = df_user_invest['Quantidade'] * df_user_invest['PrecoAtual']

                    # Agrupa caso a pessoa tenha lançado o mesmo ativo em várias linhas
                    df_carteira = df_user_invest.groupby(['Categoria', 'Ativo']).agg({
                        'TotalAtual': 'sum',
                        'PrecoAtual': 'last' # Pega o preço mais recente
                    }).reset_index()

            # --- 6. CRUZAMENTO E CÁLCULO DE GAPS ---
            total_atual = df_carteira['TotalAtual'].sum() if not df_carteira.empty else 0
            total_futuro = total_atual + valor_aporte # A base de cálculo inclui o novo dinheiro

            # Calcula quanto cada ativo DEVERIA ter em R$ no cenário ideal
            df_alvos['ValorAlvo'] = df_alvos['PesoGlobal'] * total_futuro

            df_calc = pd.merge(df_alvos, df_carteira, on=['Categoria', 'Ativo'], how='left')
            df_calc['TotalAtual'] = df_calc['TotalAtual'].fillna(0)
            df_calc['PrecoAtual'] = df_calc['PrecoAtual'].fillna(0)
            
            # Descobre a distância (Gap) entre o Alvo e o Atual
            df_calc['Falta_Comprar'] = df_calc['ValorAlvo'] - df_calc['TotalAtual']

            # --- 7. ALGORITMO DE DISTRIBUIÇÃO (Regra de Negócio) ---
            aporte_restante = valor_aporte
            compras = []

            for i in range(num_compras):
                if aporte_restante <= 0.01:
                    break # Dinheiro acabou

                # Avalia dinamicamente as categorias que mais precisam de dinheiro
                cat_gaps = df_calc.groupby('Categoria')['Falta_Comprar'].sum().sort_values(ascending=False)
                top_cat = cat_gaps.index[0]
                max_cat_gap = cat_gaps.iloc[0]

                if max_cat_gap <= 0.01:
                    # Se tudo está perfeitamente alinhado (Falta_Comprar zerou ou negativo),
                    # compramos o ativo com maior peso na estratégia global
                    df_calc.sort_values(by='PesoGlobal', ascending=False, inplace=True)
                    top_ativo_row = df_calc.iloc[0]
                    valor_alocado = aporte_restante # Pode investir o resto sem medo
                else:
                    # Dentro da categoria mais defasada, pega o ativo mais defasado
                    ativos_top_cat = df_calc[df_calc['Categoria'] == top_cat].sort_values(by='Falta_Comprar', ascending=False)
                    top_ativo_row = ativos_top_cat.iloc[0]
                    falta_ativo = top_ativo_row['Falta_Comprar']

                    # O sistema NÃO supera a meta do ativo se o aporte for muito grande
                    if falta_ativo > 0:
                        valor_alocado = min(aporte_restante, falta_ativo)
                    else:
                        valor_alocado = aporte_restante # Margem de segurança

                # Extrai dados da linha selecionada
                idx = top_ativo_row.name
                top_ativo = top_ativo_row['Ativo']
                preco_atual = top_ativo_row['PrecoAtual']
                categoria = top_ativo_row['Categoria']

                # Calcula quantidade estimada se houver preço cadastrado
                qtd = valor_alocado / preco_atual if preco_atual > 0 else 0

                compras.append({
                    'Ordem': i + 1,
                    'Categoria': categoria,
                    'Ativo': top_ativo,
                    'Valor': valor_alocado,
                    'PrecoRef': preco_atual,
                    'Qtd': qtd
                })

                # Atualiza a carteira "fictícia" para o próximo ciclo do loop (Simulando a compra)
                df_calc.loc[idx, 'Falta_Comprar'] -= valor_alocado
                df_calc.loc[idx, 'TotalAtual'] += valor_alocado
                aporte_restante -= valor_alocado

        # --- 8. RENDERIZAÇÃO DO RESULTADO ---
        st.markdown("---")
        st.subheader("🛒 Suas Ordens de Compra Sugeridas")
        st.markdown("Baseado na distância entre sua carteira atual e seu objetivo, execute estas compras:")

        if compras:
            for c in compras:
                with st.container():
                    st.markdown(f"#### {c['Ordem']}º Compra: `{c['Ativo']}` <span style='font-size:0.8em; color:gray;'>({c['Categoria']})</span>", unsafe_allow_html=True)
                    
                    col_r1, col_r2, col_r3 = st.columns(3)
                    col_r1.metric("Alocar (R$)", formata_br(c['Valor']))
                    
                    if c['PrecoRef'] > 0:
                        # Se for Renda Fixa costuma ser fração, Ações e FIIs não, mas mostramos precisão
                        col_r2.metric("Qtd Sugerida", f"{c['Qtd']:,.2f}".replace('.', ','))
                        col_r3.metric("Preço Atual", formata_br(c['PrecoRef']))
                    else:
                        col_r2.metric("Qtd Sugerida", "Ativo Novo (Indefinido)")
                        col_r3.metric("Preço Atual", "Não cadastrado")
                        
                    st.markdown("<hr style='margin: 0.5em 0; border: 0; border-top: 1px dashed #ddd;'>", unsafe_allow_html=True)

            if aporte_restante > 0.05:
                st.info(f"💰 **Sobrou {formata_br(aporte_restante)}** do seu aporte. O algoritmo limitou a alocação para não ultrapassar os tetos percentuais que você definiu na meta. Aumente o número de compras ou compre por conta própria.")
            else:
                st.success("✅ Todo o valor do seu aporte foi distribuído com sucesso!")
        else:
            st.info("Nenhuma sugestão gerada.")
