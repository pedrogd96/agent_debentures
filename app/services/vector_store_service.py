import json
import logging
import time
import uuid

from pathlib import Path

import faiss
import numpy as np

from app.services.log_service import register_log
from app.services.embedding_service import EMBEDDING_MODEL


BASE_DIR = Path(__file__).resolve().parents[2]
VECTOR_STORE_DIR = BASE_DIR / "vector_store"


def save_embeddings(embedded_chunks: list[dict], request_id: str, logger: logging.Logger) -> dict:
    if not embedded_chunks:
        raise ValueError("Nenhum embedding foi recebido para indexação.")

    try:
        request_uuid = uuid.UUID(request_id)
    except ValueError as error:
        raise ValueError("O identificador da requisição é inválido.") from error

    request_id = str(request_uuid)
    start_time = time.perf_counter()
    register_log(logger, "Iniciando criação do índice FAISS.")

    for chunk in embedded_chunks:
        if chunk.get("request_id") != request_id:
            raise ValueError("Foi encontrado um chunk de outra requisição.")

    try:
        vectors = np.asarray([chunk["embedding"] for chunk in embedded_chunks], dtype=np.float32)
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("Não foi possível converter os embeddings.") from error

    if vectors.ndim != 2:
        raise ValueError("A matriz de embeddings deve ter duas dimensões.")

    if not np.all(np.isfinite(vectors)):
        raise ValueError("Foram encontrados valores inválidos nos embeddings.")

    vector_count, vector_dimension = vectors.shape

    if vector_dimension == 0:
        raise ValueError("A dimensão dos embeddings não pode ser zero.")

    vector_norms = np.linalg.norm(vectors, axis=1)

    if np.any(vector_norms == 0):
        raise ValueError("Foram encontrados vetores com norma zero.")

    vectors = np.ascontiguousarray(vectors, dtype=np.float32)
    faiss.normalize_L2(vectors)
    index = faiss.IndexFlatIP(vector_dimension)
    index.add(vectors)

    VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)
    index_directory = (VECTOR_STORE_DIR / request_id)

    if index_directory.exists():
        raise FileExistsError("Já existe um índice FAISS para esta requisição.")

    index_directory.mkdir()
    index_path = (index_directory / "index.faiss")
    metadata_path = (index_directory / "metadata.json")
    config_path = (index_directory / "config.json")

    metadata = []
    for position, chunk in enumerate(embedded_chunks):
        metadata.append({
            "vector_position": position,
            "chunk_id": chunk["chunk_id"],
            "request_id": chunk["request_id"],
            "page_number": chunk["page_number"],
            "chunk_index": chunk["chunk_index"],
            "text": chunk["text"],
            "character_count": chunk["character_count"]
        })

    config = {
        "request_id": request_id,
        "embedding_model": EMBEDDING_MODEL,
        "vector_count": vector_count,
        "vector_dimension": vector_dimension,
        "index_type": "IndexFlatIP",
        "normalized": True,
        "similarity": "cosine"
    }

    index_bytes = faiss.serialize_index(index)
    with open(index_path, "wb") as file:
        file.write(index_bytes.tobytes())

    with open(metadata_path, "w", encoding="utf-8") as file:
        json.dump(metadata, file, ensure_ascii=False, indent=2)

    with open(config_path, "w", encoding="utf-8") as file:
        json.dump(config, file, ensure_ascii=False, indent=2)

    elapsed_seconds = (time.perf_counter() - start_time)
    register_log(logger, ("Índice FAISS salvo com sucesso. " f"Vetores: {index.ntotal}. " f"Dimensões: {vector_dimension}. " f"Tempo: {elapsed_seconds:.2f} segundos."))

    print(f"Índice FAISS criado com {index.ntotal} vetores.")
    print(f"Índice salvo em: {index_directory}")

    return {
        "request_id": request_id,
        "index_path": str(index_path),
        "metadata_path": str(metadata_path),
        "config_path": str(config_path),
        "vector_count": int(index.ntotal),
        "vector_dimension": vector_dimension,
        "elapsed_seconds": round(
            elapsed_seconds, 3
        )
    }