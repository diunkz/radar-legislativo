"""
main.py
-------
Orquestrador do pipeline Radar Legislativo | Schema Manager.

Fluxo:
    Staging
        -> Tratamento em Memória com Pandas
        -> Bronze física transitória no Supabase/PostgreSQL
        -> Camada Silver
        -> Camada Gold
        -> Drop da Bronze

Estratégia:
    FULL REFRESH

    A cada execução:
    1. Remove os schemas bronze, silver e gold, se existirem;
    2. Recria a Bronze física transitória;
    3. Recria a camada Silver com DROP + CREATE + INSERT;
    4. Recria a camada Gold com DROP + CREATE + INSERT;
    5. Remove a Bronze ao final.
"""

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from config import TABELAS
from conexoes.sqlalchemy_engine import conectar_sqlalchemy
from conexoes.supabase_client import conectar_supabase
from logger import log

from pipeline.exportacao import OUTPUT_DIR
from pipeline.leitura import carregar_tabela
from pipeline.inspecao import inspecionar_tipos
from pipeline.conversao import aplicar_conversoes
from pipeline.correcao_texto import corrigir_acentuacao
from pipeline.deduplicacao import remover_duplicatas
from pipeline.exportacao import exportar_csv

from pipeline.carga_bronze import carregar_bronze
from pipeline.carga_silver import carregar_silver
from pipeline.carga_gold import carregar_gold
from pipeline.drop_bronze import drop_bronze

from pipeline.queries_silver import QUERIES_SILVER
from pipeline.queries_gold import QUERIES_GOLD


DROPAR_BRONZE_AO_FINAL = True

SCHEMAS_PIPELINE = [
    "bronze",
    "silver",
    "gold",
]


# ============================================================
# Mapeamento Staging -> Bronze física
# ============================================================

MAPEAMENTO_BRONZE_DESTINO: dict[str, str] = {
    "stg_deputados_bruto": "deputados",
    "stg_legislaturas_bruto": "legislaturas",
    "stg_partidos_bruto": "partidos",

    "stg_orgaos_bruto": "orgaos",

    "stg_eventos_bruto": "eventos",
    "stg_eventos_orgaos_bruto": "eventos_orgaos",

    "stg_proposicoes_bruto": "proposicoes",
    "stg_proposicoes_autores_bruto": "proposicoes_autores",

    "stg_despesas_bruto": "despesas",

    "stg_votos_bruto": "votos",
    "stg_votacoes_bruto": "votacoes",

    "stg_frentes_bruto": "frentes",
    "stg_liderancas_bruto": "liderancas",
}


def _quote_identificador(identificador: str) -> str:
    """
    Aplica aspas duplas em identificadores SQL.
    """
    if not isinstance(identificador, str) or not identificador.strip():
        raise ValueError("Identificador SQL inválido ou vazio.")

    return f'"{identificador.replace(chr(34), chr(34) * 2)}"'


def dropar_schema(
    engine: Engine,
    schema: str,
) -> None:
    """
    Remove um schema inteiro, se existir.
    """
    schema_quotado = _quote_identificador(schema)

    with engine.begin() as conn:
        conn.execute(text(f"DROP SCHEMA IF EXISTS {schema_quotado} CASCADE"))

    log.info("  ✔ Schema '%s' removido, se existia.", schema)


def preparar_ambiente_inicial(engine: Engine) -> None:
    """
    Prepara o ambiente antes da execução da pipeline.

    Estratégia:
        FULL REFRESH

    Remove bronze, silver e gold no início da execução para garantir
    que não existam resíduos de tabelas, constraints, sequences ou dados
    de execuções anteriores.
    """
    log.info("")
    log.info("=" * 60)
    log.info("🧭 PREPARANDO AMBIENTE INICIAL")
    log.info("=" * 60)
    log.info("  Estratégia: FULL REFRESH")
    log.info("  Ação: remover schemas bronze, silver e gold.")

    for schema in SCHEMAS_PIPELINE:
        dropar_schema(
            engine=engine,
            schema=schema,
        )

    log.info("  ✔ Ambiente preparado para execução FULL REFRESH.")


def obter_nome_bronze(tabela_staging: str) -> str:
    """
    Retorna o nome físico da tabela no schema bronze.

    Quando a tabela staging estiver mapeada, usa o nome esperado
    pelas queries Silver.

    Quando não estiver mapeada, mantém o nome original para não
    interromper a pipeline, mas registra um warning.
    """
    nome_bronze = MAPEAMENTO_BRONZE_DESTINO.get(tabela_staging)

    if nome_bronze:
        return nome_bronze

    log.warning(
        "  ⚠ Tabela '%s' não possui mapeamento Bronze. "
        "Será carregada como bronze.%s.",
        tabela_staging,
        tabela_staging,
    )

    return tabela_staging


