"""
test_silver.py
--------------
Script de teste isolado para validar a query de 'votacao' em memória.

Uso:
    uv run test_silver.py
"""

# import os
# import sys
# import pandas as pd

# # SOLUÇÃO DEFINITIVA: Garante que o Python encontre o logger.py na raiz do projeto
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# from conexoes.sqlalchemy_engine import conectar_sqlalchemy
# from logger import log
# from pipeline.carga_silver import executar_carga_silver_em_memoria
# from pipeline.queries_silver import QUERIES_SILVER
# from pipeline.leitura import carregar_tabela
# from pipeline.conversao import aplicar_conversoes
# from pipeline.correcao_texto import corrigir_acentuacao
# from pipeline.deduplicacao import remover_duplicatas


# def test_silver_isolado() -> None:
#     """
#     Executa o teste da query Silver 'tabela' carregando apenas suas tabelas dependentes.
#     """
#     log.info("=" * 60)
#     log.info("  🚀 TESTE ISOLADO: SILVER (EM MEMÓRIA)")
#     log.info("=" * 60)

#     engine = conectar_sqlalchemy()
#     if engine is None:
#         raise RuntimeError("SQLAlchemy indisponível — verifique DB_URI_DDL no .env")

#     # AJUSTE: Mapeia apenas as duas tabelas de staging que a query 'votacao' utiliza
#     TABELAS = ["stg_votos_bruto", "stg_votacoes_bruto"]
#     dataframes_bronze: dict[str, pd.DataFrame] = {}
    
#     log.info("📦 Carregando apenas dependências para a memória...")
#     log.info("─" * 60)

#     for staging_tabela in TABELAS:
#         try:
#             log.info("  🔹 Processando Staging: %s", staging_tabela)
#             df = carregar_tabela(engine, staging_tabela)
#             if df.empty:
#                 log.warning("  ⚠ Tabela '%s' está vazia — o teste pode falhar.", staging_tabela)
#                 continue
                
#             # Esteira de tratamento em memória (garante a limpeza do hífen do ID)
#             df = aplicar_conversoes(df, staging_tabela)
#             df = corrigir_acentuacao(df, staging_tabela)
#             df = remover_duplicatas(df, staging_tabela)
            
#             # Retém o DataFrame tratado no dicionário volátil
#             dataframes_bronze[staging_tabela] = df
#             log.info("  ✓ '%s' pronta em memória (%d linhas).", staging_tabela, len(df))
#         except Exception as err:
#             log.error("  ✗ Falha crítica ao preparar staging '%s': %s", staging_tabela, err)
#             return

#     log.info("=" * 60)

#     # Executa a carga da query 'tabela' usando apenas as origens carregadas acima
#     tabela_alvo = "votacao"
#     if tabela_alvo not in QUERIES_SILVER:
#         log.error("  ✗ '%s' não existe em QUERIES_SILVER — abortando.", tabela_alvo)
#         return

#     try:
#         log.info("  🔮 Executando query Silver: %s", tabela_alvo)
        
#         # Injeta as tabelas temporárias e roda o INSERT com a chave concatenada
#         executar_carga_silver_em_memoria(tabela_alvo, engine, dataframes_bronze)
        
#         log.info("  ✓ '%s' OK — Carga concluída com sucesso!", tabela_alvo)
#     except Exception as exc:
#         log.error("  ✗ '%s' FALHOU: %s", tabela_alvo, exc)

#     log.info("=" * 60)
#     log.info("🏁 TESTE ISOLADO FINALIZADO")
#     log.info("=" * 60)


# if __name__ == "__main__":
#     test_silver_isolado()


"""
test_silver.py
--------------
Teste isolado da carga Silver.

Este teste monta a Bronze necessária, executa uma query Silver
e mantém a Bronze disponível para inspeção.
"""

"""
test_silver.py
--------------
Teste isolado da carga Silver.

Este teste:
1. Lê as tabelas Staging configuradas em config.TABELAS;
2. Aplica conversão, correção de texto e deduplicação;
3. Cria/carrega a Bronze física transitória;
4. Executa uma tabela Silver específica;
5. Mantém a Bronze no banco para inspeção.

Observação:
    Diferente do main.py, este teste NÃO executa drop_bronze().
"""

