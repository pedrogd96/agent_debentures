import logging
import time

from pathlib import Path

import numpy as np
import pymupdf

from rapidocr import RapidOCR

from app.services.log_service import register_log


OCR_DPI = 200
MIN_IMAGE_AREA_RATIO = 0.08
PREVIEW_PAGE_COUNT = 10

MIN_OCR_CONFIDENCE = 0.0


def create_ocr_engine() -> RapidOCR:
    return RapidOCR()


def extract_native_text(page) -> str:
    return page.get_text("text", sort=True).strip()


def render_page_region(page, region=None) -> np.ndarray:
    scale = OCR_DPI / 72
    matrix = pymupdf.Matrix(scale, scale)
    pixmap = page.get_pixmap(matrix=matrix, clip=region, colorspace=pymupdf.csRGB, alpha=False)
    image_array = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape( pixmap.height, pixmap.width, pixmap.n)
    return image_array.copy()


def run_ocr(image: np.ndarray, ocr_engine: RapidOCR) -> dict:
    start_time = time.perf_counter()
    result = ocr_engine(image)
    elapsed_seconds = (time.perf_counter() - start_time)

    if result is None or not result.txts:
        return {
            "text": "",
            "confidence": None,
            "line_count": 0,
            "elapsed_seconds": elapsed_seconds
        }

    recognized_lines = []
    confidence_scores = []

    scores = result.scores

    if scores is None:
        scores = []

    for index, text in enumerate(result.txts):
        if not text or not text.strip():
            continue

        score = (float(scores[index]) if index < len(scores) else None)

        if (score is not None and score < MIN_OCR_CONFIDENCE):
            continue

        recognized_lines.append(text.strip())

        if score is not None:
            confidence_scores.append(score)

    average_confidence = None

    if confidence_scores:
        average_confidence = (sum(confidence_scores) / len(confidence_scores))

    return {
        "text": "\n".join(recognized_lines),
        "confidence": average_confidence,
        "line_count": len(recognized_lines),
        "elapsed_seconds": elapsed_seconds
    }


def get_image_regions(page) -> list:
    page_data = page.get_text("dict")
    page_area = (page.rect.width * page.rect.height)

    regions = []
    seen_regions = set()

    for block in page_data["blocks"]:
        if block["type"] != 1:
            continue

        rectangle = (pymupdf.Rect(block["bbox"]) & page.rect)

        if rectangle.is_empty:
            continue

        image_area = (rectangle.width * rectangle.height)
        area_ratio = image_area / page_area

        if area_ratio < MIN_IMAGE_AREA_RATIO:
            continue

        region_key = tuple(round(value, 1) for value in rectangle)

        if region_key in seen_regions:
            continue

        seen_regions.add(region_key)
        regions.append(rectangle)

    return regions


def extract_page_text(page, page_number: int, logger: logging.Logger, ocr_engine: RapidOCR) -> dict:
    start_time = time.perf_counter()
    register_log(logger, f"Iniciando extração para a página {page_number}")

    native_text = extract_native_text(page)

    extracted_parts = []

    if native_text:
        extracted_parts.append(native_text)

    ocr_applied = False
    ocr_elapsed_seconds = 0.0
    ocr_confidences = []
    ocr_line_count = 0

    if not native_text:
        register_log(logger, f"Página {page_number}: rodando para a página inteira RapidOCR")
        image = render_page_region(page)
        ocr_result = run_ocr(image, ocr_engine)

        if ocr_result["text"]:
            extracted_parts.append(ocr_result["text"])

        ocr_applied = True
        ocr_elapsed_seconds += (ocr_result["elapsed_seconds"])
        ocr_line_count += (ocr_result["line_count"])

        if ocr_result["confidence"] is not None:
            ocr_confidences.append(ocr_result["confidence"])

    else:
        image_regions = get_image_regions(page)

        for image_index, region in enumerate( image_regions, start=1):
            register_log(logger, (f"Página {page_number}: rodando RapidOCR " f"na região da imagem {image_index}"))

            image = render_page_region(page, region)
            ocr_result = run_ocr(image, ocr_engine)

            if ocr_result["text"]:
                extracted_parts.append(ocr_result["text"])

            ocr_applied = True
            ocr_elapsed_seconds += (ocr_result["elapsed_seconds"])
            ocr_line_count += (ocr_result["line_count"])

            if ocr_result["confidence"] is not None:
                ocr_confidences.append(ocr_result["confidence"])

    final_text = "\n\n".join(part for part in extracted_parts if part).strip()
    elapsed_seconds = (time.perf_counter() - start_time)
    average_confidence = None

    if ocr_confidences:
        average_confidence = (sum(ocr_confidences) / len(ocr_confidences))

    register_log(
        logger,
        (
            f"Página {page_number}: "
            f"caracteres={len(final_text)}, "
            f"ocr_applied={ocr_applied}, "
            f"ocr_lines={ocr_line_count}, "
            f"ocr_time={ocr_elapsed_seconds:.3f}s, "
            f"total_time={elapsed_seconds:.3f}s, "
            f"confidence={average_confidence}"
        )
    )

    return {
        "page_number": page_number,
        "text": final_text,
        "ocr_applied": ocr_applied,
        "character_count": len(final_text),
        "ocr_line_count": ocr_line_count,
        "ocr_confidence": average_confidence,
        "ocr_elapsed_seconds": round(
            ocr_elapsed_seconds, 3
        ),
        "elapsed_seconds": round(
            elapsed_seconds, 3
        )
    }


