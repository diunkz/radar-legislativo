"""
=============================================================================
schema_manager.py — Radar Legislativo
Engenharia de Dados | Auditoria e Limpeza de Schema Supabase
=============================================================================
Fluxo:
  1. Valida conexões (supabase-py + SQLAlchemy) via Conectar_DB
  2. Mapeia tabelas existentes no projeto
  3. Inspeciona tipos de dados de cada coluna via Pandas
  4. Converte tipos de colunas conforme mapeamento
  5. Remove linhas duplicadas de cada tabela
  6. Exporta CSVs ajustados em /data/ajustadas/
=============================================================================
"""

import os
import logging
import shutil
import pandas as pd

from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

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
# Credenciais (.env)
# ---------------------------------------------------------------------------
load_dotenv()

DB_URL: str     = os.getenv("DB_URL", "")      # URL da API Supabase
DB_URI: str     = os.getenv("DB_URI", "")      # pooler :6543 — leitura
DB_KEY: str     = os.getenv("DB_KEY", "")      # chave anon/service
DB_URI_DDL: str = os.getenv("DB_URI_DDL", "")  # direta :5432 — DDL

# ---------------------------------------------------------------------------
# Pasta de saída dos CSVs ajustados
# ---------------------------------------------------------------------------
OUTPUT_DIR = Path(__file__).parent / "data" / "ajustadas"

if OUTPUT_DIR.exists():
    shutil.rmtree(OUTPUT_DIR)
    log.info("🗑️  Pasta anterior removida: %s", OUTPUT_DIR)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
log.info("📁 Pasta criada: %s", OUTPUT_DIR)

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

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

# ---------------------------------------------------------------------------
# Mapeamento de conversão de tipos  (coluna → dtype pandas)
# None = manter o tipo inferido automaticamente
        # Pandas -> PostgreSQL
        # Int64            -> BIGINT
        # string           -> TEXT
        # datetime64[ns]   -> DATE ou TIMESTAMPTZ
        # boolean          -> BOOLEAN
        # Float64          -> DOUBLE PRECISION

        # ---------------------------------------------------------------------------
# CONVERSAO_TIPOS — fonte única da verdade
    # Dtype pandas → tratamento automático inferido por aplicar_conversoes()
    #
    #   Int64          → pd.to_numeric(errors="coerce") + astype("Int64")
    #   Float64        → pd.to_numeric(errors="coerce") + astype("Float64")
    #   datetime64[ns] → pd.to_datetime(errors="coerce", utc=True)
    #   boolean        → mapeamento 0/1/True/False + astype("boolean")
    #   string         → astype("string")
    # ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
