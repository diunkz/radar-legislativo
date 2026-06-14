# Automação com n8n

O workflow `n8n/wf_radar_legislativo_top_proposicoes_semanais.json` executa semanalmente às **06h** e envia por e-mail as **top 5 proposições mais relevantes** consultando diretamente a camada **gold**.

1. Consulta a tabela `gold.ft_proposicao` junto com `gold.dim_proposicao` e `gold.dim_deputado`
2. Filtra proposições dos tipos `PL`, `PEC` e `PLP`
3. Considera apenas proposições com tema já classificado pela IA
4. Ordena pelo `nr_score_similaridade` em ordem decrescente
5. Consolida os registros com o nó `Aggregate`
6. Monta o e-mail em HTML com os dados retornados
7. Envia a mensagem para os destinatários configurados no Gmail

## Documentação
Em `automation/docs/`:

- `n8n_workflow.png`  
  Print do workflow no n8n.

- `dc01_coleta_proposicoes_n8n.sql`
  Query SQL utilizada para buscar os dados das proposições mais relevantes.

- `dc01_formata_email_n8n.html`
  Código html utilizado para formatar o e-mail.

## Como executar

1. Abra o n8n
2. Clique em `Import from file`
3. Selecione o arquivo `n8n/wf_radar_legislativo_top_proposicoes_semanais.json`
4. Configure as credenciais de Postgres e Gmail
5. Revise a query SQL, se necessário
6. Ative o workflow