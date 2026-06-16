"""
test_gold.py
------------

Teste individual da camada Gold.

Objetivo:
- Testar uma dimensão ou fato Gold isoladamente;
- Validar se as tabelas Silver necessárias existem antes da carga;
- Para tabelas fato, carregar previamente as dimensões Gold necessárias;
- Executar a carga Gold da tabela selecionada;
- Validar se as tabelas Gold foram criadas/carregadas ao final.

Pré-requisito:
    A camada Silver deve estar carregada no banco.

Uso:
    uv run test_gold.py

Edite TABELA_TESTE para escolher qual dimensão/fato testar.
"""

from sqlalchemy import text
from sqlalchemy.engine import Engine

from conexoes.sqlalchemy_engine import conectar_sqlalchemy
from logger import log

from pipeline.carga_gold import executar_carga_gold
from pipeline.creates_gold import CREATES_GOLD
from pipeline.queries_gold import QUERIES_GOLD


# ============================================================
# EDITE AQUI: escolha uma tabela Gold para testar
# ============================================================

TABELA_TESTE = "dim_proposicao"


# ============================================================
# Dependências Silver por tabela Gold
# ============================================================

DEPENDENCIAS_SILVER_GOLD: dict[str, list[str]] = {
    "dim_deputado": [
        "deputado",
    ],
    "dim_orgao": [
        "orgao",
    ],
    "dim_evento": [
        "evento",
    ],
    "dim_proposicao": [
        "proposicao",
    ],
    "dim_votacao": [
        "votacao",
    ],
    "ft_despesa": [
        "despesa",
    ],
    "ft_proposicao": [
        "proposicao",
    ],
    "ft_voto": [
        "votacao",
    ],
}


# ============================================================
# Ordem de execução para teste individual
# ============================================================
#
# Dimensões:
#   Executam somente elas mesmas.
#
# Fatos:
#   Executam primeiro as dimensões necessárias e depois a fato.
#
# Isso é necessário porque as fatos usam as SKs das dimensões Gold.
# ============================================================

ORDEM_EXECUCAO_GOLD_TESTE: dict[str, list[str]] = {
    "dim_deputado": [
        "dim_deputado",
    ],
    "dim_orgao": [
        "dim_orgao",
    ],
    "dim_evento": [
        "dim_evento",
    ],
    "dim_proposicao": [
        "dim_proposicao",
    ],
    "dim_votacao": [
        "dim_votacao",
    ],
    "ft_despesa": [
        "dim_deputado",
        "ft_despesa",
    ],
    "ft_proposicao": [
        "dim_deputado",
        "dim_orgao",
        "dim_proposicao",
        "ft_proposicao",
    ],
    "ft_voto": [
        "dim_votacao",
        "dim_deputado",
        "dim_orgao",
        "dim_evento",
        "dim_proposicao",
        "ft_voto",
    ],
}


