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

def motor_de_aportes(email, valor_aporte, dividir=True):
    """Cérebro matemático: Calcula as recomendações de compra otimizando trocos e lotes reais."""
    df_conf = ler_planilha("Configuracao")
    df_ativos_conf = ler_planilha("Ativos_Config")
    df_invest = ler_planilha("Investimentos")

    if df_conf.empty or email not in df_conf['Email'].astype(str).str.strip().str.lower().values:
        return [], valor_aporte, None, "Metas de Alocação Macro não definidas na Configuração."
    
    if df_ativos_conf.empty:
        df_ativos_conf = pd.DataFrame(columns=['Email', 'Categoria', 'Ativo', 'Peso'])

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
    
    cotacoes_dict = obter_cotacoes()

    # --- 1. LER ATIVOS ALVOS OFICIAIS ---
    ativos_alvos = []
    for _, row in df_user_ativos.iterrows():
        cat = normalizar_categoria(row['Categoria'])
        if cat == "Renda Fixa": continue 
        ativo = str(row['Ativo']).strip().upper()
        val_peso = row.get('Peso') if pd.notna(row.get('Peso')) else row.get('Peso (%)', 0)
        peso_global = cat_targets.get(cat, 0) * (float(val_peso) / 100.0)
        if ativo and ativo != "NAN":
            ativos_alvos.append({'Categoria': cat, 'Ativo': ativo, 'PesoGlobal': peso_global})

    peso_rf = cat_targets.get("Renda Fixa", 0)
    if peso_rf > 0:
        ativos_alvos.append({'Categoria': 'Renda Fixa', 'Ativo': 'OPORTUNIDADE DE RENDA FIXA', 'PesoGlobal': peso_rf})

    df_alvos = pd.DataFrame(ativos_alvos)
    if not df_alvos.empty:
        df_alvos['Is_Target'] = True
    else:
        df_alvos = pd.DataFrame(columns=['Categoria', 'Ativo', 'PesoGlobal', 'Is_Target'])

    # --- 2. LER ESTOQUE DA CARTEIRA REAL ---
    df_carteira = pd.DataFrame(columns=['Categoria', 'Ativo', 'TotalAtual'])
    if not df_invest.empty and 'Email' in df_invest.columns:
        df_invest['Email'] = df_invest['Email'].astype(str).str.strip().str.lower()
        df_user_invest = df_invest[df_invest['Email'] == email].copy()
        
        if not df_user_invest.empty:
            df_user_invest['Ativo'] = df_user_invest['Ativo'].astype(str).str.strip().str.upper()
            df_user_invest['Categoria'] = df_user_invest['Categoria'].apply(normalizar_categoria)
            df_user_invest['Quantidade'] = df_user_invest['Quantidade'].apply(extrair_numero_br)
            df_user_invest['PrecoLive'] = df_user_invest['Ativo'].map(cotacoes_dict).fillna(0.0)
            df_user_invest['TotalAtual'] = df_user_invest['Quantidade'] * df_user_invest['PrecoLive']

            for idx_inv, row_inv in df_user_invest.iterrows():
                if row_inv['Categoria'] == "Renda Fixa" and row_inv['TotalAtual'] == 0:
                    try:
                        preco_digitado = float(str(row_inv.get('Preco', '0')).replace('.', '').replace(',', '.'))
                        df_user_invest.at[idx_inv, 'TotalAtual'] = row_inv['Quantidade'] * preco_digitado
                    except:
                        pass

            df_carteira = df_user_invest.groupby(['Categoria', 'Ativo']).agg({
                'TotalAtual': 'sum'
            }).reset_index()

    # --- 3. MATEMÁTICA E CÁLCULO DE GAPS ---
    total_atual = df_carteira['TotalAtual'].sum() if not df_carteira.empty else 0
    total_futuro = total_atual + valor_aporte 
    
    df_calc = pd.merge(df_alvos, df_carteira, on=['Categoria', 'Ativo'], how='outer')
    df_calc['Is_Target'] = df_calc['Is_Target'].fillna(False)
    df_calc['PesoGlobal'] = df_calc['PesoGlobal'].fillna(0)
    df_calc['TotalAtual'] = df_calc['TotalAtual'].fillna(0)
    df_calc['PrecoAtual'] = df_calc['Ativo'].map(cotacoes_dict).fillna(0.0)
    
    df_calc['ValorAlvo'] = df_calc['PesoGlobal'] * total_futuro
    df_calc['Falta_Comprar'] = df_calc['ValorAlvo'] - df_calc['TotalAtual']
    df_calc['TotalAtual_Original'] = df_calc['TotalAtual'].copy()

    # --- PREPARAÇÃO DO TERMÔMETRO VISUAL (RESUMO MACRO) ---
    df_resumo_macro = df_calc.groupby('Categoria').agg(
        Alvo=('ValorAlvo', 'sum'),
        Atual=('TotalAtual', 'sum')
    ).reset_index()
    
    df_resumo_macro['Alvo (%)'] = (df_resumo_macro['Alvo'] / total_futuro * 100).round(1) if total_futuro > 0 else 0
    df_resumo_macro['Atual (%)'] = (df_resumo_macro['Atual'] / total_atual * 100).round(1) if total_atual > 0 else 0
    df_resumo_macro['Status'] = df_resumo_macro.apply(
        lambda x: "🟢 Na Meta" if abs(x['Alvo (%)'] - x['Atual (%)']) <= 2 
        else ("🔴 Abaixo da Meta" if x['Atual (%)'] < x['Alvo (%)'] else "🟡 Acima da Meta"), 
        axis=1
    )

    # --- 4. ALOCAÇÃO INTELIGENTE (DIVIDIR OU INTEGRAL) ---
    compras_dict = {}
    aporte_restante = valor_aporte
    df_disp = df_calc[df_calc['Is_Target'] == True].copy()
    
    # Prepara a estrutura local para rastrear as compras
    for idx, row in df_disp.iterrows():
        ativo = row['Ativo']
        compras_dict[ativo] = {
            'Categoria': row['Categoria'],
            'Ativo': ativo,
            'Valor': 0.0,
            'PrecoRef': row['PrecoAtual'],
            'Qtd': 0.0,
            'Is_RV': row['Categoria'] in ["Ações", "FIIs", "Stocks", "REITs", "ETFs"],
            'Is_BR': row['Categoria'] in ["Ações", "FIIs"],
            'Qtd_Alvo': row['ValorAlvo'] / row['PrecoAtual'] if row['PrecoAtual'] > 0 else 0,
            'Qtd_Atual': row['TotalAtual_Original'] / row['PrecoAtual'] if row['PrecoAtual'] > 0 else 0,
            'Falta_Comprar': row['Falta_Comprar']
        }

    if not dividir:
        # Aporte Integral: Aloca 100% no ativo mais defasado da carteira
        df_disp = df_disp.sort_values(by='Falta_Comprar', ascending=False)
        if not df_disp.empty:
            row = df_disp.iloc[0]
            ativo = row['Ativo']
            d = compras_dict[ativo]
            preco = d['PrecoRef']
            
            if d['Is_RV'] and preco > 0:
                if d['Is_BR']:
                    qtd = int(aporte_restante / preco)
                    gasto = qtd * preco
                else:
                    qtd = aporte_restante / preco
                    gasto = aporte_restante
            elif not d['Is_RV']:
                qtd = 0
                gasto = aporte_restante
            else:
                gasto = 0
                qtd = 0
                
            d['Valor'] += gasto
            d['Qtd'] += qtd
            d['Falta_Comprar'] -= gasto
            aporte_restante -= gasto

    else:
        # Aporte Dividido: Passo 1 - Alocação Proporcional Mágica
        df_gap = df_disp[df_disp['Falta_Comprar'] > 0]
        total_gap = df_gap['Falta_Comprar'].sum()
        
        if total_gap > 0:
            for idx, row in df_gap.iterrows():
                ativo = row['Ativo']
                d = compras_dict[ativo]
                preco = d['PrecoRef']
                fator = d['Falta_Comprar'] / total_gap
                alocacao_teorica = valor_aporte * fator
                
                if d['Is_RV'] and preco > 0:
                    if d['Is_BR']:
                        qtd = int(alocacao_teorica / preco) # Arredonda pra baixo (cotas cheias)
                        gasto = qtd * preco
                    else:
                        qtd = alocacao_teorica / preco
                        gasto = alocacao_teorica
                elif not d['Is_RV']:
                    qtd = 0
                    gasto = alocacao_teorica
                else:
                    gasto = 0
                    qtd = 0
                    
                d['Valor'] += gasto
                d['Qtd'] += qtd
                d['Falta_Comprar'] -= gasto
                aporte_restante -= gasto
        else:
            # Fallback: Se tudo já está na meta, distribui pelos pesos globais normais
            total_peso = df_disp['PesoGlobal'].sum()
            for idx, row in df_disp.iterrows():
                ativo = row['Ativo']
                d = compras_dict[ativo]
                preco = d['PrecoRef']
                fator = row['PesoGlobal'] / total_peso if total_peso > 0 else 1/len(df_disp)
                alocacao_teorica = valor_aporte * fator
                
                if d['Is_RV'] and preco > 0:
                    if d['Is_BR']:
                        qtd = int(alocacao_teorica / preco)
                        gasto = qtd * preco
                    else:
                        qtd = alocacao_teorica / preco
                        gasto = alocacao_teorica
                elif not d['Is_RV']:
                    qtd = 0
                    gasto = alocacao_teorica
                else:
                    gasto = 0
                    qtd = 0
                    
                d['Valor'] += gasto
                d['Qtd'] += qtd
                d['Falta_Comprar'] -= gasto
                aporte_restante -= gasto

        # Aporte Dividido: Passo 2 - Otimizador de Trocos (Greedy)
        # Absorve todo o dinheiro que sobrou por causa de cotas arredondadas no Passo 1
        comprou_no_loop = True
        while aporte_restante > 0.01 and comprou_no_loop:
            comprou_no_loop = False
            # Ordena e joga o troco em quem está com o maior gap no momento
            ativos_ordenados = sorted(compras_dict.values(), key=lambda x: x['Falta_Comprar'], reverse=True)
            
            for d in ativos_ordenados:
                preco = d['PrecoRef']
                if d['Is_RV']:
                    if preco <= 0: continue
                    if d['Is_BR']:
                        if aporte_restante >= preco:
                            d['Valor'] += preco
                            d['Qtd'] += 1
                            d['Falta_Comprar'] -= preco
                            aporte_restante -= preco
                            comprou_no_loop = True
                            break 
                    else:
                        # Ativos exteriores e ETFs podem engolir o troco fracionário todo
                        d['Valor'] += aporte_restante
                        d['Qtd'] += aporte_restante / preco
                        d['Falta_Comprar'] -= aporte_restante
                        aporte_restante = 0
                        comprou_no_loop = True
                        break
                else:
                    # Renda Fixa engole trocos perfeitamente
                    d['Valor'] += aporte_restante
                    d['Falta_Comprar'] -= aporte_restante
                    aporte_restante = 0
                    comprou_no_loop = True
                    break

    # --- 5. MONTAGEM FINAL DO EXTRATO DE COMPRAS ---
    compras = []
    ordem = 1
    # Organiza do maior montante em R$ para o menor
    for d in sorted(compras_dict.values(), key=lambda x: x['Valor'], reverse=True):
        if d['Valor'] > 0:
            qtd_sugerida_str = "-"
            qtd_faltante_str = "-"
            if d['Is_RV']:
                qtd_faltante = max(0, d['Qtd_Alvo'] - d['Qtd_Atual'])
                if d['Is_BR']:
                    qtd_sugerida_str = f"{int(d['Qtd'])} un"
                    qtd_faltante_str = f"{int(qtd_faltante)} un"
                else:
                    qtd_sugerida_str = f"{d['Qtd']:.4f} un".replace('.', ',')
                    qtd_faltante_str = f"{qtd_faltante:.4f} un".replace('.', ',')
                    
            compras.append({
                'Ordem': ordem,
                'Categoria': d['Categoria'],
                'Ativo': d['Ativo'],
                'Valor': d['Valor'],
                'PrecoRef': d['PrecoRef'],
                'Qtd_Sugerida': qtd_sugerida_str,
                'Qtd_Faltante': qtd_faltante_str,
                'Is_RV': d['Is_RV']
            })
            ordem += 1

    return compras, aporte_restante, df_resumo_macro, None


