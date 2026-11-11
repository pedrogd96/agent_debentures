import logging

from datetime import date

from pydantic import BaseModel, Field, ConfigDict
from typing import Annotated

from app.agents.retrieval_service import ContractRetriever
from app.agents.prompt_service import load_prompt
from app.agents.prompt_formatter import build_prompt_inputs
from app.agents.llm_service import LLMService
from app.agents.llm_callbacks import LLMLoggingCallback
from app.services.log_service import register_log
from app.models.required_when import RequiredWhen


MAX_ADDITIONAL_SEARCHES = 3
INITIAL_TOP_K = 5
ADDITIONAL_TOP_K = 4


STAGE_CONFIG = {
    "identification": {
        "query": (
            "Escritura de emissão de debêntures "
            "identificação da emissora razão social CNPJ "
            "preâmbulo primeira série"
        ),
        "required": ["emissor", "serie"],
    },
    "dates_values": {
        "query": (
            "Primeira série data de emissão data de "
            "vencimento valor nominal unitário "
            "valor total da emissão quantidade debêntures"
        ),
        "required": [
            "data_emissao",
            "data_vencimento",
            "valor_nominal_unitario",
        ],
    },
    "interest_correction": {
        "query": (
            "Debêntures primeira série remuneração "
            "Taxa DI CDI spread juros remuneratórios "
            "correção monetária capitalização fórmula"
        ),
        "required": [
            "possui_correcao_monetaria",
            "indexador",
            "percentual_indexador",
            "spread_anual_percentual",
            "metodologia_juros",
        ],
    },
    "amortization": {
        "query": (
            "Primeira série amortização valor nominal "
            "unitário parcelas percentuais datas "
            "cronograma amortização principal"
        ),
        "required": [
            "metodologia_amortizacao",
            "parcelas_amortizacao",
        ],
    },
}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class IdentificationData(StrictModel):
    emissor: str | None = None
    cnpj: str | None = None
    serie: str | None = None


class DatesValuesData(StrictModel):
    data_emissao: date | None = None
    data_vencimento: date | None = None
    valor_total_emissao_maximo: float | None = None
    valor_nominal_unitario: float | None = None
    quantidade_maxima_debentures: int | None = None
    moeda: str | None = None


class InterestCorrectionData(StrictModel):
    possui_correcao_monetaria: bool | None = None
    indice_correcao: Annotated[str | None, RequiredWhen(field_name="possui_correcao_monetaria", equals=True)] = Field(default=None, description="Índice da correção monetária do contrato.")
    indexador: str | None = None
    percentual_indexador: float | None = None
    spread_anual_percentual: float | None = None
    base_dias_uteis: int | None = None
    capitalizacao: str | None = None
    metodologia_juros: str | None = None
    formula_juros: str | None = None
    periodicidade_juros: str | None = None


class AmortizationInstallment(StrictModel):
    data: date
    percentual: float = Field(ge=0, le=100)
    base: str


class AmortizationData(StrictModel):
    metodologia_amortizacao: str | None = None
    parcelas_amortizacao: list[AmortizationInstallment] = Field(default_factory=list)


class ExtractionResponse(StrictModel):
    needs_more_context: bool = Field(description="True when additional clauses should be retrieved.")
    search_query: str | None = Field(default=None, description="Semantic query for retrieving missing information.")
    missing_fields: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list, description="Chunk IDs that support the extracted data, using only supplied chunks.")


class IdentificationResponse(ExtractionResponse):
    data: IdentificationData


class DatesValuesResponse(ExtractionResponse):
    data: DatesValuesData


class InterestCorrectionResponse(ExtractionResponse):
    data: InterestCorrectionData


class AmortizationResponse(ExtractionResponse):
    data: AmortizationData


RESPONSE_SCHEMAS = {
    "identification": IdentificationResponse,
    "dates_values": DatesValuesResponse,
    "interest_correction": InterestCorrectionResponse,
    "amortization": AmortizationResponse,
}


