"""
Test suite for Priority 3 CCNL data structures and functionality.

This module tests all 10 Priority 3 Specialized Industry sectors
to ensure complete data integrity and business logic correctness.
"""

import pytest
from decimal import Decimal
from datetime import date, datetime
from typing import List, Dict, Any

from app.models.ccnl_data import (
    CCNLAgreement,
    CCNLSector,
    WorkerCategory,
    JobLevel,
    SalaryTable,
    WorkingHours,
    OvertimeRules,
    LeaveEntitlement,
    NoticePerioD,
    SpecialAllowance,
    GeographicArea,
    LeaveType,
    AllowanceType,
    CompanySize
)
from app.data.ccnl_priority3 import (
    get_alimentari_industria_ccnl,
    get_panificazione_ccnl,
    get_agricoltura_ccnl,
    get_florovivaisti_ccnl,
    get_legno_arredamento_ccnl,
    get_carta_grafica_ccnl,
    get_energia_petrolio_ccnl,
    get_gas_acqua_ccnl,
    get_gomma_plastica_ccnl,
    get_vetro_ccnl,
    get_all_priority3_ccnl_data,
    validate_priority3_ccnl_data_completeness
)
from app.services.ccnl_service import ccnl_service


class TestPriority3CCNLDataStructures:
    """Test Priority 3 CCNL data structure completeness and integrity."""
    
    def test_all_priority3_sectors_defined(self):
        """Test that all 10 Priority 3 sectors are properly defined."""
        expected_sectors = [
            CCNLSector.ALIMENTARI_INDUSTRIA,
            CCNLSector.PANIFICAZIONE,
            CCNLSector.AGRICOLTURA,
            CCNLSector.FLOROVIVAISTI,
            CCNLSector.LEGNO_ARREDAMENTO,
            CCNLSector.CARTA_GRAFICA,
            CCNLSector.ENERGIA_PETROLIO,
            CCNLSector.GAS_ACQUA,
            CCNLSector.GOMMA_PLASTICA,
            CCNLSector.VETRO
        ]
        
        # Verify all sectors have priority level 3
        for sector in expected_sectors:
            assert sector.priority_level() == 3
        
        # Verify Italian names exist
        for sector in expected_sectors:
            italian_name = sector.italian_name()
            assert isinstance(italian_name, str)
            assert len(italian_name) > 0
            assert italian_name != sector.value
    
    def test_priority3_data_completeness(self):
        """Test that Priority 3 data validation passes."""
        validation_result = validate_priority3_ccnl_data_completeness()
        
        assert validation_result["status"] == "COMPLETE"
        assert validation_result["total_sectors"] == 10
        assert validation_result["sectors_complete"] == 10
        assert validation_result["completion_rate"] >= 95.0
        assert len(validation_result["missing_components"]) == 0
    
    def test_all_priority3_ccnl_data_loading(self):
        """Test that all Priority 3 CCNL agreements can be loaded."""
        all_agreements = get_all_priority3_ccnl_data()
        
        assert len(all_agreements) == 10
        
        # Verify each agreement is complete
        for agreement in all_agreements:
            assert isinstance(agreement, CCNLAgreement)
            assert agreement.sector is not None
            assert len(agreement.job_levels) > 0
            assert len(agreement.salary_tables) > 0
            assert agreement.working_hours is not None
            assert agreement.overtime_rules is not None
            assert len(agreement.leave_entitlements) > 0
            assert len(agreement.notice_periods) > 0
    
    @pytest.mark.asyncio
    async def test_ccnl_service_priority3_integration(self):
        """Test CCNL service integration with Priority 3 data."""
        # Test Priority 3 data loading
        priority3_data = await ccnl_service.get_all_priority3_ccnl()
        assert len(priority3_data) == 10
        
        # Test coverage stats
        coverage_stats = await ccnl_service.get_ccnl_coverage_stats()
        assert coverage_stats["priority3"]["sectors_covered"] == 10
        assert coverage_stats["priority3"]["agreements_count"] == 10
        assert coverage_stats["priority3"]["worker_coverage_percentage"] == 15
        
        # Test total coverage
        assert coverage_stats["total"]["sectors_covered"] == 30
        assert coverage_stats["total"]["agreements_count"] == 30
        assert coverage_stats["total"]["worker_coverage_percentage"] == 100


class TestAlimentariIndustriaCCNL:
    """Test Alimentari Industria sector CCNL data."""
    
    def test_alimentari_industria_ccnl_structure(self):
        """Test Alimentari Industria CCNL basic structure."""
        agreement = get_alimentari_industria_ccnl()
        
        assert agreement.sector == CCNLSector.ALIMENTARI_INDUSTRIA
        assert "Alimentari" in agreement.name
        assert len(agreement.job_levels) == 4  # A1-A4
        assert len(agreement.salary_tables) == 4
        assert agreement.working_hours.ordinary_weekly_hours == 40
        assert agreement.working_hours.shift_work_allowed == True
    
    def test_alimentari_industria_hygiene_allowances(self):
        """Test food industry specific hygiene allowances."""
        agreement = get_alimentari_industria_ccnl()
        
        # Should have hygiene and safety allowances
        allowance_types = [allowance.allowance_type for allowance in agreement.special_allowances]
        assert AllowanceType.INDENNITA_RISCHIO in allowance_types
        
        # Should have shift allowances for production
        salaries = [table.base_monthly_salary for table in agreement.salary_tables]
        assert all(salary >= Decimal('1400') for salary in salaries)


