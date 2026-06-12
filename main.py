"""
main.py — Orquestrador da Etapa 4 (IA)
──────────────────────────────────────
Modos de operação:
  - Bulk (padrão)       → embeddings + resumos via Ollama local (qwen2.5:14b)
  - Incremental (--incremental) → embeddings + resumos via Groq (llama-3.3-70b)

Salvamento incremental por lote (padrão: 50 proposições):
  Após cada lote, os resultados são persistidos no banco. Interrupções
  não causam perda de dados — a próxima execução retoma de onde parou.

Uso:
  python main.py                        # bulk: Ollama local, todas as novas
  python main.py --incremental          # novas proposições via Groq
  python main.py --limite 50            # limita a N proposições (testes)
  python main.py --reprocessar          # reprocessa tudo do zero
  python main.py --apenas-embeddings
  python main.py --apenas-resumos
  python main.py --tamanho-lote 100     # padrão: 50
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

# ── Configuração ──────────────────────────────────────────────────────────────

TAMANHO_LOTE_PADRAO = 50


# ── Helpers ───────────────────────────────────────────────────────────────────

def _processar_lote(
    lote: pd.DataFrame,
    apenas_embeddings: bool,
    apenas_resumos: bool,
    modo_incremental: bool,
) -> pd.DataFrame:
    """
    Processa um lote pelos dois caminhos e retorna DataFrame consolidado.
    """
    df_temas   = pd.DataFrame()
    df_resumos = pd.DataFrame()

    if not apenas_resumos:
        df_temas = classificar_proposicoes(lote)

    if not apenas_embeddings:
        df_resumos = gerar_resumos(lote, modo_incremental=modo_incremental)

    df_resultado = pd.DataFrame({"proposicao_id": lote["id"].values})

    if not df_temas.empty:
        df_resultado = df_resultado.merge(df_temas, on="proposicao_id", how="left")
    else:
        df_resultado["tema_classificado"]  = None
        df_resultado["score_similaridade"] = None

    if not df_resumos.empty:
        df_resultado = df_resultado.merge(df_resumos, on="proposicao_id", how="left")
    else:
        df_resultado["resumo_executivo"] = None

    df_resultado["processado_em"] = datetime.now(tz=timezone.utc)

    return df_resultado


# ── Pipeline ──────────────────────────────────────────────────────────────────

def rodar_pipeline(
    apenas_nao_processadas: bool = True,
    limite: int | None = None,
    apenas_embeddings: bool = False,
    apenas_resumos: bool = False,
    tamanho_lote: int = TAMANHO_LOTE_PADRAO,
    modo_incremental: bool = False,
):
    inicio  = datetime.now()
    backend = "Groq (llama-3.3-70b)" if modo_incremental else "Ollama (qwen2.5:14b)"

    logger.info("═" * 60)
    logger.info("  ETAPA 4 — PIPELINE DE IA LEGISLATIVA")
    logger.info(f"  Modo: {'INCREMENTAL' if modo_incremental else 'BULK'} — {backend}")
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

    total         = len(df)
    n_lotes       = (total + tamanho_lote - 1) // tamanho_lote
    total_salvos  = 0
    total_temas   = 0
    total_resumos = 0

    logger.info(
        f"{total} proposições | {n_lotes} lote(s) de até {tamanho_lote} | "
        f"salvamento após cada lote."
    )

    # 3. Processa e salva lote a lote
    for n, inicio_lote in enumerate(range(0, total, tamanho_lote), start=1):
        lote = df.iloc[inicio_lote : inicio_lote + tamanho_lote].copy()

        logger.info("─" * 60)
        logger.info(
            f"LOTE {n}/{n_lotes} — "
            f"proposições {inicio_lote + 1} a {min(inicio_lote + tamanho_lote, total)} "
            f"de {total}"
        )
        logger.info("─" * 60)

        try:
            df_resultado = _processar_lote(
                lote, apenas_embeddings, apenas_resumos, modo_incremental
            )
            salvar_resultados(df_resultado)

            salvos  = len(df_resultado)
            temas   = df_resultado["tema_classificado"].notna().sum() if "tema_classificado"  in df_resultado else 0
            resumos = df_resultado["resumo_executivo"].notna().sum()  if "resumo_executivo"   in df_resultado else 0

            total_salvos  += salvos
            total_temas   += temas
            total_resumos += resumos

            logger.info(
                f"✓ Lote {n} salvo — "
                f"{salvos} proposições | "
                f"{temas} temas | "
                f"{resumos} resumos"
            )

        except Exception as e:
            logger.error(
                f"✗ Erro no lote {n}: {e} — "
                f"lotes anteriores já foram salvos. Verifique e reexecute."
            )
            raise

    # 4. Sumário final
    duracao = (datetime.now() - inicio).total_seconds()
    logger.info("═" * 60)
    logger.info(f"  Pipeline concluído em {duracao:.1f}s")
    logger.info(f"  Proposições salvas  : {total_salvos}/{total}")
    logger.info(f"  Temas classificados : {total_temas}")
    logger.info(f"  Resumos gerados     : {total_resumos}")
    logger.info("═" * 60)


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Etapa 4 — Pipeline de IA para proposições legislativas"
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Usa Groq (llama-3.3-70b) para novas proposições. Padrão: Ollama local.",
    )
    parser.add_argument(
        "--reprocessar",
        action="store_true",
        help="Reprocessa todas as proposições ignorando as já existentes.",
    )
    parser.add_argument(
        "--limite",
        type=int,
        default=None,
        metavar="N",
        help="Limita o processamento a N proposições (útil para testes).",
    )
    parser.add_argument(
        "--apenas-embeddings",
        action="store_true",
        help="Executa apenas o Caminho A (classificação temática).",
    )
    parser.add_argument(
        "--apenas-resumos",
        action="store_true",
        help="Executa apenas o Caminho B (resumos).",
    )
    parser.add_argument(
        "--tamanho-lote",
        type=int,
        default=TAMANHO_LOTE_PADRAO,
        metavar="N",
        help=f"Proposições por lote antes de salvar no banco (padrão: {TAMANHO_LOTE_PADRAO}).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    rodar_pipeline(
        apenas_nao_processadas=not args.reprocessar,
        limite=args.limite,
        apenas_embeddings=args.apenas_embeddings,
        apenas_resumos=args.apenas_resumos,
        tamanho_lote=args.tamanho_lote,
        modo_incremental=args.incremental,
    )