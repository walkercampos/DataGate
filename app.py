import pandas as pd
import streamlit as st
from pathlib import Path

MODELO_PATH = Path(__file__).parent / "modelo_base.xlsx"
SHEET_DADOS = "dados"
SHEET_REGRAS = "regras"

st.set_page_config(page_title="Check in RPA", page_icon="🤖", layout="centered")


@st.cache_data
def carregar_modelo():
    colunas_obrigatorias = pd.read_excel(MODELO_PATH, sheet_name=SHEET_DADOS).columns.tolist()
    regras = pd.read_excel(MODELO_PATH, sheet_name=SHEET_REGRAS)
    return colunas_obrigatorias, regras


def validar_estrutura(df_usuario, colunas_obrigatorias):
    return [c for c in colunas_obrigatorias if c not in df_usuario.columns]


def validar_preenchimento(df_usuario, colunas_obrigatorias):
    erros = []
    for coluna in colunas_obrigatorias:
        vazio = df_usuario[coluna].isna() | (df_usuario[coluna].astype(str).str.strip() == "")
        for idx in df_usuario[vazio].index:
            erros.append(
                {
                    "Linha no Excel": idx + 2,
                    "Coluna com Erro": coluna,
                    "Descrição do Problema": "Campo obrigatório não preenchido",
                }
            )
    return pd.DataFrame(erros, columns=["Linha no Excel", "Coluna com Erro", "Descrição do Problema"]).sort_values(
        "Linha no Excel"
    ).reset_index(drop=True)


st.title("🤖 Check in RPA")
st.caption("Valide sua planilha antes de enviar para a automação.")
st.divider()

if not MODELO_PATH.exists():
    st.error("Arquivo `modelo_base.xlsx` não encontrado na raiz do projeto.")
    st.stop()

colunas_obrigatorias, regras = carregar_modelo()

arquivo = st.file_uploader("Arraste seu arquivo .xlsx aqui ou clique para selecionar", type=["xlsx"])

if arquivo is not None:
    try:
        df_usuario = pd.read_excel(arquivo, sheet_name=SHEET_DADOS)
    except ValueError:
        st.error(f"O arquivo enviado não possui uma aba chamada **'{SHEET_DADOS}'**.")
        st.stop()

    colunas_faltantes = validar_estrutura(df_usuario, colunas_obrigatorias)

    if colunas_faltantes:
        st.error("❌ **Estrutura inválida.** As colunas obrigatórias abaixo não foram encontradas na planilha:")
        st.markdown("\n".join(f"- `{coluna}`" for coluna in colunas_faltantes))
    else:
        erros = validar_preenchimento(df_usuario, colunas_obrigatorias)

        if not erros.empty:
            st.error(f"❌ **{len(erros)} erro(s) de preenchimento encontrado(s).**")
            st.dataframe(erros, use_container_width=True, hide_index=True)
        else:
            st.success("✅ **Planilha validada com sucesso!** Arquivo liberado para a automação.")
            st.balloons()

st.divider()
with st.expander("📖 Regras de preenchimento"):
    st.dataframe(regras, use_container_width=True, hide_index=True)
