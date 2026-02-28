"""Comprehensive tests for the Italian Tax Calculator Service.

Tests all pure-computation calculator classes in app/services/italian_tax_calculator.py:
- IrpefCalculator
- InpsCalculator
- VatCalculator
- CorporateTaxCalculator
- CapitalGainsTaxCalculator
- TaxDeductionEngine
- FreelancerTaxCalculator
- TaxOptimizationEngine

No mocking needed -- all classes under test are pure computation (no DB, no async).
"""

from decimal import Decimal

import pytest

from app.services.italian_tax_calculator import (
    CapitalGainsTaxCalculator,
    CorporateTaxCalculator,
    FreelancerTaxCalculator,
    InpsCalculator,
    InvalidIncomeError,
    InvalidTaxTypeError,
    IrpefCalculator,
    TaxDeductionEngine,
    TaxOptimizationEngine,
    VatCalculator,
)


# ---------------------------------------------------------------------------
# IrpefCalculator
# ---------------------------------------------------------------------------
class TestIrpefCalculator:
    """Tests for IrpefCalculator progressive-bracket income tax."""

    @pytest.fixture()
    def calculator(self) -> IrpefCalculator:
        return IrpefCalculator()

    # -- calculate_irpef: happy path --

    def test_income_in_first_bracket(self, calculator: IrpefCalculator) -> None:
        """Income <= 15 000 is taxed entirely at 23 %."""
        result = calculator.calculate_irpef(Decimal("10000"))
        assert result["gross_tax"] == Decimal("2300.00")
        assert result["marginal_rate"] == Decimal("23")
        assert len(result["bracket_details"]) == 1

    def test_income_at_first_bracket_boundary(self, calculator: IrpefCalculator) -> None:
        """Income == 15 000 exactly."""
        result = calculator.calculate_irpef(Decimal("15000"))
        assert result["gross_tax"] == Decimal("3450.00")
        assert result["marginal_rate"] == Decimal("23")

    def test_income_in_second_bracket(self, calculator: IrpefCalculator) -> None:
        """Income between 15 001 and 28 000 uses two brackets."""
        result = calculator.calculate_irpef(Decimal("20000"))
        # 15000 * 0.23 = 3450, 5000 * 0.25 = 1250 => 4700
        assert result["gross_tax"] == Decimal("4700.00")
        assert result["marginal_rate"] == Decimal("25")
        assert len(result["bracket_details"]) == 2

    def test_income_at_second_bracket_boundary(self, calculator: IrpefCalculator) -> None:
        """Income == 28 000 exactly."""
        result = calculator.calculate_irpef(Decimal("28000"))
        # 15000 * 0.23 = 3450, 13000 * 0.25 = 3250 => 6700
        assert result["gross_tax"] == Decimal("6700.00")

    def test_income_in_third_bracket(self, calculator: IrpefCalculator) -> None:
        """Income between 28 001 and 55 000."""
        result = calculator.calculate_irpef(Decimal("40000"))
        # 15000*0.23 = 3450, 13000*0.25 = 3250, 12000*0.35 = 4200 => 10900
        assert result["gross_tax"] == Decimal("10900.00")
        assert result["marginal_rate"] == Decimal("35")
        assert len(result["bracket_details"]) == 3

    def test_income_at_third_bracket_boundary(self, calculator: IrpefCalculator) -> None:
        """Income == 55 000 exactly."""
        result = calculator.calculate_irpef(Decimal("55000"))
        # 3450 + 3250 + 27000*0.35 = 3450 + 3250 + 9450 = 16150
        assert result["gross_tax"] == Decimal("16150.00")
        assert result["marginal_rate"] == Decimal("35")

    def test_income_in_fourth_bracket(self, calculator: IrpefCalculator) -> None:
        """Income above 55 000 uses all four brackets."""
        result = calculator.calculate_irpef(Decimal("100000"))
        # 3450 + 3250 + 9450 + 45000*0.43 = 3450 + 3250 + 9450 + 19350 = 35500
        assert result["gross_tax"] == Decimal("35500.00")
        assert result["marginal_rate"] == Decimal("43")
        assert len(result["bracket_details"]) == 4

    def test_effective_rate(self, calculator: IrpefCalculator) -> None:
        """Effective rate is tax / income * 100, rounded to 2 dp."""
        result = calculator.calculate_irpef(Decimal("100000"))
        expected_effective = (Decimal("35500") / Decimal("100000") * 100).quantize(Decimal("0.01"))
        assert result["effective_rate"] == expected_effective

    def test_brackets_used_keys(self, calculator: IrpefCalculator) -> None:
        """brackets_used contains lowered, underscored bracket descriptions."""
        result = calculator.calculate_irpef(Decimal("20000"))
        for key in result["brackets_used"]:
            assert " " not in key
            assert key == key.lower()

    # -- calculate_irpef: zero income --

    def test_zero_income(self, calculator: IrpefCalculator) -> None:
        result = calculator.calculate_irpef(Decimal("0"))
        assert result["gross_tax"] == Decimal("0")
        assert result["effective_rate"] == Decimal("0")
        assert result["marginal_rate"] == Decimal("0")
        assert result["brackets_used"] == []
        assert result["bracket_details"] == []

    # -- calculate_irpef: error cases --

    def test_negative_income_raises(self, calculator: IrpefCalculator) -> None:
        with pytest.raises(InvalidIncomeError):
            calculator.calculate_irpef(Decimal("-1"))

    # -- calculate_irpef_with_deductions --

    def test_deductions_reduce_taxable_income(self, calculator: IrpefCalculator) -> None:
        deductions = {"pension": Decimal("3000"), "medical": Decimal("2000")}
        result = calculator.calculate_irpef_with_deductions(Decimal("30000"), deductions)
        assert result["total_deductions"] == Decimal("5000")
        assert result["taxable_income"] == Decimal("25000")
        # Tax on 25000: 15000*0.23 + 10000*0.25 = 3450 + 2500 = 5950
        assert result["net_tax"] == Decimal("5950.00")

    def test_deductions_exceeding_income(self, calculator: IrpefCalculator) -> None:
        """Deductions > income => taxable income clamped to 0."""
        deductions = {"big": Decimal("50000")}
        result = calculator.calculate_irpef_with_deductions(Decimal("10000"), deductions)
        assert result["taxable_income"] == Decimal("0")
        assert result["net_tax"] == Decimal("0")

    def test_deductions_tax_savings(self, calculator: IrpefCalculator) -> None:
        deductions = {"pension": Decimal("5000")}
        result = calculator.calculate_irpef_with_deductions(Decimal("30000"), deductions)
        gross_full = calculator.calculate_irpef(Decimal("30000"))["gross_tax"]
        gross_reduced = calculator.calculate_irpef(Decimal("25000"))["gross_tax"]
        assert result["tax_savings"] == gross_full - gross_reduced

    # -- _get_marginal_rate --

    def test_marginal_rate_first_bracket(self, calculator: IrpefCalculator) -> None:
        assert calculator._get_marginal_rate(Decimal("5000")) == Decimal("23")

    def test_marginal_rate_second_bracket(self, calculator: IrpefCalculator) -> None:
        assert calculator._get_marginal_rate(Decimal("20000")) == Decimal("25")

    def test_marginal_rate_third_bracket(self, calculator: IrpefCalculator) -> None:
        assert calculator._get_marginal_rate(Decimal("40000")) == Decimal("35")

    def test_marginal_rate_fourth_bracket(self, calculator: IrpefCalculator) -> None:
        assert calculator._get_marginal_rate(Decimal("80000")) == Decimal("43")

    def test_very_high_income(self, calculator: IrpefCalculator) -> None:
        """Very large income still hits 43 % top bracket."""
        result = calculator.calculate_irpef(Decimal("1000000"))
        assert result["marginal_rate"] == Decimal("43")
        # 15000*0.23 + 13000*0.25 + 27000*0.35 + 945000*0.43
        # = 3450 + 3250 + 9450 + 406350 = 422500
        assert result["gross_tax"] == Decimal("422500.00")


