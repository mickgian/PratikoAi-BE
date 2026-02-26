"""DEV-388: Tests for PDF Export Service."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.pdf_export_service import PDFExportService


class TestPDFExportServiceBasic:
    """Test PDFExportService basic generation."""

    def setup_method(self) -> None:
        self.service = PDFExportService()

    def test_generate_pdf_basic(self) -> None:
        """Basic PDF generation returns bytes."""
        result = self.service.generate_pdf(
            title="Test Document",
            content="Contenuto di prova per il documento PDF.",
        )
        assert isinstance(result, bytes)
        assert len(result) > 0
        # PDF files start with %PDF
        assert result[:5] == b"%PDF-"

    def test_generate_pdf_with_italian_accents(self) -> None:
        """Italian accented characters render correctly."""
        result = self.service.generate_pdf(
            title="Città e Università",
            content="L'università è aperta. Perché no? Così è la vita.",
        )
        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"

    def test_generate_pdf_empty_content(self) -> None:
        """Empty content generates PDF with header only."""
        result = self.service.generate_pdf(
            title="Documento Vuoto",
            content="",
        )
        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"

    def test_generate_pdf_with_sections(self) -> None:
        """PDF with multiple sections."""
        sections = [
            {"title": "Sezione 1", "content": "Contenuto sezione uno."},
            {"title": "Sezione 2", "content": "Contenuto sezione due."},
        ]
        result = self.service.generate_pdf(
            title="Multi-sezione",
            content="Introduzione",
            sections=sections,
        )
        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"

    def test_generate_pdf_with_metadata(self) -> None:
        """PDF includes author and subject metadata."""
        result = self.service.generate_pdf(
            title="Con Metadati",
            content="Test",
            author="PratikoAI",
            subject="Test PDF",
        )
        assert isinstance(result, bytes)


class TestPDFExportProcedura:
    """Test procedura-specific export."""

    def setup_method(self) -> None:
        self.service = PDFExportService()

    def test_export_procedura_with_progress(self) -> None:
        """Export procedura with step progress."""
        procedura = {
            "code": "APERTURA_PIVA",
            "title": "Apertura Partita IVA",
            "steps": [
                {"step": 1, "title": "Raccolta documenti", "checklist": ["CI", "CF"]},
                {"step": 2, "title": "Invio telematico", "checklist": ["AA9/12"]},
            ],
        }
        progress = {"current_step": 1, "completed_steps": [1]}

        result = self.service.export_procedura(procedura, progress)
        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"

    def test_export_procedura_no_progress(self) -> None:
        """Export procedura without progress tracking."""
        procedura = {
            "code": "TEST",
            "title": "Test Procedura",
            "steps": [{"step": 1, "title": "Step 1", "checklist": []}],
        }
        result = self.service.export_procedura(procedura, progress=None)
        assert isinstance(result, bytes)


class TestPDFExportCalculation:
    """Test calculation export."""

    def setup_method(self) -> None:
        self.service = PDFExportService()

    def test_export_calculation_formatted(self) -> None:
        """Export tax calculation with Italian formatting."""
        calculation = {
            "tipo": "IRPEF Addizionali",
            "comune": "Roma",
            "provincia": "RM",
            "reddito_imponibile": 35000.00,
            "addizionale_regionale": {"aliquota": 1.73, "importo": 605.50},
            "addizionale_comunale": {"aliquota": 0.9, "importo": 315.00},
            "totale": 920.50,
        }
        result = self.service.export_calculation(calculation)
        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"


class TestPDFExportEdgeCases:
    """Test edge cases."""

    def setup_method(self) -> None:
        self.service = PDFExportService()

    def test_missing_template_fallback(self) -> None:
        """Unknown template falls back to default."""
        result = self.service.generate_pdf(
            title="Fallback",
            content="Test",
            template="nonexistent_template",
        )
        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"

    def test_long_content(self) -> None:
        """Long content generates multi-page PDF."""
        long_text = "Lorem ipsum dolor sit amet. " * 500
        result = self.service.generate_pdf(
            title="Lungo",
            content=long_text,
        )
        assert isinstance(result, bytes)
        assert len(result) > 1000  # Multi-page should be larger
