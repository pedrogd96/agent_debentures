import logging
import os

from pathlib import Path
from typing import TypeVar

from dotenv import load_dotenv
from pydantic import BaseModel

from langchain_core.runnables import Runnable, RunnableLambda, chain
from langchain_ollama import ChatOllama

from app.agents.llm_callbacks import LLMLoggingCallback
from app.agents.prompt_formatter import EXTRACTION_PROMPT


BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

LLM_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_CONTEXT_SIZE = int(os.getenv("OLLAMA_CONTEXT_SIZE", "16384"))
T = TypeVar("T", bound=BaseModel)


class LLMService:
    def __init__(self):
        self.model = ChatOllama(model=LLM_MODEL, base_url=OLLAMA_BASE_URL, temperature=0, num_ctx=LLM_CONTEXT_SIZE)

    @staticmethod
    def _parse_structured_response(result: dict, response_schema: type[T]) -> T:
        if result.get("parsing_error") is not None:
            raise ValueError("A LLM retornou uma saída com uma estrutura inválida: " f"{result['parsing_error']}")

        parsed = result.get("parsed")

        if parsed is None:
            raise ValueError("A LLM não retornou dados estruturados.")

        return response_schema.model_validate(parsed)

    def build_extraction_chain(self, response_schema: type[T]) -> Runnable:
        structured_model = self.model.with_structured_output(response_schema, method="json_schema", include_raw=True)
        parser = RunnableLambda(lambda result: self._parse_structured_response(result, response_schema), name="validate_contract_json")
        return EXTRACTION_PROMPT | structured_model | parser

    def build_imperative_chain(self, response_schema: type[T]) -> Runnable:
        structured_model = self.model.with_structured_output(response_schema, method="json_schema", include_raw=True)

        @chain
        def imperative_extraction(inputs: dict) -> T:
            prompt_value = EXTRACTION_PROMPT.invoke(inputs)
            result = structured_model.invoke(prompt_value)
            return self._parse_structured_response(result, response_schema)

        return imperative_extraction

    def invoke(self, messages: list, response_schema: type[T], logger: logging.Logger, stage: str) -> T:
        callback = LLMLoggingCallback(logger=logger, stage=stage)
        structured_model = self.model.with_structured_output(response_schema, method="json_schema", include_raw=True)
        result = structured_model.invoke(
            messages,
            config={
                "callbacks": [callback],
                "run_name": f"extract_{stage}",
                "tags": ["debenture-ai", stage],
            },
        )
        return self._parse_structured_response(result, response_schema)