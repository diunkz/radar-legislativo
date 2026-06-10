"""
resumos.py — Caminho B: Resumo executivo via Groq (LLM gratuito)
──────────────────────────────────────────────────────────────────
Estratégia híbrida de modelos com fallback automático:
  - Com ementa_detalhada → llama-3.3-70b-versatile
  - Só ementa curta      → llama-3.1-8b-instant
  - 70b atinge limite    → fallback para 8b em todas as próximas
  - 8b atinge limite     → pipeline para (ambos esgotados)

Rate limit do plano free Groq (junho 2025):
  - 30 requests/minuto por modelo
  - llama-3.3-70b-versatile: 100k tokens/dia
  - llama-3.1-8b-instant:    500k tokens/dia
"""

import logging
import time

import pandas as pd
from groq import Groq

from config import GROQ_API_KEY, GROQ_MAX_RPM

logger = logging.getLogger(__name__)

# ── Modelos ───────────────────────────────────────────────────────────────────

MODELO_COMPLETO = "llama-3.3-70b-versatile"
MODELO_SIMPLES  = "llama-3.1-8b-instant"

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


def _tem_detalhada(ementa_detalhada: str | None) -> bool:
    return bool(ementa_detalhada and ementa_detalhada.strip())


def _montar_prompt(ementa: str, ementa_detalhada: str | None) -> str:
    if _tem_detalhada(ementa_detalhada):
        texto = (
            f"Ementa: {ementa.strip()}\n\n"
            f"Texto completo: {ementa_detalhada.strip()}"
        )
    else:
        texto = f"Ementa: {ementa.strip()}"
    return f"{texto}\n\nResuma em até 3 frases para um executivo:"


def _is_rate_limit(erro: Exception) -> bool:
    """Detecta se o erro é especificamente de limite de tokens (429)."""
    mensagem = str(erro).lower()
    return "429" in mensagem and "tokens" in mensagem


# ── Função principal ──────────────────────────────────────────────────────────

def gerar_resumos(df: pd.DataFrame) -> pd.DataFrame:
    """
    Recebe DataFrame com colunas [id, ementa, ementa_detalhada].
    Retorna DataFrame com colunas [proposicao_id, resumo_executivo].

    Fallback automático:
      70b esgotado → continua tudo com 8b
      8b esgotado  → interrompe e salva o que foi processado até aqui
    """
    cliente = Groq(api_key=GROQ_API_KEY)

    ids     = []
    resumos = []
    erros   = 0
    contagem_modelos = {MODELO_COMPLETO: 0, MODELO_SIMPLES: 0}

    # Flags de controle de limite por modelo
    limite_70b_atingido = False
    limite_8b_atingido  = False

    tem_detalhada = "ementa_detalhada" in df.columns
    total = len(df)

    if tem_detalhada:
        n_detalhadas = df["ementa_detalhada"].notna().sum()
        logger.info(
            f"Gerando resumos para {total} proposições — "
            f"{n_detalhadas} com texto completo ({MODELO_COMPLETO}), "
            f"{total - n_detalhadas} só ementa ({MODELO_SIMPLES})."
        )
    else:
        logger.info(f"Gerando resumos para {total} proposições via {MODELO_SIMPLES}.")

    for i, (_, row) in enumerate(df.iterrows(), start=1):

        # Se ambos os modelos atingiram o limite, interrompe
        if limite_8b_atingido:
            logger.warning(
                f"Ambos os modelos atingiram o limite diário de tokens. "
                f"Interrompendo em {i}/{total}. "
                f"O pipeline incremental continuará amanhã após o reset."
            )
            break

        proposicao_id    = row["id"]
        ementa           = row["ementa"]
        ementa_detalhada = row.get("ementa_detalhada") if tem_detalhada else None

        # Decide o modelo: se 70b esgotado, força 8b independente do contexto
        if limite_70b_atingido or not _tem_detalhada(ementa_detalhada):
            modelo = MODELO_SIMPLES
        else:
            modelo = MODELO_COMPLETO

        try:
            resposta = cliente.chat.completions.create(
                model=modelo,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": _montar_prompt(ementa, ementa_detalhada)},
                ],
                temperature=0.2,
                max_tokens=250,
            )
            resumo = resposta.choices[0].message.content.strip()
            contagem_modelos[modelo] += 1

        except Exception as e:
            if _is_rate_limit(e):
                if modelo == MODELO_COMPLETO:
                    limite_70b_atingido = True
                    logger.warning(
                        f"[{i}/{total}] Limite diário do {MODELO_COMPLETO} atingido. "
                        f"Fazendo fallback para {MODELO_SIMPLES} em todas as próximas."
                    )
                    # Tenta imediatamente com o modelo menor
                    try:
                        resposta = cliente.chat.completions.create(
                            model=MODELO_SIMPLES,
                            messages=[
                                {"role": "system", "content": SYSTEM_PROMPT},
                                {"role": "user",   "content": _montar_prompt(ementa, ementa_detalhada)},
                            ],
                            temperature=0.2,
                            max_tokens=250,
                        )
                        resumo = resposta.choices[0].message.content.strip()
                        contagem_modelos[MODELO_SIMPLES] += 1

                    except Exception as e2:
                        if _is_rate_limit(e2):
                            limite_8b_atingido = True
                            logger.warning(
                                f"[{i}/{total}] Limite diário do {MODELO_SIMPLES} também atingido. "
                                f"Pipeline será interrompido."
                            )
                        else:
                            logger.warning(f"[{i}/{total}] Erro no fallback para {MODELO_SIMPLES}: {e2}")
                        resumo = None
                        erros += 1

                elif modelo == MODELO_SIMPLES:
                    limite_8b_atingido = True
                    logger.warning(
                        f"[{i}/{total}] Limite diário do {MODELO_SIMPLES} atingido. "
                        f"Pipeline será interrompido."
                    )
                    resumo = None
                    erros += 1

            else:
                # Erro genérico (timeout, rede, etc.) — não interrompe
                logger.warning(f"[{i}/{total}] Erro na proposição {proposicao_id} ({modelo}): {e}")
                resumo = None
                erros += 1

        ids.append(proposicao_id)
        resumos.append(resumo)

        if i % 10 == 0 or i == total:
            status_70b = "ESGOTADO" if limite_70b_atingido else str(contagem_modelos[MODELO_COMPLETO])
            status_8b  = "ESGOTADO" if limite_8b_atingido  else str(contagem_modelos[MODELO_SIMPLES])
            logger.info(
                f"  {i}/{total} processadas | "
                f"70b: {status_70b} | "
                f"8b: {status_8b} | "
                f"erros: {erros}"
            )

        if i < total and not limite_8b_atingido:
            time.sleep(_SLEEP_ENTRE_CHAMADAS)

    resultado = pd.DataFrame({
        "proposicao_id":    ids,
        "resumo_executivo": resumos,
    })

    logger.info(
        f"Resumos concluídos: {len(resultado) - erros} OK | {erros} falhas | "
        f"70b: {contagem_modelos[MODELO_COMPLETO]}x | "
        f"8b: {contagem_modelos[MODELO_SIMPLES]}x"
    )
    return resultado