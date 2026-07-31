import streamlit as st
import pandas as pd
import plotly.express as px
from utils import ler_planilha, salvar_configuracao, salvar_ativos_categoria

def render():
    st.title("⚙️ Central de Configuração da Carteira")
    
    # COFRE: Salva estado das metas de alocação
    if 'backup_macro' not in st.session_state:
        df_conf = ler_planilha("Configuracao")
        user_conf = {}
        if not df_conf.empty:
            df_conf['Email'] = df_conf['Email'].astype(str).str.strip().str.lower()
            row = df_conf[df_conf['Email'] == st.session_state.email]
            if not row.empty:
                user_conf = row.iloc[0].to_dict()
        
        st.session_state.backup_macro = {
            'rf': float(user_conf.get('RF', 50.0)),
            'rv': float(user_conf.get('RV', 50.0)),
            'rv_br': float(user_conf.get('RV_Brasil', 50.0)),
            'rv_ex': float(user_conf.get('RV_Exterior', 50.0)),
            'br_ac': float(user_conf.get('BR_Acoes', 50.0)),
            'br_fii': float(user_conf.get('BR_FIIs', 50.0)),
            'ex_st': float(user_conf.get('EX_Stocks', 40.0)),
            'ex_re': float(user_conf.get('EX_REITs', 30.0)),
            'ex_et': float(user_conf.get('EX_ETFs', 30.0))
        }

    # ==========================================
    # NOVO SISTEMA DE ABAS PRINCIPAL
    # ==========================================
    if 'aba_config' not in st.session_state:
        st.session_state.aba_config = "Metas"

    def mudar_aba_config(nova_aba):
        st.session_state.aba_config = nova_aba

    st.markdown("<br>", unsafe_allow_html=True)
    c_aba1, c_aba2 = st.columns(2)
    
    c_aba1.button(
        "🎯 Metas de Alocação", 
        use_container_width=True, 
        on_click=mudar_aba_config, args=("Metas",),
        type="primary" if st.session_state.aba_config == "Metas" else "secondary"
    )

    c_aba2.button(
        "📋 Ativos e Pesos por Categoria", 
        use_container_width=True, 
        on_click=mudar_aba_config, args=("Ativos",),
        type="primary" if st.session_state.aba_config == "Ativos" else "secondary"
    )
    
    st.markdown("---")

    # ==========================================
    # 1. METAS DE ALOCAÇÃO
    # ==========================================
    if st.session_state.aba_config == "Metas":
        st.markdown("Ajuste seus percentuais macro. O sistema compensa automaticamente para a soma sempre cravar **100%**.")

        # RESTAURA VALORES DO COFRE
        if 'rf_val' not in st.session_state:
            st.session_state.rf_val = st.session_state.backup_macro['rf']
            st.session_state.rv_val = st.session_state.backup_macro['rv']
            st.session_state.rv_br_val = st.session_state.backup_macro['rv_br']
            st.session_state.rv_ex_val = st.session_state.backup_macro['rv_ex']
            st.session_state.br_ac_val = st.session_state.backup_macro['br_ac']
            st.session_state.br_fii_val = st.session_state.backup_macro['br_fii']
            st.session_state.ex_st_val = st.session_state.backup_macro['ex_st']
            st.session_state.ex_re_val = st.session_state.backup_macro['ex_re']
            st.session_state.ex_et_val = st.session_state.backup_macro['ex_et']

        def ajusta_macro(modificado):
            if modificado == 'rf': st.session_state.rv_val = round(100.0 - st.session_state.rf_val, 2)
            else: st.session_state.rf_val = round(100.0 - st.session_state.rv_val, 2)
        def ajusta_rv(modificado):
            if modificado == 'br': st.session_state.rv_ex_val = round(100.0 - st.session_state.rv_br_val, 2)
            else: st.session_state.rv_br_val = round(100.0 - st.session_state.rv_ex_val, 2)
        def ajusta_br(modificado):
            if modificado == 'ac': st.session_state.br_fii_val = round(100.0 - st.session_state.br_ac_val, 2)
            else: st.session_state.br_ac_val = round(100.0 - st.session_state.br_fii_val, 2)
        def ajusta_ex(modificado):
            if modificado == 'st':
                novo_et = round(100.0 - st.session_state.ex_st_val - st.session_state.ex_re_val, 2)
                if novo_et < 0:
                    st.session_state.ex_et_val = 0.0
                    st.session_state.ex_re_val = round(100.0 - st.session_state.ex_st_val, 2)
                else: st.session_state.ex_et_val = novo_et
            elif modificado == 're':
                novo_et = round(100.0 - st.session_state.ex_st_val - st.session_state.ex_re_val, 2)
                if novo_et < 0:
                    st.session_state.ex_et_val = 0.0
                    st.session_state.ex_st_val = round(100.0 - st.session_state.ex_re_val, 2)
                else: st.session_state.ex_et_val = novo_et
            elif modificado == 'et':
                novo_st = round(100.0 - st.session_state.ex_et_val - st.session_state.ex_re_val, 2)
                if novo_st < 0:
                    st.session_state.ex_st_val = 0.0
                    st.session_state.ex_re_val = round(100.0 - st.session_state.ex_et_val, 2)
                else: st.session_state.ex_st_val = novo_st

        col_esquerda, col_direita = st.columns([1.4, 1], gap="medium")

        with col_esquerda:
            st.subheader("Nível 1: Macro Alocação")
            c1, c2 = st.columns(2)
            c1.number_input("Renda Fixa (RF) %", min_value=0.0, max_value=100.0, step=1.0, key="rf_val", on_change=ajusta_macro, args=('rf',))
            c2.number_input("Renda Variável (RV) %", min_value=0.0, max_value=100.0, step=1.0, key="rv_val", on_change=ajusta_macro, args=('rv',))
            
            st.markdown("---")
            st.subheader("Nível 2: Renda Variável")
            c3, c4 = st.columns(2)
            c3.number_input("Brasil %", min_value=0.0, max_value=100.0, step=1.0, key="rv_br_val", on_change=ajusta_rv, args=('br',))
            c4.number_input("Exterior %", min_value=0.0, max_value=100.0, step=1.0, key="rv_ex_val", on_change=ajusta_rv, args=('ex',))
            
            st.markdown("---")
            c_b1, c_b2 = st.columns(2)
            with c_b1:
                st.subheader("Nível 3A: Brasil")
                st.number_input("Ações %", min_value=0.0, max_value=100.0, step=1.0, key="br_ac_val", on_change=ajusta_br, args=('ac',))
                st.number_input("FIIs %", min_value=0.0, max_value=100.0, step=1.0, key="br_fii_val", on_change=ajusta_br, args=('fii',))
                    
            with c_b2:
                st.subheader("Nível 3B: Exterior")
                st.number_input("Stocks %", min_value=0.0, max_value=100.0, step=1.0, key="ex_st_val", on_change=ajusta_ex, args=('st',))
                st.number_input("REITs %", min_value=0.0, max_value=100.0, step=1.0, key="ex_re_val", on_change=ajusta_ex, args=('re',))
                st.number_input("ETFs %", min_value=0.0, max_value=100.0, step=1.0, key="ex_et_val", on_change=ajusta_ex, args=('et',))

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("💾 Salvar Configuração Macro", use_container_width=True, type="primary"):
                dados_para_salvar = {
                    'RF': st.session_state.rf_val, 'RV': st.session_state.rv_val, 
                    'RV_Brasil': st.session_state.rv_br_val, 'RV_Exterior': st.session_state.rv_ex_val,
                    'BR_Acoes': st.session_state.br_ac_val, 'BR_FIIs': st.session_state.br_fii_val, 
                    'EX_Stocks': st.session_state.ex_st_val, 'EX_REITs': st.session_state.ex_re_val, 'EX_ETFs': st.session_state.ex_et_val
                }
                if salvar_configuracao(st.session_state.email, dados_para_salvar):
                    st.success("✅ Metas atualizadas e persistidas com sucesso!")

        with col_direita:
            st.subheader("🎯 Resumo do Objetivo")
            st.markdown("Distribuição real sobre o **patrimônio total**:")
            
            peso_rv = st.session_state.rv_val / 100.0
            peso_br = st.session_state.rv_br_val / 100.0
            peso_ex = st.session_state.rv_ex_val / 100.0
            
            df_resumo = pd.DataFrame({
                "Categoria": ["Renda Fixa", "Ações", "FIIs", "Stocks", "REITs", "ETFs"],
                "% Alvo Final": [
                    st.session_state.rf_val, 
                    peso_rv * peso_br * st.session_state.br_ac_val,
                    peso_rv * peso_br * st.session_state.br_fii_val,
                    peso_rv * peso_ex * st.session_state.ex_st_val,
                    peso_rv * peso_ex * st.session_state.ex_re_val,
                    peso_rv * peso_ex * st.session_state.ex_et_val
                ]
            })
            
            df_resumo_grafico = df_resumo[df_resumo["% Alvo Final"] > 0]
            df_resumo['% Alvo Final'] = df_resumo['% Alvo Final'].map('{:.2f}%'.format)
            
            st.dataframe(df_resumo, use_container_width=True, hide_index=True)
            
            fig_resumo = px.pie(df_resumo_grafico, values='% Alvo Final', names="Categoria", hole=0.5)
            fig_resumo.update_traces(textinfo='label+percent')
            fig_resumo.update_layout(height=300, margin=dict(t=10, b=10, l=10, r=10), showlegend=False)
            st.plotly_chart(fig_resumo, use_container_width=True)

        st.session_state.backup_macro.update({
            'rf': st.session_state.rf_val, 'rv': st.session_state.rv_val,
            'rv_br': st.session_state.rv_br_val, 'rv_ex': st.session_state.rv_ex_val,
            'br_ac': st.session_state.br_ac_val, 'br_fii': st.session_state.br_fii_val,
            'ex_st': st.session_state.ex_st_val, 'ex_re': st.session_state.ex_re_val,
            'ex_et': st.session_state.ex_et_val
        })

    # ==========================================
    # 2. ATIVOS E PESOS POR CATEGORIA
    # ==========================================
    elif st.session_state.aba_config == "Ativos":
        st.subheader("📋 Composição de Ativos por Categoria")
        st.markdown("Adicione os ativos (tickers) e defina a porcentagem interna de cada um. **A soma de cada categoria deve fechar exatamente 100%.**")

        # Submenu dinâmico (Botões ao invés de pills)
        if 'cat_config' not in st.session_state:
            st.session_state.cat_config = "Ações"

        def mudar_cat_config(nova_cat):
            st.session_state.cat_config = nova_cat

        st.markdown("<br>", unsafe_allow_html=True)
        categorias = ["Ações", "FIIs", "Stocks", "REITs", "ETFs", "Renda Fixa"]
        cols_cat = st.columns(len(categorias))
        
        for i, cat in enumerate(categorias):
            cols_cat[i].button(
                cat,
                use_container_width=True,
                on_click=mudar_cat_config, args=(cat,),
                type="primary" if st.session_state.cat_config == cat else "secondary",
                key=f"btn_nav_{cat}"
            )
        
        cat_selecionada = st.session_state.cat_config
        st.markdown("---")
        st.markdown(f"### ⚙️ Editando: **{cat_selecionada}**")

        df_ativos_existentes = ler_planilha("Ativos_Config")
        if not df_ativos_existentes.empty and 'Email' in df_ativos_existentes.columns:
            df_ativos_existentes['Email'] = df_ativos_existentes['Email'].astype(str).str.strip().str.lower()
            df_ativos_existentes['Categoria'] = df_ativos_existentes['Categoria'].astype(str).str.strip()
            df_ativos_user = df_ativos_existentes[df_ativos_existentes['Email'] == st.session_state.email]
        else:
            df_ativos_user = pd.DataFrame(columns=['Email', 'Categoria', 'Ativo', 'Peso'])

        df_cat_salvo = df_ativos_user[df_ativos_user['Categoria'] == cat_selecionada][['Ativo', 'Peso']].copy()
        
        if df_cat_salvo.empty:
            df_inicial = pd.DataFrame({"Ativo": [""], "Peso (%)": [100.0]})
        else:
            df_cat_salvo.rename(columns={'Peso': 'Peso (%)'}, inplace=True)
            df_inicial = df_cat_salvo

        col_tabela, col_vazia = st.columns([1.5, 1])
        with col_tabela:
            df_editado = st.data_editor(
                df_inicial,
                num_rows="dynamic",
                use_container_width=True,
                hide_index=True, 
                key=f"editor_cat_v2_{cat_selecionada}",
                column_config={
                    "Ativo": st.column_config.TextColumn("Ativo (Ticker)", required=True),
                    "Peso (%)": st.column_config.NumberColumn("Peso (%)", min_value=0.0, max_value=100.0, step=0.5, format="%.2f")
                }
            )

            soma_pesos = pd.to_numeric(df_editado['Peso (%)'], errors='coerce').sum()
            
            col_info, col_btn = st.columns([2, 1])
            with col_info:
                if abs(soma_pesos - 100.0) < 0.01:
                    st.success(f"✅ Soma: **{soma_pesos:.2f}%**")
                else:
                    st.warning(f"⚠️ Soma: **{soma_pesos:.2f}%** (O ideal é 100%)")
            
            with col_btn:
                # Botão sem o type="primary" para manter o padrão cinza
                if st.button(f"💾 Salvar {cat_selecionada}", key=f"btn_save_{cat_selecionada}", use_container_width=True):
                    df_para_salvar = df_editado.copy()
                    df_para_salvar.rename(columns={'Peso (%)': 'Peso'}, inplace=True)
                    if salvar_ativos_categoria(st.session_state.email, cat_selecionada, df_para_salvar):
                        st.success(f"Ativos de {cat_selecionada} salvos!")
                        st.rerun()