# ---------------------------------------------------------------------------
# InpsCalculator
# ---------------------------------------------------------------------------
class TestInpsCalculator:
    """Tests for INPS social security contribution calculations."""

    @pytest.fixture()
    def calculator(self) -> InpsCalculator:
        return InpsCalculator()

    # -- Employee contribution --

    def test_employee_contribution_below_ceiling(self, calculator: InpsCalculator) -> None:
        result = calculator.calculate_employee_contribution(Decimal("40000"))
        # 40000 * 9.19 / 100 = 3676.00
        assert result["employee_contribution"] == Decimal("3676.00")
        assert result["contribution_base"] == Decimal("40000")

    def test_employee_contribution_above_ceiling(self, calculator: InpsCalculator) -> None:
        """Contribution base capped at ceiling 119 650."""
        result = calculator.calculate_employee_contribution(Decimal("200000"))
        # contribution_base = 119650
        assert result["contribution_base"] == Decimal("119650")
        expected = (Decimal("119650") * Decimal("9.19") / 100).quantize(Decimal("0.01"))
        assert result["employee_contribution"] == expected

    def test_employee_contribution_zero(self, calculator: InpsCalculator) -> None:
        result = calculator.calculate_employee_contribution(Decimal("0"))
        assert result["employee_contribution"] == Decimal("0.00")

    def test_employee_contribution_negative_raises(self, calculator: InpsCalculator) -> None:
        with pytest.raises(InvalidIncomeError):
            calculator.calculate_employee_contribution(Decimal("-1"))

    def test_employee_pension_and_other_split(self, calculator: InpsCalculator) -> None:
        result = calculator.calculate_employee_contribution(Decimal("50000"))
        total = result["employee_contribution"]
        assert result["pension_contribution"] == total * Decimal("0.8")
        assert result["other_contributions"] == total * Decimal("0.2")

    # -- Employer contribution --

    def test_employer_contribution(self, calculator: InpsCalculator) -> None:
        result = calculator.calculate_employer_contribution(Decimal("40000"))
        # 40000 * 30 / 100 = 12000
        assert result["employer_contribution"] == Decimal("12000.00")
        assert result["total_cost"] == Decimal("40000") + Decimal("12000")

    def test_employer_contribution_zero(self, calculator: InpsCalculator) -> None:
        result = calculator.calculate_employer_contribution(Decimal("0"))
        assert result["employer_contribution"] == Decimal("0.00")

    def test_employer_contribution_negative_raises(self, calculator: InpsCalculator) -> None:
        with pytest.raises(InvalidIncomeError):
            calculator.calculate_employer_contribution(Decimal("-100"))

    # -- Executive contribution --

    def test_executive_below_ceiling(self, calculator: InpsCalculator) -> None:
        result = calculator.calculate_executive_contribution(Decimal("80000"))
        # 80000 * 10 / 100 = 8000
        assert result["total_contribution"] == Decimal("8000.00")
        assert result["rate_used"] == Decimal("10.00")

    def test_executive_above_ceiling(self, calculator: InpsCalculator) -> None:
        """Two-tier rate above the 103 055 ceiling."""
        result = calculator.calculate_executive_contribution(Decimal("150000"))
        ceiling = Decimal("103055")
        first = ceiling * Decimal("10") / 100
        second = (Decimal("150000") - ceiling) * Decimal("3") / 100
        expected = (first + second).quantize(Decimal("0.01"))
        assert result["total_contribution"] == expected
        assert result["rate_used"] == "variable"

    def test_executive_at_ceiling(self, calculator: InpsCalculator) -> None:
        result = calculator.calculate_executive_contribution(Decimal("103055"))
        assert result["rate_used"] == Decimal("10.00")

    def test_executive_negative_raises(self, calculator: InpsCalculator) -> None:
        with pytest.raises(InvalidIncomeError):
            calculator.calculate_executive_contribution(Decimal("-5"))

    # -- Self-employed contribution --

    def test_self_employed_contribution(self, calculator: InpsCalculator) -> None:
        result = calculator.calculate_self_employed_contribution(Decimal("60000"))
        # 60000 * 25.98 / 100 = 15588
        assert result["contribution"] == Decimal("15588.00")
        assert result["regime"] == "separate_social_security"

    def test_self_employed_zero(self, calculator: InpsCalculator) -> None:
        result = calculator.calculate_self_employed_contribution(Decimal("0"))
        assert result["contribution"] == Decimal("0.00")

    def test_self_employed_negative_raises(self, calculator: InpsCalculator) -> None:
        with pytest.raises(InvalidIncomeError):
            calculator.calculate_self_employed_contribution(Decimal("-1"))

    def test_self_employed_alternative_rates_present(self, calculator: InpsCalculator) -> None:
        result = calculator.calculate_self_employed_contribution(Decimal("10000"))
        alt = result["alternative_rates"]
        assert "exclusive_coverage" in alt
        assert "with_dis_coll" in alt
        assert "without_dis_coll" in alt


