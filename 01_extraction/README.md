
# 🏛️ Pipeline de Ingestão de Dados Brutos — Câmara dos Deputados

Este repositório contém a arquitetura de Engenharia de Dados responsável por extrair os dados públicos da API de Dados Abertos da Câmara dos Deputados e enviar para o **Supabase**.

Para mitigar as instabilidades crônicas, timeouts e omissões de dados do servidor do governo, dividimos a nossa camada de Ingestão (Staging) em uma estratégia de duas etapas: 
**Extração em Lote** e **Enriquecimento**.



## 🏗️ Desenho da Arquitetura

```text
[Endpoint Geral: /votacoes] ===> (extract.py) ===> Ingestão Rápida ===> [Tabela Supabase]
                                                                            | (Possui NULLs)
                                                                            v
[Endpoint Detalhe: /votacoes/{id}] ===> (enrich_votacoes.py) ===> Update ===> [Dados]
```
O pipeline é composto por dois scripts que trabalham de forma complementar para garantir a integridade dos dados sem comprometer a performance do ecossistema.

## 📝 Scripts Disponíveis 

### Script Principal: `extract.py`

Ele faz chamadas paginadas nos endpoints em lote da API, converte estruturas complexas (listas e dicionários) em strings JSON legíveis e descarrega os dados no Supabase. 

* **Modo de Operação:** Atacado (Baixa volumes massivos em segundos). 
* **Parâmetros Suportados:** 
* `--tabela`: Executa a extração de um alvo específico (Ex: `votacoes`, `deputados`, `proposicoes`). 
* `--teste`: Limita estritamente o número de requisições para validação rápida em ambiente de desenvolvimento. 
* `--data_execucao`: Permite simular que o script está rodando em uma data específica do passado (calculando automaticamente a janela retroativa de 30 dias a partir dela). 

**Exemplo de Execução:** 
```bash
python3 src/extract.py --tabela votacoes
```

### Script de Enriquecimento: `enrich_votacoes.py`

Script satélite focado na qualidade e linhagem dos dados (_Data Quality_). A API da Câmara omite os dados da proposição principal em mais de 60% das votações da listagem geral (especialmente em Comissões permanentes como a CCJC).

Este script realiza uma auditoria em tempo real no Supabase, isola apenas os IDs que sofreram com essa omissão e efetua buscas cirúrgicas no endpoint de detalhe.

-   **Modo de Operação:** Varejo (Cirúrgico, realiza atualizações 1 a 1 direto no banco via SQLAlchemy).
    
-   **Segurança e Linhagem:** Antes de iniciar a correção, o script automaticamente cria uma coluna de auditoria chamada `proposicaoObjeto_original` no banco de dados para salvar uma "foto" de como os dados chegaram da API, garantindo que saibamos o que era `NULL` antes.

**Exemplo de Execução:**

```bash
python3 src/enrich_votacoes.py
``` 

## 🔗 Anatomia das Chamadas na API 

Para compreender a necessidade desta arquitetura, veja como a API da Câmara dos Deputados se comporta nas duas etapas: 

### Chamada em Lote (Feita pelo `extract.py`) 

O script consome a listagem massiva através do endpoint de busca por período: 
* **URL:** `https://dadosabertos.camara.leg.br/api/v2/votacoes?dataInicio=2026-05-15&ordem=ASC&ordenarPor=id` 
* **Retorno Simplificado da API (Exemplo real da votação 1228863-64):** 
```json 
{
  "dados": [
    {
      "id": "1228863-64",
      "uri": "[https://dadosabertos.camara.leg.br/api/v2/votacoes/1228863-64](https://dadosabertos.camara.leg.br/api/v2/votacoes/1228863-64)",
      "descricao": "Rejeitado o Requerimento de desmembramento da PEC 32/2015...",
      "siglaOrgao": "CCJC",
      "proposicaoObjeto": null
    }
  ]
}
```

> ⚠️ **O problema:** O campo `proposicaoObjeto` é devolvido como `null` pela Câmara para economizar largura de banda em votações de comissão.

### Chamada Individual de Enriquecimento (Feita pelo `enrich_votacoes.py`)

Para salvar o dado, o enriquecedor isola o ID e ataca a URL de detalhe individual:

-   **URL:** `https://dadosabertos.camara.leg.br/api/v2/votacoes/1228863-64`
    

**Retorno Detalhado da API:**

```json
{
  "dados": {
    "id": "1228863-64",
    "descricao": "Rejeitado o Requerimento de desmembramento da PEC 32/2015...",
    "proposicoesAfetadas": [
      {
        "id": 1228863,
        "siglaTipo": "PEC",
        "numero": 32,
        "ano": 2015,
        "ementa": "Altera a redação dos artigos 14 e 228 da Constituição Federal..."
      }
    ]
  }
}
```

✨ **A solução:** O script abre as listas internas de `proposicoesAfetadas` ou `objetosPossiveis`, extrai o texto estruturado (`PEC 32/2015`) e injeta na coluna principal via `UPDATE` instantâneo.

## 🛡️ Tratamento de Exceções e Resiliência

O ecossistema foi projetado sob os pilares da resiliência de dados:

-   **Mecanismo de Retry:** Chamadas HTTP possuem tolerância a falhas com até 3 tentativas automáticas e espaçamento de tempo (_backoff_) caso o servidor do governo sofra quedas temporárias.
    
-   **Resiliência a Timeouts (Erros 504):** Se uma requisição expirar no loop noturno, o script registra o aviso em log, pula a linha e avança para a próxima. O dado incompleto permanece como `NULL`.
    
-   **Idempotência de Enriquecimento:** Como o `enrich_votacoes.py` filtra estritamente linhas onde `proposicaoObjeto IS NULL`, ele pode ser executado repetidas vezes. Ele funcionará como um _Checkpoint_, processando apenas o que restou pendente e ignorando o que já foi corrigido.
    
-   **Tratamento de IDs Fantasmas (Erros 404):** A API da Câmara ocasionalmente gera IDs fantasmas em seu listão geral que não existem no servidor de detalhes (retornando Erro 404). O script mapeia esses casos e impede que o pipeline seja interrompido por falhas de terceiros.

## 🚀 Como Executar o Fluxo Completo

1. Garanta que o seu arquivo `.env` na raiz do projeto possui a string de conexão configurada de forma segura:
`SUPABASE_DB_URL=postgresql://postgres.suachave...`

2. Execute a extração massiva dos dados:
`python3 src/extract.py --tabela votacoes`

3. Execute o enriquecedor para limpar as omissões e carimbar a coluna de auditoria histórica:
`python3 src/enrich_votacoes.py`


