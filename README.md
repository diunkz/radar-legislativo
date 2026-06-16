# Radar Legislativo — Projeto Integrador Fase 1

Projeto de Engenharia de Dados para ingestão, tratamento, modelagem, enriquecimento e automação analítica de dados legislativos da Câmara dos Deputados.

O objetivo do projeto é transformar dados públicos legislativos em uma base confiável, estruturada em camadas, pronta para consumo analítico, dashboards, automações e recursos de inteligência artificial.

---

## Visão Geral da Arquitetura

```text
API Dados Abertos — Câmara dos Deputados
        ↓
01_ingestion — Extração e Staging
        ↓
02_data_model — Modelo relacional e dimensional
        ↓
03_processing — Tratamento, Bronze, Silver e Gold
        ↓
04_ai_features — Classificação, embeddings e resumos por IA
        ↓
05_automation — Envio automatizado de insights
```

A arquitetura segue uma abordagem próxima à **Medallion Architecture**, com separação entre dados brutos, dados tratados e dados analíticos:

```text
Staging → Bronze transitória → Silver → Gold → IA / BI / Automação
```

---

## Estrutura Geral do Projeto

```text
radar-legislativo/
├── 01_ingestion/
│   └── Extração dos dados brutos da API da Câmara
│
├── 02_data_model/
│   └── Scripts SQL e diagramas das camadas Silver e Gold
│
├── 03_processing/
│   └── Pipeline de tratamento, carga Bronze, Silver e Gold
│
├── 04_ai_features/
│   └── Enriquecimento das proposições com IA
│
└── 05_automation/
    └── Workflow n8n para envio semanal de proposições relevantes
```

> Observação: os nomes das pastas podem variar conforme a organização final do repositório, mas a divisão lógica das etapas deve ser preservada.

---

# 1. Ingestão de Dados — API Câmara dos Deputados

A etapa de ingestão é responsável por consumir os dados públicos da API de Dados Abertos da Câmara dos Deputados e enviá-los ao Supabase/PostgreSQL em tabelas de staging.

## Objetivo

Coletar dados legislativos em estado próximo ao bruto, garantindo disponibilidade para as etapas seguintes do pipeline.

A ingestão foi desenhada em duas frentes complementares:

```text
Extração em lote → carga rápida de grandes volumes
Enriquecimento pontual → correção de omissões da API
```

## Scripts Principais

### `extract.py`

Responsável por executar chamadas paginadas nos endpoints da API da Câmara.

Principais características:

- extração em lote;
- suporte a múltiplas tabelas;
- conversão de listas e dicionários em JSON textual;
- envio dos dados ao Supabase;
- parâmetros de execução para tabela específica, teste e data de referência.

Exemplo de execução:

```bash
python src/extract.py --tabela votacoes
```

### `enrich_votacoes.py`

Responsável por complementar informações ausentes nas votações, principalmente o campo `proposicaoObjeto`.

A API da Câmara pode retornar `NULL` em listagens gerais, especialmente em votações de comissão. Para corrigir isso, o enriquecedor consulta o endpoint individual de cada votação e atualiza os registros no banco.

Principais características:

- auditoria dos registros incompletos;
- consulta individual por ID de votação;
- atualização direta no Supabase via SQLAlchemy;
- criação de coluna de auditoria `proposicaoObjeto_original`;
- execução idempotente, processando apenas registros pendentes.

Exemplo de execução:

```bash
python src/enrich_votacoes.py
```

## Estratégias de Resiliência

- retry automático em chamadas HTTP;
- tratamento de timeouts da API;
- tolerância a IDs inexistentes ou retornos `404`;
- enriquecimento incremental;
- preservação da rastreabilidade dos dados originais.

---

# 2. Modelo de Dados — Silver e Gold

A etapa de modelagem define a estrutura relacional e dimensional utilizada pelo projeto.

## Objetivo

Criar as tabelas tratadas da camada Silver e o modelo dimensional da camada Gold, permitindo análise de atividade legislativa com tabelas de fatos e dimensões.

## Estrutura da Modelagem

```text
data-model/
├── silver/
│   └── ch01_cria_tabelas_silver.sql
│
├── gold/
│   └── ch01_cria_tabelas_gold.sql
│
└── docs/
    ├── modelo_logico_silver.png
    ├── modelo_dimensional_gold.png
    ├── ch01_coleta_dados_silver.sql
    └── ch01_coleta_dados_gold.sql
```

## Camada Silver

A Silver contém dados tratados e organizados em tabelas relacionais.

Tabelas principais:

- `silver.deputado`
- `silver.orgao`
- `silver.evento`
- `silver.proposicao`
- `silver.votacao`
- `silver.despesa`

Criação das tabelas:

```sql
\i data-model/silver/ch01_cria_tabelas_silver.sql;
```

## Camada Gold

A Gold organiza os dados em modelo dimensional, com foco em consumo analítico.

Dimensões principais:

- `gold.dim_deputado`
- `gold.dim_orgao`
- `gold.dim_evento`
- `gold.dim_proposicao`
- `gold.dim_votacao`
- `gold.dim_data`

