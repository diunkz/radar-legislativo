"""
resumos.py — Caminho B: Resumo executivo com estratégia dual
──────────────────────────────────────────────────────────────
Estratégia:
  - Bulk (proposições existentes) → qwen2.5:14b via Ollama (local, GPU)
  - Incremental (proposições novas) → llama-3.3-70b-versatile via Groq (API)

Fallback da Groq (caso atinja limite diário):
  llama-3.3-70b → llama-3.1-8b-instant → mixtral-8x7b-32768 → Ollama local

O modo é detectado automaticamente pelo main.py via flag `modo_incremental`.
"""

import logging
import math
import time
from typing import Literal

import pandas as pd
import requests
from groq import Groq

from config import GROQ_API_KEY, GROQ_MAX_RPM

logger = logging.getLogger(__name__)

# ── Modelos ───────────────────────────────────────────────────────────────────

# Local (Ollama) — usado no bulk
OLLAMA_MODEL   = "qwen2.5:14b"
OLLAMA_URL     = "http://localhost:11434/api/generate"

# Groq — usado no incremental, com cadeia de fallback
GROQ_MODELOS = [
    "llama-3.3-70b-versatile",   # principal
    "llama-3.1-8b-instant",      # fallback 1
    "mixtral-8x7b-32768",        # fallback 2
]

_SLEEP_ENTRE_CHAMADAS = 60.0 / GROQ_MAX_RPM

# ── Prompt ────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """
Você é um analista legislativo sênior de uma consultoria de relações governamentais.
Sua tarefa é transformar ementas de proposições legislativas brasileiras em resumos
executivos claros, objetivos e acionáveis para líderes empresariais.

Regras:
- Escreva em português brasileiro formal, mas sem juridiquês desnecessário.
- Máximo 3 frases.
- Indique o impacto prático para empresas ou cidadãos quando possível.
- Não invente informações além do que está na ementa.
- Não use bullet points. Responda apenas com o texto do resumo.
""".strip()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _tem_detalhada(ementa_detalhada) -> bool:
    """Retorna True se há conteúdo útil — trata None e NaN do pandas."""
    if ementa_detalhada is None:
        return False
    if isinstance(ementa_detalhada, float) and math.isnan(ementa_detalhada):
        return False
    return bool(str(ementa_detalhada).strip())


def _montar_prompt(ementa: str, ementa_detalhada) -> str:
    if _tem_detalhada(ementa_detalhada):
        texto = (
            f"Ementa: {ementa.strip()}\n\n"
            f"Texto completo: {str(ementa_detalhada).strip()}"
        )
    else:
        texto = f"Ementa: {ementa.strip()}"
    return f"{texto}\n\nResuma em até 3 frases para um executivo:"


def _is_rate_limit(erro: Exception) -> bool:
    mensagem = str(erro).lower()
    return "429" in mensagem and "tokens" in mensagem


# ── Backends ──────────────────────────────────────────────────────────────────

def _resumir_ollama(prompt: str) -> str:
    """Chama o modelo local via Ollama (síncrono, sem streaming)."""
    payload = {
        "model":  OLLAMA_MODEL,
        "prompt": f"{SYSTEM_PROMPT}\n\n{prompt}",
        "stream": False,
    }
    resposta = requests.post(OLLAMA_URL, json=payload, timeout=120)
    resposta.raise_for_status()
    return resposta.json()["response"].strip()


def _resumir_groq(cliente: Groq, prompt: str, esgotados: set) -> tuple[str, str]:
    """
    Chama a API da Groq percorrendo a cadeia de fallback.
    Retorna (resumo, modelo_usado).
    Lança Exception se todos os modelos estiverem esgotados.
    """
    for modelo in GROQ_MODELOS:
        if modelo in esgotados:
            continue
        try:
            resposta = cliente.chat.completions.create(
                model=modelo,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
                temperature=0.2,
                max_tokens=250,
            )
            return resposta.choices[0].message.content.strip(), modelo

        except Exception as e:
            if _is_rate_limit(e):
                esgotados.add(modelo)
                logger.warning(
                    f"Limite diário de '{modelo}' atingido "
                    f"({len(esgotados)}/{len(GROQ_MODELOS)} modelos esgotados)."
                    + (" Tentando próximo." if len(esgotados) < len(GROQ_MODELOS) else "")
                )
            else:
                raise

    raise Exception("Todos os modelos Groq atingiram o limite diário de tokens.")


# ── Função principal ──────────────────────────────────────────────────────────

def gerar_resumos(df: pd.DataFrame, modo_incremental: bool = False) -> pd.DataFrame:
    """
    Recebe DataFrame com colunas [id, ementa, ementa_detalhada].
    Retorna DataFrame com colunas [proposicao_id, resumo_executivo].

    modo_incremental=False  →  usa Ollama local (qwen2.5:14b) — bulk
    modo_incremental=True   →  usa Groq (llama-3.3-70b) com fallback — incremental
    """
    backend = "Groq (llama-3.3-70b)" if modo_incremental else f"Ollama ({OLLAMA_MODEL})"
    tem_detalhada = "ementa_detalhada" in df.columns
    total = len(df)

    logger.info(f"Gerando resumos para {total} proposições via {backend}.")

    ids      = []
    resumos  = []
    erros    = 0
    esgotados: set[str] = set()  # só usado no modo Groq
    cliente_groq = Groq(api_key=GROQ_API_KEY) if modo_incremental else None
    contagem_modelos: dict[str, int] = {}

    for i, (_, row) in enumerate(df.iterrows(), start=1):
        proposicao_id    = row["id"]
        ementa           = row["ementa"]
        ementa_detalhada = row.get("ementa_detalhada") if tem_detalhada else None
        prompt           = _montar_prompt(ementa, ementa_detalhada)
        resumo           = None

        try:
            if modo_incremental:
                # Groq — com fallback automático
                if esgotados >= set(GROQ_MODELOS):
                    logger.warning(
                        f"Todos os modelos Groq esgotados. "
                        f"Interrompendo em {i}/{total}. "
                        f"Retoma amanhã após reset (00:00 UTC)."
                    )
                    break

                resumo, modelo_usado = _resumir_groq(cliente_groq, prompt, esgotados)
                contagem_modelos[modelo_usado] = contagem_modelos.get(modelo_usado, 0) + 1

                if i < total:
                    time.sleep(_SLEEP_ENTRE_CHAMADAS)

            else:
                # Ollama local — sem rate limit, sem sleep
                resumo = _resumir_ollama(prompt)
                contagem_modelos[OLLAMA_MODEL] = contagem_modelos.get(OLLAMA_MODEL, 0) + 1

        except Exception as e:
            logger.warning(f"[{i}/{total}] Erro na proposição {proposicao_id}: {e}")
            erros += 1

        ids.append(proposicao_id)
        resumos.append(resumo)

        if i % 10 == 0 or i == total:
            status = " | ".join(f"{m}: {c}" for m, c in contagem_modelos.items())
            logger.info(f"  {i}/{total} | {status} | erros: {erros}")

    resultado = pd.DataFrame({
        "proposicao_id":    ids,
        "resumo_executivo": resumos,
    })

    logger.info(
        f"Resumos concluídos: {len(resultado) - erros} OK | {erros} falhas"
    )
    return resultado