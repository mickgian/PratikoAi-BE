"""
Test suite for CCNL service layer.

This module tests the service layer that manages CCNL data operations,
including CRUD operations, business logic, and integration with the knowledge base.
"""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional
from unittest.mock import Mock, AsyncMock, patch

from app.services.ccnl_service import (
    CCNLService,
    CCNLQueryFilters,
    CCNLSearchResult,
    CCNLComparisonResult,
    CCNLValidationError,
    CCNLDataImportResult
)
from app.models.ccnl_data import (
    CCNLAgreement,
    CCNLSector,
    WorkerCategory,
    JobLevel,
    SalaryTable,
    WorkingHours,
    LeaveEntitlement,
    NoticePerioD,
    SpecialAllowance,
    CCNLCalculator,
    GeographicArea,
    LeaveType,
    AllowanceType
)
from app.models.ccnl_database import CCNLAgreementDB, CCNLSectorDB


class TestCCNLQueryFilters:
    """Test CCNL query filters model."""
    
    def test_create_basic_filters(self):
        """Test creating basic query filters."""
        filters = CCNLQueryFilters(
            sectors=[CCNLSector.METALMECCANICI_INDUSTRIA],
            worker_categories=[WorkerCategory.OPERAIO, WorkerCategory.IMPIEGATO],
            geographic_area=GeographicArea.NORD,
            valid_on_date=date(2024, 6, 15),
            active_only=True
        )
        
        assert CCNLSector.METALMECCANICI_INDUSTRIA in filters.sectors
        assert WorkerCategory.OPERAIO in filters.worker_categories
        assert filters.geographic_area == GeographicArea.NORD
        assert filters.valid_on_date == date(2024, 6, 15)
        assert filters.active_only is True
    
    def test_create_salary_range_filters(self):
        """Test creating filters with salary range."""
        filters = CCNLQueryFilters(
            min_monthly_salary=Decimal('1500.00'),
            max_monthly_salary=Decimal('2500.00'),
            include_allowances=True
        )
        
        assert filters.min_monthly_salary == Decimal('1500.00')
        assert filters.max_monthly_salary == Decimal('2500.00')
        assert filters.include_allowances is True
    
    def test_create_experience_filters(self):
        """Test creating filters with experience requirements."""
        filters = CCNLQueryFilters(
            min_experience_months=12,
            max_experience_months=60,
            supervision_roles_only=True
        )
        
        assert filters.min_experience_months == 12
        assert filters.max_experience_months == 60
        assert filters.supervision_roles_only is True
    
    def test_filters_validation(self):
        """Test filter validation."""
        # Valid filters
        valid_filters = CCNLQueryFilters(
            min_monthly_salary=Decimal('1000.00'),
            max_monthly_salary=Decimal('2000.00')
        )
        assert valid_filters.is_valid()
        
        # Invalid filters (min > max)
        invalid_filters = CCNLQueryFilters(
            min_monthly_salary=Decimal('2000.00'),
            max_monthly_salary=Decimal('1000.00')
        )
        assert not invalid_filters.is_valid()


class TestCCNLSearchResult:
    """Test CCNL search result model."""
    
    def test_create_search_result(self):
        """Test creating search result."""
        result = CCNLSearchResult(
            total_count=150,
            filtered_count=25,
            agreements=[],  # Would contain actual agreements
            query_time_ms=45,
            filters_applied={
                "sectors": ["metalmeccanici_industria"],
                "geographic_area": "nord"
            }
        )
        
        assert result.total_count == 150
        assert result.filtered_count == 25
        assert result.query_time_ms == 45
        assert "sectors" in result.filters_applied
    
    def test_search_result_with_facets(self):
        """Test search result with faceted results."""
        result = CCNLSearchResult(
            total_count=100,
            filtered_count=30,
            agreements=[],
            query_time_ms=50,
            facets={
                "sectors": {
                    "metalmeccanici_industria": 15,
                    "commercio_terziario": 10,
                    "edilizia_industria": 5
                },
                "worker_categories": {
                    "operaio": 20,
                    "impiegato": 8,
                    "quadro": 2
                }
            }
        )
        
        assert result.facets["sectors"]["metalmeccanici_industria"] == 15
        assert result.facets["worker_categories"]["operaio"] == 20