CONVERSAO_TIPOS: dict[str, dict[str, str]] =    {
    "stg_deputados_bruto":  {
        "id":                                   "Int64",           # PostgreSQL: BIGINT
        "uri":                                  "string",          # PostgreSQL: TEXT
        "nomeCivil":                            "string",          # PostgreSQL: TEXT
        "cpf":                                  "string",          # PostgreSQL: TEXT
        "sexo":                                 "string",          # PostgreSQL: CHAR(1) ou TEXT
        "urlWebsite":                           "string",          # PostgreSQL: TEXT
        "redeSocial":                           "string",          # PostgreSQL: JSONB (recomendado) ou TEXT
        "dataNascimento":                       "datetime64[ns]",  # PostgreSQL: DATE
        "dataFalecimento":                      "datetime64[ns]",  # PostgreSQL: DATE
        "ufNascimento":                         "string",          # PostgreSQL: CHAR(2) ou TEXT
        "municipioNascimento":                  "string",          # PostgreSQL: TEXT
        "escolaridade":                         "string",          # PostgreSQL: TEXT
        "ultimoStatus.id":                      "Int64",           # PostgreSQL: BIGINT
        "ultimoStatus.uri":                     "string",          # PostgreSQL: TEXT
        "ultimoStatus.nome":                    "string",          # PostgreSQL: TEXT
        "ultimoStatus.siglaPartido":            "string",          # PostgreSQL: VARCHAR(20) ou TEXT
        "ultimoStatus.uriPartido":              "string",          # PostgreSQL: TEXT
        "ultimoStatus.siglaUf":                 "string",          # PostgreSQL: CHAR(2) ou TEXT
        "ultimoStatus.idLegislatura":           "Int64",           # PostgreSQL: BIGINT
        "ultimoStatus.urlFoto":                 "string",          # PostgreSQL: TEXT
        "ultimoStatus.email":                   "string",          # PostgreSQL: TEXT
        "ultimoStatus.data":                    "datetime64[ns]",  # PostgreSQL: TIMESTAMPTZ
        "ultimoStatus.nomeEleitoral":           "string",          # PostgreSQL: TEXT
        "ultimoStatus.gabinete.nome":           "string",          # PostgreSQL: TEXT
        "ultimoStatus.gabinete.predio":         "string",          # PostgreSQL: TEXT
        "ultimoStatus.gabinete.sala":           "string",          # PostgreSQL: TEXT
        "ultimoStatus.gabinete.andar":          "Int64",           # PostgreSQL: BIGINT
        "ultimoStatus.gabinete.telefone":       "string",          # PostgreSQL: TEXT
        "ultimoStatus.gabinete.email":          "string",          # PostgreSQL: TEXT
        "ultimoStatus.situacao":                "string",          # PostgreSQL: TEXT
        "ultimoStatus.condicaoEleitoral":       "string",          # PostgreSQL: TEXT
        "ultimoStatus.descricaoStatus":         "string",          # PostgreSQL: TEXT
        "data_captura":                         "datetime64[ns]"   # PostgreSQL: TIMESTAMPTZ
    },

    "stg_despesas_bruto": {
        "ano":                 "Int64",           # PostgreSQL: INTEGER
        "mes":                 "Int64",           # PostgreSQL: SMALLINT
        "tipoDespesa":         "string",          # PostgreSQL: TEXT
        "codDocumento":        "string",          # PostgreSQL: TEXT
        "tipoDocumento":       "string",          # PostgreSQL: TEXT
        "codTipoDocumento":    "Int64",           # PostgreSQL: INTEGER
        "dataDocumento":       "datetime64[ns]",  # PostgreSQL: DATE
        "numDocumento":        "string",          # PostgreSQL: TEXT
        "valorDocumento":      "Float64",         # PostgreSQL: NUMERIC(14,2)
        "urlDocumento":        "string",          # PostgreSQL: TEXT
        "nomeFornecedor":      "string",          # PostgreSQL: TEXT
        "cnpjCpfFornecedor":   "string",          # PostgreSQL: TEXT
        "valorLiquido":        "Float64",         # PostgreSQL: NUMERIC(14,2)
        "valorGlosa":          "Float64",         # PostgreSQL: NUMERIC(14,2)
        "numRessarcimento":    "string",          # PostgreSQL: TEXT
        "codLote":             "Int64",           # PostgreSQL: BIGINT
        "parcela":             "Int64",           # PostgreSQL: SMALLINT
        "idDeputado":          "Int64",           # PostgreSQL: BIGINT
        "data_captura":        "datetime64[ns]"   # PostgreSQL: TIMESTAMPTZ
    },

    "stg_eventos_bruto": {
        "id":                  "Int64",           # PostgreSQL: BIGINT
        "uri":                 "string",          # PostgreSQL: TEXT
        "dataHoraInicio":      "datetime64[ns]",  # PostgreSQL: TIMESTAMPTZ
        "dataHoraFim":         "datetime64[ns]",  # PostgreSQL: TIMESTAMPTZ
        "situacao":            "string",          # PostgreSQL: TEXT
        "descricaoTipo":       "string",          # PostgreSQL: TEXT
        "descricao":           "string",          # PostgreSQL: TEXT
        "localExterno":        "string",          # PostgreSQL: TEXT
        "orgaos":              "string",          # PostgreSQL: JSONB (recomendado) ou TEXT
        "urlRegistro":         "string",          # PostgreSQL: TEXT
        "localCamara.nome":    "string",          # PostgreSQL: TEXT
        "localCamara.predio":  "string",          # PostgreSQL: TEXT
        "localCamara.sala":    "string",          # PostgreSQL: TEXT
        "localCamara.andar":   "Int64",           # PostgreSQL: INTEGER
        "data_captura":        "datetime64[ns]"   # PostgreSQL: TIMESTAMPTZ
    },

    "stg_frentes_bruto": {
        "id":              "Int64",           # PostgreSQL: BIGINT
        "uri":             "string",          # PostgreSQL: TEXT
        "titulo":          "string",          # PostgreSQL: TEXT
        "idLegislatura":   "Int64",           # PostgreSQL: INTEGER
        "data_captura":    "datetime64[ns]"   # PostgreSQL: TIMESTAMPTZ
    },

    "stg_legislaturas_bruto": {
        "id":              "Int64",           # PostgreSQL: INTEGER
        "uri":             "string",          # PostgreSQL: TEXT
        "dataInicio":      "datetime64[ns]",  # PostgreSQL: DATE
        "dataFim":         "datetime64[ns]",  # PostgreSQL: DATE
        "data_captura":    "datetime64[ns]"   # PostgreSQL: TIMESTAMPTZ
    },

    "stg_liderancas_bruto": {
        "titulo":                          "string",          # PostgreSQL: TEXT
        "dataInicio":                      "datetime64[ns]",  # PostgreSQL: DATE
        "dataFim":                         "datetime64[ns]",  # PostgreSQL: DATE
        "idLegislaturaContexto":           "Int64",           # PostgreSQL: INTEGER
        "parlamentar.id":                  "Int64",           # PostgreSQL: BIGINT
        "parlamentar.uri":                 "string",          # PostgreSQL: TEXT
        "parlamentar.nome":                "string",          # PostgreSQL: TEXT
        "parlamentar.siglaPartido":        "string",          # PostgreSQL: VARCHAR(20) ou TEXT
        "parlamentar.uriPartido":          "string",          # PostgreSQL: TEXT
        "parlamentar.siglaUf":             "string",          # PostgreSQL: CHAR(2) ou TEXT
        "parlamentar.idLegislatura":       "Int64",           # PostgreSQL: INTEGER
        "parlamentar.email":               "string",          # PostgreSQL: TEXT
        "parlamentar.urlFoto":             "string",          # PostgreSQL: TEXT
        "bancada.tipo":                    "string",          # PostgreSQL: TEXT
        "bancada.nome":                    "string",          # PostgreSQL: TEXT
        "bancada.uri":                     "string",          # PostgreSQL: TEXT
        "data_captura":                    "datetime64[ns]"   # PostgreSQL: TIMESTAMPTZ
    },

    "stg_orgaos_bruto": {
        "id":               "Int64",           # PostgreSQL: BIGINT
        "uri":              "string",          # PostgreSQL: TEXT
        "sigla":            "string",          # PostgreSQL: VARCHAR(50) ou TEXT
        "nome":             "string",          # PostgreSQL: TEXT
        "apelido":          "string",          # PostgreSQL: TEXT
        "codTipoOrgao":     "Int64",           # PostgreSQL: INTEGER
        "tipoOrgao":        "string",          # PostgreSQL: TEXT
        "nomePublicacao":   "string",          # PostgreSQL: TEXT
        "nomeResumido":     "string",          # PostgreSQL: TEXT
        "data_captura":     "datetime64[ns]"   # PostgreSQL: TIMESTAMPTZ
    },

    "stg_partidos_bruto": {
        "id":                               "Int64",           # PostgreSQL: INTEGER
        "sigla":                            "string",          # PostgreSQL: VARCHAR(20) ou TEXT
        "nome":                             "string",          # PostgreSQL: TEXT
        "uri":                              "string",          # PostgreSQL: TEXT
        "numeroEleitoral":                  "Int64",           # PostgreSQL: INTEGER
        "urlLogo":                          "string",          # PostgreSQL: TEXT
        "urlWebSite":                       "string",          # PostgreSQL: TEXT
        "urlFacebook":                      "string",          # PostgreSQL: TEXT
        "status.data":                      "datetime64[ns]",  # PostgreSQL: DATE
        "status.idLegislatura":             "Int64",           # PostgreSQL: INTEGER
        "status.situacao":                  "string",          # PostgreSQL: TEXT
        "status.totalPosse":                "Int64",           # PostgreSQL: INTEGER
        "status.totalMembros":              "Int64",           # PostgreSQL: INTEGER
        "status.uriMembros":                "string",          # PostgreSQL: TEXT
        "status.lider.uri":                 "string",          # PostgreSQL: TEXT
        "status.lider.nome":                "string",          # PostgreSQL: TEXT
        "status.lider.siglaPartido":        "string",          # PostgreSQL: VARCHAR(20) ou TEXT
        "status.lider.uriPartido":          "string",          # PostgreSQL: TEXT
        "status.lider.uf":                  "string",          # PostgreSQL: CHAR(2) ou TEXT
        "status.lider.idLegislatura":       "Int64",           # PostgreSQL: INTEGER
        "status.lider.urlFoto":             "string",          # PostgreSQL: TEXT
        "data_captura":                     "datetime64[ns]"   # PostgreSQL: TIMESTAMPTZ
    },

    "stg_proposicoes_autores_bruto": {
        "uri":                   "string",          # PostgreSQL: TEXT
        "nome":                  "string",          # PostgreSQL: TEXT
        "codTipo":               "Int64",           # PostgreSQL: INTEGER
        "tipo":                  "string",          # PostgreSQL: TEXT
        "ordemAssinatura":       "Int64",           # PostgreSQL: INTEGER
        "proponente":            "boolean",         # PostgreSQL: BOOLEAN
        "idProposicaoContexto":  "Int64",           # PostgreSQL: BIGINT
        "data_captura":          "datetime64[ns]"   # PostgreSQL: TIMESTAMPTZ
    },

    "stg_proposicoes_bruto": {
        "id":                                       "Int64",           # PostgreSQL: BIGINT
        "uri":                                      "string",          # PostgreSQL: TEXT
        "siglaTipo":                                "string",          # PostgreSQL: VARCHAR(20) ou TEXT
        "codTipo":                                  "Int64",           # PostgreSQL: INTEGER
        "numero":                                   "Int64",           # PostgreSQL: INTEGER
        "ano":                                      "Int64",           # PostgreSQL: SMALLINT
        "ementa":                                   "string",          # PostgreSQL: TEXT
        "dataApresentacao":                         "datetime64[ns]",  # PostgreSQL: DATE
        "uriOrgaoNumerador":                        "string",          # PostgreSQL: TEXT
        "uriAutores":                               "string",          # PostgreSQL: TEXT
        "descricaoTipo":                            "string",          # PostgreSQL: TEXT
        "ementaDetalhada":                          "string",          # PostgreSQL: TEXT
        "keywords":                                 "string",          # PostgreSQL: TEXT
        "uriPropPrincipal":                         "string",          # PostgreSQL: TEXT
        "uriPropAnterior":                          "string",          # PostgreSQL: TEXT
        "uriPropPosterior":                         "string",          # PostgreSQL: TEXT
        "urlInteiroTeor":                           "string",          # PostgreSQL: TEXT
        "urnFinal":                                 "string",          # PostgreSQL: TEXT
        "texto":                                    "string",          # PostgreSQL: TEXT
        "justificativa":                            "string",          # PostgreSQL: TEXT
        "statusProposicao.dataHora":                "datetime64[ns]",  # PostgreSQL: TIMESTAMPTZ
        "statusProposicao.sequencia":               "Int64",           # PostgreSQL: INTEGER
        "statusProposicao.siglaOrgao":              "string",          # PostgreSQL: VARCHAR(50) ou TEXT
        "statusProposicao.uriOrgao":                "string",          # PostgreSQL: TEXT
        "statusProposicao.uriUltimoRelator":        "string",          # PostgreSQL: TEXT
        "statusProposicao.regime":                  "string",          # PostgreSQL: TEXT
        "statusProposicao.descricaoTramitacao":     "string",          # PostgreSQL: TEXT
        "statusProposicao.codTipoTramitacao":       "Int64",           # PostgreSQL: INTEGER
        "statusProposicao.descricaoSituacao":       "string",          # PostgreSQL: TEXT
        "statusProposicao.codSituacao":             "Int64",           # PostgreSQL: INTEGER
        "statusProposicao.despacho":                "string",          # PostgreSQL: TEXT
        "statusProposicao.url":                     "string",          # PostgreSQL: TEXT
        "statusProposicao.ambito":                  "string",          # PostgreSQL: TEXT
        "statusProposicao.apreciacao":              "string",          # PostgreSQL: TEXT
        "data_captura":                             "datetime64[ns]"   # PostgreSQL: TIMESTAMPTZ
    },

    "stg_votacoes_bruto": {
        "id":                   "string",          # PostgreSQL: TEXT
        "uri":                  "string",          # PostgreSQL: TEXT
        "data":                 "datetime64[ns]",  # PostgreSQL: DATE
        "dataHoraRegistro":     "datetime64[ns]",  # PostgreSQL: TIMESTAMPTZ
        "siglaOrgao":           "string",          # PostgreSQL: VARCHAR(50) ou TEXT
        "uriOrgao":             "string",          # PostgreSQL: TEXT
        "uriEvento":            "string",          # PostgreSQL: TEXT
        "proposicaoObjeto":     "string",          # PostgreSQL: TEXT
        "uriProposicaoObjeto":  "string",          # PostgreSQL: TEXT
        "descricao":            "string",          # PostgreSQL: TEXT
        "aprovacao":            "boolean",         # PostgreSQL: BOOLEAN
        "data_captura":         "datetime64[ns]"   # PostgreSQL: TIMESTAMPTZ
    },

    "stg_votos_bruto": {
        "tipoVoto":                    "string",          # PostgreSQL: TEXT
        "dataRegistroVoto":            "datetime64[ns]",  # PostgreSQL: TIMESTAMPTZ
        "idVotacaoContexto":           "Int64",           # PostgreSQL: BIGINT
        "deputado_.id":                "Int64",           # PostgreSQL: BIGINT
        "deputado_.uri":               "string",          # PostgreSQL: TEXT
        "deputado_.nome":              "string",          # PostgreSQL: TEXT
        "deputado_.siglaPartido":      "string",          # PostgreSQL: VARCHAR(20) ou TEXT
        "deputado_.uriPartido":        "string",          # PostgreSQL: TEXT
        "deputado_.siglaUf":           "string",          # PostgreSQL: CHAR(2) ou TEXT
        "deputado_.idLegislatura":     "Int64",           # PostgreSQL: INTEGER
        "deputado_.urlFoto":           "string",          # PostgreSQL: TEXT
        "deputado_.email":             "string",          # PostgreSQL: TEXT
        "data_captura":                "datetime64[ns]"   # PostgreSQL: TIMESTAMPTZ
    }
}

