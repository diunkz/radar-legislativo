=================> SELECTS UTILIZADOS PARA POPULAR TABELAS GOLD

------ DIMENSÃO DEPUTADO ------
SELECT DISTINCT
    "idDeputado" as "id_deputado",
    nome as "nm_deputado",
    sexo as "sg_sexo",
    "dataNascimento" as "dt_nascimento",
    "siglaUF" as "sg_uf",
    escolaridade as "ds_escolaridade",
    "siglaPartido" as "sg_partido",
    "LiderPartido" as "ds_lider_partido",
    situacao as "ds_situacao",
    "condicaoEleitoral" as "ds_condicao_eleitoral",
    legislatura as "cd_legislatura",
    "dataInicioLegislatura" as "dt_inicio_legislatura",
    "dataFimLegislatura" as "dt_fim_legislatura",
    current_timestamp as "dh_ingestao"
  FROM silver.deputado;
----------------------

------- DIMENSÃO ORGÃO -------
SELECT DISTINCT
    "idOrgao" as "id_orgao",
    "siglaOrgao" as "sg_orgao",
    nome as "nm_orgao",
    apelido as "ds_apelido_orgao",
    "tipoOrgao" as "ds_tipo_orgao",
    current_timestamp as "dh_ingestao"
  FROM silver.orgao;
-------------------------------

------- DIMENSÃO EVENTO -------
SELECT DISTINCT
    "idEvento" as "id_evento",      
    "descricaoTipo" as "ds_tipo_evento",
    situacao as "ds_situacao",
    current_timestamp as "dh_ingestao"
  FROM silver.evento;
 ------------------------------

----- DIMENSÃO PROPOSIÇÃO -----
SELECT DISTINCT
    "idProposicao" as "id_proposicao",  
    "siglaTipoProposicao" as "sg_tipo_proposicao",
    "descricaoTipoProposicao" as "ds_tipo_proposicao",
    "statusProposicao" as "ds_situacao",
    UPPER("tema_classificado") as "ds_tema_classificado",      -- coluna IA
    "score_similaridade" as "nr_score_similaridade",           -- coluna IA
    UPPER("resumo_executivo") as "ds_resumo_executivo",        -- coluna IA
    current_timestamp as "dh_ingestao"
  FROM silver.proposicao prop
  LEFT JOIN silver.proposicoes_ia ia ON prop."idProposicao" = ia."proposicao_id";
-------------------------------

------ DIMENSÃO VOTAÇÃO ------
SELECT DISTINCT
    "idVotacao" as "id_votacao",
    "descricaoVotacao" as "ds_votacao",
    "resultadoVotacao" as "ds_resultado",
    current_timestamp as "dh_ingestao"
  FROM silver.votacao;
---------------------

----- FATO PROPOSIÇÃO -----
SELECT
    dep."sk_deputado",
    org."sk_orgao",
    prp."sk_proposicao",
    CAST(TO_CHAR(prop."dataApresentacao", 'YYYYMMDD') as int) as "sk_data_proposicao",
    1 as "qtd_proposicao",
    current_timestamp as "dh_ingestao"
  FROM silver.proposicao prop  
 INNER JOIN gold.dim_proposicao prp ON prop."idProposicao" = prp."id_proposicao"
 INNER JOIN gold.dim_deputado dep ON prop."idDeputado" = dep."id_deputado"
 INNER JOIN gold.dim_orgao org ON prop."idOrgao" = org."id_orgao";
----------------------------

------ FATO VOTO ------
SELECT 
    vot."sk_votacao",
    dep."sk_deputado",
    org."sk_orgao",
    eve."sk_evento",
    CAST(TO_CHAR(vtc."dataVoto", 'YYYYMMDD') as int) as "sk_data_voto",
    prp."sk_proposicao" , 
    vtc."tipoVoto" as "tp_voto",
    1 as "qtd_voto",
    current_timestamp as "dh_ingestao"
  FROM silver.votacao vtc
 INNER JOIN gold.dim_votacao vot ON vtc."idVotacao" = vot."id_votacao"
 INNER JOIN gold.dim_deputado dep ON vtc."idDeputado" = dep."id_deputado"
 INNER JOIN gold.dim_orgao org ON vtc."idOrgao" = org."id_orgao"
 INNER JOIN gold.dim_evento eve ON vtc."idEvento" = eve."id_evento"
 INNER JOIN gold.dim_proposicao prp ON vtc."idProposicao" = prp."id_proposicao";
-----------------------

------ FATO DESPESA ------
SELECT 
    dep."sk_deputado",
    CAST(TO_CHAR(dsp."dataDespesa", 'YYYYMMDD') as int) as "sk_data_despesa",
    dsp."tipoDespesa" as "tp_despesa",
    dsp."valorBruto" as "vl_bruto",
    dsp."valorLiquido" as "vl_liquido",
    dsp."valorGlosa" as "vl_glosa",
    dsp.parcela as "nr_parcela",
    current_timestamp as "dh_ingestao"
  FROM silver.despesa dsp
 INNER JOIN gold.dim_deputado dep ON dsp."idDeputado" = dep."id_deputado";
--------------------------