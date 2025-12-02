"""Tests for entity extraction and validation in Expert FAQ Retrieval Service.

This module tests the entity extraction and validation logic that prevents
false positive semantic matches when document numbers, years, or article
numbers differ between query and FAQ.

Bug Context:
    Query "Parlami della risoluzione 63" was returning FAQ about "risoluzione 64"
    because semantic similarity (91.68%) exceeded threshold (90%), even though
    they refer to completely different legal documents.
"""

from unittest.mock import MagicMock

import pytest

from app.services.expert_faq_retrieval_service import ExpertFAQRetrievalService


class TestEntityExtraction:
    """Tests for _extract_entities() method."""

    @pytest.fixture
    def service(self):
        """Create service instance with mocked db session."""
        mock_db = MagicMock()
        return ExpertFAQRetrievalService(db_session=mock_db)

    def test_extracts_risoluzione_number(self, service):
        """Should extract '63' from 'risoluzione 63'."""
        entities = service._extract_entities("Parlami della risoluzione 63")
        assert "63" in entities["document_numbers"]

    def test_extracts_risoluzione_with_n(self, service):
        """Should extract '63' from 'risoluzione n. 63'."""
        entities = service._extract_entities("risoluzione n. 63 dell'agenzia delle entrate")
        assert "63" in entities["document_numbers"]

    def test_extracts_circolare_number(self, service):
        """Should extract '12' from 'circolare n. 12'."""
        entities = service._extract_entities("circolare n. 12 del 2024")
        assert "12" in entities["document_numbers"]

    def test_extracts_interpello_number(self, service):
        """Should extract '99' from 'interpello 99'."""
        entities = service._extract_entities("interpello 99")
        assert "99" in entities["document_numbers"]

    def test_extracts_year(self, service):
        """Should extract '2024' from text."""
        entities = service._extract_entities("risoluzione del 2024")
        assert "2024" in entities["years"]

    def test_extracts_multiple_years(self, service):
        """Should extract all years from text."""
        entities = service._extract_entities("novità 2024 e 2025")
        assert "2024" in entities["years"]
        assert "2025" in entities["years"]

    def test_ignores_non_relevant_years(self, service):
        """Should NOT extract years outside 2020-2030 range."""
        entities = service._extract_entities("nel 1990 e 2019 e 2031")
        assert "1990" not in entities["years"]
        assert "2019" not in entities["years"]
        assert "2031" not in entities["years"]

    def test_extracts_article_number(self, service):
        """Should extract '110' from 'art. 110'."""
        entities = service._extract_entities("art. 110 del TUIR")
        assert "110" in entities["article_numbers"]

    def test_extracts_articolo_full_word(self, service):
        """Should extract '5' from 'articolo 5'."""
        entities = service._extract_entities("articolo 5 del decreto")
        assert "5" in entities["article_numbers"]

    def test_extracts_comma(self, service):
        """Should extract '3' from 'comma 3'."""
        entities = service._extract_entities("art. 1, comma 3")
        assert "1" in entities["article_numbers"]
        assert "3" in entities["article_numbers"]

    def test_extracts_decreto_number(self, service):
        """Should extract '123' from 'decreto 123'."""
        entities = service._extract_entities("decreto 123")
        assert "123" in entities["decree_numbers"]

    def test_extracts_dl_number(self, service):
        """Should extract '45' from 'D.L. 45'."""
        entities = service._extract_entities("D.L. 45 del 2024")
        assert "45" in entities["decree_numbers"]

    def test_extracts_dlgs_number(self, service):
        """Should extract '81' from 'D.Lgs. 81'."""
        entities = service._extract_entities("D.Lgs. 81")
        assert "81" in entities["decree_numbers"]

    def test_extracts_multiple_entities(self, service):
        """Should extract all entity types from complex query."""
        text = "risoluzione 63 del 2024, art. 110 del decreto 123"
        entities = service._extract_entities(text)
        assert "63" in entities["document_numbers"]
        assert "2024" in entities["years"]
        assert "110" in entities["article_numbers"]
        assert "123" in entities["decree_numbers"]

    def test_handles_empty_text(self, service):
        """Should return empty sets for empty text."""
        entities = service._extract_entities("")
        assert entities["document_numbers"] == set()
        assert entities["years"] == set()
        assert entities["article_numbers"] == set()
        assert entities["decree_numbers"] == set()

    def test_handles_no_entities(self, service):
        """Should return empty sets when no entities present."""
        entities = service._extract_entities("Come si calcola l'IVA?")
        assert entities["document_numbers"] == set()
        assert entities["years"] == set()
        assert entities["article_numbers"] == set()
        assert entities["decree_numbers"] == set()

    def test_case_insensitive(self, service):
        """Should extract entities regardless of case."""
        entities = service._extract_entities("RISOLUZIONE 63 dell'AGENZIA")
        assert "63" in entities["document_numbers"]


