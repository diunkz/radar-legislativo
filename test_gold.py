# """
# test_gold.py
# --------------
# Script de teste para validar um subconjunto de queries Gold
# (dimensões + fatos específicas) sem rodar o pipeline completo.

# Uso:
#     python test_gold.py

# Edite a lista TABELAS_TESTE para escolher quais dimensões/fatos testar.
# """

# from conexoes.sqlalchemy_engine import conectar_sqlalchemy
# from logger import log
# from pipeline.carga_gold import executar_carga_gold
# from pipeline.queries_gold import QUERIES_GOLD


# def test_gold(tabelas_teste: list[str]) -> None:
#     """
#     Executa um subconjunto de queries Gold para testes.

#     Parameters
#     ----------
#     tabelas_teste : lista de nomes de tabelas a testar
#                     (ex.: ["dim_deputado", "fato_despesa"])
#     """
#     log.info("=" * 60)
#     log.info("  TESTE CAMADA GOLD")
#     log.info("=" * 60)

#     engine = conectar_sqlalchemy()
#     if engine is None:
#         raise RuntimeError("SQLAlchemy indisponível — verifique DB_URI_DDL no .env")

#     log.info("  Testando: %s", ", ".join(tabelas_teste))
#     log.info("=" * 60)

#     for tabela in tabelas_teste:
#         if tabela not in QUERIES_GOLD:
#             log.error("  ✗ '%s' não existe em QUERIES_GOLD — pulando.", tabela)
#             continue

#         try:
#             log.info("")
#             log.info("  Executando: %s", tabela)
#             executar_carga_gold(tabela, engine)
#             log.info("  ✓ '%s' OK", tabela)
#         except Exception as exc:  # noqa: BLE001
#             log.error("  ✗ '%s' FALHOU: %s", tabela, exc)

#     log.info("")
#     log.info("=" * 60)
#     log.info("  TESTE FINALIZADO")
#     log.info("=" * 60)


# if __name__ == "__main__":
#     # ============================================================
#     # EDITE AQUI: escolha quais tabelas testar
#     # ============================================================
#     TABELAS_TESTE = [
#         #"dim_deputado",
#         #"ft_despesa",
#         #"dim_orgao",
#         #"dim_evento"
#         #"dim_proposicao"
#         #"dim_votacao"
#         "ft_proposicao"
#         #"ft_voto"
#     ]

#     test_gold(TABELAS_TESTE)


"""
test_gold.py
------------
Script de teste para validar queries Gold individualmente.

Pré-requisito:
    As tabelas Silver já devem estar carregadas no banco.

Uso:
    python test_gold.py

Edite TABELA_TESTE para escolher qual dimensão/fato testar.
"""

from conexoes.sqlalchemy_engine import conectar_sqlalchemy
from logger import log
from pipeline.carga_gold import executar_carga_gold
from pipeline.queries_gold import QUERIES_GOLD


TABELA_TESTE = "ft_proposicao"


def test_gold(tabela_teste: str) -> None:
    """
    Executa uma única carga Gold para teste manual.

    Parameters
    ----------
    tabela_teste : str
        Nome da tabela Gold a testar.
        Ex.: "dim_deputado", "ft_despesa", "ft_proposicao", "ft_voto".
    """
    log.info("=" * 60)
    log.info("🏆 TESTE INDIVIDUAL CAMADA GOLD")
    log.info("=" * 60)

    engine = conectar_sqlalchemy()

    if engine is None:
        raise RuntimeError("SQLAlchemy indisponível — verifique DB_URI_DDL no .env")

    if tabela_teste not in QUERIES_GOLD:
        raise KeyError(f"'{tabela_teste}' não existe em QUERIES_GOLD.")

    log.info("  Tabela Gold selecionada: %s", tabela_teste)
    log.info("  Pré-requisito: Silver já carregada.")
    log.info("=" * 60)

    try:
        executar_carga_gold(tabela_teste, engine)
        log.info("  ✓ Gold.%s processada com sucesso.", tabela_teste)

    except Exception as exc:
        log.exception("  ✗ Gold.%s falhou: %s", tabela_teste, exc)
        raise

    log.info("=" * 60)
    log.info("✅ TESTE GOLD FINALIZADO")
    log.info("=" * 60)


if __name__ == "__main__":
    test_gold(TABELA_TESTE)