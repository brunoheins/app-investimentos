import streamlit as st
import pandas as pd
from datetime import datetime
from utils import registrar_deposito, registrar_compra, obter_ativos_por_categoria, formata_br
from menu.aportes import motor_de_aportes # <-- IMPORTA O CÉREBRO DE APORTES!

def render():
    st.title("📝 Central de Lançamentos")
    st.markdown("Registre a entrada de dinheiro novo na corretora e as suas ordens de compra.")

    tipo_lancamento = st.pills(
        "O que você deseja registrar?",
        ["💰 1. Depósito de Dinheiro (Aporte)", "🛒 2. Compra de Ativos"],
        default="💰 1. Depósito de Dinheiro (Aporte)"
    )
    st.markdown("---")

    # ==========================================
    # 1. DEPÓSITO DE DINHEIRO
    # ==========================================
    if tipo_lancamento == "💰 1. Depósito de Dinheiro (Aporte)":
        st.subheader("Registrar novo Aporte")
        st.info("Lance aqui todo dinheiro 'novo' que saiu do seu bolso (conta corrente) para a corretora.")
        
        with st.form("form_deposito", clear_on_submit=True):
            col1, col2 = st.columns(2)
            data_deposito = col1.date_input("Data do Depósito", value=datetime.today(), format="DD/MM/YYYY")
            valor_deposito = col2.number_input("Valor (R$)", min_value=0.01, step=100.0, format="%.2f")
            
            submit = st.form_submit_button("💾 Salvar Depósito", use_container_width=True)
            if submit:
                data_str = data_deposito.strftime("%d/%m/%Y")
                if registrar_deposito(st.session_state.email, data_str, valor_deposito):
                    st.success(f"Depósito de R$ {valor_deposito:,.2f} em {data_str} salvo com sucesso!")

    # ==========================================
    # 2. COMPRA DE ATIVOS 
    # ==========================================
    elif tipo_lancamento == "🛒 2. Compra de Ativos":
        st.subheader("Registrar Compra")
        st.info("O sistema garante que você só registre ativos que pertençam à categoria correta.")
        
        # --- PAINEL RETRÁTIL COM AS RECOMENDAÇÕES (NOVIDADE) ---
        with st.expander("💡 Precisa de ajuda? Consultar Guia de Aportes Rápido", expanded=False):
            st.markdown("Descubra qual é o ativo mais atrasado na sua carteira neste momento:")
            c_val, c_num, c_btn = st.columns([2, 1, 1.2])
            val_simul = c_val.number_input("💵 Qual valor você tem para investir?", min_value=10.0, value=1000.0, step=100.0)
            num_simul = c_num.selectbox("Fatiar em quantas compras?", [1, 2, 3])
            
            if c_btn.button("Gerar Dica Rápida", use_container_width=True):
                with st.spinner("Calculando defasagem..."):
                    compras, resto, erro = motor_de_aportes(st.session_state.email, val_simul, num_simul)
                    
                if erro:
                    st.error(erro)
                elif not compras:
                    st.warning("Nenhuma sugestão gerada.")
                else:
                    for c in compras:
                        st.success(f"🎯 **Sugerido:** Comprar **{c['Ativo']}** ({c['Categoria']}) — Alocar **{formata_br(c['Valor'])}** (Aprox. {c['Qtd_Sugerida']})")
                    if resto > 0.05:
                        st.caption(f"⚠️ O sistema recomendou segurar **{formata_br(resto)}** na conta para não ultrapassar suas metas.")
        
        st.markdown("<br>", unsafe_allow_html=True)
        # -------------------------------------------------------

        cat_ativos_dict = obter_ativos_por_categoria()
        categorias_disp = list(cat_ativos_dict.keys())

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
            data_compra = c1.date_input("Data da Compra", value=datetime.today(), format="DD/MM/YYYY")
            qtd_compra = c2.number_input("Quantidade (Cotas/Títulos)", min_value=0.0001, step=1.0, format="%.4f")
            preco_compra = c3.number_input("Preço Médio Pago (R$)", min_value=0.01, step=1.0, format="%.2f")
            
            if st.button("🛒 Registrar Compra", use_container_width=True):
                data_str = data_compra.strftime("%d/%m/%Y")
                if registrar_compra(st.session_state.email, data_str, cat_compra, ativo_compra, qtd_compra, preco_compra):
                    st.success(f"Compra de {qtd_compra}x {ativo_compra} salva com sucesso na categoria {cat_compra}!")
