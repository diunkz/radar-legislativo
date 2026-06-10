"""
db.py — Leitura e escrita no PostgreSQL (Supabase)
"""

import logging
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import create_engine, inspect, text

from config import DB_URL

logger = logging.getLogger(__name__)

# ── Engine singleton ──────────────────────────────────────────────────────────

def get_engine():
    """Cria (ou reutiliza) o engine SQLAlchemy."""
    return create_engine(DB_URL, pool_pre_ping=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _tabela_existe(nome: str) -> bool:
    """Verifica se uma tabela existe no banco sem lançar exceção."""
    engine = get_engine()
    return inspect(engine).has_table(nome)


# ── Leitura ───────────────────────────────────────────────────────────────────

def carregar_proposicoes(apenas_nao_processadas: bool = True) -> pd.DataFrame:
    """
    Retorna as proposições da tabela `stg_proposicoes_bruto`.

    Carrega `ementa` e `ementa_detalhada` (quando disponível).
    Se `apenas_nao_processadas=True`, filtra somente as que ainda não têm
    registro em `proposicoes_ia`. Se a tabela `proposicoes_ia` ainda não
    existir, retorna todas as proposições (primeira execução).
    """
    engine = get_engine()

    # Na primeira execução proposicoes_ia ainda não existe — traz tudo
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
        # proposicoes_ia não existe ainda OU reprocessamento total
        query = """
            SELECT id, ementa, "ementaDetalhada" AS ementa_detalhada
            FROM   stg_proposicoes_bruto
            WHERE  ementa IS NOT NULL
              AND  TRIM(ementa) <> ''
            ORDER  BY id
        """

    if apenas_nao_processadas and not ia_existe:
        logger.info("Tabela `proposicoes_ia` ainda não existe — carregando todas as proposições.")

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