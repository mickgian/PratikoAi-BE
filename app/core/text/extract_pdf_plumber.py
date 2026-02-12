"""PDF text extraction using pdfplumber + Tesseract OCR (MIT/Apache-2.0 licenses).

This module provides quality-aware PDF extraction using:
- Primary: pdfplumber (MIT) for fast, high-quality text extraction
- Fallback: Tesseract OCR (Apache-2.0) when text quality is poor
- Quality metrics: Automatically detects corrupted/low-quality text
- Italian language support: Tesseract 'ita' model

Replaces PyMuPDF/fitz (AGPL) with fully permissive open-source stack.

Usage:
    result = extract_pdf_with_ocr_fallback_plumber("/path/to/doc.pdf")
    # Returns: {
    #   "pages": [...],
    #   "full_text": "...",
    #   "extraction_method": "pdfplumber"|"mixed",
    #   "text_quality": 0.0-1.0,
    #   "ocr_pages": [...]
    # }
"""

import logging
import re
from dataclasses import (
    asdict,
    dataclass,
)
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
)

from app.core.config import (
    OCR_ENABLED,
    OCR_LANGUAGES,
    OCR_MAX_PAGES,
    OCR_MIN_PAGE_WIDTH,
    OCR_PAGE_SAMPLE,
)

# Import shared text quality metrics
from app.core.text.extract_pdf import text_metrics

logger = logging.getLogger(__name__)

# Try to import PDF processing dependencies
try:
    import pdfplumber

    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    logger.warning("pdfplumber not available. Install: pip install pdfplumber")

try:
    from pdf2image import convert_from_path
    from PIL import Image

    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    logger.warning("pdf2image not available. Install: pip install pdf2image Pillow")

try:
    import pytesseract

    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False
    logger.warning("pytesseract not available. Install: pip install pytesseract")


@dataclass
class PageOutput:
    """Output data for a single page"""

    page: int
    text: str
    ocr_used: bool
    quality: dict[str, Any]


def _clean_text(text: str) -> str:
    """Clean extracted text by normalizing whitespace.

    Args:
        text: Raw text

    Returns:
        Cleaned text with normalized whitespace
    """
    if not text:
        return ""
    # Repair broken hyphenation BEFORE collapsing whitespace so the
    # "letter- letter" pattern is still visible.
    from app.core.text.hyphenation import repair_broken_hyphenation

    text = repair_broken_hyphenation(text)
    # Normalize multiple spaces/newlines to single space
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _rasterize_page(pdf_path: str, page_index: int, min_width: int = OCR_MIN_PAGE_WIDTH) -> Image.Image:
    """Rasterize a single PDF page for OCR using pdf2image.

    Args:
        pdf_path: Path to PDF file
        page_index: 0-based page index
        min_width: Minimum raster width in pixels

    Returns:
        PIL Image

    Raises:
        RuntimeError: If pdf2image not available
        Exception: For rasterization errors
    """
    if not PDF2IMAGE_AVAILABLE:
        raise RuntimeError("pdf2image not available. Install: pip install pdf2image Pillow")

    try:
        # pdf2image uses 1-based page numbers
        images = convert_from_path(
            pdf_path,
            first_page=page_index + 1,
            last_page=page_index + 1,
            fmt="png",
            dpi=200,  # Good balance of quality and speed
        )

        if not images:
            raise Exception(f"No images returned for page {page_index}")

        img = images[0]

        # Scale up if needed for better OCR
        if img.width < min_width:
            scale = min_width / float(img.width)
            new_width = min_width
            new_height = int(img.height * scale)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        logger.debug(f"Rasterized page {page_index}: {img.width}x{img.height}px")
        return img

    except Exception as e:
        logger.error(f"Failed to rasterize page {page_index} of {pdf_path}: {e}", exc_info=True)
        raise


def _ocr_page(image: Image.Image, lang: str = OCR_LANGUAGES) -> str:
    """OCR a single page image using Tesseract.

    Args:
        image: PIL Image to OCR
        lang: Tesseract language code (default: 'ita')

    Returns:
        Extracted text or empty string on error

    Raises:
        RuntimeError: If pytesseract not available
    """
    if not PYTESSERACT_AVAILABLE:
        raise RuntimeError("pytesseract not available. Install: pip install pytesseract")

    try:
        text = pytesseract.image_to_string(image, lang=lang)
        return _clean_text(text)

    except pytesseract.TesseractNotFoundError:
        logger.error(
            "Tesseract not installed. "
            "macOS: brew install tesseract tesseract-lang | "
            "Linux: apt-get install tesseract-ocr tesseract-ocr-ita"
        )
        return ""

    except Exception as e:
        logger.error(f"OCR failed: {e}", exc_info=True)
        return ""


