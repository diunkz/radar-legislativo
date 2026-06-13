"""
config.py
---------
Variáveis de ambiente, constantes globais e paths do projeto.
Centralizar aqui evita "magic strings/values" espalhados pelo código.
"""

import os
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Credenciais / URIs  — nunca hardcodar, sempre via .env
# ---------------------------------------------------------------------------
load_dotenv()

DB_URL: str     = os.getenv("DB_URL", "")      # URL da API Supabase
DB_URI: str     = os.getenv("DB_URI", "")      # pooler :6543 — leitura
DB_KEY: str     = os.getenv("DB_KEY", "")      # chave anon/service
DB_URI_DDL: str = os.getenv("DB_URI_DDL", "")  # direta :5432 — DDL

# ---------------------------------------------------------------------------
# Tabelas a processar  (= todas as tabelas staging consumidas pelos JOINs
# da camada Silver, ver pipeline/queries_silver.py e pipeline/mapeamento_bronze.py)
# ---------------------------------------------------------------------------
TABELAS: list[str] = [
    "stg_deputados_bruto",
    "stg_despesas_bruto",
    "stg_eventos_bruto",
    "stg_eventos_orgaos_bruto",
    "stg_frentes_bruto",
    "stg_legislaturas_bruto",
    "stg_liderancas_bruto",
    "stg_orgaos_bruto",
    "stg_partidos_bruto",
    "stg_proposicoes_autores_bruto",
    "stg_proposicoes_bruto",
    "stg_votacoes_bruto",
    "stg_votos_bruto"
]
