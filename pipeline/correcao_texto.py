"""
pipeline/correcao_texto.py
-----------------------------
Correção de acentuação para colunas de texto em PT-BR.

Aplicado ANTES da regravação do staging no Postgres (pipeline/carga_staging.py),
para que tanto as tabelas `stg_*_bruto` quanto a camada Silver (que lê dessas
tabelas via SQL) fiquem com o texto corretamente acentuado.
"""

import unicodedata
import pandas as pd
from logger import log


def _fix_mojibake(valor: object) -> object:
    """
    Corrige o caso clássico de "dupla codificação" em PT-BR, em que texto
    UTF-8 foi lido/decodificado como Latin-1 (cp1252), gerando sequências
    como 'NÃ£o' no lugar de 'Não'.

    Estratégia: tenta reverter (encode latin1 -> decode utf-8). Se a string
    não estiver "quebrada" dessa forma, a operação falha silenciosamente e o
    valor original é mantido. Ao final, normaliza para a forma NFC (padrão
    Unicode mais comum/estável para acentos compostos).
    """
    if not isinstance(valor, str):
        return valor

    texto = valor
    try:
        texto = texto.encode("latin1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        # Texto já está correto (não passou por dupla codificação) — mantém.
        pass

    return unicodedata.normalize("NFC", texto)


def corrigir_acentuacao(df: pd.DataFrame, tabela: str) -> pd.DataFrame:
    """
    Aplica _fix_mojibake em todas as colunas de texto (string/object) do
    DataFrame. Colunas numéricas/datas são ignoradas automaticamente.
    """
    df = df.copy()
    colunas_texto = df.select_dtypes(include=["string", "object"]).columns

    for coluna in colunas_texto:
        df[coluna] = df[coluna].apply(_fix_mojibake)

    if len(colunas_texto):
        log.info(
            "  [acentuação] '%s': %d coluna(s) de texto verificada(s).",
            tabela, len(colunas_texto),
        )

    return df
