"""
pipeline/queries_gold.py
--------------------------
Repositório central das queries SQL que constroem a camada Gold a partir
da camada Silver (dados transformados em dimensões e fatos para análise).

Fluxo completo:
    bronze.<tabela>   (dados tratados)
        --> silver.<tabela>   (transformados, com regras de negócio)
        --> gold.dim_*        (dimensões — lookups/catalogos)
        --> gold.fato_*       (fatos — eventos/transações com FK para dims)

Ordem de execução (importante!):
  1. Dimensões (dim_deputado, dim_orgao, dim_evento, dim_proposicao, dim_votacao)
     → geram sk_* (surrogate keys) via SERIAL/BIGSERIAL
  2. Tabelas fato (ft_proposicao, ft_voto, ft_despesa)
     → usam as sk_* das dimensões em seus JOINs

O dicionário QUERIES_GOLD está estruturado na ordem correta:
  primeiro todas as dimensões, depois as tabelas fato.
"""

SCHEMA_GOLD: str = "gold"

# Ordem importa! Dimensões devem rodar antes das tabelas fato.
QUERIES_GOLD: dict[str, str] = {
    # =====================================================================
    # DIMENSÕES
    # =====================================================================

    # -----------------------------------------------------------------
    # gold.dim_deputado
    # -----------------------------------------------------------------
    "dim_deputado": """
        INSERT INTO gold.dim_deputado (
            "id_deputado",
            "nm_deputado",
            "sg_sexo",
            "dt_nascimento",
            "sg_uf",
            "ds_escolaridade",
            "sg_partido",
            "ds_lider_partido",
            "ds_situacao",
            "ds_condicao_eleitoral",
            "cd_legislatura",
            "dt_inicio_legislatura",
            "dt_fim_legislatura",
            "dh_ingestao"
        )
        SELECT
            "idDeputado"             AS "id_deputado",
            nome                     AS "nm_deputado",
            sexo                     AS "sg_sexo",
            "dataNascimento"         AS "dt_nascimento",
            "siglaUF"                AS "sg_uf",
            escolaridade             AS "ds_escolaridade",
            "siglaPartido"           AS "sg_partido",
            "LiderPartido"           AS "ds_lider_partido",
            situacao                 AS "ds_situacao",
            "condicaoEleitoral"      AS "ds_condicao_eleitoral",
            legislatura              AS "cd_legislatura",
            "dataInicioLegislatura"  AS "dt_inicio_legislatura",
            "dataFimLegislatura"     AS "dt_fim_legislatura",
            current_timestamp        AS "dh_ingestao"
        FROM silver.deputado;
    """,

    # -----------------------------------------------------------------
    # gold.dim_orgao
    # -----------------------------------------------------------------
    "dim_orgao": """
        INSERT INTO gold.dim_orgao (
            "id_orgao",
            "sg_orgao",
            "nm_orgao",
            "ds_apelido_orgao",
            "ds_tipo_orgao",
            "dh_ingestao"
        )
        SELECT
            "idOrgao"       AS "id_orgao",
            siglaorgao      AS "sg_orgao",
            nome            AS "nm_orgao",
            apelido         AS "ds_apelido_orgao",
            "tipoOrgao"     AS "ds_tipo_orgao",
            current_timestamp AS "dh_ingestao"
        FROM silver.orgao;
    """,

    # -----------------------------------------------------------------
    # gold.dim_evento
    # -----------------------------------------------------------------
    "dim_evento": """
        INSERT INTO gold.dim_evento (
            "id_evento",
            "ds_tipo_evento",
            "ds_situacao",
            "dh_ingestao"
        )
        SELECT
            "idEvento"          AS "id_evento",
            "descricaoTipo"     AS "ds_tipo_evento",
            situacao            AS "ds_situacao",
            current_timestamp   AS "dh_ingestao"
        FROM silver.evento;
    """,

    # -----------------------------------------------------------------
    # gold.dim_proposicao
    # -----------------------------------------------------------------
    "dim_proposicao": """
        INSERT INTO gold.dim_proposicao (
            "id_proposicao",
            "sg_tipo_proposicao",
            "ds_tipo_proposicao",
            "ds_situacao",
            "dh_ingestao"
        )
        SELECT
            "idProposicao"              AS "id_proposicao",
            "siglaTipoProposicao"       AS "sg_tipo_proposicao",
            "descricaoTipoProposicao"   AS "ds_tipo_proposicao",
            "statusProposicao"          AS "ds_situacao",
            current_timestamp           AS "dh_ingestao"
        FROM silver.proposicao;
    """,

    # -----------------------------------------------------------------
    # gold.dim_votacao
    # -----------------------------------------------------------------
    "dim_votacao": """
        INSERT INTO gold.dim_votacao (
            "id_votacao",
            "ds_votacao",
            "ds_resultado",
            "dh_ingestao"
        )
        SELECT
            CAST("idVotacao" AS BIGINT) AS "id_votacao",
            "descricaoVotacao"          AS "ds_votacao",
            "resultadoVotacao"          AS "ds_resultado",
            current_timestamp           AS "dh_ingestao"
        FROM silver.votacao;
    """,

    # =====================================================================
    # TABELAS FATO
    # =====================================================================

    # -----------------------------------------------------------------
    # gold.ft_proposicao
    # -----------------------------------------------------------------
    # "ft_proposicao": """
    #     INSERT INTO gold.ft_proposicao (
    #         "sk_deputado",
    #         "sk_orgao",
    #         "sk_proposicao",
    #         "sk_data_proposicao",
    #         "qtd_proposicao",
    #         "dh_ingestao"
    #     )
    #     SELECT DISTINCT
    #         dep."sk_deputado",
    #         org."sk_orgao",
    #         prp."sk_proposicao",
    #         CAST(TO_CHAR(prop."dataApresentacao", 'YYYYMMDD') AS int) AS "sk_data_proposicao",
    #         1 AS "qtd_proposicao",
    #         current_timestamp AS "dh_ingestao"
    #     FROM silver.proposicao prop
    #     INNER JOIN gold.dim_proposicao prp
    #             ON prop."idProposicao" = prp."id_proposicao"
    #     INNER JOIN gold.dim_deputado dep
    #             ON prop."idDeputado" = dep."id_deputado"
    #     INNER JOIN gold.dim_orgao org
    #             ON prop."idOrgao" = org."id_orgao";
    # """,

    # -----------------------------------------------------------------
    # gold.ft_despesa
    # -----------------------------------------------------------------
    "ft_despesa": """
        INSERT INTO gold.ft_despesa (
            "sk_deputado",
            "sk_data_despesa",
            "tp_despesa",
            "vl_bruto",
            "vl_liquido",
            "vl_glosa",
            "nr_parcela",
            "dh_ingestao"
        )
        SELECT
            dep."sk_deputado",
            CAST(TO_CHAR(dsp."dataDespesa", 'YYYYMMDD') AS int) AS "sk_data_despesa",
            dsp."tipoDespesa" AS "tp_despesa",
            dsp."valorBruto" AS "vl_bruto",
            dsp."valorLiquido" AS "vl_liquido",
            dsp."valorGlosa" AS "vl_glosa",
            dsp.parcela AS "nr_parcela",
            current_timestamp AS "dh_ingestao"
        FROM silver.despesa dsp
        INNER JOIN gold.dim_deputado dep
                ON dsp."idDeputado" = dep."id_deputado";
    """,

    # -----------------------------------------------------------------
    # gold.ft_voto
    # -----------------------------------------------------------------
    # "ft_voto": """
    #     INSERT INTO gold.ft_voto (
    #         "sk_votacao",
    #         "sk_deputado",
    #         "sk_orgao",
    #         "sk_evento",
    #         "sk_data_voto",
    #         "sk_proposicao",
    #         "tp_voto",
    #         "qtd_voto",
    #         "dh_ingestao"
    #     )
    #     SELECT
    #         COALESCE(vot."sk_votacao",-1)                       AS "sk_votacao",
    #         COALESCE(dep."sk_deputado",-1)                      AS "sk_deputado",
    #         COALESCE(org."sk_orgao",-1)                         AS "sk_orgao",
    #         COALESCE(eve."sk_evento",-1)                        AS "sk_evento",
    #         CAST(TO_CHAR(vtc."dataVoto", 'YYYYMMDD') AS int)    AS "sk_data_voto",
    #         COALESCE(prp."sk_proposicao",-1)                    AS "sk_proposicao",
    #         COALESCE(vtc."tipoVoto", 'NAO INFORMADO')           AS "tp_voto",
    #         1                                                   AS "qtd_voto",
    #         current_timestamp                                   AS "dh_ingestao"
    #     FROM silver.votacao vtc
    #     INNER JOIN gold.dim_votacao vot
    #             ON vtc."idVotacao" = vot."id_votacao"
    #     INNER JOIN gold.dim_deputado dep
    #             ON vtc."idDeputado" = dep."id_deputado"
    #     INNER JOIN gold.dim_orgao org
    #             ON vtc."idOrgao" = org."id_orgao"
    #     LEFT JOIN gold.dim_evento eve
    #             ON vtc."idEvento" = eve."id_evento"
    #     INNER JOIN gold.dim_proposicao prp
    #             ON vtc."idProposicao" = prp."id_proposicao";
    # """,

}
