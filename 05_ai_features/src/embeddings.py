"""
embeddings.py — Caminho A: Classificação temática via intfloat/multilingual-e5-large
──────────────────────────────────────────────────────────────────────────────────────
Modelo: intfloat/multilingual-e5-large
  - Dimensão: 1024
  - Requer prefixo "query:" para textos a classificar
  - Requer prefixo "passage:" para textos de referência (temas)

Fluxo:
  1. Carrega o modelo localmente via sentence-transformers
  2. Gera embeddings para os temas (passage:)
  3. Para cada lote de ementas, gera embeddings (query:) e calcula cosseno
  4. Retorna tema, score e vetor para cada proposição
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd
import torch
from sentence_transformers import SentenceTransformer

from .config import BATCH_SIZE, EMBEDDING_MODEL, TEMAS

logger = logging.getLogger(__name__)

# ── Modelo ────────────────────────────────────────────────────────────────────

_model: Optional[SentenceTransformer] = None

def _get_model() -> SentenceTransformer:
    """Carrega o modelo uma única vez (singleton)."""
    global _model
    if _model is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Carregando modelo {EMBEDDING_MODEL} no device: {device}...")
        _model = SentenceTransformer(EMBEDDING_MODEL, device=device)
        logger.info("Modelo carregado.")
    return _model


# ── Helpers ───────────────────────────────────────────────────────────────────

def _encode(textos: list[str]) -> np.ndarray:
    """
    Gera embeddings normalizados para uma lista de textos.
    Retorna array shape (N, 1024).
    """
    model = _get_model()
    embeddings = model.encode(
        textos,
        batch_size=BATCH_SIZE,
        normalize_embeddings=True,   # já normaliza — cosseno vira só produto interno
        show_progress_bar=False,
    )
    return np.array(embeddings)


def _cosseno(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """
    Similaridade de cosseno entre:
      a: shape (N, D) — embeddings das ementas
      b: shape (M, D) — embeddings dos temas
    Retorna: shape (N, M)
    Como os vetores já estão normalizados, cosseno = produto interno.
    """
    return a @ b.T


# ── Função principal ──────────────────────────────────────────────────────────

def classificar_proposicoes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Recebe DataFrame com colunas [id, ementa].
    Retorna DataFrame com colunas:
      - proposicao_id
      - tema_classificado
      - score_similaridade
      - embedding (lista de 1024 floats — para salvar no pgvector)
    """
    nomes_temas  = list(TEMAS.keys())
    descricoes   = list(TEMAS.values())

    # multilingual-e5-large exige prefixo "passage:" para textos de referência
    logger.info("Gerando embeddings para os temas...")
    emb_temas = _encode([f"passage: {d}" for d in descricoes])  # shape (10, 1024)

    # e prefixo "query:" para os textos a classificar
    logger.info(f"Gerando embeddings para {len(df)} ementas...")
    ementas     = df["ementa"].tolist()
    emb_ementas = _encode([f"query: {e}" for e in ementas])     # shape (N, 1024)

    # Similaridade de cosseno
    sim_matrix   = _cosseno(emb_ementas, emb_temas)             # shape (N, 10)
    idx_melhor   = sim_matrix.argmax(axis=1)
    score_melhor = sim_matrix.max(axis=1)

    temas_atribuidos = [nomes_temas[i] for i in idx_melhor]

    resultado = pd.DataFrame({
        "proposicao_id":     df["id"].values,
        "tema_classificado": temas_atribuidos,
        "score_similaridade": score_melhor.round(4),
        "embedding":         emb_ementas.tolist(),  # lista de 1024 floats por linha
    })

    distribuicao = resultado["tema_classificado"].value_counts()
    logger.info(f"Distribuição de temas:\n{distribuicao.to_string()}")

    return resultado
