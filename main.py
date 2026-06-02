"""
main.py
-------
Orquestrador do pipeline Radar Legislativo | Schema Manager.
Este arquivo não contém lógica de negócio — apenas sequencia as etapas.
Para alterar comportamento, edite o módulo responsável pela etapa.
"""

from config import OUTPUT_DIR, TABELAS
from conexoes.sqlalchemy_engine import conectar_sqlalchemy
from conexoes.supabase_client import conectar_supabase
from logger import log
from pipeline.conversao import aplicar_conversoes
from pipeline.conversao_tipos import CONVERSAO_TIPOS
from pipeline.deduplicacao import remover_duplicatas
from pipeline.exportacao import exportar_csv
from pipeline.inspecao import inspecionar_tipos
from pipeline.leitura import carregar_tabela


def main() -> None:
    log.info("=" * 60)
    log.info("  Radar Legislativo | Schema Manager")
    log.info("=" * 60)
    log.info("  Pasta de saída: %s", OUTPUT_DIR.resolve())
    log.info("=" * 60)

    # --- 1. Conexões ---
    _client = conectar_supabase()
    engine  = conectar_sqlalchemy()  # opcional; usado em etapas de DDL

    if engine is None:
        raise RuntimeError("SQLAlchemy indisponível — verifique DB_URI_DDL no .env")

    csvs_gerados: list[str] = []

    # --- Pipeline por tabela ---
    for tabela in TABELAS:
        log.info("")
        log.info("━" * 60)
        log.info("  Tabela: %s", tabela)
        log.info("━" * 60)

        # 2. Leitura
        df = carregar_tabela(engine, tabela)
        if df.empty:
            log.warning("  Tabela '%s' vazia ou inacessível — pulando.", tabela)
            continue

        # 3. Inspeção de tipos
        inspecionar_tipos(df, tabela)

        # 4. Conversão de tipos
        df = aplicar_conversoes(df, tabela)

        # 5. Remoção de duplicatas
        df = remover_duplicatas(df, tabela)

        # 6 + 7. Exportação CSV
        csv_path = exportar_csv(df, tabela)
        if csv_path and csv_path.exists():
            csvs_gerados.append(str(csv_path))

    # --- Resumo final ---
    log.info("")
    log.info("=" * 60)
    log.info("  RESUMO")
    log.info("=" * 60)
    log.info("  Tabelas processadas : %d", len(TABELAS))
    log.info("  CSVs gerados        : %d", len(csvs_gerados))
    for csv in csvs_gerados:
        log.info("    → %s", csv)
    log.info("  Pasta de saída      : %s", OUTPUT_DIR.resolve())
    log.info("=" * 60)


if __name__ == "__main__":
    main()
