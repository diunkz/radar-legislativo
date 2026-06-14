# Radar Legislativo — Pipeline de Dados

Projeto de engenharia de dados para ingestão, tratamento, organização e disponibilização analítica de dados legislativos consumidos da API da Câmara dos Deputados.

O pipeline foi estruturado em camadas, seguindo uma arquitetura próxima ao modelo **Medallion Architecture**:

```text
API Câmara dos Deputados
        ↓
Extract / Staging
        ↓
Tratamento em memória com Pandas
        ↓
Bronze física transitória — Supabase/PostgreSQL
        ↓
Silver — dados tratados e modelados
        ↓
Gold — dimensões e fatos analíticos
        ↓
Consumo analítico / BI / IA
```

---

## 1. Objetivo do Projeto

O objetivo do projeto é estruturar uma base legislativa confiável, tratada e pronta para análises, contemplando dados de deputados, proposições, despesas, votações, votos, eventos, frentes, lideranças, partidos, órgãos e legislaturas.

A etapa atual do projeto tem foco em:

- ingestão dos dados vindos da API;
- padronização e tratamento das tabelas staging;
- criação de camada Bronze física transitória;
- carga das camadas Silver e Gold;
- testes individuais das camadas Silver e Gold;
- preservação de tabelas analíticas complementares geradas por IA.

---

## 2. Estrutura Geral do Fluxo

### 2.1 Extract / Staging

A etapa de extração é responsável pelo consumo da API da Câmara dos Deputados e geração das tabelas staging brutas.

Arquivo principal relacionado:

```text
src/extract.py
```

Essa etapa foi desenvolvida para consumir os dados externos e disponibilizá-los em tabelas staging, mantendo o dado em estado próximo ao bruto para posterior tratamento.

---

### 2.2 Tratamento em Memória

Após a leitura das tabelas staging, o pipeline realiza tratamento em memória utilizando Pandas.

Principais etapas:

- leitura das tabelas staging;
- inspeção de tipos;
- conversão de tipos;
- correção de acentuação;
- remoção de duplicatas;
- exportação opcional dos dados tratados em CSV.

Arquivos principais:

```text
pipeline/leitura.py
pipeline/inspecao.py
pipeline/conversao.py
pipeline/correcao_texto.py
pipeline/deduplicacao.py
pipeline/exportacao.py
```

---

### 2.3 Bronze Física Transitória

A camada Bronze passou a ser carregada fisicamente no Supabase/PostgreSQL, em vez de permanecer somente em memória.

Essa alteração foi necessária para reduzir risco de timeout e melhorar a estabilidade do processamento, especialmente em tabelas com maior volume de registros.

A estratégia adotada foi:

1. tratar os dados staging em memória;
2. carregar os DataFrames tratados para o schema `bronze`;
3. usar a Bronze como fonte para a Silver;
4. remover a Bronze ao final do pipeline.

Arquivo principal:

```text
pipeline/carga_bronze.py
```

A Bronze é considerada **transitória**, ou seja, não é camada final de consumo.

---

### 2.4 Silver

A camada Silver consolida dados tratados, padronizados e ajustados ao modelo relacional do projeto.

Arquivo principal:

```text
pipeline/carga_silver.py
pipeline/queries_silver.py
```

Exemplo de alteração importante realizada na camada Silver:

- inclusão da coluna `codDespesa` na modelagem de despesas, necessária para aderência ao modelo de dados recebido de outro engenheiro.

A Silver é a principal camada intermediária para consumo da Gold.

---

### 2.5 Gold

A camada Gold organiza os dados em estruturas analíticas, como dimensões e fatos.

Arquivos principais:

```text
pipeline/carga_gold.py
pipeline/queries_gold.py
```

A camada Gold é voltada para consumo analítico, relatórios, dashboards e futuras integrações com modelos de IA.

---

## 3. Orquestrador Principal

O arquivo `main.py` é o orquestrador ponta a ponta do pipeline.

Responsabilidades principais:

- conectar ao Supabase/PostgreSQL;
- preparar o ambiente inicial;
- tratar as tabelas staging;
- carregar a Bronze física transitória;
- carregar a Silver;
- carregar a Gold;
- remover a Bronze ao final;
- registrar resumo da execução.

Arquivo:

```text
main.py
```

Execução:

```bash
python main.py
```

---

## 4. Estratégia de Refresh

A estratégia principal do projeto é:

```text
FULL REFRESH
```

Ou seja, a cada execução o pipeline recria as camadas controladas pelo processo.

Fluxo resumido:

1. remover objetos controlados dos schemas `bronze`, `silver` e `gold`;
2. recriar a Bronze física transitória;
3. recriar tabelas Silver;
4. recriar tabelas Gold;
5. remover a Bronze ao final.

