
# Datas e valores do contrato

## Objetivo

Extrair as datas e os valores financeiros da
operação de debêntures.

## Campos necessários

- Data de emissão
- Data de vencimento da primeira série
- Valor máximo total da emissão
- Valor nominal unitário
- Quantidade máxima de debêntures
- Moeda

## Regras obrigatórias

1. Caso existam várias séries, utilizar somente a
   data de vencimento da Primeira Série.

2. Não confundir data da escritura, data de registro
   na Junta Comercial ou data de integralização
   com a data de emissão.

3. Todas as datas devem utilizar YYYY-MM-DD.

4. Valores monetários devem ser números, sem R$
   e sem separadores de milhar.

5. Valores devem manter suas unidades originais.

6. O valor máximo total da emissão não corresponde
   necessariamente ao valor distribuído na
   Primeira Série.

7. Não atribuir o valor total da emissão à
   Primeira Série sem previsão contratual expressa.

8. Se a informação não estiver disponível,
   retornar null.

9. Não deve buscar nenhum campo desnecessário,
   deve buscar apenas os campos solicitados no formato exemplificado.

## Exemplos

Data:

"Data de Emissão: 15 de dezembro de 2024"

Resultado:
"data_emissao": "2024-12-15"

Vencimento:

"Primeira Série: 15 de dezembro de 2029.
Segunda Série: 15 de dezembro de 2031."

Resultado:
"data_vencimento": "2029-12-15"

Valor da emissão:

"O valor total da emissão será de até
R$ 140.000.000,00."

Resultado:
"valor_total_emissao_maximo": 140000000.0

Valor nominal:

"O Valor Nominal Unitário será de R$ 1.000,00."

Resultado:
"valor_nominal_unitario": 1000.0

Quantidade:

"Serão emitidas até 140.000 Debêntures."

Resultado:
"quantidade_maxima_debentures": 140000

## Recuperação complementar

Quando houver dados ausentes, consultar cláusulas
sobre características da emissão, datas,
vencimento, valor nominal e quantidade.

Utilizar expressões contratuais específicas.

Não procurar datas de outras séries para substituir
datas ausentes da Primeira Série.

## Formato da resposta

O campo data deve conter:

- data_emissao: YYYY-MM-DD ou null
- data_vencimento: YYYY-MM-DD ou null
- valor_total_emissao_maximo: número ou null
- valor_nominal_unitario: número ou null
- quantidade_maxima_debentures: inteiro ou null
- moeda: string ou null

Informar também needs_more_context, search_query,
missing_fields e sources.

Não adicionar campos fora do schema JSON fornecido.