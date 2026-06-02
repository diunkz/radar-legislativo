"""
pipeline/exportacao.py
-----------------------
Etapas 6 + 7 — Exportação CSV.
Salva o DataFrame final em OUTPUT_DIR com nome padronizado e timestamp.
"""

import pandas as pd
from pathlib import Path
from config import OUTPUT_DIR
from logger import log
from config import TIMESTAMP


# ===========================================================================
# 6 + 7. EXPORTAÇÃO CSV → data/ajustadas/
# ===========================================================================

def exportar_csv(df: pd.DataFrame, tabela: str) -> Path:
    """
    Salva o DataFrame como CSV em OUTPUT_DIR com sufixo _ajustada.
    Arquivo: data/ajustadas/<tabela>_ajustada_<timestamp>.csv
    """
    if df.empty:
        log.warning("  ⚠  '%s' sem dados — CSV não gerado.", tabela)
        return Path()

    nome_base = tabela.replace("_bruto", "")
    nome_arquivo = f"{nome_base}_ajustada_{TIMESTAMP}.csv"
    caminho = OUTPUT_DIR / nome_arquivo
    df.to_csv(caminho, index=False, encoding="utf-8")
    log.info("  💾 CSV salvo: %s", caminho)
    return caminho

