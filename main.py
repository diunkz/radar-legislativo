# """
# main.py
# -------
# Orquestrador do pipeline Radar Legislativo | Schema Manager.
# Este arquivo não contém lógica de negócio — apenas sequencia as etapas.
# Para alterar comportamento, edite o módulo responsável pela etapa.
# """

# from config import OUTPUT_DIR, TABELAS
# from conexoes.sqlalchemy_engine import conectar_sqlalchemy
# from conexoes.supabase_client import conectar_supabase
# from logger import log
# from pipeline.carga_bronze import carregar_bronze
# from pipeline.carga_gold import executar_carga_gold
# from pipeline.carga_silver import executar_carga_silver
# from pipeline.conversao import aplicar_conversoes
# from pipeline.correcao_texto import corrigir_acentuacao
# from pipeline.conversao_tipos import CONVERSAO_TIPOS
# from pipeline.deduplicacao import remover_duplicatas
# from pipeline.exportacao import exportar_csv
# from pipeline.inspecao import inspecionar_tipos
# from pipeline.leitura import carregar_tabela
# from pipeline.queries_gold import QUERIES_GOLD
# from pipeline.queries_silver import QUERIES_SILVER


# def main() -> None:
#     log.info("=" * 60)
#     log.info("  Radar Legislativo | Schema Manager")
#     log.info("=" * 60)
#     log.info("  Pasta de saída: %s", OUTPUT_DIR.resolve())
#     log.info("=" * 60)

#     # --- 1. Conexões ---
#     _client = conectar_supabase()
#     engine  = conectar_sqlalchemy()  # opcional; usado em etapas de DDL

#     if engine is None:
#         raise RuntimeError("SQLAlchemy indisponível — verifique DB_URI_DDL no .env")

#     csvs_gerados: list[str] = []

#     # --- Pipeline por tabela ---
#     for tabela in TABELAS:
#         log.info("")
#         log.info("━" * 60)
#         log.info("  Tabela: %s", tabela)
#         log.info("━" * 60)

#         # 2. Leitura
#         df = carregar_tabela(engine, tabela)
#         if df.empty:
#             log.warning("  Tabela '%s' vazia ou inacessível — pulando.", tabela)
#             continue

#         # 3. Inspeção de tipos
#         inspecionar_tipos(df, tabela)

#         # 4. Conversão de tipos
#         df = aplicar_conversoes(df, tabela)
       
#         # 5. Correção de acentuação PT-BR
#         df = corrigir_acentuacao(df, tabela)

#         # 6. Remoção de duplicatas
#         df = remover_duplicatas(df, tabela)
        
#         # 7. Grava o resultado tratado na camada Bronze
#         #    (staging permanece intocada; a camada Silver lê a partir daqui)
#         carregar_bronze(df, tabela, engine)

#         # 8. Exportação CSV
#         csv_path = exportar_csv(df, tabela)
#         if csv_path and csv_path.exists():
#             csvs_gerados.append(str(csv_path))
            
# # --- Camada Silver ---
#         # Executada após o loop staging/Bronze, pois cada tabela Silver pode
#         # depender de JOINs entre múltiplas tabelas Bronze
#         # (ex.: deputado x legislatura x partido).
#         log.info("")
#         log.info("=" * 60)
#         log.info("  CAMADA SILVER")
#         log.info("=" * 60)

#     for tabela_silver in QUERIES_SILVER:
#         executar_carga_silver(tabela_silver, engine)

#     # --- Camada Gold ---
#     # Executada após a Silver, pois as dimensões e fatos dependem dos dados
#     # já consolidados e transformados na camada Silver.
#     # IMPORTANTE: a ordem de execução é crítica — dimensões rodam antes das
#     # tabelas fato (fatos usam sk_* geradas pelas dimensões).
#         log.info("")
#         log.info("=" * 60)
#         log.info("  CAMADA GOLD")
#         log.info("=" * 60)

