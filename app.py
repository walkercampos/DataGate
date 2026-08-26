import pandas as pd
import streamlit as st

SHEET_DADOS = "dados"
SHEET_REGRAS = "regras"

st.set_page_config(page_title="Check in RPA", page_icon="🤖", layout="centered")


def ler_aba_dados(arquivo, rotulo):
    try:
        return pd.read_excel(arquivo, sheet_name=SHEET_DADOS)
    except ValueError:
        st.error(f"A **{rotulo}** não possui uma aba chamada **'{SHEET_DADOS}'**.")
        return None


def ler_aba_regras(arquivo):
    try:
        return pd.read_excel(arquivo, sheet_name=SHEET_REGRAS)
    except ValueError:
        return None


def validar_estrutura(df_solicitante, colunas_obrigatorias):
    return [c for c in colunas_obrigatorias if c not in df_solicitante.columns]


def validar_preenchimento(df_solicitante, colunas_obrigatorias):
    erros = []
    for coluna in colunas_obrigatorias:
        vazio = df_solicitante[coluna].isna() | (df_solicitante[coluna].astype(str).str.strip() == "")
        for idx in df_solicitante[vazio].index:
            erros.append(
                {
                    "Linha no Excel": idx + 2,
                    "Coluna com Erro": coluna,
                    "Descrição do Problema": "Campo obrigatório não preenchido",
                }
            )
    return (
        pd.DataFrame(erros, columns=["Linha no Excel", "Coluna com Erro", "Descrição do Problema"])
        .sort_values("Linha no Excel")
        .reset_index(drop=True)
    )


st.title("🤖 Check in RPA")
st.caption("Suba a planilha modelo (correta) e a planilha do solicitante para validar a estrutura e o preenchimento.")
st.divider()

col_modelo, col_solicitante = st.columns(2)
with col_modelo:
    arquivo_modelo = st.file_uploader("1. Planilha modelo (referência oficial)", type=["xlsx"], key="modelo")
with col_solicitante:
    arquivo_solicitante = st.file_uploader("2. Planilha do solicitante (a validar)", type=["xlsx"], key="solicitante")

if arquivo_modelo and arquivo_solicitante:
    df_modelo = ler_aba_dados(arquivo_modelo, "planilha modelo")
    df_solicitante = ler_aba_dados(arquivo_solicitante, "planilha do solicitante")

    if df_modelo is not None and df_solicitante is not None:
        colunas_obrigatorias = df_modelo.columns.tolist()
        colunas_faltantes = validar_estrutura(df_solicitante, colunas_obrigatorias)

        if colunas_faltantes:
            st.error(
                "❌ **Estrutura inválida.** As colunas obrigatórias abaixo (definidas na planilha modelo) "
                "não foram encontradas na planilha do solicitante:"
            )
            st.markdown("\n".join(f"- `{coluna}`" for coluna in colunas_faltantes))
        else:
            erros = validar_preenchimento(df_solicitante, colunas_obrigatorias)

            if not erros.empty:
                st.error(f"❌ **{len(erros)} erro(s) de preenchimento encontrado(s).**")
                st.dataframe(erros, use_container_width=True, hide_index=True)
            else:
                st.success("✅ **Planilha validada com sucesso!** Arquivo liberado para a automação.")
                st.balloons()

        regras = ler_aba_regras(arquivo_modelo)
        if regras is not None:
            st.divider()
            with st.expander("📖 Regras de preenchimento (da planilha modelo)"):
                st.dataframe(regras, use_container_width=True, hide_index=True)
elif arquivo_modelo or arquivo_solicitante:
    st.info("Envie as duas planilhas — modelo e solicitante — para iniciar a validação.")
