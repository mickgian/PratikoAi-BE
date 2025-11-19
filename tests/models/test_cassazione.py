"""Tests for Cassazione (Italian Supreme Court) models."""

from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from app.models.cassazione import (
    CassazioneDecision,
    CassazioneJurisprudenceAnalysis,
    CassazioneLegalPrinciple,
    CassazioneSearchQuery,
    CassazioneSearchResult,
    CassazioneSection,
    CassazioneUpdate,
    DecisionType,
    LegalPrincipleArea,
    classify_precedent_value,
    determine_related_sectors,
    extract_legal_keywords,
)
from app.models.ccnl_data import CCNLSector


class TestCassazioneSection:
    """Test CassazioneSection enum."""

    def test_cassazione_section_values(self):
        """Test that Cassazione sections have correct values."""
        assert CassazioneSection.CIVILE_LAVORO.value == "civile_lavoro"
        assert CassazioneSection.CIVILE_PRIMA.value == "civile_prima"
        assert CassazioneSection.CIVILE_SECONDA.value == "civile_seconda"
        assert CassazioneSection.CIVILE_TERZA.value == "civile_terza"
        assert CassazioneSection.PENALE_PRIMA.value == "penale_prima"
        assert CassazioneSection.PENALE_SECONDA.value == "penale_seconda"
        assert CassazioneSection.SEZIONI_UNITE_CIVILI.value == "sezioni_unite_civili"
        assert CassazioneSection.SEZIONI_UNITE_PENALI.value == "sezioni_unite_penali"

    def test_cassazione_section_enum_members(self):
        """Test that all expected sections exist."""
        expected = {
            "CIVILE_LAVORO",
            "CIVILE_PRIMA",
            "CIVILE_SECONDA",
            "CIVILE_TERZA",
            "PENALE_PRIMA",
            "PENALE_SECONDA",
            "SEZIONI_UNITE_CIVILI",
            "SEZIONI_UNITE_PENALI",
        }
        actual = {member.name for member in CassazioneSection}
        assert actual == expected


class TestDecisionType:
    """Test DecisionType enum."""

    def test_decision_type_values(self):
        """Test that decision types have correct values."""
        assert DecisionType.SENTENZA.value == "sentenza"
        assert DecisionType.ORDINANZA.value == "ordinanza"
        assert DecisionType.DECRETO.value == "decreto"
        assert DecisionType.MASSIMA.value == "massima"
        assert DecisionType.ORIENTAMENTO.value == "orientamento"

    def test_decision_type_enum_members(self):
        """Test that all expected decision types exist."""
        expected = {"SENTENZA", "ORDINANZA", "DECRETO", "MASSIMA", "ORIENTAMENTO"}
        actual = {member.name for member in DecisionType}
        assert actual == expected


class TestLegalPrincipleArea:
    """Test LegalPrincipleArea enum."""

    def test_legal_principle_area_values(self):
        """Test that legal principle areas have correct values."""
        assert LegalPrincipleArea.CONTRATTO_LAVORO.value == "contratto_lavoro"
        assert LegalPrincipleArea.CCNL_INTERPRETAZIONE.value == "ccnl_interpretazione"
        assert LegalPrincipleArea.LICENZIAMENTO.value == "licenziamento"
        assert LegalPrincipleArea.RETRIBUZIONE.value == "retribuzione"
        assert LegalPrincipleArea.ORARIO_LAVORO.value == "orario_lavoro"
        assert LegalPrincipleArea.FERIE_PERMESSI.value == "ferie_permessi"
        assert LegalPrincipleArea.CONTRIBUTI_PREVIDENZA.value == "contributi_previdenza"
        assert LegalPrincipleArea.SICUREZZA_LAVORO.value == "sicurezza_lavoro"
        assert LegalPrincipleArea.DISCRIMINAZIONE.value == "discriminazione"
        assert LegalPrincipleArea.SINDACATO.value == "sindacato"
        assert LegalPrincipleArea.SCIOPERO.value == "sciopero"
        assert LegalPrincipleArea.MATERNITA_PATERNITA.value == "maternita_paternita"
        assert LegalPrincipleArea.MALATTIA_INFORTUNIO.value == "malattia_infortunio"

    def test_legal_principle_area_enum_members(self):
        """Test that all expected legal principle areas exist."""
        expected = {
            "CONTRATTO_LAVORO",
            "CCNL_INTERPRETAZIONE",
            "LICENZIAMENTO",
            "RETRIBUZIONE",
            "ORARIO_LAVORO",
            "FERIE_PERMESSI",
            "CONTRIBUTI_PREVIDENZA",
            "SICUREZZA_LAVORO",
            "DISCRIMINAZIONE",
            "SINDACATO",
            "SCIOPERO",
            "MATERNITA_PATERNITA",
            "MALATTIA_INFORTUNIO",
        }
        actual = {member.name for member in LegalPrincipleArea}
        assert actual == expected


