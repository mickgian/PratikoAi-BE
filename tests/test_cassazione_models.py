"""
Test suite for Cassazione data models and enums.

This module tests the data structures used to represent
Italian Supreme Court decisions and related metadata.
"""

from dataclasses import asdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

import pytest

from app.models.cassazione_data import (
    CassazioneDecision,
    Citation,
    CourtSection,
    DecisionType,
    JuridicalSubject,
    LegalPrinciple,
    ScrapingError,
    ScrapingResult,
    ScrapingStatistics,
)


class TestCourtSectionEnum:
    """Test the court section enumeration."""

    def test_court_sections_exist(self):
        """Test that all major court sections are defined."""
        assert CourtSection.CIVILE.value == "civile"
        assert CourtSection.TRIBUTARIA.value == "tributaria"
        assert CourtSection.LAVORO.value == "lavoro"
        assert CourtSection.PENALE.value == "penale"
        assert CourtSection.SEZIONI_UNITE.value == "sezioni_unite"

    def test_court_section_from_string(self):
        """Test creating court section from Italian text."""
        assert CourtSection.from_italian_text("Sezione Civile") == CourtSection.CIVILE
        assert CourtSection.from_italian_text("Sezione Tributaria") == CourtSection.TRIBUTARIA
        assert CourtSection.from_italian_text("Sezione Lavoro") == CourtSection.LAVORO
        assert CourtSection.from_italian_text("Sezioni Unite") == CourtSection.SEZIONI_UNITE

    def test_court_section_display_name(self):
        """Test getting Italian display name for court sections."""
        assert CourtSection.CIVILE.italian_name() == "Sezione Civile"
        assert CourtSection.TRIBUTARIA.italian_name() == "Sezione Tributaria"
        assert CourtSection.LAVORO.italian_name() == "Sezione Lavoro"


class TestDecisionTypeEnum:
    """Test the decision type enumeration."""

    def test_decision_types_exist(self):
        """Test that all decision types are defined."""
        assert DecisionType.SENTENZA.value == "sentenza"
        assert DecisionType.ORDINANZA.value == "ordinanza"
        assert DecisionType.DECRETO.value == "decreto"
        assert DecisionType.AUTO.value == "auto"

    def test_decision_type_from_string(self):
        """Test creating decision type from Italian text."""
        assert DecisionType.from_italian_text("Sentenza") == DecisionType.SENTENZA
        assert DecisionType.from_italian_text("Ordinanza") == DecisionType.ORDINANZA
        assert DecisionType.from_italian_text("Decreto") == DecisionType.DECRETO

    def test_decision_type_display_name(self):
        """Test getting Italian display name for decision types."""
        assert DecisionType.SENTENZA.italian_name() == "Sentenza"
        assert DecisionType.ORDINANZA.italian_name() == "Ordinanza"
        assert DecisionType.DECRETO.italian_name() == "Decreto"


class TestJuridicalSubjectEnum:
    """Test juridical subject classification."""

    def test_juridical_subjects_exist(self):
        """Test that major juridical subjects are defined."""
        assert JuridicalSubject.DIRITTO_CIVILE.value == "diritto_civile"
        assert JuridicalSubject.DIRITTO_COMMERCIALE.value == "diritto_commerciale"
        assert JuridicalSubject.DIRITTO_TRIBUTARIO.value == "diritto_tributario"
        assert JuridicalSubject.DIRITTO_DEL_LAVORO.value == "diritto_del_lavoro"
        assert JuridicalSubject.DIRITTO_SOCIETARIO.value == "diritto_societario"

    def test_classify_from_keywords(self):
        """Test automatic classification from keywords."""
        civil_keywords = ["contratto", "responsabilità", "risarcimento"]
        assert JuridicalSubject.classify_from_keywords(civil_keywords) == JuridicalSubject.DIRITTO_CIVILE

        tax_keywords = ["IVA", "imposte", "tasse", "detrazioni"]
        assert JuridicalSubject.classify_from_keywords(tax_keywords) == JuridicalSubject.DIRITTO_TRIBUTARIO

        corporate_keywords = ["società", "amministratore", "SRL", "SpA"]
        assert JuridicalSubject.classify_from_keywords(corporate_keywords) == JuridicalSubject.DIRITTO_SOCIETARIO


