"""
Comprehensive test suite for Italian Tax Calculator using Test-Driven Development.

This test suite covers all aspects of the Italian tax system including:
- IRPEF (Personal Income Tax) with progressive brackets
- Regional and municipal tax variations
- INPS social security contributions
- VAT calculations
- Corporate taxes (IRES and IRAP)
- Property taxes (IMU)
- Capital gains taxes
- Tax deductions and optimizations
- Self-employed and freelancer taxes

Following TDD principles: write tests first, then implement functionality.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List
from uuid import uuid4

import pytest

from app.services.italian_tax_calculator import (
    CapitalGainsTaxCalculator,
    CorporateTaxCalculator,
    FreelancerTaxCalculator,
    InpsCalculator,
    InvalidIncomeError,
    InvalidLocationError,
    InvalidTaxTypeError,
    IrpefCalculator,
    ItalianTaxCalculator,
    PropertyTaxCalculator,
    TaxCalculationError,
    TaxDeductionEngine,
    TaxOptimizationEngine,
    VatCalculator,
)


class TestIrpefCalculator:
    """Test suite for IRPEF (Personal Income Tax) calculations with 2024 brackets."""

    @pytest.fixture
    def irpef_calculator(self):
        return IrpefCalculator()

    def test_irpef_calculation_low_income(self, irpef_calculator):
        """Test IRPEF calculation for income below 28,000 euros (23% bracket)."""
        income = Decimal("25000")
        result = irpef_calculator.calculate_irpef(income)

        expected_tax = Decimal("25000") * Decimal("0.23")
        assert result["gross_tax"] == expected_tax
        assert result["marginal_rate"] == Decimal("23.00")
        assert "first_bracket" in result["brackets_used"]
        assert result["income"] == income

    def test_irpef_calculation_medium_income(self, irpef_calculator):
        """Test IRPEF calculation for income between 28,001-50,000 euros (35% bracket)."""
        income = Decimal("40000")
        result = irpef_calculator.calculate_irpef(income)

        # First bracket: 28,000 * 23% = 6,440
        first_bracket = Decimal("28000") * Decimal("0.23")
        # Second bracket: (40,000 - 28,000) * 35% = 4,200
        second_bracket = (income - Decimal("28000")) * Decimal("0.35")
        expected_tax = first_bracket + second_bracket

        assert result["gross_tax"] == expected_tax
        assert result["effective_rate"] == (expected_tax / income * 100).quantize(Decimal("0.01"))
        assert "first_bracket" in result["brackets_used"]
        assert "second_bracket" in result["brackets_used"]

    def test_irpef_calculation_high_income(self, irpef_calculator):
        """Test IRPEF calculation for income above 50,000 euros (43% bracket)."""
        income = Decimal("75000")
        result = irpef_calculator.calculate_irpef(income)

        # First bracket: 28,000 * 23% = 6,440
        first_bracket = Decimal("28000") * Decimal("0.23")
        # Second bracket: (50,000 - 28,000) * 35% = 7,700
        second_bracket = Decimal("22000") * Decimal("0.35")
        # Third bracket: (75,000 - 50,000) * 43% = 10,750
        third_bracket = (income - Decimal("50000")) * Decimal("0.43")
        expected_tax = first_bracket + second_bracket + third_bracket

        assert result["gross_tax"] == expected_tax
        assert "first_bracket" in result["brackets_used"]
        assert "second_bracket" in result["brackets_used"]
        assert "third_bracket" in result["brackets_used"]

    def test_irpef_calculation_zero_income(self, irpef_calculator):
        """Test IRPEF calculation for zero income."""
        income = Decimal("0")
        result = irpef_calculator.calculate_irpef(income)

        assert result["gross_tax"] == Decimal("0")
        assert result["effective_rate"] == Decimal("0")
        assert result["brackets_used"] == []

    def test_irpef_calculation_negative_income_error(self, irpef_calculator):
        """Test that negative income raises appropriate error."""
        with pytest.raises(InvalidIncomeError) as exc_info:
            irpef_calculator.calculate_irpef(Decimal("-1000"))
        assert "Il reddito non può essere negativo" in str(exc_info.value)

    def test_irpef_with_deductions(self, irpef_calculator):
        """Test IRPEF calculation with standard deductions."""
        income = Decimal("30000")
        deductions = {
            "lavoro_dipendente": Decimal("1880"),  # Standard employee deduction
            "spese_mediche": Decimal("500"),
            "mutuo_prima_casa": Decimal("2000"),
        }

        result = irpef_calculator.calculate_irpef_with_deductions(income, deductions)

        total_deductions = sum(deductions.values())
        taxable_income = max(income - total_deductions, Decimal("0"))
        expected_tax = irpef_calculator.calculate_irpef(taxable_income)["gross_tax"]

        assert result["taxable_income"] == taxable_income
        assert result["total_deductions"] == total_deductions
        assert result["net_tax"] == expected_tax


class TestInpsCalculator:
    """Test suite for INPS social security contributions."""

    @pytest.fixture
    def inps_calculator(self):
        return InpsCalculator()

    def test_employee_inps_contribution(self, inps_calculator):
        """Test INPS contribution calculation for employees."""
        gross_salary = Decimal("35000")
        result = inps_calculator.calculate_employee_contribution(gross_salary)

        # Employee contribution is typically 9.19% up to ceiling
        expected_contribution = gross_salary * Decimal("0.0919")

        assert result["employee_contribution"] == expected_contribution
        assert result["contribution_rate"] == Decimal("9.19")
        assert result["gross_salary"] == gross_salary
        assert "pension_contribution" in result

    def test_employer_inps_contribution(self, inps_calculator):
        """Test INPS contribution calculation for employers."""
        gross_salary = Decimal("35000")
        result = inps_calculator.calculate_employer_contribution(gross_salary)

        # Employer contribution is typically around 30% of gross salary
        expected_rate = Decimal("30.00")  # Simplified standard rate
        expected_contribution = gross_salary * expected_rate / 100

        assert result["employer_contribution"] == expected_contribution
        assert result["contribution_rate"] == expected_rate
        assert result["total_cost"] == gross_salary + expected_contribution

    def test_self_employed_inps_contribution(self, inps_calculator):
        """Test INPS contribution for self-employed individuals."""
        annual_income = Decimal("45000")
        result = inps_calculator.calculate_self_employed_contribution(annual_income)

        # Self-employed in separate regime: 24% or 25.72% based on conditions
        expected_rate = Decimal("24.00")  # Standard rate for those in other regimes
        expected_contribution = annual_income * expected_rate / 100

        assert result["contribution"] == expected_contribution
        assert result["contribution_rate"] == expected_rate
        assert result["annual_income"] == annual_income

    def test_inps_contribution_ceiling(self, inps_calculator):
        """Test INPS contribution calculation with income ceiling."""
        high_income = Decimal("150000")
        result = inps_calculator.calculate_employee_contribution(high_income)

        # INPS has a maximum contribution base (around 101,427 euros in 2024)
        ceiling = Decimal("101427")
        expected_contribution = ceiling * Decimal("0.0919")

        assert result["employee_contribution"] <= expected_contribution
        assert result["contribution_base"] <= ceiling

    def test_inps_commercial_executive_contribution(self, inps_calculator):
        """Test INPS contribution for commercial executives."""
        income = Decimal("60000")
        result = inps_calculator.calculate_executive_contribution(income)

        # Different rates for executives: 9.19% up to 46,630, then 10.19%
        ceiling_first = Decimal("46630")
        if income <= ceiling_first:
            expected_contribution = income * Decimal("0.0919")
        else:
            first_part = ceiling_first * Decimal("0.0919")
            second_part = (income - ceiling_first) * Decimal("0.1019")
            expected_contribution = first_part + second_part

        assert result["total_contribution"] == expected_contribution


class TestVatCalculator:
    """Test suite for VAT (IVA) calculations with different rates."""

    @pytest.fixture
    def vat_calculator(self):
        return VatCalculator()

    def test_standard_vat_calculation(self, vat_calculator):
        """Test standard VAT calculation at 22%."""
        net_amount = Decimal("1000")
        result = vat_calculator.calculate_vat(net_amount, "standard")

        expected_vat = net_amount * Decimal("0.22")
        expected_gross = net_amount + expected_vat

        assert result["vat_amount"] == expected_vat
        assert result["gross_amount"] == expected_gross
        assert result["vat_rate"] == Decimal("22")
        assert result["net_amount"] == net_amount

    def test_reduced_vat_rates(self, vat_calculator):
        """Test reduced VAT rates for different categories."""
        net_amount = Decimal("500")

        # Test 10% reduced rate
        result_10 = vat_calculator.calculate_vat(net_amount, "reduced_10")
        expected_vat_10 = net_amount * Decimal("0.10")
        assert result_10["vat_amount"] == expected_vat_10
        assert result_10["vat_rate"] == Decimal("10")

        # Test 4% super-reduced rate
        result_4 = vat_calculator.calculate_vat(net_amount, "reduced_4")
        expected_vat_4 = net_amount * Decimal("0.04")
        assert result_4["vat_amount"] == expected_vat_4
        assert result_4["vat_rate"] == Decimal("4")

    def test_vat_exempt_calculation(self, vat_calculator):
        """Test VAT-exempt calculations."""
        net_amount = Decimal("2000")
        result = vat_calculator.calculate_vat(net_amount, "exempt")

        assert result["vat_amount"] == Decimal("0")
        assert result["gross_amount"] == net_amount
        assert result["vat_rate"] == Decimal("0")
        assert "exemption_reason" in result

    def test_reverse_vat_calculation(self, vat_calculator):
        """Test reverse VAT calculation from gross amount."""
        gross_amount = Decimal("1220")  # Including 22% VAT
        result = vat_calculator.calculate_reverse_vat(gross_amount, "standard")

        expected_net = gross_amount / Decimal("1.22")
        expected_vat = gross_amount - expected_net

        assert result["net_amount"].quantize(Decimal("0.01")) == expected_net.quantize(Decimal("0.01"))
        assert result["vat_amount"].quantize(Decimal("0.01")) == expected_vat.quantize(Decimal("0.01"))

    def test_eu_vat_calculation(self, vat_calculator):
        """Test VAT calculation for EU cross-border transactions."""
        net_amount = Decimal("1500")
        result = vat_calculator.calculate_eu_vat(
            net_amount, origin_country="IT", destination_country="DE", service_type="consulting"
        )

        # B2B consulting services: reverse charge mechanism
        assert result["vat_treatment"] == "reverse_charge"
        assert result["italian_vat"] == Decimal("0")
        assert result["foreign_vat_applicable"] is True


class TestCorporateTaxCalculator:
    """Test suite for corporate tax calculations (IRES and IRAP)."""

    @pytest.fixture
    def corporate_calculator(self):
        return CorporateTaxCalculator()

    def test_ires_calculation(self, corporate_calculator):
        """Test IRES (Corporate Income Tax) calculation at 24%."""
        taxable_income = Decimal("100000")
        result = corporate_calculator.calculate_ires(taxable_income)

        expected_ires = taxable_income * Decimal("0.24")

        assert result["ires_tax"] == expected_ires
        assert result["tax_rate"] == Decimal("24")
        assert result["taxable_income"] == taxable_income

    def test_irap_calculation_standard(self, corporate_calculator):
        """Test IRAP calculation for standard businesses at 3.9%."""
        production_value = Decimal("200000")
        result = corporate_calculator.calculate_irap(production_value, region="Lombardia", business_type="standard")

        expected_irap = production_value * Decimal("0.039")

        assert result["irap_tax"] == expected_irap
        assert result["tax_rate"] == Decimal("3.9")
        assert result["production_value"] == production_value
        assert result["region"] == "Lombardia"

    def test_irap_calculation_banks(self, corporate_calculator):
        """Test IRAP calculation for banks at higher rate."""
        production_value = Decimal("500000")
        result = corporate_calculator.calculate_irap(production_value, region="Lazio", business_type="banks")

        # Banks typically pay 4.65% IRAP
        expected_rate = Decimal("4.65")
        expected_irap = production_value * expected_rate / 100

        assert result["irap_tax"] == expected_irap
        assert result["tax_rate"] == expected_rate
        assert result["business_type"] == "banks"

    def test_combined_corporate_tax(self, corporate_calculator):
        """Test combined IRES + IRAP calculation."""
        taxable_income = Decimal("150000")
        production_value = Decimal("180000")

        result = corporate_calculator.calculate_combined_corporate_tax(
            taxable_income=taxable_income, production_value=production_value, region="Piemonte"
        )

        expected_ires = taxable_income * Decimal("0.24")
        expected_irap = production_value * Decimal("0.039")
        expected_total = expected_ires + expected_irap

        assert result["ires_tax"] == expected_ires
        assert result["irap_tax"] == expected_irap
        assert result["total_corporate_tax"] == expected_total
        assert result["effective_rate"] > Decimal("25")  # Combined rate > 24% IRES alone


class TestPropertyTaxCalculator:
    """Test suite for property tax (IMU) calculations."""

    @pytest.fixture
    def property_calculator(self):
        return PropertyTaxCalculator()

    async def test_imu_calculation_primary_residence_exempt(self, property_calculator):
        """Test IMU calculation for primary residence (usually exempt)."""
        cadastral_value = Decimal("500000")
        result = await property_calculator.calculate_imu(
            cadastral_value=cadastral_value,
            cap="00100",  # Rome
            is_primary_residence=True,
        )

        # Primary residences are typically exempt unless luxury properties
        assert result["imu_tax"] == Decimal("0")
        assert result["exemption"] is True
        assert result["exemption_reason"] == "primary_residence"

    async def test_imu_calculation_second_home(self, property_calculator):
        """Test IMU calculation for second homes."""
        cadastral_value = Decimal("300000")
        result = await property_calculator.calculate_imu(
            cadastral_value=cadastral_value,
            cap="20100",  # Milan
            is_primary_residence=False,
        )

        # IMU calculated using cadastral value * multiplier * coefficient
        cadastral_adjusted = cadastral_value * Decimal("1.05")  # 5% increase
        expected_taxable_base = cadastral_adjusted * 160  # Standard coefficient
        expected_rate = Decimal("0.86")  # Standard rate from config
        expected_tax = expected_taxable_base * expected_rate / 100

        assert result["cadastral_adjusted"] == cadastral_adjusted
        assert result["taxable_base"] == expected_taxable_base
        assert result["tax_rate"] == expected_rate
        assert result["imu_tax"] == expected_tax.quantize(Decimal("0.01"))
        assert result["exemption"] is False

    async def test_imu_calculation_commercial_property(self, property_calculator):
        """Test IMU calculation for commercial properties."""
        cadastral_value = Decimal("800000")
        result = await property_calculator.calculate_imu(
            cadastral_value=cadastral_value,
            cap="80100",  # Naples
            property_type="commercial",
        )

        # Commercial properties have different multipliers and rates
        assert result["imu_tax"] > Decimal("0")
        assert result["property_type"] == "commercial"
        assert result["tax_rate"] > Decimal("1.0")  # Commercial rates typically higher


class TestCapitalGainsTaxCalculator:
    """Test suite for capital gains tax calculations."""

    @pytest.fixture
    def capital_gains_calculator(self):
        return CapitalGainsTaxCalculator()

    def test_financial_capital_gains(self, capital_gains_calculator):
        """Test capital gains tax on financial investments at 26%."""
        purchase_price = Decimal("10000")
        sale_price = Decimal("12000")

        result = capital_gains_calculator.calculate_capital_gains_tax(
            purchase_price=purchase_price, sale_price=sale_price, asset_type="financial", holding_period_days=200
        )

        capital_gain = sale_price - purchase_price
        expected_tax = capital_gain * Decimal("0.26")

        assert result["capital_gain"] == capital_gain
        assert result["tax_amount"] == expected_tax
        assert result["tax_rate"] == Decimal("26")
        assert result["asset_type"] == "financial"

    def test_real_estate_capital_gains(self, capital_gains_calculator):
        """Test capital gains tax on real estate with holding period considerations."""
        purchase_price = Decimal("200000")
        sale_price = Decimal("250000")

        # Real estate held for more than 5 years is often exempt
        result = capital_gains_calculator.calculate_capital_gains_tax(
            purchase_price=purchase_price,
            sale_price=sale_price,
            asset_type="real_estate",
            holding_period_days=2000,  # > 5 years
        )

        assert result["tax_amount"] == Decimal("0")
        assert result["exemption"] is True
        assert result["exemption_reason"] == "long_term_holding"

    def test_cryptocurrency_capital_gains(self, capital_gains_calculator):
        """Test capital gains tax on cryptocurrency."""
        purchase_price = Decimal("5000")
        sale_price = Decimal("8000")

        result = capital_gains_calculator.calculate_capital_gains_tax(
            purchase_price=purchase_price, sale_price=sale_price, asset_type="cryptocurrency", holding_period_days=100
        )

        capital_gain = sale_price - purchase_price

        # Crypto gains over 2,000 euros are taxed at 26%
        if capital_gain > Decimal("2000"):
            expected_tax = capital_gain * Decimal("0.26")
        else:
            expected_tax = Decimal("0")

        assert result["capital_gain"] == capital_gain
        assert result["tax_amount"] == expected_tax


class TestFreelancerTaxCalculator:
    """Test suite for freelancer and P.IVA tax calculations."""

    @pytest.fixture
    def freelancer_calculator(self):
        return FreelancerTaxCalculator()

    def test_flat_rate_regime_calculation(self, freelancer_calculator):
        """Test tax calculation under flat-rate regime (Regime Forfettario)."""
        annual_revenue = Decimal("40000")
        activity_category = "consulting"

        result = freelancer_calculator.calculate_flat_rate_tax(
            annual_revenue=annual_revenue,
            activity_category=activity_category,
            is_new_business=True,  # 5% rate for first 5 years
        )

        # Consulting has 78% coefficient
        taxable_income = annual_revenue * Decimal("0.78")
        # New business rate: 5%
        expected_tax = taxable_income * Decimal("0.05")

        assert result["taxable_income"] == taxable_income
        assert result["tax_amount"] == expected_tax
        assert result["tax_rate"] == Decimal("5")
        assert result["regime"] == "forfettario"

    def test_standard_regime_freelancer(self, freelancer_calculator):
        """Test freelancer tax calculation under standard regime."""
        annual_revenue = Decimal("90000")  # Above flat-rate threshold
        business_expenses = Decimal("15000")

        result = freelancer_calculator.calculate_standard_regime_tax(
            annual_revenue=annual_revenue,
            business_expenses=business_expenses,
            region="Lombardia",
            municipality="Milano",
        )

        taxable_income = annual_revenue - business_expenses

        # Should include IRPEF, regional/municipal surcharges, INPS
        assert result["taxable_income"] == taxable_income
        assert "irpef_tax" in result
        assert "regional_surcharge" in result
        assert "municipal_surcharge" in result
        assert "inps_contribution" in result
        assert result["total_tax"] > Decimal("0")

    def test_quarterly_tax_payments(self, freelancer_calculator):
        """Test quarterly advance tax payment calculations."""
        previous_year_tax = Decimal("8000")
        current_quarter_revenue = Decimal("15000")

        result = freelancer_calculator.calculate_quarterly_payments(
            previous_year_total_tax=previous_year_tax,
            current_quarter_revenue=current_quarter_revenue,
            quarter=2,  # Second quarter
        )

        # Quarterly payments are typically based on previous year
        expected_quarterly = previous_year_tax / 4

        assert result["quarterly_payment"] == expected_quarterly
        assert result["quarter"] == 2
        assert result["payment_due_date"] in result


class TestTaxDeductionEngine:
    """Test suite for tax deduction calculations."""

    @pytest.fixture
    def deduction_engine(self):
        return TaxDeductionEngine()

    def test_employee_deductions(self, deduction_engine):
        """Test standard deductions for employees."""
        income = Decimal("35000")
        result = deduction_engine.calculate_employee_deductions(income)

        # Employee deduction decreases with income
        assert result["work_deduction"] > Decimal("0")
        assert result["total_deductions"] > Decimal("1800")  # Minimum deduction
        assert result["income"] == income

    def test_family_deductions(self, deduction_engine):
        """Test family-related deductions."""
        deductions_data = {
            "dependent_children": 2,
            "dependent_spouse": True,
            "children_ages": [5, 8],
            "spouse_income": Decimal("0"),
        }

        result = deduction_engine.calculate_family_deductions(**deductions_data)

        assert result["children_deduction"] > Decimal("0")
        assert result["spouse_deduction"] > Decimal("0")
        assert result["total_family_deductions"] > Decimal("1000")

    def test_medical_expense_deductions(self, deduction_engine):
        """Test medical expense deductions above 129.11 euro threshold."""
        medical_expenses = Decimal("800")
        result = deduction_engine.calculate_medical_deductions(medical_expenses)

        # Only expenses above 129.11 euros are deductible
        threshold = Decimal("129.11")
        expected_deduction = max(medical_expenses - threshold, Decimal("0"))

        assert result["deductible_amount"] == expected_deduction
        assert result["threshold"] == threshold
        assert result["total_expenses"] == medical_expenses

    def test_home_renovation_deductions(self, deduction_engine):
        """Test home renovation tax deductions (Superbonus, Ecobonus, etc.)."""
        renovation_expenses = Decimal("20000")
        renovation_type = "energy_efficiency"

        result = deduction_engine.calculate_renovation_deductions(
            expenses=renovation_expenses, renovation_type=renovation_type
        )

        # Energy efficiency renovations often have high deduction rates
        assert result["deduction_rate"] >= Decimal("50")
        assert result["deductible_amount"] > Decimal("0")
        assert result["spread_over_years"] > 0


class TestTaxOptimizationEngine:
    """Test suite for tax optimization suggestions."""

    @pytest.fixture
    def optimization_engine(self):
        return TaxOptimizationEngine()

    def test_employee_vs_contractor_comparison(self, optimization_engine):
        """Test tax burden comparison between employee and contractor."""
        gross_income = Decimal("50000")

        result = optimization_engine.compare_employment_types(gross_income)

        assert "employee" in result
        assert "contractor" in result
        assert "savings_potential" in result
        assert "recommendation" in result

        # Should provide detailed breakdown for each type
        assert result["employee"]["net_income"] > Decimal("0")
        assert result["contractor"]["net_income"] > Decimal("0")

    def test_pension_contribution_optimization(self, optimization_engine):
        """Test pension contribution optimization suggestions."""
        annual_income = Decimal("60000")
        current_contributions = Decimal("2000")

        result = optimization_engine.optimize_pension_contributions(
            annual_income=annual_income, current_contributions=current_contributions
        )

        assert result["recommended_contribution"] > current_contributions
        assert result["tax_savings"] > Decimal("0")
        assert result["deduction_rate"] in [Decimal("20"), Decimal("23")]  # Based on tax bracket


class TestItalianTaxCalculator:
    """Integration tests for the main Italian Tax Calculator."""

    @pytest.fixture
    def tax_calculator(self):
        return ItalianTaxCalculator()

    def test_net_salary_calculation_milan(self, tax_calculator):
        """Test complete net salary calculation for Milan employee."""
        gross_salary = Decimal("35000")

        result = tax_calculator.calculate_net_salary(
            gross_salary=gross_salary,
            location="20100",  # Milan CAP
            employment_type="employee",
            family_status={"marital_status": "single", "children": 0},
        )

        # Should include all tax components
        assert "irpef_tax" in result
        assert "regional_surcharge" in result
        assert "municipal_surcharge" in result
        assert "inps_employee" in result
        assert "net_salary" in result
        assert result["net_salary"] < gross_salary
        assert result["tax_burden_percentage"] > Decimal("30")

    def test_freelancer_tax_calculation_rome(self, tax_calculator):
        """Test complete freelancer tax calculation for Rome."""
        annual_revenue = Decimal("55000")

        result = tax_calculator.calculate_freelancer_taxes(
            annual_revenue=annual_revenue,
            location="00100",  # Rome CAP
            activity_type="consulting",
            regime="standard",  # Above flat-rate threshold
            business_expenses=Decimal("8000"),
        )

        assert "irpef_tax" in result
        assert "inps_contribution" in result
        assert "vat_due" in result
        assert "quarterly_payments" in result
        assert result["total_tax_burden"] > Decimal("10000")

    def test_multi_scenario_tax_comparison(self, tax_calculator):
        """Test tax comparison across multiple scenarios."""
        scenarios = [
            {
                "type": "employee",
                "income": Decimal("40000"),
                "location": "20100",  # Milan
            },
            {"type": "freelancer_flat_rate", "income": Decimal("40000"), "location": "20100"},
            {"type": "freelancer_standard", "income": Decimal("40000"), "location": "20100"},
        ]

        result = tax_calculator.compare_scenarios(scenarios)

        assert len(result["scenarios"]) == 3
        assert result["best_option"]["type"] in ["employee", "freelancer_flat_rate", "freelancer_standard"]
        assert result["tax_savings"] >= Decimal("0")

    def test_natural_language_query_processing(self, tax_calculator):
        """Test natural language query processing for tax questions."""
        query = "Calculate net salary for 35,000 euro gross in Milan"

        result = tax_calculator.process_natural_language_query(query)

        assert result["understood_intent"] == "net_salary_calculation"
        assert result["extracted_parameters"]["gross_income"] == Decimal("35000")
        assert result["extracted_parameters"]["location"] == "Milan"
        assert "calculation_result" in result

    def test_tax_calendar_reminders(self, tax_calculator):
        """Test tax calendar and deadline reminders."""
        taxpayer_type = "freelancer"
        current_date = date(2024, 5, 15)

        result = tax_calculator.get_tax_calendar(taxpayer_type, current_date)

        assert "upcoming_deadlines" in result
        assert "quarterly_payments" in result
        assert len(result["upcoming_deadlines"]) > 0