class TestPanificazioneCCNL:
    """Test Panificazione (Bakery) sector CCNL data."""
    
    def test_panificazione_structure(self):
        """Test bakery CCNL structure."""
        agreement = get_panificazione_ccnl()
        
        assert agreement.sector == CCNLSector.PANIFICAZIONE
        assert len(agreement.job_levels) == 4
        assert agreement.working_hours.ordinary_weekly_hours == 40
        assert agreement.working_hours.shift_work_allowed == True
    
    def test_panificazione_early_shift_conditions(self):
        """Test bakery early shift working conditions."""
        agreement = get_panificazione_ccnl()
        
        # Should have early shift allowances
        allowance_types = [allowance.allowance_type for allowance in agreement.special_allowances]
        assert AllowanceType.INDENNITA_TURNO in allowance_types
        
        # Should have night/early morning shift patterns
        assert agreement.working_hours.shift_work_allowed == True


class TestAgricolturaCCNL:
    """Test Agricoltura (Agriculture) sector CCNL data."""
    
    def test_agricoltura_structure(self):
        """Test agriculture CCNL structure."""
        agreement = get_agricoltura_ccnl()
        
        assert agreement.sector == CCNLSector.AGRICOLTURA
        assert len(agreement.job_levels) == 4
        assert agreement.working_hours.ordinary_weekly_hours == 40
    
    def test_agricoltura_seasonal_provisions(self):
        """Test agriculture seasonal work provisions."""
        agreement = get_agricoltura_ccnl()
        
        # Agriculture should have flexible working arrangements
        assert agreement.working_hours.flexible_hours_allowed == True
        
        # Should have outdoor work allowances
        allowance_types = [allowance.allowance_type for allowance in agreement.special_allowances]
        assert AllowanceType.INDENNITA_RISCHIO in allowance_types


class TestSpecializedIndustriesCCNL:
    """Test specialized industries CCNL data."""
    
    @pytest.mark.parametrize("sector_function,expected_sector", [
        (get_florovivaisti_ccnl, CCNLSector.FLOROVIVAISTI),
        (get_legno_arredamento_ccnl, CCNLSector.LEGNO_ARREDAMENTO),
        (get_carta_grafica_ccnl, CCNLSector.CARTA_GRAFICA),
        (get_energia_petrolio_ccnl, CCNLSector.ENERGIA_PETROLIO),
        (get_gas_acqua_ccnl, CCNLSector.GAS_ACQUA),
        (get_gomma_plastica_ccnl, CCNLSector.GOMMA_PLASTICA),
        (get_vetro_ccnl, CCNLSector.VETRO)
    ])
    def test_specialized_sector_basics(self, sector_function, expected_sector):
        """Test basic structure for specialized industry sectors."""
        agreement = sector_function()
        
        assert agreement.sector == expected_sector
        assert len(agreement.job_levels) >= 3
        assert len(agreement.salary_tables) >= 3
        assert agreement.working_hours.ordinary_weekly_hours <= 40
        assert len(agreement.leave_entitlements) >= 1
        assert len(agreement.notice_periods) >= 3
    
    def test_energia_petrolio_hazardous_conditions(self):
        """Test energy/petroleum sector hazardous conditions."""
        agreement = get_energia_petrolio_ccnl()
        
        # Should have hazardous conditions allowances
        allowance_types = [allowance.allowance_type for allowance in agreement.special_allowances]
        assert AllowanceType.INDENNITA_RISCHIO in allowance_types
        
        # Should have higher salary ranges due to risks
        salaries = [table.base_monthly_salary for table in agreement.salary_tables]
        max_salary = max(salaries)
        assert max_salary >= Decimal('2800')
    
    def test_vetro_industrial_conditions(self):
        """Test glass industry conditions."""
        agreement = get_vetro_ccnl()
        
        # Should have shift work capabilities for continuous production
        assert agreement.working_hours.shift_work_allowed == True
        
        # Should have hazardous conditions allowances
        allowance_types = [allowance.allowance_type for allowance in agreement.special_allowances]
        assert AllowanceType.INDENNITA_RISCHIO in allowance_types