# ---------------------------------------------------------------------------
# VatCalculator
# ---------------------------------------------------------------------------
class TestVatCalculator:
    """Tests for VAT (IVA) calculations."""

    @pytest.fixture()
    def calculator(self) -> VatCalculator:
        return VatCalculator()

    # -- calculate_vat: happy paths --

    def test_standard_vat(self, calculator: VatCalculator) -> None:
        result = calculator.calculate_vat(Decimal("1000"), "standard")
        assert result["vat_rate"] == Decimal("22")
        assert result["vat_amount"] == Decimal("220.00")
        assert result["gross_amount"] == Decimal("1220.00")

    def test_reduced_10_vat(self, calculator: VatCalculator) -> None:
        result = calculator.calculate_vat(Decimal("500"), "reduced_10")
        assert result["vat_amount"] == Decimal("50.00")
        assert result["gross_amount"] == Decimal("550.00")

    def test_reduced_4_vat(self, calculator: VatCalculator) -> None:
        result = calculator.calculate_vat(Decimal("1000"), "reduced_4")
        assert result["vat_amount"] == Decimal("40.00")
        assert result["gross_amount"] == Decimal("1040.00")

    def test_exempt_vat(self, calculator: VatCalculator) -> None:
        result = calculator.calculate_vat(Decimal("1000"), "exempt")
        assert result["vat_amount"] == Decimal("0.00")
        assert result["gross_amount"] == Decimal("1000.00")
        assert result["exemption_reason"] == "VAT exempt category"

    def test_vat_zero_amount(self, calculator: VatCalculator) -> None:
        result = calculator.calculate_vat(Decimal("0"), "standard")
        assert result["vat_amount"] == Decimal("0.00")
        assert result["gross_amount"] == Decimal("0.00")

    # -- calculate_vat: error cases --

    def test_vat_negative_amount_raises(self, calculator: VatCalculator) -> None:
        with pytest.raises(ValueError, match="negative"):
            calculator.calculate_vat(Decimal("-10"), "standard")

    def test_vat_invalid_category_raises(self, calculator: VatCalculator) -> None:
        with pytest.raises(InvalidTaxTypeError):
            calculator.calculate_vat(Decimal("100"), "nonexistent")

    # -- calculate_reverse_vat --

    def test_reverse_vat_standard(self, calculator: VatCalculator) -> None:
        result = calculator.calculate_reverse_vat(Decimal("1220"), "standard")
        assert result["net_amount"] == pytest.approx(Decimal("1000.00"), abs=Decimal("0.01"))
        assert result["vat_amount"] == pytest.approx(Decimal("220.00"), abs=Decimal("0.01"))

    def test_reverse_vat_exempt(self, calculator: VatCalculator) -> None:
        result = calculator.calculate_reverse_vat(Decimal("1000"), "exempt")
        assert result["net_amount"] == Decimal("1000.00")
        assert result["vat_amount"] == Decimal("0.00")

    def test_reverse_vat_negative_raises(self, calculator: VatCalculator) -> None:
        with pytest.raises(ValueError, match="negative"):
            calculator.calculate_reverse_vat(Decimal("-1"), "standard")

    def test_reverse_vat_invalid_category_raises(self, calculator: VatCalculator) -> None:
        with pytest.raises(InvalidTaxTypeError):
            calculator.calculate_reverse_vat(Decimal("100"), "bogus")

    def test_reverse_vat_round_trip(self, calculator: VatCalculator) -> None:
        """Forward VAT then reverse should recover original net amount."""
        forward = calculator.calculate_vat(Decimal("1500"), "reduced_10")
        reverse = calculator.calculate_reverse_vat(forward["gross_amount"], "reduced_10")
        assert reverse["net_amount"] == pytest.approx(Decimal("1500.00"), abs=Decimal("0.01"))

    # -- calculate_eu_vat --

    def test_eu_vat_consulting_service_reverse_charge(self, calculator: VatCalculator) -> None:
        result = calculator.calculate_eu_vat(Decimal("5000"), "IT", "DE", "consulting")
        assert result["vat_treatment"] == "reverse_charge"
        assert result["italian_vat"] == Decimal("0")
        assert result["foreign_vat_applicable"] is True

    def test_eu_vat_legal_service_reverse_charge(self, calculator: VatCalculator) -> None:
        result = calculator.calculate_eu_vat(Decimal("3000"), "IT", "FR", "legal")
        assert result["vat_treatment"] == "reverse_charge"

    def test_eu_vat_technical_service_reverse_charge(self, calculator: VatCalculator) -> None:
        result = calculator.calculate_eu_vat(Decimal("7000"), "IT", "ES", "technical")
        assert result["vat_treatment"] == "reverse_charge"
        assert "note" in result

    def test_eu_vat_standard_goods(self, calculator: VatCalculator) -> None:
        result = calculator.calculate_eu_vat(Decimal("2000"), "IT", "DE", "standard")
        assert result["vat_treatment"] == "reverse_charge"
        assert result["origin_country"] == "IT"
        assert result["destination_country"] == "DE"

    def test_eu_vat_negative_raises(self, calculator: VatCalculator) -> None:
        with pytest.raises(ValueError, match="negative"):
            calculator.calculate_eu_vat(Decimal("-1"), "IT", "DE")