#     for tabela_gold in QUERIES_GOLD:
#         executar_carga_gold(tabela_gold, engine)



#     # --- Resumo final ---
#     log.info("")
#     log.info("=" * 60)
#     log.info("  RESUMO")
#     log.info("=" * 60)
#     log.info("  Tabelas processadas : %d", len(TABELAS))
#     log.info("  CSVs gerados        : %d", len(csvs_gerados))
#     # for csv in csvs_gerados:
#     #     log.info("    → %s", csv)
#     # log.info("  Pasta de saída      : %s", OUTPUT_DIR.resolve())
#     # log.info("=" * 60)


# if __name__ == "__main__":
#     main()

# """
# main.py
# -------
# Orquestrador do pipeline Radar Legislativo | Schema Manager.
# Este arquivo não contém lógica de negócio — apenas sequencia as etapas.
# Para alterar comportamento, edite o módulo responsável pela etapa.
# """

# from config import OUTPUT_DIR, TABELAS
# from conexoes.sqlalchemy_engine import conectar_sqlalchemy
# from conexoes.supabase_client import conectar_supabase
# from logger import log
# from pipeline.carga_bronze import carregar_bronze
# from pipeline.carga_gold import executar_carga_gold
# from pipeline.carga_silver import executar_carga_silver
# from pipeline.conversao import aplicar_conversoes
# from pipeline.correcao_texto import corrigir_acentuacao
# from pipeline.deduplicacao import remover_duplicatas
# from pipeline.exportacao import exportar_csv
# from pipeline.inspecao import inspecionar_tipos
# from pipeline.leitura import carregar_tabela
# from pipeline.queries_gold import QUERIES_GOLD
# from pipeline.queries_silver import QUERIES_SILVER


# def main() -> None:
#     log.info("=" * 60)
#     log.info("  Radar Legislativo | Schema Manager")
#     log.info("=" * 60)
#     log.info("  Pasta de saída: %s", OUTPUT_DIR.resolve())
#     log.info("=" * 60)

#     # --- 1. Conexões ---
#     _client = conectar_supabase()
#     engine  = conectar_sqlalchemy()

#     if engine is None:
#         raise RuntimeError("SQLAlchemy indisponível — verifique DB_URI_DDL no .env")

#     csvs_gerados: list[str] = []

#     # ============================================================
#     # --- CAMADA STAGING / BRONZE ---
#     # ============================================================
#     log.info("")
#     log.info("🚀 INICIANDO CAMADA STAGING -> BRONZE")
#     log.info("=" * 60)

#     for tabela in TABELAS:
#         log.info("")
#         log.info("🔹 Tabela: %s", tabela)
#         log.info("─" * 40)

#         # 2. Leitura
#         df = carregar_tabela(engine, tabela)
#         if df.empty:
#             log.warning("  ⚠ Tabela '%s' vazia ou inacessível — pulando.", tabela)
#             continue

#         # 3. Inspeção de tipos
#         inspecionar_tipos(df, tabela)

#         # 4. Conversão de tipos
#         df = aplicar_conversoes(df, tabela)
       
#         # 5. Correção de acentuação PT-BR
#         df = corrigir_acentuacao(df, tabela)

#         # 6. Remoção de duplicatas
#         df = remover_duplicatas(df, tabela)
        
#         # 7. Grava o resultado tratado na camada Bronze
#         carregar_bronze(df, tabela, engine)

#         # 8. Exportação CSV
#         csv_path = exportar_csv(df, tabela)
#         if csv_path and csv_path.exists():
#             csvs_gerados.append(str(csv_path))

#     # ============================================================
#     # --- CAMADA SILVER ---
#     # ============================================================
#     # AJUSTE: Movido para fora do loop das tabelas Staging
#     log.info("")
#     log.info("=" * 60)
#     log.info("🔮 INICIANDO CAMADA SILVER")
#     log.info("=" * 60)

