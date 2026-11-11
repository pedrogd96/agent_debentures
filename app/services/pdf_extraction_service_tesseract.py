import logging

from io import BytesIO
from pathlib import Path

import pymupdf
import pytesseract

from PIL import Image

from app.services.log_service import register_log


OCR_LANGUAGE = "por"
OCR_DPI = 300
OCR_CONFIG = "--oem 3 --psm 3"

MIN_IMAGE_AREA_RATIO = 0.08
PREVIEW_PAGE_COUNT = 10


def extract_native_text(page) -> str:
    return page.get_text("text", sort=True).strip()


def render_page_region(page, region=None) -> Image.Image:
    scale = OCR_DPI / 72
    matrix = pymupdf.Matrix(scale, scale)
    pixmap = page.get_pixmap(matrix=matrix, clip=region, alpha=False)
    image_bytes = pixmap.tobytes("png")

    with Image.open(BytesIO(image_bytes)) as source:
        return source.convert("RGB")


def run_ocr(image: Image.Image) -> str:
    return pytesseract.image_to_string(image, lang=OCR_LANGUAGE, config=OCR_CONFIG).strip()


def get_image_regions(page) -> list:
    page_data = page.get_text("dict")
    page_area = (page.rect.width * page.rect.height)

    regions = []
    seen_regions = set()

    for block in page_data["blocks"]:
        if block["type"] != 1:
            continue

        rectangle = pymupdf.Rect(block["bbox"]) & page.rect

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


def extract_page_text(page, page_number: int, logger: logging.Logger) -> dict:
    register_log(logger, f"Extraindo página {page_number}")

    native_text = extract_native_text(page)

    extracted_parts = []
    ocr_applied = False

    if native_text:
        extracted_parts.append(native_text)

    if not native_text:
        register_log(logger, f"Página {page_number}: rodando página inteira com OCR")
        image = render_page_region(page)
        ocr_text = run_ocr(image)

        if ocr_text:
            extracted_parts.append(ocr_text)

        ocr_applied = True

    else:
        image_regions = get_image_regions(page)
        for image_index, region in enumerate(image_regions, start=1):
            register_log(logger, (f"Página {page_number}: rodando OCR " f"na região da imagem {image_index}"))

            image = render_page_region(page, region)
            ocr_text = run_ocr(image)

            if ocr_text:
                extracted_parts.append(ocr_text)

            ocr_applied = True

    final_text = "\n\n".join(part for part in extracted_parts if part).strip()

    register_log(logger, (f"Página {page_number}: " f"{len(final_text)} caracteres extraídos; " f"OCR applied: {ocr_applied}"))

    return {
        "page_number": page_number,
        "text": final_text,
        "ocr_applied": ocr_applied,
        "character_count": len(final_text)
    }


def extract_pdf_text(pdf_path: str | Path, logger: logging.Logger) -> list[dict]:
    pdf_path = Path(pdf_path)

    if not pdf_path.is_file():
        raise FileNotFoundError(f"Arquivo PDF não encontrado: {pdf_path}")

    register_log(logger, f"Iniciando extração PDF: {pdf_path.name}")

    pages = []

    with pymupdf.open(pdf_path) as document:
        if document.needs_pass:
            raise ValueError("Proteção de senha no PDF não suportado.")

        total_pages = len(document)
        register_log(logger, f"Páginas totais: {total_pages}")

        for page_index in range(total_pages):
            page = document.load_page(page_index)
            page_number = page_index + 1
            result = extract_page_text(page=page, page_number=page_number, logger=logger)
            pages.append(result)

    register_log(logger, "Extração PDF completada")

    return pages


def print_first_pages(pages: list[dict], limit: int = PREVIEW_PAGE_COUNT) -> None:
    print("\n" + "=" * 70)
    print("PREVIEW DA EXTRAÇÃO PDF")
    print("=" * 70)

    for page in pages[:limit]:
        print("\n" + "-" * 70)
        print(f"PÁGINAS: {page['page_number']} | " f"OCR: {page['ocr_applied']} | " f"CARACTERES: {page['character_count']}")
        print("-" * 70)
        print(page["text"] if page["text"] else "[SEM TEXTO EXTRAÍDO]")

    print("\n" + "=" * 70)
    print("FIM DO PREVIEW")
    print("=" * 70 + "\n")