# ===========================================================================
# 1. CONEXÕES  (mesma lógica do Conectar_DB.py)
# ===========================================================================

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


# ===========================================================================
# 2. LEITURA DAS TABELAS → DataFrame
# ===========================================================================

# def carregar_tabela(client: Client, tabela: str) -> pd.DataFrame:
#     """Lê todos os dados de uma tabela via supabase-py e retorna um DataFrame."""
#     try:
#         resposta = client.table(tabela).select("*").execute()
#         df = pd.DataFrame(resposta.data)
#         log.info("  📥 '%s': %d linhas, %d colunas", tabela, len(df), len(df.columns))
#         return df
#     except Exception as exc:
#         log.warning("  ⚠  Não foi possível carregar '%s': %s", tabela, exc)
#         return pd.DataFrame()

def carregar_tabela(engine: Engine, tabela: str) -> pd.DataFrame:
    """Lê todos os dados de uma tabela via SQLAlchemy e retorna um DataFrame."""
    try:
        query = text(f"SELECT * FROM {tabela}")
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
        log.info("  📥 '%s': %d linhas, %d colunas", tabela, len(df), len(df.columns))
        return df
    except Exception as exc:
        log.warning("  ⚠  Não foi possível carregar '%s': %s", tabela, exc)
        return pd.DataFrame()


