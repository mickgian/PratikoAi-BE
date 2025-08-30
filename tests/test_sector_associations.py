"""
Test suite for sector-specific associations integration.

This module tests the integration with Italian sector-specific labor associations
like Federmeccanica, Federchimica, etc. that provide specialized CCNL data.
"""

import pytest
import asyncio
from datetime import date, timedelta
from typing import List

from app.models.ccnl_data import CCNLSector
from app.services.data_sources.sector_associations import (
    FedermeccanicaDataSource, FederchimicaDataSource, FederalimentareDataSource,
    ASSINFORMDataSource, ASSOMARMIDataSource, get_all_sector_associations,
    get_sector_associations_for_sectors
)
from app.services.data_sources.base_source import DataSourceType, DataSourceQuery
from app.services.data_sources_manager import ccnl_data_sources_manager


class TestSectorAssociationsDataSources:
    """Test individual sector association data sources."""
    
    @pytest.mark.asyncio
    async def test_federmeccanica_initialization(self):
        """Test Federmeccanica data source initialization."""
        source = FedermeccanicaDataSource()
        
        assert source.source_info.source_id == "federmeccanica"
        assert source.source_info.source_type == DataSourceType.SECTOR_ASSOCIATION
        assert source.source_info.name == "Federmeccanica - Federazione Sindacale dell'Industria Metalmeccanica Italiana"
        assert source.source_info.organization == "Federmeccanica"
        assert source.source_info.base_url == "https://www.federmeccanica.it"
        
        # Check supported sectors
        expected_sectors = [
            CCNLSector.METALMECCANICI_INDUSTRIA,
            CCNLSector.METALMECCANICI_ARTIGIANI
        ]
        assert set(source.source_info.supported_sectors) == set(expected_sectors)
        assert source.source_info.reliability_score >= 0.9  # High reliability for authoritative source
    
    @pytest.mark.asyncio
    async def test_federchimica_initialization(self):
        """Test Federchimica data source initialization."""
        source = FederchimicaDataSource()
        
        assert source.source_info.source_id == "federchimica"
        assert source.source_info.source_type == DataSourceType.SECTOR_ASSOCIATION
        assert CCNLSector.CHIMICI_FARMACEUTICI in source.source_info.supported_sectors
        assert CCNLSector.GOMMA_PLASTICA in source.source_info.supported_sectors
        assert source.source_info.reliability_score >= 0.9
    
    @pytest.mark.asyncio
    async def test_federalimentare_initialization(self):
        """Test Federalimentare data source initialization."""
        source = FederalimentareDataSource()
        
        assert source.source_info.source_id == "federalimentare"
        assert source.source_info.source_type == DataSourceType.SECTOR_ASSOCIATION
        assert CCNLSector.ALIMENTARI_INDUSTRIA in source.source_info.supported_sectors
        assert CCNLSector.PANIFICAZIONE in source.source_info.supported_sectors
    
    @pytest.mark.asyncio
    async def test_assinform_initialization(self):
        """Test ASSINFORM data source initialization."""
        source = ASSINFORMDataSource()
        
        assert source.source_info.source_id == "assinform"
        assert source.source_info.source_type == DataSourceType.SECTOR_ASSOCIATION
        assert CCNLSector.ICT in source.source_info.supported_sectors
        assert CCNLSector.TELECOMUNICAZIONI in source.source_info.supported_sectors
    
    @pytest.mark.asyncio
    async def test_assomarmi_initialization(self):
        """Test ASSOMARMI data source initialization."""
        source = ASSOMARMIDataSource()
        
        assert source.source_info.source_id == "assomarmi"
        assert source.source_info.source_type == DataSourceType.SECTOR_ASSOCIATION
        assert CCNLSector.EDILIZIA_INDUSTRIA in source.source_info.supported_sectors
        assert CCNLSector.EDILIZIA_ARTIGIANATO in source.source_info.supported_sectors
    
    @pytest.mark.asyncio
    async def test_all_sources_have_unique_ids(self):
        """Test that all sector association sources have unique IDs."""
        sources = await get_all_sector_associations()
        
        source_ids = [source.source_info.source_id for source in sources]
        assert len(source_ids) == len(set(source_ids))  # All IDs should be unique
        
        # Check expected sources are present
        expected_ids = ["federmeccanica", "federchimica", "federalimentare", "assinform", "assomarmi"]
        actual_ids = set(source_ids)
        
        for expected_id in expected_ids:
            assert expected_id in actual_ids, f"Missing sector association: {expected_id}"


