"""
pipeline/carga_gold.py
----------------------

Carga das tabelas Gold a partir das tabelas Silver.

Estratégia adotada:
1. Garante a existência do schema gold;
2. Dropa todas as tabelas existentes no schema gold, no modo completo;
3. Dropa somente uma tabela gold, no modo de teste individual;
4. Recria as tabelas Gold com base em CREATES_GOLD;
5. Executa os INSERTs/tratamentos definidos em QUERIES_GOLD.

Essa abordagem substitui o modelo anterior de TRUNCATE + INSERT.

Motivo:
As dimensões Gold possuem registros técnicos de chave substituta,
como sk = -1 e sk = -3. Portanto, para garantir uma carga limpa,
idempotente e previsível, a tabela deve ser recriada do zero.

Modos de uso:

Pipeline ponta a ponta:
    carregar_gold(engine)

Teste individual:
    carregar_gold(engine=engine, nome_tabela="dim_deputado")

Compatibilidade com código antigo:
    executar_carga_gold("dim_deputado", engine)
"""

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

from logger import log
from pipeline.creates_gold import CREATES_GOLD
from pipeline.queries_gold import QUERIES_GOLD


SCHEMA_GOLD = "gold"


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


def garantir_schema_gold(conn: Connection) -> None:
    """
    Cria o schema Gold caso ele ainda não exista.
    """
    log.info("Garantindo existência do schema gold.")

    conn.execute(
        text(f"CREATE SCHEMA IF NOT EXISTS {_quote_identificador(SCHEMA_GOLD)}")
    )


