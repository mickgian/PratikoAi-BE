"""
Test suite for Priority 2 CCNL data structures and functionality.

This module tests all 10 Priority 2 Service & Professional sectors
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
from app.data.ccnl_priority2 import (
    get_telecomunicazioni_ccnl,
    get_credito_assicurazioni_ccnl,
    get_studi_professionali_ccnl,
    get_servizi_pulizia_ccnl,
    get_vigilanza_privata_ccnl,
    get_ict_ccnl,
    get_agenzie_viaggio_ccnl,
    get_call_center_ccnl,
    get_cooperative_sociali_ccnl,
    get_servizi_educativi_ccnl,
    get_all_priority2_ccnl_data,
    validate_priority2_ccnl_data_completeness
)
from app.services.ccnl_service import ccnl_service


class TestPriority2CCNLDataStructures:
    """Test Priority 2 CCNL data structure completeness and integrity."""
    
    def test_all_priority2_sectors_defined(self):
        """Test that all 10 Priority 2 sectors are properly defined."""
        expected_sectors = [
            CCNLSector.TELECOMUNICAZIONI,
            CCNLSector.CREDITO_ASSICURAZIONI,
            CCNLSector.STUDI_PROFESSIONALI,
            CCNLSector.SERVIZI_PULIZIA,
            CCNLSector.VIGILANZA_PRIVATA,
            CCNLSector.ICT,
            CCNLSector.AGENZIE_VIAGGIO,
            CCNLSector.CALL_CENTER,
            CCNLSector.COOPERATIVE_SOCIALI,
            CCNLSector.SERVIZI_EDUCATIVI
        ]
        
        # Verify all sectors have priority level 2
        for sector in expected_sectors:
            assert sector.get_priority_level() == 2
        
        # Verify Italian names exist
        for sector in expected_sectors:
            italian_name = sector.italian_name()
            assert isinstance(italian_name, str)
            assert len(italian_name) > 0
            assert italian_name != sector.value
    
    def test_priority2_data_completeness(self):
        """Test that Priority 2 data validation passes."""
        validation_result = validate_priority2_ccnl_data_completeness()
        
        assert validation_result["status"] == "COMPLETE"
        assert validation_result["total_sectors"] == 10
        assert validation_result["sectors_complete"] == 10
        assert validation_result["completion_rate"] >= 95.0
        assert len(validation_result["missing_components"]) == 0
    
    def test_all_priority2_ccnl_data_loading(self):
        """Test that all Priority 2 CCNL agreements can be loaded."""
        all_agreements = get_all_priority2_ccnl_data()
        
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
    async def test_ccnl_service_priority2_integration(self):
        """Test CCNL service integration with Priority 2 data."""
        # Test Priority 2 data loading
        priority2_data = await ccnl_service.get_all_priority2_ccnl()
        assert len(priority2_data) == 10
        
        # Test coverage stats
        coverage_stats = await ccnl_service.get_ccnl_coverage_stats()
        assert coverage_stats["priority2"]["sectors_covered"] == 10
        assert coverage_stats["priority2"]["agreements_count"] == 10
        assert coverage_stats["priority2"]["worker_coverage_percentage"] == 25
        
        # Test total coverage
        assert coverage_stats["total"]["sectors_covered"] == 20
        assert coverage_stats["total"]["agreements_count"] == 20
        assert coverage_stats["total"]["worker_coverage_percentage"] == 85


class TestTelecomunicazioniCCNL:
    """Test Telecomunicazioni sector CCNL data."""
    
    def test_telecomunicazioni_ccnl_structure(self):
        """Test Telecomunicazioni CCNL basic structure."""
        agreement = get_telecomunicazioni_ccnl()
        
        assert agreement.sector == CCNLSector.TELECOMUNICAZIONI
        assert "Telecomunicazioni" in agreement.agreement_name
        assert len(agreement.job_levels) == 4  # 4A, 5A, 6A, 7A
        assert len(agreement.salary_tables) == 4
        assert agreement.working_hours.weekly_hours == 38
        assert agreement.working_hours.remote_work_allowed == True
        assert agreement.working_hours.shift_work == True
    
    def test_telecomunicazioni_salary_ranges(self):
        """Test Telecomunicazioni salary ranges are reasonable."""
        agreement = get_telecomunicazioni_ccnl()
        
        salaries = [table.monthly_gross_salary for table in agreement.salary_tables]
        salaries.sort()
        
        # Check progression and ranges
        assert salaries[0] >= Decimal('1600')  # Minimum reasonable
        assert salaries[-1] <= Decimal('3500')  # Maximum reasonable
        assert salaries[-1] > salaries[0] * Decimal('1.5')  # Good progression


class TestCreditoAssicurazioniCCNL:
    """Test Credito e Assicurazioni sector CCNL data."""
    
    def test_credito_assicurazioni_structure(self):
        """Test banking/insurance CCNL structure."""
        agreement = get_credito_assicurazioni_ccnl()
        
        assert agreement.sector == CCNLSector.CREDITO_ASSICURAZIONI
        assert len(agreement.job_levels) == 4
        assert len(agreement.salary_tables) == 4
        assert agreement.working_hours.weekly_hours == 37
        assert agreement.working_hours.remote_work_allowed == True
    
    def test_banking_sector_benefits(self):
        """Test that banking sector has appropriate benefits."""
        agreement = get_credito_assicurazioni_ccnl()
        
        # Banking should have good leave entitlements
        leave_days = [leave.days_per_year for leave in agreement.leave_entitlements]
        assert max(leave_days) >= 30  # Banking typically has good leave
        
        # Should have cash handling allowances
        allowance_types = [allowance.allowance_type for allowance in agreement.special_allowances]
        assert AllowanceType.CASH_HANDLING in allowance_types


class TestICTSectorCCNL:
    """Test ICT sector CCNL data."""
    
    def test_ict_sector_structure(self):
        """Test ICT sector CCNL structure."""
        agreement = get_ict_ccnl()
        
        assert agreement.sector == CCNLSector.ICT
        assert len(agreement.job_levels) == 4
        assert agreement.working_hours.remote_work_allowed == True
        assert agreement.working_hours.flexible_hours == True
    
    def test_ict_salary_levels(self):
        """Test ICT sector has competitive salaries."""
        agreement = get_ict_ccnl()
        
        salaries = [table.monthly_gross_salary for table in agreement.salary_tables]
        max_salary = max(salaries)
        
        # ICT should have high salary ranges
        assert max_salary >= Decimal('4000')
        
        # Should have technical skills allowances
        allowance_types = [allowance.allowance_type for allowance in agreement.special_allowances]
        assert AllowanceType.TECHNICAL_SKILLS in allowance_types


class TestServiceSectorsCCNL:
    """Test various service sectors CCNL data."""
    
    @pytest.mark.parametrize("sector_function,expected_sector", [
        (get_servizi_pulizia_ccnl, CCNLSector.SERVIZI_PULIZIA),
        (get_vigilanza_privata_ccnl, CCNLSector.VIGILANZA_PRIVATA),
        (get_call_center_ccnl, CCNLSector.CALL_CENTER),
        (get_agenzie_viaggio_ccnl, CCNLSector.AGENZIE_VIAGGIO)
    ])
    def test_service_sector_basics(self, sector_function, expected_sector):
        """Test basic structure for service sectors."""
        agreement = sector_function()
        
        assert agreement.sector == expected_sector
        assert len(agreement.job_levels) >= 3
        assert len(agreement.salary_tables) >= 3
        assert agreement.working_hours.weekly_hours <= 40
        assert len(agreement.leave_entitlements) >= 1
        assert len(agreement.notice_periods) >= 3
    
    def test_vigilanza_privata_specifics(self):
        """Test security sector specific requirements."""
        agreement = get_vigilanza_privata_ccnl()
        
        # Security should have hazardous conditions allowances
        allowance_types = [allowance.allowance_type for allowance in agreement.special_allowances]
        assert AllowanceType.HAZARDOUS_CONDITIONS in allowance_types
        
        # Should allow shift work
        assert agreement.working_hours.shift_work == True
    
    def test_pulizia_sector_conditions(self):
        """Test cleaning services sector conditions."""
        agreement = get_servizi_pulizia_ccnl()
        
        # Should have hazardous conditions allowances
        allowance_types = [allowance.allowance_type for allowance in agreement.special_allowances]
        assert AllowanceType.HAZARDOUS_CONDITIONS in allowance_types
        
        # Should have shift work capabilities
        assert agreement.working_hours.shift_work == True


class TestSocialServicesCCNL:
    """Test social services sectors CCNL data."""
    
    def test_cooperative_sociali_structure(self):
        """Test social cooperatives CCNL structure."""
        agreement = get_cooperative_sociali_ccnl()
        
        assert agreement.sector == CCNLSector.COOPERATIVE_SOCIALI
        assert len(agreement.job_levels) == 4  # A1, B1, C1, D1
        
        # Should have different leave entitlements by category
        operaio_leave = next(
            leave for leave in agreement.leave_entitlements 
            if leave.worker_category == WorkerCategory.OPERAIO
        )
        impiegato_leave = next(
            leave for leave in agreement.leave_entitlements 
            if leave.worker_category == WorkerCategory.IMPIEGATO
        )
        
        assert operaio_leave.days_per_year < impiegato_leave.days_per_year
    
    def test_servizi_educativi_structure(self):
        """Test educational services CCNL structure."""
        agreement = get_servizi_educativi_ccnl()
        
        assert agreement.sector == CCNLSector.SERVIZI_EDUCATIVI
        assert len(agreement.job_levels) == 4  # ES1-ES4
        
        # Educational sector should have good leave entitlements
        max_leave = max(leave.days_per_year for leave in agreement.leave_entitlements)
        assert max_leave >= 32  # Educational sector typically has good leave
        
        # Should have professional qualification allowances
        allowance_types = [allowance.allowance_type for allowance in agreement.special_allowances]
        assert AllowanceType.PROFESSIONAL_QUALIFICATION in allowance_types


class TestPriority2DataQuality:
    """Test data quality and consistency across Priority 2 sectors."""
    
    def test_salary_table_consistency(self):
        """Test salary tables are consistent and reasonable."""
        all_agreements = get_all_priority2_ccnl_data()
        
        for agreement in all_agreements:
            salaries = [table.monthly_gross_salary for table in agreement.salary_tables]
            
            # Basic validation
            assert all(salary > Decimal('1000') for salary in salaries)  # Minimum wage check
            assert all(salary < Decimal('10000') for salary in salaries)  # Sanity check
            
            # Progression validation
            if len(salaries) > 1:
                salaries.sort()
                for i in range(1, len(salaries)):
                    assert salaries[i] > salaries[i-1]  # Should be progressive
    
    def test_working_hours_reasonableness(self):
        """Test working hours are within reasonable bounds."""
        all_agreements = get_all_priority2_ccnl_data()
        
        for agreement in all_agreements:
            wh = agreement.working_hours
            
            assert 35 <= wh.weekly_hours <= 40  # Standard work week
            assert 7.0 <= wh.daily_hours <= 8.0  # Standard work day
            assert 15 <= wh.break_minutes <= 120  # Reasonable breaks
    
    def test_notice_periods_progression(self):
        """Test notice periods increase with experience."""
        all_agreements = get_all_priority2_ccnl_data()
        
        for agreement in all_agreements:
            # Group by worker category
            categories = {}
            for notice in agreement.notice_periods:
                if notice.worker_category not in categories:
                    categories[notice.worker_category] = []
                categories[notice.worker_category].append(notice)
            
            # Check progression within each category
            for category, notices in categories.items():
                notices.sort(key=lambda x: x.months_service_min)
                
                for i in range(1, len(notices)):
                    # Notice days should not decrease with more experience
                    assert notices[i].notice_days >= notices[i-1].notice_days
    
    def test_overtime_rates_reasonableness(self):
        """Test overtime rates are reasonable."""
        all_agreements = get_all_priority2_ccnl_data()
        
        for agreement in all_agreements:
            overtime = agreement.overtime_rules
            
            # Basic rate validation
            assert Decimal('1.15') <= overtime.overtime_rate_weekday <= Decimal('1.50')
            assert Decimal('1.30') <= overtime.overtime_rate_weekend <= Decimal('2.00')
            assert Decimal('1.50') <= overtime.overtime_rate_holiday <= Decimal('2.50')
            
            # Progression validation
            assert overtime.overtime_rate_weekday <= overtime.overtime_rate_weekend
            assert overtime.overtime_rate_weekend <= overtime.overtime_rate_holiday
    
    def test_leave_entitlements_minimums(self):
        """Test leave entitlements meet legal minimums."""
        all_agreements = get_all_priority2_ccnl_data()
        
        for agreement in all_agreements:
            for leave in agreement.leave_entitlements:
                if leave.leave_type == LeaveType.ANNUAL:
                    # Italy requires minimum 20 days annual leave
                    assert leave.days_per_year >= 20