class TestCassazioneDecision:
    """Test CassazioneDecision model."""

    def test_create_decision_minimal(self):
        """Test creating decision with required fields."""
        decision_date = date(2025, 1, 15)

        decision = CassazioneDecision(
            decision_id="CASS-2025-123",
            decision_number=123,
            decision_year=2025,
            section=CassazioneSection.CIVILE_LAVORO,
            decision_date=decision_date,
            title="Licenziamento per giusta causa",
        )

        assert decision.decision_id == "CASS-2025-123"
        assert decision.decision_number == 123
        assert decision.decision_year == 2025
        assert decision.section == CassazioneSection.CIVILE_LAVORO
        assert decision.decision_type == DecisionType.SENTENZA  # Default
        assert decision.decision_date == decision_date
        assert decision.title == "Licenziamento per giusta causa"
        assert decision.precedent_value == "medium"  # Default
        assert decision.confidence_score == 95  # Default

    def test_decision_with_all_dates(self):
        """Test decision with all date fields."""
        decision_date = date(2025, 1, 15)
        publication_date = date(2025, 1, 20)
        filing_date = date(2024, 6, 10)

        decision = CassazioneDecision(
            decision_id="CASS-2025-456",
            decision_number=456,
            decision_year=2025,
            section=CassazioneSection.SEZIONI_UNITE_CIVILI,
            decision_date=decision_date,
            publication_date=publication_date,
            filing_date=filing_date,
            title="Test Decision",
        )

        assert decision.decision_date == decision_date
        assert decision.publication_date == publication_date
        assert decision.filing_date == filing_date

    def test_decision_with_content(self):
        """Test decision with full content."""
        decision = CassazioneDecision(
            decision_id="CASS-2025-789",
            decision_number=789,
            decision_year=2025,
            section=CassazioneSection.CIVILE_LAVORO,
            decision_date=date(2025, 1, 15),
            title="Interpretazione CCNL Metalmeccanici",
            summary="La Corte ha stabilito che...",
            full_text="Sentenza completa della Corte di Cassazione...",
            legal_principle="Principio giuridico estratto dalla decisione",
            keywords=["ccnl", "metalmeccanici", "retribuzione"],
        )

        assert decision.summary is not None
        assert decision.full_text is not None
        assert decision.legal_principle is not None
        assert "ccnl" in decision.keywords

    def test_decision_with_classification(self):
        """Test decision with classification fields."""
        decision = CassazioneDecision(
            decision_id="CASS-2025-100",
            decision_number=100,
            decision_year=2025,
            section=CassazioneSection.CIVILE_LAVORO,
            decision_date=date(2025, 1, 15),
            title="Test",
            legal_areas=["licenziamento", "retribuzione"],
            related_sectors=["metalmeccanici", "commercio"],
            precedent_value="high",
        )

        assert "licenziamento" in decision.legal_areas
        assert "metalmeccanici" in decision.related_sectors
        assert decision.precedent_value == "high"

    def test_decision_with_references(self):
        """Test decision with references and citations."""
        decision = CassazioneDecision(
            decision_id="CASS-2025-200",
            decision_number=200,
            decision_year=2025,
            section=CassazioneSection.CIVILE_LAVORO,
            decision_date=date(2025, 1, 15),
            title="Test",
            cited_decisions=["CASS-2020-100", "CASS-2018-500"],
            citing_decisions=["CASS-2025-300"],
            related_laws=["Art. 18 L. 300/1970", "D.Lgs. 23/2015"],
            related_ccnl=["CCNL Metalmeccanici 2024"],
        )

        assert len(decision.cited_decisions) == 2
        assert "CASS-2020-100" in decision.cited_decisions
        assert len(decision.related_laws) == 2
        assert "CCNL Metalmeccanici 2024" in decision.related_ccnl

    def test_decision_with_parties(self):
        """Test decision with party information."""
        decision = CassazioneDecision(
            decision_id="CASS-2025-300",
            decision_number=300,
            decision_year=2025,
            section=CassazioneSection.CIVILE_LAVORO,
            decision_date=date(2025, 1, 15),
            title="Test",
            appellant="Sig. Mario Rossi",
            respondent="Azienda XYZ S.p.A.",
            case_subject="Licenziamento illegittimo e richiesta reintegra",
            court_of_origin="Corte d'Appello di Milano",
        )

        assert decision.appellant == "Sig. Mario Rossi"
        assert decision.respondent == "Azienda XYZ S.p.A."
        assert decision.court_of_origin == "Corte d'Appello di Milano"

    def test_decision_with_outcome(self):
        """Test decision with outcome information."""
        decision = CassazioneDecision(
            decision_id="CASS-2025-400",
            decision_number=400,
            decision_year=2025,
            section=CassazioneSection.CIVILE_LAVORO,
            decision_date=date(2025, 1, 15),
            title="Test",
            outcome="Ricorso accolto",
            damages_awarded="€50,000",
        )

        assert decision.outcome == "Ricorso accolto"
        assert decision.damages_awarded == "€50,000"

    def test_decision_with_metadata(self):
        """Test decision with metadata."""
        decision = CassazioneDecision(
            decision_id="CASS-2025-500",
            decision_number=500,
            decision_year=2025,
            section=CassazioneSection.CIVILE_LAVORO,
            decision_date=date(2025, 1, 15),
            title="Test",
            source_url="https://italgiure.giustizia.it/...",
            confidence_score=98,
        )

        assert decision.source_url is not None
        assert decision.confidence_score == 98