class TestSectorAssociationsConnectivity:
    """Test connectivity and basic functionality of sector associations."""
    
    @pytest.mark.asyncio
    async def test_federmeccanica_connection(self):
        """Test Federmeccanica connection (may fail in CI without internet)."""
        source = FedermeccanicaDataSource()
        
        try:
            connected = await source.connect()
            if connected:
                assert source.source_info.status.value in ["active", "inactive"]
                
                # Test basic search
                query = DataSourceQuery(
                    sectors=[CCNLSector.METALMECCANICI_INDUSTRIA],
                    max_results=5
                )
                
                # This may return empty results but shouldn't crash
                documents = await source.search_documents(query)
                assert isinstance(documents, list)
                
                # Test disconnect
                await source.disconnect()
                
        except Exception as e:
            # Connection failures are expected in CI environments
            pytest.skip(f"Connection test skipped due to network issues: {str(e)}")
    
    @pytest.mark.asyncio
    async def test_connection_error_handling(self):
        """Test that connection errors are handled gracefully."""
        source = FedermeccanicaDataSource()
        
        # Override base URL to force connection failure
        original_url = source.source_info.base_url
        source.source_info.base_url = "https://nonexistent-domain-12345.invalid"
        
        try:
            connected = await source.connect()
            assert not connected  # Should fail gracefully
        finally:
            source.source_info.base_url = original_url
    
    @pytest.mark.asyncio
    async def test_search_without_connection(self):
        """Test search behavior when not connected."""
        source = FederchimicaDataSource()
        
        # Don't connect first
        query = DataSourceQuery(
            sectors=[CCNLSector.CHIMICI_FARMACEUTICI],
            max_results=5
        )
        
        # Should return empty results without crashing
        documents = await source.search_documents(query)
        assert documents == []


class TestSectorAssociationsSearch:
    """Test search functionality across sector associations."""
    
    @pytest.mark.asyncio
    async def test_sector_filtering(self):
        """Test that sector associations only search their supported sectors."""
        source = FedermeccanicaDataSource()
        
        # Query for unsupported sector
        query = DataSourceQuery(
            sectors=[CCNLSector.SANITA_PRIVATA],  # Not supported by Federmeccanica
            max_results=10
        )
        
        documents = await source.search_documents(query)
        assert documents == []  # Should return empty for unsupported sectors
        
        # Query for supported sector
        query_supported = DataSourceQuery(
            sectors=[CCNLSector.METALMECCANICI_INDUSTRIA],
            max_results=10
        )
        
        # This should at least attempt to search (may return empty but not fail)
        documents_supported = await source.search_documents(query_supported)
        assert isinstance(documents_supported, list)
    
    @pytest.mark.asyncio
    async def test_get_associations_for_sectors(self):
        """Test getting sector associations for specific sectors."""
        # Test metalworking sector
        metal_sources = await get_sector_associations_for_sectors([CCNLSector.METALMECCANICI_INDUSTRIA])
        
        federmeccanica_found = False
        for source in metal_sources:
            if source.source_info.source_id == "federmeccanica":
                federmeccanica_found = True
                break
        
        assert federmeccanica_found, "Federmeccanica should be returned for metalworking sector"
        
        # Test chemical sector
        chemical_sources = await get_sector_associations_for_sectors([CCNLSector.CHIMICI_FARMACEUTICI])
        
        federchimica_found = False
        for source in chemical_sources:
            if source.source_info.source_id == "federchimica":
                federchimica_found = True
                break
        
        assert federchimica_found, "Federchimica should be returned for chemical sector"
        
        # Test non-covered sector (should return empty)
        unknown_sources = await get_sector_associations_for_sectors([CCNLSector.SANITA_PRIVATA])
        sector_association_sources = [
            s for s in unknown_sources 
            if s.source_info.source_type == DataSourceType.SECTOR_ASSOCIATION
        ]
        # May be empty or contain generic associations
        assert isinstance(sector_association_sources, list)