class TestLegalPrincipleModel:
    """Test the legal principle data model."""

    def test_create_legal_principle(self):
        """Test creating a legal principle."""
        principle = LegalPrinciple(
            text="L'amministratore risponde delle obbligazioni sociali solo in caso di colpa grave",
            confidence_score=Decimal("0.90"),
            supporting_citations=["Art. 2476 c.c."],
            keywords=["amministratore", "responsabilità", "colpa grave"],
        )

        assert "amministratore" in principle.text.lower()
        assert principle.confidence_score == Decimal("0.90")
        assert len(principle.supporting_citations) == 1
        assert len(principle.keywords) == 3

    def test_principle_categorization(self):
        """Test automatic categorization of legal principles."""
        principle = LegalPrinciple(
            text="Il contratto deve essere interpretato secondo buona fede", confidence_score=Decimal("0.95")
        )

        category = principle.categorize()
        assert category == JuridicalSubject.DIRITTO_CIVILE

    def test_extract_principle_from_text(self):
        """Test extracting principles from decision text."""
        decision_text = """
        La Corte stabilisce il seguente principio di diritto:
        1) Il contratto deve essere interpretato secondo buona fede.
        2) L'inadempimento deve essere grave per giustificare la risoluzione.
        """

        principles = LegalPrinciple.extract_from_text(decision_text)
        assert len(principles) >= 2
        assert any("buona fede" in p.text for p in principles)
        assert any("inadempimento" in p.text for p in principles)


class TestCitationModel:
    """Test the citation data model."""

    def test_create_law_citation(self):
        """Test creating citation to law."""
        citation = Citation(
            type="law",
            reference="Art. 2476 Codice Civile",
            title="Responsabilità verso i creditori sociali",
            url="https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:regio.decreto:1942-03-16;262",
        )

        assert citation.type == "law"
        assert "2476" in citation.reference
        assert citation.is_law_citation() is True
        assert citation.is_decision_citation() is False

    def test_create_decision_citation(self):
        """Test creating citation to another decision."""
        citation = Citation(
            type="decision",
            reference="Cass. Civ. Sez. III, n. 15234/2023",
            title="Responsabilità amministratore SRL",
            court_section=CourtSection.CIVILE,
            decision_date=date(2023, 5, 15),
        )

        assert citation.type == "decision"
        assert citation.court_section == CourtSection.CIVILE
        assert citation.is_decision_citation() is True
        assert citation.is_law_citation() is False

    def test_extract_citations_from_text(self):
        """Test extracting citations from decision text."""
        text_with_citations = """
        Come stabilito dall'Art. 2476 del Codice Civile e dalla precedente
        Cass. Civ. Sez. III, n. 12345/2023, l'amministratore risponde...
        Si veda anche l'Art. 2381 c.c. e Cass. Civ. 67890/2022.
        """

        citations = Citation.extract_from_text(text_with_citations)

        law_citations = [c for c in citations if c.is_law_citation()]
        decision_citations = [c for c in citations if c.is_decision_citation()]

        assert len(law_citations) >= 2  # Art. 2476 and Art. 2381
        assert len(decision_citations) >= 2  # Two Cassazione references

    def test_citation_validation(self):
        """Test citation validation."""
        # Valid citation
        valid_citation = Citation(type="law", reference="Art. 2476 c.c.")
        assert valid_citation.is_valid() is True

        # Invalid citation (missing reference)
        invalid_citation = Citation(type="law", reference="")
        assert invalid_citation.is_valid() is False


