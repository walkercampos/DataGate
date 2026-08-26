import pandas as pd
from pathlib import Path

OUTPUT_PATH = Path(__file__).parent.parent / "modelo_base.xlsx"

COLUNAS_DADOS = [
    "Nome Completo",
    "CPF",
    "Data de Nascimento",
    "E-mail",
    "Telefone",
    "Cargo",
    "Departamento",
    "Data de Admissão",
    "Salário",
]

REGRAS = pd.DataFrame(
    [
        {"Campo": "Nome Completo", "Formato Esperado": "Texto", "Obrigatório": "Sim", "Observação": "Nome e sobrenome do colaborador, sem abreviações."},
        {"Campo": "CPF", "Formato Esperado": "000.000.000-00", "Obrigatório": "Sim", "Observação": "Somente números ou com pontuação, sem espaços."},
        {"Campo": "Data de Nascimento", "Formato Esperado": "DD/MM/AAAA", "Obrigatório": "Sim", "Observação": "Data válida e anterior à data atual."},
        {"Campo": "E-mail", "Formato Esperado": "nome@empresa.com", "Obrigatório": "Sim", "Observação": "E-mail corporativo válido."},
        {"Campo": "Telefone", "Formato Esperado": "(00) 00000-0000", "Obrigatório": "Sim", "Observação": "Com DDD, apenas um contato por linha."},
        {"Campo": "Cargo", "Formato Esperado": "Texto", "Obrigatório": "Sim", "Observação": "Cargo oficial conforme cadastro do RH."},
        {"Campo": "Departamento", "Formato Esperado": "Texto", "Obrigatório": "Sim", "Observação": "Departamento oficial conforme organograma."},
        {"Campo": "Data de Admissão", "Formato Esperado": "DD/MM/AAAA", "Obrigatório": "Sim", "Observação": "Data válida e anterior ou igual à data atual."},
        {"Campo": "Salário", "Formato Esperado": "Número", "Obrigatório": "Sim", "Observação": "Utilizar ponto como separador decimal, sem símbolo de moeda."},
    ]
)

df_dados = pd.DataFrame(columns=COLUNAS_DADOS)

with pd.ExcelWriter(OUTPUT_PATH, engine="openpyxl") as writer:
    REGRAS.to_excel(writer, sheet_name="regras", index=False)
    df_dados.to_excel(writer, sheet_name="dados", index=False)

print(f"Modelo gerado em: {OUTPUT_PATH}")
