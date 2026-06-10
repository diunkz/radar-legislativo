"""
resumos.py — Caminho B: Resumo executivo via Groq (LLM gratuito)
──────────────────────────────────────────────────────────────────
Fluxo:
  1. Para cada ementa, monta um prompt estruturado
  2. Chama a API da Groq (llama-3.1-8b-instant por padrão)
  3. Respeita o rate limit do plano gratuito (~30 RPM)
  4. Retorna DataFrame com [proposicao_id, resumo_executivo]

Rate limit do plano free Groq (junho 2025):
  - 30 requests/minuto
  - 14.400 requests/dia
  Controlamos com um sleep proporcional entre chamadas.
"""

import logging
import time

import pandas as pd
from groq import Groq

from config import GROQ_API_KEY, GROQ_MAX_RPM, GROQ_MODEL

logger = logging.getLogger(__name__)

# Intervalo mínimo entre chamadas para respeitar o rate limit
_SLEEP_ENTRE_CHAMADAS = 60.0 / GROQ_MAX_RPM  # segundos

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

def _montar_prompt(ementa: str) -> str:
    return f"Ementa: {ementa.strip()}\n\nResuma em até 3 frases para um executivo:"


# ── Função principal ──────────────────────────────────────────────────────────

def gerar_resumos(df: pd.DataFrame) -> pd.DataFrame:
    """
    Recebe DataFrame com colunas [id, ementa].
    Retorna DataFrame com colunas [proposicao_id, resumo_executivo].
    """
    cliente = Groq(api_key=GROQ_API_KEY)

    ids      = []
    resumos  = []
    erros    = 0

    total = len(df)
    logger.info(f"Gerando resumos para {total} proposições via Groq ({GROQ_MODEL})...")

    for i, (_, row) in enumerate(df.iterrows(), start=1):
        proposicao_id = row["id"]
        ementa        = row["ementa"]

        try:
            resposta = cliente.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": _montar_prompt(ementa)},
                ],
                temperature=0.2,     # baixa temperatura → respostas mais consistentes
                max_tokens=200,      # 3 frases não precisam de mais
            )
            resumo = resposta.choices[0].message.content.strip()

        except Exception as e:
            logger.warning(f"[{i}/{total}] Erro na proposição {proposicao_id}: {e}")
            resumo = None
            erros += 1

        ids.append(proposicao_id)
        resumos.append(resumo)

        # Log de progresso a cada 10 proposições
        if i % 10 == 0 or i == total:
            logger.info(f"  {i}/{total} processadas | erros acumulados: {erros}")

        # Respeita o rate limit (exceto na última iteração)
        if i < total:
            time.sleep(_SLEEP_ENTRE_CHAMADAS)

    resultado = pd.DataFrame({
        "proposicao_id":    ids,
        "resumo_executivo": resumos,
    })

    logger.info(
        f"Resumos concluídos: {total - erros} OK | {erros} falhas "
        f"({erros/total*100:.1f}%)"
    )
    return resultado