# ===========================================================================
# 3. INSPEÇÃO DE TIPOS VIA PANDAS
# ===========================================================================

def inspecionar_tipos(df: pd.DataFrame, tabela: str) -> pd.DataFrame:
    """
    Exibe e retorna um DataFrame com o diagnóstico de tipos de cada coluna:
      - dtype atual (pandas)
      - % de nulos
      - quantidade de valores únicos
    """
    if df.empty:
        log.warning("  ⚠  '%s' sem dados — inspeção ignorada.", tabela)
        return pd.DataFrame()

    diagnostico = pd.DataFrame({
        "coluna":          df.columns,
        "dtype_pandas":    [str(df[c].dtype) for c in df.columns],
        "nulos_%":         [round(df[c].isna().mean() * 100, 2) for c in df.columns],
        "valores_unicos":  [df[c].nunique() for c in df.columns],
        "exemplo":         [df[c].dropna().iloc[0] if not df[c].dropna().empty else None
                            for c in df.columns],
    })

    log.info("  🔎 Diagnóstico de tipos — '%s':", tabela)
    for _, row in diagnostico.iterrows():
        log.info(
            "     %-25s dtype=%-15s nulos=%5.1f%%  únicos=%d",
            row["coluna"], row["dtype_pandas"], row["nulos_%"], row["valores_unicos"],
        )

    return diagnostico


