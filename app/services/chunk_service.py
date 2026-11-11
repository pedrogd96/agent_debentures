import logging

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.services.log_service import register_log


DEFAULT_CHUNK_SIZE = 1200
DEFAULT_CHUNK_OVERLAP = 200


def create_chunks(extracted_pages: list[dict] | str, request_id: str, logger: logging.Logger, chunk_size: int = DEFAULT_CHUNK_SIZE, chunk_overlap: int = DEFAULT_CHUNK_OVERLAP) -> list[dict]:
    if chunk_size <= 0:
        raise ValueError("O tamanho do chunk deve ser maior que zero.")

    if not 0 <= chunk_overlap < chunk_size:
        raise ValueError("A sobreposição deve ser menor que o chunk.")

    register_log(logger, "Iniciando divisão do texto em chunks.")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=[
            "\n\n",
            "\n",
            ". ",
            "; ",
            " ",
            ""
        ],
        keep_separator=True,
        length_function=len
    )

    if isinstance(extracted_pages, str):
        extracted_pages = [
            {
                "page_number": None,
                "text": extracted_pages
            }
        ]

    chunks = []
    chunk_number = 0

    for page in extracted_pages:
        page_number = page.get("page_number")
        text = page.get("text", "")

        if not text or not text.strip():
            continue

        page_chunks = text_splitter.split_text(text)

        for page_chunk in page_chunks:
            if not page_chunk.strip():
                continue

            chunk_number += 1
            chunk = {
                "chunk_id": (
                    f"{request_id}_{chunk_number:05d}"
                ),
                "request_id": request_id,
                "page_number": page_number,
                "chunk_index": chunk_number,
                "text": page_chunk.strip(),
                "character_count": len(
                    page_chunk.strip()
                )
            }

            chunks.append(chunk)

        register_log(logger,(f"Página {page_number}: " f"{len(page_chunks)} chunks gerados."))

    register_log(logger, (f"Divisão concluída. " f"Total de chunks: {len(chunks)}."))
    print(f"Total de chunks gerados: {len(chunks)}")
    return chunks