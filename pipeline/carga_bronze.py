# """
# pipeline/carga_bronze.py
# ---------------------------
# Persiste o DataFrame já tratado (conversão de tipos + correção de
# acentuação + deduplicação) na camada Bronze (schema "bronze"), preservando
# a tabela de staging original (stg_*_bruto) intacta.

# Fluxo:
#     stg_*_bruto (cru, intocado)
#         --> pipeline de tratamento (etapas 3-6)
#         --> bronze.<tabela>   <-- este módulo
#         --> queries_silver.py lê de bronze.* --> silver.<tabela>

# Estratégia de carga: DROP + CREATE via to_sql(if_exists="replace").
#   - A tabela Bronze é inteiramente derivada do staging + tratamento, então
#     recriá-la a cada execução é seguro e evita drift entre o schema da
#     tabela e os dtypes do DataFrame após aplicar_conversoes().
#   - O schema "bronze" é criado automaticamente caso não exista.
# """

# import pandas as pd
# from sqlalchemy import Engine, text
# from logger import log
# from pipeline.mapeamento_bronze import SCHEMA_BRONZE, TABELA_BRONZE


# def carregar_bronze(
#     df: pd.DataFrame,
#     tabela_origem: str,
#     engine: Engine,
#     chunksize: int = 1000,
# ) -> None:
#     """
#     Grava `df` em `bronze.<tabela_bronze>`, onde <tabela_bronze> é obtido
#     a partir de TABELA_BRONZE[tabela_origem].

#     Parameters
#     ----------
#     df : DataFrame já tratado (pós conversão/acentuação/dedup)
#     tabela_origem : nome da tabela staging de origem (ex.: "stg_deputados_bruto")
#     engine : engine SQLAlchemy (DB_URI_DDL)
#     chunksize : tamanho do lote para o INSERT — aumente para tabelas grandes
#     """
#     if df.empty:
#         log.warning("  [bronze] DataFrame vazio — nada a gravar para '%s'.", tabela_origem)
#         return

#     tabela_bronze = TABELA_BRONZE.get(tabela_origem)
#     if tabela_bronze is None:
#         log.warning(
#             "  [bronze] '%s' não mapeada em TABELA_BRONZE — pulando gravação Bronze.",
#             tabela_origem,
#         )
#         return

#     nome_completo = f"{SCHEMA_BRONZE}.{tabela_bronze}"

#     try:
#         with engine.begin() as conn:
#             conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA_BRONZE}"))

#             df.to_sql(
#                 name=tabela_bronze,
#                 con=conn,
#                 schema=SCHEMA_BRONZE,
#                 if_exists="replace",  # recria a tabela a cada execução
#                 index=False,
#                 method="multi",
#                 chunksize=chunksize,
#             )

#         log.info("  [bronze] '%s' gravada com %d linha(s).", nome_completo, len(df))

#     except Exception as exc:  # noqa: BLE001
#         log.error("  [bronze] Erro ao gravar '%s': %s", nome_completo, exc)
#         raise

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