def preparar_tabelas_bronze(
    engine: Engine,
) -> tuple[dict[str, pd.DataFrame], list[str]]:
    """
    Lê, trata e prepara as tabelas staging em memória antes da carga Bronze.

    Retorna:
        - dicionário com nome físico da Bronze -> DataFrame tratado;
        - lista de CSVs gerados.
    """
    tabelas_bronze: dict[str, pd.DataFrame] = {}
    csvs_gerados: list[str] = []

    log.info("")
    log.info("🚀 INICIANDO TRATAMENTO DAS TABELAS STAGING")
    log.info("=" * 60)

    for tabela_staging in TABELAS:
        log.info("")
        log.info("🔹 Processando Staging: %s", tabela_staging)
        log.info("─" * 40)

        df = carregar_tabela(engine, tabela_staging)

        if df.empty:
            log.warning(
                "  ⚠ Tabela '%s' vazia ou inacessível — pulando.",
                tabela_staging,
            )
            continue

        inspecionar_tipos(df, tabela_staging)

        df = aplicar_conversoes(df, tabela_staging)
        df = corrigir_acentuacao(df, tabela_staging)
        df = remover_duplicatas(df, tabela_staging)

        nome_bronze = obter_nome_bronze(tabela_staging)

        if nome_bronze in tabelas_bronze:
            raise RuntimeError(
                f"Mapeamento Bronze duplicado detectado: bronze.{nome_bronze}. "
                f"Verifique MAPEAMENTO_BRONZE_DESTINO."
            )

        tabelas_bronze[nome_bronze] = df

        log.info(
            "  ✔ Dados tratados da '%s' preparados para bronze.%s (%d linhas).",
            tabela_staging,
            nome_bronze,
            len(df),
        )

        csv_path = exportar_csv(df, tabela_staging)

        if csv_path and csv_path.exists():
            csvs_gerados.append(str(csv_path))

    if not tabelas_bronze:
        raise RuntimeError(
            "Nenhuma tabela staging foi preparada para Bronze. Pipeline abortada."
        )

    return tabelas_bronze, csvs_gerados


def main() -> None:
    log.info("=" * 60)
    log.info("  Radar Legislativo | Schema Manager")
    log.info("=" * 60)
    log.info("  Fluxo: Staging -> Tratamento -> Bronze -> Silver -> Gold -> Drop Bronze")
    log.info("  Estratégia: FULL REFRESH")
    log.info("  Pasta de saída CSV: %s", OUTPUT_DIR.resolve())
    log.info("=" * 60)

    _client = conectar_supabase()
    engine = conectar_sqlalchemy()

    if engine is None:
        raise RuntimeError("SQLAlchemy indisponível — verifique DB_URI_DDL no .env")

    preparar_ambiente_inicial(engine)

    tabelas_bronze, csvs_gerados = preparar_tabelas_bronze(engine)

    try:
        # ============================================================
        # --- CAMADA BRONZE FÍSICA TRANSITÓRIA ---
        # ============================================================
        log.info("")
        log.info("=" * 60)
        log.info("🥉 INICIANDO CAMADA BRONZE FÍSICA TRANSITÓRIA")
        log.info("=" * 60)

        carregar_bronze(
            tabelas=tabelas_bronze,
            engine=engine,
        )

        log.info("  ✔ Bronze física carregada com sucesso.")

        # ============================================================
        # --- CAMADA SILVER ---
        # ============================================================
        log.info("")
        log.info("=" * 60)
        log.info("🔮 INICIANDO CAMADA SILVER")
        log.info("=" * 60)

        carregar_silver(engine)

        log.info("  ✔ Camada Silver processada com sucesso.")

        # ============================================================
        # --- CAMADA GOLD ---
        # ============================================================
        log.info("")
        log.info("=" * 60)
        log.info("🏆 INICIANDO CAMADA GOLD")
        log.info("=" * 60)

        carregar_gold(engine)

        log.info("  ✔ Camada Gold processada com sucesso.")

    finally:
        if DROPAR_BRONZE_AO_FINAL:
            log.info("")
            log.info("=" * 60)
            log.info("🧹 REMOVENDO CAMADA BRONZE TRANSITÓRIA")
            log.info("=" * 60)

            drop_bronze(engine)

            log.info("  ✔ Bronze transitória removida ao final.")
        else:
            log.info("")
            log.info("🥉 Bronze mantida no banco para inspeção.")

    log.info("")
    log.info("=" * 60)
    log.info("📊 RESUMO DO PROCESSAMENTO")
    log.info("=" * 60)
    log.info("  Estratégia                  : FULL REFRESH")
    log.info("  Tabelas Staging processadas : %d", len(TABELAS))
    log.info("  Tabelas Bronze carregadas   : %d", len(tabelas_bronze))
    log.info("  Tabelas Silver executadas   : %d", len(QUERIES_SILVER))
    log.info("  Tabelas Gold executadas     : %d", len(QUERIES_GOLD))
    log.info("  Arquivos CSVs gerados       : %d", len(csvs_gerados))
    log.info("=" * 60)
    log.info("🏁 PIPELINE EXECUTADA COM SUCESSO")
    log.info("🥉 Bronze física criada, usada e removida ao final.")
    log.info("🔮 Silver recriada via DROP + CREATE + INSERT.")
    log.info("🏆 Gold recriada via DROP + CREATE + INSERT.")
    log.info("=" * 60)


if __name__ == "__main__":
    main()