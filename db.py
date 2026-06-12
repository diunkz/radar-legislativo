"""
db.py — Leitura e escrita no PostgreSQL (Supabase)
"""

import logging
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import create_engine, inspect, text

from config import DB_URL, EMBEDDING_DIM

logger = logging.getLogger(__name__)

# ── Engine singleton ──────────────────────────────────────────────────────────

def get_engine():
    return create_engine(DB_URL, pool_pre_ping=True)


def _tabela_existe(nome: str) -> bool:
    return inspect(get_engine()).has_table(nome)


# ── Leitura ───────────────────────────────────────────────────────────────────

def carregar_proposicoes(apenas_nao_processadas: bool = True) -> pd.DataFrame:
    """
    Retorna proposições de `stg_proposicoes_bruto`.
    Se `apenas_nao_processadas=True` e a tabela `proposicoes_ia` já existir,
    filtra apenas as sem registro (processamento incremental).
    """
    engine    = get_engine()
    ia_existe = _tabela_existe("proposicoes_ia")

    if apenas_nao_processadas and ia_existe:
        query = """
            SELECT p.id, p.ementa, p."ementaDetalhada" AS ementa_detalhada
            FROM   stg_proposicoes_bruto p
            LEFT   JOIN proposicoes_ia ia ON ia.proposicao_id = p.id
            WHERE  ia.proposicao_id IS NULL
              AND  p.ementa IS NOT NULL
              AND  TRIM(p.ementa) <> ''
            ORDER  BY p.id
        """
    else:
        if apenas_nao_processadas and not ia_existe:
            logger.info("Tabela `proposicoes_ia` ainda não existe — carregando todas.")
        query = """
            SELECT id, ementa, "ementaDetalhada" AS ementa_detalhada
            FROM   stg_proposicoes_bruto
            WHERE  ementa IS NOT NULL
              AND  TRIM(ementa) <> ''
            ORDER  BY id
        """

    df = pd.read_sql(text(query), engine)
    logger.info(f"{len(df)} proposições carregadas para processamento.")
    return df


# ── Escrita ───────────────────────────────────────────────────────────────────

DDL_PROPOSICOES_IA = f"""
CREATE TABLE IF NOT EXISTS proposicoes_ia (
    proposicao_id       INTEGER          PRIMARY KEY,
    tema_classificado   TEXT,
    score_similaridade  FLOAT,
    embedding           vector({EMBEDDING_DIM}),
    resumo_executivo    TEXT,
    processado_em       TIMESTAMPTZ      DEFAULT NOW()
);
"""

def garantir_tabela_ia():
    """Cria a tabela proposicoes_ia (com coluna vector) se não existir."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text(DDL_PROPOSICOES_IA))
    logger.info("Tabela `proposicoes_ia` verificada/criada com sucesso.")


def salvar_resultados(df: pd.DataFrame):
    """
    Faz upsert em `proposicoes_ia`.
    A coluna `embedding` deve ser uma lista de floats (será convertida para
    o formato de string que o pgvector aceita: '[0.1, 0.2, ...]').
    """
    if df.empty:
        logger.warning("DataFrame vazio — nada para salvar.")
        return

    engine = get_engine()

    # Converte embedding de lista Python para string pgvector
    if "embedding" in df.columns:
        df = df.copy()
        df["embedding"] = df["embedding"].apply(
            lambda v: "[" + ",".join(f"{x:.8f}" for x in v) + "]" if v is not None else None
        )

    upsert_sql = """
        INSERT INTO proposicoes_ia
            (proposicao_id, tema_classificado, score_similaridade,
             embedding, resumo_executivo, processado_em)
        VALUES
            (:proposicao_id, :tema_classificado, :score_similaridade,
             CAST(:embedding AS vector), :resumo_executivo, :processado_em)
        ON CONFLICT (proposicao_id) DO UPDATE SET
            tema_classificado  = EXCLUDED.tema_classificado,
            score_similaridade = EXCLUDED.score_similaridade,
            embedding          = EXCLUDED.embedding,
            resumo_executivo   = EXCLUDED.resumo_executivo,
            processado_em      = EXCLUDED.processado_em
    """

    registros = df.to_dict(orient="records")
    with engine.begin() as conn:
        conn.execute(text(upsert_sql), registros)

    logger.info(f"{len(df)} registros salvos em `proposicoes_ia`.")