# ---------------------------------------------------------------------------
# CorporateTaxCalculator
# ---------------------------------------------------------------------------
class TestCorporateTaxCalculator:
    """Tests for IRES and IRAP corporate taxes."""

    @pytest.fixture()
    def calculator(self) -> CorporateTaxCalculator:
        return CorporateTaxCalculator()

    # -- IRES --

    def test_ires_standard(self, calculator: CorporateTaxCalculator) -> None:
        result = calculator.calculate_ires(Decimal("500000"))
        # 500000 * 24 / 100 = 120000
        assert result["ires_tax"] == Decimal("120000.00")
        assert result["tax_rate"] == Decimal("24")

    def test_ires_zero(self, calculator: CorporateTaxCalculator) -> None:
        result = calculator.calculate_ires(Decimal("0"))
        assert result["ires_tax"] == Decimal("0.00")

    def test_ires_negative_raises(self, calculator: CorporateTaxCalculator) -> None:
        with pytest.raises(InvalidIncomeError):
            calculator.calculate_ires(Decimal("-1000"))

    def test_ires_includes_reduced_rate_2025(self, calculator: CorporateTaxCalculator) -> None:
        result = calculator.calculate_ires(Decimal("100000"))
        assert result["reduced_rate_2025"] == Decimal("20")

    # -- IRAP --

    def test_irap_standard(self, calculator: CorporateTaxCalculator) -> None:
        result = calculator.calculate_irap(Decimal("200000"), "Lombardia")
        # 200000 * 3.9 / 100 = 7800
        assert result["irap_tax"] == Decimal("7800.00")
        assert result["tax_rate"] == Decimal("3.9")

    def test_irap_banking_type(self, calculator: CorporateTaxCalculator) -> None:
        result = calculator.calculate_irap(Decimal("200000"), "Lombardia", "banking")
        # 200000 * 4.65 / 100 = 9300
        assert result["irap_tax"] == Decimal("9300.00")
        assert result["tax_rate"] == Decimal("4.65")

    def test_irap_unknown_type_falls_back_to_standard(self, calculator: CorporateTaxCalculator) -> None:
        result = calculator.calculate_irap(Decimal("100000"), "Lazio", "artisanal")
        assert result["tax_rate"] == Decimal("3.9")

    def test_irap_zero(self, calculator: CorporateTaxCalculator) -> None:
        result = calculator.calculate_irap(Decimal("0"), "Lombardia")
        assert result["irap_tax"] == Decimal("0.00")

    def test_irap_negative_raises(self, calculator: CorporateTaxCalculator) -> None:
        with pytest.raises(InvalidIncomeError):
            calculator.calculate_irap(Decimal("-100"), "Roma")

    # -- Combined --

    def test_combined_corporate_tax(self, calculator: CorporateTaxCalculator) -> None:
        result = calculator.calculate_combined_corporate_tax(
            Decimal("500000"), Decimal("500000"), "Lombardia", "standard"
        )
        assert result["ires_tax"] == Decimal("120000.00")
        assert result["irap_tax"] == Decimal("19500.00")
        assert result["total_corporate_tax"] == Decimal("139500.00")

    def test_combined_effective_rate(self, calculator: CorporateTaxCalculator) -> None:
        result = calculator.calculate_combined_corporate_tax(
            Decimal("100000"), Decimal("100000"), "Lombardia", "standard"
        )
        # IRES: 24000, IRAP: 3900, total: 27900
        expected_rate = (Decimal("27900") / Decimal("100000") * 100).quantize(Decimal("0.01"))
        assert result["effective_rate"] == expected_rate

    def test_combined_zero_income(self, calculator: CorporateTaxCalculator) -> None:
        result = calculator.calculate_combined_corporate_tax(Decimal("0"), Decimal("0"), "Lombardia")
        assert result["total_corporate_tax"] == Decimal("0.00")
        assert result["effective_rate"] == Decimal("0")