Fatos principais:

- `gold.ft_proposicao`
- `gold.ft_voto`
- `gold.ft_despesa`

Criação das tabelas:

```sql
\i data-model/gold/ch01_cria_tabelas_gold.sql;
```

## Grãos Analíticos

| Tabela fato | Grão | Métrica principal |
|---|---|---|
| `gold.ft_proposicao` | 1 linha por proposição | `qtd_proposicao = 1` |
| `gold.ft_voto` | 1 linha por voto de deputado em votação | `qtd_voto = 1` |
| `gold.ft_despesa` | 1 linha por despesa de deputado por data/tipo | `vl_bruto`, `vl_liquido`, `vl_glosa` |

---

# 3. Processing — Pipeline Bronze, Silver e Gold

A etapa de processamento orquestra o tratamento dos dados, a criação da Bronze transitória e a carga das camadas Silver e Gold.

## Objetivo

Transformar dados vindos da staging em tabelas confiáveis, padronizadas e prontas para análise.

## Fluxo do Pipeline

```text
Staging
  ↓
Tratamento em memória com Pandas
  ↓
Bronze física transitória no Supabase/PostgreSQL
  ↓
Silver
  ↓
Gold
  ↓
Remoção da Bronze transitória
```

## Principais Responsabilidades

- leitura das tabelas staging;
- inspeção e conversão de tipos;
- correção textual;
- remoção de duplicidades;
- carga em Bronze física transitória;
- carga da Silver;
- carga da Gold;
- testes individuais de Silver e Gold;
- preservação de tabelas complementares de IA.

## Arquivos Principais

```text
03_processing/
├── main.py
├── test_silver.py
├── test_gold.py
├── config.py
├── logger.py
├── conexoes/
│   ├── sqlalchemy_engine.py
│   └── supabase_client.py
├── pipeline/
│   ├── leitura.py
│   ├── inspecao.py
│   ├── conversao.py
│   ├── conversao_tipos.py
│   ├── correcao_texto.py
│   ├── deduplicacao.py
│   ├── exportacao.py
│   ├── carga_bronze.py
│   ├── carga_silver.py
│   ├── carga_gold.py
│   ├── drop_bronze.py
│   ├── queries_silver.py
│   └── queries_gold.py
└── requirements.txt
```

## Orquestrador `main.py`

O `main.py` executa o pipeline ponta a ponta.

Responsabilidades:

- conectar ao Supabase/PostgreSQL;
- preparar schemas controlados;
- tratar dados staging com Pandas;
- carregar Bronze física;
- carregar Silver;
- carregar Gold;
- remover Bronze ao final;
- registrar logs e resumo de execução.

Execução:

```bash
python main.py
```

## Bronze Transitória

A Bronze passou a ser física no Supabase/PostgreSQL para reduzir timeouts e melhorar a estabilidade da carga.

Ela é transitória: serve como camada intermediária para carga da Silver e é removida ao final do pipeline.

## Preservação de Tabelas `_ia`

Foi implementada uma regra para preservar tabelas analíticas complementares no schema Silver, especialmente:

```text
silver.proposicoes_ia
```

Essa tabela é produzida pela etapa de IA e não deve ser apagada durante o refresh do pipeline principal.

Comportamento atual:

| Schema | Estratégia |
|---|---|
| `bronze` | drop completo |
| `silver` | limpeza seletiva, preservando objetos `_ia` |
| `gold` | drop completo |

## Testes Individuais

Arquivos de apoio:

```bash
python test_silver.py
python test_gold.py
```

Esses scripts permitem validar cargas específicas sem executar todo o pipeline.

---

# 4. Camada de IA — Classificação, Embeddings e Resumos

A etapa de IA enriquece proposições legislativas com classificação temática, vetores semânticos e resumos executivos.

## Objetivo

Adicionar inteligência semântica à base legislativa, permitindo análise temática, priorização de proposições e busca por similaridade.

## Tabela de Saída

A etapa grava os resultados em uma tabela complementar:

```sql
CREATE TABLE proposicoes_ia (
    proposicao_id       INTEGER PRIMARY KEY,
    tema_classificado   TEXT,
    score_similaridade  FLOAT,
    embedding           vector(1024),
    resumo_executivo    TEXT,
    processado_em       TIMESTAMPTZ
);
```

A coluna `embedding` utiliza a extensão `pgvector` no Supabase:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## Enriquecimentos Gerados

| Recurso | Descrição | Modelo |
|---|---|---|
| Classificação temática | Define o tema da proposição | `intfloat/multilingual-e5-large` |
| Embedding | Gera vetor semântico de 1024 dimensões | `intfloat/multilingual-e5-large` |
| Resumo bulk | Resume histórico completo localmente | `qwen2.5:14b` via Ollama |
| Resumo incremental | Resume novas proposições via API | `llama-3.3-70b-versatile` via Groq |

## Temas Classificados

- Saúde
- Tributário
- Trabalho
- Tecnologia
- Meio Ambiente
- Educação
- Segurança Pública
- Infraestrutura
- Economia
- Direitos Sociais

