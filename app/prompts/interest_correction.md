
# Juros e correção monetária

## Objetivo

Extrair a metodologia de remuneração das debêntures
da Primeira Série.

## Informações necessárias

- Existência de correção monetária
- Índice de correção monetária
- Indexador de juros
- Percentual aplicado ao indexador
- Spread anual
- Base de dias úteis
- Regime de capitalização
- Metodologia de cálculo
- Fórmula dos juros
- Periodicidade de pagamento

## Regras obrigatórias

1. Extrair exclusivamente os parâmetros
   remuneratórios da Primeira Série.

2. Não confundir correção monetária com juros
   pós-fixados vinculados à Taxa DI ou CDI.

3. Quando a escritura indicar ausência de
   atualização monetária, utilizar false no
   campo possui_correcao_monetaria.

4. Percentuais devem estar na escala percentual:

   100% = 100.0
   95% = 95.0
   0,95% = 0.95
   1,10% = 1.10

5. Não converter 100% do CDI para 1.0.

6. Preservar as diferenças entre taxa prefixada,
   indexador pós-fixado e spread adicional.

7. Registrar a base de cálculo informada na
   escritura, como 252 dias úteis.

8. Não inferir capitalização composta apenas
   pela presença de CDI.

9. Preservar a metodologia de cálculo descrita
   contratualmente.

10. Não calcular juros nem consultar taxas de mercado.

11. Se a fórmula estiver ausente, solicitar nova
    recuperação antes de concluir que não existe.

12. Usar null quando um campo não estiver disponível.

## Exemplos

Exemplo 1 — CDI + spread:

"Sobre o Valor Nominal Unitário das Debêntures
da Primeira Série incidirão juros equivalentes
a 100% das Taxas DI, acrescidos de spread
de 0,95% ao ano, base 252 dias úteis."

Resultado:

{
  "indexador": "CDI",
  "percentual_indexador": 100.0,
  "spread_anual_percentual": 0.95,
  "base_dias_uteis": 252
}

Exemplo 2 — Sem correção monetária:

"O Valor Nominal Unitário não será atualizado
monetariamente."

Resultado:

{
  "possui_correcao_monetaria": false,
  "indice_correcao": null
}

Exemplo 3 — Capitalização:

"A remuneração será calculada de forma exponencial
e cumulativa pro rata temporis por dias úteis,
em regime de capitalização composta."

Resultado:

{
  "capitalizacao": "Composta",
  "metodologia_juros": "Exponencial e cumulativa pro rata temporis por dias úteis"
}

Exemplo 4 — Fórmula:

"J = VNe x (Fator Juros - 1)"

Resultado:

{
  "formula_juros": "J = VNe x (Fator Juros - 1)"
}

Exemplo 5 — Séries diferentes:

"Primeira Série: 100% do CDI + 0,95% a.a.
Segunda Série: 100% do CDI + 1,10% a.a."

O spread selecionado deve ser 0.95.

## Recuperação complementar

Quando as cláusulas recuperadas não forem
suficientes, buscar especialmente:

- Remuneração da Primeira Série
- Atualização monetária
- Taxa DI ou CDI
- Fórmula dos juros remuneratórios
- Fator DI e Fator Spread
- Capitalização composta
- Pagamento da remuneração

Não utilizar a taxa de outra série.

## Formato da resposta

O campo data deve conter:

- possui_correcao_monetaria: boolean ou null
- indice_correcao: string ou null
- indexador: string ou null
- percentual_indexador: número ou null
- spread_anual_percentual: número ou null
- base_dias_uteis: inteiro ou null
- capitalizacao: string ou null
- metodologia_juros: string ou null
- formula_juros: string ou null
- periodicidade_juros: string ou null

Informar também needs_more_context, search_query,
missing_fields e sources.

Não adicionar campos fora do schema JSON fornecido.