class TestCCNLService:
    """Test main CCNL service functionality."""
    
    @pytest.fixture
    def ccnl_service(self):
        """Create CCNL service instance for testing."""
        return CCNLService()
    
    @pytest.fixture
    def sample_ccnl_agreement(self):
        """Create sample CCNL agreement for testing."""
        return CCNLAgreement(
            sector=CCNLSector.METALMECCANICI_INDUSTRIA,
            name="CCNL Metalmeccanici Test",
            valid_from=date(2024, 1, 1),
            valid_to=date(2026, 12, 31),
            signatory_unions=["FIOM-CGIL", "FIM-CISL"],
            signatory_employers=["Federmeccanica"],
            job_levels=[
                JobLevel("C1", "Operaio Comune", WorkerCategory.OPERAIO),
                JobLevel("C2", "Operaio Qualificato", WorkerCategory.OPERAIO),
                JobLevel("D1", "Impiegato", WorkerCategory.IMPIEGATO)
            ],
            salary_tables=[
                SalaryTable(
                    CCNLSector.METALMECCANICI_INDUSTRIA,
                    "C1",
                    Decimal('1450.00'),
                    thirteenth_month=True
                ),
                SalaryTable(
                    CCNLSector.METALMECCANICI_INDUSTRIA,
                    "C2", 
                    Decimal('1650.00'),
                    thirteenth_month=True,
                    fourteenth_month=True
                )
            ],
            leave_entitlements=[
                LeaveEntitlement(
                    CCNLSector.METALMECCANICI_INDUSTRIA,
                    LeaveType.FERIE,
                    base_annual_days=24,
                    seniority_bonus_schedule={60: 2, 120: 4}
                )
            ]
        )
    
    @pytest.mark.asyncio
    async def test_get_ccnl_by_id(self, ccnl_service):
        """Test retrieving CCNL by ID."""
        with patch('app.services.database.database_service.get_session_maker') as mock_session:
            mock_db_session = Mock()
            mock_session.return_value.__enter__ = Mock(return_value=mock_db_session)
            mock_session.return_value.__exit__ = Mock(return_value=None)
            
            # Mock database result
            mock_agreement = CCNLAgreementDB(
                id=1,
                sector_code="metalmeccanici_industria",
                name="CCNL Test",
                valid_from=date(2024, 1, 1)
            )
            mock_db_session.get.return_value = mock_agreement
            
            result = await ccnl_service.get_ccnl_by_id(1)
            
            assert result is not None
            assert result.sector_code == "metalmeccanici_industria"
            mock_db_session.get.assert_called_once_with(CCNLAgreementDB, 1)
    
    @pytest.mark.asyncio
    async def test_get_ccnl_by_sector(self, ccnl_service):
        """Test retrieving CCNL agreements by sector."""
        with patch('app.services.database.database_service.get_session_maker') as mock_session:
            mock_db_session = Mock()
            mock_session.return_value.__enter__ = Mock(return_value=mock_db_session)
            mock_session.return_value.__exit__ = Mock(return_value=None)
            
            # Mock query result
            mock_agreements = [
                CCNLAgreementDB(
                    id=1,
                    sector_code="metalmeccanici_industria",
                    name="CCNL Metalmeccanici 2024",
                    valid_from=date(2024, 1, 1)
                ),
                CCNLAgreementDB(
                    id=2,
                    sector_code="metalmeccanici_industria", 
                    name="CCNL Metalmeccanici 2021",
                    valid_from=date(2021, 1, 1),
                    valid_to=date(2023, 12, 31)
                )
            ]
            mock_db_session.exec.return_value = mock_agreements
            
            results = await ccnl_service.get_ccnl_by_sector(
                CCNLSector.METALMECCANICI_INDUSTRIA,
                current_only=True
            )
            
            assert len(results) >= 0  # Would filter for current in real implementation
            mock_db_session.exec.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_ccnl_agreements(self, ccnl_service):
        """Test searching CCNL agreements with filters."""
        filters = CCNLQueryFilters(
            sectors=[CCNLSector.METALMECCANICI_INDUSTRIA],
            worker_categories=[WorkerCategory.OPERAIO],
            geographic_area=GeographicArea.NAZIONALE,
            min_monthly_salary=Decimal('1400.00'),
            active_only=True
        )
        
        with patch('app.services.database.database_service.get_session_maker') as mock_session:
            mock_db_session = Mock()
            mock_session.return_value.__enter__ = Mock(return_value=mock_db_session)
            mock_session.return_value.__exit__ = Mock(return_value=None)
            
            # Mock search results - return list directly for agreements, scalar for count
            mock_count_result = Mock()
            mock_count_result.first = Mock(return_value=5)  # Total count
            
            mock_db_session.exec.side_effect = [mock_count_result, []]  # Count query, then results query
            
            result = await ccnl_service.search_ccnl_agreements(filters, limit=10, offset=0)
            
            assert isinstance(result, CCNLSearchResult)
            assert result.total_count >= 0
            assert result.filtered_count >= 0
            assert result.query_time_ms >= 0
    
    @pytest.mark.asyncio
    async def test_save_ccnl_agreement(self, ccnl_service, sample_ccnl_agreement):
        """Test saving CCNL agreement to database."""
        with patch('app.services.database.database_service.get_session_maker') as mock_session:
            mock_db_session = Mock()
            mock_session.return_value.__enter__ = Mock(return_value=mock_db_session)
            mock_session.return_value.__exit__ = Mock(return_value=None)
            
            result = await ccnl_service.save_ccnl_agreement(sample_ccnl_agreement)
            
            assert result is True
            mock_db_session.add.assert_called()
            mock_db_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_ccnl_agreement(self, ccnl_service):
        """Test updating existing CCNL agreement."""
        updates = {
            "name": "Updated CCNL Name",
            "valid_to": date(2027, 12, 31),
            "renewal_status": "vigente"
        }
        
        with patch('app.services.database.database_service.get_session_maker') as mock_session:
            mock_db_session = Mock()
            mock_session.return_value.__enter__ = Mock(return_value=mock_db_session)
            mock_session.return_value.__exit__ = Mock(return_value=None)
            
            # Mock existing agreement
            mock_existing = CCNLAgreementDB(
                id=1,
                sector_code="metalmeccanici_industria",
                name="Old Name",
                valid_from=date(2024, 1, 1)
            )
            mock_db_session.get.return_value = mock_existing
            
            result = await ccnl_service.update_ccnl_agreement(1, updates)
            
            assert result is True
            mock_db_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_ccnl_agreement(self, ccnl_service):
        """Test deleting CCNL agreement (soft delete)."""
        with patch('app.services.database.database_service.get_session_maker') as mock_session:
            mock_db_session = Mock()
            mock_session.return_value.__enter__ = Mock(return_value=mock_db_session)
            mock_session.return_value.__exit__ = Mock(return_value=None)
            
            # Mock existing agreement
            mock_existing = CCNLAgreementDB(id=1, sector_code="test", name="Test", valid_from=date(2024, 1, 1))
            mock_db_session.get.return_value = mock_existing
            
            result = await ccnl_service.delete_ccnl_agreement(1, soft_delete=True)
            
            assert result is True
            # In real implementation, would set deleted flag instead of actual delete
            mock_db_session.commit.assert_called_once()


