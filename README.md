# Radar Legislativo — Pipeline de Ingestão, Tratamento e Modelo Dimensional

Projeto de engenharia de dados para ingestão, tratamento e modelagem analítica de dados legislativos, com persistência em Supabase/PostgreSQL e organização em camadas **Staging**, **Bronze** (temp), **Silver** e **Gold**.

O projeto parte de dados consumidos pela API na etapa de extração, transforma as tabelas staging em estruturas tratadas, cria uma camada Bronze física transitória, gera a camada Silver com regras de negócio e finaliza com a camada Gold em modelo dimensional com dimensões e fatos.

---

## Visão geral do fluxo.

```text
API / Staging
    -> Tratamento em memória com Pandas
    -> Exportação CSV de dados tratados
    -> Bronze física transitória no Supabase/PostgreSQL
    -> Silver full refresh
    -> Gold dimensional full refresh
    -> Drop da Bronze transitória
```

A estratégia final adotada é **FULL REFRESH**. A cada execução ponta a ponta, os schemas técnicos do pipeline são removidos e recriados, evitando resíduos de execuções anteriores, duplicidades e inconsistências de chave substituta.

---

## Responsabilidades implementadas no projeto

As etapas abaixo foram realizadas integralmente pelo autor do projeto após o consumo inicial da API:

| Etapa | Responsabilidade |
|---|---|
| `PIPELINE` após consumo da API | Tratamento das tabelas staging carregadas pela `src/extract.py` |
| `OUTPUT` | Geração de arquivos CSV com dados tratados após consumo das staging da API |
| `main.py` | Orquestrador principal da execução ponta a ponta |
| `test_silver.py` | Entrada individual para testes de carga da camada Silver |
| `test_gold.py` | Entrada individual para testes de carga da camada Gold |
| Ajustes nas queries | Adequações necessárias para compatibilizar o modelo de dados recebido com a execução real do pipeline |

O modelo dimensional base foi recebido de outro engenheiro. Durante a implementação, foram necessários ajustes técnicos nas queries, chaves e grãos das tabelas para garantir execução íntegra, sem duplicidade e compatível com a estrutura real dos dados.

---

## Estrutura principal do projeto

```text
radar-legislativo/
├── src/
│   └── extract.py
├── pipeline/
│   ├── carga_bronze.py
│   ├── carga_silver.py
│   ├── carga_gold.py
│   ├── creates_silver.py
│   ├── creates_gold.py
│   ├── queries_silver.py
│   ├── queries_gold.py
│   ├── leitura.py
│   ├── inspecao.py
│   ├── conversao.py
│   ├── conversao_tipos.py
│   ├── correcao_texto.py
│   ├── deduplicacao.py
│   ├── exportacao.py
│   ├── drop_bronze.py
│   └── mapeamento_bronze.py
├── conexoes/
│   ├── sqlalchemy_engine.py
│   └── supabase_client.py
├── output/
├── main.py
├── test_silver.py
├── test_gold.py
├── config.py
├── logger.py
├── requirements.txt
└── .env.example
```

---

## Camadas do pipeline

### 1. Extração — `src/extract.py`
Engenheiro 1

### 2. Tratamento em memória — `pipeline/*`

Após a extração, o pipeline lê as staging e executa tratamento em memória com Pandas.

Arquivos principais:

| Arquivo | Função |
|---|---|
| `pipeline/leitura.py` | Lê tabelas staging do banco para DataFrames Pandas |
| `pipeline/inspecao.py` | Gera diagnóstico de tipos, nulos e cardinalidade |
| `pipeline/conversao.py` | Aplica conversões de tipo por tabela |
| `pipeline/conversao_tipos.py` | Centraliza o dicionário de tipos esperados |
| `pipeline/correcao_texto.py` | Corrige acentuação, mojibake e padroniza texto em uppercase |
| `pipeline/deduplicacao.py` | Remove duplicidades com chaves específicas por tabela |
| `pipeline/exportacao.py` | Exporta CSVs tratados para a pasta `output/ajustadas` |

---

### 3. Output tratado — `output/ajustadas`

A etapa de output salva cópias CSV dos DataFrames tratados, permitindo inspeção externa, auditoria e comparação com as tabelas carregadas no banco.

Formato de saída:

```text
<tabela>_ajustada_<YYYYMMDD_HHMMSS>.csv
```

Exemplo:

```text
stg_deputados_ajustada_20260613_145348.csv
stg_despesas_ajustada_20260613_145348.csv
stg_votacoes_ajustada_20260613_145348.csv
```

