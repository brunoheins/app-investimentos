import streamlit as st
import pandas as pd
import time
from datetime import datetime
from utils import registrar_deposito, registrar_compra, obter_ativos_por_categoria, formata_br, ler_planilha, atualizar_historico_usuario
from menu.aportes import motor_de_aportes

def render():
    st.title("📝 Central de Lançamentos")
    st.markdown("Registre a movimentação de dinheiro na corretora e as suas ordens de compra e venda.")

    if 'dicas_salvas' not in st.session_state:
        st.session_state.dicas_salvas = None

    if 'aba_lancamento' not in st.session_state:
        st.session_state.aba_lancamento = "Depósitos"

    def mudar_aba_lancamento(nova_aba):
        st.session_state.aba_lancamento = nova_aba

    st.markdown("<br>", unsafe_allow_html=True)
    c_aba1, c_aba2 = st.columns(2)
    
    c_aba1.button(
        "💰 1. Aporte / Saque de Caixa", 
        width='stretch', 
        on_click=mudar_aba_lancamento, args=("Depósitos",),
        type="primary" if st.session_state.aba_lancamento == "Depósitos" else "secondary"
    )

    c_aba2.button(
        "🛒 2. Lançamento de Ativos", 
        width='stretch', 
        on_click=mudar_aba_lancamento, args=("Compras",),
        type="primary" if st.session_state.aba_lancamento == "Compras" else "secondary"
    )
    
    st.markdown("---")

    # ==========================================
    # 1. DEPÓSITO / SAQUE DE DINHEIRO
    # ==========================================
    if st.session_state.aba_lancamento == "Depósitos":
        st.subheader("Registrar Movimentação de Caixa")
        st.info("Lance aqui o dinheiro que entrou (Aporte) ou que você retirou (Saque) da corretora.")
        
        tipo_mov_caixa = st.radio(
            "Tipo de Movimentação:",
            options=["Aporte (Entrada 💰)", "Saque (Saída 💸)"],
            horizontal=True
        )

        col1, col2 = st.columns(2)
        data_deposito = col1.date_input("Data do Movimento", value=datetime.today(), format="DD/MM/YYYY")
        
        if "Saque" in tipo_mov_caixa:
            valor_deposito = col2.number_input("Valor do Saque (R$)", min_value=0.01, step=100.0, format="%.2f")
            valor_deposito = -valor_deposito
        else:
            valor_deposito = col2.number_input("Valor do Aporte (R$)", min_value=0.01, step=100.0, format="%.2f")

        if st.button("💾 Salvar Movimentação de Caixa", width='stretch', type="primary"):
            data_str = data_deposito.strftime("%d/%m/%Y")
            if registrar_deposito(st.session_state.email, data_str, valor_deposito):
                tipo_str = "Saque" if valor_deposito < 0 else "Aporte"
                st.success(f"✅ {tipo_str} de R$ {abs(valor_deposito):.2f} registrado com sucesso!")
                time.sleep(1.5)
                st.rerun()

    # ==========================================
    # 2. LANÇAMENTO DE ATIVOS (COMPRA/VENDA)
    # ==========================================
    if st.session_state.aba_lancamento == "Compras":
        st.subheader("Registrar Movimentação de Ativos")
        st.info("O sistema garante que você só registre ativos que pertençam à categoria correta.")
        
        painel_aberto = True if st.session_state.dicas_salvas else False
        
        with st.expander("💡 Precisa de ajuda? Consultar Guia de Aportes Rápido", expanded=painel_aberto):
            st.markdown("Descubra qual é o ativo mais atrasado na sua carteira neste momento:")
            c_val, c_num, c_btn = st.columns([2, 2, 1.2])
            val_simul = c_val.number_input("💵 Qual valor você tem para investir?", min_value=0.00, value=1000.00, step=100.00)
            
            opcao_est = c_num.selectbox("Estratégia do Aporte:", ["Dividir pelo Objetivo", "Aporte Integral (1 Ativo)"])
            dividir = "Dividir" in opcao_est
            
            if c_btn.button("Gerar Dica Rápida", width='stretch', type="primary"):
                with st.spinner("Calculando defasagem..."):
                    compras, resto, df_macro, erro = motor_de_aportes(st.session_state.email, val_simul, dividir)
                    st.session_state.dicas_salvas = {'compras': compras, 'resto': resto, 'erro': erro}
            
            if st.session_state.dicas_salvas:
                st.markdown("---")
                d = st.session_state.dicas_salvas
                if d['erro']:
                    st.error(d['erro'])
                elif not d['compras']:
                    st.warning("Nenhuma sugestão gerada.")
                else:
                    for c in d['compras']:
                        st.success(f"🎯 **Sugerido:** Comprar **{c['Ativo']}** ({c['Categoria']}) — Alocar **{formata_br(c['Valor'])}** (Aprox. {c['Qtd_Sugerida']})")
                    if d['resto'] > 0.05:
                        st.caption(f"⚠️ O sistema recomendou segurar **{formata_br(d['resto'])}** na conta para não ultrapassar suas metas.")
                
                if st.button("🧹 Limpar Dicas"):
                    st.session_state.dicas_salvas = None
                    st.rerun()
        
        st.markdown("<br>", unsafe_allow_html=True)

        cat_ativos_dict = obter_ativos_por_categoria(st.session_state.email)
        categorias_disp = list(cat_ativos_dict.keys())

        tipo_op = st.radio(
            "Tipo de Movimentação:",
            options=["Entrada (Compra / Bonificação 📈)", "Saída (Venda / Grupamento 📉)"],
            horizontal=True
        )
        
        c_cat, c_atv = st.columns(2)
        cat_compra = c_cat.selectbox("1. Escolha a Categoria", categorias_disp)
        
        ativos_da_categoria = cat_ativos_dict.get(cat_compra, [])
        
        if not ativos_da_categoria:
            c_atv.error(f"Nenhum ativo preenchido para '{cat_compra}' na aba Cotacao.")
            ativo_compra = None
        else:
            ativo_compra = c_atv.selectbox("2. Escolha o Ativo (Digite para buscar)", options=ativos_da_categoria)
            
            st.markdown("---")
            
            is_exterior = cat_compra in ["Stocks", "REITs", "ETFs"]
            
            if is_exterior:
                st.markdown("**🇺🇸 Lançamento Internacional**")
                c1, c2, c3, c4 = st.columns(4)
                data_compra = c1.date_input("Data da Operação", value=datetime.today(), format="DD/MM/YYYY")
                qtd_compra = c2.number_input("Quantidade (Frac.)", min_value=0.00000001, step=1.0, format="%.8f")
                preco_usd = c3.number_input("Preço Unit. (US$)", min_value=0.00, step=1.0, format="%.2f")
                valor_total_brl = c4.number_input("Total Debitado/Creditado (R$)", min_value=0.00, step=10.0, format="%.2f", help="O valor exato em Reais.")
                
                observacao_user = st.text_input("Anotações (Opcional)", placeholder="Ex: Remessa Nomad, Dividendo reinvestido...")
                
                total_usd = qtd_compra * preco_usd
                dolar_efetivo = (valor_total_brl / total_usd) if total_usd > 0 else 0.0
                
                if total_usd > 0 and valor_total_brl > 0:
                    st.caption(f"ℹ️ **Resumo da Ordem:** Total em Dólar: **US$ {total_usd:.2f}** | Câmbio Efetivo: **R$ {dolar_efetivo:.4f}**")
                
                preco_unitario_brl = (valor_total_brl / qtd_compra) if qtd_compra > 0 else 0.0
                obs_final = f"[US$ {preco_usd:.2f} | Câmbio: R$ {dolar_efetivo:.4f}] {observacao_user}".strip()

            else:
                st.markdown("**🇧🇷 Lançamento Nacional**")
                c1, c2, c3 = st.columns(3)
                data_compra = c1.date_input("Data da Operação", value=datetime.today(), format="DD/MM/YYYY")
                qtd_compra = c2.number_input("Quantidade (Cotas)", min_value=0.0001, step=1.0, format="%.4f")
                preco_unitario_brl = c3.number_input("Preço Unitário (R$)", min_value=0.00, step=1.0, format="%.2f")
                
                observacao_user = st.text_input("Anotações (Opcional)", placeholder="Ex: Subscrição, Bonificação...")
                
                valor_total_brl = qtd_compra * preco_unitario_brl
                obs_final = observacao_user

            st.info("💡 **Dica corporativa:** Para Bonificação ou Grupamento, lance o valor unitário como **R$ 0,00** para não alterar o capital investido.")

            if st.button("💾 Registrar Operação", width='stretch', type="primary"):
                data_str = data_compra.strftime("%d/%m/%Y")
                qtd_final = qtd_compra if "Entrada" in tipo_op else -qtd_compra
                
                if registrar_compra(st.session_state.email, data_str, cat_compra, ativo_compra, qtd_final, preco_unitario_brl, obs_final):
                    st.session_state.dicas_salvas = None 
                    
                    if preco_unitario_brl == 0:
                        st.success(f"✅ Evento de {qtd_compra} cotas salvo com sucesso para {ativo_compra}!")
                    else:
                        acao = "Compra" if "Entrada" in tipo_op else "Venda"
                        st.success(f"✅ {acao} de {ativo_compra} salva! Total da Ordem: R$ {valor_total_brl:.2f}")
                    
                    time.sleep(2)
                    st.rerun()

    # ==========================================
    # AUDITORIA E EDIÇÃO DE LANÇAMENTOS
    # ==========================================
    st.markdown("---")
    
    with st.expander("🔍 Histórico, Edição e Auditoria de Lançamentos"):
        st.markdown("Consulte seu histórico abaixo. Para **editar**, dê um duplo clique na célula. Para **excluir**, clique na lixeira à esquerda da linha.")
        st.caption("O botão de **'Salvar Alterações'** aparecerá logo abaixo da tabela assim que você fizer qualquer modificação.")

        col_hist1, col_hist2 = st.columns([1, 2], gap="large")
        
        with col_hist1:
            st.subheader("💰 Editar Caixa")
            df_depositos = ler_planilha("Depositos") 
            if not df_depositos.empty and 'Email' in df_depositos.columns:
                df_depositos['Email'] = df_depositos['Email'].astype(str).str.strip().str.lower()
                meus_depositos = df_depositos[df_depositos['Email'] == st.session_state.email].copy()
                
                if not meus_depositos.empty:
                    meus_depositos = meus_depositos.drop(columns=['Email'])
                    
                    # Converte a coluna Valor para float de forma robusta e aplica o style BR
                    if 'Valor' in meus_depositos.columns:
                         meus_depositos['Valor'] = pd.to_numeric(meus_depositos['Valor'].astype(str).str.replace('.', '').str.replace(',', '.'), errors='coerce').fillna(0)
                         meus_depositos = meus_depositos.style.format({'Valor': "{:,.2f}"}, thousands='.', decimal=',')

                    df_depositos_editado = st.data_editor(
                        meus_depositos, 
                        num_rows="dynamic",
                        width='stretch', 
                        hide_index=True,
                        key="editor_depositos"
                    )
                    
                    # Se tivermos aplicado o estilo, voltamos df_depositos_editado para um DF normal, e formatamos o número para gravar
                    if isinstance(df_depositos_editado, pd.io.formats.style.Styler):
                        df_depositos_editado = df_depositos_editado.data
                    
                    if 'Valor' in df_depositos_editado.columns:
                         df_depositos_editado['Valor'] = df_depositos_editado['Valor'].apply(lambda x: f"{x:.2f}".replace('.', ','))

                    if st.button("💾 Salvar Alterações de Caixa", width='stretch', type="primary"):
                        with st.spinner("Atualizando caixa..."):
                            if atualizar_historico_usuario(st.session_state.email, "Depositos", df_depositos_editado):
                                st.success("Caixa atualizado com sucesso!")
                                time.sleep(1.5)
                                st.rerun()
                else:
                    st.info("Nenhum aporte registrado.")
            else:
                st.info("Banco de dados vazio.")

        with col_hist2:
            st.subheader("🛒 Editar Movimentações")
            df_compras = ler_planilha("Investimentos") 
            if not df_compras.empty and 'Email' in df_compras.columns:
                df_compras['Email'] = df_compras['Email'].astype(str).str.strip().str.lower()
                minhas_compras = df_compras[df_compras['Email'] == st.session_state.email].copy()
                
                if not minhas_compras.empty:
                    minhas_compras = minhas_compras.drop(columns=['Email'])
                    
                    # Identifica colunas de valor e qtd, e formata no estilo PT-BR para exibição
                    col_preco = next((c for c in minhas_compras.columns if 'prec' in str(c).lower() or 'custo' in str(c).lower()), None)
                    col_qtd = 'Quantidade' if 'Quantidade' in minhas_compras.columns else None

                    if col_preco:
                        minhas_compras[col_preco] = pd.to_numeric(minhas_compras[col_preco].astype(str).str.replace('.', '').str.replace(',', '.'), errors='coerce').fillna(0)
                    if col_qtd:
                        minhas_compras[col_qtd] = pd.to_numeric(minhas_compras[col_qtd].astype(str).str.replace('.', '').str.replace(',', '.'), errors='coerce').fillna(0)
                    
                    estilo_dict = {}
                    if col_preco: estilo_dict[col_preco] = "{:,.2f}"
                    if col_qtd: estilo_dict[col_qtd] = "{:,.8f}" # Quantidade aceita mais casas

                    minhas_compras_styled = minhas_compras.style.format(estilo_dict, thousands='.', decimal=',') if estilo_dict else minhas_compras

                    df_compras_editado = st.data_editor(
                        minhas_compras_styled, 
                        num_rows="dynamic", 
                        width='stretch', 
                        hide_index=True,
                        key="editor_compras"
                    )
                    
                    # Puxa o DataFrame de volta e formata as colunas em string PT-BR antes de salvar
                    if isinstance(df_compras_editado, pd.io.formats.style.Styler):
                        df_compras_editado = df_compras_editado.data
                    
                    if col_preco in df_compras_editado.columns:
                        df_compras_editado[col_preco] = df_compras_editado[col_preco].apply(lambda x: f"{x:.4f}".replace('.', ','))
                    if col_qtd in df_compras_editado.columns:
                        df_compras_editado[col_qtd] = df_compras_editado[col_qtd].apply(lambda x: f"{x:.8f}".replace('.', ',').rstrip('0').rstrip(','))
                        # Fix caso remova os zeros e vire string vazia
                        df_compras_editado[col_qtd] = df_compras_editado[col_qtd].replace('', '0')
                    
                    if st.button("💾 Salvar Alterações de Ativos", width='stretch', type="primary"):
                        with st.spinner("Atualizando carteira..."):
                            if atualizar_historico_usuario(st.session_state.email, "Investimentos", df_compras_editado):
                                st.success("Movimentações atualizadas com sucesso!")
                                time.sleep(1.5)
                                st.rerun()
                else:
                    st.info("Nenhuma movimentação registrada.")
            else:
                st.info("Banco de dados de movimentações vazio.")
