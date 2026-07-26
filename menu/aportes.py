import streamlit as st
import pandas as pd
from utils import ler_planilha, obter_cotacoes, extrair_numero_br, formata_br

def normalizar_categoria(cat_str):
    """Tradutor Universal para agrupar tudo que significa a mesma coisa no mesmo balde."""
    c = str(cat_str).strip().upper()
    if c in ["IPCA", "RF", "RENDA FIXA", "TESOURO", "PREFIXADO", "CDI", "SELIC"]: return "Renda Fixa"
    if c in ["AÇÕES", "ACOES", "AÇÃO", "ACAO", "BRASIL"]: return "Ações"
    if c in ["FIIS", "FII", "FUNDO IMOBILIARIO", "FUNDOS IMOBILIÁRIOS"]: return "FIIs"
    if c in ["STOCKS", "STOCK", "EXTERIOR"]: return "Stocks"
    if c in ["REITS", "REIT"]: return "REITs"
    if c in ["ETFS", "ETF"]: return "ETFs"
    return str(cat_str).strip()

def motor_de_aportes(email, valor_aporte, num_compras):
    """Cérebro matemático: Calcula as recomendações de compra com base no patrimônio global."""
    df_conf = ler_planilha("Configuracao")
    df_ativos_conf = ler_planilha("Ativos_Config")
    df_invest = ler_planilha("Investimentos")

    if df_conf.empty or email not in df_conf['Email'].astype(str).str.strip().str.lower().values:
        return [], valor_aporte, "Metas de Alocação Macro não definidas na Configuração."
    if df_ativos_conf.empty or email not in df_ativos_conf['Email'].astype(str).str.strip().str.lower().values:
        return [], valor_aporte, "Ativos e Pesos não cadastrados na Configuração."

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

    df_ativos_conf['Email'] = df_ativos_conf['Email'].astype(str).str.strip().str.lower()
    df_user_ativos = df_ativos_conf[df_ativos_conf['Email'] == email].copy()

    # --- 1. LER ATIVOS ALVOS OFICIAIS ---
    ativos_alvos = []
    for _, row in df_user_ativos.iterrows():
        cat = normalizar_categoria(row['Categoria'])
        ativo = str(row['Ativo']).strip().upper()
        val_peso = row.get('Peso') if pd.notna(row.get('Peso')) else row.get('Peso (%)', 0)
        peso_global = cat_targets.get(cat, 0) * (float(val_peso) / 100.0)
        if ativo and ativo != "NAN":
            ativos_alvos.append({'Categoria': cat, 'Ativo': ativo, 'PesoGlobal': peso_global})

    df_alvos = pd.DataFrame(ativos_alvos)
    if not df_alvos.empty:
        df_alvos['Is_Target'] = True
    else:
        df_alvos = pd.DataFrame(columns=['Categoria', 'Ativo', 'PesoGlobal', 'Is_Target'])

    # --- 2. LER ESTOQUE DA CARTEIRA REAL ---
    df_carteira = pd.DataFrame(columns=['Categoria', 'Ativo', 'TotalAtual', 'PrecoAtual'])
    if not df_invest.empty and 'Email' in df_invest.columns:
        df_invest['Email'] = df_invest['Email'].astype(str).str.strip().str.lower()
        df_user_invest = df_invest[df_invest['Email'] == email].copy()
        
        if not df_user_invest.empty:
            df_user_invest['Ativo'] = df_user_invest['Ativo'].astype(str).str.strip().str.upper()
            df_user_invest['Categoria'] = df_user_invest['Categoria'].apply(normalizar_categoria)
            df_user_invest['Quantidade'] = df_user_invest['Quantidade'].apply(extrair_numero_br)
            
            cotacoes_dict = obter_cotacoes()
            df_user_invest['PrecoLive'] = df_user_invest['Ativo'].map(cotacoes_dict).fillna(0.0)
            df_user_invest['TotalAtual'] = df_user_invest['Quantidade'] * df_user_invest['PrecoLive']

            df_carteira = df_user_invest.groupby(['Categoria', 'Ativo']).agg({
                'TotalAtual': 'sum',
                'PrecoLive': 'last'
            }).reset_index()
            df_carteira.rename(columns={'PrecoLive': 'PrecoAtual'}, inplace=True)

    # --- 3. MATEMÁTICA CORRIGIDA (OUTER JOIN) ---
    # Agora todo centavo investido, mesmo em ativos velhos/ilegítimos, entra na conta da categoria!
    total_atual = df_carteira['TotalAtual'].sum() if not df_carteira.empty else 0
    total_futuro = total_atual + valor_aporte 
    
    df_calc = pd.merge(df_alvos, df_carteira, on=['Categoria', 'Ativo'], how='outer')
    df_calc['Is_Target'] = df_calc['Is_Target'].fillna(False)
    df_calc['PesoGlobal'] = df_calc['PesoGlobal'].fillna(0)
    df_calc['TotalAtual'] = df_calc['TotalAtual'].fillna(0)
    df_calc['PrecoAtual'] = df_calc['PrecoAtual'].fillna(0)
    
    df_calc['ValorAlvo'] = df_calc['PesoGlobal'] * total_futuro
    df_calc['Falta_Comprar'] = df_calc['ValorAlvo'] - df_calc['TotalAtual']
    df_calc['TotalAtual_Original'] = df_calc['TotalAtual'].copy()

    aporte_restante = valor_aporte
    compras = []
    ativos_comprados = [] 

    for i in range(num_compras):
        if aporte_restante <= 0.01: break

        # A inteligência: Ele soma a defasagem da categoria incluindo TODA a sua grana (até a de ativos que vc não quer mais comprar)
        cat_gaps = df_calc.groupby('Categoria')['Falta_Comprar'].sum().sort_values(ascending=False)
        top_cat = cat_gaps.index[0]
        max_cat_gap = cat_gaps.iloc[0]

        # Filtra os ativos permitidos para compra (Apenas os Targets oficiais)
        df_disponivel = df_calc[(df_calc['Is_Target'] == True) & (~df_calc['Ativo'].isin(ativos_comprados))]
        if df_disponivel.empty: break

        if max_cat_gap <= 0.01:
            df_disponivel = df_disponivel.sort_values(by='Falta_Comprar', ascending=False)
            top_ativo_row = df_disponivel.iloc[0]
        else:
            ativos_top_cat = df_disponivel[df_disponivel['Categoria'] == top_cat]
            if ativos_top_cat.empty:
                df_disponivel = df_disponivel.sort_values(by='Falta_Comprar', ascending=False)
                top_ativo_row = df_disponivel.iloc[0]
            else:
                ativos_top_cat = ativos_top_cat.sort_values(by='Falta_Comprar', ascending=False)
                top_ativo_row = ativos_top_cat.iloc[0]

        falta_ativo = top_ativo_row['Falta_Comprar']
        compras_restantes = num_compras - i
        valor_parcela = aporte_restante / compras_restantes

        if falta_ativo > 0: valor_alocado = min(valor_parcela, falta_ativo)
        else: valor_alocado = valor_parcela 

        idx = top_ativo_row.name
        top_ativo = top_ativo_row['Ativo']
        preco_atual = top_ativo_row['PrecoAtual']
        categoria = top_ativo_row['Categoria']

        is_rv = categoria in ["Ações", "FIIs", "Stocks", "REITs", "ETFs"]
        is_br = categoria in ["Ações", "FIIs"]
        qtd_sugerida_str = "-"
        qtd_faltante_str = "-"

        if is_rv and preco_atual > 0:
            qtd_sugerida = valor_alocado / preco_atual
            qtd_alvo = top_ativo_row['ValorAlvo'] / preco_atual
            qtd_atual = top_ativo_row['TotalAtual_Original'] / preco_atual
            qtd_faltante_total = max(0, qtd_alvo - qtd_atual)
            
            if is_br:
                qtd_sugerida_str = f"{int(qtd_sugerida)} un"
                qtd_faltante_str = f"{int(qtd_faltante_total)} un"
            else:
                qtd_sugerida_str = f"{qtd_sugerida:.4f} un".replace('.', ',')
                qtd_faltante_str = f"{qtd_faltante_total:.4f} un".replace('.', ',')

        compras.append({
            'Ordem': i + 1, 'Categoria': categoria, 'Ativo': top_ativo, 'Valor': valor_alocado,
            'PrecoRef': preco_atual, 'Qtd_Sugerida': qtd_sugerida_str,
            'Qtd_Faltante': qtd_faltante_str, 'Is_RV': is_rv
        })

        df_calc.loc[idx, 'Falta_Comprar'] -= valor_alocado
        df_calc.loc[idx, 'TotalAtual'] += valor_alocado
        ativos_comprados.append(top_ativo)
        aporte_restante -= valor_alocado

    return compras, aporte_restante, None


