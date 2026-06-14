SELECT
    dp.id_proposicao,
    dp.sg_tipo_proposicao,
    dp.ds_tipo_proposicao,
    dp.ds_situacao,
    dp.ds_tema_classificado,
    ROUND(CAST(dp.nr_score_similaridade * 100 AS numeric), 1) AS score_pct,
    dp.ds_resumo_executivo,
    TO_DATE(fp.sk_data_proposicao::TEXT, 'YYYYMMDD') AS dt_apresentacao,
    ddep.nm_deputado,
    ddep.sg_partido,
    ddep.sg_uf,
    fp.qtd_proposicao,
    dp.dh_ingestao
FROM gold.ft_proposicao fp
JOIN gold.dim_proposicao dp
  ON fp.sk_proposicao = dp.sk_proposicao
JOIN gold.dim_deputado ddep
  ON fp.sk_deputado = ddep.sk_deputado
 WHERE
       TO_DATE(fp.sk_data_proposicao::TEXT, 'YYYYMMDD') >= CURRENT_DATE - INTERVAL '23 days' --| pega a data da última proposição - 7 dias
   AND TO_DATE(fp.sk_data_proposicao::TEXT, 'YYYYMMDD') <  CURRENT_DATE - INTERVAL '16 days' --| data da última proposição
   AND dp.sg_tipo_proposicao IN ('PL', 'PEC', 'PLP')
   AND dp.ds_tema_classificado <> 'NÃO CLASSIFICADO' 
 ORDER BY
     dp.nr_score_similaridade DESC,
     TO_DATE(fp.sk_data_proposicao::TEXT, 'YYYYMMDD') DESC
 LIMIT 5;