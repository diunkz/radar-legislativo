"""
pipeline/deduplicacao.py
-------------------------
Etapa 5 — Remoção de duplicatas.
Define subsets de colunas-chave por tabela para um drop_duplicates preciso.
Usar subset evita remover linhas que diferem apenas em colunas de auditoria
(ex.: updated_at), o que mascararia dados legítimos.
"""

import pandas as pd

from logger import log

# ---------------------------------------------------------------------------
# Subset de colunas que identificam unicidade por tabela.
# None → usa todas as colunas (comportamento padrão do pandas).
# ---------------------------------------------------------------------------
CHAVES_POR_TABELA: dict[str, list[str] | None] = {
    "stg_deputados_bruto"       : ["id"],
    "stg_eventos_bruto"         : ["id"],
    "stg_frentes_bruto"         : ["id"],
    "stg_legislaturas_bruto"    : ["id"],
    "stg_orgaos_bruto"          : ["id"],
    "stg_partidos_bruto"        : ["id"],
    "stg_proposicoes_bruto"     : ["id"],
    "stg_votacoes_bruto"        : ["id"]

    # tabelas sem regra explícita usarão None (todas as colunas)
}


def remover_duplicatas(df: pd.DataFrame, tabela: str) -> pd.DataFrame:
    """
    Remove linhas duplicadas com base no subset de colunas-chave da tabela.
    Loga quantas linhas foram descartadas.
    """
    subset = CHAVES_POR_TABELA.get(tabela)  # None se não mapeado
    antes  = len(df)

    df = df.drop_duplicates(subset=subset, keep="first").reset_index(drop=True)

    removidas = antes - len(df)
    if removidas:
        log.warning(
            "  [dedup] %d duplicata(s) removida(s) em '%s' (subset=%s).",
            removidas, tabela, subset,
        )
    else:
        log.info("  [dedup] Nenhuma duplicata em '%s'.", tabela)

    return df
