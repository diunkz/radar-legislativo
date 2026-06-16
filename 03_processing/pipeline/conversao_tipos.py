# ---------------------------------------------------------------------------
# Mapeamento de conversão de tipos  (coluna → dtype pandas)
# None = manter o tipo inferido automaticamente
        # Pandas -> PostgreSQL
        # Int64            -> BIGINT
        # string           -> TEXT
        # datetime64[ns]   -> DATE ou TIMESTAMPTZ
        # boolean          -> BOOLEAN
        # Float64          -> DOUBLE PRECISION

        # ---------------------------------------------------------------------------
# CONVERSAO_TIPOS — fonte única da verdade
    # Dtype pandas → tratamento automático inferido por aplicar_conversoes()
    #
    #   Int64          → pd.to_numeric(errors="coerce") + astype("Int64")
    #   Float64        → pd.to_numeric(errors="coerce") + astype("Float64")
    #   datetime64[ns] → pd.to_datetime(errors="coerce", utc=True)
    #   boolean        → mapeamento 0/1/True/False + astype("boolean")
    #   string         → astype("string")
    # ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
CONVERSAO_TIPOS: dict[str, dict[str, str]] =    {
    "stg_deputados_bruto":  {
        "id":                                   "Int64",           # PostgreSQL: BIGINT
        "uri":                                  "string",          # PostgreSQL: TEXT
        "nomeCivil":                            "string",          # PostgreSQL: TEXT
        "cpf":                                  "string",          # PostgreSQL: TEXT
        "sexo":                                 "string",          # PostgreSQL: CHAR(1) ou TEXT
        "urlWebsite":                           "string",          # PostgreSQL: TEXT
        "redeSocial":                           "string",          # PostgreSQL: JSONB (recomendado) ou TEXT
        "dataNascimento":                       "datetime64[ns]",  # PostgreSQL: DATE
        "dataFalecimento":                      "datetime64[ns]",  # PostgreSQL: DATE
        "ufNascimento":                         "string",          # PostgreSQL: CHAR(2) ou TEXT
        "municipioNascimento":                  "string",          # PostgreSQL: TEXT
        "escolaridade":                         "string",          # PostgreSQL: TEXT
        "ultimoStatus.id":                      "Int64",           # PostgreSQL: BIGINT
        "ultimoStatus.uri":                     "string",          # PostgreSQL: TEXT
        "ultimoStatus.nome":                    "string",          # PostgreSQL: TEXT
        "ultimoStatus.siglaPartido":            "string",          # PostgreSQL: VARCHAR(20) ou TEXT
        "ultimoStatus.uriPartido":              "string",          # PostgreSQL: TEXT
        "ultimoStatus.siglaUf":                 "string",          # PostgreSQL: CHAR(2) ou TEXT
        "ultimoStatus.idLegislatura":           "Int64",           # PostgreSQL: BIGINT
        "ultimoStatus.urlFoto":                 "string",          # PostgreSQL: TEXT
        "ultimoStatus.email":                   "string",          # PostgreSQL: TEXT
        "ultimoStatus.data":                    "datetime64[ns]",  # PostgreSQL: TIMESTAMPTZ
        "ultimoStatus.nomeEleitoral":           "string",          # PostgreSQL: TEXT
        "ultimoStatus.gabinete.nome":           "string",          # PostgreSQL: TEXT
        "ultimoStatus.gabinete.predio":         "string",          # PostgreSQL: TEXT
        "ultimoStatus.gabinete.sala":           "string",          # PostgreSQL: TEXT
        "ultimoStatus.gabinete.andar":          "Int64",           # PostgreSQL: BIGINT
        "ultimoStatus.gabinete.telefone":       "string",          # PostgreSQL: TEXT
        "ultimoStatus.gabinete.email":          "string",          # PostgreSQL: TEXT
        "ultimoStatus.situacao":                "string",          # PostgreSQL: TEXT
        "ultimoStatus.condicaoEleitoral":       "string",          # PostgreSQL: TEXT
        "ultimoStatus.descricaoStatus":         "string",          # PostgreSQL: TEXT
        "data_captura":                         "datetime64[ns]"   # PostgreSQL: TIMESTAMPTZ
    },

    "stg_despesas_bruto": {
        "ano":                 "Int64",           # PostgreSQL: INTEGER
        "mes":                 "Int64",           # PostgreSQL: SMALLINT
        "tipoDespesa":         "string",          # PostgreSQL: TEXT
        "codDocumento":        "string",          # PostgreSQL: TEXT
        "tipoDocumento":       "string",          # PostgreSQL: TEXT
        "codTipoDocumento":    "Int64",           # PostgreSQL: INTEGER
        "dataDocumento":       "datetime64[ns]",  # PostgreSQL: DATE
        "numDocumento":        "string",          # PostgreSQL: TEXT
        "valorDocumento":      "Float64",         # PostgreSQL: NUMERIC(14,2)
        "urlDocumento":        "string",          # PostgreSQL: TEXT
        "nomeFornecedor":      "string",          # PostgreSQL: TEXT
        "cnpjCpfFornecedor":   "string",          # PostgreSQL: TEXT
        "valorLiquido":        "Float64",         # PostgreSQL: NUMERIC(14,2)
        "valorGlosa":          "Float64",         # PostgreSQL: NUMERIC(14,2)
        "numRessarcimento":    "string",          # PostgreSQL: TEXT
        "codLote":             "Int64",           # PostgreSQL: BIGINT
        "parcela":             "Int64",           # PostgreSQL: SMALLINT
        "idDeputado":          "Int64",           # PostgreSQL: BIGINT
        "data_captura":        "datetime64[ns]"   # PostgreSQL: TIMESTAMPTZ
    },

    "stg_eventos_bruto": {
        "id":                  "Int64",           # PostgreSQL: BIGINT
        "uri":                 "string",          # PostgreSQL: TEXT
        "dataHoraInicio":      "datetime64[ns]",  # PostgreSQL: TIMESTAMPTZ
        "dataHoraFim":         "datetime64[ns]",  # PostgreSQL: TIMESTAMPTZ
        "situacao":            "string",          # PostgreSQL: TEXT
        "descricaoTipo":       "string",          # PostgreSQL: TEXT
        "descricao":           "string",          # PostgreSQL: TEXT
        "localExterno":        "string",          # PostgreSQL: TEXT
        "orgaos":              "string",          # PostgreSQL: JSONB (recomendado) ou TEXT
        "urlRegistro":         "string",          # PostgreSQL: TEXT
        "localCamara.nome":    "string",          # PostgreSQL: TEXT
        "localCamara.predio":  "string",          # PostgreSQL: TEXT
        "localCamara.sala":    "string",          # PostgreSQL: TEXT
        "localCamara.andar":   "Int64",           # PostgreSQL: INTEGER
        "data_captura":        "datetime64[ns]"   # PostgreSQL: TIMESTAMPTZ
    },

    "stg_eventos_orgaos_bruto": {
        "id":                  "Int64",           # PostgreSQL: BIGINT
        "uri":                 "string",          # PostgreSQL: TEXT
        "sigla":               "string",          # PostgreSQL: TEXT
        "nome":                "string",          # PostgreSQL: TEXT
        "apelido":             "string",          # PostgreSQL: TEXT
        "codTipoOrgao":        "Int64",           # PostgreSQL: BIGINT
        "tipoOrgao":           "string",          # PostgreSQL: TEXT
        "nomePublicacao":      "string",          # PostgreSQL: TEXT
        "nomeResumido":        "string",          # PostgreSQL: TEXT
        "idEventoContexto":    "Int64",           # PostgreSQL: BIGINT
        "data_captura":        "datetime64[ns]"   # PostgreSQL: TIMESTAMPTZ
    },

    "stg_frentes_bruto": {
        "id":              "Int64",           # PostgreSQL: BIGINT
        "uri":             "string",          # PostgreSQL: TEXT
        "titulo":          "string",          # PostgreSQL: TEXT
        "idLegislatura":   "Int64",           # PostgreSQL: INTEGER
        "data_captura":    "datetime64[ns]"   # PostgreSQL: TIMESTAMPTZ
    },

    "stg_legislaturas_bruto": {
        "id":              "Int64",           # PostgreSQL: INTEGER
        "uri":             "string",          # PostgreSQL: TEXT
        "dataInicio":      "datetime64[ns]",  # PostgreSQL: DATE
        "dataFim":         "datetime64[ns]",  # PostgreSQL: DATE
        "data_captura":    "datetime64[ns]"   # PostgreSQL: TIMESTAMPTZ
    },

    "stg_liderancas_bruto": {
        "titulo":                          "string",          # PostgreSQL: TEXT
        "dataInicio":                      "datetime64[ns]",  # PostgreSQL: DATE
        "dataFim":                         "datetime64[ns]",  # PostgreSQL: DATE
        "idLegislaturaContexto":           "Int64",           # PostgreSQL: INTEGER
        "parlamentar.id":                  "Int64",           # PostgreSQL: BIGINT
        "parlamentar.uri":                 "string",          # PostgreSQL: TEXT
        "parlamentar.nome":                "string",          # PostgreSQL: TEXT
        "parlamentar.siglaPartido":        "string",          # PostgreSQL: VARCHAR(20) ou TEXT
        "parlamentar.uriPartido":          "string",          # PostgreSQL: TEXT
        "parlamentar.siglaUf":             "string",          # PostgreSQL: CHAR(2) ou TEXT
        "parlamentar.idLegislatura":       "Int64",           # PostgreSQL: INTEGER
        "parlamentar.email":               "string",          # PostgreSQL: TEXT
        "parlamentar.urlFoto":             "string",          # PostgreSQL: TEXT
        "bancada.tipo":                    "string",          # PostgreSQL: TEXT
        "bancada.nome":                    "string",          # PostgreSQL: TEXT
        "bancada.uri":                     "string",          # PostgreSQL: TEXT
        "data_captura":                    "datetime64[ns]"   # PostgreSQL: TIMESTAMPTZ
    },

    "stg_orgaos_bruto": {
        "id":               "Int64",           # PostgreSQL: BIGINT
        "uri":              "string",          # PostgreSQL: TEXT
        "sigla":            "string",          # PostgreSQL: VARCHAR(50) ou TEXT
        "nome":             "string",          # PostgreSQL: TEXT
        "apelido":          "string",          # PostgreSQL: TEXT
        "codTipoOrgao":     "Int64",           # PostgreSQL: INTEGER
        "tipoOrgao":        "string",          # PostgreSQL: TEXT
        "nomePublicacao":   "string",          # PostgreSQL: TEXT
        "nomeResumido":     "string",          # PostgreSQL: TEXT
        "data_captura":     "datetime64[ns]"   # PostgreSQL: TIMESTAMPTZ
    },

    "stg_partidos_bruto": {
        "id":                               "Int64",           # PostgreSQL: INTEGER
        "sigla":                            "string",          # PostgreSQL: VARCHAR(20) ou TEXT
        "nome":                             "string",          # PostgreSQL: TEXT
        "uri":                              "string",          # PostgreSQL: TEXT
        "numeroEleitoral":                  "Int64",           # PostgreSQL: INTEGER
        "urlLogo":                          "string",          # PostgreSQL: TEXT
        "urlWebSite":                       "string",          # PostgreSQL: TEXT
        "urlFacebook":                      "string",          # PostgreSQL: TEXT
        "status.data":                      "datetime64[ns]",  # PostgreSQL: DATE
        "status.idLegislatura":             "Int64",           # PostgreSQL: INTEGER
        "status.situacao":                  "string",          # PostgreSQL: TEXT
        "status.totalPosse":                "Int64",           # PostgreSQL: INTEGER
        "status.totalMembros":              "Int64",           # PostgreSQL: INTEGER
        "status.uriMembros":                "string",          # PostgreSQL: TEXT
        "status.lider.uri":                 "string",          # PostgreSQL: TEXT
        "status.lider.nome":                "string",          # PostgreSQL: TEXT
        "status.lider.siglaPartido":        "string",          # PostgreSQL: VARCHAR(20) ou TEXT
        "status.lider.uriPartido":          "string",          # PostgreSQL: TEXT
        "status.lider.uf":                  "string",          # PostgreSQL: CHAR(2) ou TEXT
        "status.lider.idLegislatura":       "Int64",           # PostgreSQL: INTEGER
        "status.lider.urlFoto":             "string",          # PostgreSQL: TEXT
        "data_captura":                     "datetime64[ns]"   # PostgreSQL: TIMESTAMPTZ
    },

    "stg_proposicoes_autores_bruto": {
        "uri":                   "string",          # PostgreSQL: TEXT
        "nome":                  "string",          # PostgreSQL: TEXT
        "codTipo":               "Int64",           # PostgreSQL: INTEGER
        "tipo":                  "string",          # PostgreSQL: TEXT
        "ordemAssinatura":       "Int64",           # PostgreSQL: INTEGER
        "proponente":            "boolean",         # PostgreSQL: BOOLEAN
        "idProposicaoContexto":  "Int64",           # PostgreSQL: BIGINT
        "data_captura":          "datetime64[ns]"   # PostgreSQL: TIMESTAMPTZ
    },

    "stg_proposicoes_bruto": {
        "id":                                       "Int64",           # PostgreSQL: BIGINT
        "uri":                                      "string",          # PostgreSQL: TEXT
        "siglaTipo":                                "string",          # PostgreSQL: VARCHAR(20) ou TEXT
        "codTipo":                                  "Int64",           # PostgreSQL: INTEGER
        "numero":                                   "Int64",           # PostgreSQL: INTEGER
        "ano":                                      "Int64",           # PostgreSQL: SMALLINT
        "ementa":                                   "string",          # PostgreSQL: TEXT
        "dataApresentacao":                         "datetime64[ns]",  # PostgreSQL: DATE
        "uriOrgaoNumerador":                        "string",          # PostgreSQL: TEXT
        "uriAutores":                               "string",          # PostgreSQL: TEXT
        "descricaoTipo":                            "string",          # PostgreSQL: TEXT
        "ementaDetalhada":                          "string",          # PostgreSQL: TEXT
        "keywords":                                 "string",          # PostgreSQL: TEXT
        "uriPropPrincipal":                         "string",          # PostgreSQL: TEXT
        "uriPropAnterior":                          "string",          # PostgreSQL: TEXT
        "uriPropPosterior":                         "string",          # PostgreSQL: TEXT
        "urlInteiroTeor":                           "string",          # PostgreSQL: TEXT
        "urnFinal":                                 "string",          # PostgreSQL: TEXT
        "texto":                                    "string",          # PostgreSQL: TEXT
        "justificativa":                            "string",          # PostgreSQL: TEXT
        "statusProposicao.dataHora":                "datetime64[ns]",  # PostgreSQL: TIMESTAMPTZ
        "statusProposicao.sequencia":               "Int64",           # PostgreSQL: INTEGER
        "statusProposicao.siglaOrgao":              "string",          # PostgreSQL: VARCHAR(50) ou TEXT
        "statusProposicao.uriOrgao":                "string",          # PostgreSQL: TEXT
        "statusProposicao.uriUltimoRelator":        "string",          # PostgreSQL: TEXT
        "statusProposicao.regime":                  "string",          # PostgreSQL: TEXT
        "statusProposicao.descricaoTramitacao":     "string",          # PostgreSQL: TEXT
        "statusProposicao.codTipoTramitacao":       "Int64",           # PostgreSQL: INTEGER
        "statusProposicao.descricaoSituacao":       "string",          # PostgreSQL: TEXT
        "statusProposicao.codSituacao":             "Int64",           # PostgreSQL: INTEGER
        "statusProposicao.despacho":                "string",          # PostgreSQL: TEXT
        "statusProposicao.url":                     "string",          # PostgreSQL: TEXT
        "statusProposicao.ambito":                  "string",          # PostgreSQL: TEXT
        "statusProposicao.apreciacao":              "string",          # PostgreSQL: TEXT
        "data_captura":                             "datetime64[ns]"   # PostgreSQL: TIMESTAMPTZ
    },

    "stg_votacoes_bruto": {
        "id":                   "string",          # PostgreSQL: INTEGER
        "uri":                  "string",          # PostgreSQL: TEXT
        "data":                 "datetime64[ns]",  # PostgreSQL: DATE
        "dataHoraRegistro":     "datetime64[ns]",  # PostgreSQL: TIMESTAMPTZ
        "siglaOrgao":           "string",          # PostgreSQL: VARCHAR(50) ou TEXT
        "uriOrgao":             "string",          # PostgreSQL: TEXT
        "uriEvento":            "string",          # PostgreSQL: TEXT
        "proposicaoObjeto":     "string",          # PostgreSQL: TEXT
        "uriProposicaoObjeto":  "string",          # PostgreSQL: TEXT
        "descricao":            "string",          # PostgreSQL: TEXT
        "aprovacao":            "boolean",         # PostgreSQL: BOOLEAN
        "data_captura":         "datetime64[ns]"   # PostgreSQL: TIMESTAMPTZ
    },

    "stg_votos_bruto": {
        "tipoVoto":                    "string",          # PostgreSQL: TEXT
        "dataRegistroVoto":            "datetime64[ns]",  # PostgreSQL: TIMESTAMPTZ
        "idVotacaoContexto":           "string",          # PostgreSQL: BIGINT
        "deputado_.id":                "Int64",           # PostgreSQL: BIGINT
        "deputado_.uri":               "string",          # PostgreSQL: TEXT
        "deputado_.nome":              "string",          # PostgreSQL: TEXT
        "deputado_.siglaPartido":      "string",          # PostgreSQL: VARCHAR(20) ou TEXT
        "deputado_.uriPartido":        "string",          # PostgreSQL: TEXT
        "deputado_.siglaUf":           "string",          # PostgreSQL: CHAR(2) ou TEXT
        "deputado_.idLegislatura":     "Int64",           # PostgreSQL: INTEGER
        "deputado_.urlFoto":           "string",          # PostgreSQL: TEXT
        "deputado_.email":             "string",          # PostgreSQL: TEXT
        "data_captura":                "datetime64[ns]"   # PostgreSQL: TIMESTAMPTZ
    }
}