import os
import time
import requests
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Carrega as credenciais do arquivo .env
load_dotenv()

SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")
if not SUPABASE_DB_URL:
    raise ValueError(
        "Por favor, configure a variável SUPABASE_DB_URL no seu arquivo .env"
    )

# Cria engine de conexão com o banco do Supabase
engine = create_engine(SUPABASE_DB_URL)

# Definição de janela de 30 dias para os dados volumosos (Proposições e Votações)
DATA_INICIO_FILTRO = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")


def extrair_dados_brutos(endpoint_nome, url_inicial, params_busca=None):
    """
    Navega pelas páginas da API utilizando o ponteiro 'next', aplica lógica de
    tentativas automáticas (retry) contra erros 504/Timeout, insere metadados
    de auditoria, sincroniza colunas novas com o banco e limpa a tabela antes da carga.
    """
    if params_busca is None:
        params_busca = {}

    params_busca["itens"] = 100
    dados_acumulados = []
    proxima_url = url_inicial
    primeira_requisicao = True

    print(f"\n==================================================")
    print(f"Iniciando extração bruta: {endpoint_nome}")
    print(f"==================================================")

    while proxima_url:
        max_tentativas = 3
        tentativa = 0
        sucesso_requisicao = False

        while tentativa < max_tentativas and not sucesso_requisicao:
            try:
                time.sleep(0.5)  # Evita Rate Limit para respeitar o servidor da Câmara

                if primeira_requisicao:
                    response = requests.get(
                        proxima_url, params=params_busca, timeout=30
                    )
                else:
                    response = requests.get(proxima_url, timeout=30)

                response.raise_for_status()
                payload = response.json()
                sucesso_requisicao = True  # Rompe o loop de tentativas se der certo

            except (
                requests.exceptions.RequestException,
                requests.exceptions.HTTPError,
            ) as err:
                tentativa += 1
                print(
                    f"[ALERTA] Instabilidade (Tentativa {tentativa}/{max_tentativas}) no endpoint {endpoint_nome}: {err}"
                )
                if tentativa < max_tentativas:
                    print(" -> Aguardando 10 segundos antes de tentar novamente...")
                    time.sleep(10)
                else:
                    print(
                        f"[ERRO CRÍTICO] Limite de tentativas atingido para a página atual."
                    )
                    proxima_url = None  # Força a parada do pipeline para salvar o que já tem em memória
                    break

        if not sucesso_requisicao:
            break

        primeira_requisicao = False
        registros_pagina = payload.get("dados", [])
        if not registros_pagina:
            break

        dados_acumulados.extend(registros_pagina)

        total_registros_api = response.headers.get("X-Total-Count", "Desconhecido")
        print(
            f" -> Capturados {len(registros_pagina)} registros. Progresso: {len(dados_acumulados)} de {total_registros_api}"
        )

        # Paginação dinâmica baseada no objeto 'links' fornecido pela API
        links_paginacao = payload.get("links", [])
        proxima_url = None
        for link in links_paginacao:
            if link.get("rel") == "next":
                proxima_url = link.get("href")
                break

    if dados_acumulados:
        print(
            f" -> Convertendo {len(dados_acumulados)} registros em estrutura tabular..."
        )
        df_staging = pd.json_normalize(dados_acumulados)

        # METADADO: Inserir coluna com data e hora exata da chegada do dado para fins de auditoria
        df_staging["data_captura"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        tabela_destino = f"stg_{endpoint_nome}_bruto"

        # --- MECANISMO AUTOMÁTICO DE EVOLUÇÃO DE ESQUEMA (SCHEMA EVOLUTION) ---
        with engine.begin() as conexao:
            # 1. Se a tabela não existir, cria ela vazia imediatamente usando a estrutura do Pandas
            df_staging.head(0).to_sql(
                tabela_destino, conexao, if_exists="append", index=False
            )

            # 2. Varre o catálogo do banco para descobrir quais colunas já existem no Supabase atualmente
            query_colunas = text(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = '{tabela_destino}';
            """)
            colunas_no_banco = [
                row[0] for row in conexao.execute(query_colunas).fetchall()
            ]

            # 3. Compara e cria colunas que porventura estejam faltando via comando ALTER TABLE
            for coluna in df_staging.columns:
                if coluna not in colunas_no_banco:
                    print(
                        f" -> [Evolução de Esquema] Detectada nova coluna: '{coluna}'. Adicionando ao Supabase..."
                    )
                    # Adiciona colunas novas como TEXT para garantir compatibilidade com qualquer dado bruto original
                    conexao.execute(
                        text(
                            f'ALTER TABLE {tabela_destino} ADD COLUMN "{coluna}" TEXT;'
                        )
                    )

            # 4. LIMPEZA: Executa o comando SQL TRUNCATE para esvaziar a tabela mantendo a estrutura intacta
            print(f" -> Limpando dados antigos da tabela '{tabela_destino}'...")
            conexao.execute(text(f"TRUNCATE TABLE {tabela_destino};"))

        # 5. INGESTÃO: Grava os dados puros via 'append' (Garante integridade de tipos, índices e chaves)
        print(
            f" -> Injetando novos dados brutos na tabela '{tabela_destino}' do Supabase..."
        )
        df_staging.to_sql(tabela_destino, engine, if_exists="append", index=False)
        print(f"[SUCESSO] Carga da tabela '{tabela_destino}' finalizada.")
    else:
        print(f"[AVISO] Nenhum dado foi retornado para o endpoint {endpoint_nome}.")


if __name__ == "__main__":
    print(
        f"--- DISPARANDO PIPELINE DE EXTRAÇÃO DA CÂMARA (DATA REF: {DATA_INICIO_FILTRO}) ---"
    )

    # 1. Extração Base de Deputados
    extrair_dados_brutos(
        endpoint_nome="deputados",
        url_inicial="https://dadosabertos.camara.leg.br/api/v2/deputados",
        params_busca={"ordem": "ASC", "ordenarPor": "nome"},
    )

    # 2. Extração Base de Partidos
    extrair_dados_brutos(
        endpoint_nome="partidos",
        url_inicial="https://dadosabertos.camara.leg.br/api/v2/partidos",
        params_busca={"ordem": "ASC", "ordenarPor": "sigla"},
    )

    # 3. Extração de Proposições
    extrair_dados_brutos(
        endpoint_nome="proposicoes",
        url_inicial="https://dadosabertos.camara.leg.br/api/v2/proposicoes",
        params_busca={
            "dataInicio": DATA_INICIO_FILTRO,
            "ordem": "ASC",
            "ordenarPor": "id",
        },
    )

    # 4. Extração de Votações
    extrair_dados_brutos(
        endpoint_nome="votacoes",
        url_inicial="https://dadosabertos.camara.leg.br/api/v2/votacoes",
        params_busca={
            "dataInicio": DATA_INICIO_FILTRO,
            "ordem": "ASC",
            "ordenarPor": "id",
        },
    )

    print("\n--- PIPELINE DE EXTRAÇÃO FINALIZADO COM SUCESSO ---")