# ---------------------------------------------------------------------------
# CapitalGainsTaxCalculator
# ---------------------------------------------------------------------------
class TestCapitalGainsTaxCalculator:
    """Tests for capital gains tax on various asset types."""

    @pytest.fixture()
    def calculator(self) -> CapitalGainsTaxCalculator:
        return CapitalGainsTaxCalculator()

    # -- Financial gains --

    def test_financial_gain(self, calculator: CapitalGainsTaxCalculator) -> None:
        result = calculator.calculate_capital_gains_tax(Decimal("10000"), Decimal("15000"), "financial")
        # Gain = 5000, tax = 5000 * 26 / 100 = 1300
        assert result["capital_gain"] == Decimal("5000")
        assert result["tax_amount"] == Decimal("1300.00")
        assert result["tax_rate"] == Decimal("26")

    def test_financial_no_gain(self, calculator: CapitalGainsTaxCalculator) -> None:
        result = calculator.calculate_capital_gains_tax(Decimal("10000"), Decimal("10000"), "financial")
        assert result["tax_amount"] == Decimal("0")
        assert result["note"] == "No gain or loss - no tax due"

    def test_financial_loss(self, calculator: CapitalGainsTaxCalculator) -> None:
        result = calculator.calculate_capital_gains_tax(Decimal("15000"), Decimal("10000"), "financial")
        assert result["tax_amount"] == Decimal("0")
        assert result["capital_gain"] == Decimal("-5000")

    # -- Real estate gains --

    def test_real_estate_short_hold(self, calculator: CapitalGainsTaxCalculator) -> None:
        """Real estate sold within 5 years is taxed."""
        result = calculator.calculate_capital_gains_tax(
            Decimal("200000"), Decimal("300000"), "real_estate", holding_period_days=365
        )
        assert result["tax_amount"] == Decimal("26000.00")

    def test_real_estate_long_hold_exempt(self, calculator: CapitalGainsTaxCalculator) -> None:
        """Real estate held >= 1825 days (5 years) is exempt."""
        result = calculator.calculate_capital_gains_tax(
            Decimal("200000"), Decimal("300000"), "real_estate", holding_period_days=1825
        )
        assert result["tax_amount"] == Decimal("0")
        assert result["exemption"] is True
        assert result["exemption_reason"] == "long_term_holding"

    def test_real_estate_exactly_at_exemption_boundary(self, calculator: CapitalGainsTaxCalculator) -> None:
        """Holding period == exemption_period_days triggers exemption."""
        result = calculator.calculate_capital_gains_tax(
            Decimal("100000"), Decimal("150000"), "real_estate", holding_period_days=1825
        )
        assert result["exemption"] is True

    # -- Cryptocurrency gains --

    def test_crypto_above_threshold(self, calculator: CapitalGainsTaxCalculator) -> None:
        """Gain above 2000 threshold is taxed."""
        result = calculator.calculate_capital_gains_tax(Decimal("1000"), Decimal("5000"), "cryptocurrency")
        # Gain = 4000, above 2000 threshold
        assert result["tax_amount"] == Decimal("1040.00")
        assert result["tax_rate"] == Decimal("26")

    def test_crypto_below_threshold_exempt(self, calculator: CapitalGainsTaxCalculator) -> None:
        """Gain <= 2000 threshold is exempt."""
        result = calculator.calculate_capital_gains_tax(Decimal("1000"), Decimal("2500"), "cryptocurrency")
        # Gain = 1500, below 2000 threshold
        assert result["tax_amount"] == Decimal("0")
        assert result["exemption"] is True
        assert result["exemption_reason"] == "below_threshold"

    def test_crypto_at_threshold_exempt(self, calculator: CapitalGainsTaxCalculator) -> None:
        """Gain == threshold is still exempt (<=)."""
        result = calculator.calculate_capital_gains_tax(Decimal("1000"), Decimal("3000"), "cryptocurrency")
        assert result["tax_amount"] == Decimal("0")
        assert result["exemption"] is True

    # -- Business gains --

    def test_business_gain(self, calculator: CapitalGainsTaxCalculator) -> None:
        result = calculator.calculate_capital_gains_tax(Decimal("50000"), Decimal("80000"), "business")
        assert result["tax_amount"] == Decimal("7800.00")

    # -- Error cases --

    def test_unsupported_asset_type_raises(self, calculator: CapitalGainsTaxCalculator) -> None:
        with pytest.raises(InvalidTaxTypeError, match="Unsupported asset type"):
            calculator.calculate_capital_gains_tax(Decimal("100"), Decimal("200"), "collectibles")

    def test_negative_purchase_price_raises(self, calculator: CapitalGainsTaxCalculator) -> None:
        with pytest.raises(ValueError, match="negative"):
            calculator.calculate_capital_gains_tax(Decimal("-100"), Decimal("200"), "financial")

    def test_negative_sale_price_raises(self, calculator: CapitalGainsTaxCalculator) -> None:
        with pytest.raises(ValueError, match="negative"):
            calculator.calculate_capital_gains_tax(Decimal("100"), Decimal("-200"), "financial")

    def test_unsupported_type_not_checked_when_no_gain(self, calculator: CapitalGainsTaxCalculator) -> None:
        """When there is no gain, unsupported type check is skipped (no gain path returns early)."""
        result = calculator.calculate_capital_gains_tax(Decimal("200"), Decimal("100"), "collectibles")
        assert result["tax_amount"] == Decimal("0")