#     for tabela_silver in QUERIES_SILVER:
#         log.info("  🔄 Carregando: %s", tabela_silver)
#         executar_carga_silver(tabela_silver, engine)
#         log.info("  ✓ %s processada.", tabela_silver)

#     # ============================================================
#     # --- CAMADA GOLD ---
#     # ============================================================
#     # AJUSTE: Movido para fora do loop da Camada Silver
#     log.info("")
#     log.info("=" * 60)
#     log.info("🏆 INICIANDO CAMADA GOLD")
#     log.info("=" * 60)

#     for tabela_gold in QUERIES_GOLD:
#         log.info("  🌟 Executando: %s", tabela_gold)
#         executar_carga_gold(tabela_gold, engine)
#         log.info("  ✓ %s processada.", tabela_gold)

#     # ============================================================
#     # --- RESUMO FINAL ---
#     # ============================================================
#     # AJUSTE: Logs ativados e alinhados
#     log.info("")
#     log.info("=" * 60)
#     log.info("📊 RESUMO DO PROCESSAMENTO")
#     log.info("=" * 60)
#     log.info("  Tabelas brancas processadas : %d", len(TABELAS))
#     log.info("  Tabelas Silver executadas   : %d", len(QUERIES_SILVER))
#     log.info("  Tabelas Gold executadas     : %d", len(QUERIES_GOLD))
#     log.info("  Arquivos CSVs gerados       : %d", len(csvs_gerados))
    
#     if csvs_gerados:
#         log.info("  Caminhos dos CSVs:")
#         for csv in csvs_gerados:
#             log.info("    → %s", csv)
            
#     log.info("=" * 60)
#     log.info("🏁 PIPELINE EXECUTADO COM SUCESSO")
#     log.info("=" * 60)


# if __name__ == "__main__":
#     main()

# """
# main.py
# -------
# Orquestrador do pipeline Radar Legislativo | Schema Manager.
# Fluxo: Staging -> Tratamento em Memória (Pandas) -> Camada Silver -> Camada Gold.
# """

# from pipeline.exportacao import OUTPUT_DIR
# from config import TABELAS
# from conexoes.sqlalchemy_engine import conectar_sqlalchemy
# from conexoes.supabase_client import conectar_supabase
# from logger import log
# from pipeline.carga_gold import executar_carga_gold
# from pipeline.carga_silver import executar_carga_silver_em_memoria
# from pipeline.conversao import aplicar_conversoes
# from pipeline.correcao_texto import corrigir_acentuacao
# from pipeline.deduplicacao import remover_duplicatas
# from pipeline.exportacao import exportar_csv
# from pipeline.inspecao import inspecionar_tipos
# from pipeline.leitura import carregar_tabela
# from pipeline.queries_gold import QUERIES_GOLD
# from pipeline.queries_silver import QUERIES_SILVER
# import pandas as pd


# def main() -> None:
#     log.info("=" * 60)
#     log.info("  Radar Legislativo | Schema Manager (In-Memory Processing)")
#     log.info("=" * 60)
#     log.info("  Pasta de saída CSV: %s", OUTPUT_DIR.resolve())
#     log.info("=" * 60)

#     _client = conectar_supabase()
#     engine  = conectar_sqlalchemy()

#     if engine is None:
#         raise RuntimeError("SQLAlchemy indisponível — verifique DB_URI_DDL no .env")

#     # Dicionário que guardará os DataFrames tratados na memória (Substitutos da camada Bronze física)
#     dataframes_bronze: dict[str, pd.DataFrame] = {}
#     csvs_gerados: list[str] = []

#     # ============================================================
#     # --- CAMADA PROCESSAMENTO EM MEMÓRIA (ANTIGA BRONZE) ---
#     # ============================================================
#     log.info("")
#     log.info("🚀 INICIANDO TRATAMENTO DE DADOS EM MEMÓRIA")
#     log.info("=" * 60)