"""
test_silver.py
--------------
Teste isolado da carga Silver.

Este teste:
1. Define uma tabela Silver específica em TABELA_TESTE;
2. Lê somente as tabelas Staging/Bronze necessárias para essa Silver;
3. Aplica conversão, correção de texto e deduplicação;
4. Cria/carrega a Bronze física transitória;
5. Executa somente a Silver escolhida;
6. Mantém a Bronze no banco para inspeção.

Observação:
    Diferente do main.py, este teste NÃO executa drop_bronze().
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
from pipeline.carga_silver import carregar_tabela_silver
from pipeline.queries_silver import QUERIES_SILVER


# ============================================================
# EDITE AQUI: escolha uma tabela Silver para testar
# ============================================================

TABELA_TESTE = "votacao"


# ============================================================
# Dependências Bronze necessárias por tabela Silver
# ============================================================

DEPENDENCIAS_SILVER: dict[str, list[str]] = {
    "deputado": [
        "stg_deputados_bruto",
        "stg_legislaturas_bruto",
        "stg_partidos_bruto",
    ],
    "orgao": [
        "stg_orgaos_bruto",
    ],
    "evento": [
        "stg_eventos_bruto",
        "stg_eventos_orgaos_bruto",
    ],
    "proposicao": [
        "stg_proposicoes_bruto",
        "stg_proposicoes_autores_bruto",
    ],
    "despesa": [
        "stg_despesas_bruto",
    ],
    "votacao": [
        "stg_votos_bruto",
        "stg_votacoes_bruto",
    ],
}


def preparar_bronze_em_dataframe(
    engine,
    tabelas_origem: list[str],
) -> dict[str, pd.DataFrame]:
    """
    Lê e trata somente as tabelas staging necessárias
    antes de carregar a Bronze física.
    """
    tabelas_bronze: dict[str, pd.DataFrame] = {}

    for tabela in tabelas_origem:
        log.info("")
        log.info("🔹 Preparando tabela para Bronze: %s", tabela)
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
            "  ✔ '%s' preparada para Bronze (%d linhas).",
            tabela,
            len(df),
        )

    return tabelas_bronze


def main() -> None:
    log.info("=" * 60)
    log.info("🧪 TESTE INDIVIDUAL DA CAMADA SILVER")
    log.info("=" * 60)

    engine = conectar_sqlalchemy()

    if engine is None:
        raise RuntimeError("SQLAlchemy indisponível — verifique DB_URI_DDL no .env")

    if TABELA_TESTE not in QUERIES_SILVER:
        raise KeyError(f"Tabela Silver '{TABELA_TESTE}' não existe em QUERIES_SILVER.")

    if TABELA_TESTE not in DEPENDENCIAS_SILVER:
        raise KeyError(
            f"Tabela Silver '{TABELA_TESTE}' não possui dependências mapeadas "
            "em DEPENDENCIAS_SILVER."
        )

    tabelas_origem = DEPENDENCIAS_SILVER[TABELA_TESTE]

    log.info("  Tabela Silver selecionada: %s", TABELA_TESTE)
    log.info("  Tabelas Bronze necessárias: %s", ", ".join(tabelas_origem))

    tabelas_bronze = preparar_bronze_em_dataframe(
        engine=engine,
        tabelas_origem=tabelas_origem,
    )

    if not tabelas_bronze:
        raise RuntimeError("Nenhuma tabela foi preparada para Bronze. Teste abortado.")

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

    carregar_tabela_silver(
        nome_tabela=TABELA_TESTE,
        query_insert=QUERIES_SILVER[TABELA_TESTE],
        engine=engine,
    )

    log.info("")
    log.info("=" * 60)
    log.info("✅ TESTE SILVER CONCLUÍDO COM SUCESSO")
    log.info("🥉 A Bronze foi mantida no banco para inspeção.")
    log.info("=" * 60)


if __name__ == "__main__":
    main()