import logging
import os
import time

from math import isfinite
from pathlib import Path

from dotenv import load_dotenv
from langchain_ollama import OllamaEmbeddings

from app.services.log_service import register_log


BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "bge-m3")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBEDDING_BATCH_SIZE = 8


def create_embedding_model() -> OllamaEmbeddings:
    return OllamaEmbeddings(model=EMBEDDING_MODEL, base_url=OLLAMA_BASE_URL)


def generate_embeddings( chunks: list[dict], logger: logging.Logger, embedding_model: OllamaEmbeddings | None = None) -> list[dict]:
    if not chunks:
        raise ValueError("Nenhum chunk foi recebido para gerar embeddings.")

    start_time = time.perf_counter()
    register_log(logger, "Iniciando geração de embeddings.")
    register_log(logger, f"Modelo de embeddings: {EMBEDDING_MODEL}")

    if embedding_model is None:
        embedding_model = create_embedding_model()

    embedded_chunks = []
    expected_dimension = None
    total_chunks = len(chunks)

    for start_index in range(0, total_chunks, EMBEDDING_BATCH_SIZE):
        batch = chunks[start_index: start_index + EMBEDDING_BATCH_SIZE]
        texts = [chunk["text"] for chunk in batch]
        vectors = embedding_model.embed_documents(texts)

        if len(vectors) != len(batch):
            raise RuntimeError("A quantidade de embeddings retornados não corresponde à quantidade de chunks.")

        for chunk, vector in zip(batch, vectors):
            if not vector:
                raise ValueError("O modelo retornou um embedding vazio.")

            if not all(isfinite(value) for value in vector):
                raise ValueError("O embedding contém valores inválidos.")

            if expected_dimension is None:
                expected_dimension = len(vector)

            if len(vector) != expected_dimension:
                raise ValueError("Os embeddings possuem dimensões diferentes.")

            embedded_chunk = {**chunk, "embedding": vector}
            embedded_chunks.append(embedded_chunk)

        register_log(logger, (f"Embeddings gerados: " f"{len(embedded_chunks)}/{total_chunks}."))

    elapsed_seconds = (time.perf_counter() - start_time)
    register_log(logger, ("Geração de embeddings concluída. " f"Total: {len(embedded_chunks)}. " f"Dimensões: {expected_dimension}. " f"Tempo: {elapsed_seconds:.2f} segundos."))

    print(f"Embeddings gerados: {len(embedded_chunks)}")
    print(f"Dimensões dos vetores: {expected_dimension}")
    print(f"Tempo de geração: {elapsed_seconds:.2f} segundos")
    return embedded_chunks