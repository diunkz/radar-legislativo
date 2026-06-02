# import os
# from supabase import create_client
# from dotenv import load_dotenv

# # Carrega as credenciais do arquivo .env
# load_dotenv()

# DB_URL = os.getenv("DB_URL")
# DB_KEY = os.getenv("DB_KEY")

# # Validação das variáveis de ambiente
# if not DB_URL or not DB_KEY:
#     raise ValueError(
#         "Por favor, configure as variáveis de conexão no seu arquivo .env"
#     )

# # Cria o cliente Supabase
# supabase = create_client(DB_URL, DB_KEY)
# print("✅ Configuração carregada com sucesso! Pronto para conectar.")

# # Teste real de conexão com o banco
# try:
#     supabase.table("stg_deputados_bruto").select("*").limit(1).execute()
#     print("🚀 Conexão com o Supabase estabelecida com sucesso!")
# except Exception as e:
#     print(f"❌ Falha ao conectar ao banco. Verifique as credenciais no .env. Erro: {e}")

# import os
# from sqlalchemy import create_engine, text
# from dotenv import load_dotenv

# load_dotenv()

# DB_URI = os.getenv("DB_URI")

# if not DB_URI:
#     raise EnvironmentError("Variável DB_URI não encontrada no .env")

# engine = create_engine(
#     DB_URI,
#     pool_pre_ping=True,
#     pool_size=5,
#     max_overflow=10,
#     connect_args={
#         "connect_timeout": 10,
#         "sslmode": "require",
#     }
# )

# try:
#     with engine.connect() as conn:
#         resultado = conn.execute(text("SELECT current_database(), current_user;"))
#         banco, usuario = resultado.fetchone()
#         print(f"✅ Conectado ao banco '{banco}' como '{usuario}'")
# except Exception as e:
#     print(f"❌ Falha na conexão: {e}")

"""
=============================================================================
Conectar_DB.py — Radar Legislativo
Validação das conexões com o Supabase
=============================================================================
Testa as duas estratégias de conexão definidas no .env:

  DB_URI      + DB_KEY  → supabase-py  (pooler :6543) — leitura / CRUD
  DB_URI_DDL            → SQLAlchemy   (direta :5432)  — DDL / migrations

.env esperado:
  DB_URI     = postgresql://postgres.<ref>:<senha>@aws-0-...pooler.supabase.com:6543/postgres
  DB_KEY     = sua_chave_anon_ou_service_role
  DB_URI_DDL = postgresql://postgres:<senha>@db.<ref>.supabase.co:5432/postgres
=============================================================================
"""

import os
import logging
from dotenv import load_dotenv
from supabase import create_client
from sqlalchemy import create_engine, text

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Credenciais
# ---------------------------------------------------------------------------
load_dotenv()

DB_URL: str     = os.getenv("DB_URL", "")
DB_URI: str     = os.getenv("DB_URI", "")
DB_KEY: str     = os.getenv("DB_KEY", "")
DB_URI_DDL: str = os.getenv("DB_URI_DDL", "")

# Valida variáveis obrigatórias antes de qualquer coisa
variaveis_ausentes = [
    nome for nome, val in {
        "DB_URL":     DB_URL,
        "DB_KEY":     DB_KEY,
        "DB_URI":     DB_URI,
        "DB_URI_DDL": DB_URI_DDL,
    }.items()
    if not val
]

if variaveis_ausentes:
    raise EnvironmentError(
        f"Variável(is) ausente(s) no .env: {', '.join(variaveis_ausentes)}"
    )


# ===========================================================================
# TESTE 1 — supabase-py  (pooler :6543)
# ===========================================================================
def testar_conexao_api() -> bool:
    """
    Valida a conexão via supabase-py (DB_URL + DB_KEY).
    Usada para leitura e operações CRUD no dia a dia.
    """
    log.info("-" * 50)
    log.info("[1/2] Testando supabase-py")
    try:
        client = create_client(DB_URL, DB_KEY)
        # Usa rpc para um ping leve sem depender de tabela específica
        client.rpc("version").execute()
        log.info("✅ supabase-py conectado com sucesso!")
        return True
    except Exception as exc:
        # rpc("version") pode não existir — tenta uma query direta
        try:
            client = create_client(DB_URL, DB_KEY)
            # Qualquer tabela existente serve; ajuste se necessário
            client.table("stg_deputados_bruto").select("*").limit(1).execute()
            log.info("✅ supabase-py conectado com sucesso!")
            return True
        except Exception as exc2:
            log.error("❌ supabase-py falhou: %s", exc2)
            return False


# ===========================================================================
# TESTE 2 — SQLAlchemy + psycopg2  (direta :5432)
# ===========================================================================
def testar_conexao_ddl() -> bool:
    """
    Valida a conexão via SQLAlchemy (DB_URI_DDL).
    Usada exclusivamente para DDL (ALTER TABLE, RENAME COLUMN).
    """
    log.info("-" * 50)
    log.info("[2/2] Testando SQLAlchemy DDL (direta :5432)…")
    try:
        engine = create_engine(
            DB_URI_DDL,
            pool_pre_ping=True,
            pool_size=2,
            max_overflow=3,
            connect_args={
                "connect_timeout": 10,
                "sslmode": "require",
            },
        )
        with engine.connect() as conn:
            banco, usuario, versao_pg = conn.execute(
                text("SELECT current_database(), current_user, version();")
            ).fetchone()

        log.info("✅ SQLAlchemy conectado com sucesso!")
        log.info("   Banco    : %s", banco)
        log.info("   Usuário  : %s", usuario)
        log.info("   Postgres : %s", versao_pg.split(",")[0])  # apenas versão curta
        return True
    except Exception as exc:
        log.error("❌ SQLAlchemy DDL falhou: %s", exc)
        log.warning(
            "   Dica: porta 5432 pode estar bloqueada na sua rede. "
            "Execute DDL pelo SQL Editor do Supabase Dashboard."
        )
        return False


# ===========================================================================
# MAIN
# ===========================================================================
def main() -> None:
    log.info("=" * 50)
    log.info("  Radar Legislativo | Validação de Conexões")
    log.info("=" * 50)

    api_ok = testar_conexao_api()
    ddl_ok = testar_conexao_ddl()

    log.info("-" * 50)
    log.info("  RESULTADO FINAL")
    log.info("-" * 50)
    log.info("  supabase-py  (CRUD/leitura) : %s", "✅ OK" if api_ok else "❌ FALHOU")
    log.info("  SQLAlchemy   (DDL/migração) : %s", "✅ OK" if ddl_ok else "❌ FALHOU")
    log.info("=" * 50)

    if api_ok and not ddl_ok:
        log.warning(
            "  ⚠️  DDL indisponível via código. "
            "Use o SQL Editor do Supabase para executar migrations."
        )

    if not api_ok:
        raise RuntimeError("Conexão principal (supabase-py) falhou. Verifique DB_URI e DB_KEY.")


if __name__ == "__main__":
    main()