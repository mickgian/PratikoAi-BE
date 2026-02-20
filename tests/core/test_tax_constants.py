"""Tests for Italian tax constants and configuration."""

from datetime import date
from decimal import Decimal

import pytest

from app.core.tax_constants import (
    CAPITAL_GAINS_TAX_2024,
    CORPORATE_TAX_RATES_2024,
    ERROR_MESSAGES,
    FLAT_RATE_REGIME_2024,
    IMU_CONFIG_2024,
    INPS_RATES_2024,
    IRPEF_BRACKETS_2024,
    MUNICIPAL_IRPEF_CONFIG,
    REGIONAL_IRPEF_SURCHARGE_2024,
    REGIONAL_SPECIAL_PROVISIONS,
    TAX_CALENDAR_2024,
    TAX_DEDUCTIONS_2024,
    TAX_OPTIMIZATION_THRESHOLDS,
    VALIDATION_LIMITS,
    VAT_RATES_2024,
    WITHHOLDING_TAX_2024,
    BusinessType,
    EmploymentType,
    TaxRegime,
    VatCategory,
)


class TestTaxRegime:
    """Test TaxRegime enum."""

    def test_tax_regime_values(self):
        """Test tax regime enum values."""
        assert TaxRegime.STANDARD.value == "standard"
        assert TaxRegime.FLAT_RATE.value == "forfettario"
        assert TaxRegime.SIMPLIFIED.value == "simplified"

    def test_tax_regime_membership(self):
        """Test all expected regimes exist."""
        regimes = [r.value for r in TaxRegime]
        assert "standard" in regimes
        assert "forfettario" in regimes
        assert "simplified" in regimes


class TestEmploymentType:
    """Test EmploymentType enum."""

    def test_employment_type_values(self):
        """Test employment type enum values."""
        assert EmploymentType.EMPLOYEE.value == "employee"
        assert EmploymentType.EXECUTIVE.value == "executive"
        assert EmploymentType.SELF_EMPLOYED.value == "self_employed"
        assert EmploymentType.FREELANCER.value == "freelancer"


class TestBusinessType:
    """Test BusinessType enum."""

    def test_business_type_values(self):
        """Test business type enum values."""
        assert BusinessType.STANDARD.value == "standard"
        assert BusinessType.MANUFACTURING.value == "manufacturing"
        assert BusinessType.SERVICES.value == "services"
        assert BusinessType.HEALTHCARE.value == "healthcare"
        assert BusinessType.BANKING.value == "banking"


class TestVatCategory:
    """Test VatCategory enum."""

    def test_vat_category_values(self):
        """Test VAT category enum values."""
        assert VatCategory.STANDARD.value == "standard"
        assert VatCategory.REDUCED_10.value == "reduced_10"
        assert VatCategory.REDUCED_4.value == "reduced_4"
        assert VatCategory.EXEMPT.value == "exempt"


class TestIRPEFBrackets:
    """Test IRPEF tax brackets."""

    def test_irpef_brackets_count(self):
        """Test that there are 4 IRPEF brackets."""
        assert len(IRPEF_BRACKETS_2024) == 4

    def test_irpef_brackets_rates(self):
        """Test IRPEF bracket rates are correct."""
        assert IRPEF_BRACKETS_2024[0]["rate"] == Decimal("23")
        assert IRPEF_BRACKETS_2024[1]["rate"] == Decimal("25")
        assert IRPEF_BRACKETS_2024[2]["rate"] == Decimal("35")
        assert IRPEF_BRACKETS_2024[3]["rate"] == Decimal("43")

    def test_irpef_brackets_ranges(self):
        """Test IRPEF bracket income ranges."""
        assert IRPEF_BRACKETS_2024[0]["min_income"] == Decimal("0")
        assert IRPEF_BRACKETS_2024[0]["max_income"] == Decimal("15000")
        assert IRPEF_BRACKETS_2024[1]["min_income"] == Decimal("15000")
        assert IRPEF_BRACKETS_2024[1]["max_income"] == Decimal("28000")
        assert IRPEF_BRACKETS_2024[2]["min_income"] == Decimal("28000")
        assert IRPEF_BRACKETS_2024[2]["max_income"] == Decimal("55000")
        assert IRPEF_BRACKETS_2024[3]["min_income"] == Decimal("55000")
        assert IRPEF_BRACKETS_2024[3]["max_income"] is None  # No upper limit

    def test_irpef_brackets_have_descriptions(self):
        """Test all brackets have descriptions."""
        for bracket in IRPEF_BRACKETS_2024:
            assert "description" in bracket
            assert len(bracket["description"]) > 0