---

### 4. Bronze física transitória — `pipeline/carga_bronze.py`

A Bronze é criada fisicamente no Supabase/PostgreSQL durante a execução e removida ao final.

Objetivo:

- Evitar uso excessivo de memória.
- Reduzir timeout em cargas grandes.
- Permitir que a Silver execute transformações diretamente no banco via SQL.
- Isolar dados tratados antes da aplicação das regras de negócio.

Principais características:

- Criação do schema `bronze`.
- Carga das tabelas via `COPY FROM STDIN`, usando método customizado no `pandas.to_sql`.
- Recriação das tabelas Bronze a cada execução.
- Remoção do schema Bronze no final por meio de `pipeline/drop_bronze.py`.

Mapeamento aplicado no `main.py`:

| Staging | Bronze |
|---|---|
| `stg_deputados_bruto` | `bronze.deputados` |
| `stg_legislaturas_bruto` | `bronze.legislaturas` |
| `stg_partidos_bruto` | `bronze.partidos` |
| `stg_orgaos_bruto` | `bronze.orgaos` |
| `stg_eventos_bruto` | `bronze.eventos` |
| `stg_eventos_orgaos_bruto` | `bronze.eventos_orgaos` |
| `stg_proposicoes_bruto` | `bronze.proposicoes` |
| `stg_proposicoes_autores_bruto` | `bronze.proposicoes_autores` |
| `stg_despesas_bruto` | `bronze.despesas` |
| `stg_votos_bruto` | `bronze.votos` |
| `stg_votacoes_bruto` | `bronze.votacoes` |

---

### 5. Silver — `creates_silver.py`, `queries_silver.py`, `carga_silver.py`

A camada Silver aplica regras de negócio, padronização, tratamento de nulos, extração de IDs e preparação das entidades analíticas intermediárias.

Tabelas Silver:

```text
silver.deputado
silver.orgao
silver.evento
silver.proposicao
silver.votacao
silver.despesa
```

A carga Silver utiliza a estratégia:

```text
DROP TABLE
CREATE TABLE
INSERT INTO ... SELECT ...
```

Essa decisão foi tomada para evitar resíduos de cargas anteriores e garantir que a estrutura física reflita sempre a versão atual do projeto.

#### Principais ajustes realizados em Silver

| Tabela | Ajuste realizado |
|---|---|
| `silver.deputado` | Join com `bronze.legislaturas` e `bronze.partidos` para enriquecer dados legislativos e identificar liderança partidária |
| `silver.orgao` | Padronização de sigla, nome, apelido e tipo de órgão com defaults para valores nulos |
| `silver.evento` | Join com `bronze.eventos_orgaos` para validar contexto de evento e órgão |
| `silver.proposicao` | Uso de `SELECT DISTINCT` e extração de IDs a partir de URIs de autores e órgãos |
| `silver.votacao` | Ajuste de tipos para `bigint`, correção da coluna `deputado_.id`, casts defensivos com regex e fallback para `-1` ou `-3` |
| `silver.despesa` | Inclusão da coluna `codDespesa`, derivada de `codDocumento`, para preservar o grão da despesa e evitar duplicidade na fato Gold |

O ajuste em `silver.despesa` foi essencial para corrigir a granularidade da despesa. Sem `codDespesa`, a fato `gold.ft_despesa` ficava dependente apenas de deputado, data e tipo de despesa, o que causava colisão de chave primária quando havia mais de uma despesa do mesmo tipo no mesmo dia.

---

### 6. Gold dimensional — `creates_gold.py`, `queries_gold.py`, `carga_gold.py`

A camada Gold representa o modelo dimensional final do projeto, organizado em dimensões e fatos.

Dimensões:

```text
gold.dim_deputado
gold.dim_orgao
gold.dim_evento
gold.dim_proposicao
gold.dim_votacao
```

Fatos:

```text
gold.ft_proposicao
gold.ft_voto
gold.ft_despesa
```

A carga Gold também utiliza:

```text
DROP TABLE
CREATE TABLE
INSERT INTO ... SELECT ...
```

#### Registros técnicos de dimensão

As dimensões Gold são criadas com chaves substitutas `sk_*` e recebem registros técnicos iniciais:

| SK | Significado |
|---:|---|
| `-1` | Não informado |
| `-3` | Não se aplica |

Esses registros são inseridos diretamente no DDL de `creates_gold.py`, antes da carga dos dados de negócio.