# ---------------------------------------------------------------------------
# TaxDeductionEngine
# ---------------------------------------------------------------------------
class TestTaxDeductionEngine:
    """Tests for the tax deduction engine."""

    @pytest.fixture()
    def engine(self) -> TaxDeductionEngine:
        return TaxDeductionEngine()

    # -- Employee deductions --

    def test_employee_deduction_low_income(self, engine: TaxDeductionEngine) -> None:
        """Income <= 15 000 gets full base deduction of 1880."""
        result = engine.calculate_employee_deductions(Decimal("10000"))
        assert result["work_deduction"] == Decimal("1880.00")

    def test_employee_deduction_at_15000(self, engine: TaxDeductionEngine) -> None:
        result = engine.calculate_employee_deductions(Decimal("15000"))
        assert result["work_deduction"] == Decimal("1880.00")

    def test_employee_deduction_second_range(self, engine: TaxDeductionEngine) -> None:
        """Income 15001-28000: gradual reduction."""
        result = engine.calculate_employee_deductions(Decimal("20000"))
        # 1880 - (20000-15000)*0.02 = 1880 - 100 = 1780
        assert result["work_deduction"] == Decimal("1780.00")

    def test_employee_deduction_third_range(self, engine: TaxDeductionEngine) -> None:
        """Income 28001-55000: further reduction."""
        result = engine.calculate_employee_deductions(Decimal("35000"))
        # 1610 - (35000-28000)*0.019 = 1610 - 133 = 1477
        assert result["work_deduction"] == Decimal("1477.00")

    def test_employee_deduction_high_income(self, engine: TaxDeductionEngine) -> None:
        """Income > 55 000 gets fixed 1097."""
        result = engine.calculate_employee_deductions(Decimal("80000"))
        assert result["work_deduction"] == Decimal("1097.00")

    def test_employee_deduction_zero(self, engine: TaxDeductionEngine) -> None:
        result = engine.calculate_employee_deductions(Decimal("0"))
        assert result["work_deduction"] == Decimal("1880.00")

    def test_employee_deduction_negative_raises(self, engine: TaxDeductionEngine) -> None:
        with pytest.raises(InvalidIncomeError):
            engine.calculate_employee_deductions(Decimal("-1"))

    def test_employee_deduction_never_below_zero(self, engine: TaxDeductionEngine) -> None:
        """Even for extreme incomes the deduction is clamped to 0 minimum."""
        result = engine.calculate_employee_deductions(Decimal("55000"))
        assert result["work_deduction"] >= Decimal("0")

    # -- Family deductions --

    def test_family_deduction_spouse_eligible(self, engine: TaxDeductionEngine) -> None:
        result = engine.calculate_family_deductions(dependent_spouse=True, spouse_income=Decimal("2000"))
        assert result["spouse_deduction"] == Decimal("800")

    def test_family_deduction_spouse_income_above_threshold(self, engine: TaxDeductionEngine) -> None:
        result = engine.calculate_family_deductions(dependent_spouse=True, spouse_income=Decimal("5000"))
        assert result["spouse_deduction"] == Decimal("0")

    def test_family_deduction_children(self, engine: TaxDeductionEngine) -> None:
        result = engine.calculate_family_deductions(dependent_children=2, children_ages=[5, 8])
        # 2 children over 3: 950 * 2 = 1900
        assert result["children_deduction"] == Decimal("1900")

    def test_family_deduction_child_under_3(self, engine: TaxDeductionEngine) -> None:
        result = engine.calculate_family_deductions(dependent_children=1, children_ages=[2])
        # 950 + 270 (under 3 bonus) = 1220
        assert result["children_deduction"] == Decimal("1220")

    def test_family_deduction_mixed_ages(self, engine: TaxDeductionEngine) -> None:
        result = engine.calculate_family_deductions(dependent_children=3, children_ages=[1, 5, 10])
        # child1 (age 1): 950 + 270 = 1220
        # child2 (age 5): 950
        # child3 (age 10): 950
        assert result["children_deduction"] == Decimal("3120")

    def test_family_deduction_more_children_than_ages(self, engine: TaxDeductionEngine) -> None:
        """Children without specified age get base deduction only."""
        result = engine.calculate_family_deductions(dependent_children=3, children_ages=[2])
        # child1 (age 2): 950 + 270 = 1220
        # child2 + child3 (no age): 950 * 2 = 1900
        assert result["children_deduction"] == Decimal("3120")

    def test_family_deduction_no_dependents(self, engine: TaxDeductionEngine) -> None:
        result = engine.calculate_family_deductions()
        assert result["total_family_deductions"] == Decimal("0.00")

    def test_family_deduction_spouse_and_children(self, engine: TaxDeductionEngine) -> None:
        result = engine.calculate_family_deductions(
            dependent_children=1, dependent_spouse=True, children_ages=[4], spouse_income=Decimal("1000")
        )
        assert result["spouse_deduction"] == Decimal("800")
        assert result["children_deduction"] == Decimal("950")
        assert result["total_family_deductions"] == Decimal("1750.00")

    # -- Medical deductions --

    def test_medical_deduction_above_threshold(self, engine: TaxDeductionEngine) -> None:
        result = engine.calculate_medical_deductions(Decimal("500"))
        # 500 - 129.11 = 370.89
        assert result["deductible_amount"] == Decimal("370.89")
        assert result["deduction_rate"] == Decimal("19")

    def test_medical_deduction_below_threshold(self, engine: TaxDeductionEngine) -> None:
        result = engine.calculate_medical_deductions(Decimal("100"))
        assert result["deductible_amount"] == Decimal("0.00")

    def test_medical_deduction_at_threshold(self, engine: TaxDeductionEngine) -> None:
        result = engine.calculate_medical_deductions(Decimal("129.11"))
        assert result["deductible_amount"] == Decimal("0.00")

    def test_medical_deduction_zero(self, engine: TaxDeductionEngine) -> None:
        result = engine.calculate_medical_deductions(Decimal("0"))
        assert result["deductible_amount"] == Decimal("0.00")

    def test_medical_deduction_negative_raises(self, engine: TaxDeductionEngine) -> None:
        with pytest.raises(ValueError, match="negative"):
            engine.calculate_medical_deductions(Decimal("-10"))

    # -- Renovation deductions --

    def test_renovation_energy_efficiency(self, engine: TaxDeductionEngine) -> None:
        result = engine.calculate_renovation_deductions(Decimal("30000"), "energy_efficiency")
        # ecobonus: 65 %, max 60000
        # eligible = 30000, deductible = 30000 * 0.65 = 19500
        assert result["deductible_amount"] == Decimal("19500.00")
        assert result["annual_deduction"] == Decimal("1950.00")
        assert result["spread_over_years"] == 10

    def test_renovation_structural(self, engine: TaxDeductionEngine) -> None:
        result = engine.calculate_renovation_deductions(Decimal("50000"), "structural")
        # sismabonus: 110 %, max 96000
        assert result["deductible_amount"] == Decimal("55000.00")

    def test_renovation_facade(self, engine: TaxDeductionEngine) -> None:
        result = engine.calculate_renovation_deductions(Decimal("40000"), "facade")
        # bonus_facciate: 60 %, max 60000
        assert result["deductible_amount"] == Decimal("24000.00")

    def test_renovation_super(self, engine: TaxDeductionEngine) -> None:
        result = engine.calculate_renovation_deductions(Decimal("100000"), "super")
        # superbonus: 90 %, max 96000
        # eligible = 96000 (capped), deductible = 96000 * 0.90 = 86400
        assert result["eligible_expenses"] == Decimal("96000")
        assert result["deductible_amount"] == Decimal("86400.00")

    def test_renovation_expenses_below_max(self, engine: TaxDeductionEngine) -> None:
        result = engine.calculate_renovation_deductions(Decimal("10000"), "energy_efficiency")
        assert result["eligible_expenses"] == Decimal("10000")

    def test_renovation_expenses_above_max_capped(self, engine: TaxDeductionEngine) -> None:
        result = engine.calculate_renovation_deductions(Decimal("100000"), "energy_efficiency")
        assert result["eligible_expenses"] == Decimal("60000")

    def test_renovation_negative_raises(self, engine: TaxDeductionEngine) -> None:
        with pytest.raises(ValueError, match="negative"):
            engine.calculate_renovation_deductions(Decimal("-5000"))

    def test_renovation_unknown_type_defaults_to_ecobonus(self, engine: TaxDeductionEngine) -> None:
        result = engine.calculate_renovation_deductions(Decimal("10000"), "unknown_type")
        # Falls back to ecobonus
        assert result["deduction_rate"] == Decimal("65")


