import logging
import time

from pathlib import Path

from app.services.log_service import register_log


class InvalidTextEncodingError(Exception):
    pass


def extract_txt_text(file_path: str | Path, logger: logging.Logger) -> list[dict]:
    start_time = time.perf_counter()
    file_path = Path(file_path)

    if not file_path.is_file():
        raise FileNotFoundError(f"Arquivo TXT não encontrado: {file_path}")

    register_log(logger, f"Iniciando extração do arquivo TXT: {file_path.name}")

    try:
        text = file_path.read_text(encoding="utf-8-sig")

    except UnicodeDecodeError as error:
        raise InvalidTextEncodingError("O arquivo TXT deve usar encoding UTF-8.") from error

    if "\x00" in text:
        raise InvalidTextEncodingError("O arquivo contém bytes inválidos.")

    text = text.strip()

    if not text:
        raise InvalidTextEncodingError("O arquivo TXT não contém nenhum texto.")

    elapsed_seconds = (time.perf_counter() - start_time)
    register_log(logger, ("Extração TXT completa. " f"caracteres={len(text)}, " f"tempo={elapsed_seconds:.3f}s"))

    return [
        {
            "page_number": None,
            "text": text,
            "ocr_applied": False,
            "character_count": len(text),
            "ocr_line_count": 0,
            "ocr_confidence": None,
            "ocr_elapsed_seconds": 0.0,
            "elapsed_seconds": round(elapsed_seconds, 3)
        }
    ]