# # ===========================================================================
# # 4. CONVERSÃO DE TIPOS
# # ===========================================================================

# def converter_tipos(df: pd.DataFrame, tabela: str) -> pd.DataFrame:
#     """
#     Aplica as conversões definidas em CONVERSAO_TIPOS para a tabela informada.
#     Colunas ausentes no mapeamento são mantidas com o tipo inferido.
#     """
#     mapeamento = CONVERSAO_TIPOS.get(tabela, {})
#     if not mapeamento:
#         log.info("  ℹ️  '%s': sem mapeamento de tipos definido.", tabela)
#         return df

#     df = df.copy()
#     for coluna, novo_tipo in mapeamento.items():
#         if coluna not in df.columns:
#             log.warning("  ⚠  Coluna '%s' não encontrada em '%s' — ignorada.", coluna, tabela)
#             continue
#         try:
#             if novo_tipo == "datetime64[ns]":
#                 df[coluna] = pd.to_datetime(df[coluna], errors="coerce")
#             else:
#                 df[coluna] = df[coluna].astype(novo_tipo)
#             log.info("  🔄 '%s.%s' → %s", tabela, coluna, novo_tipo)
#         except Exception as exc:
#             log.warning("  ⚠  Erro ao converter '%s.%s' para %s: %s", tabela, coluna, novo_tipo, exc)

