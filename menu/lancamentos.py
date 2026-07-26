import streamlit as st
import pandas as pd
from datetime import datetime
from utils import ler_planilha, registrar_deposito, registrar_compra, obter_ativos_por_categoria

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
    # 2. COMPRA DE ATIVOS (AGORA DINÂMICO E SEGURO)
    # ==========================================
    elif tipo_lancamento == "🛒 2. Compra de Ativos":
        st.subheader("Registrar Compra")
        st.info("O sistema garante que você só registre ativos que pertençam à categoria correta.")
        
        # Busca o dicionário onde as chaves são as Categorias e os valores são as listas de Ativos
        cat_ativos_dict = obter_ativos_por_categoria()
        categorias_disp = list(cat_ativos_dict.keys())

        # Seleção de Categoria e Ativo ficam FORA de um st.form para atualizarem em tempo real
        c_cat, c_atv = st.columns(2)
        cat_compra = c_cat.selectbox("1. Escolha a Categoria", categorias_disp)
        
        # Puxa apenas a coluna correspondente da planilha Cotacao
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
