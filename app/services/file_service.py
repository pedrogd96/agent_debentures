from pathlib import Path
from fastapi import UploadFile
from app.services.log_service import register_log


BASE_DIR = Path(__file__).resolve().parents[2]
UPLOAD_DIR = BASE_DIR / "uploads"

MAX_SIZE = 25 * 1024 * 1024
MAX_CHUNK = 1024 * 1024

ALLOWED_EXTENSIONS = {".pdf", ".txt"}

class InvalidFileError(Exception):
    pass


class FileSizeError(Exception):
    pass


async def save_uploaded_file(file: UploadFile, request_id: str, logger) -> dict:
    name_original = (file.filename or "").replace("\\", "/").split("/")[-1]
    register_log(logger, f"Arquivo recebido: {name_original}")

    extension = Path(name_original).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise InvalidFileError("O arquivo deve possuir extensão .pdf ou .txt.")

    file_type = extension.removeprefix(".").upper()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path_file = UPLOAD_DIR / f"{request_id}{extension}"
    size = 0

    try:
        with open(path_file, "wb") as destination:
            first_block = True

            while True:
                block = await file.read(
                    MAX_CHUNK
                )

                if not block:
                    break

                if first_block:
                    first_block = False

                    if extension == ".pdf" and not block.startswith(b"%PDF-"):
                        raise InvalidFileError("O conteúdo enviado não possui uma assinatura PDF válida.")

                size += len(block)

                if size > MAX_SIZE:
                    raise FileSizeError("O size máximo permitido é de 25 MB.")

                destination.write(block)

        if size == 0:
            raise InvalidFileError("O arquivo está vazio.")

        register_log(logger, f"Arquivo salvo: {path_file.name}")
        register_log(logger, f"size: {size} bytes")

        return {
            "name_file": name_original,
            "size_bytes": size,
            "file_type": file_type,
            "path": str(path_file)
        }

    except Exception:
        path_file.unlink(missing_ok=True)
        raise

    finally:
        await file.close()