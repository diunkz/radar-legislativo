"""
main.py — Orquestrador da Etapa 4 (IA)
──────────────────────────────────────
Modos de operação:
  - Bulk (padrão)       → embeddings + resumos via Ollama local (qwen2.5:14b)
  - Incremental (--incremental) → embeddings + resumos via Groq (llama-3.3-70b)

Estratégia de persistência:
  1. Processa cada lote e salva localmente em resultados/lote_NNN.parquet
  2. Após todos os lotes, envia tudo para o Supabase em uma única operação
  Isso elimina timeouts de conexão durante o processamento intensivo de IA.

Flags adicionais:
  --apenas-upload       Pula o processamento e envia os parquets locais ao banco
  --limpar-resultados   Remove os parquets locais após upload bem-sucedido

Uso:
  python main.py                        # bulk: Ollama local, todas as novas
  python main.py --incremental          # novas proposições via Groq
  python main.py --limite 50            # limita a N proposições (testes)
  python main.py --reprocessar          # reprocessa tudo do zero
  python main.py --apenas-embeddings
  python main.py --apenas-resumos
  python main.py --tamanho-lote 100     # padrão: 50
  python main.py --apenas-upload        # envia parquets existentes ao banco
  python main.py --limpar-resultados    # remove parquets após upload
"""

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .db import carregar_proposicoes, garantir_tabela_ia, salvar_resultados
from .embeddings import classificar_proposicoes
from .resumos import gerar_resumos

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
DIR_RESULTADOS      = Path("resultados")   # pasta local para os parquets


# ── Persistência local ────────────────────────────────────────────────────────

def _caminho_lote(n: int) -> Path:
    return DIR_RESULTADOS / f"lote_{n:04d}.parquet"


def _salvar_lote_local(df: pd.DataFrame, n: int):
    """Salva o lote em parquet local. Cria a pasta se não existir."""
    DIR_RESULTADOS.mkdir(exist_ok=True)
    caminho = _caminho_lote(n)

    # Embedding é lista de floats — parquet não serializa bem, converte para string
    df_salvar = df.copy()
    if "embedding" in df_salvar.columns:
        df_salvar["embedding"] = df_salvar["embedding"].apply(
            lambda v: "[" + ",".join(f"{x:.8f}" for x in v) + "]" if v is not None else None
        )

    df_salvar.to_parquet(caminho, index=False)
    logger.info(f"  Lote {n} salvo localmente → {caminho}")


def _listar_lotes_locais() -> list[Path]:
    """Retorna todos os parquets em ordem numérica."""
    if not DIR_RESULTADOS.exists():
        return []
    return sorted(DIR_RESULTADOS.glob("lote_*.parquet"))


def _lotes_ja_processados() -> set[int]:
    """Retorna os números dos lotes que já têm parquet salvo."""
    return {
        int(p.stem.split("_")[1])
        for p in _listar_lotes_locais()
    }


# ── Upload ────────────────────────────────────────────────────────────────────

def fazer_upload(limpar: bool = False):
    """
    Lê todos os parquets locais e faz upsert no Supabase.
    Se `limpar=True`, remove os arquivos após upload bem-sucedido.
    """
    arquivos = _listar_lotes_locais()
    if not arquivos:
        logger.info("Nenhum parquet local encontrado para upload.")
        return

    logger.info(f"Iniciando upload de {len(arquivos)} lote(s) para o Supabase...")
    garantir_tabela_ia()

    total_enviados = 0
    for arquivo in arquivos:
        df = pd.read_parquet(arquivo)

        # Reconverte embedding de string para lista de floats
        if "embedding" in df.columns:
            df["embedding"] = df["embedding"].apply(
                lambda v: [float(x) for x in v.strip("[]").split(",")] if v is not None else None
            )

        salvar_resultados(df)
        total_enviados += len(df)
        logger.info(f"  ✓ {arquivo.name} — {len(df)} registros enviados")

        if limpar:
            arquivo.unlink()
            logger.info(f"  🗑 {arquivo.name} removido")

    logger.info(f"Upload concluído — {total_enviados} registros no total.")

    if limpar and DIR_RESULTADOS.exists():
        try:
            DIR_RESULTADOS.rmdir()   # remove a pasta se estiver vazia
        except OSError:
            pass


