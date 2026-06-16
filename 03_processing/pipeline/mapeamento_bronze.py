"""
pipeline/mapeamento_bronze.py
--------------------------------
Mapeamento entre as tabelas de staging (camada bruta original, somente
leitura/preservação) e as tabelas correspondentes na camada Bronze
(dados já tratados: conversão de tipos, correção de acentuação, dedup).

Convenção de nomes: remove o prefixo "stg_" e o sufixo "_bruto".
  stg_deputados_bruto        -> bronze.deputados
  stg_proposicoes_autores_bruto -> bronze.proposicoes_autores

Para adicionar uma nova tabela, basta incluir uma entrada aqui — tanto
pipeline/carga_bronze.py quanto pipeline/queries_silver.py dependem deste
mapeamento (direta ou indiretamente, via nome da tabela bronze).
"""

SCHEMA_BRONZE: str = "bronze"

TABELA_BRONZE: dict[str, str] = {
    "stg_deputados_bruto":           "deputados",
    "stg_legislaturas_bruto":        "legislaturas",
    "stg_partidos_bruto":            "partidos",
    "stg_frentes_bruto":             "frentes",
    "stg_liderancas_bruto":          "liderancas",
    "stg_orgaos_bruto":              "orgaos",
    "stg_eventos_bruto":             "eventos",
    "stg_eventos_orgaos_bruto":      "eventos_orgaos",
    "stg_proposicoes_bruto":         "proposicoes",
    "stg_proposicoes_autores_bruto": "proposicoes_autores",
    "stg_votos_bruto":               "votos",
    "stg_votacoes_bruto":            "votacoes",
    "stg_despesas_bruto":            "despesas"
}