class TestPriority3DataQuality:
    """Test data quality and consistency across Priority 3 sectors."""
    
    def test_salary_table_consistency(self):
        """Test salary tables are consistent and reasonable."""
        all_agreements = get_all_priority3_ccnl_data()
        
        for agreement in all_agreements:
            salaries = [table.base_monthly_salary for table in agreement.salary_tables]
            
            # Basic validation
            assert all(salary > Decimal('1200') for salary in salaries)  # Minimum wage check
            assert all(salary < Decimal('8000') for salary in salaries)  # Sanity check
            
            # Progression validation
            if len(salaries) > 1:
                salaries.sort()
                for i in range(1, len(salaries)):
                    assert salaries[i] > salaries[i-1]  # Should be progressive
    
    def test_working_hours_reasonableness(self):
        """Test working hours are within reasonable bounds."""
        all_agreements = get_all_priority3_ccnl_data()
        
        for agreement in all_agreements:
            wh = agreement.working_hours
            
            assert 38 <= wh.ordinary_weekly_hours <= 40  # Standard work week
            assert wh.maximum_weekly_hours <= 48  # EU working time directive
    
    def test_notice_periods_progression(self):
        """Test notice periods increase with experience."""
        all_agreements = get_all_priority3_ccnl_data()
        
        for agreement in all_agreements:
            # Group by worker category
            categories = {}
            for notice in agreement.notice_periods:
                if notice.worker_category not in categories:
                    categories[notice.worker_category] = []
                categories[notice.worker_category].append(notice)
            
            # Check progression within each category
            for category, notices in categories.items():
                notices.sort(key=lambda x: x.seniority_months_min)
                
                for i in range(1, len(notices)):
                    # Notice days should not decrease with more experience
                    assert notices[i].notice_days >= notices[i-1].notice_days
    
    def test_overtime_rates_reasonableness(self):
        """Test overtime rates are reasonable."""
        all_agreements = get_all_priority3_ccnl_data()
        
        for agreement in all_agreements:
            overtime = agreement.overtime_rules
            
            # Basic rate validation
            assert Decimal('1.15') <= overtime.daily_overtime_rate <= Decimal('1.50')
            assert Decimal('1.30') <= overtime.weekend_rate <= Decimal('2.00')
            assert Decimal('1.50') <= overtime.holiday_rate <= Decimal('2.50')
            
            # Progression validation
            assert overtime.daily_overtime_rate <= overtime.weekend_rate
            assert overtime.weekend_rate <= overtime.holiday_rate
    
    def test_leave_entitlements_minimums(self):
        """Test leave entitlements meet legal minimums."""
        all_agreements = get_all_priority3_ccnl_data()
        
        for agreement in all_agreements:
            for leave in agreement.leave_entitlements:
                if leave.leave_type == LeaveType.FERIE:
                    # Italy requires minimum 20 days annual leave
                    assert leave.base_annual_days >= 20
    
    def test_specialized_industry_characteristics(self):
        """Test that specialized industries have appropriate characteristics."""
        all_agreements = get_all_priority3_ccnl_data()
        
        # Most specialized industries should have risk allowances
        risk_sectors_count = 0
        for agreement in all_agreements:
            allowance_types = [allowance.allowance_type for allowance in agreement.special_allowances]
            if AllowanceType.INDENNITA_RISCHIO in allowance_types:
                risk_sectors_count += 1
        
        # At least 7 out of 10 specialized industries should have risk allowances
        assert risk_sectors_count >= 7
        
        # Most should have shift work capabilities
        shift_capable_count = 0
        for agreement in all_agreements:
            if agreement.working_hours.shift_work_allowed:
                shift_capable_count += 1
        
        # At least 6 out of 10 should support shift work
        assert shift_capable_count >= 6


class TestPriority3SectorSpecificFeatures:
    """Test sector-specific features for Priority 3."""
    
    def test_legno_arredamento_craftsmanship(self):
        """Test wood and furniture sector craftsmanship focus."""
        agreement = get_legno_arredamento_ccnl()
        
        # Should have different levels for craftsmanship skills
        level_names = [level.level_name for level in agreement.job_levels]
        assert any("Specializzato" in name or "Qualificato" in name for name in level_names)
    
    def test_carta_grafica_technical_skills(self):
        """Test paper and printing sector technical requirements."""
        agreement = get_carta_grafica_ccnl()
        
        # Should have technical skill requirements
        job_levels = agreement.job_levels
        assert any(level.required_qualifications for level in job_levels)
    
    def test_florovivaisti_seasonal_work(self):
        """Test floriculture sector seasonal characteristics."""
        agreement = get_florovivaisti_ccnl()
        
        # Should have flexible working arrangements for seasonal work
        assert agreement.working_hours.flexible_hours_allowed == True
        
        # Should have outdoor work considerations
        allowance_types = [allowance.allowance_type for allowance in agreement.special_allowances]
        # Outdoor work often qualifies for risk allowances
        assert AllowanceType.INDENNITA_RISCHIO in allowance_types or \
               any("clima" in str(allowance.conditions).lower() for allowance in agreement.special_allowances)