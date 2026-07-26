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
```

### 4.2. O Arquivo `requirements.txt`
Este arquivo informa ao Streamlit Cloud quais bibliotecas instalar. Exemplo:

```text
streamlit==1.41.0
pandas==2.2.3
gspread==6.1.4
google-auth==2.37.0
plotly==5.24.1
```

### 4.3. Configuração de Segredos Locais (Opcional, para testes)
Crie uma pasta oculta chamada `.streamlit` e dentro dela um arquivo `secrets.toml`. Adicione o conteúdo do seu arquivo JSON baixado do GCP no seguinte formato:

```toml
gcp_service_account = '''
{
  "type": "service_account",
  "project_id": "seu-projeto-id",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "seu-email@seu-projeto.iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "[https://accounts.google.com/o/oauth2/auth](https://accounts.google.com/o/oauth2/auth)",
  "token_uri": "[https://oauth2.googleapis.com/token](https://oauth2.googleapis.com/token)",
  "auth_provider_x509_cert_url": "[https://www.googleapis.com/oauth2/v1/certs](https://www.googleapis.com/oauth2/v1/certs)",
  "client_x509_cert_url": "..."
}
'''
```
**IMPORTANTE:** O arquivo `secrets.toml` e o JSON original **NUNCA** devem ser enviados (comitados) para o GitHub.

### 4.4. O Arquivo `.gitignore`
Para evitar vazamento de credenciais, crie um arquivo `.gitignore` com o conteúdo:

```text
.streamlit/
credenciais.json
__pycache__/
```

### 4.5. Enviando para o GitHub
1. Crie um repositório vazio no GitHub (ex: `app-investimentos`).
2. No terminal da sua máquina, dentro da pasta do projeto, execute:

```bash
git init
git add .
git commit -m "Commit inicial do App de Investimentos"
git branch -M main
git remote add origin [https://github.com/brunoheins/app-investimentos.git](https://github.com/brunoheins/app-investimentos.git)
git push -u origin main
```

## 5. Passo a Passo: Deploy (Implantação) no Streamlit Community Cloud
O Streamlit Community Cloud gerencia a hospedagem e detecta automaticamente novas atualizações (commits) feitas no repositório GitHub.

1. Acesse [share.streamlit.io](https://share.streamlit.io/) e faça login (recomenda-se usar a conta conectada ao GitHub).
2. Clique em **New app**.
3. Selecione **Use existing repo** (Usar repositório existente).
4. Preencha as informações:
   * **Repository:** `brunoheins/app-investimentos`
   * **Branch:** `main`
   * **Main file path:** `app.py`
5. **PASSO CRÍTICO - Gerenciamento de Segredos (Secrets):** Antes de clicar em "Deploy", clique em **Advanced settings** (Configurações avançadas).
6. No campo *Secrets*, cole o conteúdo do seu arquivo `secrets.toml` (criado no passo 4.3). O formato deve ser idêntico ao local.
7. Clique em **Save** e, em seguida, em **Deploy**.

## 6. Fluxo de Atualização (CI/CD)
Uma vez que o app está configurado, o processo de atualização (deploy) é automático.

1. Você realiza alterações no código (ex: modificando o `app.py` no seu computador).
2. Comita as alterações via Git:

```bash
git add app.py
git commit -m "Nova melhoria na UI"
git push origin main
```

3. O Streamlit Cloud detecta o "push" no branch `main` e reinicia a aplicação automaticamente com a nova versão, mantendo as credenciais seguras.

## 7. Principais Funcionalidades do Código (Referência Técnica)
* **Leitura de Planilhas:** Utiliza a biblioteca `gspread` autenticada com as credenciais do GCP. A função principal é `ler_planilha(nome_aba)`, que retorna um DataFrame do `pandas`.
* **Escrita de Dados:** Funções como `salvar_configuracao` e `salvar_ativos_categoria` fazem buscas na planilha, atualizam as linhas correspondentes ao usuário (email) e reescrevem os dados usando o método `sheet.update()`.
* **Gerenciamento de Estado:** O `st.session_state` é intensamente utilizado para manter informações entre recarregamentos da página, como o usuário logado (`email`), a aba ativa no menu de configurações e os valores temporários digitados nos inputs.
* **Otimização de Layout:** Injeção de CSS personalizado via `st.markdown` para compactar margens, reduzir tamanho de fontes e melhorar a exibição em monitores menores (ex: 14 polegadas).
* **Navegação Visual:** Substituição das abas nativas do Streamlit (`st.tabs`) por botões de navegação personalizados para maior destaque e controle de estado usando o parâmetro `type="primary"`/`type="secondary"`.
