import os
import uuid

from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, File, HTTPException, UploadFile
from langsmith import traceable
from starlette.concurrency import run_in_threadpool

from app.models.contract_response import ContractResponse
from app.services.file_service import save_uploaded_file, InvalidFileError, FileSizeError
from app.services.log_service import create_logger, register_log, finalize_logger
from app.services.pdf_extraction_service_tesseract import extract_pdf_text
from app.services.txt_extraction_service import extract_txt_text
from app.services.chunk_service import create_chunks
from app.services.embedding_service import generate_embeddings
from app.services.vector_store_service import save_embeddings
from app.agents.extraction_chains import ContractExtractionChains


BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

router = APIRouter(prefix="/contracts", tags=["Contracts"])


@traceable(name="process_debenture_contract", run_type="chain")
def process_contract_file(file_path: str, file_type: str, request_id: str, logger) -> dict:
    if file_type == "PDF":
        extracted_pages = extract_pdf_text(file_path, logger)
    elif file_type == "TXT":
        extracted_pages = extract_txt_text(file_path, logger)
    else:
        raise InvalidFileError(f"Tipo do arquivo não suportado: {file_type}")

    total_characters = sum(page["character_count"] for page in extracted_pages)
    ocr_pages = sum(1 for page in extracted_pages if page["ocr_applied"])

    register_log(logger, f"Páginas processadas: {len(extracted_pages)}")
    register_log(logger, f"Páginas usando OCR: {ocr_pages}")
    register_log(logger, f"Total de caracteres: {total_characters}")

    chunks = create_chunks(extracted_pages=extracted_pages, request_id=request_id, logger=logger)
    embedded_chunks = generate_embeddings(chunks=chunks, logger=logger)
    vector_result = save_embeddings(embedded_chunks=embedded_chunks, request_id=request_id, logger=logger)
    register_log(logger, f"Salvos {vector_result['vector_count']} vetores.")

    agent = ContractExtractionChains(request_id=request_id, logger=logger)
    extraction_result = agent.run()

    register_log(logger, str(extraction_result))
    return extraction_result


@router.post("/upload", response_model=ContractResponse, status_code=201)
async def upload_contract(file: UploadFile = File(...)):
    request_id = str(uuid.uuid4())
    logger = create_logger(request_id)

    try:
        register_log(logger, "Iniciando upload do arquivo.")
        result = await save_uploaded_file(file=file, request_id=request_id, logger=logger)
        register_log(logger, "Upload do arquivo finalizado com sucesso.")

        extraction_result = await run_in_threadpool(process_contract_file, result["path"], result["file_type"], request_id, logger)

        register_log(logger, "Requisição finalizada.")
        return ContractResponse(
            request_id=request_id,
            status="RECEBIDO",
            message="Arquivo recebido com sucesso.",
            file_type=result["file_type"],
            name_file=result["name_file"],
            size_bytes=result["size_bytes"],
            data=extraction_result,
        )

    except InvalidFileError as error:
        register_log(logger, str(error), "WARNING")
        raise HTTPException(status_code=400, detail={"request_id": request_id, "mensagem": str(error)}) from error

    except FileSizeError as error:
        register_log(logger, str(error), "WARNING")
        raise HTTPException(status_code=413, detail={"request_id": request_id, "mensagem": str(error)}) from error

    except Exception:
        logger.exception("Erro não identificado durante o upload.")
        raise HTTPException(
            status_code=500,
            detail={
                "request_id": request_id,
                "mensagem": "Erro interno ao receber o arquivo.",
            }
        ) from None

    finally:
        register_log(logger, "Finalizando requisição.")
        finalize_logger(logger)