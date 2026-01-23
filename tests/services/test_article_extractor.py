"""TDD Tests for DEV-245: Article Extractor Service.

Tests for extracting Italian legal article references (articolo, comma, lettera)
from legal document text.
"""

import pytest

from app.services.article_extractor import (
    ArticleExtractor,
    ArticleReference,
    article_extractor,
)


class TestArticleReferenceExtraction:
    """Tests for extracting article references from text."""

    def test_extract_simple_article(self):
        """Test extracting simple 'Art. X' pattern."""
        extractor = ArticleExtractor()
        text = "Come previsto dall'Art. 1 della presente legge."
        refs = extractor.extract_references(text)

        assert len(refs) == 1
        assert refs[0].article == "1"
        assert refs[0].comma is None
        assert refs[0].lettera is None

    def test_extract_article_with_comma(self):
        """Test extracting 'Art. X, comma Y' pattern."""
        extractor = ArticleExtractor()
        text = "L'Art. 1, comma 231 della Legge 199/2025 prevede..."
        refs = extractor.extract_references(text)

        assert len(refs) == 1
        assert refs[0].article == "1"
        assert refs[0].comma == "231"
        assert refs[0].lettera is None

    def test_extract_article_with_comma_and_lettera(self):
        """Test extracting 'Art. X, comma Y, lettera Z' pattern."""
        extractor = ArticleExtractor()
        text = "Art. 1, comma 231, lettera a) della Legge 199/2025"
        refs = extractor.extract_references(text)

        assert len(refs) == 1
        assert refs[0].article == "1"
        assert refs[0].comma == "231"
        assert refs[0].lettera == "a"

    def test_extract_comma_range(self):
        """Test extracting 'commi X-Y' pattern."""
        extractor = ArticleExtractor()
        text = "I commi da 231 a 252 della Legge 199/2025"
        refs = extractor.extract_references(text)

        assert len(refs) >= 1
        # Should capture the range
        assert any(r.comma_range == ("231", "252") for r in refs)

    def test_extract_articolo_full_form(self):
        """Test extracting 'articolo X' (full word) pattern."""
        extractor = ArticleExtractor()
        text = "L'articolo 16 disciplina le modalità di pagamento."
        refs = extractor.extract_references(text)

        assert len(refs) == 1
        assert refs[0].article == "16"

    def test_extract_multiple_references(self):
        """Test extracting multiple article references from text."""
        extractor = ArticleExtractor()
        text = """
        L'Art. 1, comma 231 definisce i tributi ammessi.
        L'Art. 2, comma 10, lettera b) stabilisce le esclusioni.
        Il comma 235 dell'Art. 1 prevede le rate.
        """
        refs = extractor.extract_references(text)

        assert len(refs) >= 2
        # Check that Art. 1 and Art. 2 are found
        articles = [r.article for r in refs]
        assert "1" in articles
        assert "2" in articles

    def test_extract_article_bis_ter(self):
        """Test extracting 'Art. X-bis', 'Art. X-ter' patterns."""
        extractor = ArticleExtractor()
        text = "L'Art. 2-bis e l'Art. 3-ter della legge."
        refs = extractor.extract_references(text)

        assert len(refs) == 2
        assert refs[0].article == "2-bis"
        assert refs[1].article == "3-ter"

    def test_extract_no_references(self):
        """Test extracting from text without article references."""
        extractor = ArticleExtractor()
        text = "Buongiorno, come posso aiutarti con le tasse?"
        refs = extractor.extract_references(text)

        assert len(refs) == 0

    def test_extract_empty_text(self):
        """Test extracting from empty text."""
        extractor = ArticleExtractor()
        refs = extractor.extract_references("")

        assert len(refs) == 0

    def test_extract_dpr_article(self):
        """Test extracting article from DPR reference."""
        extractor = ArticleExtractor()
        text = "Gli artt. 36-bis e 36-ter del DPR 600/1973"
        refs = extractor.extract_references(text)

        assert len(refs) >= 1
        # Should find 36-bis and 36-ter
        articles = [r.article for r in refs]
        assert "36-bis" in articles or "36-ter" in articles


class TestArticleReferenceDataclass:
    """Tests for ArticleReference dataclass."""

    def test_reference_str_simple(self):
        """Test string representation of simple reference."""
        ref = ArticleReference(article="1")
        assert "Art. 1" in str(ref)

    def test_reference_str_with_comma(self):
        """Test string representation with comma."""
        ref = ArticleReference(article="1", comma="231")
        result = str(ref)
        assert "Art. 1" in result
        assert "comma 231" in result

    def test_reference_str_with_lettera(self):
        """Test string representation with lettera."""
        ref = ArticleReference(article="1", comma="231", lettera="a")
        result = str(ref)
        assert "Art. 1" in result
        assert "comma 231" in result
        assert "lettera a" in result

    def test_reference_str_with_range(self):
        """Test string representation with comma range."""
        ref = ArticleReference(article="1", comma_range=("231", "252"))
        result = str(ref)
        assert "Art. 1" in result
        assert "231" in result
        assert "252" in result

    def test_reference_equality(self):
        """Test ArticleReference equality."""
        ref1 = ArticleReference(article="1", comma="231")
        ref2 = ArticleReference(article="1", comma="231")
        ref3 = ArticleReference(article="1", comma="232")

        assert ref1 == ref2
        assert ref1 != ref3

    def test_reference_to_dict(self):
        """Test to_dict serialization."""
        ref = ArticleReference(
            article="1",
            comma="231",
            lettera="a",
            source_law="Legge 199/2025",
        )
        d = ref.to_dict()

        assert d["article"] == "1"
        assert d["comma"] == "231"
        assert d["lettera"] == "a"
        assert d["source_law"] == "Legge 199/2025"