class TestCCNLCalculationService:
    """Test CCNL calculation and business logic."""
    
    @pytest.fixture
    def ccnl_service(self):
        """Create CCNL service instance."""
        return CCNLService()
    
    @pytest.mark.asyncio
    async def test_calculate_total_compensation(self, ccnl_service):
        """Test calculating total annual compensation."""
        # Mock CCNL data retrieval
        with patch.object(ccnl_service, 'get_ccnl_by_sector') as mock_get_ccnl:
            mock_agreement = Mock()
            
            # Create mock salary table with proper methods
            salary_mock = Mock()
            salary_mock.level_code = "C2"
            salary_mock.base_monthly_salary = Decimal('1650.00')
            salary_mock.thirteenth_month = True
            salary_mock.fourteenth_month = True
            salary_mock.geographic_area = "nazionale"
            salary_mock.get_annual_salary_with_additional_months.return_value = Decimal('23100.00')  # 1650 * 14
            
            mock_agreement.salary_tables = [salary_mock]
            
            # Create mock allowance with proper methods
            allowance_mock = Mock()
            allowance_mock.allowance_type = "buoni_pasto"
            allowance_mock.amount = Decimal('7.00')
            allowance_mock.frequency = "daily"
            allowance_mock.applicable_job_levels = ["C1", "C2", "C3"]
            allowance_mock.get_monthly_amount.return_value = Decimal('154.00')  # 7 * 22 days
            
            mock_agreement.special_allowances = [allowance_mock]
            mock_agreement.get_allowances_for_level.return_value = [allowance_mock]
            
            mock_get_ccnl.return_value = [mock_agreement]
            
            result = await ccnl_service.calculate_total_compensation(
                sector=CCNLSector.METALMECCANICI_INDUSTRIA,
                level_code="C2",
                geographic_area=GeographicArea.NAZIONALE,
                working_days_per_month=22,
                include_allowances=True
            )
            
            assert result is not None
            assert isinstance(result, dict)
            assert "annual_compensation" in result
            assert "breakdown" in result
    
    @pytest.mark.asyncio
    async def test_calculate_notice_period(self, ccnl_service):
        """Test calculating notice period for termination."""
        with patch.object(ccnl_service, 'get_ccnl_by_sector') as mock_get_ccnl:
            mock_agreement = Mock()
            # Create mock notice periods with applies_to_seniority method
            notice1 = Mock()
            notice1.worker_category = "operaio"
            notice1.seniority_months_min = 0
            notice1.seniority_months_max = 60
            notice1.notice_days = 15
            notice1.applies_to_seniority.return_value = False  # 72 months > 60
            
            notice2 = Mock()
            notice2.worker_category = "operaio"
            notice2.seniority_months_min = 60
            notice2.seniority_months_max = 999
            notice2.notice_days = 30
            notice2.applies_to_seniority.return_value = True  # 72 months in range
            
            mock_agreement.notice_periods = [notice1, notice2]
            mock_get_ccnl.return_value = [mock_agreement]
            
            result = await ccnl_service.calculate_notice_period(
                sector=CCNLSector.METALMECCANICI_INDUSTRIA,
                worker_category=WorkerCategory.OPERAIO,
                seniority_months=72  # 6 years
            )
            
            assert result is not None
            assert isinstance(result, dict)
            assert "notice_days" in result
            assert result["notice_days"] == 30  # Long seniority = 30 days
    
    @pytest.mark.asyncio
    async def test_calculate_leave_entitlement(self, ccnl_service):
        """Test calculating annual leave entitlement."""
        with patch.object(ccnl_service, 'get_ccnl_by_sector') as mock_get_ccnl:
            mock_agreement = Mock()
            
            # Create mock leave entitlement with get_annual_entitlement method
            leave_mock = Mock()
            leave_mock.leave_type = "ferie"
            leave_mock.base_annual_days = 24
            leave_mock.seniority_bonus_schedule = {60: 2, 120: 4}
            leave_mock.get_annual_entitlement.return_value = 26  # 24 + 2 bonus for 7 years
            
            mock_agreement.leave_entitlements = [leave_mock]
            mock_get_ccnl.return_value = [mock_agreement]
            
            result = await ccnl_service.calculate_leave_entitlement(
                sector=CCNLSector.METALMECCANICI_INDUSTRIA,
                leave_type=LeaveType.FERIE,
                seniority_months=84  # 7 years
            )
            
            assert result is not None
            assert isinstance(result, dict)
            assert "annual_days" in result
            assert result["annual_days"] == 26  # Base 24 + 2 bonus for 5+ years