def extract_pdf_with_ocr_fallback_plumber(pdf_path: str | Path) -> dict[str, Any]:
    """Extract PDF text with intelligent OCR fallback for low-quality pages using pdfplumber.

    Process:
    1. Extract all pages using pdfplumber
    2. Compute quality metrics for each page
    3. Sample first N pages to determine if OCR is needed
    4. If OCR enabled and needed, re-extract low-quality pages via OCR
    5. Return consolidated result with extraction method and quality scores

    Args:
        pdf_path: Path to PDF file

    Returns:
        Dictionary with:
        - pages: List[{"page": int, "text": str, "ocr_used": bool, "quality": {...}}]
        - full_text: str - Concatenated clean text from all pages
        - extraction_method: "pdfplumber" | "mixed"
        - text_quality: Float (0.0-1.0), average page quality
        - ocr_pages: List[{"page": int, "reason": str}]

    Raises:
        FileNotFoundError: If PDF file doesn't exist
        RuntimeError: If pdfplumber not available
    """
    pdf_path = Path(pdf_path) if isinstance(pdf_path, str) else pdf_path

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    if not PDFPLUMBER_AVAILABLE:
        raise RuntimeError("pdfplumber not available. Install: pip install pdfplumber")

    pages: list[PageOutput] = []
    ocr_pages_list: list[dict[str, Any]] = []
    needs_ocr_flags: list[bool] = []

    # Step 1: Extract all pages using pdfplumber
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                # Extract text
                raw_text = page.extract_text() or ""
                clean_txt = _clean_text(raw_text)

                # Compute quality metrics
                metrics = text_metrics(clean_txt)

                # Determine if this page needs OCR
                looks_junk = metrics.get("looks_junk", False) or len(clean_txt) < 50

                needs_ocr_flags.append(looks_junk)

                pages.append(PageOutput(page=i, text=clean_txt, ocr_used=False, quality=metrics))

        logger.info(f"Extracted {len(pages)} pages from {pdf_path.name} using pdfplumber")

    except Exception as e:
        logger.error(f"pdfplumber extraction failed for {pdf_path}: {e}", exc_info=True)
        return {
            "pages": [],
            "full_text": "",
            "extraction_method": "error",
            "text_quality": 0.0,
            "ocr_pages": [],
            "error": str(e),
        }

    # Step 2: Decide if OCR is needed by sampling first N pages
    sample_size = min(OCR_PAGE_SAMPLE, len(needs_ocr_flags))
    sample_needs_ocr = any(needs_ocr_flags[:sample_size])

    logger.info(f"PDF {pdf_path.name}: sampled {sample_size} pages, OCR needed: {sample_needs_ocr}")

    did_ocr_any = False

    # Step 3: Apply OCR if enabled and needed
    if OCR_ENABLED and sample_needs_ocr and PDF2IMAGE_AVAILABLE and PYTESSERACT_AVAILABLE:
        ocr_budget = OCR_MAX_PAGES

        for page_out in pages:
            if ocr_budget <= 0:
                break

            if needs_ocr_flags[page_out.page]:
                logger.info(f"Applying OCR to page {page_out.page} of {pdf_path.name}")

                try:
                    # Rasterize page
                    image = _rasterize_page(str(pdf_path), page_out.page)

                    # Run OCR
                    ocr_text = _ocr_page(image)

                    # Compute new metrics
                    ocr_metrics = text_metrics(ocr_text)

                    # Use OCR result if it's clearly better
                    # (not junk AND longer or similar length)
                    if not ocr_metrics.get("looks_junk", True) and len(ocr_text) >= len(page_out.text):
                        page_out.text = ocr_text
                        page_out.ocr_used = True
                        page_out.quality = ocr_metrics

                        ocr_pages_list.append({"page": page_out.page, "reason": "low_quality_text_extracted"})

                        did_ocr_any = True
                        ocr_budget -= 1

                        logger.info(f"OCR improved page {page_out.page}: quality {ocr_metrics['quality_score']:.2f}")
                    else:
                        logger.info(f"OCR did not improve page {page_out.page}, keeping original")

                except Exception as e:
                    logger.warning(f"OCR failed on page {page_out.page}: {e}")
                    # Keep original text

    elif OCR_ENABLED and sample_needs_ocr and not (PDF2IMAGE_AVAILABLE and PYTESSERACT_AVAILABLE):
        logger.warning(
            f"OCR needed for {pdf_path.name} but OCR dependencies not available. "
            f"Install: pip install pdf2image pytesseract Pillow"
        )

    # Step 4: Build full text from clean pages
    full_text = "\n\n".join(p.text for p in pages if p.text)

    # Step 5: Calculate average quality
    quality_scores = [p.quality.get("quality_score", 0.0) for p in pages]
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

    # Step 6: Determine extraction method
    extraction_method = "pdfplumber"
    if did_ocr_any:
        extraction_method = "mixed"

    result = {
        "pages": [asdict(p) for p in pages],
        "full_text": full_text,
        "extraction_method": extraction_method,
        "text_quality": round(avg_quality, 3),
        "ocr_pages": ocr_pages_list,
    }

    logger.info(
        f"PDF extraction complete for {pdf_path.name}: "
        f"method={extraction_method}, quality={avg_quality:.2f}, "
        f"OCR pages={len(ocr_pages_list)}"
    )

    return result
