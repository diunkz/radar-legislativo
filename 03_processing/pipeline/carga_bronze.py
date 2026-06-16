"""
pipeline/carga_bronze.py
------------------------
Carga das tabelas Bronze físicas e transitórias.

A Bronze é criada no Supabase/PostgreSQL apenas durante a execução do pipeline.
Depois que Silver e Gold são carregadas, o schema bronze é removido.
"""

from __future__ import annotations

import csv
from io import StringIO

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from logger import log


SCHEMA_BRONZE = "bronze"


def criar_schema_bronze(engine: Engine) -> None:
    """
    Cria o schema bronze caso ele ainda não exista.
    """
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA_BRONZE}"'))

    log.info("Schema bronze criado/verificado.")


def _copy_insert(table, conn, keys, data_iter) -> None:
    """
    Método customizado para pandas.to_sql usando COPY FROM STDIN.

    Evita INSERTs gigantes gerados pelo method='multi',
    reduzindo risco de timeout no Supabase/PostgreSQL.
    """
    dbapi_conn = conn.connection

    with dbapi_conn.cursor() as cur:
        buffer = StringIO()

        writer = csv.writer(
            buffer,
            delimiter=",",
            quotechar='"',
            quoting=csv.QUOTE_MINIMAL,
            lineterminator="\n",
        )

        writer.writerows(data_iter)
        buffer.seek(0)

        colunas = ", ".join(f'"{col}"' for col in keys)

        sql_copy = f'''
            COPY "{SCHEMA_BRONZE}"."{table.name}" ({colunas})
            FROM STDIN
            WITH (
                FORMAT CSV,
                NULL ''
            )
        '''

        cur.copy_expert(sql_copy, buffer)


def carregar_tabela_bronze(
    df: pd.DataFrame,
    nome_tabela: str,
    engine: Engine,
) -> None:
    """
    Carrega um DataFrame em bronze.<nome_tabela>.

    A tabela é recriada a cada execução.
    """
    if df is None or df.empty:
        log.warning(f"Tabela bronze.{nome_tabela} não carregada: DataFrame vazio.")
        return

    log.info(f"Iniciando carga bronze.{nome_tabela} com {len(df)} registros.")

    df.to_sql(
        name=nome_tabela,
        con=engine,
        schema=SCHEMA_BRONZE,
        if_exists="replace",
        index=False,
        method=_copy_insert,
    )

    log.info(f"Carga concluída: bronze.{nome_tabela}")


def carregar_bronze(
    tabelas: dict[str, pd.DataFrame],
    engine: Engine,
) -> None:
    """
    Carrega todas as tabelas Bronze uma única vez.
    """
    criar_schema_bronze(engine)

    for nome_tabela, df in tabelas.items():
        carregar_tabela_bronze(
            df=df,
            nome_tabela=nome_tabela,
            engine=engine,
        )