class TestSectorAssociationsIntegration:
    """Test integration with the data sources manager."""
    
    @pytest.mark.asyncio
    async def test_manager_includes_sector_associations(self):
        """Test that data sources manager includes sector associations."""
        # Initialize manager
        if not ccnl_data_sources_manager.initialized:
            await ccnl_data_sources_manager.initialize()
        
        # Check that sector associations are registered
        sector_sources = []
        for source in ccnl_data_sources_manager.registry.sources.values():
            if source.source_info.source_type == DataSourceType.SECTOR_ASSOCIATION:
                sector_sources.append(source)
        
        assert len(sector_sources) >= 5  # Should have at least 5 sector associations
        
        # Check for specific sector associations
        source_ids = {source.source_info.source_id for source in sector_sources}
        expected_associations = {"federmeccanica", "federchimica", "federalimentare", "assinform", "assomarmi"}
        
        for expected in expected_associations:
            assert expected in source_ids, f"Missing sector association in manager: {expected}"
    
    @pytest.mark.asyncio
    async def test_sector_associations_get_status(self):
        """Test getting status of sector associations through manager."""
        if not ccnl_data_sources_manager.initialized:
            await ccnl_data_sources_manager.initialize()
        
        associations = await ccnl_data_sources_manager.get_sector_associations()
        
        assert isinstance(associations, list)
        assert len(associations) >= 5
        
        # Check structure of returned data
        for association in associations:
            assert "source_id" in association
            assert "name" in association
            assert "organization" in association
            assert "supported_sectors" in association
            assert "reliability_score" in association
            assert "status" in association
            
            # Check data types
            assert isinstance(association["supported_sectors"], list)
            assert isinstance(association["reliability_score"], float)
            assert association["status"] in ["active", "inactive"]
    
    @pytest.mark.asyncio
    async def test_sector_association_coverage(self):
        """Test getting sector association coverage mapping."""
        if not ccnl_data_sources_manager.initialized:
            await ccnl_data_sources_manager.initialize()
        
        coverage = await ccnl_data_sources_manager.get_sector_association_coverage()
        
        assert isinstance(coverage, dict)
        
        # Check that metalworking is covered by Federmeccanica
        assert CCNLSector.METALMECCANICI_INDUSTRIA in coverage
        assert "federmeccanica" in coverage[CCNLSector.METALMECCANICI_INDUSTRIA]
        
        # Check that chemical sector is covered by Federchimica
        assert CCNLSector.CHIMICI_FARMACEUTICI in coverage
        assert "federchimica" in coverage[CCNLSector.CHIMICI_FARMACEUTICI]
    
    @pytest.mark.asyncio
    async def test_sector_specific_search_through_manager(self):
        """Test sector-specific search through the data sources manager."""
        if not ccnl_data_sources_manager.initialized:
            await ccnl_data_sources_manager.initialize()
        
        # Test metalworking search
        search_results = await ccnl_data_sources_manager.search_sector_specific(
            sectors=[CCNLSector.METALMECCANICI_INDUSTRIA],
            keywords=["ccnl", "contratto"],
            max_results=10
        )
        
        assert isinstance(search_results, dict)
        assert "search_query" in search_results
        assert "results" in search_results
        assert "sector_associations_used" in search_results
        
        # Check search query structure
        assert search_results["search_query"]["sectors"] == ["metalmeccanici_industria"]
        assert search_results["search_query"]["keywords"] == ["ccnl", "contratto"]
        
        # Results structure
        assert isinstance(search_results["results"]["total_documents"], int)
        assert isinstance(search_results["results"]["documents_by_source"], dict)
        assert isinstance(search_results["sector_associations_used"], list)


class TestSectorAssociationsValidation:
    """Test validation functionality for sector associations."""
    
    @pytest.mark.asyncio
    async def test_connectivity_validation(self):
        """Test validation of sector associations connectivity."""
        if not ccnl_data_sources_manager.initialized:
            await ccnl_data_sources_manager.initialize()
        
        validation_results = await ccnl_data_sources_manager.validate_sector_associations_connectivity()
        
        assert isinstance(validation_results, dict)
        assert "tested_at" in validation_results
        assert "total_associations" in validation_results
        assert "active_associations" in validation_results
        assert "association_details" in validation_results
        assert "coverage_gaps" in validation_results
        assert "recommendations" in validation_results
        
        # Check data types and structure
        assert isinstance(validation_results["total_associations"], int)
        assert isinstance(validation_results["active_associations"], int)
        assert isinstance(validation_results["association_details"], list)
        assert isinstance(validation_results["coverage_gaps"], list)
        assert isinstance(validation_results["recommendations"], list)
        
        # Should have at least 5 associations
        assert validation_results["total_associations"] >= 5
        
        # Check association details structure
        for detail in validation_results["association_details"]:
            assert "source_id" in detail
            assert "name" in detail
            assert "connection_status" in detail
            assert "data_quality" in detail
            assert "supported_sectors" in detail
            assert "reliability_score" in detail
            
            assert detail["connection_status"] in ["ok", "failed"]
            assert detail["data_quality"] in ["good", "limited", "error"]
    
    @pytest.mark.asyncio
    async def test_coverage_gap_analysis(self):
        """Test analysis of sector coverage gaps."""
        if not ccnl_data_sources_manager.initialized:
            await ccnl_data_sources_manager.initialize()
        
        validation_results = await ccnl_data_sources_manager.validate_sector_associations_connectivity()
        coverage_gaps = validation_results["coverage_gaps"]
        
        assert isinstance(coverage_gaps, list)
        
        # Check that known covered sectors are not in gaps
        covered_sectors = ["metalmeccanici_industria", "chimici_farmaceutici", "alimentari_industria"]
        
        for covered_sector in covered_sectors:
            assert covered_sector not in coverage_gaps, f"Covered sector {covered_sector} should not be in gaps"
        
        # There should be some uncovered sectors (realistic expectation)
        # but not all sectors should be uncovered
        total_sectors = len(list(CCNLSector))
        assert len(coverage_gaps) < total_sectors, "Not all sectors should be uncovered"


