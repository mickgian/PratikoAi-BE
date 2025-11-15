"""
Comprehensive tests for CCNL search functionality.

Tests natural language processing, faceted search, filtering,
and search result relevance.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import List

import pytest

from app.models.ccnl_data import AllowanceType, CCNLSector, CompanySize, GeographicArea, LeaveType, WorkerCategory
from app.models.ccnl_database import (
    CCNLAgreementDB,
    CCNLSectorDB,
    JobLevelDB,
    LeaveEntitlementDB,
    SalaryTableDB,
    WorkingHoursDB,
)
from app.services.ccnl_search_service import (
    CCNLSearchService,
    FacetCount,
    NaturalLanguageProcessor,
    SearchFilters,
    SearchResponse,
    SearchResult,
)
from app.services.database import database_service


class TestNaturalLanguageProcessor:
    """Test natural language query processing."""

    @pytest.fixture
    def nlp_processor(self):
        """Create NLP processor instance."""
        return NaturalLanguageProcessor()

    def test_parse_sector_keywords(self, nlp_processor):
        """Test sector detection from keywords."""
        # Test metalworking sector
        query = "operaio metalmeccanico milano"
        filters = nlp_processor.parse_query(query)
        assert CCNLSector.METALMECCANICI_INDUSTRIA in filters.sectors

        # Test commerce sector
        query = "commesso negozio commercio"
        filters = nlp_processor.parse_query(query)
        assert CCNLSector.COMMERCIO_TERZIARIO in filters.sectors

        # Test construction sector
        query = "muratore edilizia cantiere"
        filters = nlp_processor.parse_query(query)
        assert CCNLSector.EDILIZIA_INDUSTRIA in filters.sectors

    def test_parse_worker_categories(self, nlp_processor):
        """Test worker category detection."""
        # Test operaio
        query = "operaio specializzato"
        filters = nlp_processor.parse_query(query)
        assert WorkerCategory.OPERAIO in filters.worker_categories

        # Test impiegato
        query = "impiegato amministrativo ufficio"
        filters = nlp_processor.parse_query(query)
        assert WorkerCategory.IMPIEGATO in filters.worker_categories

        # Test quadro
        query = "quadro responsabile produzione"
        filters = nlp_processor.parse_query(query)
        assert WorkerCategory.QUADRO in filters.worker_categories

    def test_parse_geographic_areas(self, nlp_processor):
        """Test geographic area detection."""
        # Test north
        query = "metalmeccanico lombardia milano"
        filters = nlp_processor.parse_query(query)
        assert GeographicArea.NORD in filters.geographic_areas

        # Test center
        query = "impiegato roma lazio"
        filters = nlp_processor.parse_query(query)
        assert GeographicArea.CENTRO in filters.geographic_areas

        # Test south
        query = "operaio napoli campania"
        filters = nlp_processor.parse_query(query)
        assert GeographicArea.SUD in filters.geographic_areas

    def test_parse_salary_range(self, nlp_processor):
        """Test salary range extraction."""
        # Test with euro symbol
        query = "stipendio da 1500 a 2500 euro"
        filters = nlp_processor.parse_query(query)
        assert filters.min_salary == Decimal("1500")
        assert filters.max_salary == Decimal("2500")

        # Test without euro symbol
        query = "salario tra 2000 e 3000"
        filters = nlp_processor.parse_query(query)
        assert filters.min_salary == Decimal("2000")
        assert filters.max_salary == Decimal("3000")

    def test_parse_experience(self, nlp_processor):
        """Test experience extraction."""
        query = "operaio con 5 anni di esperienza"
        filters = nlp_processor.parse_query(query)
        assert filters.min_experience_months == 60  # 5 years * 12 months

        query = "impiegato 10 anni anzianità"
        filters = nlp_processor.parse_query(query)
        assert filters.min_experience_months == 120

    def test_parse_working_conditions(self, nlp_processor):
        """Test working condition requirements."""
        # Test flexible hours
        query = "impiegato orario flessibile"
        filters = nlp_processor.parse_query(query)
        assert filters.flexible_hours_required is True

        # Test part-time
        query = "commesso part-time"
        filters = nlp_processor.parse_query(query)
        assert filters.part_time_allowed is True

        # Test shift work
        query = "operaio turni notturni"
        filters = nlp_processor.parse_query(query)
        assert filters.shift_work_allowed is True

    def test_parse_vacation_requirements(self, nlp_processor):
        """Test vacation/leave requirement extraction."""
        query = "commercio con 30 giorni di ferie"
        filters = nlp_processor.parse_query(query)
        assert LeaveType.FERIE in filters.leave_types_required
        assert filters.min_vacation_days == 30

    def test_complex_query(self, nlp_processor):
        """Test complex natural language query."""
        query = "operaio metalmeccanico milano con 5 anni esperienza stipendio minimo 2000 euro orario flessibile"
        filters = nlp_processor.parse_query(query)

        assert CCNLSector.METALMECCANICI_INDUSTRIA in filters.sectors
        assert WorkerCategory.OPERAIO in filters.worker_categories
        assert GeographicArea.NORD in filters.geographic_areas
        assert filters.min_experience_months == 60
        assert filters.min_salary == Decimal("2000")
        assert filters.flexible_hours_required is True


class TestCCNLSearchService:
    """Test CCNL search service functionality."""

    @pytest.fixture
    def search_service(self):
        """Create search service instance."""
        return CCNLSearchService()

    @pytest.fixture
    def sample_data(self):
        """Create sample CCNL data for testing."""
        # This would normally be set up in a test database
        # For now, we'll use mock data
        pass

    @pytest.mark.asyncio
    async def test_basic_search(self, search_service):
        """Test basic search functionality."""
        filters = SearchFilters(sectors=[CCNLSector.METALMECCANICI_INDUSTRIA], active_only=True)

        response = await search_service.search(filters=filters)

        assert isinstance(response, SearchResponse)
        assert response.page == 1
        assert response.page_size == 20
        assert response.query_time_ms >= 0

    @pytest.mark.asyncio
    async def test_natural_language_search(self, search_service):
        """Test natural language search."""
        query = "metalmeccanico milano stipendio 2000 euro"

        response = await search_service.search(query=query)

        assert isinstance(response, SearchResponse)
        assert response.interpreted_query is not None
        assert len(response.suggested_queries) > 0

    @pytest.mark.asyncio
    async def test_faceted_search(self, search_service):
        """Test faceted search with counts."""
        response = await search_service.search(filters=SearchFilters(), include_facets=True)

        assert "sectors" in response.facets
        assert "worker_categories" in response.facets
        assert "geographic_areas" in response.facets

        # Check facet structure
        if response.facets["sectors"]:
            facet = response.facets["sectors"][0]
            assert isinstance(facet, FacetCount)
            assert facet.value is not None
            assert facet.count >= 0
            assert facet.display_name is not None

    @pytest.mark.asyncio
    async def test_salary_range_filter(self, search_service):
        """Test salary range filtering."""
        filters = SearchFilters(min_salary=Decimal("1500"), max_salary=Decimal("3000"))

        response = await search_service.search(filters=filters)

        # All results should be within salary range
        for result in response.results:
            if result.salary_range:
                assert result.salary_range[0] >= 1500 or result.salary_range[1] <= 3000

    @pytest.mark.asyncio
    async def test_geographic_filter(self, search_service):
        """Test geographic area filtering."""
        filters = SearchFilters(geographic_areas=[GeographicArea.NORD], regions=["lombardia", "piemonte"])

        response = await search_service.search(filters=filters)

        # Results should be from northern regions
        for result in response.results:
            assert any(area in ["nord", "lombardia", "piemonte"] for area in result.geographic_coverage)

    @pytest.mark.asyncio
    async def test_sorting(self, search_service):
        """Test different sorting options."""
        # Test salary ascending
        response = await search_service.search(filters=SearchFilters(), sort_by="salary_asc")

        if len(response.results) > 1:
            for i in range(1, len(response.results)):
                if response.results[i - 1].salary_range and response.results[i].salary_range:
                    assert response.results[i - 1].salary_range[0] <= response.results[i].salary_range[0]

    @pytest.mark.asyncio
    async def test_pagination(self, search_service):
        """Test search pagination."""
        # First page
        response1 = await search_service.search(filters=SearchFilters(), page=1, page_size=10)

        # Second page
        response2 = await search_service.search(filters=SearchFilters(), page=2, page_size=10)

        assert response1.page == 1
        assert response2.page == 2
        assert len(response1.results) <= 10
        assert len(response2.results) <= 10

        # Results should be different
        if response1.results and response2.results:
            assert response1.results[0].agreement_id != response2.results[0].agreement_id

    @pytest.mark.asyncio
    async def test_spelling_correction(self, search_service):
        """Test spelling correction in queries."""
        query = "comercio milano"  # Misspelled "commercio"

        response = await search_service.search(query=query)

        assert "comercio" in response.spelling_corrections
        assert response.spelling_corrections["comercio"] == "commercio"

    @pytest.mark.asyncio
    async def test_autocomplete(self, search_service):
        """Test autocomplete suggestions."""
        suggestions = await search_service.autocomplete("metal", limit=5)

        assert len(suggestions) <= 5
        assert any("metal" in s.lower() for s in suggestions)

    @pytest.mark.asyncio
    async def test_sector_comparison(self, search_service):
        """Test sector comparison functionality."""
        comparison = await search_service.compare_sectors(
            sector1=CCNLSector.METALMECCANICI_INDUSTRIA,
            sector2=CCNLSector.COMMERCIO_TERZIARIO,
            comparison_aspects=["salary", "vacation", "hours"],
        )

        assert "sector1" in comparison
        assert "sector2" in comparison
        assert "differences" in comparison

        if "salary" in comparison["differences"]:
            assert "sector1" in comparison["differences"]["salary"]
            assert "sector2" in comparison["differences"]["salary"]

    @pytest.mark.asyncio
    async def test_complex_filters(self, search_service):
        """Test search with multiple complex filters."""
        filters = SearchFilters(
            sectors=[CCNLSector.METALMECCANICI_INDUSTRIA, CCNLSector.COMMERCIO_TERZIARIO],
            worker_categories=[WorkerCategory.OPERAIO, WorkerCategory.IMPIEGATO],
            geographic_areas=[GeographicArea.NORD],
            min_salary=Decimal("1800"),
            max_salary=Decimal("3500"),
            min_experience_months=24,
            max_weekly_hours=40,
            flexible_hours_required=True,
            min_vacation_days=25,
            required_allowances=[AllowanceType.BUONI_PASTO],
            company_sizes=[CompanySize.MEDIUM, CompanySize.LARGE],
            active_only=True,
        )

        response = await search_service.search(filters=filters)

        assert isinstance(response, SearchResponse)
        # Results should match all filter criteria
        for result in response.results:
            assert result.sector in [CCNLSector.METALMECCANICI_INDUSTRIA, CCNLSector.COMMERCIO_TERZIARIO]

    @pytest.mark.asyncio
    async def test_search_statistics(self, search_service):
        """Test search result statistics."""
        response = await search_service.search(filters=SearchFilters(sectors=[CCNLSector.METALMECCANICI_INDUSTRIA]))

        if response.results:
            assert response.min_salary is not None
            assert response.max_salary is not None
            assert response.avg_salary is not None
            assert response.min_salary <= response.avg_salary <= response.max_salary


class TestSearchIntegration:
    """Integration tests for search functionality."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_end_to_end_search_flow(self):
        """Test complete search flow from query to results."""
        search_service = CCNLSearchService()

        # 1. Natural language query
        query = "operaio edile roma con 3 anni esperienza stipendio minimo 1800"

        # 2. Perform search
        response = await search_service.search(query=query)

        # 3. Verify response structure
        assert response.total_count >= 0
        assert response.interpreted_query is not None
        assert "Settore: Edilizia" in response.interpreted_query
        assert "Area geografica: Centro" in response.interpreted_query

        # 4. Check facets for refinement
        assert "sectors" in response.facets
        assert "worker_categories" in response.facets

        # 5. Refine search with facets
        if response.facets["sectors"]:
            refined_filters = SearchFilters(
                sectors=[CCNLSector(response.facets["sectors"][0].value)],
                worker_categories=[WorkerCategory.OPERAIO],
                min_salary=Decimal("1800"),
            )

            refined_response = await search_service.search(filters=refined_filters)
            assert refined_response.total_count <= response.total_count

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_search_performance(self):
        """Test search performance with various queries."""
        search_service = CCNLSearchService()

        queries = [
            "metalmeccanico milano",
            "commercio part-time nord italia",
            "edilizia operaio specializzato 5 anni esperienza",
            "turismo cameriere weekend roma",
            "trasporti autista patente c",
        ]

        for query in queries:
            response = await search_service.search(query=query)

            # Search should be fast
            assert response.query_time_ms < 1000  # Less than 1 second

            # Should return relevant results
            if response.results:
                assert response.results[0].relevance_score > 0