class TestEntityValidation:
    """Tests for _validate_entity_match() method."""

    @pytest.fixture
    def service(self):
        """Create service instance with mocked db session."""
        mock_db = MagicMock()
        return ExpertFAQRetrievalService(db_session=mock_db)

    def test_rejects_different_document_numbers(self, service):
        """Query for risoluzione 63 should NOT match FAQ about risoluzione 64.

        This is the main bug case - semantic similarity was 91.68% but
        they are completely different documents.
        """
        query = "Parlami della risoluzione 63"
        faq = "Cosa dice la risoluzione 64?"
        assert service._validate_entity_match(query, faq) is False

    def test_accepts_same_document_number(self, service):
        """Query for risoluzione 64 SHOULD match FAQ about risoluzione 64."""
        query = "Parlami della risoluzione 64"
        faq = "Cosa dice la risoluzione 64?"
        assert service._validate_entity_match(query, faq) is True

    def test_handles_queries_without_entities(self, service):
        """Generic queries without entities should pass validation."""
        query = "Come si calcola l'IVA?"
        faq = "Qual è l'aliquota IVA ordinaria?"
        assert service._validate_entity_match(query, faq) is True

    def test_rejects_different_years(self, service):
        """Query for 2024 should NOT match FAQ about 2025."""
        query = "Novità fiscali 2024"
        faq = "Novità fiscali 2025"
        assert service._validate_entity_match(query, faq) is False

    def test_accepts_matching_year(self, service):
        """Query for 2024 SHOULD match FAQ about 2024."""
        query = "Novità fiscali 2024"
        faq = "Quali sono le novità 2024?"
        assert service._validate_entity_match(query, faq) is True

    def test_handles_format_variations_n_dot(self, service):
        """Should match 'risoluzione n. 64' with 'risoluzione 64'."""
        query = "risoluzione n. 64"
        faq = "risoluzione 64"
        assert service._validate_entity_match(query, faq) is True

    def test_rejects_when_query_has_number_faq_doesnt(self, service):
        """If query has doc number but FAQ doesn't, should reject."""
        query = "Parlami della risoluzione 63"
        faq = "Come funzionano le risoluzioni dell'agenzia?"
        assert service._validate_entity_match(query, faq) is False

    def test_accepts_when_faq_has_extra_entities(self, service):
        """If FAQ has more entities than query, that's OK."""
        query = "risoluzione 63"
        faq = "risoluzione 63 del 2024"
        assert service._validate_entity_match(query, faq) is True

    def test_rejects_when_years_differ(self, service):
        """Query about 2024 should not match FAQ about 2023."""
        query = "risoluzione 63 del 2024"
        faq = "risoluzione 63 del 2023"
        assert service._validate_entity_match(query, faq) is False

    def test_accepts_multiple_matching_entities(self, service):
        """All entity types must match."""
        query = "risoluzione 63 del 2024"
        faq = "risoluzione 63 dell'anno 2024"
        assert service._validate_entity_match(query, faq) is True

    def test_rejects_different_article_numbers(self, service):
        """Query for art. 1 should NOT match FAQ about art. 2."""
        query = "art. 1 del TUIR"
        faq = "art. 2 del TUIR"
        assert service._validate_entity_match(query, faq) is False

    def test_accepts_same_article_numbers(self, service):
        """Query for art. 110 SHOULD match FAQ about art. 110."""
        query = "art. 110 del TUIR"
        faq = "articolo 110 TUIR"
        assert service._validate_entity_match(query, faq) is True

    def test_accepts_any_match_within_entity_type(self, service):
        """If query has multiple entities of same type, ANY match is OK."""
        # Note: regex only extracts numbers directly following document type keyword
        # "risoluzione 63 o risoluzione 64" extracts both 63 and 64
        query = "risoluzione 63 o risoluzione 64"
        faq = "risoluzione 64"
        assert service._validate_entity_match(query, faq) is True


class TestEntityValidationEdgeCases:
    """Additional edge case tests for entity validation."""

    @pytest.fixture
    def service(self):
        """Create service instance with mocked db session."""
        mock_db = MagicMock()
        return ExpertFAQRetrievalService(db_session=mock_db)

    def test_original_bug_case(self, service):
        """Test the exact bug case: risoluzione 63 query vs risoluzione 64 FAQ.

        Bug Context: Semantic similarity was 91.68% (> 90% threshold),
        causing wrong document to be returned.
        """
        query = "Parlami della risoluzione 63 dell'agenzia dell'entrate"
        faq = "Parlami della risoluzione 64 dell'agenzia delle entrate"

        # Entity extraction should find different numbers
        query_entities = service._extract_entities(query)
        faq_entities = service._extract_entities(faq)

        assert "63" in query_entities["document_numbers"]
        assert "64" in faq_entities["document_numbers"]
        assert "63" not in faq_entities["document_numbers"]

        # Validation should REJECT this match
        assert service._validate_entity_match(query, faq) is False

    def test_circolare_vs_risoluzione_different_types(self, service):
        """Circolare 63 should NOT match risoluzione 63 - different doc types."""
        query = "circolare 63"
        faq = "risoluzione 63"
        # Both have doc number 63 in document_numbers set
        # This should still pass since 63 matches 63
        assert service._validate_entity_match(query, faq) is True

    def test_multiple_document_types_in_query(self, service):
        """Query with multiple document references."""
        query = "risoluzione 63 e circolare 12"
        faq = "risoluzione 63"

        query_entities = service._extract_entities(query)
        assert "63" in query_entities["document_numbers"]
        assert "12" in query_entities["document_numbers"]

        faq_entities = service._extract_entities(faq)
        assert "63" in faq_entities["document_numbers"]

        # Should pass because 63 is in both
        assert service._validate_entity_match(query, faq) is True

    def test_year_in_date_format(self, service):
        """Year should be extracted from date formats."""
        entities = service._extract_entities("risoluzione del 15 marzo 2024")
        assert "2024" in entities["years"]

    def test_handles_whitespace_variations(self, service):
        """Should handle various whitespace patterns."""
        # Multiple spaces
        entities = service._extract_entities("risoluzione   63")
        assert "63" in entities["document_numbers"]

        # With n.
        entities = service._extract_entities("risoluzione n.63")
        assert "63" in entities["document_numbers"]

        # With n. and space
        entities = service._extract_entities("risoluzione n. 63")
        assert "63" in entities["document_numbers"]

    def test_handles_unicode_text(self, service):
        """Should handle Italian accented characters."""
        entities = service._extract_entities("novità risoluzione 63 dell'età")
        assert "63" in entities["document_numbers"]
