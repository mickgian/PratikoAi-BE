"""DEV-390: Tests for OCR Service.

Tests cover:
- Image extraction with Tesseract (mocked at library boundary)
- PDF extraction with PyMuPDF (mocked at library boundary)
- Scanned-vs-native detection
- Confidence parsing with various data shapes
- Error handling for corrupted files, missing libraries
- Multi-page PDF extraction
"""

from unittest.mock import MagicMock, patch

import pytest

from app.services.ocr_service import OCRResult, OCRService

# Reusable patch targets
_P_IMAGE = "app.services.ocr_service.Image"
_P_TESS = "app.services.ocr_service.pytesseract"
_P_FITZ = "app.services.ocr_service.fitz"
_P_PIL_OK = "app.services.ocr_service.PIL_AVAILABLE"
_P_TESS_OK = "app.services.ocr_service.TESSERACT_AVAILABLE"
_P_FITZ_OK = "app.services.ocr_service.FITZ_AVAILABLE"


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #
def _tesseract_tsv(*rows: tuple[float, str]) -> str:
    """Build minimal Tesseract TSV output from (confidence, text) pairs."""
    header = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext"
    lines = [header]
    for conf, text in rows:
        lines.append(f"5\t1\t1\t1\t1\t1\t0\t0\t100\t50\t{conf}\t{text}")
    return "\n".join(lines)


def _setup_tess(mock_pil, mock_tess, *, tsv_rows=((95, "Hello"),), text="Hello"):
    """Wire up PIL + Tesseract mocks for a standard image extraction."""
    mock_img = MagicMock()
    mock_pil.open.return_value = mock_img
    mock_tess.Output.STRING = "string"
    mock_tess.image_to_data.return_value = _tesseract_tsv(*tsv_rows)
    mock_tess.image_to_string.return_value = text
    return mock_img


