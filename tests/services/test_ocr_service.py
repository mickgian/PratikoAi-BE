"""DEV-390: Tests for OCR Service."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.ocr_service import OCRResult, OCRService


class TestOCRServiceBasic:
    """Test OCRService basic extraction."""

    def setup_method(self) -> None:
        self.service = OCRService()

    def test_extract_text_returns_result(self) -> None:
        """extract_text returns an OCRResult dataclass."""
        mock_img = MagicMock()
        with (
            patch("app.services.ocr_service.Image") as mock_pil,
            patch("app.services.ocr_service.pytesseract") as mock_tess,
            patch("app.services.ocr_service.PIL_AVAILABLE", True),
            patch("app.services.ocr_service.TESSERACT_AVAILABLE", True),
        ):
            mock_pil.open.return_value = mock_img
            mock_tess.Output.STRING = "string"
            mock_tess.image_to_data.return_value = (
                "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
                "5\t1\t1\t1\t1\t1\t0\t0\t100\t50\t95\tHello\n"
            )
            mock_tess.image_to_string.return_value = "Hello"
            result = self.service.extract_text(b"fake_image_bytes", filename="test.png")

        assert isinstance(result, OCRResult)
        assert result.text == "Hello"
        assert result.text_found is True

    def test_extract_empty_image(self) -> None:
        """Empty image returns empty string with text_found=False."""
        mock_img = MagicMock()
        with (
            patch("app.services.ocr_service.Image") as mock_pil,
            patch("app.services.ocr_service.pytesseract") as mock_tess,
            patch("app.services.ocr_service.PIL_AVAILABLE", True),
            patch("app.services.ocr_service.TESSERACT_AVAILABLE", True),
        ):
            mock_pil.open.return_value = mock_img
            mock_tess.Output.STRING = "string"
            mock_tess.image_to_data.return_value = (
                "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
            )
            mock_tess.image_to_string.return_value = ""
            result = self.service.extract_text(b"fake_image_bytes", filename="blank.png")

        assert result.text == ""
        assert result.text_found is False

    def test_low_confidence_flagged(self) -> None:
        """Low confidence (<60%) is flagged in result."""
        mock_img = MagicMock()
        with (
            patch("app.services.ocr_service.Image") as mock_pil,
            patch("app.services.ocr_service.pytesseract") as mock_tess,
            patch("app.services.ocr_service.PIL_AVAILABLE", True),
            patch("app.services.ocr_service.TESSERACT_AVAILABLE", True),
        ):
            mock_pil.open.return_value = mock_img
            mock_tess.Output.STRING = "string"
            mock_tess.image_to_data.return_value = (
                "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
                "5\t1\t1\t1\t1\t1\t0\t0\t100\t50\t40\tBlurry\n"
            )
            mock_tess.image_to_string.return_value = "Blurry"
            result = self.service.extract_text(b"fake_image_bytes", filename="blur.png")

        assert result.low_confidence is True
        assert result.average_confidence < 60.0


class TestOCRServiceScannedDetection:
    """Test scanned PDF detection."""

    def setup_method(self) -> None:
        self.service = OCRService()

    def test_detect_scanned_vs_native(self) -> None:
        """detect_if_scanned differentiates scanned from native PDF."""
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = "This is native text content that is long enough."
        mock_doc.__iter__ = lambda self: iter([mock_page])
        mock_doc.__len__ = lambda self: 1
        mock_doc.__enter__ = lambda self: self
        mock_doc.__exit__ = lambda *a: None

        with (
            patch("app.services.ocr_service.fitz") as mock_fitz,
            patch("app.services.ocr_service.FITZ_AVAILABLE", True),
        ):
            mock_fitz.open.return_value = mock_doc
            is_scanned = self.service.detect_if_scanned(b"fake_pdf", filename="native.pdf")

        assert is_scanned is False

    def test_detect_scanned_pdf(self) -> None:
        """Scanned PDF (no extractable text) is detected."""
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = ""
        mock_doc.__iter__ = lambda self: iter([mock_page])
        mock_doc.__len__ = lambda self: 1
        mock_doc.__enter__ = lambda self: self
        mock_doc.__exit__ = lambda *a: None

        with (
            patch("app.services.ocr_service.fitz") as mock_fitz,
            patch("app.services.ocr_service.FITZ_AVAILABLE", True),
        ):
            mock_fitz.open.return_value = mock_doc
            is_scanned = self.service.detect_if_scanned(b"fake_pdf", filename="scanned.pdf")

        assert is_scanned is True


class TestOCRServiceEdgeCases:
    """Test edge cases."""

    def setup_method(self) -> None:
        self.service = OCRService()

    def test_corrupted_file_handled(self) -> None:
        """Corrupted file returns error result."""
        with (
            patch("app.services.ocr_service.Image") as mock_img,
            patch("app.services.ocr_service.PIL_AVAILABLE", True),
            patch("app.services.ocr_service.TESSERACT_AVAILABLE", True),
        ):
            mock_img.open.side_effect = Exception("Corrupted image")
            result = self.service.extract_text(b"corrupt", filename="bad.png")

        assert result.text == ""
        assert result.text_found is False
        assert result.error is not None

    def test_password_protected_rejected(self) -> None:
        """Password-protected PDF returns error."""
        with (
            patch("app.services.ocr_service.fitz") as mock_fitz,
            patch("app.services.ocr_service.FITZ_AVAILABLE", True),
        ):
            mock_fitz.open.side_effect = Exception("encrypted")
            result = self.service.extract_text(b"encrypted_pdf", filename="locked.pdf")

        assert result.error is not None
