"""
main.py — Orquestrador da Etapa 4 (IA)
──────────────────────────────────────
Executa o pipeline completo:
  1. Garante que a tabela proposicoes_ia existe
  2. Carrega proposições ainda não processadas
  3. Caminho A: classifica temas via embeddings (bge-m3)
  4. Caminho B: gera resumos executivos via Groq
  5. Faz merge dos resultados e salva no banco

Uso:
  python main.py                    # processa apenas as novas (incremental)
  python main.py --reprocessar      # reprocessa todas, ignorando o que já existe
  python main.py --limite 50        # processa no máximo N proposições (útil para testes)
  python main.py --apenas-embeddings
  python main.py --apenas-resumos
"""

import argparse
import logging
import sys
from datetime import datetime, timezone

import pandas as pd

from db import carregar_proposicoes, garantir_tabela_ia, salvar_resultados
from embeddings import classificar_proposicoes
from resumos import gerar_resumos

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("etapa4.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("main")


# ── Pipeline ──────────────────────────────────────────────────────────────────

def rodar_pipeline(
    apenas_nao_processadas: bool = True,
    limite: int | None = None,
    apenas_embeddings: bool = False,
    apenas_resumos: bool = False,
):
    inicio = datetime.now()
    logger.info("═" * 60)
    logger.info("  ETAPA 4 — PIPELINE DE IA LEGISLATIVA")
    logger.info("═" * 60)

    # 1. Garante estrutura do banco
    garantir_tabela_ia()

    # 2. Carrega proposições
    df = carregar_proposicoes(apenas_nao_processadas=apenas_nao_processadas)

    if df.empty:
        logger.info("Nenhuma proposição nova para processar. Pipeline encerrado.")
        return

    if limite:
        df = df.head(limite)
        logger.info(f"Modo limitado: processando apenas {len(df)} proposições.")

    # 3. Caminho A — Embeddings / Classificação temática
    df_temas = pd.DataFrame()
    if not apenas_resumos:
        logger.info("─" * 40)
        logger.info("CAMINHO A — Classificação temática (bge-m3)")
        logger.info("─" * 40)
        df_temas = classificar_proposicoes(df)

    # 4. Caminho B — Resumos via Groq
    df_resumos = pd.DataFrame()
    if not apenas_embeddings:
        logger.info("─" * 40)
        logger.info("CAMINHO B — Resumos executivos (Groq)")
        logger.info("─" * 40)
        df_resumos = gerar_resumos(df)

    # 5. Merge dos resultados
    logger.info("─" * 40)
    logger.info("Consolidando resultados...")

    # Base: ids das proposições processadas
    df_resultado = pd.DataFrame({"proposicao_id": df["id"].values})

    if not df_temas.empty:
        df_resultado = df_resultado.merge(df_temas, on="proposicao_id", how="left")
    else:
        df_resultado["tema_classificado"]  = None
        df_resultado["score_similaridade"] = None

    if not df_resumos.empty:
        df_resultado = df_resultado.merge(df_resumos, on="proposicao_id", how="left")
    else:
        df_resultado["resumo_executivo"] = None

    # Timestamp de processamento (UTC)
    df_resultado["processado_em"] = datetime.now(tz=timezone.utc)

    # 6. Salva no banco
    salvar_resultados(df_resultado)

    # 7. Sumário final
    duracao = (datetime.now() - inicio).total_seconds()
    logger.info("═" * 60)
    logger.info(f"  Pipeline concluído em {duracao:.1f}s")
    logger.info(f"  Proposições processadas : {len(df_resultado)}")
    if not df_temas.empty:
        logger.info(f"  Temas classificados     : {df_resultado['tema_classificado'].notna().sum()}")
    if not df_resumos.empty:
        logger.info(f"  Resumos gerados         : {df_resultado['resumo_executivo'].notna().sum()}")
    logger.info("═" * 60)


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Etapa 4 — Pipeline de IA para proposições legislativas"
    )
    parser.add_argument(
        "--reprocessar",
        action="store_true",
        help="Reprocessa todas as proposições, ignorando as já existentes em proposicoes_ia",
    )
    parser.add_argument(
        "--limite",
        type=int,
        default=None,
        metavar="N",
        help="Limita o processamento a N proposições (útil para testes)",
    )
    parser.add_argument(
        "--apenas-embeddings",
        action="store_true",
        help="Executa apenas o Caminho A (classificação temática)",
    )
    parser.add_argument(
        "--apenas-resumos",
        action="store_true",
        help="Executa apenas o Caminho B (resumos via Groq)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    rodar_pipeline(
        apenas_nao_processadas=not args.reprocessar,
        limite=args.limite,
        apenas_embeddings=args.apenas_embeddings,
        apenas_resumos=args.apenas_resumos,
    )
