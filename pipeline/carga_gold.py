"""
pipeline/carga_gold.py
-----------------------
Responsabilidade única: executar a transformação Silver -> Gold
diretamente no PostgreSQL, via TRUNCATE + INSERT INTO ... SELECT.

A query (com os JOINs, aliases, CAST etc.) vive em
pipeline/queries_gold.py — este módulo apenas orquestra a execução.

Estratégia de carga: TRUNCATE + INSERT (full load).
  - TRUNCATE garante idempotência: rodar o pipeline várias vezes não duplica
    registros — as tabelas Gold sempre refletem 1:1 o conteúdo da Silver.
  - Ordem de execução é crítica: dimensões rodam ANTES das tabelas fato
    (as fatos dependem das chaves subrogadas sk_* das dimensões).

⚠️ Ordem de execução do dicionário QUERIES_GOLD:
    O Python 3.7+ mantém ordem de inserção em dicionários. As chaves em
    QUERIES_GOLD estão ordenadas (dimensões primeiro, depois fatos).
    Se adicionar uma nova query, cuidado com a posição!
"""

from sqlalchemy import Engine, text
from logger import log
from pipeline.queries_gold import QUERIES_GOLD, SCHEMA_GOLD


def executar_carga_gold(tabela_destino: str, engine: Engine) -> None:
    """
    Executa TRUNCATE + INSERT INTO ... SELECT para `gold.<tabela_destino>`,
    usando a query definida em QUERIES_GOLD.

    Parameters
    ----------
    tabela_destino : nome da tabela Gold, sem schema (ex.: "dim_deputado", "fato_voto")
    engine : engine SQLAlchemy (DB_URI_DDL)
    """
    query = QUERIES_GOLD.get(tabela_destino)
    nome_completo = f"{SCHEMA_GOLD}.{tabela_destino}"

    if query is None:
        log.warning("  [gold] Nenhuma query definida para '%s' — pulando.", nome_completo)
        return

    try:
        with engine.begin() as conn:
            # TRUNCATE garante full load idempotente
            conn.execute(text(f"TRUNCATE TABLE {nome_completo} CASCADE"))  # noqa: S608

            resultado = conn.execute(text(query))

        log.info(
            "  [gold] %d linha(s) inserida(s) em '%s'.",
            resultado.rowcount, nome_completo,
        )

    except Exception as exc:  # noqa: BLE001
        log.error("  [gold] Erro ao carregar '%s': %s", nome_completo, exc)
        raise