class TestCassazioneLegalPrinciple:
    """Test CassazioneLegalPrinciple model."""

    def test_create_legal_principle_minimal(self):
        """Test creating legal principle with required fields."""
        principle = CassazioneLegalPrinciple(
            principle_id="PRIN-2025-001",
            decision_id="CASS-2025-123",
            title="Principio sul licenziamento",
            principle_text="Il licenziamento deve essere motivato...",
            legal_area=LegalPrincipleArea.LICENZIAMENTO,
            decision_date=date(2025, 1, 15),
        )

        assert principle.principle_id == "PRIN-2025-001"
        assert principle.decision_id == "CASS-2025-123"
        assert principle.legal_area == LegalPrincipleArea.LICENZIAMENTO
        assert principle.precedent_strength == "medium"  # Default
        assert principle.related_sectors == []
        assert principle.keywords == []

    def test_legal_principle_with_sectors(self):
        """Test legal principle with related sectors."""
        principle = CassazioneLegalPrinciple(
            principle_id="PRIN-2025-002",
            decision_id="CASS-2025-456",
            title="CCNL Retribuzione",
            principle_text="La retribuzione deve rispettare i minimi...",
            legal_area=LegalPrincipleArea.RETRIBUZIONE,
            related_sectors=[CCNLSector.METALMECCANICI_INDUSTRIA, CCNLSector.COMMERCIO_TERZIARIO],
            precedent_strength="high",
            decision_date=date(2025, 1, 15),
        )

        assert len(principle.related_sectors) == 2
        assert CCNLSector.METALMECCANICI_INDUSTRIA in principle.related_sectors
        assert principle.precedent_strength == "high"

    def test_legal_principle_with_keywords(self):
        """Test legal principle with keywords."""
        principle = CassazioneLegalPrinciple(
            principle_id="PRIN-2025-003",
            decision_id="CASS-2025-789",
            title="Test",
            principle_text="Test principle",
            legal_area=LegalPrincipleArea.FERIE_PERMESSI,
            decision_date=date(2025, 1, 15),
            keywords=["ferie", "permessi", "maturazione", "godimento"],
        )

        assert len(principle.keywords) == 4
        assert "ferie" in principle.keywords

    def test_legal_principle_with_related_principles(self):
        """Test legal principle with related principles."""
        principle = CassazioneLegalPrinciple(
            principle_id="PRIN-2025-004",
            decision_id="CASS-2025-100",
            title="Test",
            principle_text="Test principle",
            legal_area=LegalPrincipleArea.ORARIO_LAVORO,
            decision_date=date(2025, 1, 15),
            related_principles=["PRIN-2020-050", "PRIN-2018-120"],
        )

        assert len(principle.related_principles) == 2