# ------------------------------------------------------------------ #
# Image extraction
# ------------------------------------------------------------------ #
class TestOCRImageExtraction:
    """Test image-based OCR extraction."""

    def setup_method(self) -> None:
        self.service = OCRService()

    @patch(_P_TESS_OK, True)
    @patch(_P_PIL_OK, True)
    @patch(_P_TESS)
    @patch(_P_IMAGE)
    def test_basic_text_extraction(self, mock_pil, mock_tess) -> None:
        _setup_tess(mock_pil, mock_tess, tsv_rows=((95, "Hello"), (90, "World")), text="Hello World")
        result = self.service.extract_text(b"image_bytes", filename="test.png")

        assert isinstance(result, OCRResult)
        assert result.text == "Hello World"
        assert result.text_found is True
        assert result.average_confidence > 0
        assert result.low_confidence is False
        assert result.language == "ita"

    @patch(_P_TESS_OK, True)
    @patch(_P_PIL_OK, True)
    @patch(_P_TESS)
    @patch(_P_IMAGE)
    def test_empty_image_no_text(self, mock_pil, mock_tess) -> None:
        _setup_tess(mock_pil, mock_tess, tsv_rows=(), text="")
        result = self.service.extract_text(b"blank", filename="blank.png")

        assert result.text == ""
        assert result.text_found is False
        assert result.average_confidence == 0.0

    @patch(_P_TESS_OK, True)
    @patch(_P_PIL_OK, True)
    @patch(_P_TESS)
    @patch(_P_IMAGE)
    def test_low_confidence_flagged(self, mock_pil, mock_tess) -> None:
        _setup_tess(mock_pil, mock_tess, tsv_rows=((30, "Blurry"), (25, "text")), text="Blurry text")
        result = self.service.extract_text(b"blurry", filename="blur.png")

        assert result.low_confidence is True
        assert result.average_confidence < 60.0

    @patch(_P_TESS_OK, True)
    @patch(_P_PIL_OK, True)
    @patch(_P_TESS)
    @patch(_P_IMAGE)
    def test_high_confidence_not_flagged(self, mock_pil, mock_tess) -> None:
        _setup_tess(mock_pil, mock_tess, tsv_rows=((95, "Clear"), (88, "text")), text="Clear text")
        result = self.service.extract_text(b"good", filename="good.png")

        assert result.low_confidence is False
        assert result.average_confidence >= 60.0

    @patch(_P_TESS_OK, True)
    @patch(_P_PIL_OK, True)
    @patch(_P_TESS)
    @patch(_P_IMAGE)
    def test_confidence_boundary_at_threshold(self, mock_pil, mock_tess) -> None:
        """Exactly 60% average confidence is NOT low_confidence."""
        _setup_tess(mock_pil, mock_tess, tsv_rows=((60, "Boundary"),), text="Boundary")
        result = self.service.extract_text(b"boundary", filename="b.png")

        assert result.average_confidence == 60.0
        assert result.low_confidence is False

    @patch(_P_TESS_OK, True)
    @patch(_P_PIL_OK, True)
    @patch(_P_TESS)
    @patch(_P_IMAGE)
    def test_invalid_confidence_values_skipped(self, mock_pil, mock_tess) -> None:
        """Non-numeric and zero confidence values are skipped."""
        mock_img = MagicMock()
        mock_pil.open.return_value = mock_img
        mock_tess.Output.STRING = "string"
        tsv = (
            "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
            "5\t1\t1\t1\t1\t1\t0\t0\t100\t50\tNaN\tBad\n"
            "5\t1\t1\t1\t1\t1\t0\t0\t100\t50\t0\tZero\n"
            "5\t1\t1\t1\t1\t1\t0\t0\t100\t50\t85\tGood\n"
        )
        mock_tess.image_to_data.return_value = tsv
        mock_tess.image_to_string.return_value = "Good"

        result = self.service.extract_text(b"mixed", filename="mixed.png")
        # Only 85 should count (NaN → ValueError, 0 is skipped)
        assert result.average_confidence == 85.0

    @patch(_P_TESS_OK, True)
    @patch(_P_PIL_OK, True)
    @patch(_P_TESS)
    @patch(_P_IMAGE)
    def test_short_tsv_lines_skipped(self, mock_pil, mock_tess) -> None:
        """TSV lines with fewer than 11 columns are skipped."""
        mock_img = MagicMock()
        mock_pil.open.return_value = mock_img
        mock_tess.Output.STRING = "string"
        tsv = (
            "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
            "5\t1\t1\n"
            "5\t1\t1\t1\t1\t1\t0\t0\t100\t50\t92\tOK\n"
        )
        mock_tess.image_to_data.return_value = tsv
        mock_tess.image_to_string.return_value = "OK"

        result = self.service.extract_text(b"short", filename="short.png")
        assert result.average_confidence == 92.0

    @patch(_P_TESS_OK, True)
    @patch(_P_PIL_OK, True)
    @patch(_P_IMAGE)
    def test_corrupted_image_returns_error(self, mock_pil) -> None:
        mock_pil.open.side_effect = OSError("Cannot identify image")
        result = self.service.extract_text(b"corrupt", filename="bad.png")

        assert result.error is not None
        assert result.text_found is False

    @patch(_P_TESS_OK, True)
    @patch(_P_PIL_OK, True)
    @patch(_P_TESS)
    @patch(_P_IMAGE)
    def test_custom_language(self, mock_pil, mock_tess) -> None:
        service = OCRService(language="eng")
        mock_img = _setup_tess(mock_pil, mock_tess, tsv_rows=((90, "English"),), text="English")

        result = service.extract_text(b"eng", filename="eng.png")
        assert result.language == "eng"
        mock_tess.image_to_data.assert_called_once_with(mock_img, lang="eng", output_type="string")