class TestRegionalIRPEFSurcharge:
    """Test regional IRPEF surcharge rates."""

    def test_all_regions_present(self):
        """Test that all 20 Italian regions are present."""
        assert len(REGIONAL_IRPEF_SURCHARGE_2024) == 20

    def test_special_status_regions_zero_rate(self):
        """Test special status regions have 0% rate."""
        assert REGIONAL_IRPEF_SURCHARGE_2024["Trentino-Alto Adige"] == Decimal("0.00")
        assert REGIONAL_IRPEF_SURCHARGE_2024["Valle d'Aosta"] == Decimal("0.00")

    def test_major_regions_rates(self):
        """Test rates for major regions."""
        assert REGIONAL_IRPEF_SURCHARGE_2024["Lombardia"] == Decimal("1.23")
        assert REGIONAL_IRPEF_SURCHARGE_2024["Lazio"] == Decimal("1.73")
        assert REGIONAL_IRPEF_SURCHARGE_2024["Campania"] == Decimal("1.73")
        assert REGIONAL_IRPEF_SURCHARGE_2024["Sicilia"] == Decimal("1.73")


class TestMunicipalIRPEF:
    """Test municipal IRPEF configuration."""

    def test_default_values(self):
        """Test default municipal IRPEF values."""
        assert MUNICIPAL_IRPEF_CONFIG["default_rate"] == Decimal("0.60")
        assert MUNICIPAL_IRPEF_CONFIG["default_threshold"] == Decimal("11000")

    def test_major_cities_present(self):
        """Test major Italian cities are configured."""
        cities = MUNICIPAL_IRPEF_CONFIG["typical_rates"]
        assert "Milano" in cities
        assert "Roma" in cities
        assert "Napoli" in cities
        assert "Torino" in cities

    def test_city_configurations(self):
        """Test specific city configurations."""
        milano = MUNICIPAL_IRPEF_CONFIG["typical_rates"]["Milano"]
        assert milano["rate"] == Decimal("0.80")
        assert milano["threshold"] == Decimal("12000")


class TestINPSRates:
    """Test INPS contribution rates."""

    def test_employee_rates(self):
        """Test employee INPS rates."""
        assert INPS_RATES_2024["employee"]["rate"] == Decimal("9.19")
        assert INPS_RATES_2024["employee"]["ceiling"] == Decimal("119650")

    def test_employer_rates(self):
        """Test employer INPS rates."""
        assert INPS_RATES_2024["employer"]["rate"] == Decimal("30.00")

    def test_self_employed_rates(self):
        """Test self-employed INPS rates."""
        sep = INPS_RATES_2024["self_employed_separate"]
        assert sep["rate_exclusive_coverage"] == Decimal("25.98")


class TestVATRates:
    """Test VAT rates."""

    def test_standard_vat(self):
        """Test standard VAT rate is 22%."""
        assert VAT_RATES_2024[VatCategory.STANDARD]["rate"] == Decimal("22")

    def test_reduced_vat_rates(self):
        """Test reduced VAT rates."""
        assert VAT_RATES_2024[VatCategory.REDUCED_10]["rate"] == Decimal("10")
        assert VAT_RATES_2024[VatCategory.REDUCED_4]["rate"] == Decimal("4")
        assert VAT_RATES_2024[VatCategory.EXEMPT]["rate"] == Decimal("0")

    def test_vat_categories_have_descriptions(self):
        """Test all VAT categories have descriptions."""
        for category in VatCategory:
            assert "description" in VAT_RATES_2024[category]


