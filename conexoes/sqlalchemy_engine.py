"""
conexoes/sqlalchemy_engine.py
------------------------------
Responsabilidade única: criar e retornar o engine SQLAlchemy.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from config import DB_URI_DDL
from logger import log

def conectar_sqlalchemy() -> Engine | None:
    """Conexão via SQLAlchemy (direta :5432) — DDL. Opcional."""
    if not DB_URI_DDL:
        log.warning("⚠️  [DDL]  DB_URI_DDL ausente — DDL desabilitado.")
        return None
    try:
        engine = create_engine(
            DB_URI_DDL,
            pool_pre_ping=True,
            pool_size=2,
            max_overflow=3,
            connect_args={"connect_timeout": 10, "sslmode": "require"},
        )
        with engine.connect() as conn:
            banco, usuario = conn.execute(
                text("SELECT current_database(), current_user;")
            ).fetchone()
        log.info("✅ [DDL]  SQLAlchemy conectado → banco='%s' user='%s'", banco, usuario)
        return engine
    except Exception as exc:
        log.error("❌ [DDL]  Falha SQLAlchemy: %s", exc)
        log.warning("     Execute DDL manualmente no SQL Editor do Supabase.")
        return None