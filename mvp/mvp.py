
import json
import logging
import os
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError

from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableLambda, chain
from langchain_ollama import ChatOllama


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

MODELO = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

ARQUIVO_JSON = BASE_DIR / "resultado.json"
ARQUIVO_LOG = BASE_DIR / "mvp.log"

logging.basicConfig(
    filename=ARQUIVO_LOG,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    encoding="utf-8"
)

logger = logging.getLogger("debenture_mvp")


CLAUSULAS = [
    {
        "clausula": "Preâmbulo - Identificação da Emissora",
        "pagina": 4,
        "texto": """
        ENERGISA ACRE – DISTRIBUIDORA DE ENERGIA S.A.,
        sociedade por ações com registro de companhia aberta
        perante a Comissão de Valores Mobiliários (CVM),
        com sede na cidade de Rio Branco, Estado do Acre,
        na Rua Valério Magalhães, nº 226, Bosque,
        CEP 69.900-685, inscrita no CNPJ sob o
        nº 04.065.033/0001-70, doravante denominada
        "Emissora".
        """
    },
    {
        "clausula": "3.2.1",
        "pagina": 8,
        "texto": """
        O valor total da emissão é de até R$ 140.000.000,00
        (cento e quarenta milhões de reais), na Data de Emissão,
        observada a possibilidade de distribuição parcial.
        """
    },
    {
        "clausula": "4.1.1",
        "pagina": 16,
        "texto": """
        Para todos os fins de direito e efeitos,
        a Data de Emissão das Debêntures será
        15 de dezembro de 2024.
        """
    },
    {
        "clausula": "4.1.5",
        "pagina": 16,
        "texto": """
        O prazo de vencimento das Debêntures da
        Primeira Série será de 5 anos,
        contados da Data de Emissão,
        vencendo em 15 de dezembro de 2029.
        """
    },
    {
        "clausula": "4.2.1",
        "pagina": 17,
        "texto": """
        O Valor Nominal Unitário das Debêntures
        não será atualizado monetariamente.
        """
    },
    {
        "clausula": "4.2.2",
        "pagina": 17,
        "texto": """
        Sobre o Valor Nominal Unitário das Debêntures
        da Primeira Série incidirão juros remuneratórios
        correspondentes à variação acumulada de 100%
        das Taxas DI, acrescida de spread de 0,95%
        ao ano, base 252 dias úteis.

        A remuneração será calculada de forma
        exponencial e cumulativa pro rata temporis
        por dias úteis decorridos.
        """
    },
    {
        "clausula": "4.2.3",
        "pagina": 17,
        "texto": """
        A remuneração das Debêntures da Primeira Série
        será calculada em regime de capitalização
        composta, pro rata temporis por dias úteis,
        desde a Primeira Data de Integralização
        ou desde a data de pagamento da remuneração
        imediatamente anterior, conforme aplicável.
        """
    },
    {
        "clausula": "4.3.1",
        "pagina": 21,
        "texto": """
        O Valor Nominal Unitário das Debêntures
        da Primeira Série será amortizado em
        uma única parcela, na Data de Vencimento
        da Primeira Série.
        """
    },
    {
        "clausula": "4.4.1",
        "pagina": 22,
        "texto": """
        A remuneração das Debêntures será paga
        semestralmente.

        Para a Primeira Série, o primeiro pagamento
        ocorrerá em 15 de junho de 2025.

        Para a Segunda Série, o primeiro pagamento
        ocorrerá em 15 de junho de 2025.

        Os pagamentos ocorrerão nos meses de
        junho e dezembro, até o vencimento de
        cada série, conforme os cronogramas
        previstos na escritura.
        """
    }
]


def montar_contexto_clausulas():
    partes = []

    for item in CLAUSULAS:
        trecho = (
            f"CLÁUSULA: {item['clausula']}\n"
            f"PÁGINA: {item['pagina']}\n"
            f"TEXTO:\n{item['texto'].strip()}"
        )
        partes.append(trecho)

    return "\n\n---\n\n".join(partes)


class Fonte(BaseModel):
    clausula: str = Field(description="Número da cláusula de origem")
    pagina: int = Field(ge=1, description="Página do contrato")


class ParcelaAmortizacao(BaseModel):
    data: date = Field(description="Data da amortização no formato YYYY-MM-DD")
    percentual: float = Field(ge=0, le=100, description="Percentual da amortização de 0 a 100")
    base: str = Field(description="Base de incidência da amortização: valor nominal original ou saldo remanescente")


class ExtracaoContrato(BaseModel):
    emissor: str = Field(description="Razão social do emissor")
    data_emissao: date = Field(description="Data de emissão no formato YYYY-MM-DD")
    data_vencimento: date = Field(description="Data de vencimento no formato YYYY-MM-DD")
    valor_total_emissao_maximo: float = Field(ge=0, description="Valor total máximo da emissão")
    moeda: str = Field(description="Moeda da operação")
    valor_nominal_unitario: float = Field(ge=0, description="Valor nominal unitário das debêntures")
    quantidade_maxima_debentures: int = Field(ge=0, description="Quantidade máxima de debêntures")
    possui_correcao_monetaria: bool = Field(description="Indica existência de correção monetária")
    metodologia_juros: str = Field(description="Metodologia de cálculo dos juros")
    indexador: str = Field(description="Indexador utilizado na remuneração")
    percentual_indexador: float = Field(ge=0, description="Percentual do indexador em escala percentual. Exemplo: 100.0 representa 100% do CDI")
    spread_anual_percentual: float = Field(ge=0, description="Spread anual em percentual")
    base_dias_uteis: int = Field(gt=0, description="Base de dias úteis utilizada no cálculo")
    capitalizacao: str = Field(description="Regime de capitalização")
    periodicidade_juros: str = Field(description="Periodicidade do pagamento dos juros")
    metodologia_amortizacao: str = Field(description="Metodologia de amortização do principal")
    parcelas_amortizacao: list[ParcelaAmortizacao] = Field(description="Cronograma das parcelas de amortização")
    fontes_gerais: list[Fonte] = Field(
        min_length=1,
        description=("Cláusulas e páginas utilizadas para extrair as informações do contrato")
    )