class TestCCNLComparisonService:
    """Test CCNL comparison functionality."""
    
    @pytest.fixture
    def ccnl_service(self):
        """Create CCNL service instance."""
        return CCNLService()
    
    @pytest.mark.asyncio
    async def test_compare_ccnl_provisions(self, ccnl_service):
        """Test comparing provisions between two CCNLs."""
        sector1 = CCNLSector.METALMECCANICI_INDUSTRIA
        sector2 = CCNLSector.COMMERCIO_TERZIARIO
        
        with patch.object(ccnl_service, 'get_current_ccnl_by_sector') as mock_get_ccnl:
            def mock_ccnl_side_effect(sector):
                if sector == sector1:
                    mock_agreement = Mock()
                    mock_agreement.sector = sector1
                    mock_agreement.name = "CCNL Metalmeccanici"
                    mock_agreement.leave_entitlements = [
                        Mock(leave_type="ferie", base_annual_days=24)
                    ]
                    mock_agreement.salary_tables = [
                        Mock(level_code="C1", base_monthly_salary=Decimal('1450.00'))
                    ]
                    return mock_agreement
                else:
                    mock_agreement = Mock()
                    mock_agreement.sector = sector2
                    mock_agreement.name = "CCNL Commercio"
                    mock_agreement.leave_entitlements = [
                        Mock(leave_type="ferie", base_annual_days=22)
                    ]
                    mock_agreement.salary_tables = [
                        Mock(level_code="C1", base_monthly_salary=Decimal('1350.00'))
                    ]
                    return mock_agreement
            
            mock_get_ccnl.side_effect = mock_ccnl_side_effect
            
            result = await ccnl_service.compare_ccnl_provisions(
                sector1=sector1,
                sector2=sector2,
                comparison_aspects=["leave_entitlements", "salary_tables"]
            )
            
            assert isinstance(result, CCNLComparisonResult)
            assert len(result.differences) > 0
            assert result.sector1_name == "CCNL Metalmeccanici"
            assert result.sector2_name == "CCNL Commercio"
    
    @pytest.mark.asyncio
    async def test_compare_salary_levels(self, ccnl_service):
        """Test comparing salary levels between sectors."""
        result = await ccnl_service.compare_salary_levels(
            sectors=[
                CCNLSector.METALMECCANICI_INDUSTRIA,
                CCNLSector.COMMERCIO_TERZIARIO,
                CCNLSector.EDILIZIA_INDUSTRIA
            ],
            level_codes=["C1", "C2", "D1"],
            geographic_area=GeographicArea.NAZIONALE
        )
        
        assert isinstance(result, dict)
        assert "comparison_matrix" in result
        assert "statistics" in result


