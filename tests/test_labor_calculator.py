"""
TDD Tests for Labor Calculator.

This module tests Italian labor law calculations including TFR, salary conversions,
INPS/INAIL contributions, and employment contract analysis.
"""

from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Dict, List, Optional

import pytest

# These imports will fail initially - that's the TDD approach
from app.services.validators.labor_calculator import (
    ContractType,
    ContributionCalculation,
    EmploymentContract,
    EmploymentLevel,
    LaborCalculator,
    LaborResult,
    LeaveCalculation,
    MaternityBenefit,
    OvertimeCalculation,
    PayrollCalculation,
    Region,
    SalaryBreakdown,
    SeveranceCalculation,
    TFRCalculation,
    UnemploymentBenefit,
    WorkingTime,
)


class TestLaborCalculator:
    """Test suite for Labor Calculator using TDD methodology."""

    @pytest.fixture
    def calculator(self):
        """Create labor calculator instance for tests."""
        return LaborCalculator()

    @pytest.fixture
    def sample_employee_data(self):
        """Sample employee data for testing."""
        return {
            "gross_annual_salary": Decimal("30000"),
            "contract_type": ContractType.PERMANENT,
            "employment_level": EmploymentLevel.EMPLOYEE,
            "region": Region.LOMBARDY,
            "hire_date": date(2020, 1, 15),
            "birth_date": date(1985, 6, 10),
            "family_situation": {"spouse": True, "children": 2, "spouse_income": Decimal("15000")},
            "working_hours_per_week": Decimal("40"),
            "sector": "services",
        }

    # =========================================================================
    # TFR (Trattamento di Fine Rapporto) Tests
    # =========================================================================

    def test_tfr_calculation_basic_annual_accrual(self, calculator, sample_employee_data):
        """Test basic TFR annual accrual calculation."""
        # Arrange
        gross_salary = Decimal("30000")
        # TFR = Gross Annual Salary / 13.5
        expected_annual_tfr = gross_salary / Decimal("13.5")  # €2,222.22

        # Act
        tfr_result = calculator.calculate_tfr_annual_accrual(gross_annual_salary=gross_salary, year=2024)

        # Assert
        assert isinstance(tfr_result, TFRCalculation)
        assert abs(tfr_result.annual_accrual - expected_annual_tfr) < Decimal("0.01")
        assert tfr_result.calculation_method == "Annual Salary ÷ 13.5"
        assert tfr_result.formula == f"€{gross_salary:,.2f} ÷ 13.5 = €{expected_annual_tfr:.2f}"

    def test_tfr_calculation_with_revaluation(self, calculator):
        """Test TFR calculation with annual revaluation (75% inflation + 1.5%)."""
        # Arrange
        initial_tfr = Decimal("10000")  # TFR accumulated
        inflation_rate = Decimal("0.06")  # 6% inflation
        # Revaluation = 75% of inflation + 1.5% fixed = (0.75 × 6%) + 1.5% = 6%
        expected_revaluation_rate = (Decimal("0.75") * inflation_rate) + Decimal("0.015")
        expected_revalued_tfr = initial_tfr * (Decimal("1") + expected_revaluation_rate)

        # Act
        revaluation_result = calculator.calculate_tfr_revaluation(
            current_tfr=initial_tfr, inflation_rate=inflation_rate, year=2024
        )

        # Assert
        assert abs(revaluation_result.revaluation_rate - expected_revaluation_rate) < Decimal("0.001")
        assert abs(revaluation_result.revalued_amount - expected_revalued_tfr) < Decimal("0.01")
        assert revaluation_result.inflation_component == Decimal("0.045")  # 75% of 6%
        assert revaluation_result.fixed_component == Decimal("0.015")  # 1.5% fixed

    def test_tfr_calculation_total_service_years(self, calculator, sample_employee_data):
        """Test TFR calculation for complete service period."""
        # Arrange
        hire_date = date(2015, 3, 1)
        termination_date = date(2024, 8, 15)
        annual_salaries = [
            (2015, Decimal("25000")),  # Partial year
            (2016, Decimal("26000")),
            (2017, Decimal("27000")),
            (2018, Decimal("28000")),
            (2019, Decimal("29000")),
            (2020, Decimal("30000")),
            (2021, Decimal("31000")),
            (2022, Decimal("32000")),
            (2023, Decimal("33000")),
            (2024, Decimal("34000")),  # Partial year
        ]

        # Act
        total_tfr = calculator.calculate_total_tfr(
            hire_date=hire_date, termination_date=termination_date, annual_salaries=annual_salaries
        )

        # Assert
        assert isinstance(total_tfr, TFRCalculation)
        assert total_tfr.service_years > Decimal("9")  # More than 9 years
        assert total_tfr.service_years < Decimal("10")  # Less than 10 years
        assert total_tfr.total_accrued > Decimal("20000")  # Should be substantial
        assert total_tfr.includes_revaluation is True
        assert len(total_tfr.yearly_accruals) == 10  # 10 calendar years involved
        assert total_tfr.calculation_summary is not None

    def test_tfr_calculation_partial_year_proration(self, calculator):
        """Test TFR calculation with partial year employment."""
        # Arrange
        hire_date = date(2024, 9, 1)  # Started September 1st
        termination_date = date(2024, 12, 31)  # End of year
        annual_salary = Decimal("36000")

        # Expected: (36000 / 13.5) × (4/12) = €888.89
        expected_prorated_tfr = (annual_salary / Decimal("13.5")) * (Decimal("4") / Decimal("12"))

        # Act
        partial_tfr = calculator.calculate_tfr_partial_year(
            annual_salary=annual_salary, start_date=hire_date, end_date=termination_date
        )

        # Assert
        assert abs(partial_tfr.prorated_accrual - expected_prorated_tfr) < Decimal("0.01")
        assert partial_tfr.months_worked == Decimal("4")
        assert partial_tfr.proration_factor == Decimal("0.3333")  # 4/12

    # =========================================================================
    # Salary Conversion Tests (Gross ↔ Net)
    # =========================================================================

    def test_gross_to_net_salary_conversion_employee(self, calculator, sample_employee_data):
        """Test conversion from gross to net salary for employee."""
        # Arrange
        gross_annual = Decimal("30000")
        employee_data = sample_employee_data.copy()

        # Act
        net_calculation = calculator.calculate_gross_to_net(
            gross_annual_salary=gross_annual, employee_data=employee_data
        )

        # Assert
        assert isinstance(net_calculation, SalaryBreakdown)
        assert net_calculation.gross_annual == gross_annual
        assert net_calculation.net_annual < gross_annual  # Should be less after taxes/contributions

        # Should include all deductions
        assert net_calculation.irpef_tax > Decimal("0")
        assert net_calculation.inps_employee > Decimal("0")  # ~9.19%
        assert net_calculation.regional_tax > Decimal("0")
        assert net_calculation.municipal_tax > Decimal("0")

        # Net should be gross minus all deductions
        total_deductions = (
            net_calculation.irpef_tax
            + net_calculation.inps_employee
            + net_calculation.regional_tax
            + net_calculation.municipal_tax
        )
        assert abs(net_calculation.net_annual - (gross_annual - total_deductions)) < Decimal("1")

    def test_net_to_gross_salary_conversion(self, calculator, sample_employee_data):
        """Test conversion from net to gross salary (reverse calculation)."""
        # Arrange
        target_net_annual = Decimal("22000")
        employee_data = sample_employee_data.copy()

        # Act
        gross_calculation = calculator.calculate_net_to_gross(
            target_net_salary=target_net_annual, employee_data=employee_data
        )

        # Assert
        assert isinstance(gross_calculation, SalaryBreakdown)
        assert gross_calculation.net_annual == target_net_annual
        assert gross_calculation.gross_annual > target_net_annual  # Gross should be higher

        # Verify by converting back to net
        verification = calculator.calculate_gross_to_net(gross_calculation.gross_annual, employee_data)
        assert abs(verification.net_annual - target_net_annual) < Decimal("10")  # Within €10 tolerance

    def test_monthly_salary_breakdown_with_14_payments(self, calculator, sample_employee_data):
        """Test monthly salary breakdown with 14 payments (13th and 14th salary)."""
        # Arrange
        gross_annual = Decimal("42000")
        payments_per_year = 14  # Italian standard with 13th and 14th salary

        # Act
        monthly_breakdown = calculator.calculate_monthly_breakdown(
            gross_annual_salary=gross_annual, payments_per_year=payments_per_year, employee_data=sample_employee_data
        )

        # Assert
        expected_monthly_gross = gross_annual / Decimal("14")  # €3,000
        assert monthly_breakdown.monthly_gross == expected_monthly_gross
        assert monthly_breakdown.thirteenth_salary == expected_monthly_gross
        assert monthly_breakdown.fourteenth_salary == expected_monthly_gross
        assert monthly_breakdown.total_annual_payments == Decimal("14")
        assert monthly_breakdown.december_gross > monthly_breakdown.monthly_gross  # December includes 13th

    # =========================================================================
    # INPS/INAIL Contribution Tests
    # =========================================================================

    def test_inps_contributions_employee_employer_split(self, calculator, sample_employee_data):
        """Test INPS contributions calculation (employee and employer portions)."""
        # Arrange
        gross_salary = Decimal("30000")
        # Employee INPS: 9.19%, Employer INPS: ~23.81%
        expected_employee_inps = gross_salary * Decimal("0.0919")  # €2,757
        expected_employer_inps = gross_salary * Decimal("0.2381")  # €7,143

        # Act
        inps_calculation = calculator.calculate_inps_contributions(
            gross_annual_salary=gross_salary, contract_type=ContractType.PERMANENT, sector="services"
        )

        # Assert
        assert isinstance(inps_calculation, ContributionCalculation)
        assert abs(inps_calculation.employee_contribution - expected_employee_inps) < Decimal("10")
        assert abs(inps_calculation.employer_contribution - expected_employer_inps) < Decimal("50")
        assert inps_calculation.employee_rate == Decimal("9.19")
        assert inps_calculation.employer_rate >= Decimal("23")  # At least 23%
        assert inps_calculation.contribution_type == "INPS"

    def test_inail_contributions_calculation(self, calculator, sample_employee_data):
        """Test INAIL (workplace insurance) contributions calculation."""
        # Arrange
        gross_salary = Decimal("35000")
        sector = "manufacturing"  # Higher risk sector
        # INAIL rates vary by sector risk (0.5% - 3.5%), paid by employer only

        # Act
        inail_calculation = calculator.calculate_inail_contributions(
            gross_annual_salary=gross_salary, sector=sector, risk_level="medium"
        )

        # Assert
        assert isinstance(inail_calculation, ContributionCalculation)
        assert inail_calculation.employee_contribution == Decimal("0")  # INAIL paid only by employer
        assert inail_calculation.employer_contribution > Decimal("0")
        assert Decimal("0.005") <= inail_calculation.employer_rate <= Decimal("0.035")  # 0.5% - 3.5%
        assert inail_calculation.contribution_type == "INAIL"
        assert inail_calculation.risk_category in ["low", "medium", "high"]

    def test_total_contribution_burden_calculation(self, calculator, sample_employee_data):
        """Test total contribution burden (employee + employer) calculation."""
        # Arrange
        gross_salary = Decimal("40000")

        # Act
        total_contributions = calculator.calculate_total_contribution_burden(
            gross_annual_salary=gross_salary, employee_data=sample_employee_data
        )

        # Assert
        assert total_contributions.employee_total > Decimal("0")
        assert total_contributions.employer_total > total_contributions.employee_total  # Employer pays more
        assert total_contributions.grand_total == (
            total_contributions.employee_total + total_contributions.employer_total
        )

        # Should include all contribution types
        assert "INPS" in total_contributions.contribution_breakdown
        assert "INAIL" in total_contributions.contribution_breakdown

        # Total employer cost should be gross salary + employer contributions
        total_employer_cost = gross_salary + total_contributions.employer_total
        assert total_contributions.total_employment_cost == total_employer_cost

    # =========================================================================
    # Contract Type and Level Analysis
    # =========================================================================

    def test_executive_contract_analysis(self, calculator):
        """Test executive contract with different contribution rates."""
        # Arrange
        executive_data = {
            "gross_annual_salary": Decimal("120000"),  # High salary
            "contract_type": ContractType.PERMANENT,
            "employment_level": EmploymentLevel.EXECUTIVE,
            "region": Region.LAZIO,
            "benefits": ["company_car", "health_insurance", "stock_options"],
        }

        # Act
        executive_analysis = calculator.analyze_executive_contract(executive_data)

        # Assert
        assert executive_analysis.contribution_cap_applied is True  # INPS contributions capped
        assert executive_analysis.capped_salary > Decimal("0")  # Should show capping
        assert len(executive_analysis.additional_benefits) >= 3
        assert executive_analysis.total_compensation > executive_data["gross_annual_salary"]

        # Executive INPS rate may be different
        assert executive_analysis.executive_inps_rate != Decimal("9.19")  # Different from employee rate

    def test_temporary_contract_analysis(self, calculator, sample_employee_data):
        """Test temporary contract with specific regulations."""
        # Arrange
        temp_data = sample_employee_data.copy()
        temp_data["contract_type"] = ContractType.TEMPORARY
        temp_data["contract_end_date"] = date(2025, 12, 31)
        temp_data["original_contract_date"] = date(2024, 1, 1)

        # Act
        temp_analysis = calculator.analyze_temporary_contract(temp_data)

        # Assert
        assert temp_analysis.contract_duration_months > Decimal("0")
        assert temp_analysis.max_duration_compliant is not None  # Check legal limits
        assert temp_analysis.renewal_count >= 0
        assert temp_analysis.conversion_mandatory is not None  # Required conversion to permanent?

        # Temporary contracts may have additional contributions
        assert temp_analysis.temporary_contract_surcharge >= Decimal("0")

    def test_apprenticeship_contract_analysis(self, calculator):
        """Test apprenticeship contract with reduced contribution rates."""
        # Arrange
        apprentice_data = {
            "gross_annual_salary": Decimal("18000"),
            "contract_type": ContractType.APPRENTICESHIP,
            "age": 22,
            "apprenticeship_type": "professional",
            "training_hours_required": 120,
        }

        # Act
        apprentice_analysis = calculator.analyze_apprenticeship_contract(apprentice_data)

        # Assert
        assert apprentice_analysis.reduced_contributions is True
        assert apprentice_analysis.employer_inps_rate < Decimal("23")  # Reduced rate for apprentices
        assert apprentice_analysis.training_obligation_hours == 120
        assert apprentice_analysis.apprenticeship_duration_months > Decimal("0")
        assert apprentice_analysis.age_eligible is True  # Must be under 30 for apprenticeship

    # =========================================================================
    # Leave and Absence Calculations
    # =========================================================================

    def test_annual_leave_entitlement_calculation(self, calculator, sample_employee_data):
        """Test annual leave (ferie) entitlement calculation."""
        # Arrange
        employment_start = date(2020, 3, 15)
        calculation_date = date(2024, 12, 31)

        # Act
        leave_calculation = calculator.calculate_annual_leave_entitlement(
            employment_start_date=employment_start,
            calculation_date=calculation_date,
            contract_type=ContractType.PERMANENT,
            sector="services",
        )

        # Assert
        assert isinstance(leave_calculation, LeaveCalculation)
        # Standard: 4 weeks (20 working days) per year for services
        assert leave_calculation.annual_entitlement_days == Decimal("20")
        assert leave_calculation.accrued_leave_days > Decimal("0")
        assert leave_calculation.years_of_service >= Decimal("4")  # More than 4 years

        # Should calculate monetary value
        assert leave_calculation.monetary_value_per_day > Decimal("0")
        assert leave_calculation.total_accrued_value > Decimal("0")

    def test_sick_leave_calculation_with_waiting_period(self, calculator, sample_employee_data):
        """Test sick leave calculation with waiting period (carenza)."""
        # Arrange
        sick_leave_data = {
            "sick_days": 15,
            "gross_daily_salary": Decimal("120"),
            "start_date": date(2024, 6, 1),
            "medical_certificate": True,
        }

        # Act
        sick_leave = calculator.calculate_sick_leave_payment(**sick_leave_data, employee_data=sample_employee_data)

        # Assert
        # First 3 days (carenza) usually not paid by employer
        # Days 4-20: 50% of salary
        # Days 21+: 66.66% of salary
        assert sick_leave.waiting_period_days == 3
        assert sick_leave.unpaid_days == 3
        assert sick_leave.paid_days == 12  # 15 - 3

        # Payment should be at reduced rate
        assert sick_leave.daily_payment_rate < Decimal("1.0")  # Less than 100%
        assert sick_leave.inps_portion > Decimal("0")  # INPS covers part
        assert sick_leave.employer_portion >= Decimal("0")  # Employer may cover part

    def test_maternity_leave_calculation(self, calculator, sample_employee_data):
        """Test maternity leave calculation (congedo di maternità)."""
        # Arrange
        maternity_data = {
            "expected_delivery_date": date(2024, 8, 15),
            "leave_start_date": date(2024, 6, 16),  # 2 months before
            "leave_end_date": date(2024, 11, 13),  # 3 months after
            "gross_monthly_salary": Decimal("2500"),
        }

        # Act
        maternity_leave = calculator.calculate_maternity_leave(**maternity_data, employee_data=sample_employee_data)

        # Assert
        assert isinstance(maternity_leave, MaternityBenefit)
        assert maternity_leave.total_leave_days == 150  # 5 months = ~150 days
        assert maternity_leave.payment_rate == Decimal("0.8")  # 80% of salary
        assert maternity_leave.inps_payment > Decimal("0")
        assert maternity_leave.job_protection is True
        assert maternity_leave.return_guarantee is True

    # =========================================================================
    # Severance and Termination Tests
    # =========================================================================

    def test_severance_calculation_voluntary_resignation(self, calculator, sample_employee_data):
        """Test severance calculation for voluntary resignation."""
        # Arrange
        termination_data = {
            "termination_type": "voluntary_resignation",
            "notice_period_given": 30,  # 30 days notice
            "hire_date": date(2018, 1, 15),
            "termination_date": date(2024, 8, 30),
            "final_salary": Decimal("35000"),
            "unused_vacation_days": 10,
        }

        # Act
        severance = calculator.calculate_severance_payment(**termination_data, employee_data=sample_employee_data)

        # Assert
        assert isinstance(severance, SeveranceCalculation)
        assert severance.tfr_payment > Decimal("0")  # TFR always due
        assert severance.notice_payment == Decimal("0")  # Proper notice given
        assert severance.vacation_payout > Decimal("0")  # Unused vacation
        assert severance.severance_indemnity == Decimal("0")  # No indemnity for resignation

        # Total should be TFR + vacation + any other owed amounts
        expected_total = severance.tfr_payment + severance.vacation_payout
        assert abs(severance.total_severance - expected_total) < Decimal("1")

    def test_severance_calculation_dismissal_for_cause(self, calculator, sample_employee_data):
        """Test severance calculation for dismissal with just cause."""
        # Arrange
        dismissal_data = {
            "termination_type": "dismissal_with_cause",
            "hire_date": date(2020, 6, 1),
            "termination_date": date(2024, 9, 15),
            "disciplinary_action": True,
            "gross_monthly_salary": Decimal("2800"),
        }

        # Act
        severance = calculator.calculate_severance_payment(**dismissal_data, employee_data=sample_employee_data)

        # Assert
        # Dismissal with cause: only TFR due, no notice or indemnity
        assert severance.tfr_payment > Decimal("0")  # TFR always due
        assert severance.notice_payment == Decimal("0")  # No notice for cause
        assert severance.severance_indemnity == Decimal("0")  # No indemnity for cause
        assert severance.disciplinary_reduction == Decimal("0")  # No TFR reduction for cause

    def test_severance_calculation_economic_dismissal(self, calculator, sample_employee_data):
        """Test severance calculation for economic dismissal (redundancy)."""
        # Arrange
        economic_dismissal_data = {
            "termination_type": "economic_dismissal",
            "hire_date": date(2015, 4, 1),
            "termination_date": date(2024, 10, 31),
            "company_size": "large",  # >15 employees
            "notice_period_required": 60,  # 60 days for long service
            "collective_dismissal": False,
        }

        # Act
        severance = calculator.calculate_severance_payment(
            **economic_dismissal_data, employee_data=sample_employee_data
        )

        # Assert
        # Economic dismissal: TFR + notice + possible indemnity
        assert severance.tfr_payment > Decimal("0")
        assert severance.notice_payment > Decimal("0")  # In lieu of notice
        assert severance.severance_indemnity >= Decimal("0")  # May have indemnity
        assert severance.unemployment_benefit_eligible is True

        # Should include calculation details
        assert severance.service_years > Decimal("9")  # More than 9 years service
        assert len(severance.calculation_breakdown) >= 3  # Multiple components

    # =========================================================================
    # Working Time and Overtime Tests
    # =========================================================================

    def test_overtime_calculation_standard_rates(self, calculator, sample_employee_data):
        """Test overtime calculation with standard Italian rates."""
        # Arrange
        overtime_data = {
            "regular_hours_per_week": Decimal("40"),
            "actual_hours_worked": Decimal("48"),  # 8 hours overtime
            "hourly_rate": Decimal("15.50"),
            "overtime_period": "weekly",
        }

        # Act
        overtime = calculator.calculate_overtime_payment(**overtime_data, employee_data=sample_employee_data)

        # Assert
        assert isinstance(overtime, OvertimeCalculation)
        assert overtime.overtime_hours == Decimal("8")
        assert overtime.regular_pay == Decimal("620.00")  # 40 × €15.50

        # Standard overtime rates: +25% for first 2 hours, +50% after that
        first_2_hours_rate = Decimal("19.375")  # €15.50 × 1.25
        additional_6_hours_rate = Decimal("23.25")  # €15.50 × 1.50

        expected_overtime_pay = (Decimal("2") * first_2_hours_rate) + (Decimal("6") * additional_6_hours_rate)
        assert abs(overtime.overtime_pay - expected_overtime_pay) < Decimal("1")
        assert overtime.total_pay == overtime.regular_pay + overtime.overtime_pay

    def test_night_shift_premium_calculation(self, calculator, sample_employee_data):
        """Test night shift premium calculation."""
        # Arrange
        night_shift_data = {
            "night_hours": Decimal("8"),  # Full night shift
            "regular_hourly_rate": Decimal("16.00"),
            "shift_start_time": "22:00",
            "shift_end_time": "06:00",
        }

        # Act
        night_premium = calculator.calculate_night_shift_premium(
            **night_shift_data, employee_data=sample_employee_data
        )

        # Assert
        # Night premium typically 20-30% additional
        assert night_premium.premium_rate >= Decimal("0.20")  # At least 20%
        assert night_premium.premium_rate <= Decimal("0.30")  # At most 30%
        assert night_premium.premium_pay > Decimal("0")
        assert night_premium.total_night_pay > night_premium.base_pay

        # Should identify qualifying night hours (typically 22:00-06:00)
        assert night_premium.qualifying_night_hours == Decimal("8")

    def test_holiday_work_compensation(self, calculator, sample_employee_data):
        """Test holiday work compensation calculation."""
        # Arrange
        holiday_data = {
            "holiday_date": date(2024, 12, 25),  # Christmas
            "hours_worked": Decimal("8"),
            "hourly_rate": Decimal("18.00"),
            "holiday_type": "national_religious",
        }

        # Act
        holiday_pay = calculator.calculate_holiday_work_compensation(
            **holiday_data, employee_data=sample_employee_data
        )

        # Assert
        # Holiday work typically pays double time (100% premium)
        assert holiday_pay.holiday_premium_rate == Decimal("1.00")  # 100% premium
        expected_total = Decimal("8") * Decimal("18.00") * Decimal("2")  # Double pay
        assert holiday_pay.total_holiday_pay == expected_total
        assert holiday_pay.base_pay == Decimal("144.00")  # 8 × €18
        assert holiday_pay.premium_pay == Decimal("144.00")  # Equal premium

    # =========================================================================
    # Performance and Edge Case Tests
    # =========================================================================

    def test_labor_calculation_performance_complex_payroll(self, calculator):
        """Test performance with complex payroll calculation."""
        import time

        # Arrange - Complex employee with multiple variables
        complex_employee = {
            "gross_annual_salary": Decimal("55000"),
            "contract_type": ContractType.PERMANENT,
            "employment_level": EmploymentLevel.MANAGER,
            "overtime_hours": Decimal("120"),  # Significant overtime
            "night_hours": Decimal("40"),
            "holiday_hours": Decimal("16"),
            "sick_days": 25,
            "vacation_days": 22,
            "benefits": ["company_car", "meal_vouchers", "health_insurance"],
            "family": {"spouse": True, "children": 3},
        }

        # Act
        start_time = time.time()
        comprehensive_calculation = calculator.calculate_comprehensive_payroll(complex_employee)
        end_time = time.time()

        # Assert
        calculation_time = end_time - start_time
        assert calculation_time < 3.0  # Should complete in under 3 seconds
        assert comprehensive_calculation.total_gross > Decimal("55000")  # Including overtime
        assert len(comprehensive_calculation.calculation_components) >= 8

    def test_labor_calculation_edge_cases(self, calculator):
        """Test labor calculations with edge cases."""
        # Arrange - Edge cases
        edge_cases = [
            {"gross_salary": Decimal("0"), "expected_error": "Salary cannot be zero"},
            {"gross_salary": Decimal("-1000"), "expected_error": "Salary cannot be negative"},
            {"service_years": Decimal("0"), "hours_per_week": Decimal("168")},  # More than possible
        ]

        # Act & Assert
        for case in edge_cases:
            if "expected_error" in case:
                with pytest.raises(ValueError, match=case["expected_error"]):
                    calculator.calculate_gross_to_net(case["gross_salary"], {})
            else:
                # Should handle gracefully without errors
                try:
                    result = calculator.validate_working_time(case)
                    assert result.warnings is not None
                except ValueError:
                    pass  # Expected for invalid hours

    def test_labor_regulation_compliance_check(self, calculator, sample_employee_data):
        """Test compliance check with Italian labor regulations."""
        # Act
        compliance_check = calculator.check_labor_regulation_compliance(sample_employee_data)

        # Assert
        assert compliance_check.overall_compliant is not None
        assert len(compliance_check.compliance_items) >= 10

        # Should check key areas
        compliance_areas = [item.area for item in compliance_check.compliance_items]
        assert "working_time" in compliance_areas
        assert "minimum_wage" in compliance_areas
        assert "contributions" in compliance_areas
        assert "leave_entitlement" in compliance_areas
        assert "contract_terms" in compliance_areas

        # Should provide recommendations if non-compliant
        if not compliance_check.overall_compliant:
            assert len(compliance_check.recommendations) > 0