def tabela_existe(
    engine: Engine,
    schema: str,
    tabela: str,
) -> bool:
    """
    Verifica se uma tabela física existe no banco.
    """
    query = text(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = :schema
              AND table_name = :tabela
              AND table_type = 'BASE TABLE'
        )
        """
    )

    with engine.begin() as conn:
        existe = conn.execute(
            query,
            {
                "schema": schema,
                "tabela": tabela,
            },
        ).scalar()

    return bool(existe)


def contar_registros(
    engine: Engine,
    schema: str,
    tabela: str,
) -> int:
    """
    Conta os registros de uma tabela.
    """
    query = text(f'SELECT COUNT(*) FROM "{schema}"."{tabela}"')

    with engine.begin() as conn:
        total = conn.execute(query).scalar()

    return int(total or 0)


def validar_tabela_teste(nome_tabela: str) -> None:
    """
    Valida se a tabela Gold informada possui:
    - DDL em CREATES_GOLD;
    - query em QUERIES_GOLD;
    - ordem de execução mapeada.
    """
    if nome_tabela not in CREATES_GOLD:
        raise KeyError(
            f"Tabela Gold '{nome_tabela}' não existe em CREATES_GOLD. "
            "Inclua o CREATE correspondente em pipeline/creates_gold.py."
        )

    if nome_tabela not in QUERIES_GOLD:
        raise KeyError(
            f"Tabela Gold '{nome_tabela}' não existe em QUERIES_GOLD. "
            "Inclua o INSERT correspondente em pipeline/queries_gold.py."
        )

    if nome_tabela not in ORDEM_EXECUCAO_GOLD_TESTE:
        raise KeyError(
            f"Tabela Gold '{nome_tabela}' não possui ordem de execução mapeada "
            "em ORDEM_EXECUCAO_GOLD_TESTE."
        )


def obter_dependencias_silver_da_execucao(
    ordem_execucao: list[str],
) -> list[str]:
    """
    Retorna as dependências Silver necessárias para toda a ordem de execução.

    Exemplo:
        ft_proposicao executa:
            dim_deputado, dim_orgao, dim_proposicao, ft_proposicao

        Dependências Silver finais:
            deputado, orgao, proposicao
    """
    dependencias: list[str] = []

    for tabela_gold in ordem_execucao:
        for tabela_silver in DEPENDENCIAS_SILVER_GOLD.get(tabela_gold, []):
            if tabela_silver not in dependencias:
                dependencias.append(tabela_silver)

    return dependencias


def validar_dependencias_silver(
    engine: Engine,
    dependencias: list[str],
) -> None:
    """
    Valida se as tabelas Silver necessárias existem.

    Se uma tabela Silver não existir, o teste é abortado.
    Se existir, mas estiver vazia, apenas registra warning.
    """
    dependencias_faltantes: list[str] = []

    for tabela_silver in dependencias:
        existe = tabela_existe(
            engine=engine,
            schema="silver",
            tabela=tabela_silver,
        )

        if not existe:
            dependencias_faltantes.append(tabela_silver)
            continue

        total = contar_registros(
            engine=engine,
            schema="silver",
            tabela=tabela_silver,
        )

        if total == 0:
            log.warning(
                "  ⚠ silver.%s existe, mas está vazia.",
                tabela_silver,
            )
        else:
            log.info(
                "  ✔ silver.%s disponível com %d registro(s).",
                tabela_silver,
                total,
            )

    if dependencias_faltantes:
        raise RuntimeError(
            "Dependências Silver ausentes para a carga Gold. "
            f"Faltantes: {dependencias_faltantes}"
        )


def validar_resultado_gold(
    engine: Engine,
    tabela_gold: str,
) -> None:
    """
    Valida se a tabela Gold foi criada/carregada após a execução.
    """
    existe = tabela_existe(
        engine=engine,
        schema="gold",
        tabela=tabela_gold,
    )

    if not existe:
        raise RuntimeError(
            f"A carga executou, mas a tabela gold.{tabela_gold} não foi encontrada."
        )

    total = contar_registros(
        engine=engine,
        schema="gold",
        tabela=tabela_gold,
    )

    if total == 0:
        log.warning(
            "  ⚠ gold.%s foi criada/processada, mas está vazia.",
            tabela_gold,
        )
    else:
        log.info(
            "  ✔ gold.%s disponível com %d registro(s).",
            tabela_gold,
            total,
        )


def executar_ordem_gold(
    engine: Engine,
    ordem_execucao: list[str],
) -> None:
    """
    Executa a sequência necessária para o teste Gold.

    Para dimensões:
        executa somente a dimensão.

    Para fatos:
        executa dimensões necessárias primeiro e a fato no final.
    """
    for tabela_gold in ordem_execucao:
        log.info("")
        log.info("  🌟 Executando Gold: %s", tabela_gold)

        executar_carga_gold(
            tabela_gold,
            engine,
        )

        validar_resultado_gold(
            engine=engine,
            tabela_gold=tabela_gold,
        )

        log.info("  ✓ Gold.%s processada.", tabela_gold)


def test_gold(tabela_teste: str) -> None:
    """
    Executa uma carga Gold para teste manual.

    Se a tabela selecionada for uma dimensão, executa somente ela.
    Se for uma fato, executa previamente as dimensões necessárias.
    """
    log.info("=" * 60)
    log.info("🏆 TESTE INDIVIDUAL DA CAMADA GOLD")
    log.info("=" * 60)

    engine = conectar_sqlalchemy()

    if engine is None:
        raise RuntimeError("SQLAlchemy indisponível — verifique DB_URI_DDL no .env")

    validar_tabela_teste(tabela_teste)

    ordem_execucao = ORDEM_EXECUCAO_GOLD_TESTE[tabela_teste]
    dependencias_silver = obter_dependencias_silver_da_execucao(ordem_execucao)

    log.info("  Tabela Gold selecionada: %s", tabela_teste)
    log.info("  Pré-requisito: Silver já carregada.")
    log.info("  Ordem de execução Gold: %s", " -> ".join(ordem_execucao))
    log.info("  Dependências Silver necessárias: %s", ", ".join(dependencias_silver))

    log.info("")
    log.info("=" * 60)
    log.info("🔎 VALIDANDO DEPENDÊNCIAS SILVER")
    log.info("=" * 60)

    validar_dependencias_silver(
        engine=engine,
        dependencias=dependencias_silver,
    )

    log.info("")
    log.info("=" * 60)
    log.info("🏆 EXECUTANDO GOLD DE TESTE: %s", tabela_teste)
    log.info("=" * 60)

    try:
        executar_ordem_gold(
            engine=engine,
            ordem_execucao=ordem_execucao,
        )

    except Exception as exc:
        log.exception("  ✗ Teste Gold '%s' falhou: %s", tabela_teste, exc)
        raise

    log.info("")
    log.info("=" * 60)
    log.info("✅ TESTE GOLD CONCLUÍDO COM SUCESSO")
    log.info("=" * 60)


if __name__ == "__main__":
    test_gold(TABELA_TESTE)