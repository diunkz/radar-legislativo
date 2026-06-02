"""
config.py
---------
Variáveis de ambiente, constantes globais e paths do projeto.
Centralizar aqui evita "magic strings/values" espalhados pelo código.
"""

import shutil
import os
from logger import log
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Pasta de saída dos CSVs ajustados
# ---------------------------------------------------------------------------
OUTPUT_DIR = Path(__file__).parent / "output" / "ajustadas"

if OUTPUT_DIR.exists():
    shutil.rmtree(OUTPUT_DIR)
    log.info("🗑️  Pasta anterior removida: %s", OUTPUT_DIR)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
log.info("📁 Pasta criada: %s", OUTPUT_DIR)

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

# ---------------------------------------------------------------------------
# Credenciais / URIs  — nunca hardcodar, sempre via .env
# ---------------------------------------------------------------------------
load_dotenv()

DB_URL: str     = os.getenv("DB_URL", "")      # URL da API Supabase
DB_URI: str     = os.getenv("DB_URI", "")      # pooler :6543 — leitura
DB_KEY: str     = os.getenv("DB_KEY", "")      # chave anon/service
DB_URI_DDL: str = os.getenv("DB_URI_DDL", "")  # direta :5432 — DDL

# ---------------------------------------------------------------------------
# Tabelas do projeto (adicione/remova conforme necessário)
# ---------------------------------------------------------------------------
TABELAS: list[str] = [
    "stg_deputados_bruto",
    "stg_despesas_bruto",
    "stg_eventos_bruto",
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