class TestCassazioneSearchQuery:
    """Test CassazioneSearchQuery model."""

    def test_create_search_query_minimal(self):
        """Test creating search query with no filters."""
        query = CassazioneSearchQuery()

        assert query.keywords is None
        assert query.max_results == 50  # Default
        assert query.include_full_text is False  # Default
        assert query.sort_by == "decision_date"  # Default
        assert query.sort_order == "desc"  # Default

    def test_search_query_with_keywords(self):
        """Test search query with keywords."""
        query = CassazioneSearchQuery(
            keywords=["licenziamento", "giusta causa"],
            max_results=100,
        )

        assert len(query.keywords) == 2
        assert "licenziamento" in query.keywords
        assert query.max_results == 100

    def test_search_query_with_legal_areas(self):
        """Test search query with legal areas filter."""
        query = CassazioneSearchQuery(
            legal_areas=[LegalPrincipleArea.LICENZIAMENTO, LegalPrincipleArea.RETRIBUZIONE],
        )

        assert len(query.legal_areas) == 2
        assert LegalPrincipleArea.LICENZIAMENTO in query.legal_areas

    def test_search_query_with_sectors(self):
        """Test search query with sector filter."""
        query = CassazioneSearchQuery(
            sectors=[CCNLSector.METALMECCANICI_INDUSTRIA, CCNLSector.EDILIZIA_INDUSTRIA],
        )

        assert len(query.sectors) == 2
        assert CCNLSector.METALMECCANICI_INDUSTRIA in query.sectors

    def test_search_query_with_sections(self):
        """Test search query with court section filter."""
        query = CassazioneSearchQuery(
            sections=[CassazioneSection.CIVILE_LAVORO, CassazioneSection.SEZIONI_UNITE_CIVILI],
        )

        assert len(query.sections) == 2
        assert CassazioneSection.CIVILE_LAVORO in query.sections

    def test_search_query_with_decision_types(self):
        """Test search query with decision type filter."""
        query = CassazioneSearchQuery(
            decision_types=[DecisionType.SENTENZA, DecisionType.MASSIMA],
        )

        assert len(query.decision_types) == 2
        assert DecisionType.SENTENZA in query.decision_types

    def test_search_query_with_date_range(self):
        """Test search query with date range."""
        query = CassazioneSearchQuery(
            date_from=date(2020, 1, 1),
            date_to=date(2025, 12, 31),
        )

        assert query.date_from == date(2020, 1, 1)
        assert query.date_to == date(2025, 12, 31)

    def test_search_query_with_precedent_value(self):
        """Test search query with precedent value filter."""
        query = CassazioneSearchQuery(
            precedent_value="high",
        )

        assert query.precedent_value == "high"

    def test_search_query_full_text(self):
        """Test search query with full text search."""
        query = CassazioneSearchQuery(
            full_text_search="contratto collettivo nazionale",
            include_full_text=True,
        )

        assert query.full_text_search is not None
        assert query.include_full_text is True

    def test_search_query_sorting(self):
        """Test search query with custom sorting."""
        query = CassazioneSearchQuery(
            sort_by="precedent_value",
            sort_order="asc",
        )

        assert query.sort_by == "precedent_value"
        assert query.sort_order == "asc"

    def test_search_query_max_results_validation(self):
        """Test search query max_results validation."""
        with pytest.raises(ValidationError):
            CassazioneSearchQuery(max_results=0)  # Should be >= 1

        with pytest.raises(ValidationError):
            CassazioneSearchQuery(max_results=1000)  # Should be <= 500


