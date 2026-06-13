# """
# pipeline/carga_silver.py
# --------------------------
# Responsabilidade única: executar a transformação Bronze -> Silver
# diretamente no PostgreSQL, via TRUNCATE + INSERT INTO ... SELECT.

# A query (com os JOINs, CASE, COALESCE etc.) vive em
# pipeline/queries_silver.py — este módulo apenas orquestra a execução.

# Estratégia de carga: TRUNCATE + INSERT (full load).
#   - TRUNCATE garante idempotência: rodar o pipeline várias vezes não duplica
#     registros nem deixa "lixo" de cargas anteriores.
#   - Se no futuro for necessária carga incremental, troque a estratégia aqui
#     — o restante do pipeline não precisa mudar.
# """

# from sqlalchemy import Engine, text

# from logger import log
# from pipeline.queries_silver import QUERIES_SILVER, SCHEMA_SILVER


# def executar_carga_silver(tabela_destino: str, engine: Engine) -> None:
#     """
#     Executa TRUNCATE + INSERT INTO ... SELECT para `silver.<tabela_destino>`,
#     usando a query definida em QUERIES_SILVER.

#     Parameters
#     ----------
#     tabela_destino : nome da tabela Silver, sem schema (ex.: "deputado")
#     engine : engine SQLAlchemy (DB_URI_DDL)
#     """
#     query = QUERIES_SILVER.get(tabela_destino)
#     nome_completo = f"{SCHEMA_SILVER}.{tabela_destino}"

#     if query is None:
#         log.warning("  [silver] Nenhuma query definida para '%s' — pulando.", nome_completo)
#         return

#     try:
#         with engine.begin() as conn:
#             # TRUNCATE garante full load idempotente
#             conn.execute(text(f"TRUNCATE TABLE {nome_completo}"))  # noqa: S608

#             resultado = conn.execute(text(query))

#         log.info(
#             "  [silver] %d linha(s) inserida(s) em '%s'.",
#             resultado.rowcount, nome_completo,
#         )

#     except Exception as exc:  # noqa: BLE001
#         log.error("  [silver] Erro ao carregar '%s': %s", nome_completo, exc)
#         raise

"""
pipeline/carga_silver.py
--------------------------
Responsabilidade: Criar tabelas temporárias na sessão do banco usando os DataFrames 
da memória e rodar as cargas da Silver de forma isolada, limpa e performática.
"""

# import os
# import sys
# import pandas as pd
# from sqlalchemy import Engine, text

# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# from logger import log
# from pipeline.queries_silver import QUERIES_SILVER, SCHEMA_SILVER
# from pipeline.mapeamento_bronze import TABELA_BRONZE, SCHEMA_BRONZE


# def executar_carga_silver_em_memoria(tabela_destino: str, engine: Engine, dataframes_bronze: dict[str, pd.DataFrame]) -> None:
#     """
#     Injeta os dataframes necessários como tabelas temporárias e executa o INSERT da Silver.
#     """
#     query = QUERIES_SILVER.get(tabela_destino)
#     nome_completo_silver = f'"{SCHEMA_SILVER}"."{tabela_destino}"'

#     if query is None:
#         log.warning("  [silver] Nenhuma query definida para '%s' — pulando.", tabela_destino)
#         return

#     try:
#         # Iniciamos uma transação única
#         with engine.begin() as conn:
            
#             # 1. Cria o schema temporário/físico bronze para a query ler de forma compatível
#             conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA_BRONZE}"'))

#             # 2. Injeta CADA DataFrame do dicionário de memória para dentro do banco de dados
#             #    COMO tabelas do schema bronze na sessão atual. 
#             #    Isso substitui as tabelas permanentes antigas e economiza espaço em disco rígido!
#             for tabela_origem, df_tratado in dataframes_bronze.items():
#                 nome_tabela_bronze = TABELA_BRONZE.get(tabela_origem)
                
#                 if nome_tabela_bronze:
#                     # Carrega temporariamente para o PostgreSQL usar durante o SELECT da Silver
#                     df_tratado.to_sql(
#                         name=nome_tabela_bronze,
#                         con=conn,
#                         schema=SCHEMA_BRONZE,
#                         if_exists="replace", # Substitui o cache da memória na sessão
#                         index=False,
#                         method="multi",
#                         chunksize=50
#                     )

#             # 3. Limpa a tabela Silver de destino de forma segura
#             conn.execute(text(f"TRUNCATE TABLE {nome_completo_silver} CASCADE"))

