"""
test_silver.py
--------------

Teste individual da camada Silver.

Objetivo:
- Testar uma tabela Silver isoladamente;
- Carregar na Bronze física somente as tabelas necessárias;
- Respeitar os nomes físicos esperados pelas queries em QUERIES_SILVER.

Exemplo:
    Origem staging:
        public.stg_deputados_bruto

    Tabela física criada para teste:
        bronze.deputados

    Query Silver:
        FROM bronze.deputados dep

Essa estratégia evita alterar as queries Silver para usar stg_*_bruto.
"""

import pandas as pd

from conexoes.sqlalchemy_engine import conectar_sqlalchemy
from logger import log

from pipeline.leitura import carregar_tabela
from pipeline.inspecao import inspecionar_tipos
from pipeline.conversao import aplicar_conversoes
from pipeline.correcao_texto import corrigir_acentuacao
from pipeline.deduplicacao import remover_duplicatas

from pipeline.carga_bronze import carregar_bronze
from pipeline.carga_silver import carregar_silver
from pipeline.creates_silver import CREATES_SILVER
from pipeline.queries_silver import QUERIES_SILVER


# ============================================================
# EDITE AQUI: escolha uma tabela Silver para testar
# ============================================================

TABELA_TESTE = "despesa"


# ============================================================
# Mapeamento de dependências Bronze por tabela Silver
# ============================================================
#
# Formato:
#   "tabela_silver": {
#       "tabela_staging_origem": "tabela_bronze_destino"
#   }
#
# A tabela_bronze_destino deve respeitar o nome usado dentro
# de QUERIES_SILVER.
#
# Exemplo:
#   Se QUERIES_SILVER["deputado"] usa:
#       FROM bronze.deputados dep
#
#   Então o destino aqui deve ser:
#       "stg_deputados_bruto": "deputados"
# ============================================================

DEPENDENCIAS_SILVER: dict[str, dict[str, str]] = {
    "deputado": {
        "stg_deputados_bruto": "deputados",
        "stg_legislaturas_bruto": "legislaturas",
        "stg_partidos_bruto": "partidos",
    },
    "orgao": {
        "stg_orgaos_bruto": "orgaos",
    },
    "evento": {
        "stg_eventos_bruto": "eventos",
        "stg_eventos_orgaos_bruto": "eventos_orgaos",
    },
    "proposicao": {
        "stg_proposicoes_bruto": "proposicoes",
        "stg_proposicoes_autores_bruto": "proposicoes_autores",
    },
    "despesa": {
        "stg_despesas_bruto": "despesas",
    },
    "votacao": {
        "stg_votos_bruto": "votos",
        "stg_votacoes_bruto": "votacoes",
    },
}


def preparar_bronze_em_dataframe(
    engine,
    dependencias: dict[str, str],
) -> dict[str, pd.DataFrame]:
    """
    Lê, trata e renomeia logicamente as tabelas staging para carga Bronze.

    O dicionário retornado usa como chave o nome físico que será criado
    no schema bronze.

    Exemplo:
        entrada:
            {
                "stg_deputados_bruto": "deputados"
            }

        saída:
            {
                "deputados": DataFrame(...)
            }

    Com isso, carregar_bronze() criará:
        bronze.deputados
    """
    tabelas_bronze: dict[str, pd.DataFrame] = {}

    for tabela_staging, tabela_bronze in dependencias.items():
        log.info("")
        log.info("🔹 Preparando tabela para Bronze")
        log.info("   Origem staging : %s", tabela_staging)
        log.info("   Destino bronze : bronze.%s", tabela_bronze)
        log.info("─" * 40)

        df = carregar_tabela(engine, tabela_staging)

        if df.empty:
            log.warning(
                "  ⚠ Tabela staging '%s' vazia ou inacessível — pulando.",
                tabela_staging,
            )
            continue

        inspecionar_tipos(df, tabela_staging)

        df = aplicar_conversoes(df, tabela_staging)
        df = corrigir_acentuacao(df, tabela_staging)
        df = remover_duplicatas(df, tabela_staging)

        tabelas_bronze[tabela_bronze] = df

        log.info(
            "  ✔ '%s' preparada como bronze.%s (%d linhas).",
            tabela_staging,
            tabela_bronze,
            len(df),
        )

    return tabelas_bronze