class ContractExtractionChains:
    def __init__(self, request_id: str, logger: logging.Logger):
        self.request_id = request_id
        self.logger = logger
        self.retriever = ContractRetriever(request_id=request_id, logger=logger)
        self.search_tool = self.retriever.as_tool()
        self.llm = LLMService()

    @staticmethod
    def _missing_values(data: BaseModel) -> list[str]:
        missing = []

        for field_name, field_info in type(data).model_fields.items():
            conditions = [
                item for item in field_info.metadata if isinstance(item, RequiredWhen)
            ]

            if any(getattr(data, condition.field_name, None) != condition.equals for condition in conditions):
                continue

            value = getattr(data, field_name)

            if (value is None or (isinstance(value, str) and not value.strip()) or (isinstance(value, (list, tuple, set, dict)) and not value)):
                missing.append(field_name)

        return missing

    @staticmethod
    def _merge_data(previous: BaseModel | None, current: BaseModel) -> BaseModel:
        if previous is None:
            return current

        merged = previous.model_dump(mode="json")
        latest = current.model_dump(mode="json")

        for key, value in latest.items():
            if value is not None and value != []:
                merged[key] = value

        return type(current).model_validate(merged)

    @staticmethod
    def _validated_sources(referenced_ids: list[str], chunks: list[dict], logger: logging.Logger) -> list[dict]:
        by_id = {chunk["chunk_id"]: chunk for chunk in chunks}
        sources = []
        seen = set()

        for chunk_id in referenced_ids:
            if chunk_id not in by_id:
                register_log(logger, f"Ignorando chunk ID: {chunk_id}", "WARNING")
                continue

            if chunk_id in seen:
                continue

            seen.add(chunk_id)
            sources.append(
                {
                    "chunk_id": chunk_id,
                    "page_number": by_id[chunk_id].get("page_number"),
                }
            )

        return sources

    def _search(self, stage: str, query: str, top_k: int, exclude_chunk_ids: set[str] | None = None) -> list[dict]:
        result = self.search_tool.invoke(
            {
                "query": query,
                "top_k": top_k,
                "exclude_chunk_ids": sorted(exclude_chunk_ids or set()),
            },
            config={
                "run_name": f"retrieve_{stage}",
                "tags": ["debenture-ai", stage, "rag"],
                "metadata": {"request_id": self.request_id},
            },
        )
        return result["chunks"]

    @staticmethod
    def _next_search_query(response: ExtractionResponse, data: BaseModel, missing_fields: list[str], attempted_queries: set[str]) -> str | None:
        proposed_query = (response.search_query or "").strip()

        if (response.needs_more_context and proposed_query and proposed_query.casefold() not in attempted_queries):
            return proposed_query

        for field_name in missing_fields:
            field_info = type(data).model_fields[field_name]
            field_description = (field_info.description or field_name.replace("_", " "))
            query = ("Escritura de emissão de debêntures Primeira Série cláusula contratual definição " f"{field_description}")

            if query.casefold() not in attempted_queries:
                return query

        return None

    def run_stage(self, stage: str) -> dict:
        if stage not in STAGE_CONFIG:
            raise ValueError(f"Etapa de extração não identificada: {stage}")

        stage_config = STAGE_CONFIG[stage]
        schema = RESPONSE_SCHEMAS[stage]
        prompt_text = load_prompt(stage)
        chain = self.llm.build_extraction_chain(schema)
        callback = LLMLoggingCallback(logger=self.logger, stage=stage)

        register_log(self.logger, f"Iniciando etapa de extração: {stage}")

        chunks = self._search(stage, stage_config["query"], INITIAL_TOP_K)
        all_chunks = list(chunks)
        known_chunk_ids = {item["chunk_id"] for item in chunks}

        if not chunks:
            raise ValueError("Nenhum chunk encontrado")

        previous_data = None
        attempted_queries = {stage_config["query"].strip().casefold()}
        sources_by_id = {}
        additional_searches = 0
        llm_calls = 0

        while True:
            llm_calls += 1

            inputs = build_prompt_inputs(
                prompt_text=prompt_text,
                chunks=all_chunks,
                previous_data=(previous_data.model_dump(mode="json") if previous_data is not None else None),
                attempt=llm_calls - 1,
                remaining_searches=MAX_ADDITIONAL_SEARCHES - additional_searches,
            )

            response = chain.invoke(
                inputs,
                config={
                    "callbacks": [callback],
                    "run_name": f"extract_{stage}",
                    "tags": ["debenture-ai", stage, "extraction"],
                    "metadata": {
                        "request_id": self.request_id,
                        "stage": stage,
                        "attempt": llm_calls,
                    },
                },
            )

            previous_data = self._merge_data(previous_data, response.data)
            valid_sources = self._validated_sources(response.sources, all_chunks, self.logger)

            for source in valid_sources:
                sources_by_id[source["chunk_id"]] = source

            missing_fields = self._missing_values(previous_data)
            register_log(self.logger, f"Etapa: {stage} | LLM call: {llm_calls} | " f"Campos faltantes: {missing_fields} | " f"Precisa de mais contexto: {response.needs_more_context}")

            if not missing_fields:
                break

            if additional_searches >= MAX_ADDITIONAL_SEARCHES:
                register_log(self.logger, f"Etapa {stage}: limite de buscas adicionais atingido.", "WARNING")
                break

            new_chunks = []

            while additional_searches < MAX_ADDITIONAL_SEARCHES:
                query = self._next_search_query(response=response, data=previous_data, missing_fields=missing_fields, attempted_queries=attempted_queries)

                if not query:
                    register_log(self.logger, f"Etapa {stage}: nenhuma nova consulta disponível.", "WARNING")
                    break

                attempted_queries.add(query.strip().casefold())
                register_log(self.logger, f"Etapa {stage}: busca semântica: {query}")

                new_chunks = self._search(stage, query, ADDITIONAL_TOP_K, known_chunk_ids)
                additional_searches += 1

                if new_chunks:
                    for chunk in new_chunks:
                        all_chunks.append(chunk)
                        known_chunk_ids.add(chunk["chunk_id"])

                    break

                register_log(self.logger, f"Etapa {stage}: sem cláusulas adicionais encontradas.", "WARNING")

            if not new_chunks:
                break

        final_missing = self._missing_values(previous_data)
        status = ("COMPLETED" if not final_missing else "INCOMPLETE")

        register_log(self.logger, f"Etapa {stage} finalizada | status={status} | " f"llm_calls={llm_calls} | " f"additional_searches={additional_searches}")

        return {
            "status": status,
            "data": previous_data.model_dump(mode="json"),
            "missing_fields": final_missing,
            "sources": list(sources_by_id.values()),
            "llm_calls": llm_calls,
            "additional_searches": additional_searches,
            "retrieved_chunks": len(all_chunks),
        }

    def run(self) -> dict:
        stages = [
            "identification",
            "dates_values",
            "interest_correction",
            "amortization",
        ]
        results = {}

        for stage in stages:
            results[stage] = self.run_stage(stage)

        register_log(self.logger, "Todas as etapas de extração foram concluidas.")

        return {"request_id": self.request_id, "stages": results}