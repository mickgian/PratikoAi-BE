"""TDD Tests for DEV-237: Paragraph Extraction in Retrieval.

Tests for extracting and scoring relevant paragraphs from retrieved documents.

Coverage Target: 90%+ for new code.
"""

from unittest.mock import MagicMock

import pytest

# =============================================================================
# Sample Documents for Testing
# =============================================================================

SAMPLE_DOCUMENT_IVA = """Art. 16 DPR 633/72 - Aliquote IVA

1. L'aliquota IVA ordinaria è del 22% per la maggior parte dei beni e servizi commercializzati in Italia.

2. Aliquote ridotte sono previste per specifiche categorie di beni e servizi:
   - 10% per prodotti alimentari, servizi turistici e ristrutturazioni edilizie
   - 5% per alcune prestazioni socio-sanitarie e assistenziali
   - 4% per beni di prima necessità come pane, latte, frutta e verdura

3. Le cessioni intracomunitarie sono esenti con diritto a detrazione dell'IVA assolta sugli acquisti.

4. Per le operazioni con l'estero si applicano le regole sulla territorialità previste dagli articoli 7 e seguenti."""

SAMPLE_DOCUMENT_RAVVEDIMENTO = """Circolare n. 23/E del 2020 - Ravvedimento Operoso

Il ravvedimento operoso consente al contribuente di regolarizzare spontaneamente le violazioni fiscali.

Le sanzioni sono ridotte in base al tempo trascorso dalla violazione:
- Entro 30 giorni: sanzione ridotta a 1/10 del minimo
- Entro 90 giorni: sanzione ridotta a 1/9 del minimo
- Entro 1 anno: sanzione ridotta a 1/8 del minimo
- Oltre 1 anno: sanzione ridotta a 1/7 del minimo

Il versamento deve essere effettuato mediante modello F24 con i codici tributo appropriati.

È importante che il ravvedimento avvenga prima della notifica di atti di accertamento."""


# =============================================================================
# Paragraph Splitting Tests
# =============================================================================


class TestParagraphSplitting:
    """Tests for splitting documents into paragraphs."""

    def test_split_by_double_newline(self):
        """Test splitting paragraphs by double newline."""
        from app.services.paragraph_extractor import ParagraphExtractor

        extractor = ParagraphExtractor()
        paragraphs = extractor.split_paragraphs(SAMPLE_DOCUMENT_IVA)

        assert len(paragraphs) >= 4
        assert any("22%" in p.text for p in paragraphs)

    def test_split_preserves_numbered_paragraphs(self):
        """Test that numbered paragraphs (1., 2., etc.) are preserved."""
        from app.services.paragraph_extractor import ParagraphExtractor

        extractor = ParagraphExtractor()
        paragraphs = extractor.split_paragraphs(SAMPLE_DOCUMENT_IVA)

        # Each numbered section should be a separate paragraph
        numbered = [p for p in paragraphs if p.text.strip().startswith(("1.", "2.", "3.", "4."))]
        assert len(numbered) >= 3

    def test_split_empty_content(self):
        """Test splitting empty content returns empty list."""
        from app.services.paragraph_extractor import ParagraphExtractor

        extractor = ParagraphExtractor()
        paragraphs = extractor.split_paragraphs("")

        assert paragraphs == []

    def test_split_none_content(self):
        """Test splitting None content returns empty list."""
        from app.services.paragraph_extractor import ParagraphExtractor

        extractor = ParagraphExtractor()
        paragraphs = extractor.split_paragraphs(None)

        assert paragraphs == []

    def test_split_single_paragraph(self):
        """Test content with no splits returns single paragraph."""
        from app.services.paragraph_extractor import ParagraphExtractor

        extractor = ParagraphExtractor()
        content = "This is a single paragraph with no breaks."
        paragraphs = extractor.split_paragraphs(content)

        assert len(paragraphs) == 1
        assert paragraphs[0].text == content

    def test_paragraph_has_index(self):
        """Test that each paragraph has an index."""
        from app.services.paragraph_extractor import ParagraphExtractor

        extractor = ParagraphExtractor()
        paragraphs = extractor.split_paragraphs(SAMPLE_DOCUMENT_IVA)

        for i, para in enumerate(paragraphs):
            assert para.index == i


# =============================================================================
# Relevance Scoring Tests
# =============================================================================


