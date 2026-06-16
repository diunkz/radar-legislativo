"""
pipeline/queries_silver.py
-----------------------------
Queries SQL que constroem a camada Silver a partir da camada Bronze física.
"""

SCHEMA_SILVER: str = "silver"

QUERIES_SILVER: dict[str, str] = {
    # -----------------------------------------------------------------
    # silver.deputado
    # -----------------------------------------------------------------
    "deputado": """
        INSERT INTO silver.deputado (
            "idDeputado",
            nome,
            sexo,
            "dataNascimento",
            "siglaUF",
            escolaridade,
            "siglaPartido",
            "LiderPartido",
            situacao,
            "condicaoEleitoral",
            legislatura,
            "dataInicioLegislatura",
            "dataFimLegislatura"
        )
        SELECT
            dep.id                                               AS "idDeputado",
            COALESCE(dep."ultimoStatus.nome", 'NÃO INFORMADO')   AS nome,
            COALESCE(dep.sexo, 'N/I')                            AS sexo,
            COALESCE(dep."dataNascimento", '9999-12-31')         AS "dataNascimento",
            COALESCE(dep."ultimoStatus.siglaUf", 'N/I')          AS "siglaUF",
            COALESCE(dep.escolaridade, 'NÃO INFORMADO')          AS escolaridade,
            COALESCE(dep."ultimoStatus.siglaPartido", 'N/I')     AS "siglaPartido",
            CASE
                WHEN CAST(substring(prt."status.lider.uri" FROM '[^/]+$') AS int) = dep.id
                THEN 'Sim'
                ELSE 'Não'
            END                                                   AS "LiderPartido",
            COALESCE(dep."ultimoStatus.situacao", 'NÃO INFORMADO') AS situacao,
            COALESCE(dep."ultimoStatus.condicaoEleitoral", 'NÃO INFORMADO') AS "condicaoEleitoral",
            leg.id                                                AS legislatura,
            COALESCE(leg."dataInicio", '9999-12-31')              AS "dataInicioLegislatura",
            COALESCE(leg."dataFim", '9999-12-31')                 AS "dataFimLegislatura"
        FROM bronze.deputados dep
        INNER JOIN bronze.legislaturas leg
                ON dep."ultimoStatus.idLegislatura" = leg.id
        INNER JOIN bronze.partidos prt
                ON TRIM(dep."ultimoStatus.siglaPartido") = TRIM(prt.sigla);
    """,

    # -----------------------------------------------------------------
    # silver.orgao
    # -----------------------------------------------------------------
    "orgao": """
        INSERT INTO silver.orgao (
            "idOrgao",
            siglaorgao,
            nome,
            apelido,
            "tipoOrgao"
        )
        SELECT
            id                                      AS "idOrgao",
            COALESCE(sigla, 'N/I')                  AS siglaorgao,
            COALESCE(nome, 'NÃO INFORMADO')         AS nome,
            COALESCE(apelido, 'NÃO INFORMADO')      AS apelido,
            COALESCE("tipoOrgao", 'NÃO INFORMADO')  AS "tipoOrgao"
        FROM bronze.orgaos;
    """,

    # -----------------------------------------------------------------
    # silver.evento
    # -----------------------------------------------------------------
    "evento": """
        INSERT INTO silver.evento (
            "idEvento",
            "descricaoTipo",
            situacao,
            "dataHoraInicio",
            "dataHoraFim"
        )
        SELECT
            ev.id                                         AS "idEvento",
            COALESCE(ev."descricaoTipo", 'NÃO INFORMADO') AS "descricaoTipo",
            COALESCE(ev.situacao, 'NÃO INFORMADO')        AS situacao,
            COALESCE(ev."dataHoraInicio", '9999-12-31')   AS "dataHoraInicio",
            COALESCE(ev."dataHoraFim", '9999-12-31')      AS "dataHoraFim"
        FROM bronze.eventos ev
        INNER JOIN bronze.eventos_orgaos eo
                ON ev.id = eo."idEventoContexto";
    """,

    # -----------------------------------------------------------------
    # silver.proposicao
    # -----------------------------------------------------------------
    "proposicao": """
        INSERT INTO silver.proposicao (
            "idProposicao",
            "idDeputado",
            "idOrgao",
            "siglaTipoProposicao",
            "descricaoTipoProposicao",
            ano,
            ementa,
            "statusProposicao",
            "dataApresentacao"
        )
        SELECT DISTINCT
            prop.id AS "idProposicao",
            COALESCE(CAST(substring(aut.uri FROM '[^/]+$') AS int), -1) AS "idDeputado",
            COALESCE(CAST(substring(prop."statusProposicao.uriOrgao" FROM '[^/]+$') AS int), -1) AS "idOrgao",
            COALESCE(prop."siglaTipo", 'N/I') AS "siglaTipoProposicao",
            COALESCE(prop."descricaoTipo", 'NÃO INFORMADO') AS "descricaoTipoProposicao",
            COALESCE(prop.ano, 9999) AS ano,
            COALESCE(prop.ementa, 'NÃO INFORMADO') AS ementa,
            COALESCE(prop."statusProposicao.descricaoSituacao", 'NÃO INFORMADO') AS "statusProposicao",
            COALESCE(prop."dataApresentacao", '9999-12-31') AS "dataApresentacao"
        FROM bronze.proposicoes prop
        INNER JOIN bronze.proposicoes_autores aut
                ON prop.id = aut."idProposicaoContexto";
    """,

    # -----------------------------------------------------------------
    # silver.despesa
    # -----------------------------------------------------------------
    "despesa": """
        INSERT INTO silver.despesa (
            "idDeputado",
            "codDespesa",
            "tipoDespesa",
            "dataDespesa",
            "valorBruto",
            "valorLiquido",
            "valorGlosa",
            parcela
        )
        SELECT
            "idDeputado",
            COALESCE("codDocumento", 'NÃO INFORMADO') AS "codDespesa",
            COALESCE("tipoDespesa", 'NÃO INFORMADO') AS "tipoDespesa",
            COALESCE("dataDocumento", '9999-12-31')  AS "dataDespesa",
            COALESCE("valorDocumento", 0)            AS "valorBruto",
            COALESCE("valorLiquido", 0)              AS "valorLiquido",
            COALESCE("valorGlosa", 0)                AS "valorGlosa",
            COALESCE(parcela, 0)                     AS parcela
        FROM bronze.despesas;
    """,

    # -----------------------------------------------------------------
    # silver.votacao
    # -----------------------------------------------------------------
    "votacao": """
        INSERT INTO silver.votacao (
            "idVotacao",
            "idOrgao",
            "idEvento",
            "idDeputado",
            "idProposicao",
            "tipoVoto",
            "dataVoto",
            "descricaoVotacao",
            "resultadoVotacao"
        )
        SELECT DISTINCT
            CASE
                WHEN vt."idVotacaoContexto"::text ~ '^[0-9]+$'
                THEN vt."idVotacaoContexto"::bigint
                ELSE -1
            END AS "idVotacao",

            COALESCE(
                CASE
                    WHEN substring(vc."uriOrgao"::text FROM '[^/]+$') ~ '^[0-9]+$'
                    THEN substring(vc."uriOrgao"::text FROM '[^/]+$')::bigint
                    ELSE NULL
                END,
                -1
            ) AS "idOrgao",

            COALESCE(
                CASE
                    WHEN substring(vc."uriEvento"::text FROM '[^/]+$') ~ '^[0-9]+$'
                    THEN substring(vc."uriEvento"::text FROM '[^/]+$')::bigint
                    ELSE NULL
                END,
                -1
            ) AS "idEvento",

            COALESCE(
                vt."deputado_.id"::bigint,
                -1
            ) AS "idDeputado",

            COALESCE(
                CASE
                    WHEN substring(vc."uriProposicaoObjeto"::text FROM '[^/]+$') ~ '^[0-9]+$'
                    THEN substring(vc."uriProposicaoObjeto"::text FROM '[^/]+$')::bigint
                    ELSE NULL
                END,
                -3
            ) AS "idProposicao",

            COALESCE(vt."tipoVoto", 'NÃO INFORMADO') AS "tipoVoto",

            COALESCE(
                vt."dataRegistroVoto"::date,
                DATE '9999-12-31'
            ) AS "dataVoto",

            COALESCE(vc.descricao, 'NÃO INFORMADO') AS "descricaoVotacao",

            CASE
                WHEN vc.aprovacao IS TRUE THEN 'Aprovado'
                WHEN vc.aprovacao IS FALSE THEN 'Rejeitado'
                ELSE 'NÃO INFORMADO'
            END AS "resultadoVotacao"

        FROM bronze.votos vt

            INNER JOIN bronze.votacoes vc
                    ON CASE
                        WHEN vt."idVotacaoContexto"::text ~ '^[0-9]+$'
                        THEN vt."idVotacaoContexto"::bigint
                        ELSE -1
                    END
                    =
                    CASE
                        WHEN vc.id::text ~ '^[0-9]+$'
                        THEN vc.id::bigint
                        ELSE -2
                    END;
""",
}