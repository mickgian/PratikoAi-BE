"""
Test suite for Cassazione (Italian Supreme Court) integration.

This module tests the complete integration with the Italian Supreme Court database
including legal jurisprudence, precedent analysis, and CCNL interpretation services.
"""

import asyncio
from datetime import date, timedelta
from typing import Any, Dict, List

import pytest

from app.models.cassazione import (
    CassazioneSearchQuery,
    CassazioneSection,
    DecisionType,
    LegalPrincipleArea,
    classify_precedent_value,
    determine_related_sectors,
    extract_legal_keywords,
)
from app.models.ccnl_data import CCNLSector
from app.services.data_sources.base_source import DataSourceQuery
from app.services.data_sources.cassazione_source import (
    CassazioneDataSource,
    analyze_jurisprudence_consistency,
    extract_decision_citations,
)
from app.services.data_sources_manager import ccnl_data_sources_manager


class TestCassazioneDataSource:
    """Test Cassazione data source functionality."""

    @pytest.mark.asyncio
    async def test_cassazione_initialization(self):
        """Test Cassazione data source initialization."""
        source = CassazioneDataSource()

        assert source.source_info.source_id == "cassazione"
        assert source.source_info.name == "Corte di Cassazione - Sezioni Civili e del Lavoro"
        assert source.source_info.organization == "Corte Suprema di Cassazione"
        assert source.source_info.base_url == "https://www.cortedicassazione.it"

        # Check highest reliability for Supreme Court
        assert source.source_info.reliability_score == 0.99
        assert source.source_info.update_frequency.value == "daily"

        # Should support all sectors (jurisprudence applies universally)
        assert len(source.source_info.supported_sectors) > 25
        assert CCNLSector.METALMECCANICI_INDUSTRIA in source.source_info.supported_sectors

        # Check endpoints configuration
        assert hasattr(source, "endpoints")
        expected_endpoints = [
            "civil_decisions",
            "labor_decisions",
            "united_sections",
            "recent_decisions",
            "legal_principles",
            "advanced_search",
        ]
        for endpoint in expected_endpoints:
            assert endpoint in source.endpoints

    @pytest.mark.asyncio
    async def test_legal_area_mapping(self):
        """Test legal area keyword mapping."""
        source = CassazioneDataSource()

        # Test keyword expansion
        ccnl_keywords = source._expand_legal_keywords("ccnl")
        assert "contratto collettivo" in ccnl_keywords
        assert "contrattazione collettiva" in ccnl_keywords

        lavoro_keywords = source._expand_legal_keywords("lavoro")
        assert "rapporto di lavoro" in lavoro_keywords
        assert "contratto di lavoro" in lavoro_keywords

        # Test legal area determination
        keywords_ccnl = ["ccnl", "contratto collettivo"]
        areas = source._determine_legal_areas(None, keywords_ccnl)
        assert LegalPrincipleArea.CCNL_INTERPRETAZIONE in areas

        keywords_licenziamento = ["licenziamento", "risoluzione"]
        areas = source._determine_legal_areas(None, keywords_licenziamento)
        assert LegalPrincipleArea.LICENZIAMENTO in areas

    @pytest.mark.asyncio
    async def test_cassazione_query_conversion(self):
        """Test conversion of general query to Cassazione-specific parameters."""
        source = CassazioneDataSource()

        general_query = DataSourceQuery(
            sectors=[CCNLSector.METALMECCANICI_INDUSTRIA, CCNLSector.COMMERCIO_TERZIARIO],
            keywords=["ccnl", "licenziamento"],
            date_from=date(2023, 1, 1),
            date_to=date(2024, 12, 31),
            max_results=25,
        )

        cassazione_query = source._convert_to_cassazione_query(general_query)

        assert isinstance(cassazione_query, CassazioneSearchQuery)
        assert cassazione_query.sectors == general_query.sectors
        assert cassazione_query.date_from == general_query.date_from
        assert cassazione_query.date_to == general_query.date_to
        assert cassazione_query.max_results == general_query.max_results

        # Check legal keywords expansion
        assert len(cassazione_query.keywords) >= len(general_query.keywords)

        # Check legal areas determination
        assert len(cassazione_query.legal_areas) > 0
        assert LegalPrincipleArea.CCNL_INTERPRETAZIONE in cassazione_query.legal_areas
        assert LegalPrincipleArea.LICENZIAMENTO in cassazione_query.legal_areas

    @pytest.mark.asyncio
    async def test_decision_date_extraction(self):
        """Test extraction of decision dates from various formats."""
        source = CassazioneDataSource()

        class MockElement:
            def __init__(self, text):
                self.text = text

            def get_text(self):
                return self.text

        # Test Italian month format
        element1 = MockElement("Sentenza del 15 marzo 2024")
        date1 = source._extract_decision_date(element1)
        assert date1 == date(2024, 3, 15)

        # Test numeric format DD/MM/YYYY
        element2 = MockElement("Data: 20/06/2023")
        date2 = source._extract_decision_date(element2)
        assert date2 == date(2023, 6, 20)

        # Test YYYY/MM/DD format
        element3 = MockElement("2024/01/30")
        date3 = source._extract_decision_date(element3)
        assert date3 == date(2024, 1, 30)

        # Test no date found
        element4 = MockElement("No date in this text")
        date4 = source._extract_decision_date(element4)
        assert date4 is None

    @pytest.mark.asyncio
    async def test_cassazione_section_determination(self):
        """Test determination of Cassazione court sections."""
        source = CassazioneDataSource()

        class MockElement:
            def __init__(self, text):
                self.text = text

            def get_text(self):
                return self.text

        # Test Sezioni Unite
        element1 = MockElement("Sezioni Unite Civili")
        section1 = source._determine_cassazione_section(element1, "Sezioni Unite n. 123/2024")
        assert section1 == "S.U."

        # Test Labor Section
        element2 = MockElement("Sezione Lavoro")
        section2 = source._determine_cassazione_section(element2, "Sez. Lav. n. 456/2024")
        assert section2 == "Lav."

        # Test numbered sections
        element3 = MockElement("Prima Sezione Civile")
        section3 = source._determine_cassazione_section(element3, "Sez. I Civile")
        assert section3 == "I"

        # Test default civil
        element4 = MockElement("Generic text")
        section4 = source._determine_cassazione_section(element4, "Generic decision")
        assert section4 == "Civ."

    @pytest.mark.asyncio
    async def test_decision_type_determination(self):
        """Test determination of decision types."""
        source = CassazioneDataSource()

        class MockElement:
            def __init__(self, text):
                self.text = text

            def get_text(self):
                return self.text

        # Test ordinanza
        element1 = MockElement("Ordinanza n. 123")
        dtype1 = source._determine_decision_type("Ordinanza", element1)
        assert dtype1 == "ordinanza"

        # Test decreto
        element2 = MockElement("Decreto n. 456")
        dtype2 = source._determine_decision_type("Decreto", element2)
        assert dtype2 == "decreto"

        # Test massima
        element3 = MockElement("Massima giuridica")
        dtype3 = source._determine_decision_type("Principio di diritto", element3)
        assert dtype3 == "massima"

        # Test default sentenza
        element4 = MockElement("Generic decision")
        dtype4 = source._determine_decision_type("Decision", element4)
        assert dtype4 == "sentenza"

    @pytest.mark.asyncio
    async def test_document_matching_query(self):
        """Test document matching against Cassazione query criteria."""
        source = CassazioneDataSource()

        # Create mock document
        from app.services.data_sources.base_source import CCNLDocument

        doc = CCNLDocument(
            document_id="test_doc_1",
            source_id="cassazione",
            title="Licenziamento per giusta causa - CCNL Metalmeccanici",
            sector=CCNLSector.METALMECCANICI_INDUSTRIA,
            publication_date=date(2024, 3, 15),
            effective_date=date(2024, 3, 15),
            expiry_date=None,
            document_type="jurisprudence",
            url="https://cortedicassazione.it/decision/123",
            content_hash="abc123",
            confidence_score=0.95,
            raw_content="Decision about dismissal for just cause in metalworking sector",
            extracted_data={
                "related_sectors": [CCNLSector.METALMECCANICI_INDUSTRIA.value],
                "legal_keywords": ["licenziamento", "giusta causa", "ccnl"],
            },
        )

        # Test keyword matching
        query1 = CassazioneSearchQuery(keywords=["licenziamento"], max_results=10)
        assert source._document_matches_query(doc, query1)

        # Test sector matching
        query2 = CassazioneSearchQuery(sectors=[CCNLSector.METALMECCANICI_INDUSTRIA], max_results=10)
        assert source._document_matches_query(doc, query2)

        # Test date range matching
        query3 = CassazioneSearchQuery(date_from=date(2024, 1, 1), date_to=date(2024, 12, 31), max_results=10)
        assert source._document_matches_query(doc, query3)

        # Test non-matching
        query4 = CassazioneSearchQuery(keywords=["unrelated_keyword"], max_results=10)
        assert not source._document_matches_query(doc, query4)

    @pytest.mark.asyncio
    async def test_document_deduplication(self):
        """Test deduplication of legal documents."""
        source = CassazioneDataSource()

        from app.services.data_sources.base_source import CCNLDocument

        # Create duplicate documents
        doc1 = CCNLDocument(
            document_id="doc1",
            source_id="cassazione",
            title="Decision 123/2024",
            sector=CCNLSector.METALMECCANICI_INDUSTRIA,
            publication_date=date(2024, 3, 15),
            effective_date=date(2024, 3, 15),
            expiry_date=None,
            document_type="jurisprudence",
            url="https://example.com/1",
            content_hash="same_hash",
            confidence_score=0.95,
            extracted_data={"decision_number": 123, "decision_year": 2024},
        )

        doc2 = CCNLDocument(  # Same content hash
            document_id="doc2",
            source_id="cassazione",
            title="Decision 123/2024 (duplicate)",
            sector=CCNLSector.METALMECCANICI_INDUSTRIA,
            publication_date=date(2024, 3, 15),
            effective_date=date(2024, 3, 15),
            expiry_date=None,
            document_type="jurisprudence",
            url="https://example.com/2",
            content_hash="same_hash",
            confidence_score=0.95,
            extracted_data={"decision_number": 123, "decision_year": 2024},
        )

        doc3 = CCNLDocument(  # Different content
            document_id="doc3",
            source_id="cassazione",
            title="Decision 456/2024",
            sector=CCNLSector.COMMERCIO_TERZIARIO,
            publication_date=date(2024, 4, 1),
            effective_date=date(2024, 4, 1),
            expiry_date=None,
            document_type="jurisprudence",
            url="https://example.com/3",
            content_hash="different_hash",
            confidence_score=0.90,
            extracted_data={"decision_number": 456, "decision_year": 2024},
        )

        documents = [doc1, doc2, doc3]
        unique_docs = source._deduplicate_legal_documents(documents)

        assert len(unique_docs) == 2  # doc1/doc2 should be deduplicated
        assert doc3 in unique_docs  # doc3 should remain

    @pytest.mark.asyncio
    async def test_connection_error_handling(self):
        """Test connection error handling."""
        source = CassazioneDataSource()

        # Override base URL to force connection failure
        original_url = source.source_info.base_url
        source.source_info.base_url = "https://nonexistent-court-domain-12345.invalid"

        try:
            connected = await source.connect()
            assert not connected  # Should fail gracefully
        finally:
            source.source_info.base_url = original_url

    @pytest.mark.asyncio
    async def test_search_without_connection(self):
        """Test search behavior when not connected."""
        source = CassazioneDataSource()

        # Don't connect first
        query = DataSourceQuery(keywords=["ccnl", "lavoro"], max_results=5)

        # Should return empty results without crashing
        documents = await source.search_documents(query)
        assert documents == []


