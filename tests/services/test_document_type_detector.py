"""DEV-421: Tests for Document Type Auto-Detection.

Tests: XML fattura detection, PDF F24, PDF bilancio, ambiguous documents.
"""

import pytest

from app.services.document_type_detector import DocumentTypeDetector


@pytest.fixture
def detector():
    return DocumentTypeDetector()


class TestDetectByExtension:
    def test_xml_detected(self, detector):
        result = detector.detect("fattura.xml", content=None, mime_type="text/xml")
        assert result["detected_type"] == "fattura_elettronica"
        assert result["confidence"] >= 0.7

    def test_pdf_default(self, detector):
        result = detector.detect("document.pdf", content=None, mime_type="application/pdf")
        assert result["detected_type"] in ("unknown", "generic_pdf")

    def test_xlsx_detected(self, detector):
        result = detector.detect(
            "bilancio_2025.xlsx",
            content=None,
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        assert result["detected_type"] == "bilancio"
        assert result["confidence"] >= 0.5


class TestDetectByContent:
    def test_fattura_xml_by_namespace(self, detector):
        content = '<FatturaElettronica xmlns="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2">'
        result = detector.detect("doc.xml", content=content)
        assert result["detected_type"] == "fattura_elettronica"
        assert result["confidence"] >= 0.9

    def test_f24_by_keywords(self, detector):
        content = "MODELLO F24 SEZIONE ERARIO codice tributo 4001 PERIODO DI RIFERIMENTO"
        result = detector.detect("tax.pdf", content=content)
        assert result["detected_type"] == "f24"

    def test_cu_by_keywords(self, detector):
        content = "CERTIFICAZIONE UNICA 2026 REDDITI 2025 dati fiscali ritenute operate"
        result = detector.detect("cu.pdf", content=content)
        assert result["detected_type"] == "certificazione_unica"

    def test_bilancio_by_keywords(self, detector):
        content = "BILANCIO DI ESERCIZIO stato patrimoniale conto economico nota integrativa fatturato utile"
        result = detector.detect("report.pdf", content=content)
        assert result["detected_type"] == "bilancio"

    def test_busta_paga_by_keywords(self, detector):
        content = "BUSTA PAGA cedolino stipendio retribuzione lorda INPS trattenute netto"
        result = detector.detect("paga.pdf", content=content)
        assert result["detected_type"] == "busta_paga"


class TestAmbiguous:
    def test_unknown_document(self, detector):
        result = detector.detect("random.pdf", content="just some random text")
        assert result["confidence"] < 0.5

    def test_empty_filename(self, detector):
        result = detector.detect("", content=None)
        assert result["detected_type"] == "unknown"
