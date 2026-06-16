"""
pipeline/carga_silver.py
------------------------

Carga das tabelas Silver a partir das tabelas Bronze.

Estratégia adotada:
1. Garante a existência do schema silver;
2. Dropa todas as tabelas existentes no schema silver, no modo completo;
3. Dropa somente uma tabela silver, no modo de teste individual;
4. Recria as tabelas Silver com base em CREATES_SILVER;
5. Executa os INSERTs/tratamentos definidos em QUERIES_SILVER.

Essa abordagem é adequada para pipeline ponta a ponta e testes,
principalmente quando existem registros técnicos/substitutos de dimensão
que precisam nascer novamente a cada execução full refresh.
"""

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

from logger import log
from pipeline.creates_silver import CREATES_SILVER
from pipeline.queries_silver import QUERIES_SILVER


SCHEMA_SILVER = "silver"


def _quote_identificador(identificador: str) -> str:
    """
    Aplica aspas duplas em identificadores SQL para evitar problemas
    com nomes reservados, letras maiúsculas ou caracteres especiais.
    """
    if not isinstance(identificador, str) or not identificador.strip():
        raise ValueError("Identificador SQL inválido ou vazio.")

    return f'"{identificador.replace(chr(34), chr(34) * 2)}"'


def _nome_tabela_qualificado(schema: str, tabela: str) -> str:
    """
    Retorna o nome da tabela no formato:
        "schema"."tabela"
    """
    return f"{_quote_identificador(schema)}.{_quote_identificador(tabela)}"


def garantir_schema_silver(conn: Connection) -> None:
    """
    Cria o schema Silver caso ele ainda não exista.
    """
    log.info("Garantindo existência do schema silver.")

    conn.execute(
        text(f"CREATE SCHEMA IF NOT EXISTS {_quote_identificador(SCHEMA_SILVER)}")
    )


