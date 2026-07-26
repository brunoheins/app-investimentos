# app-investimentos

# Documentação Funcional e Técnica: App de Investimentos

Esta documentação detalha o processo de criação, configuração e implantação do aplicativo de investimentos construído com Streamlit, utilizando o Google Sheets como banco de dados e o GitHub para controle de versão e hospedagem no Streamlit Community Cloud. O código-fonte está disponível em https://github.com/brunoheins/app-investimentos/.

## 1. Visão Geral da Arquitetura
* **Frontend & Lógica:** Streamlit (Python).
* **Banco de Dados:** Google Sheets (acessado via API do Google Cloud).
* **Controle de Versão:** GitHub.
* **Deploy (Hospedagem):** Streamlit Community Cloud.

## 2. Passo a Passo: Criação e Configuração do Banco de Dados (Google Sheets)
O aplicativo utiliza uma planilha do Google Sheets chamada `App_Investimentos` como seu banco de dados relacional. É crucial que a estrutura das abas seja mantida para o correto funcionamento da aplicação.

### 2.1. Estrutura da Planilha `App_Investimentos`
Crie uma nova planilha no seu Google Drive com o nome exato **App_Investimentos**. Adicione as seguintes abas (worksheets) e seus respectivos cabeçalhos na primeira linha:

#### Aba: Usuarios
| Email | Senha | Nome | Status |
| :--- | :--- | :--- | :--- |
| seu_email@exemplo.com | sua_senha | Seu Nome | Ativo |

#### Aba: Configuracao
Armazena as metas de alocação macro (em %).
| Email | RF | RV | RV_Brasil | RV_Exterior | BR_Acoes | BR_FIIs | EX_Stocks | EX_REITs | EX_ETFs |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| seu_email@exemplo.com | 50 | 50 | 50 | 50 | 50 | 50 | 40 | 30 | 30 |

#### Aba: Ativos_Config
Armazena a composição de ativos e seus respectivos pesos (em %) dentro de cada categoria.
| Email | Categoria | Ativo | Peso |
| :--- | :--- | :--- | :--- |
| seu_email@exemplo.com | Ações | PETR4 | 50.0 |

## 3. Passo a Passo: Integração com a API do Google Cloud (GCP)
Para que a aplicação Streamlit possa ler e gravar dados na planilha, é necessário criar credenciais de serviço no Google Cloud Platform.

1. Acesse o [Google Cloud Console](https://console.cloud.google.com/).
2. Crie um novo projeto (ex: `StreamlitAppInvestimentos`).
3. Navegue até **APIs e Serviços > Biblioteca**.
4. Pesquise e ative as seguintes APIs:
   * **Google Drive API**
   * **Google Sheets API**
5. Vá para **APIs e Serviços > Credenciais**.
6. Clique em **Criar Credenciais > Conta de Serviço**.
7. Preencha o nome da conta (ex: `streamlit-sheets-access`) e conclua a criação.
8. Na lista de Contas de Serviço, clique no e-mail recém-criado. Vá na aba **Chaves**.
9. Clique em **Adicionar Chave > Criar nova chave**. Escolha o formato **JSON**. O arquivo será baixado para o seu computador (nome similar a `credenciais.json`).
10. **ATENÇÃO:** Abra o arquivo JSON baixado e localize o campo `client_email`. Copie esse endereço de e-mail.
11. Vá até a sua planilha `App_Investimentos` no Google Drive, clique em **Compartilhar** e adicione o e-mail copiado com permissão de **Editor**.

## 4. Passo a Passo: Preparação do Ambiente Local e GitHub

### 4.1. Estrutura do Repositório Local
No seu computador, crie uma pasta para o projeto e adicione os seguintes arquivos essenciais:

```text
app-investimentos/
│
├── app.py                # Arquivo principal contendo todo o código Streamlit/Python
├── requirements.txt      # Dependências do projeto
├── .gitignore            # Arquivos ignorados pelo Git
└── .streamlit/
    └── secrets.toml      # Suas credenciais (APENAS PARA USO LOCAL - NÃO COMITAR)