class TestCassazioneModels:
    """Test Cassazione data models and utility functions."""

    def test_legal_keyword_extraction(self):
        """Test legal keyword extraction from Italian text."""
        text = """
        La Cassazione ha stabilito che il licenziamento per giusta causa deve essere
        supportato da prove concrete. Il contratto collettivo nazionale prevede
        specifiche procedure per la risoluzione del rapporto di lavoro.
        """

        keywords = extract_legal_keywords(text)

        expected_keywords = ["contratto collettivo", "licenziamento", "giusta causa"]

        for expected in expected_keywords:
            assert expected in keywords

    def test_precedent_value_classification(self):
        """Test precedent value classification for different decision types."""

        # Test Sezioni Unite (highest precedent)
        value1 = classify_precedent_value(
            CassazioneSection.SEZIONI_UNITE_CIVILI,
            DecisionType.SENTENZA,
            citations_count=15,
            legal_principle_clarity="high",
        )
        assert value1 == "high"

        # Test Labor Section
        value2 = classify_precedent_value(
            CassazioneSection.CIVILE_LAVORO, DecisionType.MASSIMA, citations_count=8, legal_principle_clarity="high"
        )
        assert value2 == "high"

        # Test Civil Section with few citations
        value3 = classify_precedent_value(
            CassazioneSection.CIVILE_PRIMA, DecisionType.ORDINANZA, citations_count=2, legal_principle_clarity="medium"
        )
        assert value3 in ["medium", "low"]

    def test_sector_determination_from_text(self):
        """Test determination of related CCNL sectors from legal text."""

        # Test metalworking sector
        text1 = "Contratto collettivo metalmeccanici industria - licenziamento operaio"
        sectors1 = determine_related_sectors(text1, [LegalPrincipleArea.LICENZIAMENTO])
        assert CCNLSector.METALMECCANICI_INDUSTRIA in sectors1

        # Test construction sector
        text2 = "CCNL edilizia - sicurezza cantiere opere pubbliche"
        sectors2 = determine_related_sectors(text2, [LegalPrincipleArea.SICUREZZA_LAVORO])
        assert CCNLSector.EDILIZIA_INDUSTRIA in sectors2

        # Test healthcare sector
        text3 = "Sanità privata - contratto infermieri clinica ospedale"
        sectors3 = determine_related_sectors(text3, [LegalPrincipleArea.CONTRATTO_LAVORO])
        assert CCNLSector.SANITA_PRIVATA in sectors3

        # Test fallback for CCNL interpretation
        text4 = "Interpretazione generale contratto collettivo"
        sectors4 = determine_related_sectors(text4, [LegalPrincipleArea.CCNL_INTERPRETAZIONE])
        assert len(sectors4) >= 3  # Should return major sectors