#### Ajustes importantes em Gold

| Tabela | Ajuste realizado |
|---|---|
| `dim_deputado` | Correção do atributo `nm_deputado` e criação de surrogate key `sk_deputado` |
| `dim_orgao` | Criação de `sk_orgao` e registros técnicos `-1` e `-3` |
| `dim_evento` | Criação de `sk_evento` e padronização de situação/tipo |
| `dim_proposicao` | Criação de `sk_proposicao` e status da proposição |
| `dim_votacao` | Uso de `bigint` para `id_votacao` devido ao tamanho dos identificadores de votação |
| `ft_proposicao` | Construção com SKs de deputado, órgão, proposição e data da proposição |
| `ft_voto` | Construção com SKs de votação, deputado, órgão, evento, proposição e data do voto |
| `ft_despesa` | Inclusão de `sk_cod_despesa` na chave primária para respeitar o grão real da despesa |

A fato `ft_despesa` ficou no seguinte grão:

```text
sk_deputado + sk_data_despesa + sk_cod_despesa + tp_despesa
```

Esse ajuste evita duplicidade quando um deputado possui mais de uma despesa no mesmo dia e do mesmo tipo.

---

## Orquestrador principal — `main.py`

O arquivo `main.py` é o corpo principal do pipeline ponta a ponta.

Responsabilidades:

1. Conectar ao Supabase e ao PostgreSQL via SQLAlchemy.
2. Preparar o ambiente em estratégia FULL REFRESH.
3. Remover schemas `bronze`, `silver` e `gold` no início da execução.
4. Ler tabelas staging.
5. Aplicar inspeção, conversão, correção textual e deduplicação.
6. Exportar CSVs tratados.
7. Criar e carregar Bronze física transitória.
8. Criar e carregar Silver.
9. Criar e carregar Gold.
10. Remover Bronze ao final da execução.
11. Registrar resumo final no log.

Fluxo resumido:

```text
preparar_ambiente_inicial()
preparar_tabelas_bronze()
carregar_bronze()
carregar_silver()
carregar_gold()
drop_bronze()
```

---

## Testes individuais

### Teste Silver — `test_silver.py`

Permite testar uma tabela Silver isoladamente sem rodar a pipeline completa.

Características:

- Escolha da tabela por meio de `TABELA_TESTE`.
- Mapeamento das dependências Bronze necessárias por tabela Silver.
- Criação de Bronze física somente para as tabelas necessárias.
- Validação de existência da tabela em `CREATES_SILVER` e `QUERIES_SILVER`.
- Execução de `carregar_silver(engine, nome_tabela=TABELA_TESTE)`.

Exemplo:

```python
TABELA_TESTE = "despesa"
```

Execução:

```bash
uv run test_silver.py
```

---

### Teste Gold — `test_gold.py`

Permite testar uma dimensão ou fato Gold isoladamente.

Características:

- Escolha da tabela por meio de `TABELA_TESTE`.
- Validação das dependências Silver antes da execução.
- Para fatos, carrega automaticamente as dimensões Gold necessárias antes da fato.
- Validação de existência e quantidade de registros após a carga.

Exemplo:

```python
TABELA_TESTE = "ft_despesa"
```

Execução:

```bash
uv run test_gold.py
```

Ordem de execução aplicada para fatos:

| Fato | Ordem de carga no teste |
|---|---|
| `ft_despesa` | `dim_deputado -> ft_despesa` |
| `ft_proposicao` | `dim_deputado -> dim_orgao -> dim_proposicao -> ft_proposicao` |
| `ft_voto` | `dim_votacao -> dim_deputado -> dim_orgao -> dim_evento -> dim_proposicao -> ft_voto` |

---

## Como executar

### 1. Instalar dependências

```bash
pip install -r requirements.txt
```

ou, usando `uv`:

```bash
uv pip install -r requirements.txt
```

> Observação: como o projeto utiliza `supabase-py` em `conexoes/supabase_client.py`, garanta que o pacote `supabase` esteja instalado no ambiente caso ele não esteja listado no `requirements.txt` local.

### 2. Configurar variáveis de ambiente

Crie um arquivo `.env` na raiz do projeto.

Exemplo recomendado:

```env
DB_URL=https://<projeto>.supabase.co
DB_KEY=<sua-chave-anon-ou-service-role>
DB_URI_DDL=postgresql+psycopg2://user:password@host:5432/dbname
SUPABASE_DB_URL=postgresql+psycopg2://user:password@host:5432/dbname
```

