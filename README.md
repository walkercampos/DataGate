# 🤖 Check in RPA

Validador minimalista de planilhas Excel, construído em Streamlit, para conferir se os arquivos enviados pelos usuários seguem a estrutura exigida pelas automações (RPA) antes do envio.

## Como funciona

1. O app carrega o arquivo `modelo_base.xlsx` (na raiz do projeto), que define a estrutura oficial.
2. O usuário faz upload do próprio arquivo `.xlsx` pela interface.
3. **Etapa 1 — Validação estrutural:** o app confere se todas as colunas obrigatórias (definidas na aba `dados` do modelo) existem na aba `dados` do arquivo enviado. Se faltar alguma, o envio é rejeitado.
4. **Etapa 2 — Validação de preenchimento:** se a estrutura estiver correta, o app percorre linha a linha as colunas obrigatórias procurando células vazias, reportando o número exato da linha no Excel.
5. Se não houver erros, o arquivo é aprovado para a automação.

## Estrutura do repositório

```
.
├── app.py                       # Interface e lógica de validação (Streamlit)
├── modelo_base.xlsx             # Modelo oficial de referência (estrutura + regras)
├── requirements.txt             # Dependências do projeto
├── .streamlit/
│   └── config.toml              # Tema visual minimalista
└── scripts/
    └── gerar_modelo_base.py     # Script auxiliar para (re)gerar o modelo_base.xlsx
```

## Estrutura do `modelo_base.xlsx`

O arquivo modelo deve conter exatamente **duas abas**:

### Aba `dados`
Contém **apenas o cabeçalho oficial**, sem nenhuma linha de dados. Cada coluna do cabeçalho é tratada como um campo **obrigatório** que o arquivo do usuário precisa ter, preenchido em todas as linhas.

| Nome Completo | CPF | Data de Nascimento | E-mail | Telefone | Cargo | Departamento | Data de Admissão | Salário |
|---|---|---|---|---|---|---|---|---|

*(linha de cabeçalho apenas — sem dados abaixo)*

### Aba `regras`
Documentação livre, exibida ao usuário no expander "📖 Regras de preenchimento" da interface. Sugestão de colunas:

| Campo | Formato Esperado | Obrigatório | Observação |
|---|---|---|---|
| Nome Completo | Texto | Sim | Nome e sobrenome, sem abreviações |
| CPF | 000.000.000-00 | Sim | ... |

Para gerar (ou regenerar) esse arquivo com o exemplo padrão, rode:

```bash
python scripts/gerar_modelo_base.py
```

> Para adaptar o validador à sua empresa, edite as colunas de `COLUNAS_DADOS` e o conteúdo de `REGRAS` em `scripts/gerar_modelo_base.py` e rode o script novamente — ou edite `modelo_base.xlsx` diretamente no Excel, mantendo os nomes das abas `dados` e `regras`.

## Rodando localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Publicando no Streamlit Community Cloud

1. Suba este repositório para o GitHub (incluindo o `modelo_base.xlsx`).
2. Acesse [share.streamlit.io](https://share.streamlit.io) e conecte sua conta do GitHub.
3. Selecione o repositório, o branch e defina `app.py` como arquivo principal.
4. Clique em **Deploy**. O Streamlit Cloud instala as dependências de `requirements.txt` automaticamente.
