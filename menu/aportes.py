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

                    df_carteira = df_user_invest.groupby(['Categoria', 'Ativo']).agg({
                        'TotalAtual': 'sum',
                        'PrecoAtual': 'last'
                    }).reset_index()

            # --- 6. CRUZAMENTO E CÁLCULO DE GAPS ---
            total_atual = df_carteira['TotalAtual'].sum() if not df_carteira.empty else 0
            total_futuro = total_atual + valor_aporte # A meta é traçada projetando o dinheiro novo
            
            df_calc = pd.merge(df_alvos, df_carteira, on=['Categoria', 'Ativo'], how='left')
            df_calc['TotalAtual'] = df_calc['TotalAtual'].fillna(0)
            df_calc['PrecoAtual'] = df_calc['PrecoAtual'].fillna(0)
            
            # Guardamos o total original para calcular com precisão a "Qtd Faltante" depois
            df_calc['TotalAtual_Original'] = df_calc['TotalAtual'].copy()
            df_calc['ValorAlvo'] = df_calc['PesoGlobal'] * total_futuro
            df_calc['Falta_Comprar'] = df_calc['ValorAlvo'] - df_calc['TotalAtual']

            # --- 7. ALGORITMO DE DISTRIBUIÇÃO EXATA (Dividido por Ativos Diferentes) ---
            aporte_restante = valor_aporte
            compras = []
            ativos_comprados = [] # Lista para garantir que não vamos repetir o mesmo ativo

            for i in range(num_compras):
                if aporte_restante <= 0.01:
                    break # Dinheiro acabou

                # Filtra apenas os ativos que AINDA NÃO foram escolhidos nesta simulação
                df_disponivel = df_calc[~df_calc['Ativo'].isin(ativos_comprados)]
                if df_disponivel.empty:
                    break

                # Avalia qual categoria disponível está precisando de mais dinheiro
                cat_gaps = df_disponivel.groupby('Categoria')['Falta_Comprar'].sum().sort_values(ascending=False)
                top_cat = cat_gaps.index[0]
                max_cat_gap = cat_gaps.iloc[0]

                if max_cat_gap <= 0.01:
                    # Se todos os ativos disponíveis já bateram a meta, compra o com maior peso global
                    df_disponivel = df_disponivel.sort_values(by='PesoGlobal', ascending=False)
                    top_ativo_row = df_disponivel.iloc[0]
                    falta_ativo = aporte_restante # Sem limite, pois é compra forçada
                else:
                    # Pega o ativo mais defasado da categoria mais defasada
                    ativos_top_cat = df_disponivel[df_disponivel['Categoria'] == top_cat].sort_values(by='Falta_Comprar', ascending=False)
                    top_ativo_row = ativos_top_cat.iloc[0]
                    falta_ativo = top_ativo_row['Falta_Comprar']

                # Divide o dinheiro que sobrou pelas fatias de compra que faltam
                compras_restantes = num_compras - i
                valor_parcela = aporte_restante / compras_restantes

                # Limita a compra ao que o ativo precisa (para não ultrapassar o teto do objetivo)
                if falta_ativo > 0:
                    valor_alocado = min(valor_parcela, falta_ativo)
                else:
                    valor_alocado = valor_parcela 

                # Extrai os dados para montar o relatório
                idx = top_ativo_row.name
                top_ativo = top_ativo_row['Ativo']
                preco_atual = top_ativo_row['PrecoAtual']
                categoria = top_ativo_row['Categoria']
                valor_alvo = top_ativo_row['ValorAlvo']
                total_atual_orig = top_ativo_row['TotalAtual_Original']

                is_rv = categoria in ["Ações", "FIIs", "Stocks", "REITs", "ETFs"]
                is_br = categoria in ["Ações", "FIIs"]

                qtd_sugerida_str = "-"
                qtd_faltante_str = "-"

                # Cálculos de Quantidade se for Renda Variável e tiver o preço cadastrado
                if is_rv and preco_atual > 0:
                    qtd_sugerida = valor_alocado / preco_atual
                    qtd_alvo = valor_alvo / preco_atual
                    qtd_atual = total_atual_orig / preco_atual
                    qtd_faltante_total = max(0, qtd_alvo - qtd_atual)
                    
                    if is_br:
                        # BR costuma ser número inteiro (1 cota, 10 ações)
                        qtd_sugerida_str = f"{int(qtd_sugerida)} un"
                        qtd_faltante_str = f"{int(qtd_faltante_total)} un"
                    else:
                        # Exterior (Stocks, ETFs) permite compra fracionada
                        qtd_sugerida_str = f"{qtd_sugerida:.4f} un".replace('.', ',')
                        qtd_faltante_str = f"{qtd_faltante_total:.4f} un".replace('.', ',')

                compras.append({
                    'Ordem': i + 1,
                    'Categoria': categoria,
                    'Ativo': top_ativo,
                    'Valor': valor_alocado,
                    'PrecoRef': preco_atual,
                    'Qtd_Sugerida': qtd_sugerida_str,
                    'Qtd_Faltante': qtd_faltante_str,
                    'Is_RV': is_rv
                })

                # Atualiza a carteira fictícia e a lista de bloqueio para o próximo ciclo
                df_calc.loc[idx, 'Falta_Comprar'] -= valor_alocado
                df_calc.loc[idx, 'TotalAtual'] += valor_alocado
                ativos_comprados.append(top_ativo)
                aporte_restante -= valor_alocado

        # --- 8. RENDERIZAÇÃO DO RESULTADO ---
        st.markdown("---")
        st.subheader("🛒 Suas Ordens de Compra Sugeridas")
        st.markdown("O algoritmo distribuiu seu aporte visando equilibrar as defasagens da carteira.")

        if compras:
            for c in compras:
                with st.container():
                    st.markdown(f"#### {c['Ordem']}º Compra: `{c['Ativo']}` <span style='font-size:0.8em; color:gray;'>({c['Categoria']})</span>", unsafe_allow_html=True)
                    
                    if c['Is_RV']:
                        col_r1, col_r2, col_r3, col_r4 = st.columns(4)
                        col_r1.metric("Alocar (R$)", formata_br(c['Valor']))
                        col_r2.metric("Cotação Atual", formata_br(c['PrecoRef']) if c['PrecoRef'] > 0 else "Não cadastrado")
                        col_r3.metric("Comprar (Qtd)", c['Qtd_Sugerida'] if c['PrecoRef'] > 0 else "N/A")
                        col_r4.metric("Falta p/ Meta", c['Qtd_Faltante'] if c['PrecoRef'] > 0 else "N/A")
                    else:
                        col_r1, col_r2, col_r3 = st.columns(3)
                        col_r1.metric("Alocar (R$)", formata_br(c['Valor']))
                        col_r2.metric("Preço Atual", formata_br(c['PrecoRef']) if c['PrecoRef'] > 0 else "N/A")
                        col_r3.metric("Status", "Renda Fixa")
                        
                    st.markdown("<hr style='margin: 0.5em 0; border: 0; border-top: 1px dashed #ddd;'>", unsafe_allow_html=True)

            if aporte_restante > 0.05:
                st.info(f"💰 **Sobrou {formata_br(aporte_restante)}** do seu aporte. O algoritmo evitou investir isso para não estourar o limite percentual dos seus ativos. Você pode guardar esse saldo ou aportar manualmente.")
            else:
                st.success("✅ Todo o valor do seu aporte foi distribuído de forma otimizada!")
        else:
            st.info("Nenhuma sugestão gerada.")