def render():
    st.title("🎯 Guia de Aportes Inteligente")
    st.markdown("Descubra exatamente onde alocar seu dinheiro para manter a carteira alinhada aos seus objetivos.")

    st.markdown("### 1. Dados do Aporte")
    col1, col2 = st.columns([1, 1], gap="large")
    with col1:
        valor_aporte = st.number_input("💸 Valor do Aporte (R$)", min_value=0.0, value=1000.0, step=100.0)
    with col2:
        num_compras = st.pills("Dividir em até quantas compras?", options=[1, 2, 3, 4, 5], default=1)

    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("🚀 Calcular Onde Aportar", use_container_width=True, type="primary"):
        if valor_aporte <= 0:
            st.warning("Insira um valor maior que zero para o aporte.")
            return

        with st.spinner("Analisando o balanço real da sua carteira..."):
            compras, aporte_restante, df_macro, erro = motor_de_aportes(st.session_state.email, valor_aporte, num_compras)
            
            if erro:
                st.error(f"⚠️ {erro}")
                return
                
        # --- NOVO: TERMÔMETRO DA CARTEIRA ---
        st.markdown("---")
        st.subheader("📊 Termômetro da Carteira (Antes do Aporte)")
        st.dataframe(
            df_macro[['Categoria', 'Alvo (%)', 'Atual (%)', 'Status']].style.map(
                lambda x: 'color: #00C851' if '🟢' in str(x) else ('color: #ff4444' if '🔴' in str(x) else 'color: #ffbb33'), 
                subset=['Status']
            ),
            use_container_width=True,
            hide_index=True
        )

        st.markdown("---")
        st.subheader("🛒 Suas Ordens de Compra Sugeridas")

        if compras:
            for c in compras:
                with st.container():
                    st.markdown(f"#### {c['Ordem']}º Compra: `{c['Ativo']}` <span style='font-size:0.8em; color:gray;'>({c['Categoria']})</span>", unsafe_allow_html=True)
                    if c['Is_RV']:
                        c_r1, c_r2, c_r3, c_r4 = st.columns(4)
                        c_r1.metric("Alocar Exato", formata_br(c['Valor']))
                        c_r2.metric("Cotação", formata_br(c['PrecoRef']) if c['PrecoRef'] > 0 else "N/A")
                        c_r3.metric("Comprar", c['Qtd_Sugerida'])
                        c_r4.metric("Falta p/ Meta", c['Qtd_Faltante'])
                    else:
                        c_r1, c_r2, c_r3 = st.columns(3)
                        c_r1.metric("Alocar Exato", formata_br(c['Valor']))
                        c_r2.metric("Estratégia", "Escolha Livre")
                        c_r3.metric("Sugestão", "Melhor Taxa IPCA+")
                    st.markdown("<hr style='margin: 0.5em 0; border: 0; border-top: 1px dashed #ddd;'>", unsafe_allow_html=True)

            if aporte_restante > 0.05:
                st.info(f"💰 **Sobrou {formata_br(aporte_restante)}**. Esse valor representa o 'troco' que não foi suficiente para comprar uma cota inteira adicional dos ativos selecionados.")
            else:
                st.success("✅ Todo o valor foi distribuído com precisão cirúrgica para rebalancear a sua carteira!")
        else:
            st.info("Nenhuma sugestão gerada. Verifique se o valor do aporte é suficiente para comprar os ativos que estão para trás na sua meta.")