class TestSectorAssociationsErrorHandling:
    """Test error handling in sector associations."""
    
    @pytest.mark.asyncio
    async def test_invalid_sector_search(self):
        """Test search with invalid or unsupported sectors."""
        source = FederchimicaDataSource()
        
        # Create query with no matching sectors
        query = DataSourceQuery(
            sectors=[CCNLSector.SANITA_PRIVATA, CCNLSector.SCUOLA_PRIVATA],  # Not supported
            max_results=5
        )
        
        # Should return empty results without error
        documents = await source.search_documents(query)
        assert documents == []
    
    @pytest.mark.asyncio
    async def test_network_timeout_handling(self):
        """Test handling of network timeouts and errors."""
        source = ASSINFORMDataSource()
        
        # This test is mainly to ensure no unhandled exceptions
        query = DataSourceQuery(
            sectors=[CCNLSector.ICT],
            max_results=5
        )
        
        try:
            documents = await source.search_documents(query)
            assert isinstance(documents, list)  # Should always return a list
        except Exception as e:
            # Any exceptions should be logged but not crash the application
            assert "timeout" in str(e).lower() or "connection" in str(e).lower()
    
    @pytest.mark.asyncio
    async def test_malformed_response_handling(self):
        """Test handling of malformed responses from sector associations."""
        source = ASSOMARMIDataSource()
        
        # Test search functionality - should handle any response gracefully
        query = DataSourceQuery(
            sectors=[CCNLSector.EDILIZIA_INDUSTRIA],
            max_results=3
        )
        
        documents = await source.search_documents(query)
        assert isinstance(documents, list)
        
        # All returned documents should have required fields
        for doc in documents:
            assert hasattr(doc, 'document_id')
            assert hasattr(doc, 'source_id')
            assert hasattr(doc, 'title')
            assert hasattr(doc, 'sector')
            assert hasattr(doc, 'publication_date')
            assert doc.source_id == "assomarmi"


class TestSectorAssociationsPerformance:
    """Test performance characteristics of sector associations."""
    
    @pytest.mark.asyncio
    async def test_concurrent_searches(self):
        """Test concurrent searches across multiple sector associations."""
        sources = await get_all_sector_associations()
        
        if len(sources) < 2:
            pytest.skip("Need at least 2 sector associations for concurrency test")
        
        # Create concurrent search tasks
        tasks = []
        for source in sources[:3]:  # Test first 3 sources
            if source.source_info.supported_sectors:
                query = DataSourceQuery(
                    sectors=source.source_info.supported_sectors[:1],
                    max_results=5
                )
                task = source.search_documents(query)
                tasks.append(task)
        
        # Run searches concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check that all tasks completed (may be empty results but should not crash)
        for result in results:
            if isinstance(result, Exception):
                # Log the exception but don't fail the test for network issues
                print(f"Search task failed: {result}")
            else:
                assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_search_response_time(self):
        """Test that searches complete within reasonable time."""
        import time
        
        source = FederalimentareDataSource()
        query = DataSourceQuery(
            sectors=[CCNLSector.ALIMENTARI_INDUSTRIA],
            max_results=5
        )
        
        start_time = time.time()
        documents = await source.search_documents(query)
        end_time = time.time()
        
        search_time = end_time - start_time
        
        # Search should complete within 30 seconds (generous for network calls)
        assert search_time < 30, f"Search took too long: {search_time:.2f} seconds"
        assert isinstance(documents, list)