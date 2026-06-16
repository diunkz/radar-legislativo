"""
pipeline/exportacao.py
-----------------------
Etapas 9 — Exportação CSV.
Salva o DataFrame final em OUTPUT_DIR com nome padronizado e timestamp.
"""

import pandas as pd
import shutil
from logger import log
from datetime import datetime
from pathlib import Path
from logger import log


# ---------------------------------------------------------------------------
# Pasta de saída dos CSVs ajustados
# ---------------------------------------------------------------------------
OUTPUT_DIR = Path(__file__).parent / "output" / "ajustadas"

if OUTPUT_DIR.exists():
    shutil.rmtree(OUTPUT_DIR)
    log.info("🗑️  Pasta anterior removida: %s", OUTPUT_DIR)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
log.info("📁 Pasta criada: %s", OUTPUT_DIR)

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


# ===========================================================================
# 9. EXPORTAÇÃO CSV → data/ajustadas/
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

