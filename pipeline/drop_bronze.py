"""
pipeline/drop_bronze.py
-----------------------
Remove o schema bronze ao final do pipeline.
"""

from sqlalchemy import text
from sqlalchemy.engine import Engine

from logger import log


def drop_bronze(engine: Engine) -> None:
    """
    Remove o schema bronze e todos os objetos dentro dele.

    Atenção:
    DROP SCHEMA ... CASCADE remove tabelas, views e dependências
    ligadas ao schema bronze.
    """
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS bronze CASCADE"))

    log.info("Schema bronze removido com sucesso.")