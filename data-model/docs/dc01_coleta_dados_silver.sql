=================> SELECTS UTILIZADOS PARA POPULAR TABELAS SILVER

------ DEPUTADO ------
SELECT 
    dep.id as "idDeputado",
    dep."ultimoStatus.nome" as nome,
    dep.sexo,
    dep."dataNascimento",
    dep."ultimoStatus.siglaUf" as "siglaUF",
    dep.escolaridade,
    dep."ultimoStatus.siglaPartido" as "siglaPartido",
    CASE WHEN 
      CAST(substring(prt."status.lider.uri" FROM '[^/]+$') as int) = dep.id 
    THEN 'Sim' ELSE 'Não' END as "LiderPartido",
    dep."ultimoStatus.situacao" as situacao,
    dep."ultimoStatus.condicaoEleitoral" as "condicaoEleitoral",
    leg.id as legislatura,
    leg."dataInicio" as "dataInicioLegislatura",
    leg."dataFim" as "dataFimLegislatura"
  FROM stg_deputados_bruto dep
 INNER JOIN stg_legislaturas_bruto leg ON dep."ultimoStatus.idLegislatura" = leg.id
 INNER JOIN stg_partidos_bruto prt ON dep."ultimoStatus.siglaPartido" = prt.sigla;
----------------------

------- ORGÃO -------
SELECT 
    id as "idOrgao",
    sigla as "siglaOrgao",
    nome,
    apelido,
    "tipoOrgao"
  FROM stg_orgaos_bruto;
---------------------

------- EVENTO -------
SELECT 
    ev.id as "idEvento",      
    ev."descricaoTipo",
    ev.situacao,
    ev."dataHoraInicio",
    ev."dataHoraFim"
  FROM stg_eventos_bruto ev
 INNER JOIN stg_eventos_orgaos_bruto eo ON ev.id = eo."idEventoContexto";
 ---------------------

----- PROPOSICAO -----
SELECT
    prop.id as "idProposicao",    
    substring(aut.uri FROM '[^/]+$') as "idDeputado",
    substring(prop."statusProposicao.uriOrgao" FROM '[^/]+$') as "idOrgao",
    prop."siglaTipo" as "siglaTipoProposicao",
    prop."descricaoTipo" as "descricaoTipoProposicao",
    prop.ano,
    prop.ementa,    
    prop."statusProposicao.descricaoSituacao" as "statusProposicao",
    prop."dataApresentacao"
  FROM stg_proposicoes_bruto prop
 INNER JOIN stg_proposicoes_autores_bruto aut ON prop.id = aut."idProposicaoContexto";
---------------------

------ VOTACAO ------
SELECT
    vt."idVotacaoContexto" as "idVotacao",
    CAST(substring(vc."uriOrgao" FROM '[^/]+$') as int) as "idOrgao",
    CAST(substring(vc."uriEvento" FROM '[^/]+$') as int) as "idEvento",
    vt."deputado_.id" as "idDeputado",
    CAST(substring(vc."uriProposicaoObjeto" FROM '[^/]+$') as int) as "idProposicao",
    vt."tipoVoto",
    vt."dataRegistroVoto" as "dataVoto",
    vc.descricao as "descricaoVotacao",
    CASE WHEN vc.aprovacao = 1 THEN 'Aprovado' ELSE 'Rejeitado' END as "resultadoVotacao"
  FROM stg_votos_bruto vt
 INNER JOIN stg_votacoes_bruto vc ON vt."idVotacaoContexto" = vc.id;
---------------------

------ DESPESA ------
SELECT 
    "idDeputado",
    "tipoDespesa",
    "dataDocumento" as "dataDespesa",
    "valorDocumento" as "valorBruto",
    "valorLiquido",
    "valorGlosa",
    parcela
  FROM stg_despesas_bruto;
  ---------------------