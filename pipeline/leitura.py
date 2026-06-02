"""
pipeline/leitura.py
--------------------
Etapa 2 — Leitura.
Carrega uma tabela do banco de dados e retorna um DataFrame pandas.
"""

import pandas as pd
from sqlalchemy import Engine, text
from logger import log

# ===========================================================================
# 2. LEITURA DAS TABELAS → DataFrame
# ===========================================================================

# def carregar_tabela(client: Client, tabela: str) -> pd.DataFrame:
#     """Lê todos os dados de uma tabela via supabase-py e retorna um DataFrame."""
#     try:
#         resposta = client.table(tabela).select("*").execute()
#         df = pd.DataFrame(resposta.data)
#         log.info("  📥 '%s': %d linhas, %d colunas", tabela, len(df), len(df.columns))
#         return df
#     except Exception as exc:
#         log.warning("  ⚠  Não foi possível carregar '%s': %s", tabela, exc)
#         return pd.DataFrame()

def carregar_tabela(engine: Engine, tabela: str) -> pd.DataFrame:
    """Lê todos os dados de uma tabela via SQLAlchemy e retorna um DataFrame."""
    try:
        query = text(f"SELECT * FROM {tabela}")
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
        log.info("  📥 '%s': %d linhas, %d colunas", tabela, len(df), len(df.columns))
        return df
    except Exception as exc:
        log.warning("  ⚠  Não foi possível carregar '%s': %s", tabela, exc)
        return pd.DataFrame()