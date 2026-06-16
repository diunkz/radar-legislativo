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
    "stg_eventos_orgaos_bruto"  : ["idEventoContexto"],
    "stg_frentes_bruto"         : ["id"],
    "stg_legislaturas_bruto"    : ["id"],
    "stg_orgaos_bruto"          : ["id"],
    "stg_partidos_bruto"        : ["id"],
    "stg_proposicoes_bruto"     : ["id"],
    "stg_despesas_bruto"        : ["codDocumento"],
    "stg_votacoes_bruto"        : ["id"],

    # tabelas sem regra explícita usarão None (todas as colunas)
}


# def remover_duplicatas(df: pd.DataFrame, tabela: str) -> pd.DataFrame:
#     """
#     Remove linhas duplicadas com base no subset de colunas-chave da tabela.
#     Loga quantas linhas foram descartadas.
#     """
 

def remover_duplicatas(df: pd.DataFrame, tabela: str) -> pd.DataFrame:
    """
    Remove linhas com ID inválido e depois elimina duplicatas.
    """
    if tabela == "stg_votacoes_bruto" and "id" in df.columns:
        df["id"] = df["id"].astype("str").str.replace("-", "", regex=False)
    elif tabela == "stg_votos_bruto" and "idVotacaoContexto" in df.columns:
        df["idVotacaoContexto"] = df["idVotacaoContexto"].astype("str").str.replace("-", "", regex=False)

    # ------------------------------------------------------------------
    # Remove registros com ID inválido somente para tabelas
    # cuja chave de unicidade contém a coluna 'id'
    # ------------------------------------------------------------------
    subset = CHAVES_POR_TABELA.get(tabela)

    if subset and "id" in subset and "id" in df.columns:

        antes_id = len(df)

        ids_convertidos = pd.to_numeric(
            df["id"],
            errors="coerce"
        )

        mascara_valida = (
              ids_convertidos.notna()
              & (ids_convertidos % 1 == 0)
              & (ids_convertidos > 0)
        )

        df = df.loc[mascara_valida].copy()
        df["id"] = ids_convertidos.loc[mascara_valida].astype("Int64")

        removidos_id = antes_id - len(df)

        if removidos_id:
            log.warning(
                "  [id] %d registro(s) removido(s) por ID inválido em '%s'.",
                removidos_id,
                tabela,
            )

    # ------------------------------------------------------------------
    # Remoção de duplicatas
    # ------------------------------------------------------------------
    antes = len(df)

    df = (
        df.drop_duplicates(
            subset=subset,
            keep="first"
        )
        .reset_index(drop=True)
    )

    removidas = antes - len(df)

    if removidas:
        log.warning(
            "  [dedup] %d duplicata(s) removida(s) em '%s' (subset=%s).",
            removidas,
            tabela,
            subset,
        )
        log.info("")
    else:
        log.info(
            "  [dedup] Nenhuma duplicata em '%s'.",
            tabela,
        )
        log.info("")
    return df