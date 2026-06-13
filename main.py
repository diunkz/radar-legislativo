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
"""

import pandas as pd

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
from pipeline.carga_gold import executar_carga_gold
from pipeline.drop_bronze import drop_bronze

from pipeline.queries_silver import QUERIES_SILVER
from pipeline.queries_gold import QUERIES_GOLD


def main() -> None:
    log.info("=" * 60)
    log.info("  Radar Legislativo | Schema Manager")
    log.info("=" * 60)
    log.info("  Fluxo: Staging -> Tratamento -> Bronze -> Silver -> Gold -> Drop Bronze")
    log.info("  Pasta de saída CSV: %s", OUTPUT_DIR.resolve())
    log.info("=" * 60)

    _client = conectar_supabase()
    engine = conectar_sqlalchemy()

    if engine is None:
        raise RuntimeError("SQLAlchemy indisponível — verifique DB_URI_DDL no .env")

    tabelas_bronze: dict[str, pd.DataFrame] = {}
    csvs_gerados: list[str] = []

    # ============================================================
    # --- TRATAMENTO DAS STAGING EM MEMÓRIA ---
    # ============================================================
    log.info("")
    log.info("🚀 INICIANDO TRATAMENTO DAS TABELAS STAGING")
    log.info("=" * 60)

    for tabela in TABELAS:
        log.info("")
        log.info("🔹 Processando Staging: %s", tabela)
        log.info("─" * 40)

        df = carregar_tabela(engine, tabela)

        if df.empty:
            log.warning("  ⚠ Tabela '%s' vazia ou inacessível — pulando.", tabela)
            continue

        inspecionar_tipos(df, tabela)

        df = aplicar_conversoes(df, tabela)
        df = corrigir_acentuacao(df, tabela)
        df = remover_duplicatas(df, tabela)

        tabelas_bronze[tabela] = df

        log.info(
            "  ✔ Dados tratados da '%s' preparados para Bronze (%d linhas).",
            tabela,
            len(df),
        )

        csv_path = exportar_csv(df, tabela)

        if csv_path and csv_path.exists():
            csvs_gerados.append(str(csv_path))

    if not tabelas_bronze:
        raise RuntimeError(
            "Nenhuma tabela staging foi preparada para Bronze. Pipeline abortada."
        )

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

        for tabela_gold in QUERIES_GOLD:
            log.info("  🌟 Executando Gold: %s", tabela_gold)

            executar_carga_gold(
                tabela_gold,
                engine,
            )

            log.info("  ✓ Gold.%s processada.", tabela_gold)

    finally:
        # ============================================================
        # --- DROP DA BRONZE ---
        # ============================================================
        log.info("")
        log.info("=" * 60)
        log.info("🧹 REMOVENDO CAMADA BRONZE TRANSITÓRIA")
        log.info("=" * 60)

        drop_bronze(engine)

    # ============================================================
    # --- RESUMO FINAL ---
    # ============================================================
    log.info("")
    log.info("=" * 60)
    log.info("📊 RESUMO DO PROCESSAMENTO")
    log.info("=" * 60)
    log.info("  Tabelas Staging processadas : %d", len(TABELAS))
    log.info("  Tabelas Bronze carregadas   : %d", len(tabelas_bronze))
    log.info("  Tabelas Silver executadas   : %d", len(QUERIES_SILVER))
    log.info("  Tabelas Gold executadas     : %d", len(QUERIES_GOLD))
    log.info("  Arquivos CSVs gerados       : %d", len(csvs_gerados))
    log.info("=" * 60)
    log.info("🏁 PIPELINE EXECUTADA COM SUCESSO")
    log.info("🥉 Bronze física criada, usada e removida ao final.")
    log.info("=" * 60)


if __name__ == "__main__":
    main()