## Estratégia de Execução

A etapa opera em duas fases para reduzir risco de timeout com o banco:

```text
Fase 1 — processamento local em lotes e gravação em arquivos Parquet
Fase 2 — upload dos resultados ao Supabase
```

Essa separação permite retomar execuções interrompidas sem reprocessar todos os dados.

## Estrutura de Arquivos

```text
04_ai_features/
├── run.py
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── db.py
│   ├── embeddings.py
│   ├── resumos.py
│   └── main.py
├── resultados/
├── requirements.txt
└── env.example
```

## Execução

```bash
# Teste inicial
python run.py --limite 10

# Processamento completo
python run.py

# Processamento incremental
python run.py --incremental

# Apenas upload dos lotes já processados
python run.py --apenas-upload
```

---

# 5. Automação — n8n

A etapa de automação utiliza n8n para consultar a camada Gold e enviar semanalmente as proposições mais relevantes por e-mail.

## Objetivo

Automatizar a distribuição de insights legislativos, reduzindo esforço manual e permitindo acompanhamento recorrente das proposições mais importantes.

## Workflow

Arquivo principal:

```text
05_automation/wf_radar_legislativo_top_proposicoes_semanais.json
```

O workflow executa semanalmente às 06h e envia as top 5 proposições mais relevantes.

## Lógica da Automação

1. Consulta `gold.ft_proposicao` junto com `gold.dim_proposicao` e `gold.dim_deputado`.
2. Filtra proposições dos tipos `PL`, `PEC` e `PLP`.
3. Considera apenas proposições com tema classificado pela IA.
4. Ordena pelo `nr_score_similaridade` em ordem decrescente.
5. Consolida os registros com o nó `Aggregate`.
6. Monta o e-mail em HTML.
7. Envia a mensagem via Gmail.

## Documentação de Apoio

```text
05_automation/docs/
├── n8n_workflow.png
├── dc01_coleta_proposicoes_n8n.sql
└── dc01_formata_email_n8n.html
```

## Como Executar

1. Abrir o n8n.
2. Clicar em `Import from file`.
3. Importar o arquivo `wf_radar_legislativo_top_proposicoes_semanais.json`.
4. Configurar credenciais de Postgres e Gmail.
5. Revisar a query SQL, se necessário.
6. Ativar o workflow.

---

# Variáveis de Ambiente

Cada etapa pode possuir variáveis específicas, mas o projeto depende principalmente de credenciais de banco e, na camada de IA, chaves de API.

Exemplo geral:

```env
SUPABASE_URL=...
SUPABASE_KEY=...
DATABASE_URL=...
DB_URI_DDL=...
GROQ_API_KEY=...
```

> O arquivo `.env` não deve ser versionado. Utilize `env.example` ou `.env.example` como referência segura.

---

# Ordem Recomendada de Execução

```text
1. Criar/validar modelo de dados Silver e Gold
2. Executar ingestão da API para staging
3. Executar pipeline de processamento Bronze → Silver → Gold
4. Executar camada de IA para enriquecer proposições
5. Ativar automação n8n para envio semanal dos insights
```

Comandos principais:

```bash
# Ingestão
python src/extract.py --tabela votacoes
python src/enrich_votacoes.py

# Processing
python main.py

# Testes individuais
python test_silver.py
python test_gold.py

# IA
python run.py --limite 10
python run.py
python run.py --incremental
```

---

# Boas Práticas do Projeto

- separar responsabilidades por etapa;
- manter `.gitignore` na raiz do repositório;
- não versionar `.env`, `__pycache__`, `.DS_Store`, arquivos `.zip` ou outputs locais pesados;
- preservar tabelas externas de IA durante refresh da Silver;
- usar logs para rastrear execução e falhas;
- tratar timeouts e instabilidades da API da Câmara;
- manter tabelas Gold sem nulos em atributos analíticos críticos;
- validar cargas Silver e Gold individualmente antes de rodar o fluxo completo;
- documentar queries, diagramas, workflows e decisões técnicas.

---

# Status Consolidado

| Etapa | Descrição | Status |
|---|---|---|
| 1. Ingestão | Extração e enriquecimento inicial da API da Câmara | Implementada |
| 2. Modelo de Dados | Scripts SQL Silver e Gold, modelo relacional e dimensional | Implementada |
| 3. Processing | Tratamento, Bronze transitória, Silver, Gold e testes | Implementada |
| 4. IA | Classificação temática, embeddings e resumos executivos | Implementada |
| 5. Automação | Workflow n8n para envio semanal de proposições relevantes | Implementada |

---

# Resultado Esperado

Ao final do fluxo, o projeto disponibiliza uma base legislativa estruturada, enriquecida e automatizada, permitindo:

- análise de deputados, proposições, votações, despesas e eventos;
- consumo em dashboards e ferramentas de BI;
- priorização de proposições por similaridade e relevância;
- envio automático de insights legislativos;
- evolução futura com modelos de IA, busca semântica e análises preditivas.
