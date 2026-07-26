import streamlit as st
from utils import ler_planilha

def render():
    st.title("📈 Histórico de Saldo")
    df_saldo = ler_planilha("Saldo")
    if not df_saldo.empty:
        df_saldo['Email'] = df_saldo['Email'].astype(str).str.strip().str.lower()
        dados = df_saldo[df_saldo['Email'] == st.session_state.email]
        if not dados.empty:
            st.line_chart(dados.set_index('Data')['Valor'], height=400)
        else:
            st.info("Sem histórico.")