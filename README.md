## Etapa 4 — Camada de IA

Módulo de enriquecimento automático das proposições legislativas com **classificação temática**, **geração de embeddings** e **resumos executivos**, utilizando exclusivamente modelos open source e APIs gratuitas.

---

### Visão geral

Após a carga das proposições no banco, esta etapa adiciona três camadas de inteligência à tabela `stg_proposicoes_bruto`, gravando os resultados em uma nova tabela `proposicoes_ia`:

| Caminho | O que faz | Modelo | Infraestrutura |
|---------|-----------|--------|----------------|
| A | Classifica cada proposição em um dos 10 temas e gera o vetor semântico | `intfloat/multilingual-e5-large` | Local (CPU/GPU) |
| B — Bulk | Resumo executivo de até 3 frases para o histórico completo | `qwen2.5:14b` via Ollama | Local (GPU) |
| B — Incremental | Resumo executivo para novas proposições com maior qualidade | `llama-3.3-70b-versatile` via Groq | API gratuita |

---

### Tabela de saída

Criada automaticamente na primeira execução.

```sql
CREATE TABLE proposicoes_ia (
    proposicao_id       INTEGER          PRIMARY KEY,  -- referência a stg_proposicoes_bruto.id
    tema_classificado   TEXT,                          -- ex: "Tecnologia"
    score_similaridade  FLOAT,                         -- similaridade de cosseno (0.0 a 1.0)
    embedding           vector(1024),                  -- vetor semântico (pgvector)
    resumo_executivo    TEXT,                          -- resumo gerado pelo LLM
    processado_em       TIMESTAMPTZ
);
```

> A coluna `embedding` requer a extensão `pgvector` habilitada no Supabase.  
> Para habilitar: `CREATE EXTENSION IF NOT EXISTS vector;`
>
> Se a tabela já existir sem a coluna `embedding`:  
> `ALTER TABLE proposicoes_ia ADD COLUMN IF NOT EXISTS embedding vector(1024);`

---

### Temas classificados

`Saúde · Tributário · Trabalho · Tecnologia · Meio Ambiente · Educação · Segurança Pública · Infraestrutura · Economia · Direitos Sociais`

A classificação usa similaridade de cosseno entre o embedding da ementa (prefixo `query:`) e embeddings de descrições ricas de cada tema (prefixo `passage:`). O modelo `multilingual-e5-large` exige esses prefixos para funcionar corretamente — sem eles a qualidade da similaridade cai significativamente.

---

### Estratégia de resumos

**Bulk** — processa o histórico completo com o modelo local `qwen2.5:14b` via Ollama. Roda na GPU (recomendado: 8GB+ VRAM), sem limite de tokens e sem custo de API. As chamadas são paralelizadas com 3 workers simultâneos para aproveitar a GPU ao máximo.

**Incremental** — novas proposições são processadas com `llama-3.3-70b-versatile` via Groq, modelo de maior qualidade reservado para o volume menor do dia a dia.

Quando há `ementaDetalhada` disponível, ela é passada ao modelo junto com a ementa curta para um resumo mais preciso. Caso contrário, usa apenas a ementa.

**Cadeia de fallback da Groq** — ao atingir o limite diário de tokens de um modelo, o pipeline faz fallback automático para o próximo sem intervenção manual:

```
llama-3.3-70b-versatile  (100k tokens/dia)
        ↓ limite atingido
llama-3.1-8b-instant     (500k tokens/dia)
        ↓ limite atingido
mixtral-8x7b-32768       (500k tokens/dia)
        ↓ limite atingido
pipeline interrompido — retoma amanhã após reset (00:00 UTC)
```

---

### Salvamento incremental por lote

O pipeline processa e **salva no banco a cada lote de 50 proposições** (configurável). Interrupções — por limite de tokens, queda de rede ou qualquer outro erro — não causam perda de dados. Os lotes já salvos são pulados automaticamente na próxima execução.

```
lote 1 (50)  →  classifica + embedding + resume  →  salva ✓
lote 2 (50)  →  classifica + embedding + resume  →  salva ✓
lote N (50)  →  interrompido
                      ↓
próxima execução: retoma do lote N automaticamente
```

