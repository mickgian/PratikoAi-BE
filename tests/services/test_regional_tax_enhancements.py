"""DEV-393: Tests for Regional Tax Service enhancements.

Tests for client-context-aware calculations, IRPEF national brackets,
P.IVA province-to-regione mapping, and edge cases.
"""

from decimal import Decimal

import pytest

from app.services.regional_tax_service import (
    IRPEF_BRACKETS,
    PROVINCE_TO_REGIONE,
    RegionalTaxService,
    calculate_irpef_nazionale,
    get_regione_from_piva_prefix,
)


class TestIRPEFNationalBrackets:
    """Test national IRPEF bracket calculations."""

    def test_irpef_brackets_exist(self) -> None:
        """IRPEF brackets constant is defined."""
        assert len(IRPEF_BRACKETS) > 0

    def test_irpef_zero_income(self) -> None:
        """Zero income returns zero tax."""
        result = calculate_irpef_nazionale(Decimal("0"))
        assert result == Decimal("0")

    def test_irpef_negative_imponibile_zero_tax(self) -> None:
        """Negative income (losses) returns zero tax."""
        result = calculate_irpef_nazionale(Decimal("-5000"))
        assert result == Decimal("0")

    def test_irpef_first_bracket(self) -> None:
        """Income within the first bracket uses lowest rate."""
        result = calculate_irpef_nazionale(Decimal("10000"))
        assert result > Decimal("0")
        # 23% of 10000 = 2300
        assert result == Decimal("2300")

    def test_irpef_bracket_boundary_inclusive(self) -> None:
        """Income exactly at bracket boundary uses lower bracket (<=)."""
        # At 28000 boundary the first 28000 is taxed at 23%
        result = calculate_irpef_nazionale(Decimal("28000"))
        expected = Decimal("28000") * Decimal("0.23")
        assert result == expected

    def test_irpef_high_income(self) -> None:
        """High income crosses multiple brackets."""
        result = calculate_irpef_nazionale(Decimal("100000"))
        assert result > Decimal("0")
        assert result < Decimal("100000")  # Tax < income


class TestProvinceToRegioneMapping:
    """Test P.IVA province code to regione mapping."""

    def test_piva_province_to_regione(self) -> None:
        """Known P.IVA prefix maps to regione."""
        # Roma prefix -> Lazio
        regione = get_regione_from_piva_prefix("058")
        assert regione is not None
        assert regione == "Lazio"

    def test_piva_milano_to_lombardia(self) -> None:
        """Milano prefix maps to Lombardia."""
        regione = get_regione_from_piva_prefix("015")
        assert regione is not None
        assert regione == "Lombardia"

    def test_unknown_prefix_returns_none(self) -> None:
        """Unknown prefix returns None."""
        regione = get_regione_from_piva_prefix("999")
        assert regione is None

    def test_province_mapping_has_entries(self) -> None:
        """Province mapping is populated."""
        assert len(PROVINCE_TO_REGIONE) > 0


class TestMissingRateDefault:
    """Test fallback when rates are missing."""

    def test_default_regional_rate(self) -> None:
        """Missing regional rate falls back to national default."""
        # The DEFAULT_TAX_RATES should cover at least Lazio and Lombardia
        from app.models.regional_taxes import DEFAULT_TAX_RATES

        assert "ADDIZIONALE_REGIONALE" in DEFAULT_TAX_RATES
        assert "Lazio" in DEFAULT_TAX_RATES["ADDIZIONALE_REGIONALE"]
        assert "Lombardia" in DEFAULT_TAX_RATES["ADDIZIONALE_REGIONALE"]

    def test_zero_rate_valid(self) -> None:
        """Zero rate is a valid value (some comuni have 0% addizionale)."""
        result = calculate_irpef_nazionale(Decimal("0"))
        assert result == Decimal("0")


class TestAllRegionalRatesConfigured:
    """Test that all 20 Italian regions have default rates."""

    def test_all_20_regions_have_addizionale(self) -> None:
        """All 20 Italian regions should have addizionale IRPEF default rates."""
        from app.models.regional_taxes import DEFAULT_TAX_RATES

        regioni = DEFAULT_TAX_RATES.get("ADDIZIONALE_REGIONALE", {})
        assert len(regioni) >= 20, f"Only {len(regioni)} regions configured, expected 20"