class TestRelevanceScoring:
    """Tests for paragraph relevance scoring."""

    def test_score_paragraph_with_query_terms(self):
        """Test that paragraphs with query terms score higher."""
        from app.services.paragraph_extractor import ParagraphExtractor

        extractor = ParagraphExtractor()

        high_relevance = "L'aliquota IVA ordinaria è del 22% per beni e servizi."
        low_relevance = "Le cessioni intracomunitarie sono esenti."

        query = "aliquota IVA 22%"

        score_high = extractor.score_relevance(high_relevance, query)
        score_low = extractor.score_relevance(low_relevance, query)

        assert score_high > score_low

    def test_score_empty_paragraph(self):
        """Test scoring empty paragraph returns 0."""
        from app.services.paragraph_extractor import ParagraphExtractor

        extractor = ParagraphExtractor()
        score = extractor.score_relevance("", "aliquota IVA")

        assert score == 0.0

    def test_score_empty_query(self):
        """Test scoring with empty query returns 0."""
        from app.services.paragraph_extractor import ParagraphExtractor

        extractor = ParagraphExtractor()
        score = extractor.score_relevance("Some paragraph text", "")

        assert score == 0.0

    def test_score_case_insensitive(self):
        """Test that scoring is case insensitive."""
        from app.services.paragraph_extractor import ParagraphExtractor

        extractor = ParagraphExtractor()

        paragraph = "L'aliquota IVA ordinaria"
        query_upper = "ALIQUOTA IVA"
        query_lower = "aliquota iva"

        score_upper = extractor.score_relevance(paragraph, query_upper)
        score_lower = extractor.score_relevance(paragraph, query_lower)

        assert score_upper == score_lower

    def test_score_normalized_0_to_1(self):
        """Test that scores are normalized between 0 and 1."""
        from app.services.paragraph_extractor import ParagraphExtractor

        extractor = ParagraphExtractor()

        score = extractor.score_relevance(
            "L'aliquota IVA ordinaria è del 22%",
            "aliquota IVA 22%",
        )

        assert 0.0 <= score <= 1.0


# =============================================================================
# Best Paragraph Extraction Tests
# =============================================================================


class TestBestParagraphExtraction:
    """Tests for extracting best paragraphs from documents."""

    def test_extract_best_paragraph_for_query(self):
        """Test extracting the most relevant paragraph for a query."""
        from app.services.paragraph_extractor import ParagraphExtractor

        extractor = ParagraphExtractor()

        result = extractor.extract_best_paragraph(
            content=SAMPLE_DOCUMENT_IVA,
            query="aliquota IVA 22%",
            doc_id="doc_001",
        )

        assert result is not None
        assert result.paragraph_id is not None
        assert result.relevance_score > 0
        assert "22%" in result.excerpt or "aliquota" in result.excerpt.lower()

    def test_extract_returns_paragraph_id(self):
        """Test that extraction returns paragraph_id with doc_id prefix."""
        from app.services.paragraph_extractor import ParagraphExtractor

        extractor = ParagraphExtractor()

        result = extractor.extract_best_paragraph(
            content=SAMPLE_DOCUMENT_RAVVEDIMENTO,
            query="sanzioni ravvedimento",
            doc_id="circolare_23E",
        )

        assert "circolare_23E" in result.paragraph_id

    def test_extract_returns_relevance_score(self):
        """Test that extraction returns relevance score."""
        from app.services.paragraph_extractor import ParagraphExtractor

        extractor = ParagraphExtractor()

        result = extractor.extract_best_paragraph(
            content=SAMPLE_DOCUMENT_RAVVEDIMENTO,
            query="sanzioni ridotte",
            doc_id="doc_002",
        )

        assert isinstance(result.relevance_score, float)
        assert 0.0 <= result.relevance_score <= 1.0

    def test_extract_returns_excerpt(self):
        """Test that extraction returns excerpt within max length."""
        from app.services.paragraph_extractor import ParagraphExtractor

        extractor = ParagraphExtractor()

        result = extractor.extract_best_paragraph(
            content=SAMPLE_DOCUMENT_IVA,
            query="aliquote ridotte 10%",
            doc_id="doc_003",
        )

        assert result.excerpt is not None
        assert len(result.excerpt) <= 200  # Max excerpt length

    def test_extract_empty_content(self):
        """Test extraction from empty content returns None."""
        from app.services.paragraph_extractor import ParagraphExtractor

        extractor = ParagraphExtractor()

        result = extractor.extract_best_paragraph(
            content="",
            query="aliquota IVA",
            doc_id="doc_empty",
        )

        assert result is None

    def test_extract_top_n_paragraphs(self):
        """Test extracting top N most relevant paragraphs."""
        from app.services.paragraph_extractor import ParagraphExtractor

        extractor = ParagraphExtractor()

        results = extractor.extract_top_paragraphs(
            content=SAMPLE_DOCUMENT_IVA,
            query="aliquota IVA",
            doc_id="doc_004",
            top_n=3,
        )

        assert len(results) <= 3
        # Results should be sorted by relevance score descending
        scores = [r.relevance_score for r in results]
        assert scores == sorted(scores, reverse=True)