#     for tabela in TABELAS:
#         log.info("")
#         log.info("🔹 Processando Staging: %s", tabela)
#         log.info("─" * 40)

#         # 2. Leitura da Staging original
#         df = carregar_tabela(engine, tabela)
#         if df.empty:
#             log.warning("  ⚠ Tabela '%s' vazia ou inacessível — pulando.", tabela)
#             continue

#         # 3. Inspeção de tipos
#         inspecionar_tipos(df, tabela)

#         # 4. Conversão de tipos
#         df = aplicar_conversoes(df, tabela)
       
#         # 5. Correção de acentuação PT-BR
#         df = corrigir_acentuacao(df, tabela)

#         # 6. Remoção de duplicatas e hífens
#         df = remover_duplicatas(df, tabela)
        
#         # Guardando o DataFrame limpo na memória associado ao seu nome original
#         dataframes_bronze[tabela] = df
#         log.info("  ✔ Dados da '%s' retidos em memória (%d linhas).", tabela, len(df))

#         # 8. Exportação CSV (Mantido para Auditoria local / Backup)
#         csv_path = exportar_csv(df, tabela)
#         if csv_path and csv_path.exists():
#             csvs_gerados.append(str(csv_path))

#     # ============================================================
#     # --- CAMADA SILVER ---
#     # ============================================================
#     log.info("")
#     log.info("=" * 60)
#     log.info("🔮 INICIANDO CAMADA SILVER (LEITURA DA MEMÓRIA)")
#     log.info("=" * 60)

#     # Executa a carga enviando o mapa de dataframes da memória
#     for tabela_silver in QUERIES_SILVER:
#         log.info("  🔄 Carregando: %s", tabela_silver)
#         executar_carga_silver_em_memoria(tabela_silver, engine, dataframes_bronze)
#         log.info("  ✓ %s processada.", tabela_silver)

#     # ============================================================
#     # --- CAMADA GOLD ---
#     # ============================================================
#     log.info("")
#     log.info("=" * 60)
#     log.info("🏆 INICIANDO CAMADA GOLD")
#     log.info("=" * 60)

#     for tabela_gold in QUERIES_GOLD:
#         log.info("  🌟 Executando: %s", tabela_gold)
#         executar_carga_gold(tabela_gold, engine)
#         log.info("  ✓ %s processada.", tabela_gold)

#     # ============================================================
#     # --- RESUMO FINAL ---
#     # ============================================================
#     log.info("")
#     log.info("=" * 60)
#     log.info("📊 RESUMO DO PROCESSAMENTO")
#     log.info("=" * 60)
#     log.info("  Tabelas Staging processadas : %d", len(TABELAS))
#     log.info("  Tabelas Silver executadas   : %d", len(QUERIES_SILVER))
#     log.info("  Tabelas Gold executadas     : %d", len(QUERIES_GOLD))
#     log.info("  Arquivos CSVs gerados       : %d", len(csvs_gerados))
#     log.info("=" * 60)
#     log.info("🏁 PIPELINE EXECUTADO COM SUCESSO (SEM BRONZE NO DB)")
#     log.info("=" * 60)


# if __name__ == "__main__":
#     main()


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
from pipeline.carga_silver import executar_carga_silver
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

        log.info("  ✔ Dados tratados da '%s' preparados para Bronze (%d linhas).", tabela, len(df))

        csv_path = exportar_csv(df, tabela)

        if csv_path and csv_path.exists():
            csvs_gerados.append(str(csv_path))

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

    for tabela_silver in QUERIES_SILVER:
        log.info("  🔄 Carregando Silver: %s", tabela_silver)

        executar_carga_silver(
            tabela_silver,
            engine,
        )

        log.info("  ✓ Silver.%s processada.", tabela_silver)

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
    log.info("🏁 PIPELINE EXECUTADO COM SUCESSO")
    log.info("🥉 Bronze física criada, usada e removida ao final.")
    log.info("=" * 60)


if __name__ == "__main__":
    main()