def extract_pdf_text(pdf_path: str | Path, logger: logging.Logger) -> list[dict]:
    pdf_path = Path(pdf_path)

    if not pdf_path.is_file():
        raise FileNotFoundError(f"Arquivo PDF não encontrado: {pdf_path}")

    start_time = time.perf_counter()
    register_log(logger, f"Iniciando extração PDF: {pdf_path.name}")
    register_log(logger, "OCR engine: RapidOCR + ONNX Runtime")

    ocr_engine = create_ocr_engine()
    pages = []

    with pymupdf.open(pdf_path) as document:
        if document.needs_pass:
            raise ValueError("Proteção de senha no PDF não suportado.")

        total_pages = len(document)
        register_log(logger, f"Páginas totais: {total_pages}")

        for page_index in range(total_pages):
            page = document.load_page(page_index)
            result = extract_page_text(page=page, page_number=page_index + 1, logger=logger, ocr_engine=ocr_engine)
            pages.append(result)

    total_elapsed_seconds = (time.perf_counter() - start_time)
    total_ocr_seconds = sum(page["ocr_elapsed_seconds"] for page in pages)
    total_characters = sum(page["character_count"] for page in pages)
    ocr_pages = sum(1 for page in pages if page["ocr_applied"])

    register_log(
        logger,
        (
            "Extração PDF completada. "
            f"páginas={len(pages)}, "
            f"ocr_pages={ocr_pages}, "
            f"characters={total_characters}, "
            f"ocr_time={total_ocr_seconds:.3f}s, "
            f"total_time={total_elapsed_seconds:.3f}s"
        )
    )

    print("\n" + "=" * 70)
    print("RESUMO DA EXTRAÇÃO PDF RAPIDOCR")
    print("=" * 70)

    print(f"PDF: {pdf_path.name}")
    print(f"Páginas processadas: {len(pages)}")
    print(f"Páginas usando OCR: {ocr_pages}")
    print(f"Total de caracteres: {total_characters}")

    print(f"Tempo de inferência OCR: " f"{total_ocr_seconds:.2f} seconds")
    print(f"Tempo total de processamento: " f"{total_elapsed_seconds:.2f} seconds")
    print("=" * 70)

    return pages


def print_first_pages(pages: list[dict], limit: int = PREVIEW_PAGE_COUNT) -> None:
    print("\n" + "=" * 70)
    print("PREVIEW DA EXTRAÇÃO PDF RAPIDOCR")
    print("=" * 70)

    for page in pages[:limit]:
        print("\n" + "-" * 70)
        print(f"Página: {page['page_number']} | " f"OCR: {page['ocr_applied']} | " f"Caracteres: {page['character_count']}")
        print(f"OCR LINES: {page['ocr_line_count']} | " f"OCR TIME: {page['ocr_elapsed_seconds']:.3f}s | " f"TOTAL TIME: {page['elapsed_seconds']:.3f}s")
        print(f"OCR CONFIDENCE: " f"{page['ocr_confidence']}")
        print("-" * 70)
        print(page["text"] if page["text"] else "[SEM TEXTO EXTRAÍDO]")

    print("\n" + "=" * 70)
    print("FIM DO PREVIEW")
    print("=" * 70 + "\n")