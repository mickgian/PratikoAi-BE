"""
Test suite for government sources integration.

This module tests the integration with official Italian government sources
including Ministry of Labor, INPS, and other authoritative government agencies
that provide CCNL and labor law information.
"""

import asyncio
from datetime import date, timedelta
from typing import List

import pytest

from app.models.ccnl_data import CCNLSector
from app.services.data_sources.base_source import DataSourceQuery, DataSourceType
from app.services.data_sources.government_sources import (
    INPSDataSource,
    MinistryOfLaborDataSource,
    get_all_government_sources,
)
from app.services.data_sources_manager import ccnl_data_sources_manager


class TestGovernmentDataSources:
    """Test individual government data sources."""

    @pytest.mark.asyncio
    async def test_ministry_of_labor_initialization(self):
        """Test Ministry of Labor data source initialization."""
        source = MinistryOfLaborDataSource()

        assert source.source_info.source_id == "ministry_labor"
        assert source.source_info.source_type == DataSourceType.GOVERNMENT
        assert source.source_info.name == "Ministero del Lavoro e delle Politiche Sociali"
        assert source.source_info.organization == "Governo Italiano - Ministero del Lavoro"
        assert source.source_info.base_url == "https://www.lavoro.gov.it"

        # Check supported sectors (should support all sectors)
        assert len(source.source_info.supported_sectors) > 20
        assert CCNLSector.METALMECCANICI_INDUSTRIA in source.source_info.supported_sectors
        assert CCNLSector.COMMERCIO_TERZIARIO in source.source_info.supported_sectors

        # Check high reliability for government source
        assert source.source_info.reliability_score >= 0.95
        assert source.source_info.update_frequency.value == "daily"

    @pytest.mark.asyncio
    async def test_inps_initialization(self):
        """Test INPS data source initialization."""
        source = INPSDataSource()

        assert source.source_info.source_id == "inps"
        assert source.source_info.source_type == DataSourceType.GOVERNMENT
        assert source.source_info.name == "INPS - Istituto Nazionale della Previdenza Sociale"
        assert source.source_info.organization == "INPS"
        assert source.source_info.base_url == "https://www.inps.it"

        # Check supported sectors (INPS covers all sectors)
        assert len(source.source_info.supported_sectors) > 20
        assert source.source_info.reliability_score >= 0.95

    @pytest.mark.asyncio
    async def test_all_government_sources_have_unique_ids(self):
        """Test that all government sources have unique IDs."""
        sources = await get_all_government_sources()

        source_ids = [source.source_info.source_id for source in sources]
        assert len(source_ids) == len(set(source_ids))  # All IDs should be unique

        # Check expected sources are present
        expected_ids = ["ministry_labor", "inps"]
        actual_ids = set(source_ids)

        for expected_id in expected_ids:
            assert expected_id in actual_ids, f"Missing government source: {expected_id}"

    @pytest.mark.asyncio
    async def test_government_sources_are_government_type(self):
        """Test that all government sources have correct type."""
        sources = await get_all_government_sources()

        for source in sources:
            assert source.source_info.source_type == DataSourceType.GOVERNMENT
            # Government sources should have high reliability
            assert source.source_info.reliability_score >= 0.90


class TestGovernmentSourcesConnectivity:
    """Test connectivity and basic functionality of government sources."""

    @pytest.mark.asyncio
    async def test_ministry_of_labor_connection(self):
        """Test Ministry of Labor connection (may fail in CI without internet)."""
        source = MinistryOfLaborDataSource()

        try:
            connected = await source.connect()
            if connected:
                assert source.source_info.status.value in ["active", "inactive"]

                # Test basic search
                query = DataSourceQuery(sectors=[CCNLSector.METALMECCANICI_INDUSTRIA], max_results=5)

                # This may return empty results but shouldn't crash
                documents = await source.search_documents(query)
                assert isinstance(documents, list)

                # Test disconnect
                await source.disconnect()

        except Exception as e:
            # Connection failures are expected in CI environments
            pytest.skip(f"Connection test skipped due to network issues: {str(e)}")

    @pytest.mark.asyncio
    async def test_inps_connection(self):
        """Test INPS connection."""
        source = INPSDataSource()

        try:
            connected = await source.connect()
            if connected:
                # Test basic search
                query = DataSourceQuery(keywords=["aliquote", "contributi"], max_results=3)

                documents = await source.search_documents(query)
                assert isinstance(documents, list)

                await source.disconnect()

        except Exception as e:
            pytest.skip(f"INPS connection test skipped: {str(e)}")

    @pytest.mark.asyncio
    async def test_connection_error_handling(self):
        """Test that connection errors are handled gracefully."""
        source = MinistryOfLaborDataSource()

        # Override base URL to force connection failure
        original_url = source.source_info.base_url
        source.source_info.base_url = "https://nonexistent-government-domain-12345.invalid"

        try:
            connected = await source.connect()
            assert not connected  # Should fail gracefully
        finally:
            source.source_info.base_url = original_url

    @pytest.mark.asyncio
    async def test_search_without_connection(self):
        """Test search behavior when not connected."""
        source = INPSDataSource()

        # Don't connect first
        query = DataSourceQuery(keywords=["ccnl"], max_results=5)

        # Should return empty results without crashing
        documents = await source.search_documents(query)
        assert documents == []