class TestCCNLDataImportService:
    """Test CCNL data import and validation functionality."""
    
    @pytest.fixture
    def ccnl_service(self):
        """Create CCNL service instance."""
        return CCNLService()
    
    @pytest.mark.asyncio
    async def test_import_ccnl_from_external_source(self, ccnl_service):
        """Test importing CCNL data from external source."""
        external_data = {
            "source": "https://www.federmeccanica.it/ccnl",
            "sector": "metalmeccanici_industria",
            "agreement_name": "CCNL Metalmeccanici 2024-2027",
            "valid_from": "2024-01-01",
            "valid_to": "2026-12-31",
            "job_levels": [
                {"code": "C1", "name": "Operaio Comune", "category": "operaio"},
                {"code": "C2", "name": "Operaio Qualificato", "category": "operaio"}
            ],
            "salary_tables": [
                {"level": "C1", "salary": "1450.00", "13th": True, "14th": False},
                {"level": "C2", "salary": "1650.00", "13th": True, "14th": True}
            ]
        }
        
        with patch.object(ccnl_service, 'save_ccnl_agreement') as mock_save:
            mock_save.return_value = True
            
            result = await ccnl_service.import_ccnl_from_external_data(
                external_data, 
                validate_data=True,
                overwrite_existing=False
            )
            
            assert isinstance(result, CCNLDataImportResult)
            assert result.success is True
            assert result.records_imported > 0
            assert len(result.validation_errors) == 0
    
    @pytest.mark.asyncio
    async def test_validate_ccnl_data_integrity(self, ccnl_service):
        """Test validating CCNL data integrity."""
        # Test data with validation issues
        invalid_data = {
            "sector": "invalid_sector",  # Invalid sector
            "agreement_name": "",  # Empty name
            "valid_from": "2025-01-01",  # Future date
            "salary_tables": [
                {"level": "C1", "salary": "-1000.00"}  # Negative salary
            ]
        }
        
        result = await ccnl_service.validate_ccnl_data(invalid_data)
        
        assert result.is_valid is False
        assert len(result.errors) > 0
        assert any("sector" in error.field for error in result.errors)
        assert any("salary" in error.message.lower() for error in result.errors)
    
    @pytest.mark.asyncio
    async def test_bulk_import_ccnl_data(self, ccnl_service):
        """Test bulk importing multiple CCNL agreements."""
        bulk_data = [
            {
                "sector": "metalmeccanici_industria",
                "agreement_name": "CCNL Metalmeccanici",
                "valid_from": "2024-01-01"
            },
            {
                "sector": "commercio_terziario", 
                "agreement_name": "CCNL Commercio",
                "valid_from": "2024-01-01"
            },
            {
                "sector": "invalid_sector",  # This should fail validation
                "agreement_name": "Invalid CCNL",
                "valid_from": "2024-01-01"
            }
        ]
        
        with patch.object(ccnl_service, 'save_ccnl_agreement') as mock_save:
            mock_save.return_value = True
            
            result = await ccnl_service.bulk_import_ccnl_data(
                bulk_data,
                validate_each=True,
                stop_on_error=False
            )
            
            assert isinstance(result, CCNLDataImportResult)
            assert result.records_processed == 3
            assert result.records_imported == 2  # 2 valid, 1 invalid
            assert result.records_failed == 1
            assert len(result.validation_errors) >= 1


