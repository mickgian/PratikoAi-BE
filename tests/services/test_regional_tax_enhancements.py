"""DEV-393: Tests for Regional Tax Service enhancements.

Tests cover:
- IRPEF national bracket calculations (all brackets, boundaries, edge cases)
- P.IVA province-to-regione mapping
- All 20 Italian regions configured
- Default tax rate configuration
- IRPEF bracket structure validation
"""

from decimal import Decimal

import pytest

from app.services.regional_tax_service import (
    IRPEF_BRACKETS,
    PROVINCE_TO_REGIONE,
    calculate_irpef_nazionale,
    get_regione_from_piva_prefix,
)


# ------------------------------------------------------------------ #
# IRPEF National Brackets
# ------------------------------------------------------------------ #
class TestIRPEFNationalBrackets:
    """Test national IRPEF bracket calculations."""

    def test_irpef_brackets_defined(self) -> None:
        """IRPEF brackets constant is defined with 3 brackets."""
        assert len(IRPEF_BRACKETS) == 3

    def test_irpef_brackets_ascending(self) -> None:
        """Brackets have ascending upper bounds and rates."""
        for i in range(1, len(IRPEF_BRACKETS)):
            assert IRPEF_BRACKETS[i][0] > IRPEF_BRACKETS[i - 1][0]
            assert IRPEF_BRACKETS[i][1] > IRPEF_BRACKETS[i - 1][1]

    def test_irpef_zero_income(self) -> None:
        assert calculate_irpef_nazionale(Decimal("0")) == Decimal("0")

    def test_irpef_negative_income(self) -> None:
        assert calculate_irpef_nazionale(Decimal("-5000")) == Decimal("0")

    def test_irpef_first_bracket_only(self) -> None:
        """10,000 taxed at 23% = 2,300."""
        result = calculate_irpef_nazionale(Decimal("10000"))
        assert result == Decimal("2300")

    def test_irpef_first_bracket_boundary(self) -> None:
        """28,000 exactly at first bracket boundary → 28000 * 23%."""
        result = calculate_irpef_nazionale(Decimal("28000"))
        assert result == Decimal("28000") * Decimal("0.23")

    def test_irpef_second_bracket(self) -> None:
        """35,000: first 28000 at 23% + 7000 at 35%."""
        result = calculate_irpef_nazionale(Decimal("35000"))
        expected = Decimal("28000") * Decimal("0.23") + Decimal("7000") * Decimal("0.35")
        assert result == expected

    def test_irpef_second_bracket_boundary(self) -> None:
        """50,000 exactly at second bracket boundary."""
        result = calculate_irpef_nazionale(Decimal("50000"))
        expected = Decimal("28000") * Decimal("0.23") + Decimal("22000") * Decimal("0.35")
        assert result == expected

    def test_irpef_third_bracket(self) -> None:
        """100,000 crosses all three brackets."""
        result = calculate_irpef_nazionale(Decimal("100000"))
        expected = (
            Decimal("28000") * Decimal("0.23")
            + Decimal("22000") * Decimal("0.35")
            + Decimal("50000") * Decimal("0.43")
        )
        assert result == expected

    def test_irpef_high_income(self) -> None:
        """Very high income: tax < income."""
        result = calculate_irpef_nazionale(Decimal("500000"))
        assert result > Decimal("0")
        assert result < Decimal("500000")

    def test_irpef_one_euro(self) -> None:
        """1 euro income = 0.23 tax."""
        result = calculate_irpef_nazionale(Decimal("1"))
        assert result == Decimal("0.23")

    def test_irpef_small_amount(self) -> None:
        """Small fractional income."""
        result = calculate_irpef_nazionale(Decimal("0.01"))
        assert result == Decimal("0.0023")


# ------------------------------------------------------------------ #
# Province-to-Regione mapping
# ------------------------------------------------------------------ #
class TestProvinceToRegioneMapping:
    """Test P.IVA province code to regione mapping."""

    def test_roma_to_lazio(self) -> None:
        assert get_regione_from_piva_prefix("058") == "Lazio"

    def test_milano_to_lombardia(self) -> None:
        assert get_regione_from_piva_prefix("015") == "Lombardia"

    def test_torino_to_piemonte(self) -> None:
        assert get_regione_from_piva_prefix("001") == "Piemonte"

    def test_napoli_to_campania(self) -> None:
        assert get_regione_from_piva_prefix("063") == "Campania"

    def test_palermo_to_sicilia(self) -> None:
        assert get_regione_from_piva_prefix("082") == "Sicilia"

    def test_aosta_to_valle_daosta(self) -> None:
        assert get_regione_from_piva_prefix("007") == "Valle d'Aosta"

    def test_unknown_prefix_returns_none(self) -> None:
        assert get_regione_from_piva_prefix("999") is None

    def test_empty_prefix_returns_none(self) -> None:
        assert get_regione_from_piva_prefix("") is None

    def test_province_mapping_populated(self) -> None:
        assert len(PROVINCE_TO_REGIONE) > 90  # ~106 provinces

    def test_all_20_regions_in_mapping(self) -> None:
        """All 20 Italian regions appear in the province mapping."""
        regions = set(PROVINCE_TO_REGIONE.values())
        expected = {
            "Piemonte",
            "Valle d'Aosta",
            "Lombardia",
            "Trentino-Alto Adige",
            "Veneto",
            "Friuli-Venezia Giulia",
            "Liguria",
            "Emilia-Romagna",
            "Toscana",
            "Umbria",
            "Marche",
            "Lazio",
            "Abruzzo",
            "Molise",
            "Campania",
            "Puglia",
            "Basilicata",
            "Calabria",
            "Sicilia",
            "Sardegna",
        }
        assert regions == expected


# ------------------------------------------------------------------ #
# Default tax rates
# ------------------------------------------------------------------ #
class TestDefaultTaxRates:
    """Test default tax rate configuration."""

    def test_addizionale_regionale_exists(self) -> None:
        from app.models.regional_taxes import DEFAULT_TAX_RATES

        assert "ADDIZIONALE_REGIONALE" in DEFAULT_TAX_RATES

    def test_all_20_regions_configured(self) -> None:
        from app.models.regional_taxes import DEFAULT_TAX_RATES

        regioni = DEFAULT_TAX_RATES.get("ADDIZIONALE_REGIONALE", {})
        assert len(regioni) >= 20, f"Only {len(regioni)} regions configured, expected 20"

    def test_lazio_and_lombardia_present(self) -> None:
        from app.models.regional_taxes import DEFAULT_TAX_RATES

        rates = DEFAULT_TAX_RATES["ADDIZIONALE_REGIONALE"]
        assert "Lazio" in rates
        assert "Lombardia" in rates

    def test_rates_are_positive(self) -> None:
        """All configured rates are positive numbers."""
        from app.models.regional_taxes import DEFAULT_TAX_RATES

        for region, rate in DEFAULT_TAX_RATES["ADDIZIONALE_REGIONALE"].items():
            assert rate > 0, f"{region} has non-positive rate: {rate}"