class TestCassazioneSearchResult:
    """Test CassazioneSearchResult model."""

    def test_create_search_result_minimal(self):
        """Test creating search result with required fields."""
        result = CassazioneSearchResult(
            decision_id="CASS-2025-123",
            decision_number=123,
            decision_year=2025,
            section=CassazioneSection.CIVILE_LAVORO,
            decision_type=DecisionType.SENTENZA,
            decision_date=date(2025, 1, 15),
            title="Test Decision",
            precedent_value="medium",
        )

        assert result.decision_id == "CASS-2025-123"
        assert result.section == CassazioneSection.CIVILE_LAVORO
        assert result.summary is None
        assert result.legal_areas == []
        assert result.related_sectors == []
        assert result.keywords == []
        assert result.relevance_score == 0.0  # Default

    def test_search_result_with_summary(self):
        """Test search result with summary."""
        result = CassazioneSearchResult(
            decision_id="CASS-2025-456",
            decision_number=456,
            decision_year=2025,
            section=CassazioneSection.CIVILE_LAVORO,
            decision_type=DecisionType.SENTENZA,
            decision_date=date(2025, 1, 15),
            title="Test",
            precedent_value="high",
            summary="La Corte ha stabilito...",
            legal_principle="Principio giuridico importante",
        )

        assert result.summary is not None
        assert result.legal_principle is not None

    def test_search_result_with_classification(self):
        """Test search result with classification."""
        result = CassazioneSearchResult(
            decision_id="CASS-2025-789",
            decision_number=789,
            decision_year=2025,
            section=CassazioneSection.CIVILE_LAVORO,
            decision_type=DecisionType.SENTENZA,
            decision_date=date(2025, 1, 15),
            title="Test",
            precedent_value="medium",
            legal_areas=[LegalPrincipleArea.LICENZIAMENTO, LegalPrincipleArea.RETRIBUZIONE],
            related_sectors=[CCNLSector.METALMECCANICI_INDUSTRIA],
            keywords=["licenziamento", "ccnl"],
        )

        assert len(result.legal_areas) == 2
        assert LegalPrincipleArea.LICENZIAMENTO in result.legal_areas
        assert CCNLSector.METALMECCANICI_INDUSTRIA in result.related_sectors

    def test_search_result_with_relevance(self):
        """Test search result with relevance score."""
        result = CassazioneSearchResult(
            decision_id="CASS-2025-100",
            decision_number=100,
            decision_year=2025,
            section=CassazioneSection.CIVILE_LAVORO,
            decision_type=DecisionType.MASSIMA,
            decision_date=date(2025, 1, 15),
            title="Test",
            precedent_value="high",
            relevance_score=0.95,
        )

        assert result.relevance_score == 0.95

    def test_search_result_with_full_text(self):
        """Test search result with full text."""
        result = CassazioneSearchResult(
            decision_id="CASS-2025-200",
            decision_number=200,
            decision_year=2025,
            section=CassazioneSection.CIVILE_LAVORO,
            decision_type=DecisionType.SENTENZA,
            decision_date=date(2025, 1, 15),
            title="Test",
            precedent_value="medium",
            full_text="Testo completo della sentenza...",
            source_url="https://italgiure.giustizia.it/...",
        )

        assert result.full_text is not None
        assert result.source_url is not None


