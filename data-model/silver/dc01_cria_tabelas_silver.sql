/* CRIAÇÃO DE TABELAS DA CAMADA SILVER (TRATADAS) */

------ DEPUTADO ------
CREATE TABLE silver.deputado 
(
  "idDeputado" int not null,
  nome text not null default 'NÃO INFORMADO',
  sexo text not null default 'N/I',
  "dataNascimento" date not null default '9999-12-31',
  "siglaUF" text not null default 'N/I',
  escolaridade text not null default 'NÃO INFORMADO',
  "siglaPartido" text not null default 'N/I',
  "LiderPartido" text not null default 'N/I',
  situacao text not null default 'NÃO INFORMADO',
  "condicaoEleitoral" text not null default 'NÃO INFORMADO',
  legislatura int not null default -1,
  "dataInicioLegislatura" date not null default '9999-12-31',
  "dataFimLegislatura" date not null default '9999-12-31',
  "dataIngestao" date not null default current_timestamp
) TABLESPACE pg_default;
----------------------

------- ORGÃO -------
CREATE TABLE silver.orgao 
(
  "idOrgao" int not null,
  siglaOrgao text not null default 'N/I',
  nome text not null default 'NÃO INFORMADO',
  apelido text not null default 'NÃO INFORMADO',
  "tipoOrgao" text not null default 'NÃO INFORMADO',
  "dataIngestao" date not null default current_timestamp
) TABLESPACE pg_default;
---------------------

------- EVENTO -------
CREATE TABLE silver.evento 
(
  "idEvento" int not null,
  "descricaoTipo" text not null default 'NÃO INFORMADO',
  situacao text not null default 'NÃO INFORMADO',
  "dataHoraInicio" date not null default '9999-12-31',
  "dataHoraFim" date not null default '9999-12-31',
  "dataIngestao" date not null default current_timestamp
) TABLESPACE pg_default;
---------------------

----- PROPOSICAO -----
CREATE TABLE silver.proposicao 
(
  "idProposicao" int not null,
  "idDeputado" int not null default -1,
  "idOrgao" int not null default -1,
  "siglaTipoProposicao" text not null default 'N/I',
  "descricaoTipoProposicao" text not null default 'NÃO INFORMADO',
  ano int not null default 9999,
  ementa text not null default 'NÃO INFORMADO',
  "statusProposicao" text not null default 'NÃO INFORMADO',
  "dataApresentacao" date not null default '9999-12-31',
  "dataIngestao" date not null default current_timestamp
) TABLESPACE pg_default;
---------------------

------ VOTACAO ------
CREATE TABLE silver.votacao 
(
  "idVotacao" int not null,
  "idOrgao" int not null default -1,
  "idEvento" int not null default -1,
  "idDeputado" int not null default -1,
  "idProposicao" int not null default -3, 
  "tipoVoto" text not null default 'NÃO INFORMADO',
  "dataVoto" date not null default '9999-12-31',
  "descricaoVotacao" text not null default 'NÃO INFORMADO',
  "resultadoVotacao" text not null default 'NÃO INFORMADO',
  "dataIngestao" date not null default current_timestamp
) TABLESPACE pg_default; 
---------------------

------ DESPESA ------
CREATE TABLE silver.despesa 
(
  "idDeputado" int not null,
  "tipoDespesa" text not null default 'NÃO INFORMADO',
  "dataDespesa" date not null default '9999-12-31',
  "valorBruto" decimal not null default 0,
  "valorLiquido" decimal not null default 0,
  "valorGlosa" decimal not null default 0,
  parcela int not null default 0,
  "dataIngestao" date not null default current_timestamp
) TABLESPACE pg_default; 
---------------------

------ PROPOSICAO IA ------
CREATE TABLE silver.proposicoes_ia (
  proposicao_id integer not null,
  tema_classificado text null,
  score_similaridade double precision null,
  resumo_executivo text null,
  processado_em timestamp with time zone null default now(),
  embedding public.vector null,
  constraint proposicoes_ia_pkey primary key (proposicao_id)
) TABLESPACE pg_default;
---------------------------