class TestCorporateTaxRates:
    """Test corporate tax rates."""

    def test_ires_rates(self):
        """Test IRES corporate tax rates."""
        assert CORPORATE_TAX_RATES_2024["ires"]["standard_rate"] == Decimal("24")
        assert CORPORATE_TAX_RATES_2024["ires"]["reduced_rate_2025"] == Decimal("20")

    def test_irap_rates(self):
        """Test IRAP regional business tax rates."""
        irap = CORPORATE_TAX_RATES_2024["irap"]
        assert irap["standard_rate"] == Decimal("3.9")
        assert irap["banking_rate"] == Decimal("4.65")
        assert irap["insurance_rate"] == Decimal("5.90")


class TestIMUConfig:
    """Test IMU property tax configuration."""

    def test_imu_rates(self):
        """Test IMU standard rates."""
        assert IMU_CONFIG_2024["standard_rate"] == Decimal("0.86")
        assert IMU_CONFIG_2024["cadastral_value_multiplier"] == Decimal("1.05")

    def test_imu_exemptions(self):
        """Test IMU exemption rules."""
        assert IMU_CONFIG_2024["exemptions"]["primary_residence"] is True
        luxury = IMU_CONFIG_2024["exemptions"]["luxury_categories"]
        assert "A/1" in luxury
        assert "A/8" in luxury
        assert "A/9" in luxury

    def test_imu_payment_schedule(self):
        """Test IMU payment schedule."""
        schedule = IMU_CONFIG_2024["payment_schedule"]
        assert schedule["first_installment"]["percentage"] == 50
        assert schedule["second_installment"]["percentage"] == 50
        assert schedule["first_installment"]["due_date"] == date(2024, 6, 17)


class TestCapitalGainsTax:
    """Test capital gains tax configuration."""

    def test_financial_capital_gains(self):
        """Test financial capital gains tax rate."""
        assert CAPITAL_GAINS_TAX_2024["financial"]["rate"] == Decimal("26")

    def test_real_estate_capital_gains(self):
        """Test real estate capital gains."""
        re = CAPITAL_GAINS_TAX_2024["real_estate"]
        assert re["rate"] == Decimal("26")
        assert re["exemption_period_days"] == 1825  # 5 years

    def test_cryptocurrency_capital_gains(self):
        """Test cryptocurrency capital gains."""
        crypto = CAPITAL_GAINS_TAX_2024["cryptocurrency"]
        assert crypto["rate"] == Decimal("26")
        assert crypto["threshold"] == Decimal("2000")


class TestFlatRateRegime:
    """Test flat rate regime (forfettario) configuration."""

    def test_flat_rate_thresholds(self):
        """Test flat rate regime thresholds."""
        assert FLAT_RATE_REGIME_2024["revenue_threshold"] == Decimal("85000")
        assert FLAT_RATE_REGIME_2024["standard_rate"] == Decimal("15")
        assert FLAT_RATE_REGIME_2024["new_business_rate"] == Decimal("5")

    def test_activity_coefficients(self):
        """Test activity coefficients for different business types."""
        coeffs = FLAT_RATE_REGIME_2024["activity_coefficients"]
        assert coeffs["trade"] == Decimal("0.40")
        assert coeffs["manufacturing"] == Decimal("0.86")
        assert coeffs["services"] == Decimal("0.78")
        assert coeffs["consulting"] == Decimal("0.67")


class TestTaxDeductions:
    """Test tax deductions configuration."""

    def test_work_income_deductions(self):
        """Test work income deductions."""
        work = TAX_DEDUCTIONS_2024["work_income"]
        assert work["employee_base"] == Decimal("1880")
        assert work["pensioner_base"] == Decimal("1955")

    def test_family_deductions(self):
        """Test family deductions."""
        family = TAX_DEDUCTIONS_2024["family"]
        assert family["spouse"]["base_deduction"] == Decimal("800")
        assert family["children"]["base_deduction"] == Decimal("950")
        assert family["children"]["under_3_additional"] == Decimal("270")

    def test_medical_expenses_deduction(self):
        """Test medical expenses deduction."""
        medical = TAX_DEDUCTIONS_2024["medical_expenses"]
        assert medical["threshold"] == Decimal("129.11")
        assert medical["deduction_rate"] == Decimal("19")

    def test_home_renovation_deductions(self):
        """Test home renovation deductions."""
        reno = TAX_DEDUCTIONS_2024["home_renovations"]
        assert reno["ecobonus"]["rate"] == Decimal("65")
        assert reno["superbonus"]["rate"] == Decimal("90")