# ---------------------------------------------------------------------------
# FreelancerTaxCalculator
# ---------------------------------------------------------------------------
class TestFreelancerTaxCalculator:
    """Tests for freelancer / P.IVA tax calculations."""

    @pytest.fixture()
    def calculator(self) -> FreelancerTaxCalculator:
        return FreelancerTaxCalculator()

    # -- Flat rate regime --

    def test_flat_rate_standard(self, calculator: FreelancerTaxCalculator) -> None:
        result = calculator.calculate_flat_rate_tax(Decimal("60000"), "consulting")
        # coefficient for consulting = 0.67
        # taxable = 60000 * 0.67 = 40200
        # tax = 40200 * 15 / 100 = 6030
        assert result["taxable_income"] == Decimal("40200.00")
        assert result["tax_amount"] == Decimal("6030.00")
        assert result["tax_rate"] == Decimal("15")
        assert result["is_new_business"] is False

    def test_flat_rate_new_business(self, calculator: FreelancerTaxCalculator) -> None:
        result = calculator.calculate_flat_rate_tax(Decimal("50000"), "consulting", is_new_business=True)
        # taxable = 50000 * 0.67 = 33500
        # tax = 33500 * 5 / 100 = 1675
        assert result["tax_rate"] == Decimal("5")
        assert result["tax_amount"] == Decimal("1675.00")
        assert result["is_new_business"] is True

    def test_flat_rate_trade_category(self, calculator: FreelancerTaxCalculator) -> None:
        result = calculator.calculate_flat_rate_tax(Decimal("40000"), "trade")
        # trade coefficient = 0.40
        # taxable = 40000 * 0.40 = 16000
        assert result["activity_coefficient"] == Decimal("0.40")
        assert result["taxable_income"] == Decimal("16000.00")

    def test_flat_rate_unknown_category_defaults(self, calculator: FreelancerTaxCalculator) -> None:
        """Unknown activity category falls back to 'other_services' coefficient (0.67)."""
        result = calculator.calculate_flat_rate_tax(Decimal("30000"), "artistic_endeavors")
        assert result["activity_coefficient"] == Decimal("0.67")

    def test_flat_rate_at_threshold(self, calculator: FreelancerTaxCalculator) -> None:
        """Revenue exactly at 85000 threshold is allowed."""
        result = calculator.calculate_flat_rate_tax(Decimal("85000"), "consulting")
        assert result["regime"] == "forfettario"

    def test_flat_rate_exceeds_threshold_raises(self, calculator: FreelancerTaxCalculator) -> None:
        with pytest.raises(ValueError, match="threshold"):
            calculator.calculate_flat_rate_tax(Decimal("85001"), "consulting")

    def test_flat_rate_zero_revenue(self, calculator: FreelancerTaxCalculator) -> None:
        result = calculator.calculate_flat_rate_tax(Decimal("0"), "consulting")
        assert result["tax_amount"] == Decimal("0.00")

    def test_flat_rate_negative_raises(self, calculator: FreelancerTaxCalculator) -> None:
        with pytest.raises(InvalidIncomeError):
            calculator.calculate_flat_rate_tax(Decimal("-1000"), "consulting")

    def test_flat_rate_vat_exempt_flag(self, calculator: FreelancerTaxCalculator) -> None:
        result = calculator.calculate_flat_rate_tax(Decimal("50000"), "services")
        assert result["vat_exempt"] is True

    # -- Standard regime --

    def test_standard_regime(self, calculator: FreelancerTaxCalculator) -> None:
        result = calculator.calculate_standard_regime_tax(Decimal("100000"), Decimal("30000"), "Lombardia", "Milano")
        assert result["taxable_income"] == Decimal("70000")
        assert result["regime"] == "standard"
        assert result["vat_applicable"] is True
        assert result["total_tax"] > Decimal("0")

    def test_standard_regime_includes_irpef(self, calculator: FreelancerTaxCalculator) -> None:
        result = calculator.calculate_standard_regime_tax(Decimal("50000"), Decimal("10000"), "Lombardia", "Milano")
        # taxable_income = 40000
        # IRPEF on 40000: 3450 + 3250 + (40000-28000)*0.35 = 3450+3250+4200 = 10900
        assert result["irpef_tax"] == Decimal("10900.00")

    def test_standard_regime_regional_surcharge(self, calculator: FreelancerTaxCalculator) -> None:
        result = calculator.calculate_standard_regime_tax(Decimal("60000"), Decimal("10000"), "Lombardia", "Milano")
        # taxable = 50000, Lombardia rate = 1.23 %
        expected_regional = (Decimal("50000") * Decimal("1.23") / 100).quantize(Decimal("0.01"))
        assert result["regional_surcharge"] == expected_regional

    def test_standard_regime_unknown_region_uses_default(self, calculator: FreelancerTaxCalculator) -> None:
        """Unknown region uses default 1.73 % surcharge."""
        result = calculator.calculate_standard_regime_tax(Decimal("50000"), Decimal("10000"), "Atlantis", "SomeCity")
        expected_regional = (Decimal("40000") * Decimal("1.73") / 100).quantize(Decimal("0.01"))
        assert result["regional_surcharge"] == expected_regional

    def test_standard_regime_negative_revenue_raises(self, calculator: FreelancerTaxCalculator) -> None:
        with pytest.raises(InvalidIncomeError):
            calculator.calculate_standard_regime_tax(Decimal("-100"), Decimal("0"), "Lombardia", "Milano")

    def test_standard_regime_negative_expenses_raises(self, calculator: FreelancerTaxCalculator) -> None:
        with pytest.raises(InvalidIncomeError):
            calculator.calculate_standard_regime_tax(Decimal("100000"), Decimal("-500"), "Lombardia", "Milano")

    # -- Quarterly payments --

    def test_quarterly_payment(self, calculator: FreelancerTaxCalculator) -> None:
        result = calculator.calculate_quarterly_payments(Decimal("20000"), Decimal("25000"), 1)
        assert result["quarterly_payment"] == Decimal("5000.00")
        assert result["quarter"] == 1

    def test_quarterly_payment_cumulative(self, calculator: FreelancerTaxCalculator) -> None:
        result = calculator.calculate_quarterly_payments(Decimal("20000"), Decimal("10000"), 3)
        assert result["cumulative_payments"] == Decimal("5000") * 3

    def test_quarterly_payment_invalid_quarter_raises(self, calculator: FreelancerTaxCalculator) -> None:
        with pytest.raises(ValueError, match="Quarter must be between 1 and 4"):
            calculator.calculate_quarterly_payments(Decimal("10000"), Decimal("5000"), 5)

    def test_quarterly_payment_zero_raises(self, calculator: FreelancerTaxCalculator) -> None:
        with pytest.raises(ValueError, match="Quarter must be between 1 and 4"):
            calculator.calculate_quarterly_payments(Decimal("10000"), Decimal("5000"), 0)

    def test_quarterly_payment_has_due_date(self, calculator: FreelancerTaxCalculator) -> None:
        result = calculator.calculate_quarterly_payments(Decimal("8000"), Decimal("3000"), 2)
        assert result["payment_due_date"] is not None