O `db.py` monta o SQL de upsert **dinamicamente** com base nas colunas presentes no DataFrame — permitindo rodar `--apenas-embeddings` ou `--apenas-resumos` sem erros de coluna ausente. Em caso de falha de conexão com o Supabase, há retry automático com 3 tentativas (espera de 5s, 10s e 15s entre elas).

---

### Estrutura de arquivos

```
etapa4/
├── config.py        # parâmetros globais: modelo, dimensão, temas, rate limit
├── db.py            # leitura de stg_proposicoes_bruto, upsert dinâmico em proposicoes_ia
├── embeddings.py    # Caminho A: embeddings + similaridade de cosseno
├── resumos.py       # Caminho B: resumos paralelos via Ollama ou Groq com fallback
├── main.py          # orquestrador com CLI e salvamento por lote
├── requirements.txt
└── env.example
```

---

### Pré-requisitos

**Ollama** (para o modo bulk)
- Instale em [ollama.com/download](https://ollama.com/download)
- Baixe o modelo: `ollama pull qwen2.5:14b`
- Recomendado: GPU com 8GB+ VRAM (testado em RTX 3060 12GB)

**pgvector** (extensão do Supabase)
```sql
-- Rode no SQL Editor do Supabase
CREATE EXTENSION IF NOT EXISTS vector;
```

---

### Instalação

```bash
pip install -r /requirements.txt
```

> O modelo `multilingual-e5-large` (~1.1GB) é baixado automaticamente na primeira execução via cache do HuggingFace. Nas execuções seguintes é carregado do disco.

---

### Configuração

Copie o arquivo de exemplo e preencha as credenciais:

```bash
cp etapa4/env.example etapa4/.env
```

| Variável | Onde obter |
|----------|------------|
| `DATABASE_URL` | Supabase → Project Settings → Database → URI |
| `GROQ_API_KEY` | [console.groq.com/keys](https://console.groq.com/keys) — necessário apenas para o modo incremental |

---

### Execução

```bash
# Teste inicial (recomendado antes de rodar tudo)
python main.py --limite 10

# Bulk completo — histórico via Ollama local
python main.py

# Incremental — novas proposições via Groq
python main.py --incremental

# Reprocessar tudo do zero
python main.py --reprocessar

# Rodar apenas um dos caminhos
python main.py --apenas-embeddings
python main.py --apenas-resumos

# Ajustar tamanho do lote (padrão: 50)
python main.py --tamanho-lote 100
```

O pipeline é **incremental por padrão**: processa apenas proposições sem registro em `proposicoes_ia`. Interrupções não causam retrabalho.

---

### Consultando os resultados

```sql
-- Distribuição por tema
SELECT tema_classificado, COUNT(*) AS total
FROM   proposicoes_ia
GROUP  BY tema_classificado
ORDER  BY total DESC;

-- Proposições de Tecnologia com maior score de confiança
SELECT p.ementa, ia.score_similaridade, ia.resumo_executivo
FROM   proposicoes_ia ia
JOIN   stg_proposicoes_bruto p ON p.id = ia.proposicao_id
WHERE  ia.tema_classificado = 'Tecnologia'
ORDER  BY ia.score_similaridade DESC
LIMIT  10;

-- Busca semântica por similaridade (requer pgvector)
-- Substitua [...] pelo embedding do texto de busca
SELECT p.ementa, ia.tema_classificado, ia.resumo_executivo,
       1 - (ia.embedding <=> '[...]'::vector) AS similaridade
FROM   proposicoes_ia ia
JOIN   stg_proposicoes_bruto p ON p.id = ia.proposicao_id
ORDER  BY ia.embedding <=> '[...]'::vector
LIMIT  10;

-- Proposições ainda não processadas
SELECT COUNT(*)
FROM   stg_proposicoes_bruto p
LEFT   JOIN proposicoes_ia ia ON ia.proposicao_id = p.id
WHERE  ia.proposicao_id IS NULL;
```