class TestScrapingResultModel:
    """Test the scraping result data model."""

    def test_create_scraping_result(self):
        """Test creating a scraping result."""
        result = ScrapingResult(
            decisions_found=100,
            decisions_processed=95,
            decisions_saved=90,
            errors=5,
            duration_seconds=300,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        assert result.decisions_found == 100
        assert result.decisions_saved == 90
        assert result.success_rate == 0.9  # 90/100
        assert result.processing_rate == 0.95  # 95/100
        assert result.duration_minutes == 5.0  # 300/60

    def test_result_validation(self):
        """Test scraping result validation."""
        # Valid result
        valid_result = ScrapingResult(decisions_found=100, decisions_processed=95, decisions_saved=90, errors=5)
        assert valid_result.is_valid() is True

        # Invalid result (processed > found)
        invalid_result = ScrapingResult(
            decisions_found=100,
            decisions_processed=105,  # Can't process more than found
            decisions_saved=90,
            errors=5,
        )
        assert invalid_result.is_valid() is False

    def test_combine_results(self):
        """Test combining multiple scraping results."""
        result1 = ScrapingResult(
            decisions_found=50, decisions_processed=48, decisions_saved=45, errors=2, duration_seconds=150
        )

        result2 = ScrapingResult(
            decisions_found=30, decisions_processed=29, decisions_saved=28, errors=1, duration_seconds=120
        )

        combined = ScrapingResult.combine([result1, result2])

        assert combined.decisions_found == 80
        assert combined.decisions_processed == 77
        assert combined.decisions_saved == 73
        assert combined.errors == 3
        assert combined.duration_seconds == 270


class TestScrapingStatisticsModel:
    """Test the scraping statistics tracking model."""

    def test_create_empty_statistics(self):
        """Test creating empty statistics."""
        stats = ScrapingStatistics()

        assert stats.total_pages_attempted == 0
        assert stats.total_pages_successful == 0
        assert stats.total_decisions_found == 0
        assert stats.total_decisions_saved == 0
        assert stats.success_rate == 0.0
        assert stats.average_page_duration == 0.0

    def test_record_page_activity(self):
        """Test recording page scraping activity."""
        stats = ScrapingStatistics()

        # Record successful pages
        stats.record_page_scraped(success=True, duration=1.5)
        stats.record_page_scraped(success=True, duration=2.0)
        stats.record_page_scraped(success=False, duration=0.5)

        assert stats.total_pages_attempted == 3
        assert stats.total_pages_successful == 2
        assert stats.success_rate == pytest.approx(0.667, rel=1e-2)
        assert stats.average_page_duration == pytest.approx(1.333, rel=1e-2)

    def test_record_decision_activity(self):
        """Test recording decision processing activity."""
        stats = ScrapingStatistics()

        # Record decision processing
        stats.record_decision_processed(saved=True)
        stats.record_decision_processed(saved=True)
        stats.record_decision_processed(saved=False)  # Error during save

        assert stats.total_decisions_found == 3
        assert stats.total_decisions_saved == 2
        assert stats.save_rate == pytest.approx(0.667, rel=1e-2)

    def test_statistics_reset(self):
        """Test resetting statistics."""
        stats = ScrapingStatistics()

        # Add some data
        stats.record_page_scraped(success=True, duration=1.0)
        stats.record_decision_processed(saved=True)

        # Reset
        stats.reset()

        assert stats.total_pages_attempted == 0
        assert stats.total_decisions_found == 0
        assert stats.success_rate == 0.0


class TestScrapingErrorModel:
    """Test the scraping error model."""

    def test_create_scraping_error(self):
        """Test creating a scraping error."""
        error = ScrapingError(
            message="Network timeout while fetching page",
            error_code="NETWORK_TIMEOUT",
            url="https://www.cortedicassazione.it/page/123",
            timestamp=datetime.now(),
            retry_count=2,
            is_recoverable=True,
        )

        assert "timeout" in error.message.lower()
        assert error.error_code == "NETWORK_TIMEOUT"
        assert error.is_recoverable is True
        assert error.retry_count == 2

    def test_error_categorization(self):
        """Test automatic error categorization."""
        # Network error
        network_error = ScrapingError("Connection timeout", "TIMEOUT")
        assert network_error.category() == "network"

        # Parsing error
        parse_error = ScrapingError("Invalid HTML structure", "PARSE_ERROR")
        assert parse_error.category() == "parsing"

        # Server error
        server_error = ScrapingError("HTTP 500 Internal Server Error", "HTTP_500")
        assert server_error.category() == "server"

    def test_error_recovery_suggestions(self):
        """Test getting recovery suggestions for errors."""
        timeout_error = ScrapingError("Connection timeout", "TIMEOUT")
        suggestions = timeout_error.get_recovery_suggestions()

        assert any("retry" in suggestion.lower() for suggestion in suggestions)
        assert any("delay" in suggestion.lower() for suggestion in suggestions)


class TestDataModelIntegration:
    """Test integration between different data models."""

    def test_decision_with_all_components(self):
        """Test creating a complete decision with all components."""
        # Create legal principles
        principles = [
            LegalPrinciple(
                text="L'amministratore risponde solo in caso di colpa grave", confidence_score=Decimal("0.90")
            ),
            LegalPrinciple(
                text="È necessario il nesso causale tra condotta e danno", confidence_score=Decimal("0.85")
            ),
        ]

        # Create citations
        citations = [
            Citation(type="law", reference="Art. 2476 c.c."),
            Citation(type="decision", reference="Cass. Civ. 12345/2023"),
        ]

        # Create complete decision
        decision = CassazioneDecision(
            decision_number="15234/2024",
            date=date(2024, 3, 15),
            section=CourtSection.CIVILE,
            subject="Responsabilità amministratore SRL",
            legal_principles=principles,
            citations_to_laws=[c for c in citations if c.is_law_citation()],
            citations_to_decisions=[c for c in citations if c.is_decision_citation()],
        )

        assert len(decision.legal_principles) == 2
        assert len(decision.citations_to_laws) == 1
        assert len(decision.citations_to_decisions) == 1
        assert decision.juridical_subject == JuridicalSubject.DIRITTO_SOCIETARIO

    def test_decision_serialization(self):
        """Test serializing decision to dict for storage."""
        decision = CassazioneDecision(
            decision_number="15234/2024", date=date(2024, 3, 15), section=CourtSection.CIVILE, subject="Test decision"
        )

        decision_dict = decision.to_dict()

        assert decision_dict["decision_number"] == "15234/2024"
        assert decision_dict["section"] == "civile"
        assert "date" in decision_dict

    def test_decision_deserialization(self):
        """Test creating decision from dict."""
        decision_dict = {
            "decision_number": "15234/2024",
            "date": "2024-03-15",
            "section": "civile",
            "subject": "Test decision",
        }

        decision = CassazioneDecision.from_dict(decision_dict)

        assert decision.decision_number == "15234/2024"
        assert decision.section == CourtSection.CIVILE
        assert decision.date == date(2024, 3, 15)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