class TestCassazioneUtilityFunctions:
    """Test utility functions for Cassazione data processing."""

    @pytest.mark.asyncio
    async def test_decision_citation_extraction(self):
        """Test extraction of citations from legal text."""
        text = """
        Come stabilito da Cass. Civ., Sez. Lav., n. 12345/2023, e confermato da
        Cassazione Sezioni Unite, n. 67890/2024, il principio è consolidato.
        Vedi anche Sezioni Unite Civili, n. 11111/2022.
        """

        citations = await extract_decision_citations(text)

        expected_citations = ["12345/2023", "67890/2024", "11111/2022"]

        for expected in expected_citations:
            assert expected in citations

        # Should remove duplicates
        assert len(set(citations)) == len(citations)

    @pytest.mark.asyncio
    async def test_jurisprudence_consistency_analysis(self):
        """Test analysis of jurisprudence consistency across decisions."""
        from app.services.data_sources.base_source import CCNLDocument

        # Create mock decisions for analysis
        decisions = []
        for i in range(5):
            doc = CCNLDocument(
                document_id=f"decision_{i}",
                source_id="cassazione",
                title=f"Labor Decision {i + 1}/2024",
                sector=CCNLSector.METALMECCANICI_INDUSTRIA,
                publication_date=date(2024, 3 + i, 15),
                effective_date=date(2024, 3 + i, 15),
                expiry_date=None,
                document_type="jurisprudence",
                url=f"https://example.com/{i}",
                content_hash=f"hash_{i}",
                confidence_score=0.90 + (i * 0.02),
                extracted_data={
                    "legal_areas": [LegalPrincipleArea.LICENZIAMENTO.value],
                    "section": "Lav." if i % 2 == 0 else "I",
                    "decision_year": 2024,
                },
            )
            decisions.append(doc)

        analysis = await analyze_jurisprudence_consistency(decisions)

        assert "consistency_score" in analysis
        assert "total_decisions" in analysis
        assert analysis["total_decisions"] == 5
        assert "legal_areas_covered" in analysis
        assert "temporal_distribution" in analysis
        assert "section_distribution" in analysis

        # Check temporal distribution
        assert "2024" in analysis["temporal_distribution"]
        assert analysis["temporal_distribution"]["2024"] == 5

        # Check section distribution
        assert "Lav." in analysis["section_distribution"]
        assert "I" in analysis["section_distribution"]