# ------------------------------------------------------------------ #
# Library unavailable
# ------------------------------------------------------------------ #
class TestOCRLibraryUnavailable:
    """Test graceful handling when OCR libraries are not installed."""

    def setup_method(self) -> None:
        self.service = OCRService()

    @patch(_P_TESS_OK, False)
    @patch(_P_PIL_OK, False)
    def test_image_no_libraries(self) -> None:
        result = self.service.extract_text(b"img", filename="test.png")
        assert result.error is not None
        assert "non disponibil" in result.error.lower()

    @patch(_P_TESS_OK, True)
    @patch(_P_PIL_OK, False)
    def test_image_no_pil(self) -> None:
        result = self.service.extract_text(b"img", filename="test.png")
        assert result.error is not None

    @patch(_P_FITZ_OK, False)
    def test_pdf_no_fitz(self) -> None:
        result = self.service.extract_text(b"pdf", filename="test.pdf")
        assert result.error is not None
        assert "fitz" in result.error.lower()


# ------------------------------------------------------------------ #
# PDF extraction
# ------------------------------------------------------------------ #
class TestOCRPDFExtraction:
    """Test PDF-based OCR extraction via PyMuPDF."""

    def setup_method(self) -> None:
        self.service = OCRService()

    def _make_fitz_doc(self, pages: list[MagicMock]) -> MagicMock:
        """Create a mock fitz document with context manager support."""
        mock_doc = MagicMock()
        mock_doc.__enter__ = lambda s: s
        mock_doc.__exit__ = lambda *a: None
        mock_doc.__iter__ = lambda s: iter(pages)
        mock_doc.__len__ = lambda s: len(pages)
        return mock_doc

    def _make_fitz_page(self) -> MagicMock:
        """Create a mock fitz page with pixmap."""
        page = MagicMock()
        pix = MagicMock()
        pix.tobytes.return_value = b"png_bytes"
        page.get_pixmap.return_value = pix
        return page

    @patch(_P_TESS_OK, True)
    @patch(_P_PIL_OK, True)
    @patch(_P_TESS)
    @patch(_P_IMAGE)
    @patch(_P_FITZ_OK, True)
    @patch(_P_FITZ)
    def test_single_page_pdf(self, mock_fitz, mock_pil, mock_tess) -> None:
        mock_fitz.open.return_value = self._make_fitz_doc([self._make_fitz_page()])
        _setup_tess(mock_pil, mock_tess, tsv_rows=((85, "PDF"), (90, "text")), text="PDF text")

        result = self.service.extract_text(b"pdf_bytes", filename="scan.pdf")

        assert result.text_found is True
        assert "PDF text" in result.text
        assert result.page_count == 1
        assert result.average_confidence > 0

    @patch(_P_TESS_OK, True)
    @patch(_P_PIL_OK, True)
    @patch(_P_TESS)
    @patch(_P_IMAGE)
    @patch(_P_FITZ_OK, True)
    @patch(_P_FITZ)
    def test_multi_page_pdf(self, mock_fitz, mock_pil, mock_tess) -> None:
        pages = [self._make_fitz_page() for _ in range(3)]
        mock_fitz.open.return_value = self._make_fitz_doc(pages)
        _setup_tess(mock_pil, mock_tess, tsv_rows=((80, "Page"),), text="Page content")

        result = self.service.extract_text(b"big_pdf", filename="multi.pdf")

        assert result.page_count == 3
        assert result.text.count("Page content") == 3

    @patch(_P_FITZ_OK, True)
    @patch(_P_FITZ)
    def test_encrypted_pdf_returns_error(self, mock_fitz) -> None:
        mock_fitz.open.side_effect = RuntimeError("encrypted")
        result = self.service.extract_text(b"enc_pdf", filename="locked.pdf")
        assert result.error is not None

    @patch(_P_FITZ_OK, False)
    def test_pdf_routing_by_filename(self) -> None:
        """Filename ending in .pdf routes to PDF extraction."""
        result = self.service.extract_text(b"data", filename="document.PDF")
        assert result.error is not None
        assert "fitz" in result.error.lower()

    @patch(_P_TESS_OK, True)
    @patch(_P_PIL_OK, True)
    @patch(_P_TESS)
    @patch(_P_IMAGE)
    @patch(_P_FITZ_OK, True)
    @patch(_P_FITZ)
    def test_pdf_page_with_no_text_produces_empty(self, mock_fitz, mock_pil, mock_tess) -> None:
        mock_fitz.open.return_value = self._make_fitz_doc([self._make_fitz_page()])
        _setup_tess(mock_pil, mock_tess, tsv_rows=(), text="")

        result = self.service.extract_text(b"blank_pdf", filename="blank.pdf")

        assert result.text_found is False
        assert result.average_confidence == 0.0


