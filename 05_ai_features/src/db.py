"""
db.py — Leitura e escrita no PostgreSQL (Supabase)
"""

import logging
import time
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import create_engine, inspect, text

from .config import DB_URL, EMBEDDING_DIM

logger = logging.getLogger(__name__)

# ── Schema ────────────────────────────────────────────────────────────────────

SCHEMA = "silver"

# ── Engine singleton ──────────────────────────────────────────────────────────

_engine = None

def get_engine():
    """
    Retorna engine singleton com pool robusto para longas execuções.
    pool_pre_ping: testa a conexão antes de usar (detecta conexões mortas).
    pool_recycle:  recria conexões após 10min (evita timeout do Supabase).
    search_path:   garante que o schema silver é usado por padrão.
    """
    global _engine
    if _engine is None:
        _engine = create_engine(
            DB_URL,
            pool_pre_ping=True,
            pool_recycle=600,
            pool_size=2,
            max_overflow=2,
            connect_args={"options": f"-csearch_path={SCHEMA},public"},
        )
    return _engine


def _tabela_existe(nome: str, schema: str = SCHEMA) -> bool:
    """Verifica se a tabela existe no schema especificado."""
    return inspect(get_engine()).has_table(nome, schema=schema)


# ── Leitura ───────────────────────────────────────────────────────────────────

def carregar_proposicoes(apenas_nao_processadas: bool = True) -> pd.DataFrame:
    """
    Retorna proposições de `stg_proposicoes_bruto` (schema public).
    A fonte de verdade para saber o que já foi processado é o banco
    (silver.proposicoes_ia) — não arquivos locais.

    Se `apenas_nao_processadas=True`, retorna apenas proposições sem
    registro em silver.proposicoes_ia.
    """
    engine    = get_engine()
    ia_existe = _tabela_existe("proposicoes_ia")

    if apenas_nao_processadas and ia_existe:
        query = """
            SELECT p.id, p.ementa, p."ementaDetalhada" AS ementa_detalhada
            FROM   public.stg_proposicoes_bruto p
            LEFT   JOIN silver.proposicoes_ia ia ON ia.proposicao_id = p.id
            WHERE  ia.proposicao_id IS NULL
              AND  p.ementa IS NOT NULL
              AND  TRIM(p.ementa) <> ''
            ORDER  BY p.id
        """
    else:
        if apenas_nao_processadas and not ia_existe:
            logger.info("Tabela `silver.proposicoes_ia` ainda não existe — carregando todas.")
        query = """
            SELECT id, ementa, "ementaDetalhada" AS ementa_detalhada
            FROM   public.stg_proposicoes_bruto
            WHERE  ementa IS NOT NULL
              AND  TRIM(ementa) <> ''
            ORDER  BY id
        """

    df = pd.read_sql(text(query), engine)
    logger.info(f"{len(df)} proposições carregadas para processamento.")
    return df


# ── Escrita ───────────────────────────────────────────────────────────────────

DDL_PROPOSICOES_IA = f"""
CREATE TABLE IF NOT EXISTS {SCHEMA}.proposicoes_ia (
    proposicao_id       INTEGER          PRIMARY KEY,
    tema_classificado   TEXT,
    score_similaridade  FLOAT,
    embedding           vector({EMBEDDING_DIM}),
    resumo_executivo    TEXT,
    processado_em       TIMESTAMPTZ      DEFAULT NOW()
);
"""

def garantir_tabela_ia():
    """Cria a tabela silver.proposicoes_ia se não existir."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text(DDL_PROPOSICOES_IA))
    logger.info(f"Tabela `{SCHEMA}.proposicoes_ia` verificada/criada com sucesso.")


def salvar_resultados(df: pd.DataFrame, tentativas: int = 3):
    """
    Faz upsert em `silver.proposicoes_ia` com retry automático em caso de
    queda de conexão (comum em execuções longas contra o Supabase).

    Monta o SQL dinamicamente com base nas colunas presentes no DataFrame,
    permitindo salvar apenas embeddings, apenas resumos, ou ambos.
    """
    if df.empty:
        logger.warning("DataFrame vazio — nada para salvar.")
        return

    df = df.copy()

    # Converte embedding de lista Python para string pgvector
    if "embedding" in df.columns:
        df["embedding"] = df["embedding"].apply(
            lambda v: "[" + ",".join(f"{x:.8f}" for x in v) + "]" if v is not None else None
        )

    # Colunas opcionais — só incluídas no SQL se existirem no DataFrame
    COLUNAS_OPCIONAIS = {
        "tema_classificado":  "tema_classificado  = EXCLUDED.tema_classificado",
        "score_similaridade": "score_similaridade = EXCLUDED.score_similaridade",
        "embedding":          "embedding          = EXCLUDED.embedding",
        "resumo_executivo":   "resumo_executivo   = EXCLUDED.resumo_executivo",
    }

    colunas_presentes = [c for c in COLUNAS_OPCIONAIS if c in df.columns]

    col_insert = ["proposicao_id"] + colunas_presentes + ["processado_em"]
    val_insert = []
    for c in col_insert:
        if c == "embedding":
            val_insert.append("CAST(:embedding AS vector)")
        else:
            val_insert.append(f":{c}")

    update_set = [COLUNAS_OPCIONAIS[c] for c in colunas_presentes]
    update_set.append("processado_em = EXCLUDED.processado_em")

    upsert_sql = f"""
        INSERT INTO {SCHEMA}.proposicoes_ia ({", ".join(col_insert)})
        VALUES ({", ".join(val_insert)})
        ON CONFLICT (proposicao_id) DO UPDATE SET
            {",\n            ".join(update_set)}
    """

    registros = df.to_dict(orient="records")

    for tentativa in range(1, tentativas + 1):
        try:
            engine = get_engine()
            with engine.begin() as conn:
                conn.execute(text(upsert_sql), registros)
            logger.info(f"{len(df)} registros salvos em `{SCHEMA}.proposicoes_ia`.")
            return

        except Exception as e:
            logger.warning(f"Falha ao salvar (tentativa {tentativa}/{tentativas}): {e}")
            if tentativa < tentativas:
                espera = tentativa * 5
                logger.info(f"Aguardando {espera}s antes de tentar novamente...")
                time.sleep(espera)
            else:
                logger.error("Todas as tentativas de salvamento falharam.")
                raise
