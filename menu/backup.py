import streamlit as st
import pandas as pd
from io import BytesIO
from utils import ler_planilha, deletar_registros_usuario, inserir_lote_registros

def render():
    st.title("📊 Importar e Exportar Dados (Excel)")
    st.markdown("Faça o backup completo ou a restauração dos seus dados utilizando planilhas do Excel (.xlsx).")
    
    email_logado = st.session_state.email.strip().lower()
    
    tab_export, tab_import = st.tabs(["📤 Exportar para Excel", "📥 Importar do Excel"])
    
    # ==========================================
    # LÓGICA DE EXPORTAÇÃO (EXCEL)
    # ==========================================
    with tab_export:
        st.subheader("Gerar Planilha de Backup")
        st.write("Baixe todas as suas informações em um arquivo Excel consolidado. O arquivo conterá abas separadas para cada seção, preservando sua privacidade (sem a coluna de e-mail).")
        
        if st.button("Gerar Arquivo Excel", use_container_width=True):
            with st.spinner("Compilando seus dados em Excel..."):
                abas_alvo = ["Configuracao", "Depositos", "Investimentos"]
                
                # Utiliza o BytesIO para gerar o arquivo Excel na memória RAM
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    tem_dados = False
                    for aba in abas_alvo:
                        df = ler_planilha(aba)
                        if not df.empty and 'Email' in df.columns:
                            df['Email'] = df['Email'].astype(str).str.strip().str.lower()
                            meus_dados = df[df['Email'] == email_logado].copy()
                            
                            if not meus_dados.empty:
                                # Remove a coluna de Email para privacidade
                                meus_dados = meus_dados.drop(columns=['Email'])
                                meus_dados.to_excel(writer, sheet_name=aba, index=False)
                                tem_dados = True
                            else:
                                # Cria uma aba vazia com o cabeçalho original para manter a estrutura
                                df_vazio = df.drop(columns=['Email']).iloc[0:0]
                                df_vazio.to_excel(writer, sheet_name=aba, index=False)
                        else:
                            # Se a aba principal estiver totalmente vazia
                            pd.DataFrame().to_excel(writer, sheet_name=aba, index=False)
                
                processed_data = output.getvalue()
                
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
                # Lê todas as abas do arquivo Excel para um dicionário de DataFrames
                xls = pd.ExcelFile(arquivo_upload)
                
                st.info(f"Arquivo lido com sucesso! Abas encontradas: {', *'.join(xls.sheet_names)}")
                
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
                    with st.spinner("Processando restauração dos dados..."):
                        
                        abas_alvo = ["Configuracao", "Depositos", "Investimentos"]
                        
                        for aba in abas_alvo:
                            if aba in xls.sheet_names:
                                df_novo = pd.read_excel(xls, sheet_name=aba)
                                
                                # Remove linhas que venham totalmente vazias por acidente
                                df_novo = df_novo.dropna(how='all')
                                
                                if not df_novo.empty:
                                    # Injeta o e-mail exclusivo do usuário logado
                                    df_novo['Email'] = email_logado
                                    
                                    # A aba de Configuração sempre substitui os dados antigos por ser única por usuário
                                    if aba == "Configuracao" or modo_importacao.startswith("Substituir Tudo"):
                                        deletar_registros_usuario(aba, email_logado)
                                    
                                    inserir_lote_registros(aba, df_novo)
                                elif modo_importacao.startswith("Substituir Tudo"):
                                    deletar_registros_usuario(aba, email_logado)
                                    
                    st.success("✅ Restauração via Excel concluída com sucesso! Atualize a página ou navegue pelo menu para visualizar suas informações.")
                    
            except Exception as e:
                st.error(f"Erro ao ler ou processar a planilha. Verifique se o arquivo segue o formato correto. Detalhes: {e}")
                