#     return df


# ===========================================================================
# 4. CONVERSÃO DE TIPOS — funções auxiliares + aplicar_conversoes()
# ===========================================================================

def _converter_inteiro(serie: pd.Series, coluna: str) -> pd.Series:
    """Converte para Int64 nullable com tratamento de erros."""
    serie = pd.to_numeric(serie, errors="coerce")
    return serie.astype("Int64")


def _converter_float(serie: pd.Series, coluna: str) -> pd.Series:
    """Converte para Float64 nullable com tratamento de erros."""
    serie = pd.to_numeric(serie, errors="coerce")
    return serie.astype("Float64")


def _converter_datetime(serie: pd.Series, coluna: str) -> pd.Series:
    """
    Converte para datetime64[ns] com UTC.
    Remove timezone após conversão para compatibilidade com PostgreSQL DATE/TIMESTAMP.
    """
    serie = pd.to_datetime(serie, errors="coerce", utc=True)
    return serie.dt.tz_localize(None)   # remove tzinfo → datetime64[ns] puro


def _converter_boolean(serie: pd.Series, coluna: str) -> pd.Series:
    """
    Normaliza valores para boolean nullable:
    1 / 1.0 / 'true' / 'True' / True  → True
    0 / 0.0 / 'false' / 'False' / False → False
    demais → pd.NA
    """
    mapa = {
        1: True,  1.0: True,  "1": True,  "true": True,  "True": True,  True: True,
        0: False, 0.0: False, "0": False, "false": False, "False": False, False: False,
    }
    return serie.map(mapa).astype("boolean")


# Roteador de conversões: dtype → função auxiliar
_CONVERSORES: dict[str, callable] = {
    "Int64":          _converter_inteiro,
    "Float64":        _converter_float,
    "datetime64[ns]": _converter_datetime,
    "boolean":        _converter_boolean,
}