class TestCassazioneJurisprudenceAnalysis:
    """Test CassazioneJurisprudenceAnalysis model."""

    def test_create_jurisprudence_analysis_minimal(self):
        """Test creating jurisprudence analysis with required fields."""
        analysis = CassazioneJurisprudenceAnalysis(
            analysis_id="ANAL-2025-001",
            legal_area=LegalPrincipleArea.LICENZIAMENTO,
            time_period={"from": date(2020, 1, 1), "to": date(2025, 1, 1)},
            trend_direction="stable",
        )

        assert analysis.analysis_id == "ANAL-2025-001"
        assert analysis.legal_area == LegalPrincipleArea.LICENZIAMENTO
        assert analysis.trend_direction == "stable"
        assert analysis.total_decisions == 0  # Default
        assert analysis.consistency_score == 0.0  # Default
        assert analysis.related_sectors == []
        assert analysis.dominant_principles == []

    def test_jurisprudence_analysis_with_results(self):
        """Test jurisprudence analysis with results."""
        analysis = CassazioneJurisprudenceAnalysis(
            analysis_id="ANAL-2025-002",
            legal_area=LegalPrincipleArea.RETRIBUZIONE,
            time_period={"from": date(2020, 1, 1), "to": date(2025, 1, 1)},
            trend_direction="evolving",
            total_decisions=150,
            consistency_score=0.82,
        )

        assert analysis.total_decisions == 150
        assert analysis.consistency_score == 0.82
        assert analysis.trend_direction == "evolving"

    def test_jurisprudence_analysis_with_findings(self):
        """Test jurisprudence analysis with key findings."""
        analysis = CassazioneJurisprudenceAnalysis(
            analysis_id="ANAL-2025-003",
            legal_area=LegalPrincipleArea.CCNL_INTERPRETAZIONE,
            related_sectors=[CCNLSector.METALMECCANICI_INDUSTRIA],
            time_period={"from": date(2020, 1, 1), "to": date(2025, 1, 1)},
            trend_direction="stable",
            dominant_principles=["PRIN-2020-100", "PRIN-2022-050"],
            recent_changes=["Nuovo orientamento su minimi retributivi"],
            conflicting_decisions=["CASS-2024-100 vs CASS-2024-200"],
        )

        assert len(analysis.dominant_principles) == 2
        assert len(analysis.recent_changes) == 1
        assert len(analysis.conflicting_decisions) == 1

    def test_jurisprudence_analysis_with_implications(self):
        """Test jurisprudence analysis with practical implications."""
        analysis = CassazioneJurisprudenceAnalysis(
            analysis_id="ANAL-2025-004",
            legal_area=LegalPrincipleArea.LICENZIAMENTO,
            time_period={"from": date(2020, 1, 1), "to": date(2025, 1, 1)},
            trend_direction="contradictory",
            ccnl_implications=["Rivedere clausole sul preavviso"],
            practice_recommendations=["Documentare sempre le motivazioni"],
        )

        assert len(analysis.ccnl_implications) == 1
        assert len(analysis.practice_recommendations) == 1

    def test_jurisprudence_analysis_with_supporting_data(self):
        """Test jurisprudence analysis with supporting data."""
        analysis = CassazioneJurisprudenceAnalysis(
            analysis_id="ANAL-2025-005",
            legal_area=LegalPrincipleArea.ORARIO_LAVORO,
            time_period={"from": date(2020, 1, 1), "to": date(2025, 1, 1)},
            trend_direction="stable",
            decision_distribution={"accolto": 75, "rigettato": 50, "inammissibile": 25},
            section_analysis={
                "civile_lavoro": {"count": 120, "avg_confidence": 0.9},
                "sezioni_unite": {"count": 30, "avg_confidence": 0.95},
            },
            citation_network={"CASS-2020-100": ["CASS-2021-200", "CASS-2022-300"]},
        )

        assert "accolto" in analysis.decision_distribution
        assert analysis.decision_distribution["accolto"] == 75
        assert "civile_lavoro" in analysis.section_analysis
        assert "CASS-2020-100" in analysis.citation_network