# =============================================================================
# ParagraphResult Schema Tests
# =============================================================================


class TestParagraphResultSchema:
    """Tests for ParagraphResult dataclass."""

    def test_paragraph_result_creation(self):
        """Test creating ParagraphResult with all fields."""
        from app.services.paragraph_extractor import ParagraphResult

        result = ParagraphResult(
            paragraph_id="doc_001_p2",
            paragraph_index=2,
            relevance_score=0.85,
            excerpt="L'aliquota IVA ordinaria è del 22%...",
            full_text="L'aliquota IVA ordinaria è del 22% per la maggior parte dei beni.",
        )

        assert result.paragraph_id == "doc_001_p2"
        assert result.paragraph_index == 2
        assert result.relevance_score == 0.85
        assert "22%" in result.excerpt

    def test_paragraph_result_to_dict(self):
        """Test converting ParagraphResult to dictionary."""
        from app.services.paragraph_extractor import ParagraphResult

        result = ParagraphResult(
            paragraph_id="doc_001_p0",
            paragraph_index=0,
            relevance_score=0.75,
            excerpt="Test excerpt",
            full_text="Test full text",
        )

        data = result.to_dict()

        assert data["paragraph_id"] == "doc_001_p0"
        assert data["paragraph_index"] == 0
        assert data["relevance_score"] == 0.75
        assert data["excerpt"] == "Test excerpt"


# =============================================================================
# Integration with Step 040 Tests
# =============================================================================


class TestStep040Integration:
    """Tests for integration with Step 040 context building."""

    def test_extract_for_kb_document(self):
        """Test extracting paragraph info for KB document metadata."""
        from app.services.paragraph_extractor import ParagraphExtractor

        extractor = ParagraphExtractor()

        kb_doc = {
            "id": "doc_iva_001",
            "content": SAMPLE_DOCUMENT_IVA,
            "title": "Art. 16 DPR 633/72",
        }

        result = extractor.extract_best_paragraph(
            content=kb_doc["content"],
            query="Qual è l'aliquota IVA ordinaria?",
            doc_id=kb_doc["id"],
        )

        # Result should be suitable for kb_sources_metadata
        assert result.paragraph_id.startswith("doc_iva_001")
        assert len(result.excerpt) <= 200

    def test_extract_multiple_documents(self):
        """Test extracting paragraphs from multiple documents."""
        from app.services.paragraph_extractor import ParagraphExtractor

        extractor = ParagraphExtractor()

        kb_docs = [
            {"id": "doc_001", "content": SAMPLE_DOCUMENT_IVA},
            {"id": "doc_002", "content": SAMPLE_DOCUMENT_RAVVEDIMENTO},
        ]

        query = "aliquota IVA"

        results = []
        for doc in kb_docs:
            result = extractor.extract_best_paragraph(
                content=doc["content"],
                query=query,
                doc_id=doc["id"],
            )
            if result:
                results.append(result)

        assert len(results) == 2
        # First doc should have higher relevance for IVA query
        assert results[0].relevance_score >= results[1].relevance_score


# =============================================================================
# Edge Cases Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_very_short_paragraphs_filtered(self):
        """Test that very short paragraphs are filtered out."""
        from app.services.paragraph_extractor import ParagraphExtractor

        extractor = ParagraphExtractor()

        content = """Title

Short.

This is a proper paragraph with enough content to be meaningful for extraction.

X

Another good paragraph with sufficient text for analysis."""

        paragraphs = extractor.split_paragraphs(content, min_length=20)

        # Very short paragraphs should be filtered
        for p in paragraphs:
            assert len(p.text) >= 20 or p.text.strip() == ""

    def test_special_characters_in_content(self):
        """Test handling content with special characters."""
        from app.services.paragraph_extractor import ParagraphExtractor

        extractor = ParagraphExtractor()

        content = """Art. 1 § 2 - Definizioni

L'aliquota (22%) si applica ai beni "ordinari" e/o servizi.

Riferimento: D.Lgs. n° 633/72, artt. 16-17."""

        result = extractor.extract_best_paragraph(
            content=content,
            query="aliquota 22%",
            doc_id="doc_special",
        )

        assert result is not None
        assert result.relevance_score > 0

    def test_unicode_content(self):
        """Test handling Unicode content (Italian accents)."""
        from app.services.paragraph_extractor import ParagraphExtractor

        extractor = ParagraphExtractor()

        content = """L'imposta sul valore aggiunto è dovuta per le cessioni di beni.

Le aliquote variano in base alla tipologia merceologica."""

        result = extractor.extract_best_paragraph(
            content=content,
            query="imposta valore aggiunto",
            doc_id="doc_unicode",
        )

        assert result is not None
        assert "imposta" in result.excerpt.lower() or "valore" in result.excerpt.lower()
