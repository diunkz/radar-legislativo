# Modelo de Dados (Camadas Silver e Gold)

Esta pasta contém os scripts SQL e os diagramas usados na modelagem do star schema para análise de atividade legislativa da Câmara dos Deputados.

## Estrutura

```text
data-model/
  ├─ silver/
  │   └─ ch01_cria_tabelas_silver.sql  
  ├─ gold/
  │   └─ ch01_cria_tabelas_gold.sql  
  └─ docs/
      ├─ silver_model.png
      ├─ gold_model.png
      ├─ ch01_coleta_dados_silver.sql
      └─ ch01_coleta_dados_gold.sql
```

### 1. Camada Silver (tabelas tratadas)

Scripts em `data-model/silver/`:

- `ch01_cria_tabelas_silver.sql`  
  Cria as tabelas tratadas com dados da API da Câmara:
  - `silver.deputado`
  - `silver.orgao`
  - `silver.evento`
  - `silver.proposicao`
  - `silver.votacao`
  - `silver.despesa`

### 2. Camada Gold (modelo dimensional)

Scripts em `data-model/gold/`:

- `ch01_cria_tabelas_gold.sql`  
  Cria o modelo dimensional com esquema estrela:

  **Dimensões**
  - `gold.dim_deputado`
  - `gold.dim_orgao`
  - `gold.dim_evento`
  - `gold.dim_proposicao`
  - `gold.dim_votacao`
  - `gold.dim_data` (gerada separadamente, não está neste script)

  **Fatos**
  - `gold.ft_proposicao`  
    - Grão: 1 linha por proposição  
    - Métrica: `qtd_proposicao = 1`  
  - `gold.ft_voto`  
    - Grão: 1 linha por voto de deputado em uma votação  
    - Métrica: `qtd_voto = 1`  
    - `tp_voto` é tratado como dimensão degenerada  
  - `gold.ft_despesa`  
    - Grão: 1 linha por despesa de deputado por data/tipo  
    - Métricas: `vl_bruto`, `vl_liquido`, `vl_glosa`

### 3. Scripts Auxiliares

Em `data-model/docs/`:

- `ch01_coleta_dados_silver.sql`  
  Script auxiliar, utilizado para popular as tabelas silver a partir das tabelas de staging via python.
- `ch01_coleta_dados_gold.sql`  
  Script auxiliar, utilizado para popular as tabelas gold a partir das tabelas de staging via python.

### 4. Diagramas

Em `data-model/docs/`:

- `modelo_logico_silver.png`  
  Modelo lógico da camada silver, com as tabelas:
  - DEPUTADO, EVENTO, ORGAO, DESPESAS, VOTACAO, PROPOSICAO.

- `modelo_dimensional_gold.png`  
  Esquema estrela com:
  - Fatos: `FATO_PROPOSICAO`, `FATO_VOTO`, `FATO_DESPESA`;
  - Dimensões: `DIM_DEPUTADO`, `DIM_ORGAO`, `DIM_EVENTO`, `DIM_PROPOSICAO`, `DIM_VOTACAO`, `DIM_DATA` (apresentada no diagrama, mas será gerada em outra camada quando necessário)

### 5. Como executar

1. Criar as tabelas silver:

   ```sql
   \i data-model/silver/ch01_cria_tabelas_silver.sql;
   ```

2. Criar as tabelas gold (dimensional):

   ```sql
   \i data-model/gold/ch01_cria_tabelas_gold.sql;
   ```

> Observação: 
> - as tabelas de staging (`stg_*_bruto`) foram previamente carregadas com os dados da API da Câmara dos Deputados.
> - Os scripts auxiliares de coleta de dados (`ch01_coleta_dados_silver.sql` e `ch01_coleta_dados_gold.sql`) foram utilizados para auxiliar a carga das tabelas via python, não serão executados.