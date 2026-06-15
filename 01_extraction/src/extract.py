import os
import time
import json
import argparse
import logging
from datetime import datetime, timedelta
import requests
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from tqdm import tqdm


# ==============================================================================
# CONFIGURAÇÃO DE LOGS DE FORMA COMPATÍVEL COM TQDM
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


os.makedirs("logs", exist_ok=True)
arquivo_log = f"logs/extracao_{datetime.now().strftime('%Y%m%d')}.log"

logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

file_handler = logging.FileHandler(arquivo_log, encoding="utf-8")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

stream_handler = TqdmLoggingHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

load_dotenv()

# ANO_ATUAL serve para o filtro das despesas dos deputados
ANO_ATUAL = datetime.now().year


def requisicao_com_retry(url, params=None, max_tentativas=3):
    tentativa = 0
    while tentativa < max_tentativas:
        try:
            time.sleep(0.15)  # Evita Rate Limit
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as err:
            tentativa += 1
            logging.warning(
                f"Falha na chamada (Tentativa {tentativa}/{max_tentativas}) para {url}: {err}"
            )
            if tentativa < max_tentativas:
                time.sleep(5)
    logging.error(f"Limite de tentativas esgotado para a URL: {url}")
    return None


def salvar_no_supabase(df, endpoint_nome):
    if df.empty:
        logging.warning(f"DataFrame vazio para '{endpoint_nome}'. Carga abortada.")
        return

    df = df.copy()
    df["data_captura"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tabela_destino = f"stg_{endpoint_nome}_bruto"

    for col in df.columns:
        if df[col].apply(lambda x: isinstance(x, (dict, list))).any():
            logging.info(
                f" -> [Tratamento] Convertendo coluna complexa '{col}' em String JSON para compatibilidade..."
            )
            df[col] = df[col].apply(
                lambda x: (
                    json.dumps(x, ensure_ascii=False)
                    if isinstance(x, (dict, list))
                    else x
                )
            )

    url_banco = os.getenv("SUPABASE_DB_URL")
    if not url_banco:
        logging.critical("SUPABASE_DB_URL não configurada no arquivo .env!")
        return

    engine_local = create_engine(url_banco)

    try:
        with engine_local.begin() as conexao:
            df.head(0).to_sql(tabela_destino, conexao, if_exists="append", index=False)

            query_colunas = text(
                f"SELECT column_name FROM information_schema.columns WHERE table_name = '{tabela_destino}';"
            )
            colunas_no_banco = [
                row[0] for row in conexao.execute(query_colunas).fetchall()
            ]

            for coluna in df.columns:
                if coluna not in colunas_no_banco:
                    logging.info(
                        f"[Evolução de Esquema] Adicionando coluna '{coluna}' em '{tabela_destino}'..."
                    )
                    conexao.execute(
                        text(
                            f'ALTER TABLE {tabela_destino} ADD COLUMN "{coluna}" TEXT;'
                        )
                    )

            logging.info(
                f"Limpando dados antigos via TRUNCATE na tabela '{tabela_destino}'..."
            )
            conexao.execute(text(f"TRUNCATE TABLE {tabela_destino};"))

        logging.info(f"Injetando novos dados na tabela '{tabela_destino}'...")
        df.to_sql(tabela_destino, engine_local, if_exists="append", index=False)
        logging.info(
            f"[SUCESSO] Tabela '{tabela_destino}' atualizada com {len(df)} registros."
        )

    except Exception as ex:
        logging.error(
            f"Erro crítico durante a carga da tabela '{tabela_destino}': {ex}"
        )
    finally:
        engine_local.dispose()


def listar_endpoint_basico(
    url_inicial, params_busca=None, desc_barra=None, modo_teste=False
):
    dados_acumulados = []
    proxima_url = url_inicial
    primeira = True

    pbar = tqdm(desc=desc_barra, unit="pag", leave=False) if desc_barra else None

    while proxima_url:
        payload = requisicao_com_retry(
            proxima_url, params=params_busca if primeira else None
        )
        if not payload:
            break
        primeira = False

        registros = payload.get("dados", [])
        if not registros:
            break
        dados_acumulados.extend(registros)

        if pbar is not None:
            pbar.update(1)

        if modo_teste:
            logging.info(
                f" -> [Modo Teste] Interrompendo paginação do endpoint de listagem na primeira página."
            )
            break

        links = payload.get("links", [])
        proxima_url = next(
            (l.get("href") for l in links if l.get("rel") == "next"), None
        )

    if pbar is not None:
        pbar.close()
    return dados_acumulados


# ==============================================================================
# ENGINES DE PROCESSAMENTO MAPEADAS POR TABELA (Globais de Data injetadas no Main)
# ==============================================================================


def rodar_legislaturas(modo_teste, data_filtro):
    logging.info("Iniciando extração: legislaturas")
    lista_leg = listar_endpoint_basico(
        "https://dadosabertos.camara.leg.br/api/v2/legislaturas",
        {"ordem": "DESC", "ordenarPor": "id"},
        modo_teste=modo_teste,
    )
    if modo_teste:
        lista_leg = lista_leg[:20]
    salvar_no_supabase(pd.json_normalize(lista_leg), "legislaturas")


def rodar_liderancas(modo_teste, data_filtro):
    logging.info("Iniciando extração: liderancas")
    lista_leg = listar_endpoint_basico(
        "https://dadosabertos.camara.leg.br/api/v2/legislaturas",
        {"ordem": "DESC", "ordenarPor": "id"},
        modo_teste=modo_teste,
    )
    ids_legislaturas = [str(item["id"]) for item in lista_leg[:2]] if lista_leg else []

    lideres_acumulados = []
    for leg_id in ids_legislaturas:
        url_lideres = (
            f"https://dadosabertos.camara.leg.br/api/v2/legislaturas/{leg_id}/lideres"
        )
        res = listar_endpoint_basico(
            url_lideres, desc_barra=f"Líderes Leg {leg_id}", modo_teste=modo_teste
        )
        for r in res:
            r["idLegislaturaContexto"] = leg_id
        lideres_acumulados.extend(res)
        if modo_teste:
            break

    df = pd.json_normalize(lideres_acumulados)
    if modo_teste:
        df = df.head(20)
    salvar_no_supabase(df, "liderancas")


def rodar_deputados_e_despesas(modo_teste, data_filtro):
    logging.info("Iniciando extração combinada: deputados e despesas")
    deputados_resumo = listar_endpoint_basico(
        "https://dadosabertos.camara.leg.br/api/v2/deputados",
        {"ordem": "ASC", "ordenarPor": "nome"},
        modo_teste=modo_teste,
    )
    ids_deputados = [str(d["id"]) for d in deputados_resumo]

    if modo_teste:
        ids_deputados = ids_deputados[:5]
        logging.info("Modo teste ativo: Limitando sub-loop a 5 deputados detalhados.")

    deputados_detalhes = []
    despesas_acumuladas = []

    for d_id in tqdm(ids_deputados, desc="Minerando perfis e despesas", unit="dep"):
        payload_det = requisicao_com_retry(
            f"https://dadosabertos.camara.leg.br/api/v2/deputados/{d_id}"
        )
        if payload_det and "dados" in payload_det:
            deputados_detalhes.append(payload_det["dados"])

        params_desp = {"ano": ANO_ATUAL}
        if modo_teste:
            params_desp["itens"] = 10

        payload_desp = listar_endpoint_basico(
            f"https://dadosabertos.camara.leg.br/api/v2/deputados/{d_id}/despesas",
            params_desp,
            modo_teste=modo_teste,
        )
        for desp in payload_desp:
            desp["idDeputado"] = d_id
        despesas_acumuladas.extend(payload_desp)

    salvar_no_supabase(pd.json_normalize(deputados_detalhes), "deputados")
    salvar_no_supabase(pd.json_normalize(despesas_acumuladas), "despesas")


def rodar_partidos(modo_teste, data_filtro):
    logging.info("Iniciando extração: partidos")
    partidos_resumo = listar_endpoint_basico(
        "https://dadosabertos.camara.leg.br/api/v2/partidos",
        {"ordem": "ASC", "ordenarPor": "sigla"},
        modo_teste=modo_teste,
    )

    if modo_teste:
        partidos_resumo = partidos_resumo[:5]
        logging.info("Modo teste ativo: Limitando detalhamento a 5 partidos.")

    partidos_detalhes = []
    for p in tqdm(partidos_resumo, desc="Detalhando Partidos", unit="part"):
        payload_p = requisicao_com_retry(
            f"https://dadosabertos.camara.leg.br/api/v2/partidos/{p['id']}"
        )
        if payload_p and "dados" in payload_p:
            partidos_detalhes.append(payload_p["dados"])

    salvar_no_supabase(pd.json_normalize(partidos_detalhes), "partidos")


def rodar_frentes(modo_teste, data_filtro):
    logging.info("Iniciando extração: frentes")
    params = {}
    if modo_teste:
        params["itens"] = 20
    frentes_bruto = listar_endpoint_basico(
        "https://dadosabertos.camara.leg.br/api/v2/frentes",
        params,
        desc_barra="Baixando frentes",
        modo_teste=modo_teste,
    )
    salvar_no_supabase(pd.json_normalize(frentes_bruto), "frentes")


def rodar_orgaos(modo_teste, data_filtro):
    logging.info("Iniciando extração: orgaos")
    orgaos_bruto = listar_endpoint_basico(
        "https://dadosabertos.camara.leg.br/api/v2/orgaos",
        {"ordem": "ASC", "ordenarPor": "sigla"},
        desc_barra="Baixando órgãos",
        modo_teste=modo_teste,
    )
    if modo_teste:
        orgaos_bruto = orgaos_bruto[:20]
    salvar_no_supabase(pd.json_normalize(orgaos_bruto), "orgaos")


def rodar_eventos(modo_teste, data_filtro):
    logging.info(
        f"Iniciando extração: eventos e órgãos vinculados (Filtro dataInicio: {data_filtro})"
    )
    params = {"dataInicio": data_filtro, "ordem": "ASC", "ordenarPor": "dataHoraInicio"}
    if modo_teste:
        params["itens"] = 10

    eventos_bruto = listar_endpoint_basico(
        "https://dadosabertos.camara.leg.br/api/v2/eventos",
        params,
        desc_barra="Baixando eventos",
        modo_teste=modo_teste,
    )
    if modo_teste:
        eventos_bruto = eventos_bruto[:10]

    eventos_orgaos_relacionamento = []
    for ev in eventos_bruto:
        ev_id = ev.get("id")
        lista_orgaos = ev.get("orgaos", [])
        if isinstance(lista_orgaos, list):
            for org in lista_orgaos:
                org_copia = org.copy()
                org_copia["idEventoContexto"] = ev_id
                eventos_orgaos_relacionamento.extend([org_copia])

    salvar_no_supabase(pd.json_normalize(eventos_bruto), "eventos")
    salvar_no_supabase(
        pd.json_normalize(eventos_orgaos_relacionamento), "eventos_orgaos"
    )


def rodar_proposicoes(modo_teste, data_filtro):
    logging.info(
        f"Iniciando extração: proposicoes e autores (Filtro dataInicio: {data_filtro})"
    )
    params = {"dataInicio": data_filtro, "ordem": "ASC", "ordenarPor": "id"}
    if modo_teste:
        params["itens"] = 5

    props_resumo = listar_endpoint_basico(
        "https://dadosabertos.camara.leg.br/api/v2/proposicoes",
        params,
        desc_barra="Lista de proposições",
        modo_teste=modo_teste,
    )
    if modo_teste:
        props_resumo = props_resumo[:5]

    props_detalhes = []
    autores_acumulados = []
    for p in tqdm(props_resumo, desc="Detalhando Proposições", unit="prop"):
        p_id = p["id"]
        payload_prop = requisicao_com_retry(
            f"https://dadosabertos.camara.leg.br/api/v2/proposicoes/{p_id}"
        )
        if payload_prop and "dados" in payload_prop:
            props_detalhes.append(payload_prop["dados"])

        payload_aut = listar_endpoint_basico(
            f"https://dadosabertos.camara.leg.br/api/v2/proposicoes/{p_id}/autores",
            modo_teste=modo_teste,
        )
        for aut in payload_aut:
            aut["idProposicaoContexto"] = p_id
        autores_acumulados.extend(payload_aut)

    salvar_no_supabase(pd.json_normalize(props_detalhes), "proposicoes")
    salvar_no_supabase(pd.json_normalize(autores_acumulados), "proposicoes_autores")


def rodar_votacoes(modo_teste, data_filtro):
    logging.info(
        f"Iniciando extração: votacoes e votos (Filtro dataInicio: {data_filtro})"
    )
    params = {"dataInicio": data_filtro, "ordem": "ASC", "ordenarPor": "id"}
    if modo_teste:
        params["itens"] = 5

    votacoes_resumo = listar_endpoint_basico(
        "https://dadosabertos.camara.leg.br/api/v2/votacoes",
        params,
        desc_barra="Lista de votações",
        modo_teste=modo_teste,
    )
    if modo_teste:
        votacoes_resumo = votacoes_resumo[:5]

    votos_acumulados = []
    for v in tqdm(votacoes_resumo, desc="Minerando Votos Nominais", unit="vot"):
        v_id = v["id"]
        payload_votos = listar_endpoint_basico(
            f"https://dadosabertos.camara.leg.br/api/v2/votacoes/{v_id}/votos",
            modo_teste=modo_teste,
        )
        for voto in payload_votos:
            voto["idVotacaoContexto"] = v_id
        votos_acumulados.extend(payload_votos)

    salvar_no_supabase(pd.json_normalize(votacoes_resumo), "votacoes")
    salvar_no_supabase(pd.json_normalize(votos_acumulados), "votos")


# ==============================================================================
# ORQUESTRADOR PRINCIPAL COM PARSER DE ARGUMENTOS AVANÇADO
# ==============================================================================

MAPA_MIGRACOES = {
    "legislaturas": rodar_legislaturas,
    "liderancas": rodar_liderancas,
    "deputados": rodar_deputados_e_despesas,
    "despesas": rodar_deputados_e_despesas,
    "partidos": rodar_partidos,
    "frentes": rodar_frentes,
    "orgaos": rodar_orgaos,
    "eventos": rodar_eventos,
    "eventos_orgaos": rodar_eventos,
    "proposicoes": rodar_proposicoes,
    "votacoes": rodar_votacoes,
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Pipeline Avançado de Extração da API da Câmara"
    )
    parser.add_argument(
        "--teste",
        action="store_true",
        help="Se ativo, roda apenas um lote rápido de requisições restritas.",
    )
    parser.add_argument(
        "--tabela",
        type=str,
        choices=list(MAPA_MIGRACOES.keys()),
        help="Escolha uma tabela específica para rodar isoladamente.",
    )

    # NOVA FLAG: Substitui a anterior para simular o dia da rodada
    parser.add_argument(
        "--data_execucao",
        type=str,
        help="Simula que o script está rodando nesta data (YYYY-MM-DD), calculando 30 dias retroativos a partir dela.",
    )

    args = parser.parse_args()

    # Determina a data âncora da execução (Hoje ou o passado simulado)
    if args.data_execucao:
        try:
            # Valida o formato da data inserida pelo usuário
            data_ancora = datetime.strptime(args.data_execucao, "%Y-%m-%d")
            logging.info(
                f"⏳ VIAGEM NO TEMPO: Simulando execução como se hoje fosse {args.data_execucao}"
            )
        except ValueError:
            logging.critical(
                "❌ Erro fatal: O formato da data passada em --data_execucao deve ser rigidamente YYYY-MM-DD!"
            )
            exit(1)
    else:
        # Se não passou nada, a âncora é o dia de hoje
        data_ancora = datetime.now()
        logging.info(f"📆 Execução normal: Utilizando a data de hoje como âncora.")

    # Calcula os 30 dias retroativos baseados na âncora definida acima
    data_final_filtro = (data_ancora - timedelta(days=30)).strftime("%Y-%m-%d")

    logging.info(
        f"--- DISPARANDO ENGINE DE INGESTÃO (FILTRANDO APARTIR DE: {data_final_filtro}) ---"
    )
    if args.teste:
        logging.info(
            "⚠️ MODO TESTE ATIVADO. Executando limites estritos de requisições."
        )

    if args.tabela:
        logging.info(
            f"🎯 Alvo único selecionado: Executando apenas a tabela '{args.tabela}'"
        )
        MAPA_MIGRACOES[args.tabela](args.teste, data_final_filtro)
    else:
        logging.info(
            "🔄 Fluxo completo selecionado: Executando todas as tabelas em sequência..."
        )
        for nome_tabela, funcao_carga in MAPA_MIGRACOES.items():
            if nome_tabela in ["despesas", "eventos_orgaos"]:
                continue
            funcao_carga(args.teste, data_final_filtro)

    logging.info("--- PIPELINE FINALIZADO ---")
