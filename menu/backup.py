import streamlit as st
import pandas as pd
import tempfile
import os
from utils import ler_planilha, deletar_registros_usuario, inserir_lote_registros

def render():
    st.title("📊 Importar e Exportar Dados (Excel)")
    st.markdown("Faça o backup completo ou a restauração dos seus dados utilizando planilhas do Excel (.xlsx).")
    
    email_logado = st.session_state.email.strip().lower()
    
    tab_export, tab_import = st.tabs(["📤 Exportar para Excel", "📥 Importar do Excel"])
    
    # ==========================================
    # LÓGICA DE EXPORTAÇÃO (EXCEL FÍSICO)
    # ==========================================
    with tab_export:
        st.subheader("Gerar Planilha de Backup")
        st.write("Baixe todas as suas informações em um arquivo Excel consolidado. O arquivo conterá abas separadas para cada seção, preservando sua privacidade (sem a coluna de e-mail).")
        
        if st.button("Gerar Arquivo Excel", use_container_width=True):
            with st.spinner("Compilando seus dados em Excel..."):
                abas_alvo = ["Configuracao", "Depositos", "Investimentos"]
                
                # Cria um arquivo temporário real no disco do servidor
                with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                    caminho_temp = tmp.name
                    
                try:
                    # Salva os dados nesse arquivo físico (Resolve o problema do Google Drive)
                    with pd.ExcelWriter(caminho_temp, engine='xlsxwriter') as writer:
                        for aba in abas_alvo:
                            df = ler_planilha(aba)
                            if not df.empty and 'Email' in df.columns:
                                df['Email'] = df['Email'].astype(str).str.strip().str.lower()
                                meus_dados = df[df['Email'] == email_logado].copy()
                                
                                if not meus_dados.empty:
                                    meus_dados = meus_dados.drop(columns=['Email'])
                                    meus_dados.to_excel(writer, sheet_name=aba, index=False)
                                else:
                                    pd.DataFrame({"Aviso": ["Aba sem dados"]}).to_excel(writer, sheet_name=aba, index=False)
                            else:
                                pd.DataFrame({"Aviso": ["Aba sem dados"]}).to_excel(writer, sheet_name=aba, index=False)
                                
                    # Lê o arquivo recém-criado em modo binário
                    with open(caminho_temp, "rb") as f:
                        processed_data = f.read()
                        
                finally:
                    # Limpa o arquivo do disco imediatamente após ler (segurança e performance)
                    if os.path.exists(caminho_temp):
                        os.remove(caminho_temp)
                
                st.success("Planilha de backup gerada com sucesso!")
                st.download_button(
                    label="⬇️ Baixar Planilha de Backup (.xlsx)",
                    data=processed_data,
                    file_name="meu_backup_investimentos.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

    # ==========================================
    # LÓGICA DE IMPORTAÇÃO (EXCEL)
    # ==========================================
    with tab_import:
        st.subheader("Restaurar a partir de Planilha Excel")
        st.write("Suba o arquivo `.xlsx` de backup gerado anteriormente pelo sistema.")
        
        arquivo_upload = st.file_uploader("Selecione o arquivo Excel de backup", type=["xlsx"])
        
        if arquivo_upload is not None:
            try:
                xls = pd.ExcelFile(arquivo_upload)
                st.info(f"Arquivo lido com sucesso! Abas encontradas: {', '.join(xls.sheet_names)}")
                
                modo_importacao = st.radio(
                    "Modo de Restauração:",
                    options=[
                        "Substituir Tudo (Apaga os dados atuais e carrega apenas o arquivo)",
                        "Mesclar (Sobrepõe as configurações, mas apenas acrescenta os depósitos e investimentos)"
                    ],
                    index=0
                )
                
                st.warning("⚠️ Atenção: Esta ação irá modificar seu banco de dados na nuvem e não poderá ser desfeita.")
                
                if st.button("🚀 Iniciar Restauração via Excel", type="primary", use_container_width=True):
                    with st.spinner("Processando restauração dos dados... Isso pode demorar um pouco."):
                        
                        abas_alvo = ["Configuracao", "Depositos", "Investimentos"]
                        teve_erro = False
                        
                        for aba in abas_alvo:
                            if aba in xls.sheet_names:
                                df_novo = pd.read_excel(xls, sheet_name=aba)
                                df_novo = df_novo.dropna(how='all')
                                
                                # Ignora as abas de aviso
                                if not df_novo.empty and "Aviso" not in df_novo.columns:
                                    df_novo['Email'] = email_logado
                                    
                                    if aba == "Configuracao" or modo_importacao.startswith("Substituir Tudo"):
                                        sucesso_del, msg_del = deletar_registros_usuario(aba, email_logado)
                                        if not sucesso_del:
                                            st.error(f"Erro ao limpar aba {aba}: {msg_del}")
                                            teve_erro = True
                                    
                                    sucesso_ins, msg_ins = inserir_lote_registros(aba, df_novo)
                                    if not sucesso_ins:
                                        st.error(f"Erro ao gravar aba {aba}: {msg_ins}")
                                        teve_erro = True
                                        
                                elif modo_importacao.startswith("Substituir Tudo"):
                                    sucesso_del, msg_del = deletar_registros_usuario(aba, email_logado)
                                    if not sucesso_del:
                                        st.error(f"Erro ao limpar aba {aba}: {msg_del}")
                                        teve_erro = True
                                        
                        if not teve_erro:
                            st.success("✅ Restauração via Excel concluída com sucesso! Atualize a página ou navegue pelo menu para visualizar suas informações.")
                        else:
                            st.warning("⚠️ A restauração terminou, mas ocorreram alguns erros listados acima.")
                            
            except Exception as e:
                st.error(f"Erro ao ler ou processar a planilha. Verifique se o arquivo segue o formato correto. Detalhes: {e}")