modelo = ChatOllama(model=MODELO, base_url=OLLAMA_URL, temperature=0, num_ctx=16384)
parser = JsonOutputParser(pydantic_object=ExtracaoContrato)


def validar_resultado(resultado):
    contrato = ExtracaoContrato.model_validate(resultado)

    # Verifica a consistência das datas
    if contrato.data_vencimento <= contrato.data_emissao:
        raise ValueError("A data de vencimento deve ser posterior à data de emissão.")

    for parcela in contrato.parcelas_amortizacao:
        if parcela.data < contrato.data_emissao:
            raise ValueError("A data de amortização não pode ser anterior à data de emissão.")

        if parcela.data > contrato.data_vencimento:
            raise ValueError("A data de amortização não pode ser posterior ao vencimento.")

    # Valida as fontes
    fontes_validas = {
        (item["clausula"], item["pagina"])
        for item in CLAUSULAS
    }

    for fonte in contrato.fontes_gerais:
        referencia = (fonte.clausula, fonte.pagina)

        if referencia not in fontes_validas:
            raise ValueError(
                f"Fonte não encontrada nas cláusulas "
                f"fornecidas: cláusula {fonte.clausula}, "
                f"página {fonte.pagina}"
            )

    return contrato.model_dump(mode="json")


prompt_extracao = PromptTemplate.from_template(
    """
    Analise as cláusulas contratuais abaixo e extraia
    as informações financeiras necessárias para o
    cadastro de uma operação de debêntures.

    INFORMAÇÕES NECESSÁRIAS:

    1. Identificação do emissor.
    2. Data de emissão.
    3. Data de vencimento.
    4. Valor total máximo da emissão.
    5. Existência de correção monetária.
    6. Indexador da correção.
    7. Taxa de juros.
    8. Base de juros.
    9. Metodologia e parcelas de amortização.
    10. Páginas e cláusulas de origem.

    REGRAS:

    - Não invente informações.
    - Utilize somente as cláusulas fornecidas.
    - Datas devem utilizar YYYY-MM-DD.
    - Valores monetários devem ser numéricos.
    - Percentuais devem ser numéricos.
    - Preserve as unidades de cada percentual.
    - Diferencie valor nominal original e saldo.
    - Na amortização, preserve a base percentual.
    - Não confunda ausência de correção monetária com ausência de juros pós-fixados.
    - Não inclua explicações fora do JSON.

    CLÁUSULAS DO CONTRATO:

    {clausulas}
    """
)


chat_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
        Você é um especialista na análise de contratos
        financeiros brasileiros, especialmente
        escrituras de emissão de debêntures.

        Sua responsabilidade é identificar parâmetros
        financeiros para o futuro cadastro de uma
        operação em um sistema financeiro.

        O cadastro poderá futuramente permitir:
        cálculo de juros, pagamentos, amortizações,
        provisões e classificações CP e LP.

        Sua função atual é somente a extração
        estruturada das informações contratuais.

        Não invente dados.
        Não realize cálculos financeiros.
        Preserve a rastreabilidade das informações.

        Retorne exclusivamente um JSON válido.
        """
    ),

    (
        "human",
        """
        {tarefa}

        FORMATO JSON OBRIGATÓRIO:

        {formato}
        """
    )

])


chain = chat_prompt | modelo | parser | RunnableLambda(validar_resultado)


def executar_chain(contexto):
    tarefa = prompt_extracao.invoke({"clausulas": contexto})
    return chain.invoke({"tarefa": tarefa.to_string(), "formato": parser.get_format_instructions()})


def salvar_json(resultado):
    with open(ARQUIVO_JSON, "w", encoding="utf-8") as arquivo:
        json.dump(resultado, arquivo, ensure_ascii=False, indent=4)


def main():
    inicio = datetime.now()
    logger.info("=" * 60)
    logger.info("Iniciando processamento do MVP")
    logger.info("Modelo: %s", MODELO)

    print("\n================================")
    print("DEBENTURE - MVP")
    print(f"Modelo: {MODELO}")
    print(f"Cláusulas: {len(CLAUSULAS)}")

    contexto = montar_contexto_clausulas()

    try:
        resultado = executar_chain(contexto)
        salvar_json(resultado)

        print("\nEXTRAÇÃO CONCLUÍDA")
        print(json.dumps(resultado, ensure_ascii=False, indent=4))

        logger.info("Extração concluída")
        logger.info("Resultado salvo em: %s", ARQUIVO_JSON)
    except (ValidationError, ValueError) as erro:
        logger.exception("Erro na validação da extração")
        print("\nERRO DE VALIDAÇÃO:")
        print(erro)
    except Exception as erro:
        logger.exception("Erro durante o processamento")
        print("\nERRO NO PROCESSAMENTO:")
        print(erro)
    finally:
        duracao = (datetime.now() - inicio).total_seconds()
        logger.info("Duração: %.2f segundos", duracao)
        print(f"\nTempo total: {duracao:.2f} segundos")


if __name__ == "__main__":
    main()