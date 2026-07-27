import streamlit as st
import pandas as pd
from utils import ler_planilha, registrar_novo_usuario, alterar_senha_esquecida

st.set_page_config(page_title="App Investimentos v1.0", layout="wide")

st.markdown("""
    <style>
        .block-container { padding-top: 2rem; padding-bottom: 2rem; }
        h1 { font-size: 1.8rem !important; padding-bottom: 0.5rem !important; }
        h2 { font-size: 1.5rem !important; }
        h3 { font-size: 1.2rem !important; }
        p { font-size: 0.95rem !important; }
    </style>
""", unsafe_allow_html=True)

# Importando as telas
from menu import resumo, saldo, aportes, configuracao, lancamentos, perfil

if 'logado' not in st.session_state:
    st.session_state.logado = False
    st.session_state.email = ""
    st.session_state.nome = ""
    # --- Variáveis para o fluxo de redefinição de senha ---
    st.session_state.codigo_recuperacao = None
    st.session_state.email_recuperacao = None

# ==========================================
# TELA DE ACESSO (DESLOGADO)
# ==========================================
if not st.session_state.logado:
    st.markdown("<h1 style='text-align: center;'>🔑 Acesso ao Sistema de Investimentos</h1>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # Sistema de Abas (Tabs) para organizar a interface
        tab_login, tab_cadastro, tab_esqueci = st.tabs(["Entrar", "Novo Cadastro", "Esqueci a Senha"])
        
        # --- ABA 1: LOGIN ---
        with tab_login:
            with st.form("form_login"):
                email_input = st.text_input("E-mail")
                senha_input = st.text_input("Senha", type="password")
                submit_login = st.form_submit_button("Entrar", use_container_width=True)
                
                if submit_login:
                    df_usuarios = ler_planilha("Usuarios")
                    if not df_usuarios.empty:
                        df_usuarios['Email'] = df_usuarios['Email'].astype(str).str.strip().str.lower()
                        df_usuarios['Senha'] = df_usuarios['Senha'].astype(str).str.strip()
                        
                        email_valido = email_input.strip().lower()
                        senha_valida = senha_input.strip()
                        
                        usuario = df_usuarios[(df_usuarios['Email'] == email_valido) & (df_usuarios['Senha'] == senha_valida)]
                        
                        if not usuario.empty:
                            status_usuario = str(usuario.iloc[0]['Status']).strip()
                            if status_usuario == 'Ativo':
                                st.session_state.logado = True
                                st.session_state.email = email_valido
                                st.session_state.nome = usuario.iloc[0]['Nome']
                                st.rerun()
                            elif status_usuario == 'Pendente':
                                st.warning("⏳ Seu cadastro está em análise. Aguarde a liberação do administrador.")
                            else:
                                st.error("❌ Seu acesso foi revogado ou bloqueado.")
                        else:
                            st.error("Usuário ou senha incorretos.")
                    else:
                        st.error("Erro ao acessar base de dados.")

        # --- ABA 2: NOVO CADASTRO ---
        with tab_cadastro:
            with st.form("form_cadastro", clear_on_submit=True):
                st.info("Preencha os dados abaixo. Seu acesso será liberado após a aprovação do administrador.")
                cad_nome = st.text_input("Seu Nome Completo")
                cad_email = st.text_input("Seu melhor E-mail")
                cad_senha = st.text_input("Crie uma Senha", type="password")
                
                submit_cadastro = st.form_submit_button("Enviar Solicitação de Acesso", use_container_width=True)
                
                if submit_cadastro:
                    if not cad_nome or not cad_email or not cad_senha:
                        st.warning("Preencha todos os campos obrigatórios.")
                    else:
                        with st.spinner("Registrando..."):
                            sucesso, msg = registrar_novo_usuario(cad_nome, cad_email, cad_senha)
                            if sucesso: st.success(msg)
                            else: st.error(msg)
                            
        # --- ABA 3: ESQUECI A SENHA ---
        with tab_esqueci:
            if not st.session_state.codigo_recuperacao:
                # ETAPA 1: Solicitar o E-mail e Disparar o Código
                with st.form("form_pedir_codigo"):
                    st.info("Digite seu e-mail cadastrado. Enviaremos um código de 6 caracteres para validar sua identidade.")
                    esq_email = st.text_input("E-mail Cadastrado")
                    submit_pedir = st.form_submit_button("Enviar Código de Segurança", use_container_width=True)
                    
                    if submit_pedir:
                        if not esq_email:
                            st.warning("Preencha o campo de e-mail.")
                        else:
                            with st.spinner("Verificando cadastro e enviando e-mail..."):
                                from utils import verificar_email_cadastrado, enviar_codigo_email
                                import random, string
                                
                                if verificar_email_cadastrado(esq_email):
                                    # Gera um código alfanumérico de 6 dígitos
                                    codigo_gerado = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                                    
                                    sucesso, msg = enviar_codigo_email(esq_email, codigo_gerado)
                                    if sucesso:
                                        st.session_state.codigo_recuperacao = codigo_gerado
                                        st.session_state.email_recuperacao = esq_email.strip().lower()
                                        st.rerun()
                                    else:
                                        st.error(msg)
                                else:
                                    st.error("Este e-mail não foi encontrado em nossa base de dados.")
            else:
                # ETAPA 2: Validar o Código e Gravar Nova Senha
                with st.form("form_nova_senha"):
                    st.success(f"📧 O código foi enviado para **{st.session_state.email_recuperacao}**!")
                    
                    codigo_digitado = st.text_input("Digite o código de 6 caracteres")
                    st.markdown("---")
                    esq_nova_senha = st.text_input("Nova Senha", type="password")
                    esq_confirma_senha = st.text_input("Confirme a Nova Senha", type="password")
                    
                    c_btn1, c_btn2 = st.columns(2)
                    submit_validar = c_btn1.form_submit_button("Salvar Nova Senha", use_container_width=True)
                    submit_cancelar = c_btn2.form_submit_button("Cancelar", use_container_width=True)
                    
                    if submit_cancelar:
                        st.session_state.codigo_recuperacao = None
                        st.session_state.email_recuperacao = None
                        st.rerun()
                        
                    if submit_validar:
                        if not codigo_digitado or not esq_nova_senha or not esq_confirma_senha:
                            st.warning("Preencha todos os campos obrigatórios.")
                        elif codigo_digitado.strip().upper() != st.session_state.codigo_recuperacao:
                            st.error("❌ Código incorreto. Verifique o e-mail e tente novamente.")
                        elif esq_nova_senha != esq_confirma_senha:
                            st.error("❌ As senhas não conferem.")
                        else:
                            with st.spinner("Atualizando credenciais..."):
                                from utils import redefinir_senha_aprovada
                                sucesso, msg = redefinir_senha_aprovada(st.session_state.email_recuperacao, esq_nova_senha)
                                if sucesso:
                                    st.success(msg)
                                    st.info("Acesse a aba 'Entrar' para fazer o login.")
                                    # Limpa a memória para permitir novos acessos
                                    st.session_state.codigo_recuperacao = None
                                    st.session_state.email_recuperacao = None
                                else:
                                    st.error(msg)


# ==========================================
# TELA INTERNA (LOGADO)
# ==========================================
else:
    st.sidebar.write(f"👤 **{st.session_state.nome}**")
    st.sidebar.markdown("---")
    
    menu_selecionado = st.sidebar.radio(
        "Navegação / Painéis:",
        [
            "💼 Resumo da Aplicação", 
            "📈 Evolução do Saldo", 
            "🎯 Guia de Aportes", 
            "📝 Lançamentos", 
            "⚙️ Configuração da Carteira",
            "👤 Meu Perfil"
        ]
    )
    
    st.sidebar.markdown("---")
    if st.sidebar.button("Sair do App"):
        st.session_state.clear()
        st.rerun()

    # Roteamento 
    if menu_selecionado == "💼 Resumo da Aplicação": resumo.render()
    elif menu_selecionado == "📈 Evolução do Saldo": saldo.render()
    elif menu_selecionado == "🎯 Guia de Aportes": aportes.render()
    elif menu_selecionado == "📝 Lançamentos": lancamentos.render()
    elif menu_selecionado == "⚙️ Configuração da Carteira": configuracao.render()
    elif menu_selecionado == "👤 Meu Perfil": perfil.render()