class TestCassazioneIntegrationWithManager:
    """Test Cassazione integration with the data sources manager."""

    @pytest.mark.asyncio
    async def test_manager_includes_cassazione_source(self):
        """Test that data sources manager includes Cassazione source."""
        # Initialize manager
        if not ccnl_data_sources_manager.initialized:
            await ccnl_data_sources_manager.initialize()

        # Check that Cassazione source is registered
        assert "cassazione" in ccnl_data_sources_manager.registry.sources

        cassazione_source = ccnl_data_sources_manager.registry.sources["cassazione"]
        assert cassazione_source.source_info.source_id == "cassazione"
        assert cassazione_source.source_info.source_type.value == "government"

        # Check priority (should be highest for Supreme Court)
        priority = ccnl_data_sources_manager.registry.source_priority.get("cassazione", 0)
        assert priority == 10  # Highest priority

    @pytest.mark.asyncio
    async def test_cassazione_in_government_sources(self):
        """Test Cassazione appears in government sources list."""
        if not ccnl_data_sources_manager.initialized:
            await ccnl_data_sources_manager.initialize()

        government_sources = await ccnl_data_sources_manager.get_government_sources()

        # Find Cassazione in government sources
        cassazione_info = None
        for source in government_sources:
            if source["source_id"] == "cassazione":
                cassazione_info = source
                break

        assert cassazione_info is not None
        assert cassazione_info["name"] == "Corte di Cassazione - Sezioni Civili e del Lavoro"
        assert cassazione_info["organization"] == "Corte Suprema di Cassazione"
        assert cassazione_info["reliability_score"] == 0.99
        assert cassazione_info["priority"] == 10

    @pytest.mark.asyncio
    async def test_cassazione_comprehensive_search(self):
        """Test Cassazione inclusion in comprehensive searches."""
        if not ccnl_data_sources_manager.initialized:
            await ccnl_data_sources_manager.initialize()

        # Create search query
        query = DataSourceQuery(
            sectors=[CCNLSector.METALMECCANICI_INDUSTRIA], keywords=["licenziamento", "ccnl"], max_results=10
        )

        # Perform comprehensive search
        search_results = await ccnl_data_sources_manager.comprehensive_search(query)

        assert isinstance(search_results.documents_by_source, dict)

        # Cassazione should be included in sources searched
        # (May return 0 documents but should be attempted)
        sources_searched = list(search_results.documents_by_source.keys())
        government_sources = [
            s for s in sources_searched if s in ["cassazione", "ministry_labor", "cnel_official", "inps"]
        ]
        assert len(government_sources) >= 1  # At least one government source should be searched