class TestWithholdingTax:
    """Test withholding tax rates."""

    def test_professional_services_withholding(self):
        """Test professional services withholding."""
        assert WITHHOLDING_TAX_2024["professional_services"] == Decimal("20")
        assert WITHHOLDING_TAX_2024["consulting"] == Decimal("20")

    def test_investment_income_withholding(self):
        """Test investment income withholding."""
        assert WITHHOLDING_TAX_2024["dividends"] == Decimal("26")
        assert WITHHOLDING_TAX_2024["interest"] == Decimal("26")

    def test_rental_income_withholding(self):
        """Test rental income withholding (cedolare secca)."""
        assert WITHHOLDING_TAX_2024["rental_income"] == Decimal("21")


class TestTaxCalendar:
    """Test tax calendar deadlines."""

    def test_income_tax_return_deadlines(self):
        """Test income tax return deadlines."""
        itr = TAX_CALENDAR_2024["income_tax_return"]
        assert itr["filing_deadline"] == date(2024, 10, 31)
        assert itr["payment_deadline"] == date(2024, 11, 30)

    def test_quarterly_payments(self):
        """Test quarterly payment deadlines."""
        quarterly = TAX_CALENDAR_2024["quarterly_payments"]
        assert len(quarterly) == 2
        assert quarterly[0]["deadline"] == date(2024, 6, 17)

    def test_vat_quarterly_deadlines(self):
        """Test quarterly VAT deadlines."""
        vat = TAX_CALENDAR_2024["vat_quarterly"]
        assert len(vat) == 4
        assert vat[0]["deadline"] == date(2024, 4, 16)

    def test_imu_payment_deadlines(self):
        """Test IMU payment deadlines."""
        imu = TAX_CALENDAR_2024["imu_payments"]
        assert len(imu) == 2
        assert imu[0]["deadline"] == date(2024, 6, 17)
        assert imu[1]["deadline"] == date(2024, 12, 16)


class TestRegionalSpecialProvisions:
    """Test regional special provisions."""

    def test_autonomous_regions(self):
        """Test autonomous regions have special provisions."""
        assert REGIONAL_SPECIAL_PROVISIONS["Trentino-Alto Adige"]["autonomous_province"] is True
        assert REGIONAL_SPECIAL_PROVISIONS["Valle d'Aosta"]["autonomous_region"] is True

    def test_special_irpef_provisions(self):
        """Test special IRPEF provisions."""
        taa = REGIONAL_SPECIAL_PROVISIONS["Trentino-Alto Adige"]
        assert taa["special_irpef_rates"] is True
        assert taa["reduced_irap"] is True


class TestTaxOptimizationThresholds:
    """Test tax optimization thresholds."""

    def test_optimization_thresholds(self):
        """Test key optimization thresholds."""
        assert TAX_OPTIMIZATION_THRESHOLDS["flat_rate_threshold"] == Decimal("85000")
        assert TAX_OPTIMIZATION_THRESHOLDS["vat_threshold"] == Decimal("65000")
        assert TAX_OPTIMIZATION_THRESHOLDS["real_estate_exemption_years"] == 5


class TestValidationLimits:
    """Test validation limits."""

    def test_validation_limits(self):
        """Test validation limits are set."""
        assert VALIDATION_LIMITS["max_annual_income"] == Decimal("10000000")
        assert VALIDATION_LIMITS["min_annual_income"] == Decimal("0")
        assert VALIDATION_LIMITS["max_vat_amount"] == Decimal("1000000")


class TestErrorMessages:
    """Test error messages."""

    def test_error_messages_exist(self):
        """Test error messages are defined."""
        assert "negative_income" in ERROR_MESSAGES
        assert "invalid_location" in ERROR_MESSAGES
        assert "calculation_error" in ERROR_MESSAGES

    def test_error_messages_not_empty(self):
        """Test all error messages have content."""
        for key, msg in ERROR_MESSAGES.items():
            assert len(msg) > 0
            assert isinstance(msg, str)
