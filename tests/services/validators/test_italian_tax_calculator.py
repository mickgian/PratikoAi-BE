"""Comprehensive tests for the ItalianTaxCalculator service.

Tests cover all public methods: __init__, calculate_irpef, calculate_iva,
calculate_ires, calculate_irap, calculate_withholding_tax,
calculate_complete_individual_taxes, and calculate_complete_company_taxes.

Each method has happy-path, error, and edge-case tests (TDD / ADR-013).
"""

from decimal import Decimal

import pytest

from app.services.validators.italian_tax_calculator import (
    DeductionType,
    ItalianTaxCalculator,
    IVARate,
    TaxCreditType,
    TaxResult,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def calculator() -> ItalianTaxCalculator:
    """Default calculator for tax year 2024."""
    return ItalianTaxCalculator(tax_year=2024)


# ---------------------------------------------------------------------------
# 1. __init__ tests
# ---------------------------------------------------------------------------


class TestInit:
    """Tests for ItalianTaxCalculator.__init__."""

    def test_valid_default_year(self) -> None:
        calc = ItalianTaxCalculator()
        assert calc.tax_year == 2024

    def test_valid_custom_year(self) -> None:
        calc = ItalianTaxCalculator(tax_year=2025)
        assert calc.tax_year == 2025

    def test_valid_boundary_low(self) -> None:
        calc = ItalianTaxCalculator(tax_year=2020)
        assert calc.tax_year == 2020

    def test_valid_boundary_high(self) -> None:
        calc = ItalianTaxCalculator(tax_year=2029)
        assert calc.tax_year == 2029

    def test_invalid_year_too_low(self) -> None:
        with pytest.raises(ValueError, match="Tax year must be between 2020 and 2029"):
            ItalianTaxCalculator(tax_year=2019)

    def test_invalid_year_too_high(self) -> None:
        with pytest.raises(ValueError, match="Tax year must be between 2020 and 2029"):
            ItalianTaxCalculator(tax_year=2030)

    def test_irpef_brackets_initialised(self) -> None:
        calc = ItalianTaxCalculator()
        assert len(calc.irpef_brackets) == 4

    def test_main_calculator_initialised(self) -> None:
        calc = ItalianTaxCalculator()
        assert calc._main_calculator is not None


# ---------------------------------------------------------------------------
# 2. calculate_irpef tests
# ---------------------------------------------------------------------------


class TestCalculateIrpef:
    """Tests for progressive IRPEF calculation."""

    # --- Zero income ---

    def test_zero_income_returns_all_zeros(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_irpef(Decimal("0"))
        assert result.tax_amount == Decimal("0")
        assert result.effective_rate == Decimal("0")
        assert result.taxable_income == Decimal("0")
        assert result.gross_amount == Decimal("0")
        assert result.calculation_steps == []

    # --- Negative income ---

    def test_negative_income_raises(self, calculator: ItalianTaxCalculator) -> None:
        with pytest.raises(ValueError, match="Income cannot be negative"):
            calculator.calculate_irpef(Decimal("-1"))

    # --- Small income: 10,000 (entirely in 23% bracket) ---

    def test_small_income_10k(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_irpef(Decimal("10000"))
        # 10,000 * 23% = 2,300
        assert result.tax_amount == Decimal("2300.00")
        assert result.taxable_income == Decimal("10000")
        assert result.gross_amount == Decimal("10000")

    def test_small_income_effective_rate(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_irpef(Decimal("10000"))
        assert result.effective_rate == Decimal("23.00")

    # --- Medium income: 30,000 (spans three brackets) ---

    def test_medium_income_30k(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_irpef(Decimal("30000"))
        # Bracket 1: 15,000 * 23% = 3,450
        # Bracket 2: 13,000 * 25% = 3,250
        # Bracket 3:  2,000 * 35% =   700
        # Total = 7,400
        assert result.tax_amount == Decimal("7400.00")

    def test_medium_income_taxable_income(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_irpef(Decimal("30000"))
        assert result.taxable_income == Decimal("30000")

    def test_medium_income_has_calculation_steps(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_irpef(Decimal("30000"))
        # Should have 3 bracket steps
        bracket_steps = [s for s in result.calculation_steps if s["type"] == "irpef_bracket"]
        assert len(bracket_steps) == 3

    # --- High income: 80,000 (spans all four brackets) ---

    def test_high_income_80k(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_irpef(Decimal("80000"))
        # Bracket 1: 15,000 * 23% =  3,450
        # Bracket 2: 13,000 * 25% =  3,250
        # Bracket 3: 27,000 * 35% =  9,450
        # Bracket 4: 25,000 * 43% = 10,750
        # Total = 26,900
        assert result.tax_amount == Decimal("26900.00")

    def test_high_income_effective_rate(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_irpef(Decimal("80000"))
        expected_rate = (Decimal("26900") / Decimal("80000") * 100).quantize(Decimal("0.01"))
        assert result.effective_rate == expected_rate

    def test_high_income_all_four_brackets(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_irpef(Decimal("80000"))
        bracket_steps = [s for s in result.calculation_steps if s["type"] == "irpef_bracket"]
        assert len(bracket_steps) == 4

    # --- Exact bracket boundaries ---

    def test_income_exactly_15k(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_irpef(Decimal("15000"))
        # 15,000 * 23% = 3,450
        assert result.tax_amount == Decimal("3450.00")

    def test_income_exactly_28k(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_irpef(Decimal("28000"))
        # 15,000 * 23% = 3,450
        # 13,000 * 25% = 3,250
        # Total = 6,700
        assert result.tax_amount == Decimal("6700.00")

    def test_income_exactly_55k(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_irpef(Decimal("55000"))
        # 15,000 * 23% =  3,450
        # 13,000 * 25% =  3,250
        # 27,000 * 35% =  9,450
        # Total = 16,150
        assert result.tax_amount == Decimal("16150.00")

    # --- With deductions ---

    def test_with_deductions_reduces_taxable_income(self, calculator: ItalianTaxCalculator) -> None:
        deductions = [{"type": DeductionType.MEDICAL, "amount": Decimal("5000")}]
        result = calculator.calculate_irpef(Decimal("30000"), deductions=deductions)
        # Taxable income = 30,000 - 5,000 = 25,000
        assert result.taxable_income == Decimal("25000")
        assert result.deductions_applied == Decimal("5000")

    def test_with_deductions_correct_tax(self, calculator: ItalianTaxCalculator) -> None:
        deductions = [{"type": DeductionType.EMPLOYEE, "amount": Decimal("5000")}]
        result = calculator.calculate_irpef(Decimal("30000"), deductions=deductions)
        # Taxable: 25,000
        # Bracket 1: 15,000 * 23% = 3,450
        # Bracket 2: 10,000 * 25% = 2,500
        # Total = 5,950
        assert result.tax_amount == Decimal("5950.00")

    def test_with_multiple_deductions(self, calculator: ItalianTaxCalculator) -> None:
        deductions = [
            {"type": DeductionType.EMPLOYEE, "amount": Decimal("3000")},
            {"type": DeductionType.MEDICAL, "amount": Decimal("2000")},
        ]
        result = calculator.calculate_irpef(Decimal("30000"), deductions=deductions)
        assert result.taxable_income == Decimal("25000")
        assert result.deductions_applied == Decimal("5000")

    def test_deductions_exceeding_income_zero_tax(self, calculator: ItalianTaxCalculator) -> None:
        deductions = [{"type": DeductionType.MEDICAL, "amount": Decimal("50000")}]
        result = calculator.calculate_irpef(Decimal("10000"), deductions=deductions)
        assert result.taxable_income == Decimal("0")
        assert result.tax_amount == Decimal("0.00")

    # --- With tax credits ---

    def test_with_tax_credits_reduces_tax(self, calculator: ItalianTaxCalculator) -> None:
        credits = [{"type": TaxCreditType.WORK, "amount": Decimal("1000")}]
        result = calculator.calculate_irpef(Decimal("30000"), tax_credits=credits)
        # Tax before credits = 7,400; after = 6,400
        assert result.tax_amount == Decimal("6400.00")
        assert result.tax_credits_applied == Decimal("1000")

    def test_with_multiple_credits(self, calculator: ItalianTaxCalculator) -> None:
        credits = [
            {"type": TaxCreditType.SPOUSE, "amount": Decimal("500")},
            {"type": TaxCreditType.CHILD, "amount": Decimal("300")},
        ]
        result = calculator.calculate_irpef(Decimal("30000"), tax_credits=credits)
        # Tax before credits = 7,400; after = 6,600
        assert result.tax_amount == Decimal("6600.00")
        assert result.tax_credits_applied == Decimal("800")

    def test_credits_cannot_make_tax_negative(self, calculator: ItalianTaxCalculator) -> None:
        credits = [{"type": TaxCreditType.WORK, "amount": Decimal("50000")}]
        result = calculator.calculate_irpef(Decimal("10000"), tax_credits=credits)
        # Tax = 2,300, credits = 50,000, but min is 0
        assert result.tax_amount == Decimal("0.00")

    # --- Deductions + credits combined ---

    def test_deductions_and_credits_combined(self, calculator: ItalianTaxCalculator) -> None:
        deductions = [{"type": DeductionType.EMPLOYEE, "amount": Decimal("5000")}]
        credits = [{"type": TaxCreditType.WORK, "amount": Decimal("1000")}]
        result = calculator.calculate_irpef(Decimal("30000"), deductions=deductions, tax_credits=credits)
        # Taxable: 25,000; Tax: 5,950; Credits: 1,000 -> 4,950
        assert result.tax_amount == Decimal("4950.00")
        assert result.deductions_applied == Decimal("5000")
        assert result.tax_credits_applied == Decimal("1000")

    # --- Formula populated ---

    def test_formula_is_populated(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_irpef(Decimal("30000"))
        assert "IRPEF 2024" in result.formula
        assert "30,000.00" in result.formula

    # --- Return type ---

    def test_returns_tax_result(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_irpef(Decimal("10000"))
        assert isinstance(result, TaxResult)


# ---------------------------------------------------------------------------
# 3. calculate_iva tests
# ---------------------------------------------------------------------------


class TestCalculateIva:
    """Tests for IVA (VAT) calculation."""

    # --- add_iva ---

    def test_add_iva_standard_22(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_iva(Decimal("1000"), IVARate.STANDARD, "add_iva")
        assert result.iva_amount == Decimal("220.00")
        assert result.gross_amount_vat == Decimal("1220.00")
        assert result.net_amount == Decimal("1000.00")
        assert result.rate_applied == Decimal("22")

    def test_add_iva_reduced_10(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_iva(Decimal("1000"), IVARate.REDUCED, "add_iva")
        assert result.iva_amount == Decimal("100.00")
        assert result.gross_amount_vat == Decimal("1100.00")

    def test_add_iva_super_reduced_4(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_iva(Decimal("1000"), IVARate.SUPER_REDUCED, "add_iva")
        assert result.iva_amount == Decimal("40.00")
        assert result.gross_amount_vat == Decimal("1040.00")

    def test_add_iva_exempt(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_iva(Decimal("1000"), IVARate.EXEMPT, "add_iva")
        assert result.iva_amount == Decimal("0.00")
        assert result.gross_amount_vat == Decimal("1000.00")

    def test_add_iva_zero_amount(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_iva(Decimal("0"), IVARate.STANDARD, "add_iva")
        assert result.iva_amount == Decimal("0.00")
        assert result.gross_amount_vat == Decimal("0.00")

    # --- extract_iva ---

    def test_extract_iva_standard(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_iva(Decimal("1220"), IVARate.STANDARD, "extract_iva")
        assert result.net_amount == Decimal("1000.00")
        assert result.iva_amount == Decimal("220.00")
        assert result.gross_amount_vat == Decimal("1220.00")

    def test_extract_iva_reduced(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_iva(Decimal("1100"), IVARate.REDUCED, "extract_iva")
        assert result.net_amount == Decimal("1000.00")
        assert result.iva_amount == Decimal("100.00")

    def test_extract_iva_super_reduced(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_iva(Decimal("1040"), IVARate.SUPER_REDUCED, "extract_iva")
        assert result.net_amount == Decimal("1000.00")
        assert result.iva_amount == Decimal("40.00")

    def test_extract_iva_exempt(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_iva(Decimal("1000"), IVARate.EXEMPT, "extract_iva")
        assert result.net_amount == Decimal("1000.00")
        assert result.iva_amount == Decimal("0.00")

    # --- Roundtrip consistency: add then extract ---

    def test_roundtrip_add_then_extract(self, calculator: ItalianTaxCalculator) -> None:
        added = calculator.calculate_iva(Decimal("500"), IVARate.STANDARD, "add_iva")
        extracted = calculator.calculate_iva(added.gross_amount_vat, IVARate.STANDARD, "extract_iva")
        assert extracted.net_amount == Decimal("500.00")

    # --- Error cases ---

    def test_negative_amount_raises(self, calculator: ItalianTaxCalculator) -> None:
        with pytest.raises(ValueError, match="Net amount cannot be negative"):
            calculator.calculate_iva(Decimal("-100"), IVARate.STANDARD)

    def test_invalid_rate_raises(self, calculator: ItalianTaxCalculator) -> None:
        with pytest.raises(ValueError, match="Invalid IVA rate"):
            calculator.calculate_iva(Decimal("1000"), "invalid_rate")  # type: ignore[arg-type]

    def test_invalid_calculation_type_raises(self, calculator: ItalianTaxCalculator) -> None:
        with pytest.raises(ValueError, match="Invalid calculation type"):
            calculator.calculate_iva(Decimal("1000"), IVARate.STANDARD, "multiply_iva")

    # --- Legacy compatibility fields ---

    def test_legacy_gross_amount_field(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_iva(Decimal("1000"), IVARate.STANDARD, "add_iva")
        assert result.gross_amount == result.gross_amount_vat

    def test_legacy_tax_amount_field(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_iva(Decimal("1000"), IVARate.STANDARD, "add_iva")
        assert result.tax_amount == result.iva_amount

    # --- Formula ---

    def test_add_iva_formula_populated(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_iva(Decimal("1000"), IVARate.STANDARD, "add_iva")
        assert "22%" in result.formula

    # --- Returns TaxResult ---

    def test_returns_tax_result(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_iva(Decimal("1000"), IVARate.STANDARD)
        assert isinstance(result, TaxResult)

    # --- Default calculation_type is add_iva ---

    def test_default_calculation_type_is_add_iva(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_iva(Decimal("1000"), IVARate.STANDARD)
        # Default should add IVA
        assert result.gross_amount_vat == Decimal("1220.00")


# ---------------------------------------------------------------------------
# 4. calculate_ires tests
# ---------------------------------------------------------------------------


class TestCalculateIres:
    """Tests for IRES (corporate income tax) calculation."""

    def test_standard_rate_24_percent(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_ires(Decimal("100000"))
        assert result.tax_amount == Decimal("24000.00")
        assert result.effective_rate == Decimal("24")
        assert result.rate_applied == Decimal("24")

    def test_startup_incentive_12_percent(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_ires(Decimal("100000"), startup_incentive=True)
        assert result.tax_amount == Decimal("12000.00")
        assert result.effective_rate == Decimal("12")
        assert result.rate_applied == Decimal("12")

    def test_zero_income(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_ires(Decimal("0"))
        assert result.tax_amount == Decimal("0.00")

    def test_negative_income_raises(self, calculator: ItalianTaxCalculator) -> None:
        with pytest.raises(ValueError, match="Taxable income cannot be negative"):
            calculator.calculate_ires(Decimal("-1"))

    def test_formula_standard(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_ires(Decimal("50000"))
        assert "IRES" in result.formula
        assert "24%" in result.formula

    def test_formula_startup(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_ires(Decimal("50000"), startup_incentive=True)
        assert "startup incentive" in result.formula

    def test_gross_amount_is_taxable_income(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_ires(Decimal("75000"))
        assert result.gross_amount == Decimal("75000")

    def test_returns_tax_result(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_ires(Decimal("100000"))
        assert isinstance(result, TaxResult)

    def test_small_amount_rounding(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_ires(Decimal("1"))
        # 1 * 24% = 0.24
        assert result.tax_amount == Decimal("0.24")


# ---------------------------------------------------------------------------
# 5. calculate_irap tests
# ---------------------------------------------------------------------------


class TestCalculateIrap:
    """Tests for IRAP (regional business tax) calculation."""

    def test_standard_rate_3_9_percent(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_irap(Decimal("100000"))
        # 100,000 * 3.9% = 3,900
        assert result.tax_amount == Decimal("3900.00")
        assert result.effective_rate == Decimal("3.9")
        assert result.rate_applied == Decimal("3.9")

    def test_with_deductions(self, calculator: ItalianTaxCalculator) -> None:
        deductions = [{"type": "employee_costs", "amount": Decimal("20000")}]
        result = calculator.calculate_irap(Decimal("100000"), deductions=deductions)
        # Taxable base = 100,000 - 20,000 = 80,000
        # 80,000 * 3.9% = 3,120
        assert result.taxable_base == Decimal("80000")
        assert result.taxable_income == Decimal("80000")
        assert result.tax_amount == Decimal("3120.00")
        assert result.deductions_applied == Decimal("20000")

    def test_with_multiple_deductions(self, calculator: ItalianTaxCalculator) -> None:
        deductions = [
            {"type": "employee_costs", "amount": Decimal("10000")},
            {"type": "other", "amount": Decimal("5000")},
        ]
        result = calculator.calculate_irap(Decimal("50000"), deductions=deductions)
        # Taxable base = 50,000 - 15,000 = 35,000
        # 35,000 * 3.9% = 1,365
        assert result.taxable_base == Decimal("35000")
        assert result.tax_amount == Decimal("1365.00")

    def test_deductions_exceeding_production_value(self, calculator: ItalianTaxCalculator) -> None:
        deductions = [{"type": "employee_costs", "amount": Decimal("150000")}]
        result = calculator.calculate_irap(Decimal("100000"), deductions=deductions)
        assert result.taxable_base == Decimal("0")
        assert result.tax_amount == Decimal("0.00")

    def test_zero_production_value(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_irap(Decimal("0"))
        assert result.tax_amount == Decimal("0.00")

    def test_negative_production_value_raises(self, calculator: ItalianTaxCalculator) -> None:
        with pytest.raises(ValueError, match="Production value cannot be negative"):
            calculator.calculate_irap(Decimal("-1"))

    def test_gross_amount_is_production_value(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_irap(Decimal("50000"))
        assert result.gross_amount == Decimal("50000")

    def test_formula_without_deductions(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_irap(Decimal("50000"))
        assert "IRAP" in result.formula
        assert "3.9%" in result.formula

    def test_formula_with_deductions(self, calculator: ItalianTaxCalculator) -> None:
        deductions = [{"type": "employee_costs", "amount": Decimal("10000")}]
        result = calculator.calculate_irap(Decimal("50000"), deductions=deductions)
        assert "deductions" in result.formula

    def test_returns_tax_result(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_irap(Decimal("100000"))
        assert isinstance(result, TaxResult)

    def test_no_deductions_default(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_irap(Decimal("100000"))
        assert result.deductions_applied == Decimal("0")
        assert result.taxable_base == Decimal("100000")


# ---------------------------------------------------------------------------
# 6. calculate_withholding_tax tests
# ---------------------------------------------------------------------------


class TestCalculateWithholdingTax:
    """Tests for withholding tax (Ritenuta d'Acconto)."""

    def test_standard_20_percent(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_withholding_tax(Decimal("5000"), "professional", Decimal("20"))
        assert result.withholding_amount == Decimal("1000.00")
        assert result.net_payment == Decimal("4000.00")
        assert result.rate_applied == Decimal("20")

    def test_different_rate(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_withholding_tax(Decimal("10000"), "other", Decimal("30"))
        assert result.withholding_amount == Decimal("3000.00")
        assert result.net_payment == Decimal("7000.00")

    def test_zero_amount(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_withholding_tax(Decimal("0"), "professional", Decimal("20"))
        assert result.withholding_amount == Decimal("0.00")
        assert result.net_payment == Decimal("0.00")

    def test_negative_amount_raises(self, calculator: ItalianTaxCalculator) -> None:
        with pytest.raises(ValueError, match="Gross amount cannot be negative"):
            calculator.calculate_withholding_tax(Decimal("-100"), "professional", Decimal("20"))

    def test_tax_amount_equals_withholding(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_withholding_tax(Decimal("5000"), "professional", Decimal("20"))
        assert result.tax_amount == result.withholding_amount

    def test_gross_amount_stored(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_withholding_tax(Decimal("5000"), "professional", Decimal("20"))
        assert result.gross_amount == Decimal("5000")

    def test_effective_rate_matches(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_withholding_tax(Decimal("5000"), "professional", Decimal("20"))
        assert result.effective_rate == Decimal("20")

    def test_formula_populated(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_withholding_tax(Decimal("5000"), "professional", Decimal("20"))
        assert "Ritenuta" in result.formula
        assert "20%" in result.formula

    def test_returns_tax_result(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_withholding_tax(Decimal("5000"), "professional", Decimal("20"))
        assert isinstance(result, TaxResult)

    def test_small_fractional_amount(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_withholding_tax(Decimal("33.33"), "professional", Decimal("20"))
        # 33.33 * 20% = 6.666 -> 6.67 (rounding)
        assert result.withholding_amount == Decimal("6.67")
        assert result.net_payment == Decimal("26.66")


# ---------------------------------------------------------------------------
# 7. calculate_complete_individual_taxes tests
# ---------------------------------------------------------------------------


class TestCalculateCompleteIndividualTaxes:
    """Tests for full individual tax burden calculation."""

    def test_returns_dict(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_complete_individual_taxes(Decimal("50000"))
        assert isinstance(result, dict)

    def test_contains_irpef_key(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_complete_individual_taxes(Decimal("50000"))
        assert "irpef" in result
        assert "amount" in result["irpef"]
        assert "rate" in result["irpef"]
        assert "taxable_income" in result["irpef"]

    def test_contains_regional_tax_key(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_complete_individual_taxes(Decimal("50000"))
        assert "regional_tax" in result
        assert "amount" in result["regional_tax"]
        assert "rate" in result["regional_tax"]

    def test_contains_municipal_tax_key(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_complete_individual_taxes(Decimal("50000"))
        assert "municipal_tax" in result
        assert "amount" in result["municipal_tax"]
        assert "rate" in result["municipal_tax"]

    def test_contains_total_tax_key(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_complete_individual_taxes(Decimal("50000"))
        assert "total_tax" in result
        assert "amount" in result["total_tax"]
        assert "effective_rate" in result["total_tax"]

    def test_contains_calculation_summary(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_complete_individual_taxes(Decimal("50000"))
        assert "calculation_summary" in result
        assert isinstance(result["calculation_summary"], list)
        assert len(result["calculation_summary"]) == 4

    def test_regional_rate_1_73(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_complete_individual_taxes(Decimal("50000"))
        assert result["regional_tax"]["rate"] == Decimal("1.73")

    def test_municipal_rate_0_60(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_complete_individual_taxes(Decimal("50000"))
        assert result["municipal_tax"]["rate"] == Decimal("0.60")

    def test_regional_tax_amount(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_complete_individual_taxes(Decimal("50000"))
        # Taxable income = 50,000 (no deductions)
        # Regional: 50,000 * 1.73% = 865.00
        assert result["regional_tax"]["amount"] == Decimal("865.00")

    def test_municipal_tax_amount(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_complete_individual_taxes(Decimal("50000"))
        # Municipal: 50,000 * 0.60% = 300.00
        assert result["municipal_tax"]["amount"] == Decimal("300.00")

    def test_total_is_sum_of_components(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_complete_individual_taxes(Decimal("50000"))
        irpef_amount = result["irpef"]["amount"]
        regional_amount = result["regional_tax"]["amount"]
        municipal_amount = result["municipal_tax"]["amount"]
        expected_total = (irpef_amount + regional_amount + municipal_amount).quantize(Decimal("0.01"))
        assert result["total_tax"]["amount"] == expected_total

    def test_with_deductions_reduces_all_taxes(self, calculator: ItalianTaxCalculator) -> None:
        deductions = [{"type": DeductionType.EMPLOYEE, "amount": Decimal("10000")}]
        result = calculator.calculate_complete_individual_taxes(Decimal("50000"), deductions=deductions)
        # Taxable: 40,000
        assert result["irpef"]["taxable_income"] == Decimal("40000")
        # Regional on 40k: 40,000 * 1.73% = 692.00
        assert result["regional_tax"]["amount"] == Decimal("692.00")

    def test_with_tax_credits(self, calculator: ItalianTaxCalculator) -> None:
        credits = [{"type": TaxCreditType.WORK, "amount": Decimal("1000")}]
        result = calculator.calculate_complete_individual_taxes(Decimal("50000"), tax_credits=credits)
        # IRPEF should be reduced by credits, but regional/municipal are not
        # IRPEF on 50k = 14,400 - 1,000 = 13,400
        assert result["irpef"]["amount"] == Decimal("13400.00")

    def test_irpef_amount_matches_standalone(self, calculator: ItalianTaxCalculator) -> None:
        standalone = calculator.calculate_irpef(Decimal("50000"))
        complete = calculator.calculate_complete_individual_taxes(Decimal("50000"))
        assert complete["irpef"]["amount"] == standalone.tax_amount

    def test_effective_rate_calculation(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_complete_individual_taxes(Decimal("50000"))
        total = result["total_tax"]["amount"]
        expected_rate = (total / Decimal("50000") * 100).quantize(Decimal("0.01"))
        assert result["total_tax"]["effective_rate"] == expected_rate


# ---------------------------------------------------------------------------
# 8. calculate_complete_company_taxes tests
# ---------------------------------------------------------------------------


class TestCalculateCompleteCompanyTaxes:
    """Tests for full company tax burden calculation."""

    def test_returns_dict(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_complete_company_taxes(Decimal("200000"), Decimal("300000"))
        assert isinstance(result, dict)

    def test_contains_ires_key(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_complete_company_taxes(Decimal("200000"), Decimal("300000"))
        assert "ires" in result
        assert "amount" in result["ires"]
        assert "rate" in result["ires"]
        assert "taxable_income" in result["ires"]

    def test_contains_irap_key(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_complete_company_taxes(Decimal("200000"), Decimal("300000"))
        assert "irap" in result
        assert "amount" in result["irap"]
        assert "rate" in result["irap"]
        assert "production_value" in result["irap"]

    def test_contains_total_tax_key(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_complete_company_taxes(Decimal("200000"), Decimal("300000"))
        assert "total_tax" in result
        assert "amount" in result["total_tax"]
        assert "effective_rate" in result["total_tax"]

    def test_ires_amount_correct(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_complete_company_taxes(Decimal("200000"), Decimal("300000"))
        # IRES: 200,000 * 24% = 48,000
        assert result["ires"]["amount"] == Decimal("48000.00")
        assert result["ires"]["rate"] == Decimal("24")

    def test_irap_amount_correct(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_complete_company_taxes(Decimal("200000"), Decimal("300000"))
        # IRAP: 300,000 * 3.9% = 11,700
        assert result["irap"]["amount"] == Decimal("11700.00")
        assert result["irap"]["rate"] == Decimal("3.9")

    def test_total_is_sum_ires_irap(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_complete_company_taxes(Decimal("200000"), Decimal("300000"))
        # Total = 48,000 + 11,700 = 59,700
        expected_total = Decimal("59700.00")
        assert result["total_tax"]["amount"] == expected_total

    def test_effective_rate_based_on_taxable_income(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_complete_company_taxes(Decimal("200000"), Decimal("300000"))
        total = result["total_tax"]["amount"]
        expected_rate = (total / Decimal("200000") * 100).quantize(Decimal("0.01"))
        assert result["total_tax"]["effective_rate"] == expected_rate

    def test_ires_matches_standalone(self, calculator: ItalianTaxCalculator) -> None:
        standalone = calculator.calculate_ires(Decimal("200000"))
        complete = calculator.calculate_complete_company_taxes(Decimal("200000"), Decimal("300000"))
        assert complete["ires"]["amount"] == standalone.tax_amount

    def test_irap_matches_standalone(self, calculator: ItalianTaxCalculator) -> None:
        standalone = calculator.calculate_irap(Decimal("300000"))
        complete = calculator.calculate_complete_company_taxes(Decimal("200000"), Decimal("300000"))
        assert complete["irap"]["amount"] == standalone.tax_amount

    def test_taxable_income_stored(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_complete_company_taxes(Decimal("200000"), Decimal("300000"))
        assert result["ires"]["taxable_income"] == Decimal("200000")

    def test_production_value_stored(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_complete_company_taxes(Decimal("200000"), Decimal("300000"))
        assert result["irap"]["production_value"] == Decimal("300000")

    def test_equal_income_and_production(self, calculator: ItalianTaxCalculator) -> None:
        result = calculator.calculate_complete_company_taxes(Decimal("100000"), Decimal("100000"))
        # IRES: 100k * 24% = 24,000
        # IRAP: 100k * 3.9% = 3,900
        # Total = 27,900
        assert result["total_tax"]["amount"] == Decimal("27900.00")


# ---------------------------------------------------------------------------
# Cross-cutting / TaxResult dataclass tests
# ---------------------------------------------------------------------------


class TestTaxResultDataclass:
    """Verify TaxResult field defaults and structure."""

    def test_default_deductions_applied_zero(self) -> None:
        result = TaxResult(
            gross_amount=Decimal("100"),
            tax_amount=Decimal("10"),
            effective_rate=Decimal("10"),
        )
        assert result.deductions_applied == Decimal("0")

    def test_default_tax_credits_applied_zero(self) -> None:
        result = TaxResult(
            gross_amount=Decimal("100"),
            tax_amount=Decimal("10"),
            effective_rate=Decimal("10"),
        )
        assert result.tax_credits_applied == Decimal("0")

    def test_optional_fields_default_none(self) -> None:
        result = TaxResult(
            gross_amount=Decimal("100"),
            tax_amount=Decimal("10"),
            effective_rate=Decimal("10"),
        )
        assert result.taxable_income is None
        assert result.net_amount is None
        assert result.iva_amount is None
        assert result.gross_amount_vat is None
        assert result.rate_applied is None
        assert result.withholding_amount is None
        assert result.net_payment is None
        assert result.taxable_base is None

    def test_calculation_steps_default_empty_list(self) -> None:
        result = TaxResult(
            gross_amount=Decimal("100"),
            tax_amount=Decimal("10"),
            effective_rate=Decimal("10"),
        )
        assert result.calculation_steps == []

    def test_formula_default_empty_string(self) -> None:
        result = TaxResult(
            gross_amount=Decimal("100"),
            tax_amount=Decimal("10"),
            effective_rate=Decimal("10"),
        )
        assert result.formula == ""


# ---------------------------------------------------------------------------
# Enum tests
# ---------------------------------------------------------------------------


class TestEnums:
    """Verify enum members exist with expected values."""

    def test_iva_rate_standard(self) -> None:
        assert IVARate.STANDARD.value == "standard"

    def test_iva_rate_reduced(self) -> None:
        assert IVARate.REDUCED.value == "reduced_10"

    def test_iva_rate_super_reduced(self) -> None:
        assert IVARate.SUPER_REDUCED.value == "reduced_4"

    def test_iva_rate_exempt(self) -> None:
        assert IVARate.EXEMPT.value == "exempt"

    def test_tax_credit_type_members(self) -> None:
        assert TaxCreditType.SPOUSE.value == "spouse"
        assert TaxCreditType.CHILD.value == "child"
        assert TaxCreditType.WORK.value == "work"
        assert TaxCreditType.PENSION.value == "pension"

    def test_deduction_type_members(self) -> None:
        assert DeductionType.EMPLOYEE.value == "employee"
        assert DeductionType.SPOUSE.value == "spouse"
        assert DeductionType.CHILD.value == "child"
        assert DeductionType.MEDICAL.value == "medical"
        assert DeductionType.RENOVATION.value == "renovation"
        assert DeductionType.PENSION.value == "pension"