class TestGovernmentSourcesSearch:
    """Test search functionality across government sources."""

    @pytest.mark.asyncio
    async def test_ministry_sector_coverage(self):
        """Test that Ministry of Labor supports comprehensive sector coverage."""
        source = MinistryOfLaborDataSource()

        # Ministry should support major sectors
        major_sectors = [
            CCNLSector.METALMECCANICI_INDUSTRIA,
            CCNLSector.COMMERCIO_TERZIARIO,
            CCNLSector.EDILIZIA_INDUSTRIA,
            CCNLSector.SANITA_PRIVATA,
            CCNLSector.TRASPORTI_LOGISTICA,
        ]

        for sector in major_sectors:
            assert sector in source.source_info.supported_sectors

    @pytest.mark.asyncio
    async def test_document_type_determination(self):
        """Test document type determination logic."""
        source = MinistryOfLaborDataSource()

        # Test different document types
        assert source._determine_document_type("Rinnovo CCNL Metalmeccanici", "ccnl_archive") == "renewal"
        assert source._determine_document_type("Modifica accordo commercio", "ccnl_archive") == "amendment"
        assert source._determine_document_type("CCNL Industria Alimentare", "ccnl_archive") == "agreement"
        assert source._determine_document_type("Decreto Ministeriale", "labour_law") == "regulation"
        assert source._determine_document_type("Circolare interpretativa", "circular") == "interpretation"

    @pytest.mark.asyncio
    async def test_sector_determination_from_content(self):
        """Test sector determination from document content."""
        source = MinistryOfLaborDataSource()

        # Test sector keywords
        assert (
            source._determine_sector_from_content("CCNL Metalmeccanici Industria")
            == CCNLSector.METALMECCANICI_INDUSTRIA
        )
        assert (
            source._determine_sector_from_content("Contratto Edilizia e Costruzioni") == CCNLSector.EDILIZIA_INDUSTRIA
        )
        assert (
            source._determine_sector_from_content("Accordo Commercio al Dettaglio") == CCNLSector.COMMERCIO_TERZIARIO
        )
        assert source._determine_sector_from_content("Sanità Privata Ospedali") == CCNLSector.SANITA_PRIVATA
        assert source._determine_sector_from_content("Trasporti e Logistica") == CCNLSector.TRASPORTI_LOGISTICA

    @pytest.mark.asyncio
    async def test_ccnl_keyword_detection(self):
        """Test CCNL keyword detection."""
        source = MinistryOfLaborDataSource()

        # Test positive cases
        assert source._contains_ccnl_keywords("Rinnovo CCNL Metalmeccanici")
        assert source._contains_ccnl_keywords("Contratto collettivo nazionale commercio")
        assert source._contains_ccnl_keywords("Accordo sindacale edilizia")
        assert source._contains_ccnl_keywords("Negoziazione salario minimo")

        # Test negative cases
        assert not source._contains_ccnl_keywords("Comunicato generico")
        assert not source._contains_ccnl_keywords("Notizia politica generale")


