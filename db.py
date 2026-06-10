"""
db.py — Leitura e escrita no PostgreSQL (Supabase)
"""

import logging
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import create_engine, text

from config import DB_URL

logger = logging.getLogger(__name__)

# ── Engine singleton ──────────────────────────────────────────────────────────

def get_engine():
    """Cria (ou reutiliza) o engine SQLAlchemy."""
    return create_engine(DB_URL, pool_pre_ping=True)


# ── Leitura ───────────────────────────────────────────────────────────────────

def carregar_proposicoes(apenas_nao_processadas: bool = True) -> pd.DataFrame:
    """
    Retorna as proposições da tabela `stg_proposicoes_bruto`.

    Carrega `ementa` e `ementa_detalhada` (quando disponível).
    Se `apenas_nao_processadas=True`, filtra somente as que ainda não têm
    registro em `proposicoes_ia` (processamento incremental).
    """
    engine = get_engine()

    if apenas_nao_processadas:
        query = """
            SELECT p.id, p.ementa, p.ementa_detalhada
            FROM   stg_proposicoes_bruto p
            LEFT   JOIN proposicoes_ia ia ON ia.proposicao_id = p.id
            WHERE  ia.proposicao_id IS NULL
              AND  p.ementa IS NOT NULL
              AND  TRIM(p.ementa) <> ''
            ORDER  BY p.id
        """
    else:
        query = """
            SELECT id, ementa, ementa_detalhada
            FROM   stg_proposicoes_bruto
            WHERE  ementa IS NOT NULL
              AND  TRIM(ementa) <> ''
            ORDER  BY id
        """

    df = pd.read_sql(text(query), engine)
    logger.info(f"{len(df)} proposições carregadas para processamento.")
    return df


# ── Escrita ───────────────────────────────────────────────────────────────────

DDL_PROPOSICOES_IA = """
CREATE TABLE IF NOT EXISTS proposicoes_ia (
    proposicao_id       INTEGER      PRIMARY KEY,
    tema_classificado   TEXT,
    score_similaridade  FLOAT,
    resumo_executivo    TEXT,
    processado_em       TIMESTAMPTZ  DEFAULT NOW()
);
"""

def garantir_tabela_ia():
    """Cria a tabela proposicoes_ia se ela ainda não existir."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text(DDL_PROPOSICOES_IA))
    logger.info("Tabela `proposicoes_ia` verificada/criada com sucesso.")


def salvar_resultados(df: pd.DataFrame):
    """
    Faz upsert dos resultados em `proposicoes_ia`.

    O DataFrame deve conter as colunas:
        proposicao_id, tema_classificado, score_similaridade,
        resumo_executivo, processado_em
    """
    if df.empty:
        logger.warning("DataFrame vazio — nada para salvar.")
        return

    engine = get_engine()

    upsert_sql = """
        INSERT INTO proposicoes_ia
            (proposicao_id, tema_classificado, score_similaridade,
             resumo_executivo, processado_em)
        VALUES
            (:proposicao_id, :tema_classificado, :score_similaridade,
             :resumo_executivo, :processado_em)
        ON CONFLICT (proposicao_id) DO UPDATE SET
            tema_classificado  = EXCLUDED.tema_classificado,
            score_similaridade = EXCLUDED.score_similaridade,
            resumo_executivo   = EXCLUDED.resumo_executivo,
            processado_em      = EXCLUDED.processado_em
    """

    registros = df.to_dict(orient="records")
    with engine.begin() as conn:
        conn.execute(text(upsert_sql), registros)

    logger.info(f"{len(df)} registros salvos em `proposicoes_ia`.")