
# Identificação do contrato

## Objetivo

Identificar a empresa emissora das debêntures,
seu CNPJ e a série que será processada.

## Regras obrigatórias

1. Buscar a identificação da emissora no preâmbulo
   ou nas cláusulas de identificação das partes.

2. A emissora é a empresa que emite as debêntures.
   Não confundir com agente fiduciário, coordenador,
   escriturador, distribuidor ou debenturista.

3. Se houver mais de uma série, extrair exclusivamente
   as informações da Primeira Série.

4. Se existir apenas uma série, identificar a
   denominação utilizada na escritura.

5. O CNPJ deve ser uma string, preservando zeros
   à esquerda e, quando disponíveis, a pontuação.

6. Não utilizar informações de outras séries para
   preencher campos da primeira.

7. Não inventar dados. Usar null quando ausentes.

## Exemplos

Exemplo de emissora:

Texto:
"ENERGISA ACRE - DISTRIBUIDORA DE ENERGIA S.A.,
inscrita no CNPJ sob nº 04.065.033/0001-70,
doravante denominada Emissora."

Extração:

{
  "emissor": "ENERGISA ACRE - DISTRIBUIDORA DE ENERGIA S.A.",
  "cnpj": "04.065.033/0001-70"
}

Exemplo de múltiplas séries:

Texto:
"As Debêntures serão emitidas em duas séries,
denominadas Primeira Série e Segunda Série."

Extração:
{
  "serie": "Primeira Série"
}

## Recuperação complementar

Caso o nome da emissora ou a série não tenham sido
identificados, solicitar nova recuperação semântica.

Priorizar consultas sobre:

- Preâmbulo da escritura
- Qualificação da emissora
- Denominação social
- CNPJ da emissora
- Número de séries da emissão

Não solicitar novas buscas apenas para confirmar
dados já sustentados pelas cláusulas recuperadas.

## Formato da resposta

O campo data deve conter:

- emissor: string ou null
- cnpj: string ou null
- serie: string ou null

Além dos dados, preencher:

- needs_more_context: boolean
- search_query: string ou null
- missing_fields: lista de nomes dos campos ausentes
- sources: lista de referências aos chunks utilizados

Se solicitar uma nova busca, informar uma consulta
objetiva em search_query.

Não adicionar campos fora do schema JSON fornecido.