class TestLawAssociation:
    """Tests for associating article references with their source law."""

    def test_extract_with_law_context(self):
        """Test extracting references with associated law."""
        extractor = ArticleExtractor()
        text = "Art. 1, comma 231 della Legge n. 199/2025 (Legge di Bilancio 2026)"
        refs = extractor.extract_references(text)

        assert len(refs) == 1
        assert refs[0].source_law is not None
        assert "199/2025" in refs[0].source_law

    def test_extract_multiple_laws(self):
        """Test extracting references from text with multiple laws."""
        extractor = ArticleExtractor()
        text = """
        L'Art. 1, comma 231 della Legge 199/2025 e
        l'Art. 16 del D.Lgs. 472/1997.
        """
        refs = extractor.extract_references(text)

        assert len(refs) >= 2
        # Each reference should have its associated law
        laws = [r.source_law for r in refs if r.source_law]
        assert len(laws) >= 1


class TestChunkMetadataExtraction:
    """Tests for extracting article metadata from document chunks."""

    def test_extract_chunk_metadata(self):
        """Test extracting complete metadata from a chunk."""
        extractor = ArticleExtractor()
        chunk_text = """
        Art. 1 - Definizioni
        Comma 231. Ai fini della presente legge, si definisce "definizione agevolata"...
        Comma 232. I tributi di cui al comma 231, lettera a), includono:
        a) imposte dirette;
        b) imposte indirette;
        """

        metadata = extractor.extract_chunk_metadata(chunk_text)

        assert "article_references" in metadata
        assert len(metadata["article_references"]) >= 1
        assert metadata["primary_article"] == "1"

    def test_extract_chunk_metadata_no_refs(self):
        """Test extracting metadata from chunk without references."""
        extractor = ArticleExtractor()
        chunk_text = "Questo documento descrive le procedure fiscali."

        metadata = extractor.extract_chunk_metadata(chunk_text)

        assert "article_references" in metadata
        assert len(metadata["article_references"]) == 0
        assert metadata["primary_article"] is None


class TestSingletonInstance:
    """Tests for the singleton instance."""

    def test_singleton_is_article_extractor(self):
        """Test that singleton is an ArticleExtractor instance."""
        assert isinstance(article_extractor, ArticleExtractor)

    def test_singleton_can_extract(self):
        """Test that singleton can perform extraction."""
        refs = article_extractor.extract_references("Art. 1, comma 231")

        assert isinstance(refs, list)
        assert len(refs) == 1


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_article_in_header(self):
        """Test extracting article from header format."""
        extractor = ArticleExtractor()
        text = "ARTICOLO 1\n(Definizioni)\n\n1. Ai fini della presente legge..."
        refs = extractor.extract_references(text)

        assert len(refs) >= 1
        assert refs[0].article == "1"

    def test_roman_numeral_article(self):
        """Test handling articles with Roman numerals (if present)."""
        extractor = ArticleExtractor()
        text = "Art. IV della Costituzione"
        refs = extractor.extract_references(text)

        # Should handle or skip Roman numerals gracefully
        # (Italian laws typically use Arabic numerals, but some older docs have Roman)
        assert isinstance(refs, list)

    def test_multiple_commi_same_article(self):
        """Test extracting multiple commi from same article."""
        extractor = ArticleExtractor()
        text = """
        Art. 1, comma 231, comma 232 e comma 233
        """
        refs = extractor.extract_references(text)

        # Should find multiple comma references
        assert len(refs) >= 1
        # All should reference Art. 1
        assert all(r.article == "1" for r in refs)

    def test_abbreviated_forms(self):
        """Test various abbreviated forms."""
        extractor = ArticleExtractor()
        text = """
        art. 1, c. 231
        co. 232
        lett. a)
        """
        refs = extractor.extract_references(text)

        # Should handle abbreviated forms
        assert len(refs) >= 1

    def test_case_insensitivity(self):
        """Test that extraction is case-insensitive."""
        extractor = ArticleExtractor()
        text = "ART. 1, COMMA 231, LETTERA A)"
        refs = extractor.extract_references(text)

        assert len(refs) == 1
        assert refs[0].article == "1"
        assert refs[0].comma == "231"
        assert refs[0].lettera.lower() == "a"