Variáveis usadas:

| Variável | Uso |
|---|---|
| `DB_URL` | URL do projeto Supabase usada pelo client Supabase |
| `DB_KEY` | Chave de autenticação Supabase |
| `DB_URI_DDL` | Conexão SQLAlchemy direta para DDL e cargas SQL |
| `SUPABASE_DB_URL` | Conexão usada pela etapa `src/extract.py` |

### 3. Executar extração da API

```bash
uv run src/extract.py
```

Essa etapa carrega/atualiza as tabelas staging `stg_*_bruto`.

### 4. Executar pipeline ponta a ponta

```bash
uv run main.py
```

A execução ponta a ponta aplica:

```text
FULL REFRESH
-> Bronze transitória
-> Silver
-> Gold
-> Drop Bronze
```

---

## Estratégia de carga

### Bronze

- Física e transitória.
- Criada durante a execução.
- Carregada via `COPY FROM STDIN`.
- Removida ao final.

### Silver

- Full refresh.
- Remove e recria as tabelas.
- Consome exclusivamente `bronze.*`.
- Aplica regras intermediárias e tratamento de campos.

### Gold

- Full refresh.
- Remove e recria dimensões e fatos.
- Consome exclusivamente `silver.*`.
- Preserva registros técnicos de dimensão.
- Gera modelo dimensional final.

---

## Modelo Gold final

```text
gold.dim_deputado
gold.dim_orgao
gold.dim_evento
gold.dim_proposicao
gold.dim_votacao

gold.ft_proposicao
gold.ft_voto
gold.ft_despesa
```

Relacionamento lógico:

```text
Silver
  -> Dimensões Gold
      -> Fatos Gold
```

As tabelas fato usam surrogate keys das dimensões, evitando exposição direta dos IDs naturais da origem na camada analítica final.

---

## Principais problemas resolvidos durante o projeto

| Problema | Solução implementada |
|---|---|
| Timeout em cargas grandes | Criação de Bronze física transitória com `COPY FROM STDIN` |
| Dependência de DataFrames em memória | Silver passou a consumir tabelas Bronze físicas no banco |
| Tabelas antigas contaminando novas execuções | Estratégia `DROP + CREATE + INSERT` em Silver e Gold |
| Perda de registros técnicos de dimensão | Registros `-1` e `-3` inseridos no DDL das dimensões Gold |
| Nome físico incorreto entre staging e Bronze | Mapeamento explícito `stg_*_bruto -> bronze.<nome>` |
| Erro de coluna em votação | Correção de `deputado__id` para `deputado_.id` |
| Identificadores grandes em votação | Ajuste de casts para `bigint` e validação com regex |
| Duplicidade na fato despesa | Inclusão de `codDespesa` na Silver e `sk_cod_despesa` na Gold |
| Texto inconsistente | Correção de mojibake, normalização Unicode e uppercase |
| Testes difíceis de isolar | Criação de `test_silver.py` e `test_gold.py` com dependências controladas |

---

## Observações de manutenção

- A ordem dos dicionários `QUERIES_GOLD` e `CREATES_GOLD` é relevante: dimensões devem ser criadas/carregadas antes das fatos.
- A Bronze é transitória; não deve ser tratada como camada histórica.
- A Silver e a Gold são recriadas em full refresh.
- Para evoluir para carga incremental, será necessário implementar chaves únicas e lógica de `UPSERT`, `MERGE` ou `ON CONFLICT` por tabela.
- Ao adicionar uma nova tabela, revise simultaneamente:
  - `config.py`
  - `main.py`, no mapeamento Bronze
  - `pipeline/conversao_tipos.py`
  - `pipeline/creates_silver.py`
  - `pipeline/queries_silver.py`
  - `pipeline/creates_gold.py`, se aplicável
  - `pipeline/queries_gold.py`, se aplicável
  - `test_silver.py` ou `test_gold.py`, se aplicável

---

## Status final

Projeto de ingestão finalizado com sucesso.

Camadas estabilizadas:

```text
Extract/API -> Staging -> Tratamento -> Bronze -> Silver -> Gold
```

Entregas concluídas:

- Pipeline de tratamento após consumo da API.
- Output de bases ajustadas em CSV.
- Orquestrador principal `main.py`.
- Carga Bronze física transitória.
- Carga Silver full refresh.
- Carga Gold dimensional full refresh.
- Testes individuais Silver e Gold.
- Ajustes de queries e grão das tabelas finais.
- Padronização textual em uppercase.
