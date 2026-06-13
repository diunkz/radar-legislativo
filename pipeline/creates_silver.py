"""
pipeline/creates_silver.py
--------------------------

DDL das tabelas da camada Silver.

Este arquivo centraliza a criação física das tabelas Silver.
A carga Silver deve primeiro dropar as tabelas existentes,
depois recriar as estruturas e, por fim, executar os INSERTs
definidos em queries_silver.py.
"""


CREATES_SILVER: dict[str, str] = {
    "deputado": """
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
            "dataIngestao" date not null default current_date
        ) TABLESPACE pg_default;
    """,

    "orgao": """
        CREATE TABLE silver.orgao 
        (
            "idOrgao" int not null,
            siglaOrgao text not null default 'N/I',
            nome text not null default 'NÃO INFORMADO',
            apelido text not null default 'NÃO INFORMADO',
            "tipoOrgao" text not null default 'NÃO INFORMADO',
            "dataIngestao" date not null default current_date
        ) TABLESPACE pg_default;
    """,

    "evento": """
        CREATE TABLE silver.evento 
        (
            "idEvento" int not null,
            "descricaoTipo" text not null default 'NÃO INFORMADO',
            situacao text not null default 'NÃO INFORMADO',
            "dataHoraInicio" date not null default '9999-12-31',
            "dataHoraFim" date not null default '9999-12-31',
            "dataIngestao" date not null default current_date
        ) TABLESPACE pg_default;
    """,

    "proposicao": """
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
            "dataIngestao" date not null default current_date
        ) TABLESPACE pg_default;
    """,

    "votacao": """
        CREATE TABLE silver.votacao 
        (
            "idVotacao" bigint not null,
            "idOrgao" bigint not null default -1,
            "idEvento" bigint not null default -1,
            "idDeputado" bigint not null default -1,
            "idProposicao" bigint not null default -3, 
            "tipoVoto" text not null default 'NÃO INFORMADO',
            "dataVoto" date not null default '9999-12-31',
            "descricaoVotacao" text not null default 'NÃO INFORMADO',
            "resultadoVotacao" text not null default 'NÃO INFORMADO',
            "dataIngestao" date not null default current_date
        ) TABLESPACE pg_default;
    """,

    "despesa": """
        CREATE TABLE silver.despesa 
        (
            "idDeputado" int not null,
            "tipoDespesa" text not null default 'NÃO INFORMADO',
            "dataDespesa" date not null default '9999-12-31',
            "valorBruto" decimal not null default 0,
            "valorLiquido" decimal not null default 0,
            "valorGlosa" decimal not null default 0,
            parcela int not null default 0,
            "dataIngestao" date not null default current_date
        ) TABLESPACE pg_default;
    """,
}