class TestCassazioneUpdate:
    """Test CassazioneUpdate model."""

    def test_create_update_minimal(self):
        """Test creating update with required fields."""
        update = CassazioneUpdate(
            update_type="new_decision",
        )

        assert update.update_id is not None  # Auto-generated UUID
        assert update.update_type == "new_decision"
        assert update.affected_decisions == []
        assert update.new_decisions == []
        assert update.updated_principles == []
        assert update.total_changes == 0
        assert update.processing_status == "completed"  # Default
        assert update.validation_errors == []

    def test_update_with_new_decisions(self):
        """Test update with new decisions."""
        update = CassazioneUpdate(
            update_type="new_decision",
            new_decisions=["CASS-2025-100", "CASS-2025-101", "CASS-2025-102"],
            total_changes=3,
            change_summary="Aggiunte 3 nuove decisioni",
            data_source="Italgiure Web Scraper",
        )

        assert len(update.new_decisions) == 3
        assert update.total_changes == 3
        assert update.change_summary != ""
        assert update.data_source != ""

    def test_update_with_decision_updates(self):
        """Test update with decision updates."""
        update = CassazioneUpdate(
            update_type="decision_update",
            affected_decisions=["CASS-2024-500", "CASS-2024-501"],
            total_changes=2,
            change_summary="Aggiornati testi completi",
        )

        assert update.update_type == "decision_update"
        assert len(update.affected_decisions) == 2

    def test_update_with_principle_updates(self):
        """Test update with principle updates."""
        update = CassazioneUpdate(
            update_type="principle_update",
            updated_principles=["PRIN-2025-001", "PRIN-2025-002"],
            total_changes=2,
            change_summary="Riclassificati principi giuridici",
        )

        assert len(update.updated_principles) == 2

    def test_update_with_validation_errors(self):
        """Test update with validation errors."""
        update = CassazioneUpdate(
            update_type="new_decision",
            validation_errors=["Missing decision date", "Invalid section code"],
            processing_status="failed",
        )

        assert len(update.validation_errors) == 2
        assert update.processing_status == "failed"

    def test_update_with_confidence_metrics(self):
        """Test update with confidence metrics."""
        update = CassazioneUpdate(
            update_type="new_decision",
            confidence_metrics={
                "extraction_accuracy": 0.92,
                "classification_confidence": 0.88,
                "principle_extraction": 0.85,
            },
        )

        assert "extraction_accuracy" in update.confidence_metrics
        assert update.confidence_metrics["extraction_accuracy"] == 0.92


