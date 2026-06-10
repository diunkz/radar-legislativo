import os
from dotenv import load_dotenv

load_dotenv()

# ── PostgreSQL / Supabase ──────────────────────────────────────────────────────
DB_URL = os.getenv("DATABASE_URL")
# Formato esperado no .env:
# DATABASE_URL=postgresql://user:password@host:5432/postgres

# ── Groq ──────────────────────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL   = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")  # rápido e gratuito

# ── Embeddings ────────────────────────────────────────────────────────────────
EMBEDDING_MODEL = "BAAI/bge-m3"

# ── Temas legislativos ────────────────────────────────────────────────────────
# Cada tema é descrito com uma frase mais rica para melhorar a similaridade
TEMAS = {
    "Saúde":               "saúde pública, sistema único de saúde, medicamentos, hospitais, vigilância sanitária, planos de saúde",
    "Tributário":          "impostos, tributos, arrecadação fiscal, receita federal, ICMS, reforma tributária, isenção fiscal",
    "Trabalho":            "emprego, trabalhadores, CLT, sindicatos, salário mínimo, reforma trabalhista, previdência social",
    "Tecnologia":          "tecnologia da informação, inteligência artificial, regulação digital, startups, telecomunicações, internet",
    "Meio Ambiente":       "meio ambiente, sustentabilidade, desmatamento, carbono, clima, recursos naturais, saneamento básico",
    "Educação":            "educação, ensino, escolas, universidades, bolsas de estudo, MEC, alfabetização",
    "Segurança Pública":   "segurança pública, polícia, crime, violência, presídios, legislação penal, drogas",
    "Infraestrutura":      "infraestrutura, obras públicas, rodovias, ferrovias, portos, aeroportos, energia elétrica",
    "Economia":            "economia, mercado financeiro, crédito, bancos, investimentos, câmbio, política econômica",
    "Direitos Sociais":    "direitos humanos, assistência social, igualdade, minorias, habitação, programas sociais",
}

# ── Processamento ─────────────────────────────────────────────────────────────
BATCH_SIZE     = 32    # proposições por lote no embedding (ajuste conforme RAM)
GROQ_MAX_RPM   = 30    # requisições por minuto no plano gratuito da Groq
