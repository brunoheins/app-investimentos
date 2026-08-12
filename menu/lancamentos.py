import streamlit as st
import pandas as pd
from datetime import datetime
from utils import registrar_deposito, registrar_compra, obter_ativos_por_categoria, formata_br, ler_planilha, atualizar_historico_usuario
from menu.aportes import motor_de_aportes # <-- IMPORTA O CÉREBRO DE APORTES!

def render():
    st.title("📝 Central de Lançamentos")
    st.markdown("Registre a entrada de dinheiro novo na corretora e as suas ordens de compra.")

    # Cria a variável na memória do sistema caso ela não exista
    if 'dicas_salvas' not in st.session_state:
        st.session_state.dicas_salvas = None

    # ==========================================
    # NOVO SISTEMA DE ABAS (BOTÕES INTELIGENTES)
    # ==========================================
    if 'aba_lancamento' not in st.session_state:
        st.session_state.aba_lancamento = "Depósitos"

    def mudar_aba_lancamento(nova_aba):
        st.session_state.aba_lancamento = nova_aba

    st.markdown("<br>", unsafe_allow_html=True)
    c_aba1, c_aba2 = st.columns(2)
    
    c_aba1.button(
        "💰 1. Depósito de Dinheiro (Aporte)", 
        use_container_width=True, 
        on_click=mudar_aba_lancamento, args=("Depósitos",),
        type="primary" if st.session_state.aba_lancamento == "Depósitos" else "secondary"
    )

    c_aba2.button(
        "🛒 2. Lançamento de Ativos", 
        use_container_width=True, 
        on_click=mudar_aba_lancamento, args=("Compras",),
        type="primary" if st.session_state.aba_lancamento == "Compras" else "secondary"
    )
    
    st.markdown("---")

    # ==========================================
    # 1. DEPÓSITO DE DINHEIRO
    # ==========================================
    if st.session_state.aba_lancamento == "Depósitos":
        st.subheader("Registrar novo Aporte")
        st.info("Lance aqui todo dinheiro 'novo' que saiu do seu bolso (conta corrente) para a corretora.")
        
        with st.form("form_deposito", clear_on_submit=True):
            col1, col2 = st.columns(2)
            data_deposito = col1.date_input("Data do Depósito", value=datetime.today(), format="DD/MM/YYYY")
            valor_deposito = col2.number_input("Valor (R$)", min_value=0.00, value=1000.00, step=100.0, format="%.2f")
            
            submit = st.form_submit_button("💾 Salvar Depósito", use_container_width=True, type="primary")
            if submit:
                data_str = data_deposito.strftime("%d/%m/%Y")
                if registrar_deposito(st.session_state.email, data_str, valor_deposito):
                    st.success(f"Depósito de R$ {valor_deposito:,.2f} em {data_str} salvo com sucesso!")

    # ==========================================
    # 2. COMPRA / VENDA / EVENTOS CORPORATIVOS
    # ==========================================
    elif st.session_state.aba_lancamento == "Compras":
        st.subheader("Registrar Movimentação")
        st.info("O sistema garante que você só registre ativos que pertençam à categoria correta.")
        
        # --- PAINEL RETRÁTIL COM AS RECOMENDAÇÕES (COM MEMÓRIA) ---
        painel_aberto = True if st.session_state.dicas_salvas else False
        
        with st.expander("💡 Precisa de ajuda? Consultar Guia de Aportes Rápido", expanded=painel_aberto):
            st.markdown("Descubra qual é o ativo mais atrasado na sua carteira neste momento:")
            c_val, c_num, c_btn = st.columns([2, 1, 1.2])
            val_simul = c_val.number_input("💵 Qual valor você tem para investir?", min_value=0.00, value=1000.00, step=100.00)
            num_simul = c_num.selectbox("Fatiar em quantas compras?", [1, 2, 3])
            
            if c_btn.button("Gerar Dica Rápida", use_container_width=True, type="primary"):
                with st.spinner("Calculando defasagem..."):
                    compras, resto, erro = motor_de_aportes(st.session_state.email, val_simul, num_simul)
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
        # -------------------------------------------------------

        cat_ativos_dict = obter_ativos_por_categoria(st.session_state.email)
        categorias_disp = list(cat_ativos_dict.keys())

        # --- INÍCIO DAS ALTERAÇÕES NO FORMULÁRIO DE ATIVOS ---
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
            c1, c2, c3 = st.columns(3)
            data_compra = c1.date_input("Data da Operação", value=datetime.today(), format="DD/MM/YYYY")
            qtd_compra = c2.number_input("Quantidade (Cotas/Títulos)", min_value=0.0001, step=1.0, format="%.4f")
            preco_compra = c3.number_input("Preço Unitário (R$)", min_value=0.00, step=1.0, format="%.2f")
            
            observacao = st.text_input("Anotações (Opcional)", placeholder="Ex: Split 1:10, Bonificação, Realização de Lucro...")
            
            st.info("💡 **Dica para Eventos Corporativos:** Se for Bonificação (ganhou cotas) ou Grupamento (perdeu cotas), deixe o Preço Unitário como **R$ 0,00** para não alterar o dinheiro investido.")

            if st.button("💾 Registrar Operação", use_container_width=True, type="primary"):
                data_str = data_compra.strftime("%d/%m/%Y")
                
                # MÁGICA: Se for Saída (Venda/Grupamento), a quantidade enviada ao banco vira negativa
                qtd_final = qtd_compra if "Entrada" in tipo_op else -qtd_compra
                
                # Chama a função passando o novo campo de observação
                if registrar_compra(st.session_state.email, data_str, cat_compra, ativo_compra, qtd_final, preco_compra, observacao):
                    if preco_compra == 0:
                        st.success(f"✅ Evento corporativo de {qtd_compra} cotas salvo com sucesso para {ativo_compra}!")
                    else:
                        acao = "Compra" if "Entrada" in tipo_op else "Venda"
                        st.success(f"✅ {acao} de {qtd_compra}x {ativo_compra} salva com sucesso na categoria {cat_compra}!")
        # --- FIM DAS ALTERAÇÕES NO FORMULÁRIO DE ATIVOS ---

    # ==========================================
    # AUDITORIA E EDIÇÃO DE LANÇAMENTOS
    # ==========================================
    st.markdown("---")
    
    with st.expander("🔍 Histórico, Edição e Auditoria de Lançamentos"):
        st.markdown("Consulte seu histórico abaixo. Para **editar**, dê um duplo clique na célula. Para **excluir**, clique na linha e aperte a tecla `Delete`. Depois, clique no botão de salvar.")
        
        col_hist1, col_hist2 = st.columns(2)
        
        # --- COLUNA ESQUERDA: DEPÓSITOS ---
        with col_hist1:
            st.subheader("💰 Editar Depósitos")
            df_depositos = ler_planilha("Depositos") 
            if not df_depositos.empty and 'Email' in df_depositos.columns:
                df_depositos['Email'] = df_depositos['Email'].astype(str).str.strip().str.lower()
                meus_depositos = df_depositos[df_depositos['Email'] == st.session_state.email].copy()
                
                if not meus_depositos.empty:
                    meus_depositos = meus_depositos.drop(columns=['Email'])
                    
                    df_depositos_editado = st.data_editor(
                        meus_depositos, 
                        num_rows="dynamic",
                        use_container_width=True, 
                        hide_index=True,
                        key="editor_depositos"
                    )
                    
                    if st.button("💾 Salvar Alterações (Depósitos)", use_container_width=True, type="primary"):
                        with st.spinner("Atualizando depósitos..."):
                            if atualizar_historico_usuario(st.session_state.email, "Depositos", df_depositos_editado):
                                st.success("Depósitos atualizados com sucesso!")
                                st.rerun()
                else:
                    st.info("Nenhum depósito registrado.")
            else:
                st.info("Banco de dados vazio.")

        # --- COLUNA DIREITA: COMPRAS (INVESTIMENTOS) ---
        with col_hist2:
            st.subheader("🛒 Editar Movimentações")
            df_compras = ler_planilha("Investimentos") 
            if not df_compras.empty and 'Email' in df_compras.columns:
                df_compras['Email'] = df_compras['Email'].astype(str).str.strip().str.lower()
                minhas_compras = df_compras[df_compras['Email'] == st.session_state.email].copy()
                
                if not minhas_compras.empty:
                    minhas_compras = minhas_compras.drop(columns=['Email'])
                    
                    df_compras_editado = st.data_editor(
                        minhas_compras, 
                        num_rows="dynamic", 
                        use_container_width=True, 
                        hide_index=True,
                        key="editor_compras"
                    )
                    
                    if st.button("💾 Salvar Alterações (Movimentações)", use_container_width=True, type="primary"):
                        with st.spinner("Atualizando carteira..."):
                            if atualizar_historico_usuario(st.session_state.email, "Investimentos", df_compras_editado):
                                st.success("Movimentações atualizadas com sucesso!")
                                st.rerun()
                else:
                    st.info("Nenhuma movimentação registrada.")
            else:
                st.info("Banco de dados de movimentações vazio.")