# ---------------------------------------------------------------------------
# TaxOptimizationEngine
# ---------------------------------------------------------------------------
class TestTaxOptimizationEngine:
    """Tests for tax optimization and comparison engine."""

    @pytest.fixture()
    def engine(self) -> TaxOptimizationEngine:
        return TaxOptimizationEngine()

    # -- compare_employment_types --

    def test_compare_employment_types_returns_both(self, engine: TaxOptimizationEngine) -> None:
        result = engine.compare_employment_types(Decimal("50000"))
        assert "employee" in result
        assert "contractor" in result
        assert "savings_potential" in result
        assert "recommendation" in result

    def test_compare_employment_types_employee_fields(self, engine: TaxOptimizationEngine) -> None:
        result = engine.compare_employment_types(Decimal("50000"))
        emp = result["employee"]
        assert "irpef_tax" in emp
        assert "inps_contribution" in emp
        assert "net_income" in emp
        assert "tax_rate" in emp

    def test_compare_employment_types_contractor_fields(self, engine: TaxOptimizationEngine) -> None:
        result = engine.compare_employment_types(Decimal("50000"))
        con = result["contractor"]
        assert "total_tax" in con
        assert "net_income" in con
        assert "tax_rate" in con

    def test_compare_employment_types_recommendation(self, engine: TaxOptimizationEngine) -> None:
        result = engine.compare_employment_types(Decimal("50000"))
        assert result["recommendation"] in ("employee", "contractor")

    def test_compare_employment_types_net_income_positive(self, engine: TaxOptimizationEngine) -> None:
        result = engine.compare_employment_types(Decimal("80000"))
        assert result["employee"]["net_income"] > Decimal("0")
        assert result["contractor"]["net_income"] > Decimal("0")

    def test_compare_employment_types_savings_sign(self, engine: TaxOptimizationEngine) -> None:
        """savings_potential > 0 => contractor recommended, else employee."""
        result = engine.compare_employment_types(Decimal("60000"))
        if result["savings_potential"] > 0:
            assert result["recommendation"] == "contractor"
        else:
            assert result["recommendation"] == "employee"

    # -- optimize_pension_contributions --

    def test_optimize_pension_no_current(self, engine: TaxOptimizationEngine) -> None:
        result = engine.optimize_pension_contributions(Decimal("50000"), Decimal("0"))
        assert result["recommended_contribution"] > Decimal("0")
        assert result["additional_contribution"] == result["recommended_contribution"]
        assert result["tax_savings"] > Decimal("0")

    def test_optimize_pension_already_at_max(self, engine: TaxOptimizationEngine) -> None:
        """Current contributions already at max => no additional contribution."""
        result = engine.optimize_pension_contributions(Decimal("50000"), Decimal("6000"))
        # Optimal = min(50000*0.10, 5164.57) = 5000
        # Additional = max(5000 - 6000, 0) = 0
        assert result["additional_contribution"] == Decimal("0.00")
        assert result["tax_savings"] == Decimal("0.00")

    def test_optimize_pension_partial_contribution(self, engine: TaxOptimizationEngine) -> None:
        result = engine.optimize_pension_contributions(Decimal("80000"), Decimal("3000"))
        # Optimal = min(80000*0.10, 5164.57) = 5164.57
        # Additional = 5164.57 - 3000 = 2164.57
        assert result["recommended_contribution"] == Decimal("5164.57")
        assert result["additional_contribution"] == Decimal("2164.57")

    def test_optimize_pension_high_income_caps_at_max(self, engine: TaxOptimizationEngine) -> None:
        """High income: 10 % of income > max deductible => capped at 5164.57."""
        result = engine.optimize_pension_contributions(Decimal("200000"), Decimal("0"))
        assert result["recommended_contribution"] == Decimal("5164.57")

    def test_optimize_pension_low_income_uses_percentage(self, engine: TaxOptimizationEngine) -> None:
        """Low income: 10 % of income < max deductible => uses percentage."""
        result = engine.optimize_pension_contributions(Decimal("30000"), Decimal("0"))
        assert result["recommended_contribution"] == Decimal("3000.00")

    def test_optimize_pension_marginal_rate_includes_surcharges(self, engine: TaxOptimizationEngine) -> None:
        result = engine.optimize_pension_contributions(Decimal("50000"), Decimal("0"))
        # Marginal rate = IRPEF marginal + 1.73 (regional) + 0.60 (municipal)
        # For 50000 income, IRPEF marginal = 35
        expected_marginal = Decimal("35") + Decimal("1.73") + Decimal("0.60")
        assert result["marginal_rate"] == expected_marginal

    def test_optimize_pension_max_deductible_field(self, engine: TaxOptimizationEngine) -> None:
        result = engine.optimize_pension_contributions(Decimal("50000"), Decimal("0"))
        assert result["max_deductible"] == Decimal("5164.57")
