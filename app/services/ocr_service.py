"""DEV-390: OCR Service for Scanned Document Text Extraction.

Extracts text from images and scanned PDFs using Tesseract OCR
with Italian language support.
"""

from dataclasses import dataclass, field
from io import BytesIO
from typing import Any

from app.core.logging import logger

try:
    import pytesseract  # type: ignore[import-untyped]

    TESSERACT_AVAILABLE = True
except ImportError:
    pytesseract = None  # type: ignore[assignment]
    TESSERACT_AVAILABLE = False

try:
    from PIL import Image  # type: ignore[import-untyped]

    PIL_AVAILABLE = True
except ImportError:
    Image = None  # type: ignore[assignment, misc]
    PIL_AVAILABLE = False

try:
    import fitz  # type: ignore[import-untyped]  # PyMuPDF

    FITZ_AVAILABLE = True
except ImportError:
    fitz = None  # type: ignore[assignment]
    FITZ_AVAILABLE = False

# Default confidence threshold (%)
_CONFIDENCE_THRESHOLD = 60.0

# Minimum text length to consider a page as "native" (not scanned)
_NATIVE_TEXT_MIN_LENGTH = 30


@dataclass
class OCRResult:
    """Result of an OCR extraction."""

    text: str = ""
    text_found: bool = False
    average_confidence: float = 0.0
    low_confidence: bool = False
    language: str = "ita"
    page_count: int = 1
    error: str | None = None


class OCRService:
    """OCR service for extracting text from images and scanned PDFs.

    Uses Tesseract with Italian language model by default.
    """

    def __init__(self, language: str = "ita") -> None:
        self.language = language

    def extract_text(
        self,
        file_bytes: bytes,
        *,
        filename: str = "",
    ) -> OCRResult:
        """Extract text from an image or scanned PDF.

        Args:
            file_bytes: Raw file bytes.
            filename: Original filename (used to detect PDF vs image).

        Returns:
            OCRResult with extracted text and metadata.
        """
        is_pdf = filename.lower().endswith(".pdf")

        if is_pdf:
            return self._extract_from_pdf(file_bytes, filename)
        return self._extract_from_image(file_bytes, filename)

    def detect_if_scanned(self, file_bytes: bytes, *, filename: str = "") -> bool:
        """Detect whether a PDF is scanned (image-based) or native text.

        Args:
            file_bytes: Raw PDF bytes.
            filename: Original filename.

        Returns:
            True if the PDF appears to be scanned.
        """
        if not FITZ_AVAILABLE:
            logger.warning("ocr_fitz_unavailable", action="assume_scanned")
            return True

        try:
            with fitz.open(stream=file_bytes, filetype="pdf") as doc:
                for page in doc:
                    text = page.get_text().strip()
                    if len(text) >= _NATIVE_TEXT_MIN_LENGTH:
                        return False
            return True
        except Exception as e:
            logger.error("ocr_scanned_detection_error", error=str(e), filename=filename)
            return True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_from_image(self, file_bytes: bytes, filename: str) -> OCRResult:
        """OCR an image file."""
        if not TESSERACT_AVAILABLE or not PIL_AVAILABLE:
            return OCRResult(error="Tesseract o PIL non disponibili")

        try:
            img = Image.open(BytesIO(file_bytes))
            return self._run_tesseract(img)
        except Exception as e:
            logger.error("ocr_image_error", error=str(e), filename=filename)
            return OCRResult(error=str(e))

    def _extract_from_pdf(self, file_bytes: bytes, filename: str) -> OCRResult:
        """OCR a scanned PDF by converting pages to images."""
        if not FITZ_AVAILABLE:
            return OCRResult(error="PyMuPDF (fitz) non disponibile")

        try:
            with fitz.open(stream=file_bytes, filetype="pdf") as doc:
                texts: list[str] = []
                confidences: list[float] = []

                for page in doc:
                    pix = page.get_pixmap(dpi=300)
                    img_bytes = pix.tobytes("png")
                    page_result = self._extract_from_image(img_bytes, filename)
                    if page_result.text:
                        texts.append(page_result.text)
                    if page_result.average_confidence > 0:
                        confidences.append(page_result.average_confidence)

                combined_text = "\n\n".join(texts)
                avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

                return OCRResult(
                    text=combined_text,
                    text_found=bool(combined_text.strip()),
                    average_confidence=avg_conf,
                    low_confidence=avg_conf < _CONFIDENCE_THRESHOLD,
                    language=self.language,
                    page_count=len(doc),
                )
        except Exception as e:
            logger.error("ocr_pdf_error", error=str(e), filename=filename)
            return OCRResult(error=str(e))

    def _run_tesseract(self, img: Any) -> OCRResult:
        """Run Tesseract OCR on a PIL Image and return structured result."""
        raw_data = pytesseract.image_to_data(img, lang=self.language, output_type=pytesseract.Output.STRING)
        text = pytesseract.image_to_string(img, lang=self.language).strip()

        # Parse confidence values from TSV output
        confidences: list[float] = []
        for line in raw_data.strip().split("\n")[1:]:
            parts = line.split("\t")
            if len(parts) >= 11:
                try:
                    conf = float(parts[10])
                    if conf > 0:
                        confidences.append(conf)
                except ValueError:
                    pass

        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

        return OCRResult(
            text=text,
            text_found=bool(text),
            average_confidence=avg_conf,
            low_confidence=avg_conf < _CONFIDENCE_THRESHOLD,
            language=self.language,
        )
