import json
import logging
import time

from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler


class LLMLoggingCallback(BaseCallbackHandler):
    def __init__(self, logger: logging.Logger, stage: str):
        self.logger = logger
        self.stage = stage
        self.start_times = {}

    def on_chat_model_start(self, serialized: dict[str, Any], messages: list, *, run_id: UUID, **kwargs) -> None:
        self.start_times[run_id] = time.perf_counter()
        self.logger.info("Etapa %s | LLM started | run_id=%s", self.stage, run_id)

        for batch_index, message_batch in enumerate(messages, start=1):
            prompt_messages = [
                {
                    "role": getattr(message, "type", "unknown"),
                    "content": getattr(message, "content", ""),
                }
                for message in message_batch
            ]
            self.logger.info("Etapa %s | LLM prompt | run_id=%s | batch=%s\n%s", self.stage, run_id, batch_index, json.dumps(prompt_messages, ensure_ascii=False, indent=2, default=str))

    def on_llm_start(self, serialized: dict[str, Any], prompts: list[str], *, run_id: UUID, **kwargs) -> None:
        self.start_times[run_id] = time.perf_counter()
        self.logger.info("Etapa %s | Modelo iniciado | run_id=%s", self.stage, run_id)

        for prompt_index, prompt in enumerate(prompts, start=1):
            self.logger.info("Etapa %s | LLM prompt | run_id=%s | prompt=%s\n%s", self.stage, run_id, prompt_index, prompt)

    def on_llm_end(self, response, *, run_id: UUID, **kwargs) -> None:
        started = self.start_times.pop(run_id, None)
        elapsed = time.perf_counter() - started if started is not None else None
        usage = {}

        if response.generations:
            first_batch = response.generations[0]
            if first_batch:
                message = getattr(first_batch[0], "message", None)
                if message is not None:
                    usage = getattr(message, "usage_metadata", None) or {}

        if not usage:
            usage = (response.llm_output or {}).get("token_usage", {})

        self.logger.info("Etapa %s | LLM finalizada | run_id=%s | duration=%s | " "input_tokens=%s | output_tokens=%s | total_tokens=%s", self.stage, run_id, f"{elapsed:.2f}s" if elapsed is not None else "N/A", usage.get("input_tokens", usage.get("prompt_tokens")), usage.get("output_tokens", usage.get("completion_tokens")), usage.get("total_tokens"))

    def on_llm_error(self, error: BaseException, *, run_id: UUID, **kwargs) -> None:
        self.start_times.pop(run_id, None)
        self.logger.error("Etapa %s | LLM error | run_id=%s | error=%s", self.stage, run_id, error)

    def on_tool_start(self, serialized: dict, input_str: str, *, run_id: UUID, **kwargs) -> None:
        self.logger.info("Etapa %s | Tool iniciada | run_id=%s", self.stage, run_id)

    def on_tool_end(self, output: Any, *, run_id: UUID, **kwargs) -> None:
        self.logger.info("Etapa %s | Tool finalizada | run_id=%s", self.stage, run_id)

    def on_tool_error(self, error: BaseException, *, run_id: UUID, **kwargs) -> None:
        self.logger.error("Etapa %s | Tool error | run_id=%s | error=%s", self.stage, run_id, error)