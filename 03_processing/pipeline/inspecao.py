"""
pipeline/inspecao.py
---------------------
Etapa 3 — Inspeção de tipos.
Loga um resumo dos dtypes e valores nulos de cada coluna.
Não altera o DataFrame — apenas observa e registra.
"""

import pandas as pd
from logger import log


# ===========================================================================
# 3. INSPEÇÃO DE TIPOS VIA PANDAS
# ===========================================================================

def inspecionar_tipos(df: pd.DataFrame, tabela: str) -> pd.DataFrame:
    """
    Exibe e retorna um DataFrame com o diagnóstico de tipos de cada coluna:
      - dtype atual (pandas)
      - % de nulos
      - quantidade de valores únicos
    """
    if df.empty:
        log.warning("  ⚠  '%s' sem dados — inspeção ignorada.", tabela)
        return pd.DataFrame()

    diagnostico = pd.DataFrame({
        "coluna":          df.columns,
        "dtype_pandas":    [str(df[c].dtype) for c in df.columns],
        "nulos_%":         [round(df[c].isna().mean() * 100, 2) for c in df.columns],
        "valores_unicos":  [df[c].nunique() for c in df.columns],
        "exemplo":         [df[c].dropna().iloc[0] if not df[c].dropna().empty else None
                            for c in df.columns],
    })

    log.info("  🔎 Diagnóstico de tipos — '%s':", tabela)
    for _, row in diagnostico.iterrows():
        log.info(
            "     %-25s dtype=%-15s nulos=%5.1f%%  únicos=%d",
            row["coluna"], row["dtype_pandas"], row["nulos_%"], row["valores_unicos"],
        )

    return diagnostico