def listar_tabelas_silver(conn: Connection) -> list[str]:
    """
    Lista todas as tabelas físicas existentes no schema silver.
    """
    resultado = conn.execute(
        text(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = :schema
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """
        ),
        {"schema": SCHEMA_SILVER},
    )

    return list(resultado.scalars().all())


def dropar_tabelas_silver(conn: Connection) -> None:
    """
    Remove todas as tabelas existentes no schema silver.

    Usado na pipeline ponta a ponta.
    O uso de CASCADE remove dependências diretas, como constraints,
    indexes dependentes e objetos relacionados à tabela.
    """
    tabelas = listar_tabelas_silver(conn)

    if not tabelas:
        log.info("Nenhuma tabela existente encontrada no schema silver.")
        return

    log.info(f"Removendo {len(tabelas)} tabela(s) existente(s) no schema silver.")

    for tabela in tabelas:
        tabela_qualificada = _nome_tabela_qualificado(SCHEMA_SILVER, tabela)

        log.info(f"Dropando tabela silver.{tabela}")

        conn.execute(
            text(f"DROP TABLE IF EXISTS {tabela_qualificada} CASCADE")
        )

    log.info("Tabelas existentes no schema silver removidas com sucesso.")


def dropar_tabela_silver(conn: Connection, nome_tabela: str) -> None:
    """
    Remove uma tabela específica do schema silver.

    Usado principalmente no teste individual da camada Silver.
    """
    tabela_qualificada = _nome_tabela_qualificado(SCHEMA_SILVER, nome_tabela)

    log.info(f"Dropando tabela silver.{nome_tabela}")

    conn.execute(
        text(f"DROP TABLE IF EXISTS {tabela_qualificada} CASCADE")
    )

    log.info(f"Tabela silver.{nome_tabela} removida com sucesso.")


def criar_tabelas_silver(
    conn: Connection,
    nome_tabela: str | None = None,
) -> None:
    """
    Cria as tabelas Silver a partir do dicionário CREATES_SILVER.

    Quando nome_tabela for informado:
        cria somente a tabela solicitada.

    Quando nome_tabela for None:
        cria todas as tabelas Silver.
    """
    if not CREATES_SILVER:
        raise ValueError("Nenhum CREATE TABLE encontrado em CREATES_SILVER.")

    if nome_tabela:
        if nome_tabela not in CREATES_SILVER:
            raise KeyError(
                f"Tabela silver.{nome_tabela} não encontrada em CREATES_SILVER."
            )

        ddl = CREATES_SILVER[nome_tabela]

        if not ddl or not ddl.strip():
            raise ValueError(f"DDL vazio para silver.{nome_tabela}")

        log.info(f"Criando tabela silver.{nome_tabela}")
        conn.execute(text(ddl))
        log.info(f"Tabela silver.{nome_tabela} criada com sucesso.")

        return

    log.info("Iniciando criação das tabelas Silver.")

    for tabela, ddl in CREATES_SILVER.items():
        if not ddl or not ddl.strip():
            raise ValueError(f"DDL vazio para silver.{tabela}")

        log.info(f"Criando tabela silver.{tabela}")

        conn.execute(text(ddl))

    log.info("Tabelas Silver criadas com sucesso.")


def carregar_dados_silver(
    conn: Connection,
    nome_tabela: str | None = None,
) -> None:
    """
    Executa os INSERTs/tratamentos da camada Silver.

    As queries devem estar em QUERIES_SILVER e devem conter somente
    as instruções de carga/tratamento, normalmente INSERT INTO ... SELECT ...

    Quando nome_tabela for informado:
        carrega somente a tabela solicitada.

    Quando nome_tabela for None:
        carrega todas as tabelas Silver.
    """
    if not QUERIES_SILVER:
        raise ValueError("Nenhuma query de carga encontrada em QUERIES_SILVER.")

    if nome_tabela:
        if nome_tabela not in QUERIES_SILVER:
            raise KeyError(
                f"Tabela silver.{nome_tabela} não encontrada em QUERIES_SILVER."
            )

        query_insert = QUERIES_SILVER[nome_tabela]

        if not query_insert or not query_insert.strip():
            raise ValueError(f"Query de carga vazia para silver.{nome_tabela}")

        log.info(f"Iniciando carga silver.{nome_tabela}")

        conn.execute(text(query_insert))

        log.info(f"Carga concluída: silver.{nome_tabela}")

        return

    log.info("Iniciando carga de dados nas tabelas Silver.")

    for tabela, query_insert in QUERIES_SILVER.items():
        if not query_insert or not query_insert.strip():
            raise ValueError(f"Query de carga vazia para silver.{tabela}")

        log.info(f"Iniciando carga silver.{tabela}")

        conn.execute(text(query_insert))

        log.info(f"Carga concluída: silver.{tabela}")

    log.info("Carga de dados Silver concluída com sucesso.")


def carregar_silver(
    engine: Engine,
    nome_tabela: str | None = None,
) -> None:
    """
    Executa a carga full refresh da camada Silver.

    Modo pipeline ponta a ponta:
        carregar_silver(engine)

    Modo teste individual:
        carregar_silver(engine=engine, nome_tabela="deputado")

    Fluxo no modo completo:
    1. Cria o schema silver, se necessário;
    2. Dropa todas as tabelas existentes;
    3. Recria todas as tabelas;
    4. Insere todos os dados tratados.

    Fluxo no modo individual:
    1. Cria o schema silver, se necessário;
    2. Dropa somente a tabela informada;
    3. Recria somente a tabela informada;
    4. Insere somente os dados da tabela informada.

    A execução ocorre dentro de uma única transação.
    Se qualquer etapa falhar, o banco faz rollback automático.
    """
    if nome_tabela:
        log.info(f"Iniciando carga full refresh individual: silver.{nome_tabela}")
    else:
        log.info("Iniciando carga full refresh completa da camada Silver.")

    with engine.begin() as conn:
        garantir_schema_silver(conn)

        if nome_tabela:
            dropar_tabela_silver(
                conn=conn,
                nome_tabela=nome_tabela,
            )

            criar_tabelas_silver(
                conn=conn,
                nome_tabela=nome_tabela,
            )

            carregar_dados_silver(
                conn=conn,
                nome_tabela=nome_tabela,
            )
        else:
            dropar_tabelas_silver(conn)
            criar_tabelas_silver(conn)
            carregar_dados_silver(conn)

    if nome_tabela:
        log.info(f"Carga full refresh individual concluída: silver.{nome_tabela}")
    else:
        log.info("Carga full refresh completa da camada Silver concluída com sucesso.")