def listar_tabelas_gold(conn: Connection) -> list[str]:
    """
    Lista todas as tabelas físicas existentes no schema gold.
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
        {"schema": SCHEMA_GOLD},
    )

    return list(resultado.scalars().all())


def dropar_tabelas_gold(conn: Connection) -> None:
    """
    Remove todas as tabelas existentes no schema gold.

    Usado na pipeline ponta a ponta.

    O uso de CASCADE remove dependências diretas, como constraints,
    indexes dependentes, views ou objetos relacionados à tabela.
    """
    tabelas = listar_tabelas_gold(conn)

    if not tabelas:
        log.info("Nenhuma tabela existente encontrada no schema gold.")
        return

    log.info(f"Removendo {len(tabelas)} tabela(s) existente(s) no schema gold.")

    for tabela in tabelas:
        tabela_qualificada = _nome_tabela_qualificado(SCHEMA_GOLD, tabela)

        log.info(f"Dropando tabela gold.{tabela}")

        conn.execute(
            text(f"DROP TABLE IF EXISTS {tabela_qualificada} CASCADE")
        )

    log.info("Tabelas existentes no schema gold removidas com sucesso.")


def dropar_tabela_gold(conn: Connection, nome_tabela: str) -> None:
    """
    Remove uma tabela específica do schema gold.

    Usado principalmente no teste individual da camada Gold.
    """
    tabela_qualificada = _nome_tabela_qualificado(SCHEMA_GOLD, nome_tabela)

    log.info(f"Dropando tabela gold.{nome_tabela}")

    conn.execute(
        text(f"DROP TABLE IF EXISTS {tabela_qualificada} CASCADE")
    )

    log.info(f"Tabela gold.{nome_tabela} removida com sucesso.")


def criar_tabelas_gold(
    conn: Connection,
    nome_tabela: str | None = None,
) -> None:
    """
    Cria as tabelas Gold a partir do dicionário CREATES_GOLD.

    Quando nome_tabela for informado:
        cria somente a tabela solicitada.

    Quando nome_tabela for None:
        cria todas as tabelas Gold.

    Observação:
    Os DDLs das dimensões também inserem os registros técnicos
    de chave substituta, como -1 e -3.
    """
    if not CREATES_GOLD:
        raise ValueError("Nenhum CREATE TABLE encontrado em CREATES_GOLD.")

    if nome_tabela:
        if nome_tabela not in CREATES_GOLD:
            raise KeyError(
                f"Tabela gold.{nome_tabela} não encontrada em CREATES_GOLD."
            )

        ddl = CREATES_GOLD[nome_tabela]

        if not ddl or not ddl.strip():
            raise ValueError(f"DDL vazio para gold.{nome_tabela}")

        log.info(f"Criando tabela gold.{nome_tabela}")
        conn.execute(text(ddl))
        log.info(f"Tabela gold.{nome_tabela} criada com sucesso.")

        return

    log.info("Iniciando criação das tabelas Gold.")

    for tabela, ddl in CREATES_GOLD.items():
        if not ddl or not ddl.strip():
            raise ValueError(f"DDL vazio para gold.{tabela}")

        log.info(f"Criando tabela gold.{tabela}")

        conn.execute(text(ddl))

    log.info("Tabelas Gold criadas com sucesso.")


def carregar_dados_gold(
    conn: Connection,
    nome_tabela: str | None = None,
) -> None:
    """
    Executa os INSERTs/tratamentos da camada Gold.

    As queries devem estar em QUERIES_GOLD e devem conter somente
    as instruções de carga/tratamento, normalmente INSERT INTO ... SELECT ...

    Quando nome_tabela for informado:
        carrega somente a tabela solicitada.

    Quando nome_tabela for None:
        carrega todas as tabelas Gold na ordem definida em QUERIES_GOLD.

    Atenção:
    A ordem de QUERIES_GOLD é importante.
    Dimensões devem vir antes das fatos.
    """
    if not QUERIES_GOLD:
        raise ValueError("Nenhuma query de carga encontrada em QUERIES_GOLD.")

    if nome_tabela:
        if nome_tabela not in QUERIES_GOLD:
            raise KeyError(
                f"Tabela gold.{nome_tabela} não encontrada em QUERIES_GOLD."
            )

        query_insert = QUERIES_GOLD[nome_tabela]

        if not query_insert or not query_insert.strip():
            raise ValueError(f"Query de carga vazia para gold.{nome_tabela}")

        log.info(f"Iniciando carga gold.{nome_tabela}")

        resultado = conn.execute(text(query_insert))

        log.info(
            "Carga concluída: gold.%s | rowcount=%s",
            nome_tabela,
            resultado.rowcount,
        )

        return

    log.info("Iniciando carga de dados nas tabelas Gold.")

    for tabela, query_insert in QUERIES_GOLD.items():
        if not query_insert or not query_insert.strip():
            raise ValueError(f"Query de carga vazia para gold.{tabela}")

        log.info(f"Iniciando carga gold.{tabela}")

        resultado = conn.execute(text(query_insert))

        log.info(
            "Carga concluída: gold.%s | rowcount=%s",
            tabela,
            resultado.rowcount,
        )

    log.info("Carga de dados Gold concluída com sucesso.")


def carregar_gold(
    engine: Engine,
    nome_tabela: str | None = None,
) -> None:
    """
    Executa a carga full refresh da camada Gold.

    Modo pipeline ponta a ponta:
        carregar_gold(engine)

    Modo teste individual:
        carregar_gold(engine=engine, nome_tabela="dim_deputado")

    Fluxo no modo completo:
    1. Cria o schema gold, se necessário;
    2. Dropa todas as tabelas existentes;
    3. Recria todas as tabelas;
    4. Insere todos os dados tratados.

    Fluxo no modo individual:
    1. Cria o schema gold, se necessário;
    2. Dropa somente a tabela informada;
    3. Recria somente a tabela informada;
    4. Insere somente os dados da tabela informada.

    A execução ocorre dentro de uma única transação.
    Se qualquer etapa falhar, o banco faz rollback automático.
    """
    if nome_tabela:
        log.info(f"Iniciando carga full refresh individual: gold.{nome_tabela}")
    else:
        log.info("Iniciando carga full refresh completa da camada Gold.")

    with engine.begin() as conn:
        garantir_schema_gold(conn)

        if nome_tabela:
            dropar_tabela_gold(
                conn=conn,
                nome_tabela=nome_tabela,
            )

            criar_tabelas_gold(
                conn=conn,
                nome_tabela=nome_tabela,
            )

            carregar_dados_gold(
                conn=conn,
                nome_tabela=nome_tabela,
            )
        else:
            dropar_tabelas_gold(conn)
            criar_tabelas_gold(conn)
            carregar_dados_gold(conn)

    if nome_tabela:
        log.info(f"Carga full refresh individual concluída: gold.{nome_tabela}")
    else:
        log.info("Carga full refresh completa da camada Gold concluída com sucesso.")


def executar_carga_gold(
    tabela_destino: str,
    engine: Engine,
) -> None:
    """
    Função de compatibilidade com a versão antiga do projeto.

    Antes:
        executar_carga_gold("dim_deputado", engine)

    Agora internamente executa:
        carregar_gold(engine=engine, nome_tabela="dim_deputado")

    Mantida para evitar quebrar test_gold.py ou main.py antigos.
    """
    carregar_gold(
        engine=engine,
        nome_tabela=tabela_destino,
    )