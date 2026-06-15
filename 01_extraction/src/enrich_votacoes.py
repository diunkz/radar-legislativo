import os
import time
import json
import logging
from datetime import datetime
import requests
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from tqdm import tqdm

# ==============================================================================
# CONFIGURAÇÃO DE LOGS COMPATÍVEL COM O SEU SCRIPT
# ==============================================================================
class TqdmLoggingHandler(logging.Handler):
    def __init__(self, level=logging.NOTSET):
        super().__init__(level)

    def emit(self, record):
        try:
            msg = self.format(record)
            tqdm.write(msg)
            self.flush()
        except Exception:
            self.handleError(record)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

# Reaproveita a pasta de logs que você já criou
os.makedirs("logs", exist_ok=True)
arquivo_log = f"logs/enriquecimento_{datetime.now().strftime('%Y%m%d')}.log"

file_handler = logging.FileHandler(arquivo_log, encoding="utf-8")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

stream_handler = TqdmLoggingHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

load_dotenv()


def preparar_coluna_auditoria(engine, tabela_destino):
    """Cria a coluna de backup no banco caso ela não exista e faz o backup inicial"""
    query_colunas = text(
        f"SELECT column_name FROM information_schema.columns WHERE table_name = '{tabela_destino}';"
    )
    
    with engine.begin() as conexao:
        colunas_no_banco = [row[0] for row in conexao.execute(query_colunas).fetchall()]
        
        # Se a coluna de backup não existir, nós a criamos de forma automática
        if "proposicaoObjeto_original" not in colunas_no_banco:
            logging.info(f"[Evolução de Esquema] Adicionando coluna de auditoria 'proposicaoObjeto_original' em '{tabela_destino}'...")
            conexao.execute(text(f'ALTER TABLE {tabela_destino} ADD COLUMN "proposicaoObjeto_original" TEXT;'))
            
            # Copia o estado atual dos dados para a coluna de backup (guardando quem nasceu nulo)
            logging.info(" -> Salvando o estado original dos dados para fins de histórico...")
            conexao.execute(text(f'UPDATE {tabela_destino} SET "proposicaoObjeto_original" = "proposicaoObjeto";'))


def extrair_detalhe_api(id_votacao):
    """Bate no endpoint individual da Câmara para buscar o projeto escondido"""
    url = f"https://dadosabertos.camara.leg.br/api/v2/votacoes/{id_votacao}"
    headers = {"Accept": "application/json"}
    
    try:
        # 1.0 segundo para ir bem na manha durante a madrugada
        time.sleep(1.0) 
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            dados = response.json().get("dados", {})
            
            # Tenta a Estratégia A: Proposições Afetadas
            prof_afetadas = dados.get("proposicoesAfetadas", [])
            if prof_afetadas and len(prof_afetadas) > 0:
                p = prof_afetadas[0]
                return f"{p.get('siglaTipo')} {p.get('numero')}/{p.get('ano')}"
            
            # Tenta a Estratégia B: Objetos Possíveis
            obj_possiveis = dados.get("objetosPossiveis", [])
            if obj_possiveis and len(obj_possiveis) > 0:
                p = obj_possiveis[0]
                return f"{p.get('siglaTipo')} {p.get('numero')}/{p.get('ano')}"
                
        elif response.status_code == 504:
            logging.warning(f"⚠️ Timeout (504) na API para o ID {id_votacao}. Avançando...")
    except Exception as err:
        logging.error(f"Erro na chamada individual do ID {id_votacao}: {err}")
        
    return None


def main():
    url_banco = os.getenv("SUPABASE_DB_URL")
    if not url_banco:
        logging.critical("SUPABASE_DB_URL não configurada no arquivo .env!")
        return

    engine_local = create_engine(url_banco)
    tabela = "stg_votacoes_bruto"

    try:
        # 1. Garante a integridade física da coluna de auditoria antes do loop
        preparar_coluna_auditoria(engine_local, tabela)

        # 2. Busca cirurgicamente os IDs que estão como NULL na coluna principal
        query_nulos = text(f'SELECT id FROM {tabela} WHERE "proposicaoObjeto" IS NULL;')
        with engine_local.connect() as conexao:
            ids_nulos = [row[0] for row in conexao.execute(query_nulos).fetchall()]

        total_tarefas = len(ids_nulos)
        if total_tarefas == 0:
            logging.info("✨ Sensacional! Nenhum registro nulo encontrado no banco.")
            return

        logging.info(f"🔍 Iniciando o processamento noturno de {total_tarefas} registros nulos...")

        # 3. Varre os dados atualizando um por um direto no banco
        sucessos = 0
        for id_votacao in tqdm(ids_nulos, desc="Enriquecendo Votações", unit="vot"):
            texto_descoberto = extrair_detalhe_api(id_votacao)
            
            if texto_descoberto:
                query_update = text(f"""
                    UPDATE {tabela} 
                    SET "proposicaoObjeto" = :texto
                    WHERE id = :id_alvo;
                """)
                with engine_local.begin() as conexao:
                    conexao.execute(query_update, {"texto": texto_descoberto, "id_alvo": id_votacao})
                sucessos += 1

        logging.info(f"🏁 PIPELINE NOTURNO FINALIZADO. {sucessos} linhas foram corrigidas na tabela '{tabela}'.")
        logging.info("💡 A coluna 'proposicaoObjeto_original' guardou com sucesso quem era NULL antes para sua auditoria.")

    except Exception as ex:
        logging.error(f"Erro crítico no orquestrador de enriquecimento: {ex}")
    finally:
        engine_local.dispose()


if __name__ == "__main__":
    main()