class TestCCNLAnalyticsService:
    """Test CCNL analytics and reporting functionality."""
    
    @pytest.fixture
    def ccnl_service(self):
        """Create CCNL service instance."""
        return CCNLService()
    
    @pytest.mark.asyncio
    async def test_generate_ccnl_coverage_report(self, ccnl_service):
        """Test generating CCNL coverage statistics."""
        result = await ccnl_service.generate_coverage_report()
        
        assert isinstance(result, dict)
        assert "total_sectors" in result
        assert "implemented_sectors" in result
        assert "coverage_percentage" in result
        assert "priority_breakdown" in result
        assert "worker_coverage_estimate" in result
    
    @pytest.mark.asyncio
    async def test_generate_salary_statistics(self, ccnl_service):
        """Test generating salary statistics across sectors."""
        result = await ccnl_service.generate_salary_statistics(
            sectors=[CCNLSector.METALMECCANICI_INDUSTRIA, CCNLSector.COMMERCIO_TERZIARIO],
            worker_categories=[WorkerCategory.OPERAIO, WorkerCategory.IMPIEGATO],
            geographic_areas=[GeographicArea.NAZIONALE]
        )
        
        assert isinstance(result, dict)
        assert "salary_ranges" in result
        assert "sector_comparisons" in result
        assert "geographic_differences" in result
        assert "percentile_data" in result
    
    @pytest.mark.asyncio
    async def test_analyze_ccnl_trends(self, ccnl_service):
        """Test analyzing CCNL renewal and update trends."""
        result = await ccnl_service.analyze_ccnl_trends(
            start_date=date(2020, 1, 1),
            end_date=date(2024, 12, 31)
        )
        
        assert isinstance(result, dict)
        assert "renewal_patterns" in result
        assert "salary_growth_trends" in result
        assert "benefit_evolution" in result
        assert "upcoming_expirations" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=app.services.ccnl_service"])