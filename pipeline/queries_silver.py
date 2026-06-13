# """
# pipeline/queries_silver.py
# -----------------------------
# Repositório central das queries SQL que constroem a camada Silver a partir
# da camada Bronze (dados já tratados: conversão de tipos, correção de
# acentuação e deduplicação — ver pipeline/carga_bronze.py).

# Fluxo completo:
#     stg_*_bruto (cru, intocado)
#         --> pipeline de tratamento (etapas 3-6 do main.py)
#         --> bronze.<tabela>
#         --> queries deste módulo (JOINs, CASE, COALESCE)
#         --> silver.<tabela>

# Por que SQL puro (e não pandas)?
#   - As tabelas Silver dependem de JOINs entre múltiplas tabelas Bronze
#     (ex.: deputados x legislaturas x partidos). Fazer isso em pandas exigiria
#     carregar tudo em memória e reimplementar a lógica de junção/CASE em
#     Python — desnecessário, já que os dados já estão no Postgres.
#   - COALESCE() aplica os defaults do DDL diretamente na SELECT, então não há
#     necessidade de uma etapa pandas separada para "preencher nulos".

# Para adicionar uma nova tabela Silver:
#   1. Garanta que a tabela staging correspondente está mapeada em
#      pipeline/mapeamento_bronze.py (TABELA_BRONZE).
#   2. Crie a entrada em QUERIES_SILVER com a chave = nome da tabela Silver
#      (sem schema) e o valor = INSERT INTO silver.<tabela> (...) SELECT ...
#      FROM bronze.<tabela_bronze> ...
#   3. Garanta que os nomes/ordem das colunas no INSERT batam com o DDL.
# """

# SCHEMA_SILVER: str = "silver"

# QUERIES_SILVER: dict[str, str] = {
#     # -----------------------------------------------------------------
#     # silver.deputado
#     # -----------------------------------------------------------------
#     "deputado": """
#         INSERT INTO silver.deputado (
#             "idDeputado",
#             nome,
#             sexo,
#             "dataNascimento",
#             "siglaUF",
#             escolaridade,
#             "siglaPartido",
#             "LiderPartido",
#             situacao,
#             "condicaoEleitoral",
#             legislatura,
#             "dataInicioLegislatura",
#             "dataFimLegislatura"
#         )
#         SELECT
#             dep.id                                              AS "idDeputado",
#             COALESCE(dep."ultimoStatus.nome", 'NÃO INFORMADO')  AS nome,
#             COALESCE(dep.sexo, 'N/I')                           AS sexo,
#             COALESCE(dep."dataNascimento", '9999-12-31')        AS "dataNascimento",
#             COALESCE(dep."ultimoStatus.siglaUf", 'N/I')         AS "siglaUF",
#             COALESCE(dep.escolaridade, 'NÃO INFORMADO')         AS escolaridade,
#             COALESCE(dep."ultimoStatus.siglaPartido", 'N/I')    AS "siglaPartido",
#             CASE
#                 WHEN CAST(substring(prt."status.lider.uri" FROM '[^/]+$') AS int) = dep.id
#                 THEN 'Sim'
#                 ELSE 'Não'
#             END                                                  AS "LiderPartido",
#             COALESCE(dep."ultimoStatus.situacao", 'NÃO INFORMADO')        AS situacao,
#             COALESCE(dep."ultimoStatus.condicaoEleitoral", 'NÃO INFORMADO') AS "condicaoEleitoral",
#             leg.id                                               AS legislatura,
#             COALESCE(leg."dataInicio", '9999-12-31')             AS "dataInicioLegislatura",
#             COALESCE(leg."dataFim", '9999-12-31')                AS "dataFimLegislatura"
#         FROM bronze.deputados dep
#         INNER JOIN bronze.legislaturas leg
#                 ON dep."ultimoStatus.idLegislatura" = leg.id
#         INNER JOIN bronze.partidos prt
#                 ON dep."ultimoStatus.siglaPartido" = prt.sigla;
#     """,

