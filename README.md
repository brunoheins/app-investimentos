# 📈 App Investimentos - Sistema de Gestão de Carteira

Este é um aplicativo web desenvolvido em **Python + Streamlit** para gestão de portfólio de investimentos. Ele permite definir metas de alocação (macro e micro), registrar aportes, lançar compras de ativos e calcular automaticamente o rebalanceamento ideal da carteira com base na defasagem dos ativos.

---

## 🏗️ Arquitetura do Projeto para IA (Contexto Mestre)

Este projeto foi construído de forma modular para facilitar a manutenção e escalabilidade. Qualquer IA assistente atuando neste repositório deve respeitar a estrutura abaixo:

### 1. Estrutura de Arquivos
```text
/app-investimentos-main/
│
├── app.py                 # Ponto de entrada (Entrypoint). Gerencia Login, 2FA e st.navigation.
├── utils.py               # Motor de regras (Banco de Dados, Autenticação, Disparo de E-mails).
├── requirements.txt       # Dependências do projeto (streamlit, pandas, plotly, gspread, etc).
│
└── menu/                  # Módulos das telas (Roteamento nativo)
    ├── __init__.py        
    ├── resumo.py          # Dashboard geral com gráficos (Plotly).
    ├── saldo.py           # Gráfico de evolução patrimonial histórica.
    ├── aportes.py         # Motor de rebalanceamento (Onde investir o próximo aporte).
    ├── lancamentos.py     # Inputs de novos depósitos e registro de compras de ativos.
    ├── configuracao.py    # Definição de metas Macro (ex: RF vs RV) e Micro (Pesos por Ativo).
    └── perfil.py          # Edição de dados do usuário e alteração de senha.
2. Stack Tecnológico
Frontend/Roteamento: Streamlit (st.navigation, st.Page, st.tabs, st.pills).

Manipulação de Dados: Pandas (pd.DataFrame).

Visualização: Plotly Express (px.pie, etc.).

Banco de Dados (BaaS): Google Sheets API via biblioteca gspread e google.oauth2.

Segurança e Notificações: Disparo de e-mails via smtplib usando Gmail (App Passwords) para Autenticação de 2 Fatores (2FA) na recuperação de senha.

⚙️ Especificação Técnica e Regras de Negócio
A. Gestão de Estado (Session State)
O aplicativo depende fortemente do st.session_state para persistir informações. Variáveis essenciais que a IA não deve sobrescrever acidentalmente:

st.session_state.logado (Booleano)

st.session_state.email (Chave primária do usuário nas queries)

st.session_state.nome (Usado para UI)

st.session_state.codigo_recuperacao / email_recuperacao (Fluxo de 2FA)

st.session_state.dicas_salvas (Cache do motor de aportes na tela de Lançamentos)

st.session_state.backup_macro (Cofre de restauração para a tela de Configuração)

st.session_state.aba_lancamento e st.session_state.aba_config (Navegação interna via botões inteligentes).

B. Fluxo de Autenticação e Segurança
Cadastro: Novos usuários são registrados com status "Pendente". Requer liberação manual do admin na planilha.

Login: Acesso restrito. E-mail é tratado sempre com .strip().lower() para evitar falhas.

Recuperação de Senha (2FA):

Etapa 1: Pede o e-mail, gera um token alfanumérico de 6 dígitos e envia via SMTP do Gmail.

Etapa 2: Valida o token contra o armazenado na sessão antes de atualizar o banco de dados.

C. Padrões de Interface (UI/UX)
Botões de Ação Principal: Devem sempre utilizar componentes nativos (st.button) com os parâmetros use_container_width=True e type="primary".

Gráficos: Sempre usar use_container_width=True na plotagem do Plotly.

📊 Guia de Estruturação do Banco de Dados (Google Sheets)
O sistema utiliza o Google Sheets como banco de dados. A leitura feita pelo arquivo utils.py é abstrata, ou seja, ele lê a primeira linha de cada aba para descobrir em qual coluna estão os dados (ex: cabecalho.index('email')).

Para o sistema funcionar perfeitamente, crie uma planilha chamada App_Investimentos e crie as seguintes abas (o nome da aba deve ser exato, e a Linha 1 deve conter exatamente os nomes das colunas abaixo):

Aba 1: Usuarios
Gerencia o acesso ao sistema.

Colunas (Linha 1): Nome | Email | Senha | Status

Nota: O campo Status deve conter "Ativo", "Pendente" ou "Bloqueado". O admin deve mudar manualmente de Pendente para Ativo após o cadastro.

Aba 2: Configuracao
Guarda as metas Macro de cada usuário (A soma final é garantida pela lógica do frontend).

Colunas (Linha 1): Email | RF | RV | RV_Brasil | RV_Exterior | BR_Acoes | BR_FIIs | EX_Stocks | EX_REITs | EX_ETFs

Aba 3: Ativos_Config
Guarda os ativos escolhidos pelo usuário e seus pesos desejados por categoria.

Colunas (Linha 1): Email | Categoria | Ativo | Peso

Aba 4: Aportes
Registra as entradas de dinheiro (depósitos) enviadas para a corretora.

Colunas (Linha 1): Email | Data | Valor

Aba 5: Lancamentos
Registra o histórico de compras de ativos.

Colunas (Linha 1): Email | Data | Categoria | Ativo | Quantidade | Preco

Aba 6: Cotacao
(Uso pelo motor de aportes e atualização de saldo). Aba contendo o preço atualizado dos ativos.

Colunas (Linha 1): Categoria | Ativo | Preco_Atual

🚀 Como Executar o Projeto
1. Clonar e Instalar Dependências
Bash
git clone [https://github.com/seu-usuario/app-investimentos.git](https://github.com/seu-usuario/app-investimentos.git)
cd app-investimentos
pip install -r requirements.txt
2. Configurar Variáveis de Ambiente (Secrets)
Crie um diretório .streamlit na raiz do projeto e dentro dele um arquivo secrets.toml contendo as credenciais do Google Cloud e do e-mail disparador:

Ini, TOML
# Credenciais da Service Account do Google Cloud (GCP)
gcp_service_account = '{"type": "service_account", "project_id": "...", "private_key": "...", ...}'

# Credenciais de e-mail para 2FA
[email]
endereco = "seu-email@gmail.com"
senha_app = "sua_senha_de_app_de_16_caracteres"
3. Rodar a Aplicação
Bash
streamlit run app.py
🤖 Nota para Assistentes de IA / LLMs: Ao receber este arquivo como contexto para implementar novas funcionalidades, mantenha a modularidade das telas dentro da pasta /menu/, sempre declare as variáveis no st.session_state antes do seu uso, utilize botões nativos (st.button) em vez de HTML, e manipule o banco de dados de forma abstrata passando as regras exclusivamente para o arquivo utils.py.
