"""
run.py — Ponto de entrada do pipeline
Execute a partir da raiz do projeto:
    python run.py [opções]
"""
import sys
from pathlib import Path

# Garante que a raiz do projeto está no path
sys.path.insert(0, str(Path(__file__).parent))

from src.main import rodar_pipeline, parse_args

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