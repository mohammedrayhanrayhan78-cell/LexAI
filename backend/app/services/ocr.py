from __future__ import annotations

import logging
import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)


class OCRService:
    @staticmethod
    def extract_text_from_image(image: Image.Image) -> str:
        """
        Runs Tesseract OCR on a given PIL Image object to extract readable text.
        Requires 'tesseract-ocr' installed on the host/container system.
        """
        try:
            text = pytesseract.image_to_string(image)
            return text.strip()
        except Exception as e:
            logger.error(f"OCR execution failed on page image: {e}")
            return ""