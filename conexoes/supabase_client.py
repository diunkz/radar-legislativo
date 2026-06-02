"""
conexoes/supabase_client.py
---------------------------
Responsabilidade única: criar e retornar o client Supabase.
"""

from supabase import Client, create_client

from config import DB_KEY, DB_URL, TABELAS
from logger import log
from supabase import create_client, Client



def conectar_supabase() -> Client:
    """Conexão via supabase-py (pooler :6543) — leitura / CRUD."""
    ausentes = [v for v, val in {"DB_URL": DB_URL, "DB_KEY": DB_KEY}.items() if not val]
    if ausentes:
        raise EnvironmentError(f"Variável(is) ausente(s) no .env: {', '.join(ausentes)}")
    try:
        client = create_client(DB_URL, DB_KEY)
        client.table(TABELAS[0]).select("*").limit(1).execute()
        log.info("✅ [API]  supabase-py conectado (pooler :6543)")
        return client
    except Exception as exc:
        log.error("❌ [API]  Falha supabase-py: %s", exc)
        raise
