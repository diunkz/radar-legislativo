"""
embeddings.py — Caminho A: Classificação temática via BAAI/bge-m3
─────────────────────────────────────────────────────────────────
Fluxo:
  1. Carrega o modelo bge-m3 localmente (FlagEmbedding ou sentence-transformers)
  2. Gera embeddings para os temas definidos em config.py
  3. Para cada lote de ementas, gera embeddings e calcula similaridade de cosseno
  4. Retorna o tema com maior score para cada proposição
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd
import torch
from FlagEmbedding import BGEM3FlagModel

from config import BATCH_SIZE, EMBEDDING_MODEL, TEMAS

logger = logging.getLogger(__name__)


# ── Carregamento do modelo ────────────────────────────────────────────────────

_model: Optional[BGEM3FlagModel] = None

def _get_model() -> BGEM3FlagModel:
    """Carrega o modelo uma única vez (singleton)."""
    global _model
    if _model is None:
        logger.info(f"Carregando modelo {EMBEDDING_MODEL}...")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Device: {device}")
        _model = BGEM3FlagModel(
            EMBEDDING_MODEL,
            use_fp16=(device == "cuda"),   # fp16 só vale a pena com GPU
            device=device,
        )
        logger.info("Modelo carregado.")
    return _model


# ── Helpers ───────────────────────────────────────────────────────────────────

def _embeddings_densos(textos: list[str]) -> np.ndarray:
    """
    Gera embeddings densos para uma lista de textos.
    Retorna array shape (N, 1024).
    """
    model = _get_model()
    output = model.encode(
        textos,
        batch_size=BATCH_SIZE,
        max_length=512,
        return_dense=True,
        return_sparse=False,
        return_colbert_vecs=False,
    )
    return np.array(output["dense_vecs"])


def _cosseno(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """
    Similaridade de cosseno entre:
      a: shape (N, D)  — embeddings das ementas
      b: shape (M, D)  — embeddings dos temas

    Retorna: shape (N, M)
    """
    # Normaliza cada vetor (divide pela norma L2)
    a_norm = a / (np.linalg.norm(a, axis=1, keepdims=True) + 1e-10)
    b_norm = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-10)
    return a_norm @ b_norm.T   # produto interno de vetores normalizados = cosseno


# ── Função principal ──────────────────────────────────────────────────────────

def classificar_proposicoes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Recebe DataFrame com colunas [id, ementa].
    Retorna DataFrame com colunas [proposicao_id, tema_classificado, score_similaridade].
    """
    nomes_temas   = list(TEMAS.keys())
    descricoes    = list(TEMAS.values())

    # ── Embeddings dos temas (calculado uma vez) ──────────────────────────────
    logger.info("Gerando embeddings para os temas...")
    emb_temas = _embeddings_densos(descricoes)  # shape (10, 1024)

    # ── Embeddings das ementas em lotes ───────────────────────────────────────
    logger.info(f"Gerando embeddings para {len(df)} ementas...")
    ementas = df["ementa"].tolist()
    emb_ementas = _embeddings_densos(ementas)   # shape (N, 1024)

    # ── Similaridade cosseno ──────────────────────────────────────────────────
    sim_matrix = _cosseno(emb_ementas, emb_temas)  # shape (N, 10)

    # Para cada proposição: tema com maior score
    idx_melhor   = sim_matrix.argmax(axis=1)
    score_melhor = sim_matrix.max(axis=1)

    temas_atribuidos = [nomes_temas[i] for i in idx_melhor]

    resultado = pd.DataFrame({
        "proposicao_id":    df["id"].values,
        "tema_classificado": temas_atribuidos,
        "score_similaridade": score_melhor.round(4),
    })

    # Log de distribuição para inspeção rápida
    distribuicao = resultado["tema_classificado"].value_counts()
    logger.info(f"Distribuição de temas:\n{distribuicao.to_string()}")

    return resultado