# ── Helpers ───────────────────────────────────────────────────────────────────

def _processar_lote(
    lote: pd.DataFrame,
    apenas_embeddings: bool,
    apenas_resumos: bool,
    modo_incremental: bool,
) -> pd.DataFrame:
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
    apenas_upload: bool = False,
    limpar_resultados: bool = False,
):
    inicio  = datetime.now()
    backend = "Groq (llama-3.3-70b)" if modo_incremental else "Ollama (qwen2.5:14b)"

    logger.info("═" * 60)
    logger.info("  ETAPA 4 — PIPELINE DE IA LEGISLATIVA")
    logger.info(f"  Modo: {'INCREMENTAL' if modo_incremental else 'BULK'} — {backend}")
    logger.info("═" * 60)

    # ── Modo apenas-upload: pula processamento e vai direto ao banco ──────────
    if apenas_upload:
        fazer_upload(limpar=limpar_resultados)
        return

    # ── Fase 1: Processamento local ───────────────────────────────────────────
    df = carregar_proposicoes(apenas_nao_processadas=apenas_nao_processadas)

    if df.empty:
        logger.info("Nenhuma proposição nova para processar.")
    else:
        if limite:
            df = df.head(limite)
            logger.info(f"Modo limitado: processando apenas {len(df)} proposições.")

        total   = len(df)
        n_lotes = (total + tamanho_lote - 1) // tamanho_lote
        ja_feitos = _lotes_ja_processados()

        logger.info(
            f"{total} proposições | {n_lotes} lote(s) de até {tamanho_lote} | "
            f"salvamento local em {DIR_RESULTADOS}/"
        )
        if ja_feitos:
            logger.info(f"Lotes já processados localmente (serão pulados): {sorted(ja_feitos)}")

        total_processados = 0

        for n, inicio_lote in enumerate(range(0, total, tamanho_lote), start=1):
            # Pula lotes que já têm parquet salvo (retomada após interrupção)
            if n in ja_feitos:
                logger.info(f"LOTE {n}/{n_lotes} — já processado, pulando.")
                continue

            lote = df.iloc[inicio_lote : inicio_lote + tamanho_lote].copy()

            logger.info("─" * 60)
            logger.info(
                f"LOTE {n}/{n_lotes} — "
                f"proposições {inicio_lote + 1} a {min(inicio_lote + tamanho_lote, total)} "
                f"de {total}"
            )
            logger.info("─" * 60)

            df_resultado = _processar_lote(
                lote, apenas_embeddings, apenas_resumos, modo_incremental
            )
            _salvar_lote_local(df_resultado, n)
            total_processados += len(df_resultado)

        logger.info(f"Fase 1 concluída — {total_processados} proposições processadas localmente.")

    # ── Fase 2: Upload para o Supabase ────────────────────────────────────────
    logger.info("─" * 60)
    logger.info("Fase 2 — Upload para o Supabase")
    logger.info("─" * 60)
    fazer_upload(limpar=limpar_resultados)

    duracao = (datetime.now() - inicio).total_seconds()
    logger.info("═" * 60)
    logger.info(f"  Pipeline concluído em {duracao:.1f}s")
    logger.info("═" * 60)


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Etapa 4 — Pipeline de IA para proposições legislativas"
    )
    parser.add_argument("--incremental",       action="store_true", help="Usa Groq para novas proposições.")
    parser.add_argument("--reprocessar",       action="store_true", help="Reprocessa todas as proposições.")
    parser.add_argument("--apenas-embeddings", action="store_true", help="Executa apenas o Caminho A.")
    parser.add_argument("--apenas-resumos",    action="store_true", help="Executa apenas o Caminho B.")
    parser.add_argument("--apenas-upload",     action="store_true", help="Envia parquets locais ao banco sem reprocessar.")
    parser.add_argument("--limpar-resultados", action="store_true", help="Remove parquets locais após upload.")
    parser.add_argument("--limite",            type=int, default=None, metavar="N", help="Limita a N proposições.")
    parser.add_argument("--tamanho-lote",      type=int, default=TAMANHO_LOTE_PADRAO, metavar="N",
                        help=f"Proposições por lote (padrão: {TAMANHO_LOTE_PADRAO}).")
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
        apenas_upload=args.apenas_upload,
        limpar_resultados=args.limpar_resultados,
    )