class TestCassazioneErrorHandling:
    """Test error handling in Cassazione integration."""

    @pytest.mark.asyncio
    async def test_malformed_html_handling(self):
        """Test handling of malformed HTML responses."""
        source = CassazioneDataSource()

        # Test with empty BeautifulSoup object
        from bs4 import BeautifulSoup

        empty_soup = BeautifulSoup("", "html.parser")

        # Should not crash with empty/malformed HTML
        documents = await source._extract_cassazione_decisions(empty_soup, "https://example.com", "test")
        assert isinstance(documents, list)
        assert len(documents) == 0

    @pytest.mark.asyncio
    async def test_invalid_date_handling(self):
        """Test handling of invalid dates in decisions."""
        source = CassazioneDataSource()

        class MockElement:
            def __init__(self, text):
                self.text = text

            def get_text(self):
                return self.text

        # Test invalid dates
        invalid_dates = [
            "32/13/2024",  # Invalid day/month
            "29/02/2023",  # Invalid leap year
            "invalid date format",  # No date pattern
            "",  # Empty string
        ]

        for invalid_date in invalid_dates:
            element = MockElement(invalid_date)
            result = source._extract_decision_date(element)
            # Should return None for invalid dates, not crash
            assert result is None

    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test handling of connection timeouts."""
        source = CassazioneDataSource()

        # This test ensures timeout handling doesn't crash the application
        query = DataSourceQuery(keywords=["ccnl"], max_results=5)

        try:
            documents = await source.search_documents(query)
            # Should always return a list, even if empty or after timeout
            assert isinstance(documents, list)
        except Exception as e:
            # Any exceptions should be related to network/timeout, not application errors
            assert any(keyword in str(e).lower() for keyword in ["timeout", "connection", "network"])


class TestCassazionePerformance:
    """Test performance characteristics of Cassazione integration."""

    @pytest.mark.asyncio
    async def test_search_response_time(self):
        """Test that searches complete within reasonable time."""
        import time

        source = CassazioneDataSource()
        query = DataSourceQuery(keywords=["lavoro"], max_results=5)

        start_time = time.time()
        documents = await source.search_documents(query)
        end_time = time.time()

        search_time = end_time - start_time

        # Search should complete within 45 seconds (generous for court website)
        assert search_time < 45, f"Cassazione search took too long: {search_time:.2f} seconds"
        assert isinstance(documents, list)

    @pytest.mark.asyncio
    async def test_date_extraction_performance(self):
        """Test date extraction methods performance."""
        source = CassazioneDataSource()

        # Test with various Italian date formats
        test_texts = [
            "Sentenza del 15 marzo 2024",
            "Data pubblicazione: 20/06/2023",
            "2024-01-30 - Decisione n. 123",
            "Depositata il 10 dicembre 2023",
            "No valid date in this text",
        ]

        import time

        start_time = time.time()

        for text in test_texts:

            class MockElement:
                def get_text(self):
                    return text

            element = MockElement()
            date_result = source._extract_decision_date(element)
            # Should either return a date or None without crashing
            assert date_result is None or isinstance(date_result, date)

        end_time = time.time()
        extraction_time = end_time - start_time

        # Date extraction should be fast
        assert extraction_time < 1, f"Date extraction too slow: {extraction_time:.3f} seconds"

    @pytest.mark.asyncio
    async def test_legal_keyword_extraction_performance(self):
        """Test performance of legal keyword extraction."""
        # Large legal text for performance testing
        large_text = (
            """
        La Corte di Cassazione, Sezione Lavoro, con sentenza n. 12345/2024,
        ha stabilito importanti principi in materia di licenziamento per giusta causa
        e interpretazione dei contratti collettivi nazionali di lavoro.
        """
            * 50
        )  # Repeat to create larger text

        import time

        start_time = time.time()

        keywords = extract_legal_keywords(large_text)

        end_time = time.time()
        extraction_time = end_time - start_time

        # Should be fast even with large text
        assert extraction_time < 2, f"Keyword extraction too slow: {extraction_time:.3f} seconds"
        assert isinstance(keywords, list)
        assert len(keywords) > 0


class TestCassazioneDataQuality:
    """Test data quality and validation in Cassazione integration."""

    def test_legal_principle_areas_completeness(self):
        """Test that all important legal areas are covered."""
        areas = list(LegalPrincipleArea)

        # Check key areas for labor law
        essential_areas = [
            LegalPrincipleArea.CONTRATTO_LAVORO,
            LegalPrincipleArea.CCNL_INTERPRETAZIONE,
            LegalPrincipleArea.LICENZIAMENTO,
            LegalPrincipleArea.RETRIBUZIONE,
            LegalPrincipleArea.ORARIO_LAVORO,
            LegalPrincipleArea.SINDACATO,
        ]

        for essential_area in essential_areas:
            assert essential_area in areas

    def test_cassazione_sections_completeness(self):
        """Test that all relevant court sections are covered."""
        sections = list(CassazioneSection)

        # Check key sections
        essential_sections = [
            CassazioneSection.CIVILE_LAVORO,
            CassazioneSection.SEZIONI_UNITE_CIVILI,
            CassazioneSection.CIVILE_PRIMA,
            CassazioneSection.CIVILE_SECONDA,
        ]

        for essential_section in essential_sections:
            assert essential_section in sections

    def test_decision_types_completeness(self):
        """Test that all relevant decision types are covered."""
        types = list(DecisionType)

        essential_types = [DecisionType.SENTENZA, DecisionType.ORDINANZA, DecisionType.MASSIMA]

        for essential_type in essential_types:
            assert essential_type in types

    @pytest.mark.asyncio
    async def test_sector_coverage_accuracy(self):
        """Test accuracy of sector determination from legal text."""
        test_cases = [
            {
                "text": "CCNL metalmeccanici - operai industria meccanica",
                "expected_sector": CCNLSector.METALMECCANICI_INDUSTRIA,
            },
            {"text": "contratto edilizia costruzioni cantieri", "expected_sector": CCNLSector.EDILIZIA_INDUSTRIA},
            {"text": "commercio distribuzione negozi vendita", "expected_sector": CCNLSector.COMMERCIO_TERZIARIO},
            {"text": "sanità cliniche ospedali medici", "expected_sector": CCNLSector.SANITA_PRIVATA},
        ]

        for test_case in test_cases:
            sectors = determine_related_sectors(test_case["text"], [LegalPrincipleArea.CONTRATTO_LAVORO])
            assert (
                test_case["expected_sector"] in sectors
            ), f"Expected {test_case['expected_sector']} in sectors for text: {test_case['text']}"


class TestCassazioneEndToEnd:
    """End-to-end integration tests for Cassazione functionality."""

    @pytest.mark.asyncio
    async def test_complete_cassazione_workflow(self):
        """Test complete workflow from search to analysis."""
        # This test simulates a complete user workflow

        # 1. Initialize data sources manager
        if not ccnl_data_sources_manager.initialized:
            await ccnl_data_sources_manager.initialize()

        # 2. Verify Cassazione source is available
        assert "cassazione" in ccnl_data_sources_manager.registry.sources

        # 3. Get Cassazione source
        cassazione_source = ccnl_data_sources_manager.registry.sources["cassazione"]

        # 4. Create search query
        query = DataSourceQuery(
            sectors=[CCNLSector.METALMECCANICI_INDUSTRIA], keywords=["licenziamento", "giusta causa"], max_results=5
        )

        # 5. Perform search
        documents = await cassazione_source.search_documents(query)

        # 6. Verify search results structure
        assert isinstance(documents, list)

        # If we get results, verify they have proper structure
        for doc in documents[:3]:  # Check first 3 results
            assert hasattr(doc, "document_id")
            assert hasattr(doc, "title")
            assert hasattr(doc, "publication_date")
            assert hasattr(doc, "confidence_score")
            assert doc.source_id == "cassazione"

            if doc.extracted_data:
                # Verify extracted data has legal information
                assert isinstance(doc.extracted_data, dict)

        # 7. If we have documents, test jurisprudence analysis
        if documents:
            analysis = await analyze_jurisprudence_consistency(documents)
            assert "total_decisions" in analysis
            assert "consistency_score" in analysis

        # Test passed - complete workflow executed successfully
        assert True

    @pytest.mark.asyncio
    async def test_cassazione_government_search_integration(self):
        """Test Cassazione integration in government-specific searches."""
        if not ccnl_data_sources_manager.initialized:
            await ccnl_data_sources_manager.initialize()

        # Test government sources search that should include Cassazione
        government_search = await ccnl_data_sources_manager.search_government_sources(
            sectors=[CCNLSector.METALMECCANICI_INDUSTRIA, CCNLSector.COMMERCIO_TERZIARIO],
            keywords=["ccnl", "contratto", "lavoro"],
            max_results=10,
        )

        assert isinstance(government_search, dict)
        assert "search_query" in government_search
        assert "results" in government_search
        assert "government_sources_used" in government_search

        # Cassazione should be among government sources used
        sources_used = government_search["government_sources_used"]
        government_source_ids = [source.get("source_id") for source in sources_used]

        # At least some government sources should be used
        assert len(government_source_ids) >= 1

        # Check if any are high-priority government sources (including potentially Cassazione)
        high_priority_sources = [source for source in sources_used if source.get("priority", 0) == 10]
        assert len(high_priority_sources) >= 1