class TestUtilityFunctions:
    """Test utility functions."""

    def test_extract_legal_keywords_basic(self):
        """Test basic keyword extraction."""
        text = "Il contratto collettivo nazionale prevede il licenziamento per giusta causa."
        keywords = extract_legal_keywords(text)

        assert "contratto collettivo" in keywords
        assert "ccnl" in keywords or "licenziamento" in keywords
        assert "giusta causa" in keywords

    def test_extract_legal_keywords_multiple(self):
        """Test extraction of multiple keywords."""
        text = "La retribuzione include ferie, permessi, malattia e contributi previdenziali."
        keywords = extract_legal_keywords(text)

        assert "retribuzione" in keywords
        assert "ferie" in keywords
        assert "permessi" in keywords
        assert "malattia" in keywords
        assert "contributi" in keywords

    def test_extract_legal_keywords_case_insensitive(self):
        """Test case-insensitive keyword extraction."""
        text = "LICENZIAMENTO e RETRIBUZIONE sono temi importanti."
        keywords = extract_legal_keywords(text)

        assert "licenziamento" in keywords
        assert "retribuzione" in keywords

    def test_extract_legal_keywords_empty_text(self):
        """Test keyword extraction with empty text."""
        keywords = extract_legal_keywords("")
        assert keywords == []

    def test_extract_legal_keywords_none_text(self):
        """Test keyword extraction with None text."""
        keywords = extract_legal_keywords(None)
        assert keywords == []

    def test_classify_precedent_value_high(self):
        """Test high precedent value classification."""
        value = classify_precedent_value(
            section=CassazioneSection.SEZIONI_UNITE_CIVILI,
            decision_type=DecisionType.MASSIMA,
            citations_count=15,
            legal_principle_clarity="high",
        )

        assert value == "high"

    def test_classify_precedent_value_medium(self):
        """Test medium precedent value classification."""
        value = classify_precedent_value(
            section=CassazioneSection.CIVILE_PRIMA,
            decision_type=DecisionType.ORDINANZA,
            citations_count=3,
            legal_principle_clarity="medium",
        )

        assert value == "medium"

    def test_classify_precedent_value_low(self):
        """Test low precedent value classification."""
        value = classify_precedent_value(
            section=CassazioneSection.CIVILE_TERZA,
            decision_type=DecisionType.ORDINANZA,
            citations_count=0,
            legal_principle_clarity="low",
        )

        assert value == "low"

    def test_classify_precedent_value_civil_labor_section(self):
        """Test precedent value for civil labor section."""
        value = classify_precedent_value(
            section=CassazioneSection.CIVILE_LAVORO,
            decision_type=DecisionType.SENTENZA,
            citations_count=8,
        )

        assert value in ["medium", "high"]

    def test_determine_related_sectors_metalmeccanici(self):
        """Test sector determination for metalmeccanici."""
        text = "Il CCNL dei metalmeccanici prevede..."
        sectors = determine_related_sectors(text, [])

        assert CCNLSector.METALMECCANICI_INDUSTRIA in sectors

    def test_determine_related_sectors_edilizia(self):
        """Test sector determination for edilizia."""
        text = "Nel settore edilizia e costruzioni..."
        sectors = determine_related_sectors(text, [])

        assert CCNLSector.EDILIZIA_INDUSTRIA in sectors

    def test_determine_related_sectors_commercio(self):
        """Test sector determination for commercio."""
        text = "I lavoratori del commercio e terziario..."
        sectors = determine_related_sectors(text, [])

        assert CCNLSector.COMMERCIO_TERZIARIO in sectors

    def test_determine_related_sectors_multiple(self):
        """Test sector determination with multiple sectors."""
        text = "Questa decisione si applica a metalmeccanici, commercio e edilizia."
        sectors = determine_related_sectors(text, [])

        assert CCNLSector.METALMECCANICI_INDUSTRIA in sectors
        assert CCNLSector.COMMERCIO_TERZIARIO in sectors
        assert CCNLSector.EDILIZIA_INDUSTRIA in sectors

    def test_determine_related_sectors_ccnl_interpretation(self):
        """Test sector determination for CCNL interpretation."""
        text = "Interpretazione generale"
        sectors = determine_related_sectors(text, [LegalPrincipleArea.CCNL_INTERPRETAZIONE])

        assert len(sectors) > 0  # Should return multiple broad sectors
        assert CCNLSector.METALMECCANICI_INDUSTRIA in sectors

    def test_determine_related_sectors_empty_text(self):
        """Test sector determination with empty text."""
        sectors = determine_related_sectors("", [])

        assert sectors == []

    def test_determine_related_sectors_no_match(self):
        """Test sector determination with no keyword matches."""
        text = "Testo generico senza riferimenti a settori specifici"
        sectors = determine_related_sectors(text, [LegalPrincipleArea.LICENZIAMENTO])

        # Should return empty list if no CCNL interpretation area
        assert isinstance(sectors, list)