---

## 5. Atualização Recente — Preservação de Tabelas `_ia` na Silver

Foi adicionada uma regra especial no `main.py` para preservar tabelas com sufixo `_ia` dentro do schema `silver`.

Motivo da alteração:

- a tabela `silver.proposicoes_ia` é criada em outra etapa do projeto;
- essa etapa é mantida por outro engenheiro;
- o pipeline principal não deve apagar essa tabela durante o refresh;
- a Gold pode depender dessa tabela para enriquecimento analítico.

Antes da alteração, o pipeline executava:

```sql
DROP SCHEMA IF EXISTS "silver" CASCADE;
```

Esse comando removia o schema inteiro, apagando também:

```text
silver.proposicoes_ia
```

Com a alteração, o schema `silver` passou a ser limpo seletivamente.

Comportamento atual:

| Schema | Comportamento |
|---|---|
| `bronze` | Drop completo do schema |
| `silver` | Remove objetos do schema, mas preserva objetos terminados em `_ia` |
| `gold` | Drop completo do schema |

Configuração adicionada ao `main.py`:

```python
SCHEMAS_COM_TABELAS_IA_PRESERVADAS = {
    "silver",
}
```

A função `dropar_schema` agora trata o schema `silver` como exceção e chama uma rotina específica para preservar objetos com sufixo `_ia`.

---

## 6. Atualização Recente — Ajuste da Gold `dim_proposicao`

Durante o teste individual da camada Gold, a tabela `gold.dim_proposicao` apresentou erro de `NOT NULL` na coluna:

```text
ds_tema_classificado
```

O erro ocorreu porque a carga faz `LEFT JOIN` com a tabela `silver.proposicoes_ia`.

Como nem todas as proposições possuem enriquecimento de IA, algumas colunas retornavam `NULL`, causando falha no insert da Gold.

Consulta original com risco de erro:

```sql
UPPER("tema_classificado") AS "ds_tema_classificado",
"score_similaridade" AS "nr_score_similaridade",
UPPER("resumo_executivo") AS "ds_resumo_executivo"
```

Correção recomendada:

```sql
COALESCE(
    NULLIF(UPPER(TRIM(ia."tema_classificado")), ''),
    'NÃO CLASSIFICADO'
) AS "ds_tema_classificado",

COALESCE(
    ia."score_similaridade",
    0
) AS "nr_score_similaridade",

COALESCE(
    NULLIF(UPPER(TRIM(ia."resumo_executivo")), ''),
    'SEM RESUMO EXECUTIVO GERADO'
) AS "ds_resumo_executivo"
```

Com essa alteração, a Gold passa a aceitar proposições que ainda não foram processadas pela etapa de IA, mantendo valores padrão controlados.

Valores padrão adotados:

| Campo | Valor padrão |
|---|---|
| `ds_tema_classificado` | `NÃO CLASSIFICADO` |
| `nr_score_similaridade` | `0` |
| `ds_resumo_executivo` | `SEM RESUMO EXECUTIVO GERADO` |

Recomendação: manter as colunas como `NOT NULL` na Gold, pois a dimensão analítica deve evitar campos nulos em atributos de classificação.

---

## 7. Testes Individuais

Foram criados arquivos específicos para testes isolados das camadas Silver e Gold.

Arquivos:

```text
test_silver.py
test_gold.py
```

### 7.1 Teste da Silver

Objetivo:

- executar uma tabela Silver específica;
- validar dependências da Bronze;
- facilitar depuração sem rodar o pipeline completo.

Execução:

```bash
python test_silver.py
```

---

### 7.2 Teste da Gold

Objetivo:

- executar uma tabela Gold específica;
- validar dependências da Silver;
- testar dimensões ou fatos individualmente;
- facilitar correções pontuais em `queries_gold.py`.

Execução:

```bash
python test_gold.py
```

Exemplo recente validado:

```text
gold.dim_proposicao
```

Dependência principal:

```text
silver.proposicao
```

Dependência complementar de IA:

```text
silver.proposicoes_ia
```

---

## 8. Principais Arquivos do Projeto

```text
.
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
│   ├── correcao_texto.py
│   ├── deduplicacao.py
│   ├── exportacao.py
│   ├── carga_bronze.py
│   ├── carga_silver.py
│   ├── carga_gold.py
│   ├── drop_bronze.py
│   ├── queries_silver.py
│   └── queries_gold.py
└── src/
    └── extract.py
```

---

## 9. Variáveis de Ambiente

O projeto depende de configuração de conexão com o banco Supabase/PostgreSQL.