# ------------------------------------------------------------------ #
# Scanned detection
# ------------------------------------------------------------------ #
class TestOCRScannedDetection:
    """Test detect_if_scanned()."""

    def setup_method(self) -> None:
        self.service = OCRService()

    @patch(_P_FITZ_OK, True)
    @patch(_P_FITZ)
    def test_native_pdf_detected(self, mock_fitz) -> None:
        mock_page = MagicMock()
        mock_page.get_text.return_value = "This is a native text PDF with enough characters to pass."
        mock_doc = MagicMock()
        mock_doc.__enter__ = lambda s: s
        mock_doc.__exit__ = lambda *a: None
        mock_doc.__iter__ = lambda s: iter([mock_page])
        mock_fitz.open.return_value = mock_doc

        assert self.service.detect_if_scanned(b"pdf", filename="native.pdf") is False

    @patch(_P_FITZ_OK, True)
    @patch(_P_FITZ)
    def test_scanned_pdf_detected(self, mock_fitz) -> None:
        mock_page = MagicMock()
        mock_page.get_text.return_value = ""
        mock_doc = MagicMock()
        mock_doc.__enter__ = lambda s: s
        mock_doc.__exit__ = lambda *a: None
        mock_doc.__iter__ = lambda s: iter([mock_page])
        mock_fitz.open.return_value = mock_doc

        assert self.service.detect_if_scanned(b"pdf", filename="scan.pdf") is True

    @patch(_P_FITZ_OK, False)
    def test_fitz_unavailable_assumes_scanned(self) -> None:
        assert self.service.detect_if_scanned(b"pdf", filename="unknown.pdf") is True

    @patch(_P_FITZ_OK, True)
    @patch(_P_FITZ)
    def test_fitz_error_assumes_scanned(self, mock_fitz) -> None:
        mock_fitz.open.side_effect = RuntimeError("broken")
        assert self.service.detect_if_scanned(b"pdf", filename="broken.pdf") is True

    @patch(_P_FITZ_OK, True)
    @patch(_P_FITZ)
    def test_short_text_page_considered_scanned(self, mock_fitz) -> None:
        """Page with text < 30 chars is considered scanned."""
        mock_page = MagicMock()
        mock_page.get_text.return_value = "Short"
        mock_doc = MagicMock()
        mock_doc.__enter__ = lambda s: s
        mock_doc.__exit__ = lambda *a: None
        mock_doc.__iter__ = lambda s: iter([mock_page])
        mock_fitz.open.return_value = mock_doc

        assert self.service.detect_if_scanned(b"pdf", filename="tiny.pdf") is True


# ------------------------------------------------------------------ #
# OCRResult dataclass
# ------------------------------------------------------------------ #
class TestOCRResult:
    """Test OCRResult dataclass defaults."""

    def test_defaults(self) -> None:
        result = OCRResult()
        assert result.text == ""
        assert result.text_found is False
        assert result.average_confidence == 0.0
        assert result.low_confidence is False
        assert result.language == "ita"
        assert result.page_count == 1
        assert result.error is None

    def test_custom_values(self) -> None:
        result = OCRResult(
            text="Ciao",
            text_found=True,
            average_confidence=92.5,
            language="eng",
            page_count=5,
        )
        assert result.text == "Ciao"
        assert result.page_count == 5
        assert result.language == "eng"
