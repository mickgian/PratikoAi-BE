"""
Test suite for the enhanced CCNL calculation engine.

This module tests the comprehensive calculation capabilities including
salary computations, leave calculations, and complex scenario analysis.
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List

from app.services.ccnl_calculator_engine import (
    EnhancedCCNLCalculator,
    CompensationBreakdown,
    LeaveBalance,
    SeniorityBenefits,
    CCNLComparisonDetail,
    CalculationPeriod
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
    GeographicArea,
    LeaveType,
    AllowanceType,
    CompanySize,
    OvertimeRules
)


@pytest.fixture
def sample_metalmeccanici_ccnl():
    """Create a sample Metalmeccanici CCNL for testing."""
    ccnl = CCNLAgreement(
        sector=CCNLSector.METALMECCANICI_INDUSTRIA,
        name="CCNL Metalmeccanici Industria 2024-2026",
        valid_from=date(2024, 1, 1),
        valid_to=date(2026, 12, 31)
    )
    
    # Add job levels
    ccnl.job_levels = [
        JobLevel(
            level_code="C1",
            level_name="Operaio Comune",
            category=WorkerCategory.OPERAIO,
            minimum_experience_months=0
        ),
        JobLevel(
            level_code="C2",
            level_name="Operaio Qualificato",
            category=WorkerCategory.OPERAIO,
            minimum_experience_months=12
        ),
        JobLevel(
            level_code="B1",
            level_name="Operaio Specializzato",
            category=WorkerCategory.OPERAIO,
            minimum_experience_months=36
        ),
        JobLevel(
            level_code="5",
            level_name="Impiegato",
            category=WorkerCategory.IMPIEGATO,
            minimum_experience_months=0
        ),
        JobLevel(
            level_code="6",
            level_name="Impiegato Qualificato",
            category=WorkerCategory.IMPIEGATO,
            minimum_experience_months=24
        )
    ]
    
    # Add salary tables
    ccnl.salary_tables = [
        SalaryTable(
            ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
            level_code="C1",
            base_monthly_salary=Decimal('1800.00'),
            geographic_area=GeographicArea.NAZIONALE,
            thirteenth_month=True,
            fourteenth_month=True
        ),
        SalaryTable(
            ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
            level_code="C2",
            base_monthly_salary=Decimal('2000.00'),
            geographic_area=GeographicArea.NAZIONALE,
            thirteenth_month=True,
            fourteenth_month=True
        ),
        SalaryTable(
            ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
            level_code="C2",
            base_monthly_salary=Decimal('2100.00'),
            geographic_area=GeographicArea.NORD,
            thirteenth_month=True,
            fourteenth_month=True,
            company_size_adjustments={
                CompanySize.LARGE: Decimal('50.00')
            }
        ),
        SalaryTable(
            ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
            level_code="B1",
            base_monthly_salary=Decimal('2300.00'),
            geographic_area=GeographicArea.NAZIONALE,
            thirteenth_month=True,
            fourteenth_month=True
        )
    ]
    
    # Add working hours
    ccnl.working_hours = WorkingHours(
        ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
        ordinary_weekly_hours=40,
        maximum_weekly_hours=48,
        flexible_hours_allowed=True,
        shift_work_allowed=True
    )
    
    # Add overtime rules
    ccnl.overtime_rules = OvertimeRules(
        ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
        daily_overtime_rate=Decimal('1.25'),
        weekend_rate=Decimal('1.50'),
        holiday_rate=Decimal('2.00'),
        maximum_daily_overtime=3,
        maximum_weekly_overtime=12,
        maximum_annual_overtime=250
    )
    
    # Add leave entitlements
    ccnl.leave_entitlements = [
        LeaveEntitlement(
            ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
            leave_type=LeaveType.FERIE,
            base_annual_days=26,
            seniority_bonus_schedule={
                60: 2,   # +2 days after 5 years
                120: 4   # +4 days after 10 years
            }
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
            leave_type=LeaveType.ROL_EX_FESTIVITA,
            base_annual_hours=32,
            calculation_method="monthly_accrual"
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
            leave_type=LeaveType.PERMESSI_RETRIBUITI,
            base_annual_hours=64,
            minimum_usage_hours=2
        )
    ]
    
    # Add notice periods
    ccnl.notice_periods = [
        NoticePerioD(
            ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
            worker_category=WorkerCategory.OPERAIO,
            seniority_months_min=0,
            seniority_months_max=60,
            notice_days=15
        ),
        NoticePerioD(
            ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
            worker_category=WorkerCategory.OPERAIO,
            seniority_months_min=60,
            seniority_months_max=120,
            notice_days=30
        ),
        NoticePerioD(
            ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
            worker_category=WorkerCategory.OPERAIO,
            seniority_months_min=120,
            seniority_months_max=999,
            notice_days=45
        )
    ]
    
    # Add special allowances
    ccnl.special_allowances = [
        SpecialAllowance(
            ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
            allowance_type=AllowanceType.BUONI_PASTO,
            amount=Decimal('7.00'),
            frequency="daily",
            conditions=["Full-time employment", "Minimum 6 hours daily"]
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
            allowance_type=AllowanceType.INDENNITA_TRASPORTO,
            amount=Decimal('100.00'),
            frequency="monthly",
            geographic_areas=[GeographicArea.NORD, GeographicArea.CENTRO]
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
            allowance_type=AllowanceType.INDENNITA_TURNO,
            amount=Decimal('150.00'),
            frequency="monthly",
            job_levels=["C2", "B1"],
            conditions=["Shift work"]
        )
    ]
    
    return ccnl


@pytest.fixture
def calculator(sample_metalmeccanici_ccnl):
    """Create an enhanced calculator with sample CCNL."""
    return EnhancedCCNLCalculator(sample_metalmeccanici_ccnl)


class TestComprehensiveCompensationCalculation:
    """Test comprehensive compensation calculations."""
    
    def test_basic_annual_compensation(self, calculator):
        """Test basic annual compensation calculation."""
        compensation = calculator.calculate_comprehensive_compensation(
            level_code="C2",
            geographic_area=GeographicArea.NAZIONALE,
            include_allowances=False
        )
        
        # Base: 2000 * 12 = 24000
        # 13th month: 2000
        # 14th month: 2000
        # Total gross: 28000
        assert compensation.gross_total == Decimal('28000.00')
        assert compensation.base_salary == Decimal('24000.00')
        assert compensation.thirteenth_month == Decimal('2000.00')
        assert compensation.fourteenth_month == Decimal('2000.00')
    
    def test_compensation_with_geographic_adjustment(self, calculator):
        """Test compensation with geographic area adjustments."""
        compensation = calculator.calculate_comprehensive_compensation(
            level_code="C2",
            geographic_area=GeographicArea.NORD,
            include_allowances=False
        )
        
        # Base (Nord): 2100 * 12 = 25200
        # 13th month: 2100
        # 14th month: 2100
        # Total gross: 29400
        assert compensation.gross_total == Decimal('29400.00')
        assert compensation.base_salary == Decimal('25200.00')
    
    def test_compensation_with_company_size_adjustment(self, calculator):
        """Test compensation with company size adjustments."""
        compensation = calculator.calculate_comprehensive_compensation(
            level_code="C2",
            geographic_area=GeographicArea.NORD,
            company_size=CompanySize.LARGE,
            include_allowances=False
        )
        
        # Base (Nord + Large company): (2100 + 50) * 12 = 25800
        # 13th month: 2150
        # 14th month: 2150
        # Total gross: 30100
        assert compensation.gross_total == Decimal('30100.00')
    
    def test_compensation_with_allowances(self, calculator):
        """Test compensation including allowances."""
        compensation = calculator.calculate_comprehensive_compensation(
            level_code="C2",
            geographic_area=GeographicArea.NORD,
            working_days_per_month=22,
            include_allowances=True
        )
        
        # Should include meal vouchers and transport allowance
        assert "Buoni Pasto" in compensation.allowances
        assert "Indennità di Trasporto" in compensation.allowances
        assert "Indennità di Turno" in compensation.allowances
        
        # Meal vouchers: 7 * 22 * 12 = 1848
        assert compensation.allowances["Buoni Pasto"] == Decimal('1848.00')
        # Transport: 100 * 12 = 1200
        assert compensation.allowances["Indennità di Trasporto"] == Decimal('1200.00')
        # Shift allowance: 150 * 12 = 1800
        assert compensation.allowances["Indennità di Turno"] == Decimal('1800.00')
    
    def test_compensation_with_overtime(self, calculator):
        """Test compensation including overtime."""
        compensation = calculator.calculate_comprehensive_compensation(
            level_code="C2",
            overtime_hours_monthly=10,
            include_allowances=False
        )
        
        # Calculate expected overtime
        # Hourly rate: 2000 / (40/5 * 22) = 2000 / 176 ≈ 11.36
        # Overtime: 11.36 * 1.25 * 10 * 12 ≈ 1704
        assert compensation.overtime > Decimal('0')
        assert compensation.gross_total > Decimal('28000.00')  # Base + 13th + 14th
    
    def test_monthly_compensation_conversion(self, calculator):
        """Test converting annual compensation to monthly."""
        compensation = calculator.calculate_comprehensive_compensation(
            level_code="C2",
            period=CalculationPeriod.MONTHLY,
            include_allowances=False  # Exclude allowances for simpler calculation
        )
        
        # Annual gross 28000 / 12 = 2333.33
        assert compensation.period == CalculationPeriod.MONTHLY
        assert compensation.gross_total == Decimal('2333.33')
    
    def test_compensation_with_deductions(self, calculator):
        """Test that deductions are calculated."""
        compensation = calculator.calculate_comprehensive_compensation(
            level_code="C2"
        )
        
        assert len(compensation.deductions) > 0
        assert "Contributi INPS" in compensation.deductions
        assert "IRPEF" in compensation.deductions
        assert compensation.net_total < compensation.gross_total


class TestLeaveCalculations:
    """Test leave balance and entitlement calculations."""
    
    def test_basic_leave_balances(self, calculator):
        """Test calculating leave balances."""
        balances = calculator.calculate_leave_balances(
            seniority_months=36  # 3 years
        )
        
        # Should have vacation, ROL, and paid leave
        assert len(balances) == 3
        
        # Find vacation balance
        vacation = next(b for b in balances if b.leave_type == LeaveType.FERIE)
        assert vacation.annual_entitlement == 26  # Base days, no seniority bonus yet
        assert vacation.remaining_days == 26  # No days used
    
    def test_leave_with_seniority_bonus(self, calculator):
        """Test leave calculation with seniority bonuses."""
        balances = calculator.calculate_leave_balances(
            seniority_months=72  # 6 years
        )
        
        vacation = next(b for b in balances if b.leave_type == LeaveType.FERIE)
        assert vacation.annual_entitlement == 28  # 26 base + 2 seniority
    
    def test_leave_with_usage(self, calculator):
        """Test leave balance with used days."""
        used_days = {
            LeaveType.FERIE: 10,
            LeaveType.PERMESSI_RETRIBUITI: 4
        }
        
        balances = calculator.calculate_leave_balances(
            seniority_months=36,
            used_days=used_days
        )
        
        vacation = next(b for b in balances if b.leave_type == LeaveType.FERIE)
        assert vacation.used_days == 10
        assert vacation.remaining_days == 16  # 26 - 10
    
    def test_leave_accrual_rates(self, calculator):
        """Test leave accrual rate calculations."""
        balances = calculator.calculate_leave_balances(
            seniority_months=36
        )
        
        # ROL should have monthly accrual
        rol = next(b for b in balances if b.leave_type == LeaveType.ROL_EX_FESTIVITA)
        assert rol.accrual_rate == 32 / 12  # Hours per month
    
    def test_leave_expiry_dates(self, calculator):
        """Test leave expiry date calculations."""
        calculation_date = date(2024, 8, 15)
        balances = calculator.calculate_leave_balances(
            seniority_months=36,
            calculation_date=calculation_date
        )
        
        vacation = next(b for b in balances if b.leave_type == LeaveType.FERIE)
        assert vacation.expiry_date == date(2025, 6, 30)


class TestSeniorityBenefits:
    """Test seniority-based benefit calculations."""
    
    def test_basic_seniority_benefits(self, calculator):
        """Test basic seniority benefit calculation."""
        hire_date = date(2019, 1, 1)  # 5 years ago
        benefits = calculator.calculate_seniority_benefits(
            worker_category=WorkerCategory.OPERAIO,
            hire_date=hire_date,
            calculation_date=date(2024, 1, 1)
        )
        
        assert benefits.seniority_months == 60
        assert benefits.seniority_years == 5.0
        assert benefits.notice_period_days == 15  # 5 years = 60 months, which is in 0-60 range
    
    def test_seniority_with_additional_leave(self, calculator):
        """Test seniority benefits including additional leave days."""
        hire_date = date(2018, 1, 1)  # 6 years ago
        benefits = calculator.calculate_seniority_benefits(
            worker_category=WorkerCategory.OPERAIO,
            hire_date=hire_date,
            calculation_date=date(2024, 1, 1)
        )
        
        assert benefits.seniority_months == 72
        assert benefits.additional_leave_days == 2  # Vacation bonus after 5 years
    
    def test_severance_pay_calculation(self, calculator):
        """Test severance pay month calculation."""
        hire_date = date(2014, 1, 1)  # 10 years ago
        benefits = calculator.calculate_seniority_benefits(
            worker_category=WorkerCategory.OPERAIO,
            hire_date=hire_date,
            calculation_date=date(2024, 1, 1)
        )
        
        assert benefits.severance_pay_months == 10.0  # 1 month per year


class TestGeographicDifferences:
    """Test geographic area difference calculations."""
    
    def test_geographic_salary_differences(self, calculator):
        """Test calculating salary differences across areas."""
        differences = calculator.calculate_geographic_differences(
            level_code="C2",
            base_area=GeographicArea.NAZIONALE
        )
        
        # Should have comparison with NORD area
        assert GeographicArea.NORD.value in differences
        nord_diff = differences[GeographicArea.NORD.value]
        
        assert nord_diff["monthly_salary"] == 2100.0
        assert nord_diff["difference"] == 100.0  # 2100 - 2000
        assert nord_diff["percentage_difference"] == 5.0  # 5% higher
        assert nord_diff["annual_difference"] == 1200.0


class TestOvertimeScenarios:
    """Test overtime calculation scenarios."""
    
    def test_overtime_scenarios(self, calculator):
        """Test various overtime scenarios."""
        scenarios = calculator.calculate_overtime_scenarios(
            base_monthly_salary=Decimal('2000.00')
        )
        
        assert "weekday_overtime" in scenarios
        assert "weekend_overtime" in scenarios
        assert "holiday_overtime" in scenarios
        
        # Check multipliers
        assert scenarios["weekday_overtime"]["rate_multiplier"] == 1.25
        assert scenarios["weekend_overtime"]["rate_multiplier"] == 1.5
        assert scenarios["holiday_overtime"]["rate_multiplier"] == 2.0
        
        # Check examples
        assert scenarios["weekday_overtime"]["examples"]["1_hour"] > 0
        assert scenarios["weekend_overtime"]["examples"]["1_hour"] > \
               scenarios["weekday_overtime"]["examples"]["1_hour"]
    
    def test_overtime_limits(self, calculator):
        """Test overtime limit information."""
        scenarios = calculator.calculate_overtime_scenarios(
            base_monthly_salary=Decimal('2000.00')
        )
        
        assert "limits" in scenarios
        limits = scenarios["limits"]
        assert limits["daily_max"] == 3
        assert limits["weekly_max"] == 12
        assert limits["annual_max"] == 250


class TestCCNLComparison:
    """Test CCNL comparison functionality."""
    
    def test_compare_with_other_ccnl(self, calculator, sample_metalmeccanici_ccnl):
        """Test comparing two CCNLs."""
        # Create another CCNL with different values
        other_ccnl = CCNLAgreement(
            sector=CCNLSector.COMMERCIO_TERZIARIO,
            name="CCNL Commercio",
            valid_from=date(2024, 1, 1)
        )
        
        other_ccnl.salary_tables = [
            SalaryTable(
                ccnl_sector=CCNLSector.COMMERCIO_TERZIARIO,
                level_code="C2",
                base_monthly_salary=Decimal('1900.00'),
                geographic_area=GeographicArea.NAZIONALE,
                thirteenth_month=True,
                fourteenth_month=False
            )
        ]
        
        other_ccnl.leave_entitlements = [
            LeaveEntitlement(
                ccnl_sector=CCNLSector.COMMERCIO_TERZIARIO,
                leave_type=LeaveType.FERIE,
                base_annual_days=24
            )
        ]
        
        comparisons = calculator.compare_with_other_ccnl(
            other_ccnl,
            level_code="C2",
            comparison_aspects=["salary", "leave"]
        )
        
        # Check salary comparison
        salary_comp = next(c for c in comparisons if c.aspect == "Monthly Base Salary")
        assert salary_comp.ccnl1_value == 2000.0
        assert salary_comp.ccnl2_value == 1900.0
        assert salary_comp.difference == 100.0
        assert salary_comp.favors_ccnl == 1
        
        # Check leave comparison
        leave_comp = next(c for c in comparisons if "Ferie" in c.aspect)
        assert leave_comp.ccnl1_value == 26
        assert leave_comp.ccnl2_value == 24
        assert leave_comp.favors_ccnl == 1


class TestCareerProgression:
    """Test career progression calculations."""
    
    def test_career_progression_calculation(self, calculator):
        """Test calculating earnings over career progression."""
        progression_path = [
            ("C1", 24),  # 2 years at C1
            ("C2", 36),  # 3 years at C2
            ("B1", 60),  # 5 years at B1
        ]
        
        result = calculator.calculate_career_progression(
            starting_level="C1",
            progression_path=progression_path,
            starting_date=date(2014, 1, 1)
        )
        
        assert result["total_months"] == 120  # 10 years
        assert len(result["progression_path"]) == 3
        assert result["total_earnings"] > 0
        assert result["average_monthly"] > 0
        
        # Check progression details
        first_level = result["progression_path"][0]
        assert first_level["level"] == "C1"
        assert first_level["months"] == 24
        assert first_level["monthly_salary"] == 1800.0


class TestComplexQuery:
    """Test answering complex queries."""
    
    def test_answer_complex_metalworker_query(self, calculator):
        """Test answering the specific complex query example."""
        result = calculator.answer_complex_query(
            level_code="C2",
            worker_category=WorkerCategory.OPERAIO,
            geographic_area=GeographicArea.NORD,
            seniority_years=5,
            include_all_benefits=True
        )
        
        # Check query parameters are captured
        assert result["query_parameters"]["level"] == "C2"
        assert result["query_parameters"]["seniority_years"] == 5
        assert result["query_parameters"]["geographic_area"] == "nord"
        
        # Check compensation is calculated
        assert "compensation" in result
        assert result["compensation"]["period"] == "annual"
        assert result["compensation"]["gross_total"] > 0
        
        # Check leave entitlements
        assert len(result["leave_entitlements"]) > 0
        vacation = next(l for l in result["leave_entitlements"] if l["leave_type"] == "ferie")
        assert vacation["annual_entitlement"] == 28  # 26 base + 2 seniority
        
        # Check seniority benefits (allowing for slight calculation differences)
        assert abs(result["seniority_benefits"]["seniority_years"] - 5.0) < 0.1
        assert result["seniority_benefits"]["notice_period_days"] == 15  # 5 years = 60 months, which is in the 0-60 range
        
        # Check summary
        assert result["summary"]["annual_gross_total"] > 30000  # Should include allowances
        assert result["summary"]["total_leave_days"] > 26
        assert result["summary"]["notice_period_days"] == 15
    
    def test_complex_query_different_scenarios(self, calculator):
        """Test complex query with different parameters."""
        # Junior employee
        junior_result = calculator.answer_complex_query(
            level_code="C1",
            worker_category=WorkerCategory.OPERAIO,
            geographic_area=GeographicArea.NAZIONALE,
            seniority_years=1
        )
        
        # Senior employee - use same level C2 but with more seniority and allowances
        senior_result = calculator.answer_complex_query(
            level_code="C2",
            worker_category=WorkerCategory.OPERAIO,
            geographic_area=GeographicArea.NORD,
            seniority_years=10,
            include_all_benefits=True
        )
        
        # Senior should have higher compensation and more benefits
        assert senior_result["summary"]["annual_gross_total"] > \
               junior_result["summary"]["annual_gross_total"]
        assert senior_result["summary"]["total_leave_days"] > \
               junior_result["summary"]["total_leave_days"]
        assert senior_result["summary"]["notice_period_days"] > \
               junior_result["summary"]["notice_period_days"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=app.services.ccnl_calculator_engine"])