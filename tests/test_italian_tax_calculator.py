"""
TDD Tests for Italian Tax Calculator.

This module tests all Italian tax calculations including IRPEF, IVA, IRES, IRAP,
withholding taxes, and regional/municipal taxes with complete accuracy.
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Dict, List

import pytest

# These imports will fail initially - that's the TDD approach
from app.services.validators.italian_tax_calculator import (
    DeductionType,
    IRPEFBracket,
    ItalianTaxCalculator,
    IVARate,
    TaxCreditType,
    TaxResult,
    TaxYear,
)


class TestItalianTaxCalculator:
    """Test suite for Italian Tax Calculator using TDD methodology."""

    @pytest.fixture
    def calculator(self):
        """Create calculator instance for tests."""
        return ItalianTaxCalculator(tax_year=2024)

    # =========================================================================
    # IRPEF (Income Tax) Tests - Start with failing tests
    # =========================================================================

    def test_irpef_calculation_single_bracket_minimum(self, calculator):
        """Test IRPEF for income in first bracket only (€15,000)."""
        # Arrange
        gross_income = Decimal("15000")
        # First bracket: €15,000 * 23% = €3,450
        expected_tax = Decimal("3450.00")
        expected_net_rate = Decimal("23.00")

        # Act
        result = calculator.calculate_irpef(gross_income=gross_income, deductions=[], tax_credits=[])

        # Assert
        assert isinstance(result, TaxResult)
        assert result.gross_amount == gross_income
        assert result.tax_amount == expected_tax
        assert result.effective_rate == expected_net_rate
        assert len(result.calculation_steps) == 1
        assert result.calculation_steps[0]["bracket"] == "23%"
        assert result.calculation_steps[0]["amount"] == expected_tax
        assert result.formula.startswith("IRPEF 2024:")

    def test_irpef_calculation_multiple_brackets_30k(self, calculator):
        """Test IRPEF for €30,000 income (spans 3 brackets)."""
        # Arrange
        gross_income = Decimal("30000")
        # First bracket: €15,000 * 23% = €3,450
        # Second bracket: €13,000 * 25% = €3,250
        # Third bracket: €2,000 * 35% = €700
        # Total: €7,400
        expected_tax = Decimal("7400.00")
        expected_effective_rate = Decimal("24.67")  # €7,400 / €30,000 = 24.67%

        # Act
        result = calculator.calculate_irpef(gross_income, [], [])

        # Assert
        assert result.tax_amount == expected_tax
        assert result.effective_rate == expected_effective_rate
        assert len(result.calculation_steps) == 3
        assert result.calculation_steps[0]["bracket"] == "23%"
        assert result.calculation_steps[1]["bracket"] == "25%"
        assert result.calculation_steps[2]["bracket"] == "35%"

    def test_irpef_calculation_with_standard_deductions_50k(self, calculator):
        """Test IRPEF for €50,000 with standard employee deductions."""
        # Arrange
        gross_income = Decimal("50000")
        deductions = [
            {"type": DeductionType.EMPLOYEE, "amount": Decimal("1000")},  # Standard employee deduction
        ]
        taxable_income = Decimal("49000")  # After deductions

        # First bracket: €15,000 * 23% = €3,450
        # Second bracket: €13,000 * 25% = €3,250
        # Third bracket: €21,000 * 35% = €7,350
        # Total: €14,050
        expected_tax = Decimal("14050.00")

        # Act
        result = calculator.calculate_irpef(gross_income, deductions, [])

        # Assert
        assert result.taxable_income == taxable_income
        assert result.tax_amount == expected_tax
        assert len(result.calculation_steps) == 3
        assert result.deductions_applied == Decimal("1000")

    def test_irpef_calculation_with_tax_credits_family(self, calculator):
        """Test IRPEF with family tax credits (spouse + children)."""
        # Arrange
        gross_income = Decimal("40000")
        deductions = []
        tax_credits = [
            {"type": TaxCreditType.SPOUSE, "amount": Decimal("800")},
            {"type": TaxCreditType.CHILD, "amount": Decimal("1200")},  # 2 children
        ]

        # Calculate gross tax first
        # First bracket: €15,000 * 23% = €3,450
        # Second bracket: €13,000 * 25% = €3,250
        # Third bracket: €12,000 * 35% = €4,200
        # Gross tax: €10,900
        # Less credits: €10,900 - €800 - €1,200 = €8,900
        expected_tax = Decimal("8900.00")

        # Act
        result = calculator.calculate_irpef(gross_income, deductions, tax_credits)

        # Assert
        assert result.tax_amount == expected_tax
        assert result.tax_credits_applied == Decimal("2000.00")
        assert "spouse_credit" in [step["type"] for step in result.calculation_steps]
        assert "child_credit" in [step["type"] for step in result.calculation_steps]

    def test_irpef_calculation_high_income_100k(self, calculator):
        """Test IRPEF for high income €100,000 (all brackets)."""
        # Arrange
        gross_income = Decimal("100000")

        # All brackets calculation:
        # 1st: €15,000 * 23% = €3,450
        # 2nd: €13,000 * 25% = €3,250
        # 3rd: €27,000 * 35% = €9,450
        # 4th: €45,000 * 43% = €19,350
        # Total: €35,500
        expected_tax = Decimal("35500.00")
        expected_effective_rate = Decimal("35.50")

        # Act
        result = calculator.calculate_irpef(gross_income, [], [])

        # Assert
        assert result.tax_amount == expected_tax
        assert result.effective_rate == expected_effective_rate
        assert len(result.calculation_steps) == 4
        assert result.calculation_steps[3]["bracket"] == "43%"

    def test_irpef_edge_case_zero_income(self, calculator):
        """Test IRPEF calculation with zero income."""
        # Act & Assert
        result = calculator.calculate_irpef(Decimal("0"), [], [])
        assert result.tax_amount == Decimal("0")
        assert result.effective_rate == Decimal("0")
        assert len(result.calculation_steps) == 0

    def test_irpef_edge_case_negative_income(self, calculator):
        """Test IRPEF calculation with negative income (should raise error)."""
        with pytest.raises(ValueError, match="Income cannot be negative"):
            calculator.calculate_irpef(Decimal("-1000"), [], [])

    # =========================================================================
    # IVA (VAT) Tests
    # =========================================================================

    def test_iva_calculation_standard_rate_22_percent(self, calculator):
        """Test IVA calculation at standard 22% rate."""
        # Arrange
        net_amount = Decimal("1000.00")
        iva_rate = IVARate.STANDARD  # 22%
        expected_iva = Decimal("220.00")
        expected_gross = Decimal("1220.00")

        # Act
        result = calculator.calculate_iva(net_amount=net_amount, rate=iva_rate, calculation_type="add_iva")

        # Assert
        assert result.net_amount == net_amount
        assert result.iva_amount == expected_iva
        assert result.gross_amount == expected_gross
        assert result.rate_applied == Decimal("22.00")
        assert result.formula == "€1,000.00 + (€1,000.00 × 22%) = €1,220.00"

    def test_iva_calculation_reduced_rate_10_percent(self, calculator):
        """Test IVA calculation at reduced 10% rate."""
        # Arrange
        net_amount = Decimal("500.00")
        iva_rate = IVARate.REDUCED  # 10%
        expected_iva = Decimal("50.00")

        # Act
        result = calculator.calculate_iva(net_amount, iva_rate, "add_iva")

        # Assert
        assert result.iva_amount == expected_iva
        assert result.rate_applied == Decimal("10.00")

    def test_iva_calculation_super_reduced_rate_4_percent(self, calculator):
        """Test IVA calculation at super-reduced 4% rate."""
        # Arrange
        net_amount = Decimal("250.00")
        iva_rate = IVARate.SUPER_REDUCED  # 4%
        expected_iva = Decimal("10.00")

        # Act
        result = calculator.calculate_iva(net_amount, iva_rate, "add_iva")

        # Assert
        assert result.iva_amount == expected_iva
        assert result.rate_applied == Decimal("4.00")

    def test_iva_reverse_calculation_from_gross(self, calculator):
        """Test reverse IVA calculation (extract IVA from gross amount)."""
        # Arrange
        gross_amount = Decimal("1220.00")
        iva_rate = IVARate.STANDARD  # 22%
        expected_net = Decimal("1000.00")
        expected_iva = Decimal("220.00")

        # Act
        result = calculator.calculate_iva(net_amount=gross_amount, rate=iva_rate, calculation_type="extract_iva")

        # Assert
        assert result.net_amount == expected_net
        assert result.iva_amount == expected_iva
        assert result.formula == "€1,220.00 ÷ 1.22 = €1,000.00 (net) + €220.00 (IVA)"

    def test_iva_zero_rate_exempt(self, calculator):
        """Test IVA calculation for exempt goods (0% rate)."""
        # Arrange
        net_amount = Decimal("1000.00")
        iva_rate = IVARate.EXEMPT  # 0%

        # Act
        result = calculator.calculate_iva(net_amount, iva_rate, "add_iva")

        # Assert
        assert result.iva_amount == Decimal("0.00")
        assert result.gross_amount == net_amount
        assert result.rate_applied == Decimal("0.00")

    # =========================================================================
    # IRES (Corporate Tax) Tests
    # =========================================================================

    def test_ires_calculation_basic_24_percent(self, calculator):
        """Test IRES calculation at 24% rate for corporations."""
        # Arrange
        taxable_income = Decimal("100000")
        expected_ires = Decimal("24000.00")  # 100,000 * 24%

        # Act
        result = calculator.calculate_ires(taxable_income)

        # Assert
        assert result.tax_amount == expected_ires
        assert result.rate_applied == Decimal("24.00")
        assert result.formula == "IRES: €100,000.00 × 24% = €24,000.00"

    def test_ires_with_startup_incentives(self, calculator):
        """Test IRES with startup tax incentives (reduced rate)."""
        # Arrange
        taxable_income = Decimal("50000")
        is_startup = True
        expected_ires = Decimal("6000.00")  # 50,000 * 12% (reduced rate)

        # Act
        result = calculator.calculate_ires(taxable_income, startup_incentive=is_startup)

        # Assert
        assert result.tax_amount == expected_ires
        assert result.rate_applied == Decimal("12.00")
        assert "startup incentive" in result.formula.lower()

    # =========================================================================
    # IRAP (Regional Tax) Tests
    # =========================================================================

    def test_irap_calculation_standard_3_9_percent(self, calculator):
        """Test IRAP calculation at standard 3.9% rate."""
        # Arrange
        production_value = Decimal("200000")
        expected_irap = Decimal("7800.00")  # 200,000 * 3.9%

        # Act
        result = calculator.calculate_irap(production_value)

        # Assert
        assert result.tax_amount == expected_irap
        assert result.rate_applied == Decimal("3.90")
        assert result.formula == "IRAP: €200,000.00 × 3.9% = €7,800.00"

    def test_irap_with_deductions_healthcare(self, calculator):
        """Test IRAP with healthcare sector deductions."""
        # Arrange
        production_value = Decimal("500000")
        sector_deductions = Decimal("50000")  # Healthcare deductions
        taxable_base = production_value - sector_deductions
        expected_irap = taxable_base * Decimal("0.039")

        # Act
        result = calculator.calculate_irap(
            production_value, deductions=[{"type": "healthcare", "amount": sector_deductions}]
        )

        # Assert
        assert result.taxable_base == taxable_base
        assert result.tax_amount == expected_irap
        assert result.deductions_applied == sector_deductions

    # =========================================================================
    # Withholding Tax (Ritenuta d'Acconto) Tests
    # =========================================================================

    def test_withholding_tax_professionals_20_percent(self, calculator):
        """Test withholding tax for professionals at 20%."""
        # Arrange
        gross_fee = Decimal("5000.00")
        expected_withholding = Decimal("1000.00")  # 5,000 * 20%
        expected_net_payment = Decimal("4000.00")

        # Act
        result = calculator.calculate_withholding_tax(
            gross_amount=gross_fee, withholding_type="professional", rate=Decimal("20.00")
        )

        # Assert
        assert result.withholding_amount == expected_withholding
        assert result.net_payment == expected_net_payment
        assert result.rate_applied == Decimal("20.00")
        assert result.formula == "Ritenuta: €5,000.00 × 20% = €1,000.00"

    def test_withholding_tax_dividends_26_percent(self, calculator):
        """Test withholding tax on dividends at 26%."""
        # Arrange
        dividend_amount = Decimal("10000.00")
        expected_withholding = Decimal("2600.00")  # 10,000 * 26%

        # Act
        result = calculator.calculate_withholding_tax(dividend_amount, "dividend", Decimal("26.00"))

        # Assert
        assert result.withholding_amount == expected_withholding
        assert result.rate_applied == Decimal("26.00")

    # =========================================================================
    # Integration Tests - Multiple Tax Calculations
    # =========================================================================

    def test_complete_tax_calculation_individual(self, calculator):
        """Test complete tax calculation for individual with all taxes."""
        # Arrange
        gross_income = Decimal("60000")
        deductions = [{"type": DeductionType.EMPLOYEE, "amount": Decimal("2000")}]
        tax_credits = [{"type": TaxCreditType.CHILD, "amount": Decimal("600")}]

        # Act
        result = calculator.calculate_complete_individual_taxes(
            gross_income=gross_income, deductions=deductions, tax_credits=tax_credits, region="lombardy"
        )

        # Assert
        assert isinstance(result, dict)
        assert "irpef" in result
        assert "regional_tax" in result
        assert "municipal_tax" in result
        assert "total_tax" in result
        assert result["total_tax"]["amount"] > Decimal("0")
        assert len(result["calculation_summary"]) > 0

    def test_complete_tax_calculation_company(self, calculator):
        """Test complete tax calculation for company with IRES + IRAP."""
        # Arrange
        taxable_income = Decimal("150000")
        production_value = Decimal("500000")

        # Act
        result = calculator.calculate_complete_company_taxes(
            taxable_income=taxable_income, production_value=production_value, region="lazio"
        )

        # Assert
        assert "ires" in result
        assert "irap" in result
        assert "total_tax" in result
        assert result["ires"]["amount"] == Decimal("36000.00")  # 150,000 * 24%
        assert result["irap"]["amount"] > Decimal("0")

    # =========================================================================
    # Performance Tests
    # =========================================================================

    def test_calculation_performance_multiple_scenarios(self, calculator):
        """Test calculation performance with multiple scenarios."""
        import time

        # Arrange
        test_scenarios = [
            (Decimal("25000"), [], []),
            (Decimal("50000"), [{"type": DeductionType.EMPLOYEE, "amount": Decimal("1000")}], []),
            (Decimal("100000"), [], [{"type": TaxCreditType.CHILD, "amount": Decimal("1200")}]),
        ]

        # Act
        start_time = time.time()
        results = []
        for income, deductions, credits in test_scenarios:
            result = calculator.calculate_irpef(income, deductions, credits)
            results.append(result)
        end_time = time.time()

        # Assert
        assert len(results) == 3
        assert (end_time - start_time) < 0.1  # Should complete in < 100ms
        assert all(isinstance(r, TaxResult) for r in results)

    # =========================================================================
    # Error Handling Tests
    # =========================================================================

    def test_invalid_tax_year(self):
        """Test error handling for invalid tax year."""
        with pytest.raises(ValueError, match="Tax year must be between"):
            ItalianTaxCalculator(tax_year=2010)  # Too old

        with pytest.raises(ValueError, match="Tax year must be between"):
            ItalianTaxCalculator(tax_year=2030)  # Too far in future

    def test_invalid_iva_rate(self, calculator):
        """Test error handling for invalid IVA rate."""
        with pytest.raises(ValueError, match="Invalid IVA rate"):
            calculator.calculate_iva(
                Decimal("1000"),
                "invalid_rate",  # Invalid rate
                "add_iva",
            )

    def test_calculation_precision(self, calculator):
        """Test calculation precision to 2 decimal places."""
        # Arrange
        amount = Decimal("1000.01")  # Precise amount

        # Act
        result = calculator.calculate_iva(amount, IVARate.STANDARD, "add_iva")

        # Assert
        assert str(result.iva_amount).count(".") == 1  # Has decimal point
        assert len(str(result.iva_amount).split(".")[1]) <= 2  # Max 2 decimal places
        assert result.iva_amount == Decimal("220.00")  # Rounded properly
