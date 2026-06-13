"""
pipeline/correcao_texto.py
--------------------------

Correção de acentuação e padronização de texto para PT-BR.

Responsabilidades:
1. Corrigir casos clássicos de mojibake/dupla codificação;
2. Normalizar caracteres Unicode para NFC;
3. Transformar todas as entradas textuais em maiúsculas.

Aplicado antes da carga na Bronze física, garantindo que as camadas
Bronze, Silver e Gold recebam textos padronizados.
"""

import unicodedata

import pandas as pd

from logger import log


def _corrigir_texto(valor: object) -> object:
    """
    Corrige textos com possível problema de dupla codificação e
    padroniza a saída em maiúsculas.

    Exemplo de correção:
        'NÃ£O INFORMADO' -> 'NÃO INFORMADO'

    Etapas:
    1. Verifica se o valor é string;
    2. Tenta corrigir mojibake com encode latin1 -> decode utf-8;
    3. Normaliza Unicode em NFC;
    4. Aplica upper case.
    """
    if not isinstance(valor, str):
        return valor

    texto = valor

    try:
        texto = texto.encode("latin1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        # Texto já está correto ou não passou por dupla codificação.
        pass

    texto = unicodedata.normalize("NFC", texto)

    return texto.upper()


def corrigir_acentuacao(df: pd.DataFrame, tabela: str) -> pd.DataFrame:
    """
    Aplica correção de acentuação e upper case em todas as colunas
    textuais do DataFrame.

    Colunas numéricas, datas e booleanas são ignoradas automaticamente.
    """
    df = df.copy()

    colunas_texto = df.select_dtypes(include=["string", "object"]).columns

    for coluna in colunas_texto:
        df[coluna] = df[coluna].apply(_corrigir_texto)

    if len(colunas_texto):
        log.info(
            "  [texto] '%s': %d coluna(s) de texto corrigida(s) e padronizada(s) em maiúsculas.",
            tabela,
            len(colunas_texto),
        )

    return df