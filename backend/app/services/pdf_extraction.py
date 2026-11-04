from __future__ import annotations

import io
import logging
from typing import List, Dict, Any
from pypdf import PdfReader
from pdf2image import convert_from_bytes
from app.services.ocr import OCRService

logger = logging.getLogger(__name__)


class PDFExtractionService:
    @staticmethod
    def extract_text_with_pages(pdf_bytes: bytes) -> List[Dict[str, Any]]:
        """
        Extracts text page by page from raw PDF bytes.
        If a page contains near-empty extractable text (scanned or image-only page),
        it rasterizes that specific page and falls back to OCR.
        """
        try:
            pdf_file = io.BytesIO(pdf_bytes)
            reader = PdfReader(pdf_file)
            extracted_pages: List[Dict[str, Any]] = []

            for page_num, page in enumerate(reader.pages, start=1):
                text = page.extract_text()
                cleaned_text = text.strip() if text else ""

                # Fallback to OCR if page text layer is near-empty (< 20 characters)
                if len(cleaned_text) < 20:
                    logger.info(f"Page {page_num} has sparse text layer ({len(cleaned_text)} chars). Triggering OCR fallback...")
                    try:
                        # Convert specific page using pdf2image (first_page and last_page are 1-indexed)
                        images = convert_from_bytes(
                            pdf_bytes,
                            first_page=page_num,
                            last_page=page_num,
                            dpi=200
                        )
                        if images:
                            ocr_text = OCRService.extract_text_from_image(images[0])
                            if len(ocr_text) > len(cleaned_text):
                                cleaned_text = ocr_text
                    except Exception as ocr_err:
                        logger.warning(f"OCR fallback failed for page {page_num}: {ocr_err}")

                if cleaned_text:
                    extracted_pages.append({
                        "page_number": page_num,
                        "content": cleaned_text
                    })

            return extracted_pages
        except Exception as e:
            logger.error(f"Failed to extract text from PDF: {e}")
            raise ValueError("Invalid or corrupted PDF file.")