def validar_tabela_teste(nome_tabela: str) -> None:
    """
    Valida se a tabela Silver informada possui:
    - DDL em CREATES_SILVER;
    - query de carga em QUERIES_SILVER;
    - dependências Bronze mapeadas em DEPENDENCIAS_SILVER.
    """
    if nome_tabela not in CREATES_SILVER:
        raise KeyError(
            f"Tabela Silver '{nome_tabela}' não existe em CREATES_SILVER. "
            "Inclua o CREATE TABLE correspondente em pipeline/creates_silver.py."
        )

    if nome_tabela not in QUERIES_SILVER:
        raise KeyError(
            f"Tabela Silver '{nome_tabela}' não existe em QUERIES_SILVER. "
            "Inclua o INSERT correspondente em pipeline/queries_silver.py."
        )

    if nome_tabela not in DEPENDENCIAS_SILVER:
        raise KeyError(
            f"Tabela Silver '{nome_tabela}' não possui dependências mapeadas "
            "em DEPENDENCIAS_SILVER."
        )


def validar_dependencias_preparadas(
    dependencias: dict[str, str],
    tabelas_bronze: dict[str, pd.DataFrame],
) -> None:
    """
    Garante que todas as tabelas Bronze esperadas foram preparadas.

    Isso evita rodar a Silver com dependência faltante e receber erro
    posterior do PostgreSQL, como relation bronze.x does not exist.
    """
    esperadas = set(dependencias.values())
    preparadas = set(tabelas_bronze.keys())

    faltantes = esperadas - preparadas

    if faltantes:
        raise RuntimeError(
            "Nem todas as tabelas Bronze necessárias foram preparadas. "
            f"Faltantes: {sorted(faltantes)}"
        )


def main() -> None:
    log.info("=" * 60)
    log.info("🧪 TESTE INDIVIDUAL DA CAMADA SILVER")
    log.info("=" * 60)

    engine = conectar_sqlalchemy()

    if engine is None:
        raise RuntimeError("SQLAlchemy indisponível — verifique DB_URI_DDL no .env")

    validar_tabela_teste(TABELA_TESTE)

    dependencias = DEPENDENCIAS_SILVER[TABELA_TESTE]

    log.info("  Tabela Silver selecionada: %s", TABELA_TESTE)
    log.info("  Dependências Bronze necessárias:")

    for tabela_staging, tabela_bronze in dependencias.items():
        log.info("    %s -> bronze.%s", tabela_staging, tabela_bronze)

    tabelas_bronze = preparar_bronze_em_dataframe(
        engine=engine,
        dependencias=dependencias,
    )

    if not tabelas_bronze:
        raise RuntimeError("Nenhuma tabela foi preparada para Bronze. Teste abortado.")

    validar_dependencias_preparadas(
        dependencias=dependencias,
        tabelas_bronze=tabelas_bronze,
    )

    log.info("")
    log.info("=" * 60)
    log.info("🥉 CARREGANDO BRONZE FÍSICA PARA TESTE")
    log.info("=" * 60)

    carregar_bronze(
        tabelas=tabelas_bronze,
        engine=engine,
    )

    log.info("")
    log.info("=" * 60)
    log.info("🔮 EXECUTANDO SILVER DE TESTE: %s", TABELA_TESTE)
    log.info("=" * 60)

    carregar_silver(
        engine=engine,
        nome_tabela=TABELA_TESTE,
    )

    log.info("")
    log.info("=" * 60)
    log.info("✅ TESTE SILVER CONCLUÍDO COM SUCESSO")
    log.info("🥉 A Bronze foi mantida no banco para inspeção.")
    log.info("=" * 60)


if __name__ == "__main__":
    main()