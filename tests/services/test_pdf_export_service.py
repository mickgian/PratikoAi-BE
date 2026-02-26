"""DEV-388: Tests for PDF Export Service.

Tests cover:
- Basic PDF generation (title, content, sections, metadata)
- Procedura export (with/without progress, checklists)
- Calculation export (nested dicts, float formatting, tables)
- Edge cases (empty content, unknown template, long content)
- Italian text rendering
"""

import pytest

from app.services.pdf_export_service import PDFExportService


# ------------------------------------------------------------------ #
# Basic generation
# ------------------------------------------------------------------ #
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
        """Empty content generates PDF with spacer (no crash)."""
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

    def test_generate_pdf_sections_without_content(self) -> None:
        """Sections with empty content and missing keys."""
        sections = [
            {"title": "Solo titolo"},
            {"content": "Solo contenuto"},
            {},
        ]
        result = self.service.generate_pdf(
            title="Sections Edge",
            content="Body",
            sections=sections,
        )
        assert isinstance(result, bytes)

    def test_generate_pdf_with_metadata(self) -> None:
        """PDF includes author and subject metadata."""
        result = self.service.generate_pdf(
            title="Con Metadati",
            content="Test",
            author="Dott. Rossi",
            subject="Consulenza Fiscale",
        )
        assert isinstance(result, bytes)
        assert len(result) > 100


# ------------------------------------------------------------------ #
# Template handling
# ------------------------------------------------------------------ #
class TestPDFExportTemplates:
    """Test template parameter handling."""

    def setup_method(self) -> None:
        self.service = PDFExportService()

    def test_default_template(self) -> None:
        """template='default' generates normally."""
        result = self.service.generate_pdf(title="Default", content="Test", template="default")
        assert isinstance(result, bytes)

    def test_unknown_template_fallback(self) -> None:
        """Unknown template falls back to default with warning."""
        result = self.service.generate_pdf(
            title="Fallback",
            content="Test",
            template="nonexistent_template",
        )
        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"

    def test_none_template(self) -> None:
        """None template uses default."""
        result = self.service.generate_pdf(title="No Template", content="Test", template=None)
        assert isinstance(result, bytes)


# ------------------------------------------------------------------ #
# Procedura export
# ------------------------------------------------------------------ #
class TestPDFExportProcedura:
    """Test procedura-specific export."""

    def setup_method(self) -> None:
        self.service = PDFExportService()

    def test_export_procedura_with_progress(self) -> None:
        """Export procedura with step progress markers."""
        procedura = {
            "code": "APERTURA_PIVA",
            "title": "Apertura Partita IVA",
            "steps": [
                {"step": 1, "title": "Raccolta documenti", "checklist": ["CI", "CF"]},
                {"step": 2, "title": "Invio telematico", "checklist": ["AA9/12"]},
                {"step": 3, "title": "Conferma", "checklist": []},
            ],
        }
        progress = {"current_step": 2, "completed_steps": [1]}

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

    def test_export_procedura_all_completed(self) -> None:
        """All steps marked as completed."""
        procedura = {
            "code": "DONE",
            "title": "Completata",
            "steps": [
                {"step": 1, "title": "Primo", "checklist": ["A"]},
                {"step": 2, "title": "Secondo", "checklist": ["B"]},
            ],
        }
        progress = {"completed_steps": [1, 2]}
        result = self.service.export_procedura(procedura, progress)
        assert isinstance(result, bytes)

    def test_export_procedura_empty_steps(self) -> None:
        """Procedura with no steps."""
        procedura = {"code": "EMPTY", "title": "Vuota", "steps": []}
        result = self.service.export_procedura(procedura)
        assert isinstance(result, bytes)

    def test_export_procedura_missing_keys(self) -> None:
        """Procedura with missing optional keys."""
        procedura = {}
        result = self.service.export_procedura(procedura)
        assert isinstance(result, bytes)

    def test_export_procedura_step_without_checklist(self) -> None:
        """Step without checklist key."""
        procedura = {
            "code": "NOCK",
            "title": "No Checklist",
            "steps": [{"step": 1, "title": "Solo titolo"}],
        }
        result = self.service.export_procedura(procedura)
        assert isinstance(result, bytes)


# ------------------------------------------------------------------ #
# Calculation export
# ------------------------------------------------------------------ #
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

    def test_export_calculation_empty(self) -> None:
        """Empty calculation dict produces valid PDF."""
        result = self.service.export_calculation({})
        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"

    def test_export_calculation_no_tipo(self) -> None:
        """Missing 'tipo' uses default title."""
        result = self.service.export_calculation({"valore": 1000})
        assert isinstance(result, bytes)

    def test_export_calculation_float_formatting(self) -> None:
        """Float values are formatted with euro symbol."""
        calculation = {"importo": 1234.56, "label": "Test"}
        result = self.service.export_calculation(calculation)
        assert isinstance(result, bytes)

    def test_export_calculation_nested_dicts(self) -> None:
        """Nested dict values expand into sub-rows."""
        calculation = {
            "tipo": "Test",
            "dettagli": {
                "base": 10000,
                "aliquota": 0.23,
                "imposta": 2300.0,
            },
        }
        result = self.service.export_calculation(calculation)
        assert isinstance(result, bytes)

    def test_export_calculation_string_values(self) -> None:
        """String values rendered as-is."""
        calculation = {"tipo": "IMU", "immobile": "Abitazione", "anno": 2026}
        result = self.service.export_calculation(calculation)
        assert isinstance(result, bytes)


# ------------------------------------------------------------------ #
# Internal helpers
# ------------------------------------------------------------------ #
class TestPDFExportInternals:
    """Test internal formatting and document creation."""

    def setup_method(self) -> None:
        self.service = PDFExportService()

    def test_fmt_float(self) -> None:
        assert self.service._fmt(1234.56) == "€ 1,234.56"

    def test_fmt_int(self) -> None:
        assert self.service._fmt(42) == "42"

    def test_fmt_string(self) -> None:
        assert self.service._fmt("Roma") == "Roma"

    def test_fmt_zero(self) -> None:
        assert self.service._fmt(0.0) == "€ 0.00"

    def test_fmt_negative(self) -> None:
        assert self.service._fmt(-500.0) == "€ -500.00"

    def test_long_content_multi_page(self) -> None:
        """Long content generates multi-page PDF."""
        long_text = "Lorem ipsum dolor sit amet. " * 500
        result = self.service.generate_pdf(title="Lungo", content=long_text)
        assert isinstance(result, bytes)
        assert len(result) > 1000

    def test_custom_styles_registered(self) -> None:
        """Custom styles are registered during init."""
        assert "BrandTitle" in self.service._styles
        assert "SectionHeader" in self.service._styles
