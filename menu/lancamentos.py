import streamlit as st
import pandas as pd
from datetime import datetime
from utils import ler_planilha, registrar_deposito, registrar_compra, obter_cotacoes

def render():
    st.title("📝 Central de Lançamentos")
    st.markdown("Registre a entrada de dinheiro novo na corretora e as suas ordens de compra.")

    # Navegação interna
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
        st.info("Só é possível registrar compras de ativos que já estejam cadastrados na sua aba 'Cotacao'.")
        
        # 1. BUSCA A LISTA DE ATIVOS PERMITIDOS (DA ABA COTAÇÃO)
        cotacoes_dict = obter_cotacoes()
        ativos_permitidos = sorted(list(cotacoes_dict.keys()))
        
        if not ativos_permitidos:
            st.error("⚠️ Nenhum ativo encontrado na aba 'Cotacao'. Por favor, cadastre os ativos e os preços atuais na planilha antes de registrar uma compra.")
            return

        # 2. BUSCA AS CATEGORIAS PARA O MENU
        df_ativos = ler_planilha("Ativos_Config")
        categorias_disp = ["Ações", "FIIs", "Stocks", "REITs", "ETFs", "Renda Fixa"]
        
        if not df_ativos.empty:
            df_ativos['Email'] = df_ativos['Email'].astype(str).str.strip().str.lower()
            df_user_ativos = df_ativos[df_ativos['Email'] == st.session_state.email]
            if not df_user_ativos.empty:
                categorias_disp = df_user_ativos['Categoria'].unique().tolist()

        with st.form("form_compra", clear_on_submit=True):
            c1, c2, c3 = st.columns([1, 1, 1.5])
            data_compra = c1.date_input("Data da Compra", value=datetime.today(), format="DD/MM/YYYY")
            cat_compra = c2.selectbox("Categoria", categorias_disp)
            
            # 3. MUDANÇA AQUI: Dropdown pesquisável com a lista oficial da Cotação
            ativo_compra = c3.selectbox("Ativo (Digite para buscar)", options=ativos_permitidos)
            
            c4, c5 = st.columns(2)
            qtd_compra = c4.number_input("Quantidade (Cotas/Títulos)", min_value=0.0001, step=1.0, format="%.4f")
            preco_compra = c5.number_input("Preço Médio Pago (R$)", min_value=0.01, step=1.0, format="%.2f")
            
            submit_compra = st.form_submit_button("🛒 Registrar Compra", use_container_width=True)
            if submit_compra:
                if not ativo_compra:
                    st.warning("Selecione um ativo válido.")
                else:
                    data_str = data_compra.strftime("%d/%m/%Y")
                    # Envia a compra para o banco de dados
                    if registrar_compra(st.session_state.email, data_str, cat_compra, ativo_compra, qtd_compra, preco_compra):
                        st.success(f"Compra de {qtd_compra}x {ativo_compra} salva com sucesso na categoria {cat_compra}!")
