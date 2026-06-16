"""
pipeline/conversao.py
----------------------
Etapa 4 — Conversão de tipos.
Centraliza as regras de cast por tabela.
Adicione novos blocos no dicionário REGRAS_POR_TABELA conforme o schema crescer.
"""

import pandas as pd
from pipeline.conversao_tipos import CONVERSAO_TIPOS
from logger import log


# ===========================================================================
# 4. CONVERSÃO DE TIPOS — funções auxiliares + aplicar_conversoes()
# ===========================================================================

def _converter_inteiro(serie: pd.Series, coluna: str) -> pd.Series:
    """Converte para Int64 nullable com tratamento de erros e remoção de hífens."""
    # AJUSTE: Remove hífens de IDs (como idVotacao) antes de converter para número
    if serie.dtype == "object":
        serie = serie.str.replace("-", "", regex=False)
        
    serie = pd.to_numeric(serie, errors="coerce")
    return serie.astype("Int64")

def _converter_string(serie: pd.Series, coluna: str, tabela: str) -> pd.Series:
    """
    Converte para String e limpa o hífen caso seja a coluna 'id' 
    especificamente da tabela 'stg_votacoes_bruto'.
    """
    serie = serie.astype(str)
    
    # AJUSTE: Limpa o hífen se a tabela for stg_votacoes_bruto e a coluna for 'id'
    if coluna == "id" and tabela == "stg_votacoes_bruto":
        serie = serie.str.replace("-", "", regex=False)
        
    return serie

def _converter_float(serie: pd.Series, coluna: str) -> pd.Series:
    """Converte para Float64 nullable com tratamento de erros."""
    serie = pd.to_numeric(serie, errors="coerce")
    return serie.astype("Float64")


def _converter_datetime(serie: pd.Series, coluna: str) -> pd.Series:
    """
    Converte para datetime64[ns] com UTC.
    Remove timezone após conversão para compatibilidade com PostgreSQL DATE/TIMESTAMP.
    """
    serie = pd.to_datetime(serie, errors="coerce", utc=True)
    return serie.dt.tz_localize(None)   # remove tzinfo → datetime64[ns] puro


def _converter_boolean(serie: pd.Series, coluna: str) -> pd.Series:
    """
    Normaliza valores para boolean nullable:
    1 / 1.0 / 'true' / 'True' / True  → True
    0 / 0.0 / 'false' / 'False' / False → False
    demais → pd.NA
    """
    mapa = {
        1: True,  1.0: True,  "1": True,  "true": True,  "True": True,  True: True,
        0: False, 0.0: False, "0": False, "false": False, "False": False, False: False,
    }
    return serie.map(mapa).astype("boolean")


# Roteador de conversões: dtype → função auxiliar
_CONVERSORES: dict[str, callable] = {
    "Int64":          _converter_inteiro,
    "Float64":        _converter_float,
    "datetime64[ns]": _converter_datetime,
    "boolean":        _converter_boolean
}


def aplicar_conversoes(df: pd.DataFrame, tabela: str) -> pd.DataFrame:
    """
    Camada genérica de conversão de tipos para qualquer tabela staging.

    Infere automaticamente o tratamento necessário pelo dtype definido em
    CONVERSAO_TIPOS — sem necessidade de lógica condicional por tabela.

    Fluxo por coluna:
      1. Verifica se a coluna existe no DataFrame (ignora silenciosamente se não)
      2. Busca o conversor adequado pelo dtype em _CONVERSORES
      3. Aplica tratamento prévio + astype() de forma segura
      4. Loga cada conversão executada

    Args:
        df:     DataFrame com os dados brutos da tabela.
        tabela: Nome da tabela (chave em CONVERSAO_TIPOS).

    Returns:
        DataFrame com os tipos convertidos conforme mapeamento.
    """
    mapeamento = CONVERSAO_TIPOS.get(tabela, {})
    if not mapeamento:
        log.info("  ℹ️  '%s': sem mapeamento definido — tipos mantidos.", tabela)
        return df

    df = df.copy()
    convertidas, ignoradas, erros = 0, 0, 0

    for coluna, dtype in mapeamento.items():

        # Coluna ausente no DataFrame → ignora
        if coluna not in df.columns:
            log.debug("  ⏭  '%s.%s' não encontrada — ignorada.", tabela, coluna)
            ignoradas += 1
            continue

        try:
            conversor = _CONVERSORES.get(dtype)

            if conversor:
                # dtype com tratamento especial (Int64, Float64, datetime, boolean)
                df[coluna] = conversor(df[coluna], coluna)
            else:
                # dtype simples (string, category, etc.) → astype direto
                df[coluna] = df[coluna].astype(dtype)

            log.info("  🔄 %-35s → %s", f"'{tabela}.{coluna}'", dtype)
            convertidas += 1

        except Exception as exc:
            log.warning("  ⚠  Erro em '%s.%s' → %s: %s", tabela, coluna, dtype, exc)
            erros += 1

    log.info(
        "  📊 '%s': %d convertidas | %d ignoradas | %d erros",
        tabela, convertidas, ignoradas, erros,
    )
    return df