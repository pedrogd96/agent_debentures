
# Metodologia e tabela de amortização

## Objetivo

Identificar como o principal das debêntures da
Primeira Série será amortizado.

## Campos necessários

- Metodologia de amortização
- Datas das parcelas
- Percentual de cada parcela
- Base de incidência de cada percentual

## Regras obrigatórias

1. Considerar somente a Primeira Série.

2. Não utilizar parcelas de amortização da
   Segunda Série ou de outras séries.

3. Diferenciar amortização do principal de
   pagamento de juros remuneratórios.

4. Todas as datas devem utilizar YYYY-MM-DD.

5. Percentuais devem ser numéricos na escala
   de 0 a 100.

6. Se o contrato informar amortização única
   no vencimento, retornar uma parcela
   correspondente a 100% do principal.

7. Se a amortização ocorrer em parcelas,
   preservar todas as datas encontradas.

8. Diferenciar percentuais aplicados ao valor
   nominal original de percentuais aplicados
   ao saldo remanescente.

9. Não somar percentuais de bases diferentes
   como se fossem equivalentes.

10. Não criar datas ou parcelas não previstas
    expressamente na escritura.

11. Se a tabela não estiver disponível,
    solicitar nova recuperação semântica.

12. Se, após as buscas, não for possível
    identificar as parcelas, retornar uma
    lista vazia e registrar o campo ausente.

13. Não deve buscar nenhum campo desnecessário,
   deve buscar apenas os campos solicitados no formato exemplificado.

## Exemplos

Exemplo 1 — Amortização única:

"O Valor Nominal Unitário das Debêntures
da Primeira Série será amortizado em parcela
única na Data de Vencimento, em 15/12/2029."

Resultado:

{
  "metodologia_amortizacao": "Parcela única no vencimento",
  "parcelas_amortizacao": [
    {
      "data": "2029-12-15",
      "percentual": 100.0,
      "base": "Valor Nominal Unitário"
    }
  ]
}

Exemplo 2 — Duas parcelas:

"50% do Valor Nominal Unitário em 15/12/2030
e 100% do saldo remanescente em 15/12/2031."

Resultado:

{
  "metodologia_amortizacao": "Duas parcelas",
  "parcelas_amortizacao": [
    {
      "data": "2030-12-15",
      "percentual": 50.0,
      "base": "Valor Nominal Unitário"
    },
    {
      "data": "2031-12-15",
      "percentual": 100.0,
      "base": "Saldo remanescente"
    }
  ]
}

O segundo exemplo demonstra a interpretação
dos percentuais, mas seus dados não devem ser
utilizados para outra série.

Exemplo 3 — Múltiplas séries:

"Primeira Série: amortização única em 2029.
Segunda Série: amortizações em 2030 e 2031."

Selecionar apenas a amortização da Primeira Série.

## Recuperação complementar

Quando a metodologia ou as parcelas não estiverem
claras, consultar cláusulas sobre:

- Amortização da Primeira Série
- Amortização do Valor Nominal Unitário
- Cronograma de amortização
- Percentuais de amortização
- Saldo do Valor Nominal Unitário
- Pagamento do principal

## Formato da resposta

O campo data deve conter:

- metodologia_amortizacao: string ou null
- parcelas_amortizacao: lista de objetos

Cada parcela deve conter:

- data: YYYY-MM-DD
- percentual: número
- base: string

Informar também needs_more_context, search_query,
missing_fields e sources.

Não adicionar campos fora do schema JSON fornecido.