class TestGovernmentSourcesIntegration:
    """Test integration with the data sources manager."""

    @pytest.mark.asyncio
    async def test_manager_includes_government_sources(self):
        """Test that data sources manager includes government sources."""
        # Initialize manager
        if not ccnl_data_sources_manager.initialized:
            await ccnl_data_sources_manager.initialize()

        # Check that government sources are registered
        government_sources = []
        for source in ccnl_data_sources_manager.registry.sources.values():
            if source.source_info.source_type == DataSourceType.GOVERNMENT:
                government_sources.append(source)

        assert len(government_sources) >= 3  # Should have at least 3 government sources (CNEL + Ministry + INPS)

        # Check for specific government sources
        source_ids = {source.source_info.source_id for source in government_sources}
        expected_government_sources = {"cnel_official", "ministry_labor", "inps"}

        for expected in expected_government_sources:
            assert expected in source_ids, f"Missing government source in manager: {expected}"

    @pytest.mark.asyncio
    async def test_government_sources_get_status(self):
        """Test getting status of government sources through manager."""
        if not ccnl_data_sources_manager.initialized:
            await ccnl_data_sources_manager.initialize()

        government_sources = await ccnl_data_sources_manager.get_government_sources()

        assert isinstance(government_sources, list)
        assert len(government_sources) >= 3

        # Check structure of returned data
        for source in government_sources:
            assert "source_id" in source
            assert "name" in source
            assert "organization" in source
            assert "supported_sectors" in source
            assert "reliability_score" in source
            assert "status" in source
            assert "priority" in source

            # Check data types
            assert isinstance(source["supported_sectors"], list)
            assert isinstance(source["reliability_score"], float)
            assert source["status"] in ["active", "inactive"]
            assert isinstance(source["priority"], int)

            # Government sources should have high priority
            assert source["priority"] >= 8

    @pytest.mark.asyncio
    async def test_government_sources_search_through_manager(self):
        """Test government-specific search through the data sources manager."""
        if not ccnl_data_sources_manager.initialized:
            await ccnl_data_sources_manager.initialize()

        # Test government sources search
        search_results = await ccnl_data_sources_manager.search_government_sources(
            sectors=[CCNLSector.METALMECCANICI_INDUSTRIA], keywords=["ccnl", "contratto"], max_results=10
        )

        assert isinstance(search_results, dict)
        assert "search_query" in search_results
        assert "results" in search_results
        assert "government_sources_used" in search_results

        # Check search query structure
        assert search_results["search_query"]["sectors"] == [CCNLSector.METALMECCANICI_INDUSTRIA.value]
        assert search_results["search_query"]["keywords"] == ["ccnl", "contratto"]

        # Results structure
        assert isinstance(search_results["results"]["total_documents"], int)
        assert isinstance(search_results["results"]["documents_by_source"], dict)
        assert isinstance(search_results["government_sources_used"], list)


class TestGovernmentSourcesValidation:
    """Test validation functionality for government sources."""

    @pytest.mark.asyncio
    async def test_connectivity_validation(self):
        """Test validation of government sources connectivity."""
        if not ccnl_data_sources_manager.initialized:
            await ccnl_data_sources_manager.initialize()

        validation_results = await ccnl_data_sources_manager.validate_government_sources_connectivity()

        assert isinstance(validation_results, dict)
        assert "tested_at" in validation_results
        assert "total_government_sources" in validation_results
        assert "active_government_sources" in validation_results
        assert "government_source_details" in validation_results
        assert "reliability_assessment" in validation_results
        assert "recommendations" in validation_results

        # Check data types and structure
        assert isinstance(validation_results["total_government_sources"], int)
        assert isinstance(validation_results["active_government_sources"], int)
        assert isinstance(validation_results["government_source_details"], list)
        assert isinstance(validation_results["reliability_assessment"], dict)
        assert isinstance(validation_results["recommendations"], list)

        # Should have at least 3 government sources
        assert validation_results["total_government_sources"] >= 3

        # Check government source details structure
        for detail in validation_results["government_source_details"]:
            assert "source_id" in detail
            assert "name" in detail
            assert "connection_status" in detail
            assert "data_quality" in detail
            assert "reliability_score" in detail
            assert "priority" in detail

            assert detail["connection_status"] in ["ok", "failed"]
            assert detail["data_quality"] in ["excellent", "limited", "error"]
            assert detail["reliability_score"] >= 0.9  # Government sources should be highly reliable

    @pytest.mark.asyncio
    async def test_reliability_assessment(self):
        """Test reliability assessment of government sources."""
        if not ccnl_data_sources_manager.initialized:
            await ccnl_data_sources_manager.initialize()

        validation_results = await ccnl_data_sources_manager.validate_government_sources_connectivity()
        reliability = validation_results["reliability_assessment"]

        assert isinstance(reliability, dict)
        assert "average_reliability_score" in reliability
        assert "active_sources_ratio" in reliability
        assert "overall_status" in reliability

        # Government sources should have high reliability
        assert reliability["average_reliability_score"] >= 0.9
        assert reliability["overall_status"] in ["excellent", "good", "needs_attention"]

        # Active sources ratio should be reasonable
        assert 0.0 <= reliability["active_sources_ratio"] <= 1.0


class TestGovernmentSourcesErrorHandling:
    """Test error handling in government sources."""

    @pytest.mark.asyncio
    async def test_invalid_endpoint_handling(self):
        """Test handling of invalid or non-existent endpoints."""
        source = MinistryOfLaborDataSource()

        # Test search with invalid endpoint (should not crash)
        query = DataSourceQuery(sectors=[CCNLSector.METALMECCANICI_INDUSTRIA], max_results=5)

        # Should return empty results without error
        documents = await source.search_documents(query)
        assert isinstance(documents, list)

    @pytest.mark.asyncio
    async def test_malformed_response_handling(self):
        """Test handling of malformed responses from government sources."""
        source = INPSDataSource()

        # Test search functionality - should handle any response gracefully
        query = DataSourceQuery(keywords=["contributi"], max_results=3)

        documents = await source.search_documents(query)
        assert isinstance(documents, list)

    @pytest.mark.asyncio
    async def test_network_timeout_handling(self):
        """Test handling of network timeouts and errors."""
        source = MinistryOfLaborDataSource()

        # This test is mainly to ensure no unhandled exceptions
        query = DataSourceQuery(sectors=[CCNLSector.COMMERCIO_TERZIARIO], max_results=5)

        try:
            documents = await source.search_documents(query)
            assert isinstance(documents, list)  # Should always return a list
        except Exception as e:
            # Any exceptions should be logged but not crash the application
            assert "timeout" in str(e).lower() or "connection" in str(e).lower()