Exemplo esperado no `.env`:

```env
SUPABASE_URL=...
SUPABASE_KEY=...
DB_URI_DDL=postgresql+psycopg2://usuario:senha@host:porta/database
```

A variável mais crítica para execução das cargas via SQLAlchemy é:

```text
DB_URI_DDL
```

Ela deve permitir operações DDL e DML, como:

- `CREATE SCHEMA`;
- `DROP SCHEMA`;
- `CREATE TABLE`;
- `DROP TABLE`;
- `INSERT INTO`;
- `COPY` ou carga equivalente.

---

## 10. Ordem Recomendada de Execução

### 10.1 Execução completa

```bash
python main.py
```

### 10.2 Testar apenas Silver

```bash
python test_silver.py
```

### 10.3 Testar apenas Gold

```bash
python test_gold.py
```

---

## 11. Boas Práticas Adotadas

- Separação clara entre camadas Staging, Bronze, Silver e Gold.
- Bronze física transitória para reduzir timeout e melhorar controle de carga.
- Uso de orquestrador único para execução ponta a ponta.
- Testes individuais para Silver e Gold.
- Mapeamento explícito entre staging e Bronze.
- Preservação de tabelas `_ia` criadas fora do pipeline principal.
- Uso de valores padrão controlados para evitar nulos em dimensões analíticas.
- Logs detalhados para auditoria e depuração.

---

## 12. Histórico de Alterações Relevantes

### 12.1 Bronze Física Transitória

Alteração realizada para evitar problemas de timeout no Supabase/PostgreSQL.

Antes:

```text
Staging tratada em memória → múltiplas cargas intermediárias
```

Depois:

```text
Staging tratada → Bronze física transitória → Silver → Gold → Drop Bronze
```

---

### 12.2 Preservação da Tabela `silver.proposicoes_ia`

Alteração realizada no `main.py` para impedir que a tabela de IA seja apagada durante o refresh da Silver.

Regra atual:

```text
Todo objeto terminado em _ia no schema silver deve ser preservado.
```

Exemplo preservado:

```text
silver.proposicoes_ia
```

---

### 12.3 Ajuste da `gold.dim_proposicao`

Alteração recomendada em `queries_gold.py` para tratar ausência de classificação por IA.

Problema corrigido:

```text
psycopg2.errors.NotNullViolation: null value in column "ds_tema_classificado"
```

Solução:

```text
Aplicar COALESCE nas colunas vindas de silver.proposicoes_ia.
```

---

## 13. Responsabilidades Desenvolvidas Nesta Etapa

As etapas integralmente desenvolvidas nesta fase foram:

- pipeline após consumo da API realizado na `extract.py` da pasta `src`;
- geração de output com dados tratados após consumo das tabelas staging da API;
- orquestrador principal `main.py`;
- criação e ajuste dos testes individuais `test_silver.py` e `test_gold.py`;
- ajustes para estabilidade do pipeline com Bronze física transitória;
- ajuste do `main.py` para preservação de tabelas `_ia` no schema Silver;
- ajuste recomendado para a Gold consumir dados de IA sem quebrar em registros ainda não classificados.

Alterações relacionadas ao modelo de dados recebido de outro engenheiro foram incorporadas conforme necessidade do pipeline, como a inclusão de colunas específicas na Silver e o consumo da tabela `silver.proposicoes_ia` na Gold.

---

## 14. Status Atual

```text
Etapa de ingestão de dados do projeto: finalizada.
Pipeline principal: funcional com Bronze transitória.
Silver: carregada a partir da Bronze.
Gold: em validação incremental por tabela.
Integração com IA: preservada por regra no schema Silver.
```

---

## 15. Próximos Pontos de Atenção

- Validar se todas as queries da Gold tratam corretamente valores nulos vindos de tabelas complementares.
- Revisar se outras tabelas analíticas externas também devem seguir o padrão `_ia`.
- Garantir que `silver.proposicoes_ia` possua chave compatível com `silver.proposicao`.
- Validar duplicidade em joins da Gold caso a tabela de IA tenha mais de um registro por proposição.
- Avaliar criação de constraints ou índices na tabela `silver.proposicoes_ia`, especialmente sobre `proposicao_id`.

---

## 16. Observação Final

Este README documenta a fase atual do projeto Radar Legislativo, com foco na consolidação do pipeline de ingestão, tratamento, carga Bronze/Silver/Gold e integração com a tabela complementar de IA.

A principal decisão arquitetural recente foi preservar objetos `_ia` no schema Silver, permitindo que o pipeline principal continue em estratégia de `FULL REFRESH` sem apagar entregas mantidas por etapas externas do projeto.