#     # -----------------------------------------------------------------
#     # silver.orgao
#     # -----------------------------------------------------------------
#         "orgao": """
#             INSERT INTO silver.orgao (
#                 "idOrgao",
#                 siglaorgao,       -- Mudado para minúsculo e sem aspas
#                 nome,
#                 apelido,
#                 "tipoOrgao"
#             )
#             SELECT
#                 id                                       AS "idOrgao",
#                 COALESCE(sigla, 'N/I')                   AS siglaorgao, -- Mudado para minúsculo
#                 COALESCE(nome, 'NÃO INFORMADO')          AS nome,
#                 COALESCE(apelido, 'NÃO INFORMADO')       AS apelido,
#                 COALESCE("tipoOrgao", 'NÃO INFORMADO')   AS "tipoOrgao"
#             FROM bronze.orgaos;
#         """,

#     # -----------------------------------------------------------------
#     # silver.evento
#     # -----------------------------------------------------------------
#     "evento": """
#         INSERT INTO silver.evento (
#             "idEvento",
#             "descricaoTipo",
#             situacao,
#             "dataHoraInicio",
#             "dataHoraFim"
#         )
#         SELECT
#             ev.id                                          AS "idEvento",
#             COALESCE(ev."descricaoTipo", 'NÃO INFORMADO')  AS "descricaoTipo",
#             COALESCE(ev.situacao, 'NÃO INFORMADO')         AS situacao,
#             COALESCE(ev."dataHoraInicio", '9999-12-31')    AS "dataHoraInicio",
#             COALESCE(ev."dataHoraFim", '9999-12-31')       AS "dataHoraFim"
#         FROM bronze.eventos ev
#         INNER JOIN bronze.eventos_orgaos eo
#                 ON ev.id = eo."idEventoContexto";
#     """,

#     # -----------------------------------------------------------------
#     # silver.proposicao
#     # -----------------------------------------------------------------
#     "proposicao": """
#         INSERT INTO silver.proposicao (
#             "idProposicao",
#             "idDeputado",
#             "idOrgao",
#             "siglaTipoProposicao",
#             "descricaoTipoProposicao",
#             ano,
#             ementa,
#             "statusProposicao",
#             "dataApresentacao"
#         )
#         SELECT DISTINCT
#             prop.id                                                                          AS "idProposicao",
#             COALESCE(CAST(substring(aut.uri FROM '[^/]+$') AS int), -1)                      AS "idDeputado",
#             COALESCE(CAST(substring(prop."statusProposicao.uriOrgao" FROM '[^/]+$') AS int), -1) AS "idOrgao",
#             COALESCE(prop."siglaTipo", 'N/I')                                                 AS "siglaTipoProposicao",
#             COALESCE(prop."descricaoTipo", 'NÃO INFORMADO')                                   AS "descricaoTipoProposicao",
#             COALESCE(prop.ano, 9999)                                                          AS ano,
#             COALESCE(prop.ementa, 'NÃO INFORMADO')                                            AS ementa,
#             COALESCE(prop."statusProposicao.descricaoSituacao", 'NÃO INFORMADO')              AS "statusProposicao",
#             COALESCE(prop."dataApresentacao", '9999-12-31')                                   AS "dataApresentacao"
#         FROM bronze.proposicoes prop
#         INNER JOIN bronze.proposicoes_autores aut
#                 ON prop.id = aut."idProposicaoContexto";
#     """,

#     # -----------------------------------------------------------------
#     # silver.despesa
#     # -----------------------------------------------------------------
#     "despesa": """
#         INSERT INTO silver.despesa (
#             "idDeputado",
#             "tipoDespesa",
#             "dataDespesa",
#             "valorBruto",
#             "valorLiquido",
#             "valorGlosa",
#             parcela
#         )
#         SELECT
#             "idDeputado",
#             COALESCE("tipoDespesa", 'NÃO INFORMADO')   AS "tipoDespesa",
#             COALESCE("dataDocumento", '9999-12-31')    AS "dataDespesa",
#             COALESCE("valorDocumento", 0)              AS "valorBruto",
#             COALESCE("valorLiquido", 0)                AS "valorLiquido",
#             COALESCE("valorGlosa", 0)                  AS "valorGlosa",
#             COALESCE(parcela, 0)                       AS parcela
#         FROM bronze.despesas;
#     """,