#             # 4. Executa a query de transformação que lê do schema bronze populado acima
#             resultado = conn.execute(text(query))
#             linhas_afetadas = resultado.rowcount if resultado.rowcount is not None and resultado.rowcount >= 0 else 0

#         log.info(
#             "  [silver] %d linha(s) inserida(s) em '%s' a partir da memória.",
#             linhas_afetadas, nome_completo_silver,
#         )

#     except Exception as exc:
#         log.error("  [silver] Erro ao carregar '%s' via memória: %s", nome_completo_silver, exc)
#         raise

# """
# pipeline/carga_silver.py
# --------------------------
# Responsabilidade: Criar tabelas temporárias na sessão do banco usando os DataFrames 
# da memória e rodar as cargas da Silver de forma isolada, limpa e performática.
# """

# import os
# import sys
# import pandas as pd
# from sqlalchemy import Engine, text

# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# from logger import log
# from pipeline.queries_silver import QUERIES_SILVER, SCHEMA_SILVER
# from pipeline.mapeamento_bronze import TABELA_BRONZE, SCHEMA_BRONZE


# def executar_carga_silver_em_memoria(tabela_destino: str, engine: Engine, dataframes_bronze: dict[str, pd.DataFrame]) -> None:
#     """
#     Injeta os dataframes necessários como tabelas temporárias e executa o INSERT da Silver.
#     """
#     query = QUERIES_SILVER.get(tabela_destino)
#     nome_completo_silver = f'"{SCHEMA_SILVER}"."{tabela_destino}"'

#     if query is None:
#         log.warning("  [silver] Nenhuma query definida para '%s' — pulando.", tabela_destino)
#         return

#     try:
#         with engine.begin() as conn:
#             # 1. Cria o schema temporário/físico bronze para a query ler de forma compatível
#             conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA_BRONZE}"'))

#             # 2. Injeta CADA DataFrame do dicionário de memória para dentro do banco de dados
#             for tabela_origem, df_original in dataframes_bronze.items():
#                 nome_tabela_bronze = TABELA_BRONZE.get(tabela_origem)
                
#                 if nome_tabela_bronze:
#                     # CORREÇÃO CRÍTICA: Faz uma cópia e limpa os pontos finais (.) substituindo por underline (_)
#                     # Exemplo: 'deputado_.id' vira 'deputado__id' no banco temporário
#                     df_tratado = df_original.copy()
#                     df_tratado.columns = [col.replace(".", "_") for col in df_tratado.columns]

#                     # Carrega temporariamente para o PostgreSQL usar durante o SELECT da Silver
#                     df_tratado.to_sql(
#                         name=nome_tabela_bronze,
#                         con=conn,
#                         schema=SCHEMA_BRONZE,
#                         if_exists="replace",
#                         index=False,
#                         method="multi",
#                         chunksize=500
#                     )

#             # 3. Limpa a tabela Silver de destino de forma segura
#             conn.execute(text(f"TRUNCATE TABLE {nome_completo_silver} CASCADE"))

#             # 4. Executa a query de transformação que lê do schema bronze populado acima
#             resultado = conn.execute(text(query))
#             linhas_afetadas = resultado.rowcount if resultado.rowcount is not None and resultado.rowcount >= 0 else 0

#         log.info(
#             "  [silver] %d linha(s) inserida(s) em '%s' a partir da memória.",
#             linhas_afetadas, nome_completo_silver,
#         )

#     except Exception as exc:
#         erro_curto = str(exc).split("\n")[0]  # Mantém o terminal limpo em caso de erro
#         log.error("  [silver] Erro ao carregar '%s' via memória: %s", nome_completo_silver, erro_curto)
#         raise

"""
pipeline/carga_silver.py
--------------------------
Responsabilidade: Criar tabelas temporárias de sessão usando DataFrames 
da memória e rodar as cargas Silver de forma isolada e performática.
"""

"""
pipeline/carga_silver.py
--------------------------
Responsabilidade: Criar tabelas temporárias voláteis na RAM do PostgreSQL usando 
os DataFrames da memória e executar a carga Silver sem estourar o timeout.
"""
"""
pipeline/carga_silver.py
--------------------------
Responsabilidade: Criar tabelas temporárias voláteis na RAM do PostgreSQL usando 
os DataFrames da memória e executar a carga Silver de forma instantânea.
"""

"""
pipeline/carga_silver.py
--------------------------
Responsabilidade: Criar tabelas físicas de passagem no schema Bronze,
executar a carga Silver e dropar as origens em seguida para poupar espaço em disco.
"""

# import os
# import sys
# import pandas as pd
# from sqlalchemy import Engine, text

# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# from logger import log
# from pipeline.queries_silver import QUERIES_SILVER, SCHEMA_SILVER
# from pipeline.mapeamento_bronze import TABELA_BRONZE, SCHEMA_BRONZE


# def executar_carga_silver_em_memoria(tabela_destino: str, engine: Engine, dataframes_bronze: dict[str, pd.DataFrame]) -> None:
#     """
#     Cria tabelas físicas de passagem no schema Bronze, roda o INSERT Silver e limpa o banco.
#     """
#     query = QUERIES_SILVER.get(tabela_destino)
#     nome_completo_silver = f'"{SCHEMA_SILVER}"."{tabela_destino}"'

#     if query is None:
#         log.warning("  [silver] Nenhuma query definida para '%s' — pulando.", tabela_destino)
#         return

#     # Guardaremos o nome das tabelas físicas criadas para dropá-las no final
#     tabelas_criadas_fiscamente = []

#     try:
#         with engine.begin() as conn:
            
#             # 1. Garante que o schema bronze exista fisicamente no Supabase
#             conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA_BRONZE}"'))

#             # 2. Injeta os DataFrames como tabelas físicas REAIS (Passagem)
#             for tabela_origem, df_original in dataframes_bronze.items():
#                 nome_tabela_bronze = TABELA_BRONZE.get(tabela_origem)
                
#                 if nome_tabela_bronze:
#                     df_tratado = df_original.copy()
                    
#                     # Faxina de colunas (converte ponto para underline duplo)
#                     df_tratado.columns = [col.replace(".", "_") for col in df_tratado.columns]

#                     # Grava como tabela física normal no schema bronze
#                     df_tratado.to_sql(
#                         name=nome_tabela_bronze,
#                         con=conn,
#                         schema=SCHEMA_BRONZE,
#                         if_exists="replace",  # Substitui se houver lixo anterior
#                         index=False,
#                         chunksize=1000        # Lote estável para tabelas físicas
#                     )
                    
#                     # Guarda o caminho completo para o DROP posterior
#                     tabelas_criadas_fiscamente.append(f'"{SCHEMA_BRONZE}"."{nome_tabela_bronze}"')

#             # 3. Limpa e esvazia a tabela de destino física (Silver) no Supabase
#             conn.execute(text(f"TRUNCATE TABLE {nome_completo_silver} CASCADE"))

#             # 4. Executa a query de transformação (lê de bronze.* e insere em silver.*)
#             # Como as tabelas físicas se chamam 'bronze.votos', sua query original não precisa de replace!
#             resultado = conn.execute(text(query))
#             linhas_afetadas = resultado.rowcount if resultado.rowcount is not None and resultado.rowcount >= 0 else 0

#             log.info(
#                 "  [silver] %d linha(s) inserida(s) em '%s' com sucesso.",
#                 linhas_afetadas, nome_completo_silver,
#             )

#             # 5. FAXINA DE DISCO: Dropa as tabelas bronze imediatamente após o uso
#             log.info("🧹 Efetuando faxina de disco no Supabase...")
#             for tabela_fisica in tabelas_criadas_fiscamente:
#                 conn.execute(text(f"DROP TABLE IF EXISTS {tabela_fisica} CASCADE"))
#                 log.info("    → Tabela de passagem %s eliminada.", tabela_fisica)

#     except Exception as exc:
#         erro_curto = str(exc).split("\n")
#         log.error("  [silver] Erro ao carregar '%s' via passagem: %s", nome_completo_silver, erro_curto)
#         raise


"""
pipeline/carga_silver.py
------------------------
Carga das tabelas Silver a partir das tabelas Bronze.
"""

from sqlalchemy import text
from sqlalchemy.engine import Engine

from logger import log
from pipeline.queries_silver import QUERIES_SILVER


def carregar_tabela_silver(
    nome_tabela: str,
    query_insert: str,
    engine: Engine,
) -> None:
    """
    Trunca e recarrega uma tabela Silver.
    """
    log.info(f"Iniciando carga silver.{nome_tabela}")

    with engine.begin() as conn:
        conn.execute(text(f'TRUNCATE TABLE silver."{nome_tabela}" CASCADE'))
        conn.execute(text(query_insert))

    log.info(f"Carga concluída: silver.{nome_tabela}")


def carregar_silver(engine: Engine) -> None:
    """
    Executa a carga de todas as tabelas Silver.
    """
    for nome_tabela, query_insert in QUERIES_SILVER.items():
        carregar_tabela_silver(
            nome_tabela=nome_tabela,
            query_insert=query_insert,
            engine=engine,
        )