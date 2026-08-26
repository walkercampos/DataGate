# 🤖 Check in RPA

Validador minimalista de planilhas Excel, construído em Streamlit, para conferir se os arquivos enviados pelos usuários seguem a estrutura exigida pelas automações (RPA) antes do envio.

## Como funciona

A cada validação, o usuário sobe **duas planilhas** diretamente na interface — não há nenhum modelo fixo salvo no repositório, então o app funciona para **qualquer** tipo de planilha (RH, fornecedores, notas fiscais, etc.), cada uma com suas próprias regras:

1. **Planilha modelo (referência oficial)** — define a estrutura correta.
2. **Planilha do solicitante** — o arquivo que será validado.

Com as duas em mãos, o app faz:

- **Etapa 1 — Validação estrutural:** confere se todas as colunas presentes na aba `dados` da planilha **modelo** também existem na aba `dados` da planilha do **solicitante**. Se faltar alguma, o envio é rejeitado.
- **Etapa 2 — Validação de preenchimento:** se a estrutura estiver correta, percorre linha a linha as colunas obrigatórias (as mesmas colunas da planilha modelo) procurando células vazias na planilha do solicitante, reportando o número exato da linha no Excel.
- Se não houver erros, o arquivo é aprovado para a automação.
- Se a planilha modelo tiver uma aba `regras`, seu conteúdo aparece num expander explicativo para o solicitante.

Como a comparação é sempre feita contra a planilha modelo enviada no momento, **não é preciso alterar nada no código para validar um novo tipo de planilha** — basta subir o modelo correspondente.

## Estrutura do repositório

```
.
├── app.py                       # Interface e lógica de validação (Streamlit)
├── modelo_base.xlsx             # Exemplo de planilha modelo (estrutura + regras)
├── requirements.txt             # Dependências do projeto
├── .streamlit/
│   └── config.toml              # Tema visual minimalista
└── scripts/
    └── gerar_modelo_base.py     # Script auxiliar para gerar novos modelos de exemplo
```

## Estrutura esperada da planilha modelo

Cada planilha **modelo** (a de referência, subida no campo 1 da interface) segue a mesma convenção de abas, qualquer que seja o processo de RPA:

### Aba `dados` (obrigatória)
Contém **apenas o cabeçalho oficial**, sem nenhuma linha de dados. Cada coluna do cabeçalho é tratada como um campo **obrigatório** que a planilha do solicitante precisa ter, preenchido em todas as linhas.

| Nome Completo | CPF | Data de Nascimento | E-mail | Telefone | Cargo | Departamento | Data de Admissão | Salário |
|---|---|---|---|---|---|---|---|---|

*(linha de cabeçalho apenas — sem dados abaixo)*

### Aba `regras` (opcional)
Documentação livre, exibida ao solicitante no expander "📖 Regras de preenchimento" da interface. Se a planilha modelo não tiver essa aba, o expander simplesmente não aparece. Sugestão de colunas:

| Campo | Formato Esperado | Obrigatório | Observação |
|---|---|---|---|
| Nome Completo | Texto | Sim | Nome e sobrenome, sem abreviações |
| CPF | 000.000.000-00 | Sim | ... |

O `modelo_base.xlsx` na raiz do projeto é apenas **um exemplo** desse formato — não é lido automaticamente pelo app. Para criar modelos novos (um por tipo de planilha/processo de RPA), edite as colunas de `COLUNAS_DADOS` e o conteúdo de `REGRAS` em `scripts/gerar_modelo_base.py` e rode:

```bash
python scripts/gerar_modelo_base.py
```

ou simplesmente monte o `.xlsx` direto no Excel, mantendo os nomes das abas `dados` e (opcionalmente) `regras`, e suba esse arquivo no campo "Planilha modelo" da interface sempre que for validar aquele tipo de planilha.

## Rodando localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Publicando no Streamlit Community Cloud

1. Suba este repositório para o GitHub.
2. Acesse [share.streamlit.io](https://share.streamlit.io) e conecte sua conta do GitHub.
3. Selecione o repositório, o branch e defina `app.py` como arquivo principal.
4. Clique em **Deploy**. O Streamlit Cloud instala as dependências de `requirements.txt` automaticamente.