def render():
    st.title("🎯 Guia de Aportes Inteligente")
    st.markdown("Descubra exatamente onde alocar seu dinheiro para manter a carteira alinhada aos seus objetivos.")

    st.markdown("### 1. Dados do Aporte")
    col1, col2 = st.columns([1, 1], gap="large")
    with col1:
        valor_aporte = st.number_input("💸 Valor do Aporte (R$)", min_value=0.0, value=1000.0, step=100.0)
    with col2:
        num_compras = st.pills("Dividir em até quantas compras?", options=[1, 2, 3], default=1)

    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("🚀 Calcular Onde Aportar", use_container_width=True):
        if valor_aporte <= 0:
            st.warning("Insira um valor maior que zero para o aporte.")
            return

        with st.spinner("Analisando o balanço real da sua carteira..."):
            compras, aporte_restante, erro = motor_de_aportes(st.session_state.email, valor_aporte, num_compras)
            
            if erro:
                st.error(f"⚠️ {erro}")
                return

        st.markdown("---")
        st.subheader("🛒 Suas Ordens de Compra Sugeridas")

        if compras:
            for c in compras:
                with st.container():
                    st.markdown(f"#### {c['Ordem']}º Compra: `{c['Ativo']}` <span style='font-size:0.8em; color:gray;'>({c['Categoria']})</span>", unsafe_allow_html=True)
                    if c['Is_RV']:
                        c_r1, c_r2, c_r3, c_r4 = st.columns(4)
                        c_r1.metric("Alocar (R$)", formata_br(c['Valor']))
                        c_r2.metric("Cotação", formata_br(c['PrecoRef']) if c['PrecoRef'] > 0 else "N/A")
                        c_r3.metric("Comprar", c['Qtd_Sugerida'])
                        c_r4.metric("Falta p/ Meta", c['Qtd_Faltante'])
                    else:
                        c_r1, c_r2, c_r3 = st.columns(3)
                        c_r1.metric("Alocar (R$)", formata_br(c['Valor']))
                        c_r2.metric("Preço Atual", formata_br(c['PrecoRef']) if c['PrecoRef'] > 0 else "N/A")
                        c_r3.metric("Status", "Renda Fixa")
                    st.markdown("<hr style='margin: 0.5em 0; border: 0; border-top: 1px dashed #ddd;'>", unsafe_allow_html=True)

            if aporte_restante > 0.05:
                st.info(f"💰 **Sobrou {formata_br(aporte_restante)}**. O algoritmo evitou investir isso para não estourar os limites percentuais configurados.")
            else:
                st.success("✅ Todo o valor foi distribuído de forma otimizada para rebalancear a sua carteira!")
        else:
            st.info("Nenhuma sugestão gerada.")
