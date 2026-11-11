import json
import logging
import uuid

from pathlib import Path

import faiss
import numpy as np

from langchain_core.tools import tool

from app.services.embedding_service import create_embedding_model, EMBEDDING_MODEL
from app.services.log_service import register_log


BASE_DIR = Path(__file__).resolve().parents[2]
VECTOR_STORE_DIR = BASE_DIR / "vector_store"


class ContractRetriever:

    def __init__(self, request_id: str, logger: logging.Logger):
        self.request_id = str(uuid.UUID(request_id))
        self.logger = logger

        directory = VECTOR_STORE_DIR / self.request_id

        index_path = directory / "index.faiss"
        metadata_path = directory / "metadata.json"
        config_path = directory / "config.json"

        if not all(path.is_file() for path in (index_path, metadata_path, config_path)):
            raise FileNotFoundError("Índice vetorial do contrato não encontrado.")

        index_bytes = index_path.read_bytes()
        index_array = np.frombuffer(index_bytes, dtype=np.uint8).copy()
        self.index = faiss.deserialize_index(index_array)
        self.metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        self.config = json.loads(config_path.read_text(encoding="utf-8"))

        if self.config["embedding_model"] != EMBEDDING_MODEL:
            raise ValueError("O modelo de embeddings é diferente daquele utilizado na indexação.")

        if len(self.metadata) != self.index.ntotal:
            raise ValueError("A quantidade de metadados não corresponde à quantidade de vetores.")

        self.metadata_by_position = {item["vector_position"]: item for item in self.metadata}
        self.embedding_model = create_embedding_model()
        register_log(logger, ("Recuperador FAISS inicializado. " f"Total de vetores: {self.index.ntotal}"))

    def search(self, query: str, top_k: int = 5, exclude_chunk_ids: set[str] | None = None) -> list[dict]:
        if not query.strip():
            raise ValueError("A consulta semântica não pode estar vazia.")

        if top_k < 1:
            raise ValueError("top_k deve ser maior que zero.")

        excluded = exclude_chunk_ids or set()
        register_log(self.logger, f"Consulta semântica: {query}")
        vector = self.embedding_model.embed_query(query)
        query_vector = np.asarray([vector], dtype=np.float32)

        if query_vector.shape[1] != self.index.d:
            raise ValueError("Dimensão do embedding incompatível com o índice FAISS.")

        query_vector = np.ascontiguousarray(query_vector)
        faiss.normalize_L2(query_vector)
        distances, positions = self.index.search(query_vector, self.index.ntotal)
        results = []

        for score, position in zip(distances[0], positions[0]):
            position = int(position)

            if position < 0:
                continue

            item = self.metadata_by_position.get(position)

            if item is None:
                continue

            if item["chunk_id"] in excluded:
                continue

            results.append({
                "chunk_id": item["chunk_id"],
                "text": item["text"],
                "page_number": item.get("page_number"),
                "chunk_index": item["chunk_index"],
                "similarity": float(score)
            })

            if len(results) >= top_k:
                break

        register_log(self.logger, f"Chunks recuperados: {len(results)}")

        for item in results:
            register_log(self.logger, (f"Chunk: {item['chunk_id']} | " f"Página: {item['page_number']} | " f"Similaridade: {item['similarity']:.4f}"))

        return results

    def as_tool(self):
        @tool(
            "search_contract_clauses",
            description=(
                "Pesquisa no índice FAISS existente as cláusulas relevantes "
                "de um contrato financeiro. Retorna os textos recuperados, "
                "identificadores dos chunks, números das páginas e pontuações "
                "de similaridade semântica. Utilize esta ferramenta para "
                "localizar evidências contratuais necessárias à extração "
                "de informações financeiras."
            ),
        )
        def search_contract_clauses(query: str, top_k: int = 5, exclude_chunk_ids: list[str] | None = None) -> dict:
            return {
                "chunks": self.search(query=query, top_k=top_k, exclude_chunk_ids=set(exclude_chunk_ids or []))
            }

        return search_contract_clauses