def aplicar_conversoes(df: pd.DataFrame, tabela: str) -> pd.DataFrame:
    """
    Camada genérica de conversão de tipos para qualquer tabela staging.

    Infere automaticamente o tratamento necessário pelo dtype definido em
    CONVERSAO_TIPOS — sem necessidade de lógica condicional por tabela.

    Fluxo por coluna:
      1. Verifica se a coluna existe no DataFrame (ignora silenciosamente se não)
      2. Busca o conversor adequado pelo dtype em _CONVERSORES
      3. Aplica tratamento prévio + astype() de forma segura
      4. Loga cada conversão executada

    Args:
        df:     DataFrame com os dados brutos da tabela.
        tabela: Nome da tabela (chave em CONVERSAO_TIPOS).

    Returns:
        DataFrame com os tipos convertidos conforme mapeamento.
    """
    mapeamento = CONVERSAO_TIPOS.get(tabela, {})
    if not mapeamento:
        log.info("  ℹ️  '%s': sem mapeamento definido — tipos mantidos.", tabela)
        return df

    df = df.copy()
    convertidas, ignoradas, erros = 0, 0, 0

    for coluna, dtype in mapeamento.items():

        # Coluna ausente no DataFrame → ignora
        if coluna not in df.columns:
            log.debug("  ⏭  '%s.%s' não encontrada — ignorada.", tabela, coluna)
            ignoradas += 1
            continue

        try:
            conversor = _CONVERSORES.get(dtype)

            if conversor:
                # dtype com tratamento especial (Int64, Float64, datetime, boolean)
                df[coluna] = conversor(df[coluna], coluna)
            else:
                # dtype simples (string, category, etc.) → astype direto
                df[coluna] = df[coluna].astype(dtype)

            log.info("  🔄 %-35s → %s", f"'{tabela}.{coluna}'", dtype)
            convertidas += 1

        except Exception as exc:
            log.warning("  ⚠  Erro em '%s.%s' → %s: %s", tabela, coluna, dtype, exc)
            erros += 1

    log.info(
        "  📊 '%s': %d convertidas | %d ignoradas | %d erros",
        tabela, convertidas, ignoradas, erros,
    )
    return df

# ===========================================================================
# 5. REMOÇÃO DE DUPLICATAS
# ===========================================================================

def remover_duplicatas(df: pd.DataFrame, tabela: str) -> pd.DataFrame:
    """
    Remove linhas completamente duplicadas.
    Retorna o DataFrame limpo e loga quantas linhas foram removidas.
    """
    total_antes = len(df)
    df = df.drop_duplicates()
    removidas = total_antes - len(df)

    if removidas > 0:
        log.info("  🗑️  '%s': %d duplicata(s) removida(s).", tabela, removidas)
    else:
        log.info("  ✅ '%s': nenhuma duplicata encontrada.", tabela)

    return df


# ===========================================================================
# 6 + 7. EXPORTAÇÃO CSV → data/ajustadas/
# ===========================================================================

def exportar_csv(df: pd.DataFrame, tabela: str) -> Path:
    """
    Salva o DataFrame como CSV em OUTPUT_DIR com sufixo _ajustada.
    Arquivo: data/ajustadas/<tabela>_ajustada_<timestamp>.csv
    """
    if df.empty:
        log.warning("  ⚠  '%s' sem dados — CSV não gerado.", tabela)
        return Path()

    nome_base = tabela.replace("_bruto", "")
    nome_arquivo = f"{nome_base}_ajustada_{TIMESTAMP}.csv"
    caminho = OUTPUT_DIR / nome_arquivo
    df.to_csv(caminho, index=False, encoding="utf-8")
    log.info("  💾 CSV salvo: %s", caminho)
    return caminho


# ===========================================================================
# ORQUESTRADOR
# ===========================================================================

def main() -> None:
    log.info("=" * 60)
    log.info("  Radar Legislativo | Schema Manager")
    log.info("=" * 60)
    log.info("  Pasta de saída: %s", OUTPUT_DIR.resolve())
    log.info("=" * 60)

    # --- 1. Conexões ---
    _client  = conectar_supabase()
    engine = conectar_sqlalchemy()   # opcional; usado em etapas futuras de DDL

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
        df = carregar_tabela(engine, tabela) # ← engine ou client (alterar de acordo com o main() )
        if df.empty:
            continue

        # 3. Inspeção de tipos
        inspecionar_tipos(df, tabela)

        # 4. Conversão de tipos
        #df = converter_tipos(df, tabela)
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