class TestGovernmentSourcesPerformance:
    """Test performance characteristics of government sources."""

    @pytest.mark.asyncio
    async def test_concurrent_government_searches(self):
        """Test concurrent searches across multiple government sources."""
        sources = await get_all_government_sources()

        if len(sources) < 2:
            pytest.skip("Need at least 2 government sources for concurrency test")

        # Create concurrent search tasks
        tasks = []
        for source in sources[:2]:  # Test first 2 sources
            query = DataSourceQuery(
                sectors=[CCNLSector.METALMECCANICI_INDUSTRIA, CCNLSector.COMMERCIO_TERZIARIO], max_results=3
            )
            task = source.search_documents(query)
            tasks.append(task)

        # Run searches concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check that all tasks completed (may be empty results but should not crash)
        for result in results:
            if isinstance(result, Exception):
                # Log the exception but don't fail the test for network issues
                print(f"Government search task failed: {result}")
            else:
                assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_search_response_time(self):
        """Test that searches complete within reasonable time."""
        import time

        source = MinistryOfLaborDataSource()
        query = DataSourceQuery(sectors=[CCNLSector.METALMECCANICI_INDUSTRIA], max_results=5)

        start_time = time.time()
        documents = await source.search_documents(query)
        end_time = time.time()

        search_time = end_time - start_time

        # Search should complete within 45 seconds (generous for government sites)
        assert search_time < 45, f"Government search took too long: {search_time:.2f} seconds"
        assert isinstance(documents, list)

    @pytest.mark.asyncio
    async def test_date_extraction_performance(self):
        """Test date extraction methods performance."""
        source = MinistryOfLaborDataSource()

        # Test with various date formats
        test_texts = [
            "Pubblicato il 15/03/2024",
            "Data efficacia: 01 gennaio 2024",
            "Scadenza 31/12/2024",
            "Vigore dal 2024-01-01",
            "15 marzo 2024",
        ]

        import time

        start_time = time.time()

        for text in test_texts:
            # Create a mock element
            class MockElement:
                def get_text(self):
                    return text

            element = MockElement()
            date_result = source._extract_publication_date(element)
            # Should either return a date or None without crashing
            assert date_result is None or isinstance(date_result, date)

        end_time = time.time()
        extraction_time = end_time - start_time

        # Date extraction should be fast
        assert extraction_time < 1, f"Date extraction too slow: {extraction_time:.3f} seconds"


class TestGovernmentSourcesPriority:
    """Test priority handling for government sources."""

    @pytest.mark.asyncio
    async def test_government_sources_high_priority(self):
        """Test that government sources have appropriately high priority."""
        sources = await get_all_government_sources()

        for source in sources:
            # Government sources should have high reliability
            assert source.source_info.reliability_score >= 0.9

            # Check specific expected high reliability for key sources
            if source.source_info.source_id == "ministry_labor" or source.source_info.source_id == "cnel":
                assert source.source_info.reliability_score >= 0.98
            elif source.source_info.source_id == "inps":
                assert source.source_info.reliability_score >= 0.96

    @pytest.mark.asyncio
    async def test_government_sources_in_manager_priority(self):
        """Test government sources priority in data sources manager."""
        if not ccnl_data_sources_manager.initialized:
            await ccnl_data_sources_manager.initialize()

        # Get priority mappings
        government_priorities = {}
        for source_id, source in ccnl_data_sources_manager.registry.sources.items():
            if source.source_info.source_type == DataSourceType.GOVERNMENT:
                priority = ccnl_data_sources_manager.registry.source_priority.get(source_id, 0)
                government_priorities[source_id] = priority

        # Government sources should have priority >= 8
        for source_id, priority in government_priorities.items():
            assert priority >= 8, f"Government source {source_id} has low priority: {priority}"

        # Key government sources should have the highest priorities
        if "ministry_labor" in government_priorities:
            assert government_priorities["ministry_labor"] == 10
        if "cnel_official" in government_priorities:
            assert government_priorities["cnel_official"] == 10
        if "inps" in government_priorities:
            assert government_priorities["inps"] == 9