#     # -----------------------------------------------------------------
#     # silver.votacao
#     # -----------------------------------------------------------------
#     "votacao": """
#         INSERT INTO silver.votacao (
#             "cd_chave_voto",
#             "idVotacao",
#             "idOrgao",
#             "idEvento",
#             "idDeputado",
#             "idProposicao",
#             "tipoVoto",
#             "dataVoto",
#             "descricaoVotacao",
#             "resultadoVotacao"
#         )
#         -- O DISTINCT garante a deduplicação nativa com base em todas as colunas selecionadas
#         SELECT DISTINCT
#             (
#                 CAST(vt."idVotacaoContexto" AS TEXT) || '_' ||
#                 COALESCE(CAST(substring(vc."uriEvento" FROM '[^/]+$') AS TEXT), '-1') || '_' ||
#                 COALESCE(CAST(vt."deputado__id" AS TEXT), '-1')
#             )                                                                               AS "cd_chave_voto",
            
#             CAST(vt."idVotacaoContexto" AS BIGINT)                                          AS "idVotacao",
#             COALESCE(CAST(substring(vc."uriOrgao" FROM '[^/]+$') AS INT), -1)               AS "idOrgao",
#             COALESCE(CAST(substring(vc."uriEvento" FROM '[^/]+$') AS INT), -1)              AS "idEvento",
#             COALESCE(CAST(vt."deputado__id" AS BIGINT), -1)                                 AS "idDeputado",
#             COALESCE(CAST(substring(vc."uriProposicaoObjeto" FROM '[^/]+$') AS INT), -3)    AS "idProposicao",
#             COALESCE(vt."tipoVoto", 'NÃO INFORMADO')                                        AS "tipoVoto",
#             CAST(vt."dataRegistroVoto" AS DATE)                                             AS "dataVoto",
#             COALESCE(vc.descricao, 'NÃO INFORMADO')                                         AS "descricaoVotacao",
#             COALESCE(
#                 CASE WHEN vc.aprovacao IS TRUE THEN 'Aprovado' ELSE 'Rejeitado' END,
#                 'NÃO INFORMADO'
#             )                                                                               AS "resultadoVotacao"
#         FROM bronze.votos vt
#         INNER JOIN bronze.votacoes vc 
#                 ON CAST(vt."idVotacaoContexto" AS BIGINT) = vc.id;
#     """,
# }

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
            "tipoDespesa",
            "dataDespesa",
            "valorBruto",
            "valorLiquido",
            "valorGlosa",
            parcela
        )
        SELECT
            "idDeputado",
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
            "cd_chave_voto",
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
            (
                CAST(vt."idVotacaoContexto" AS TEXT) || '_' ||
                COALESCE(CAST(substring(vc."uriEvento" FROM '[^/]+$') AS TEXT), '-1') || '_' ||
                COALESCE(CAST(vt."deputado__id" AS TEXT), '-1')
            ) AS "cd_chave_voto",

            CAST(vt."idVotacaoContexto" AS BIGINT) AS "idVotacao",
            COALESCE(CAST(substring(vc."uriOrgao" FROM '[^/]+$') AS INT), -1) AS "idOrgao",
            COALESCE(CAST(substring(vc."uriEvento" FROM '[^/]+$') AS INT), -1) AS "idEvento",
            COALESCE(CAST(vt."deputado__id" AS BIGINT), -1) AS "idDeputado",
            COALESCE(CAST(substring(vc."uriProposicaoObjeto" FROM '[^/]+$') AS INT), -3) AS "idProposicao",
            COALESCE(vt."tipoVoto", 'NÃO INFORMADO') AS "tipoVoto",
            CAST(vt."dataRegistroVoto" AS DATE) AS "dataVoto",
            COALESCE(vc.descricao, 'NÃO INFORMADO') AS "descricaoVotacao",
            CASE
                WHEN vc.aprovacao IS TRUE THEN 'Aprovado'
                WHEN vc.aprovacao IS FALSE THEN 'Rejeitado'
                ELSE 'NÃO INFORMADO'
            END AS "resultadoVotacao"
        FROM bronze.votos vt
        INNER JOIN bronze.votacoes vc
                ON CAST(vt."idVotacaoContexto" AS BIGINT)
                 = CAST(vc.id AS BIGINT);
    """,
}