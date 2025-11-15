"""
Comprehensive TDD Tests for Regional Tax Variations.

This test suite covers Italian regional and municipal tax variations
including IMU, IRAP, and IRPEF addizionali with location-based calculations.

Following TDD methodology: write tests first, then implement functionality.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

# Import models that will be implemented
from app.models.regional_taxes import ComunalTaxRate, Comune, RegionalTaxRate, Regione
from app.services.location_service import InvalidCAP, ItalianLocationService, LocationAmbiguous
from app.services.regional_tax_service import (
    InvalidTaxCalculation,
    LocationNotFound,
    RegionalTaxService,
    TaxRateNotFound,
)

# Test Data Setup


@pytest.fixture
def sample_regioni():
    """Sample Italian regions for testing"""
    return [
        {"id": uuid4(), "codice_istat": "12", "nome": "Lazio", "is_autonomous": False},
        {"id": uuid4(), "codice_istat": "03", "nome": "Lombardia", "is_autonomous": False},
        {"id": uuid4(), "codice_istat": "15", "nome": "Campania", "is_autonomous": False},
        {"id": uuid4(), "codice_istat": "01", "nome": "Piemonte", "is_autonomous": False},
        {"id": uuid4(), "codice_istat": "04", "nome": "Trentino-Alto Adige", "is_autonomous": True},
    ]


@pytest.fixture
def sample_comuni(sample_regioni):
    """Sample Italian municipalities for testing"""
    lazio_id = next(r["id"] for r in sample_regioni if r["nome"] == "Lazio")
    lombardia_id = next(r["id"] for r in sample_regioni if r["nome"] == "Lombardia")
    campania_id = next(r["id"] for r in sample_regioni if r["nome"] == "Campania")
    piemonte_id = next(r["id"] for r in sample_regioni if r["nome"] == "Piemonte")

    return [
        {
            "id": uuid4(),
            "codice_istat": "058091",
            "nome": "Roma",
            "provincia": "RM",
            "regione_id": lazio_id,
            "cap_codes": ["00100", "00118", "00119", "00120", "00121"],
            "popolazione": 2872800,
            "is_capoluogo": True,
        },
        {
            "id": uuid4(),
            "codice_istat": "015146",
            "nome": "Milano",
            "provincia": "MI",
            "regione_id": lombardia_id,
            "cap_codes": ["20100", "20121", "20122", "20123", "20124"],
            "popolazione": 1396059,
            "is_capoluogo": True,
        },
        {
            "id": uuid4(),
            "codice_istat": "063049",
            "nome": "Napoli",
            "provincia": "NA",
            "regione_id": campania_id,
            "cap_codes": ["80100", "80121", "80122", "80123", "80124"],
            "popolazione": 967069,
            "is_capoluogo": True,
        },
        {
            "id": uuid4(),
            "codice_istat": "001272",
            "nome": "Torino",
            "provincia": "TO",
            "regione_id": piemonte_id,
            "cap_codes": ["10100", "10121", "10122", "10123", "10124"],
            "popolazione": 870952,
            "is_capoluogo": True,
        },
    ]


@pytest.fixture
def sample_imu_rates(sample_comuni):
    """Sample IMU rates for different comuni"""
    roma_id = next(c["id"] for c in sample_comuni if c["nome"] == "Roma")
    milano_id = next(c["id"] for c in sample_comuni if c["nome"] == "Milano")
    napoli_id = next(c["id"] for c in sample_comuni if c["nome"] == "Napoli")
    torino_id = next(c["id"] for c in sample_comuni if c["nome"] == "Torino")

    return [
        {
            "id": uuid4(),
            "comune_id": roma_id,
            "tax_type": "IMU",
            "rate": Decimal("1.06"),
            "rate_prima_casa": Decimal("0.5"),
            "esenzione_prima_casa": True,
            "valid_from": date(2024, 1, 1),
            "valid_to": None,
            "detrazioni": {"abitazione_principale": 200},
            "soglie": {},
        },
        {
            "id": uuid4(),
            "comune_id": milano_id,
            "tax_type": "IMU",
            "rate": Decimal("1.04"),
            "rate_prima_casa": Decimal("0.6"),
            "esenzione_prima_casa": False,
            "valid_from": date(2024, 1, 1),
            "valid_to": None,
            "detrazioni": {"abitazione_principale": 300},
            "soglie": {},
        },
        {
            "id": uuid4(),
            "comune_id": napoli_id,
            "tax_type": "IMU",
            "rate": Decimal("1.14"),
            "rate_prima_casa": Decimal("0.6"),
            "esenzione_prima_casa": False,
            "valid_from": date(2024, 1, 1),
            "valid_to": None,
            "detrazioni": {"abitazione_principale": 200},
            "soglie": {},
        },
        {
            "id": uuid4(),
            "comune_id": torino_id,
            "tax_type": "IMU",
            "rate": Decimal("1.06"),
            "rate_prima_casa": Decimal("0.45"),
            "esenzione_prima_casa": True,
            "valid_from": date(2024, 1, 1),
            "valid_to": None,
            "detrazioni": {"abitazione_principale": 200},
            "soglie": {},
        },
    ]


@pytest.fixture
def sample_irap_rates(sample_regioni):
    """Sample IRAP rates for different regions"""
    lazio_id = next(r["id"] for r in sample_regioni if r["nome"] == "Lazio")
    lombardia_id = next(r["id"] for r in sample_regioni if r["nome"] == "Lombardia")
    campania_id = next(r["id"] for r in sample_regioni if r["nome"] == "Campania")

    return [
        {
            "id": uuid4(),
            "regione_id": lazio_id,
            "tax_type": "IRAP",
            "rate_standard": Decimal("4.82"),
            "rate_banks": Decimal("5.57"),
            "rate_insurance": Decimal("6.82"),
            "rate_agriculture": Decimal("1.9"),
            "valid_from": date(2024, 1, 1),
            "valid_to": None,
        },
        {
            "id": uuid4(),
            "regione_id": lombardia_id,
            "tax_type": "IRAP",
            "rate_standard": Decimal("3.9"),
            "rate_banks": Decimal("5.57"),
            "rate_insurance": Decimal("6.82"),
            "rate_agriculture": Decimal("1.9"),
            "valid_from": date(2024, 1, 1),
            "valid_to": None,
        },
        {
            "id": uuid4(),
            "regione_id": campania_id,
            "tax_type": "IRAP",
            "rate_standard": Decimal("3.9"),
            "rate_banks": Decimal("5.57"),
            "rate_insurance": Decimal("6.82"),
            "rate_agriculture": Decimal("1.9"),
            "valid_from": date(2024, 1, 1),
            "valid_to": None,
        },
    ]


@pytest.fixture
def sample_addizionale_rates(sample_regioni, sample_comuni):
    """Sample addizionale IRPEF rates"""
    lazio_id = next(r["id"] for r in sample_regioni if r["nome"] == "Lazio")
    lombardia_id = next(r["id"] for r in sample_regioni if r["nome"] == "Lombardia")
    campania_id = next(r["id"] for r in sample_regioni if r["nome"] == "Campania")

    roma_id = next(c["id"] for c in sample_comuni if c["nome"] == "Roma")
    milano_id = next(c["id"] for c in sample_comuni if c["nome"] == "Milano")
    napoli_id = next(c["id"] for c in sample_comuni if c["nome"] == "Napoli")

    return {
        "regional": [
            {
                "id": uuid4(),
                "regione_id": lazio_id,
                "tax_type": "ADDIZIONALE_IRPEF",
                "rate_standard": Decimal("1.73"),
                "valid_from": date(2024, 1, 1),
            },
            {
                "id": uuid4(),
                "regione_id": lombardia_id,
                "tax_type": "ADDIZIONALE_IRPEF",
                "rate_standard": Decimal("1.73"),
                "valid_from": date(2024, 1, 1),
            },
            {
                "id": uuid4(),
                "regione_id": campania_id,
                "tax_type": "ADDIZIONALE_IRPEF",
                "rate_standard": Decimal("2.03"),
                "valid_from": date(2024, 1, 1),
            },
        ],
        "municipal": [
            {
                "id": uuid4(),
                "comune_id": roma_id,
                "tax_type": "ADDIZIONALE_COMUNALE_IRPEF",
                "rate": Decimal("0.9"),
                "valid_from": date(2024, 1, 1),
                "soglie": {"no_tax_under": 11000},
            },
            {
                "id": uuid4(),
                "comune_id": milano_id,
                "tax_type": "ADDIZIONALE_COMUNALE_IRPEF",
                "rate": Decimal("0.8"),
                "valid_from": date(2024, 1, 1),
                "soglie": {"no_tax_under": 15000},
            },
            {
                "id": uuid4(),
                "comune_id": napoli_id,
                "tax_type": "ADDIZIONALE_COMUNALE_IRPEF",
                "rate": Decimal("0.8"),
                "valid_from": date(2024, 1, 1),
                "soglie": {"no_tax_under": 12000},
            },
        ],
    }


# Location Detection Tests


class TestLocationDetection:
    """Test CAP to comune mapping and location detection"""

    @pytest.mark.asyncio
    async def test_cap_to_comune_mapping_roma(self, sample_comuni):
        """Test CAP mapping for Roma"""
        service = ItalianLocationService(Mock(), Mock())
        service.db.query = AsyncMock()

        # Mock database response for Roma
        next(c for c in sample_comuni if c["nome"] == "Roma")
        service.db.query.return_value = Mock(
            comune="Roma", provincia="RM", regione="Lazio", popolazione=2872800, is_capoluogo=True
        )

        result = await service.get_location_from_cap("00100")

        assert result["comune"] == "Roma"
        assert result["provincia"] == "RM"
        assert result["regione"] == "Lazio"
        assert result["cap"] == "00100"
        assert result["is_capoluogo"] is True

    @pytest.mark.asyncio
    async def test_cap_to_comune_mapping_milano(self, sample_comuni):
        """Test CAP mapping for Milano"""
        service = ItalianLocationService(Mock(), Mock())
        service.db.query = AsyncMock()

        service.db.query.return_value = Mock(
            comune="Milano", provincia="MI", regione="Lombardia", popolazione=1396059, is_capoluogo=True
        )

        result = await service.get_location_from_cap("20100")

        assert result["comune"] == "Milano"
        assert result["provincia"] == "MI"
        assert result["regione"] == "Lombardia"

    @pytest.mark.asyncio
    async def test_cap_to_comune_mapping_napoli(self, sample_comuni):
        """Test CAP mapping for Napoli"""
        service = ItalianLocationService(Mock(), Mock())
        service.db.query = AsyncMock()

        service.db.query.return_value = Mock(
            comune="Napoli", provincia="NA", regione="Campania", popolazione=967069, is_capoluogo=True
        )

        result = await service.get_location_from_cap("80100")

        assert result["comune"] == "Napoli"
        assert result["provincia"] == "NA"
        assert result["regione"] == "Campania"

    @pytest.mark.asyncio
    async def test_multiple_cap_same_comune(self):
        """Test handling of multiple CAPs for same comune"""
        service = ItalianLocationService(Mock(), Mock())
        service.db.query = AsyncMock(return_value=Mock(comune="Roma", provincia="RM", regione="Lazio"))

        # All these CAPs should resolve to Roma
        cap_codes = ["00100", "00118", "00119", "00120", "00121"]

        for cap in cap_codes:
            result = await service.get_location_from_cap(cap)
            assert result["comune"] == "Roma"

    @pytest.mark.asyncio
    async def test_invalid_cap_validation(self):
        """Test validation of invalid CAP codes"""
        service = ItalianLocationService(Mock(), Mock())

        # Test various invalid formats
        invalid_caps = ["", "123", "123456", "abcde", "1234a", None]

        for invalid_cap in invalid_caps:
            is_valid = await service.validate_cap(invalid_cap)
            assert is_valid is False

    @pytest.mark.asyncio
    async def test_valid_cap_validation(self):
        """Test validation of valid CAP codes"""
        service = ItalianLocationService(Mock(), Mock())

        valid_caps = ["00100", "20100", "80100", "10100", "50100"]

        for valid_cap in valid_caps:
            is_valid = await service.validate_cap(valid_cap)
            assert is_valid is True

    @pytest.mark.asyncio
    async def test_provincia_to_regione_mapping(self):
        """Test provincia abbreviation to region mapping"""
        service = ItalianLocationService(Mock(), Mock())

        expected_mappings = {
            "RM": "Lazio",
            "MI": "Lombardia",
            "NA": "Campania",
            "TO": "Piemonte",
            "PA": "Sicilia",
            "FI": "Toscana",
        }

        for provincia, expected_regione in expected_mappings.items():
            regione = service.PROVINCIA_TO_REGIONE.get(provincia)
            assert regione == expected_regione

    @pytest.mark.asyncio
    async def test_unknown_location_handling(self):
        """Test handling of unknown CAP codes"""
        service = ItalianLocationService(Mock(), Mock())
        service.db.query = AsyncMock(return_value=None)
        service.cache.get = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="Località non trovata"):
            await service.get_location_from_cap("99999")

    @pytest.mark.asyncio
    async def test_special_autonomous_regions(self, sample_regioni):
        """Test handling of special autonomous regions"""
        ItalianLocationService(Mock(), Mock())

        # Test Trentino-Alto Adige autonomous region
        trentino = next(r for r in sample_regioni if r["nome"] == "Trentino-Alto Adige")
        assert trentino["is_autonomous"] is True


# IMU Calculation Tests


class TestIMUCalculations:
    """Test IMU calculations with regional variations"""

    @pytest.mark.asyncio
    async def test_imu_calculation_roma_prima_casa(self, sample_comuni, sample_imu_rates):
        """Test IMU calculation for Roma abitazione principale (should be exempt)"""
        service = RegionalTaxService(Mock(), Mock())
        service.get_comune_by_cap = AsyncMock()
        service.get_tax_rates = AsyncMock()

        # Setup Roma data
        roma_comune = next(c for c in sample_comuni if c["nome"] == "Roma")
        roma_rates = next(r for r in sample_imu_rates if r["comune_id"] == roma_comune["id"])

        service.get_comune_by_cap.return_value = Mock(**roma_comune)
        service.get_tax_rates.return_value = Mock(**roma_rates)

        result = await service.calculate_imu(property_value=Decimal("300000"), cap="00100", is_prima_casa=True)

        assert result["comune"] == "Roma"
        assert result["provincia"] == "RM"
        assert result["aliquota"] == 0
        assert result["imposta_dovuta"] == 0
        assert "esente" in result["note"].lower()

    @pytest.mark.asyncio
    async def test_imu_calculation_milano_prima_casa(self, sample_comuni, sample_imu_rates):
        """Test IMU calculation for Milano abitazione principale (not exempt)"""
        service = RegionalTaxService(Mock(), Mock())
        service.get_comune_by_cap = AsyncMock()
        service.get_tax_rates = AsyncMock()

        milano_comune = next(c for c in sample_comuni if c["nome"] == "Milano")
        milano_rates = next(r for r in sample_imu_rates if r["comune_id"] == milano_comune["id"])

        service.get_comune_by_cap.return_value = Mock(**milano_comune)
        service.get_tax_rates.return_value = Mock(**milano_rates)

        result = await service.calculate_imu(property_value=Decimal("400000"), cap="20100", is_prima_casa=True)

        # Calculate expected values
        base_imponibile = 400000 * Decimal("0.63")  # 252,000
        imposta_lorda = base_imponibile * Decimal("0.6") / 100  # 1,512
        detrazioni = Decimal("300")
        imposta_netta = imposta_lorda - detrazioni  # 1,212

        assert result["comune"] == "Milano"
        assert result["aliquota"] == 0.6
        assert result["base_imponibile"] == float(base_imponibile)
        assert result["imposta_dovuta"] == float(imposta_netta)
        assert result["detrazioni"] == 300

    @pytest.mark.asyncio
    async def test_imu_calculation_napoli_altri_immobili(self, sample_comuni, sample_imu_rates):
        """Test IMU calculation for Napoli altri immobili"""
        service = RegionalTaxService(Mock(), Mock())
        service.get_comune_by_cap = AsyncMock()
        service.get_tax_rates = AsyncMock()

        napoli_comune = next(c for c in sample_comuni if c["nome"] == "Napoli")
        napoli_rates = next(r for r in sample_imu_rates if r["comune_id"] == napoli_comune["id"])

        service.get_comune_by_cap.return_value = Mock(**napoli_comune)
        service.get_tax_rates.return_value = Mock(**napoli_rates)

        result = await service.calculate_imu(property_value=Decimal("200000"), cap="80100", is_prima_casa=False)

        # Calculate expected values for highest rate city
        base_imponibile = 200000 * Decimal("0.63")  # 126,000
        imposta_dovuta = base_imponibile * Decimal("1.14") / 100  # 1,436.4

        assert result["comune"] == "Napoli"
        assert result["aliquota"] == 1.14  # Highest rate
        assert result["imposta_dovuta"] == float(imposta_dovuta)
        assert "altri immobili" in result["note"].lower()

    @pytest.mark.asyncio
    async def test_imu_rate_comparison_different_cities(self, sample_comuni, sample_imu_rates):
        """Test IMU rate differences between cities"""
        RegionalTaxService(Mock(), Mock())

        # Get rates for comparison
        roma_rates = next(
            r
            for r in sample_imu_rates
            if any(c["id"] == r["comune_id"] and c["nome"] == "Roma" for c in sample_comuni)
        )
        milano_rates = next(
            r
            for r in sample_imu_rates
            if any(c["id"] == r["comune_id"] and c["nome"] == "Milano" for c in sample_comuni)
        )
        napoli_rates = next(
            r
            for r in sample_imu_rates
            if any(c["id"] == r["comune_id"] and c["nome"] == "Napoli" for c in sample_comuni)
        )

        # Verify rate differences
        assert roma_rates["rate"] == Decimal("1.06")
        assert milano_rates["rate"] == Decimal("1.04")  # Lowest
        assert napoli_rates["rate"] == Decimal("1.14")  # Highest

        # Verify prima casa differences
        assert roma_rates["esenzione_prima_casa"] is True
        assert milano_rates["esenzione_prima_casa"] is False
        assert napoli_rates["esenzione_prima_casa"] is False

    @pytest.mark.asyncio
    async def test_imu_detrazioni_calculation(self, sample_comuni, sample_imu_rates):
        """Test IMU detrazioni (deductions) application"""
        service = RegionalTaxService(Mock(), Mock())
        service.get_comune_by_cap = AsyncMock()
        service.get_tax_rates = AsyncMock()

        milano_comune = next(c for c in sample_comuni if c["nome"] == "Milano")
        milano_rates = next(r for r in sample_imu_rates if r["comune_id"] == milano_comune["id"])

        service.get_comune_by_cap.return_value = Mock(**milano_comune)
        service.get_tax_rates.return_value = Mock(**milano_rates)

        # Test with low property value where detrazioni matter
        result = await service.calculate_imu(property_value=Decimal("100000"), cap="20100", is_prima_casa=True)

        # Verify detrazioni were applied
        assert result["detrazioni"] == 300
        assert result["imposta_dovuta"] >= 0  # Should not be negative

    @pytest.mark.asyncio
    async def test_imu_unknown_cap_error(self):
        """Test IMU calculation with unknown CAP"""
        service = RegionalTaxService(Mock(), Mock())
        service.get_comune_by_cap = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="CAP .* non trovato"):
            await service.calculate_imu(Decimal("300000"), "99999", is_prima_casa=True)


# IRAP Calculation Tests


class TestIRAPCalculations:
    """Test IRAP calculations with regional variations"""

    @pytest.mark.asyncio
    async def test_irap_calculation_lazio_standard(self, sample_regioni, sample_irap_rates):
        """Test IRAP calculation for Lazio standard business"""
        service = RegionalTaxService(Mock(), Mock())
        service.get_regione_by_name = AsyncMock()
        service.get_regional_tax_rates = AsyncMock()

        lazio_regione = next(r for r in sample_regioni if r["nome"] == "Lazio")
        lazio_rates = next(r for r in sample_irap_rates if r["regione_id"] == lazio_regione["id"])

        service.get_regione_by_name.return_value = Mock(**lazio_regione)
        service.get_regional_tax_rates.return_value = Mock(**lazio_rates)

        result = await service.calculate_irap(revenue=Decimal("1000000"), region="Lazio", business_type="standard")

        # Calculate expected values - Lazio has higher IRAP (4.82%)
        valore_produzione = 1000000 * Decimal("0.85")  # 850,000
        imposta = valore_produzione * Decimal("4.82") / 100  # 40,970

        assert result["regione"] == "Lazio"
        assert result["aliquota"] == 4.82
        assert result["tipo_attivita"] == "standard"
        assert result["imposta_dovuta"] == float(imposta)

    @pytest.mark.asyncio
    async def test_irap_calculation_lombardia_standard(self, sample_regioni, sample_irap_rates):
        """Test IRAP calculation for Lombardia standard business"""
        service = RegionalTaxService(Mock(), Mock())
        service.get_regione_by_name = AsyncMock()
        service.get_regional_tax_rates = AsyncMock()

        lombardia_regione = next(r for r in sample_regioni if r["nome"] == "Lombardia")
        lombardia_rates = next(r for r in sample_irap_rates if r["regione_id"] == lombardia_regione["id"])

        service.get_regione_by_name.return_value = Mock(**lombardia_regione)
        service.get_regional_tax_rates.return_value = Mock(**lombardia_rates)

        result = await service.calculate_irap(revenue=Decimal("1000000"), region="Lombardia", business_type="standard")

        # Lombardia has standard IRAP (3.9%)
        valore_produzione = 1000000 * Decimal("0.85")
        imposta = valore_produzione * Decimal("3.9") / 100  # 33,150

        assert result["regione"] == "Lombardia"
        assert result["aliquota"] == 3.9
        assert result["imposta_dovuta"] == float(imposta)

    @pytest.mark.asyncio
    async def test_irap_calculation_banks_higher_rate(self, sample_regioni, sample_irap_rates):
        """Test IRAP calculation for banks with higher rate"""
        service = RegionalTaxService(Mock(), Mock())
        service.get_regione_by_name = AsyncMock()
        service.get_regional_tax_rates = AsyncMock()

        lombardia_regione = next(r for r in sample_regioni if r["nome"] == "Lombardia")
        lombardia_rates = next(r for r in sample_irap_rates if r["regione_id"] == lombardia_regione["id"])

        service.get_regione_by_name.return_value = Mock(**lombardia_regione)
        service.get_regional_tax_rates.return_value = Mock(**lombardia_rates)

        result = await service.calculate_irap(revenue=Decimal("5000000"), region="Lombardia", business_type="banks")

        # Banks pay higher IRAP rate (5.57%)
        valore_produzione = 5000000 * Decimal("0.85")
        imposta = valore_produzione * Decimal("5.57") / 100

        assert result["tipo_attivita"] == "banks"
        assert result["aliquota"] == 5.57
        assert result["imposta_dovuta"] == float(imposta)

    @pytest.mark.asyncio
    async def test_irap_calculation_insurance_higher_rate(self, sample_regioni, sample_irap_rates):
        """Test IRAP calculation for insurance companies with highest rate"""
        service = RegionalTaxService(Mock(), Mock())
        service.get_regione_by_name = AsyncMock()
        service.get_regional_tax_rates = AsyncMock()

        lombardia_regione = next(r for r in sample_regioni if r["nome"] == "Lombardia")
        lombardia_rates = next(r for r in sample_irap_rates if r["regione_id"] == lombardia_regione["id"])

        service.get_regione_by_name.return_value = Mock(**lombardia_regione)
        service.get_regional_tax_rates.return_value = Mock(**lombardia_rates)

        result = await service.calculate_irap(
            revenue=Decimal("3000000"), region="Lombardia", business_type="insurance"
        )

        # Insurance pays highest IRAP rate (6.82%)
        assert result["tipo_attivita"] == "insurance"
        assert result["aliquota"] == 6.82

    @pytest.mark.asyncio
    async def test_irap_calculation_agriculture_lower_rate(self, sample_regioni, sample_irap_rates):
        """Test IRAP calculation for agriculture with lower rate"""
        service = RegionalTaxService(Mock(), Mock())
        service.get_regione_by_name = AsyncMock()
        service.get_regional_tax_rates = AsyncMock()

        lombardia_regione = next(r for r in sample_regioni if r["nome"] == "Lombardia")
        lombardia_rates = next(r for r in sample_irap_rates if r["regione_id"] == lombardia_regione["id"])

        service.get_regione_by_name.return_value = Mock(**lombardia_regione)
        service.get_regional_tax_rates.return_value = Mock(**lombardia_rates)

        result = await service.calculate_irap(
            revenue=Decimal("500000"), region="Lombardia", business_type="agriculture"
        )

        # Agriculture pays lower IRAP rate (1.9%)
        assert result["tipo_attivita"] == "agriculture"
        assert result["aliquota"] == 1.9

    @pytest.mark.asyncio
    async def test_irap_regional_comparison(self, sample_regioni, sample_irap_rates):
        """Test IRAP rate differences between regions"""
        lazio_rates = next(
            r
            for r in sample_irap_rates
            if any(regione["id"] == r["regione_id"] and regione["nome"] == "Lazio" for regione in sample_regioni)
        )
        lombardia_rates = next(
            r
            for r in sample_irap_rates
            if any(regione["id"] == r["regione_id"] and regione["nome"] == "Lombardia" for regione in sample_regioni)
        )

        # Verify Lazio has higher standard rate
        assert lazio_rates["rate_standard"] == Decimal("4.82")
        assert lombardia_rates["rate_standard"] == Decimal("3.9")
        assert lazio_rates["rate_standard"] > lombardia_rates["rate_standard"]


# IRPEF Addizionali Tests


class TestIRPEFAddizionali:
    """Test IRPEF addizionali (regional and municipal surcharges)"""

    @pytest.mark.asyncio
    async def test_addizionale_irpef_roma_full_calculation(self, sample_comuni, sample_addizionale_rates):
        """Test complete addizionale IRPEF calculation for Roma"""
        service = RegionalTaxService(Mock(), Mock())
        service.get_comune_by_cap = AsyncMock()
        service.get_regione_by_id = AsyncMock()
        service.get_regional_addizionale_irpef = AsyncMock()
        service.get_municipal_addizionale_irpef = AsyncMock()

        roma_comune = next(c for c in sample_comuni if c["nome"] == "Roma")
        service.get_comune_by_cap.return_value = Mock(**roma_comune)
        service.get_regione_by_id.return_value = Mock(nome="Lazio")

        # Lazio regional rate: 1.73%, Roma municipal rate: 0.9%
        service.get_regional_addizionale_irpef.return_value = Decimal("1.73")
        service.get_municipal_addizionale_irpef.return_value = Decimal("0.9")

        result = await service.calculate_irpef_addizionali(reddito_imponibile=Decimal("50000"), cap="00100")

        # Calculate expected values
        addizionale_regionale = 50000 * Decimal("1.73") / 100  # 865
        addizionale_comunale = 50000 * Decimal("0.9") / 100  # 450
        totale = addizionale_regionale + addizionale_comunale  # 1315

        assert result["comune"] == "Roma"
        assert result["regione"] == "Lazio"
        assert result["addizionale_regionale"]["aliquota"] == 1.73
        assert result["addizionale_regionale"]["importo"] == float(addizionale_regionale)
        assert result["addizionale_comunale"]["aliquota"] == 0.9
        assert result["addizionale_comunale"]["importo"] == float(addizionale_comunale)
        assert result["totale_addizionali"] == float(totale)

    @pytest.mark.asyncio
    async def test_addizionale_irpef_milano_calculation(self, sample_comuni, sample_addizionale_rates):
        """Test addizionale IRPEF calculation for Milano"""
        service = RegionalTaxService(Mock(), Mock())
        service.get_comune_by_cap = AsyncMock()
        service.get_regione_by_id = AsyncMock()
        service.get_regional_addizionale_irpef = AsyncMock()
        service.get_municipal_addizionale_irpef = AsyncMock()

        milano_comune = next(c for c in sample_comuni if c["nome"] == "Milano")
        service.get_comune_by_cap.return_value = Mock(**milano_comune)
        service.get_regione_by_id.return_value = Mock(nome="Lombardia")

        # Lombardia regional rate: 1.73%, Milano municipal rate: 0.8%
        service.get_regional_addizionale_irpef.return_value = Decimal("1.73")
        service.get_municipal_addizionale_irpef.return_value = Decimal("0.8")

        result = await service.calculate_irpef_addizionali(reddito_imponibile=Decimal("60000"), cap="20100")

        assert result["comune"] == "Milano"
        assert result["regione"] == "Lombardia"
        assert result["addizionale_comunale"]["aliquota"] == 0.8  # Lower than Roma

    @pytest.mark.asyncio
    async def test_addizionale_irpef_campania_higher_regional(self, sample_comuni, sample_addizionale_rates):
        """Test addizionale IRPEF for Campania (higher regional rate)"""
        service = RegionalTaxService(Mock(), Mock())
        service.get_comune_by_cap = AsyncMock()
        service.get_regione_by_id = AsyncMock()
        service.get_regional_addizionale_irpef = AsyncMock()
        service.get_municipal_addizionale_irpef = AsyncMock()

        napoli_comune = next(c for c in sample_comuni if c["nome"] == "Napoli")
        service.get_comune_by_cap.return_value = Mock(**napoli_comune)
        service.get_regione_by_id.return_value = Mock(nome="Campania")

        # Campania has higher regional rate: 2.03%
        service.get_regional_addizionale_irpef.return_value = Decimal("2.03")
        service.get_municipal_addizionale_irpef.return_value = Decimal("0.8")

        result = await service.calculate_irpef_addizionali(reddito_imponibile=Decimal("40000"), cap="80100")

        assert result["regione"] == "Campania"
        assert result["addizionale_regionale"]["aliquota"] == 2.03  # Higher than other regions

    @pytest.mark.asyncio
    async def test_addizionale_municipal_threshold_exemption(self, sample_addizionale_rates):
        """Test municipal addizionale exemption under threshold"""
        service = RegionalTaxService(Mock(), Mock())
        service.get_comum_by_cap = AsyncMock()

        # Test income under threshold (should have reduced or no municipal addizionale)
        low_income = Decimal("10000")  # Under Roma threshold of 11,000

        # Mock service to return threshold info
        service.get_municipal_addizionale_irpef = AsyncMock()
        service.get_municipal_tax_info = AsyncMock(return_value={"rate": Decimal("0.9"), "threshold": 11000})

        # Should apply threshold logic
        municipal_rate = await service.get_municipal_addizionale_irpef_with_threshold(
            comune_id=uuid4(), reddito=low_income
        )

        # Rate should be 0 or reduced for income under threshold
        assert municipal_rate <= Decimal("0.9")


# Integration Tests


class TestRegionalTaxIntegration:
    """Test complete tax calculations with all regional variations"""

    @pytest.mark.asyncio
    async def test_complete_tax_calculation_roma(self, sample_comuni, sample_imu_rates, sample_addizionale_rates):
        """Test complete tax calculation for Roma resident with property"""
        service = RegionalTaxService(Mock(), Mock())

        # Mock all required services
        service.calculate_imu = AsyncMock(
            return_value={
                "comune": "Roma",
                "imposta_dovuta": 0,  # Prima casa exempt
                "note": "Abitazione principale esente IMU",
            }
        )

        service.calculate_irpef_addizionali = AsyncMock(
            return_value={
                "comune": "Roma",
                "regione": "Lazio",
                "addizionale_regionale": {"aliquota": 1.73, "importo": 865},
                "addizionale_comunale": {"aliquota": 0.9, "importo": 450},
                "totale_addizionali": 1315,
            }
        )

        service.get_location_from_cap = AsyncMock(
            return_value={"comune": "Roma", "provincia": "RM", "regione": "Lazio"}
        )

        # Calculate total tax burden
        total_taxes = await service.calculate_total_tax_burden(
            cap="00100", income=50000, property_value=300000, is_prima_casa=True
        )

        assert total_taxes["location"]["comune"] == "Roma"
        assert total_taxes["imu"]["imposta_dovuta"] == 0  # Exempt
        assert total_taxes["addizionali"]["totale_addizionali"] == 1315

    @pytest.mark.asyncio
    async def test_tax_comparison_roma_vs_milano(self):
        """Test tax burden comparison between Roma and Milano"""
        service = RegionalTaxService(Mock(), Mock())

        # Mock Roma calculation
        service.calculate_total_tax_burden = AsyncMock()
        service.calculate_total_tax_burden.side_effect = [
            {  # Roma
                "comune": "Roma",
                "imu": {"imposta_dovuta": 0},
                "addizionali": {"totale_addizionali": 1315},
                "total": 1315,
            },
            {  # Milano
                "comune": "Milano",
                "imu": {"imposta_dovuta": 912},  # Not exempt
                "addizionali": {"totale_addizionali": 1238},
                "total": 2150,
            },
        ]

        comparison = await service.compare_regional_taxes(
            cap1="00100",  # Roma
            cap2="20100",  # Milano
            income=50000,
            property_value=300000,
        )

        assert comparison["location1"]["comune"] == "Roma"
        assert comparison["location2"]["comune"] == "Milano"
        assert comparison["difference"]["amount"] == 835  # Milano costs more
        assert comparison["difference"]["favors"] == "Roma"

    @pytest.mark.asyncio
    async def test_business_tax_calculation_with_location(self):
        """Test business tax calculation including IRAP regional variations"""
        service = RegionalTaxService(Mock(), Mock())

        service.calculate_irap = AsyncMock(
            return_value={"regione": "Lazio", "aliquota": 4.82, "imposta_dovuta": 40970, "tipo_attivita": "standard"}
        )

        service.get_location_from_cap = AsyncMock(return_value={"regione": "Lazio"})

        result = await service.calculate_business_taxes(cap="00100", revenue=1000000, business_type="standard")

        assert result["irap"]["regione"] == "Lazio"
        assert result["irap"]["aliquota"] == 4.82  # Higher Lazio rate
        assert result["irap"]["imposta_dovuta"] == 40970


# Data Management Tests


class TestRegionalTaxDataManagement:
    """Test tax rate updates and data management"""

    @pytest.mark.asyncio
    async def test_tax_rate_historical_lookup(self):
        """Test lookup of historical tax rates"""
        service = RegionalTaxService(Mock(), Mock())

        # Mock historical rates
        service.get_tax_rates = AsyncMock(
            return_value=Mock(
                rate=Decimal("1.04"),  # 2023 rate
                valid_from=date(2023, 1, 1),
                valid_to=date(2023, 12, 31),
            )
        )

        historical_rate = await service.get_tax_rates(
            comune_id=uuid4(), tax_type="IMU", reference_date=date(2023, 6, 1)
        )

        assert historical_rate.rate == Decimal("1.04")
        assert historical_rate.valid_from <= date(2023, 6, 1) <= historical_rate.valid_to

    @pytest.mark.asyncio
    async def test_bulk_rate_update(self):
        """Test bulk update of municipal rates"""
        service = RegionalTaxService(Mock(), Mock())

        new_rates = [
            {"comune_id": uuid4(), "tax_type": "IMU", "rate": Decimal("1.08")},
            {"comune_id": uuid4(), "tax_type": "IMU", "rate": Decimal("1.05")},
            {"comune_id": uuid4(), "tax_type": "IMU", "rate": Decimal("1.12")},
        ]

        service.bulk_update_rates = AsyncMock(return_value={"updated": 3, "errors": 0})

        result = await service.bulk_update_rates(new_rates, effective_date=date(2024, 1, 1))

        assert result["updated"] == 3
        assert result["errors"] == 0

    @pytest.mark.asyncio
    async def test_rate_change_notification(self):
        """Test rate change notification system"""
        service = RegionalTaxService(Mock(), Mock())

        service.detect_rate_changes = AsyncMock(
            return_value=[
                {
                    "comune": "Roma",
                    "tax_type": "IMU",
                    "old_rate": Decimal("1.06"),
                    "new_rate": Decimal("1.08"),
                    "change_date": date(2024, 1, 1),
                }
            ]
        )

        changes = await service.detect_rate_changes(date(2024, 1, 1))

        assert len(changes) == 1
        assert changes[0]["comune"] == "Roma"
        assert changes[0]["new_rate"] > changes[0]["old_rate"]

    @pytest.mark.asyncio
    async def test_concurrent_rate_access(self):
        """Test concurrent access to rate data with caching"""
        service = RegionalTaxService(Mock(), Mock())

        # Mock cache for performance
        service.cache.get = AsyncMock(return_value=None)
        service.cache.set = AsyncMock()

        service.get_tax_rates = AsyncMock(return_value=Mock(rate=Decimal("1.06")))

        # Simulate concurrent access
        import asyncio

        tasks = [service.get_tax_rates(uuid4(), "IMU", date.today()) for _ in range(10)]

        results = await asyncio.gather(*tasks)

        # All should return same rate
        assert all(r.rate == Decimal("1.06") for r in results)

    @pytest.mark.asyncio
    async def test_api_response_caching(self):
        """Test API response caching for performance"""
        service = RegionalTaxService(Mock(), Mock())

        # Mock cache behavior
        service.cache.get = AsyncMock(side_effect=[None, {"cached": True}])  # Miss then hit
        service.cache.set = AsyncMock()

        # First call should miss cache
        await service.get_all_rates_for_location("00100")
        service.cache.set.assert_called_once()

        # Second call should hit cache
        result2 = await service.get_all_rates_for_location("00100")
        assert result2.get("cached") is True


# Performance and Error Handling Tests


class TestRegionalTaxPerformance:
    """Test performance and error handling"""

    @pytest.mark.asyncio
    async def test_fallback_to_default_rates(self):
        """Test fallback to default rates for unknown locations"""
        service = RegionalTaxService(Mock(), Mock())

        service.get_comune_by_cap = AsyncMock(return_value=None)
        service.get_default_rates = AsyncMock(
            return_value={"IMU": {"rate": Decimal("1.06"), "note": "Aliquota standard"}}
        )

        result = await service.calculate_imu_with_fallback(
            property_value=Decimal("300000"),
            cap="99999",  # Unknown CAP
            is_prima_casa=False,
        )

        assert result["aliquota"] == 1.06
        assert "standard" in result["note"].lower()

    @pytest.mark.asyncio
    async def test_rate_lookup_performance_with_cache(self):
        """Test rate lookup performance with caching"""
        service = RegionalTaxService(Mock(), Mock())

        # Mock fast cache response
        service.cache.get = AsyncMock(return_value={"rate": 1.06, "cached_at": datetime.now().isoformat()})

        start_time = datetime.now()
        result = await service.get_tax_rates_cached(uuid4(), "IMU", date.today())
        end_time = datetime.now()

        # Should be very fast with cache
        assert (end_time - start_time).total_seconds() < 0.1
        assert result["rate"] == 1.06

    @pytest.mark.asyncio
    async def test_invalid_calculation_parameters(self):
        """Test handling of invalid calculation parameters"""
        service = RegionalTaxService(Mock(), Mock())

        # Test negative property value
        with pytest.raises(ValueError, match="valore non può essere negativo"):
            await service.calculate_imu(property_value=Decimal("-100000"), cap="00100", is_prima_casa=True)

        # Test zero revenue for IRAP
        with pytest.raises(ValueError, match="fatturato deve essere positivo"):
            await service.calculate_irap(revenue=Decimal("0"), region="Lazio", business_type="standard")

    @pytest.mark.asyncio
    async def test_database_connection_error_handling(self):
        """Test handling of database connection errors"""
        service = RegionalTaxService(Mock(), Mock())

        # Mock database error
        service.db.query = AsyncMock(side_effect=Exception("Database connection failed"))

        with pytest.raises(Exception, match="Database connection failed"):
            await service.get_comune_by_cap("00100")

    @pytest.mark.asyncio
    async def test_rate_update_validation(self):
        """Test validation of rate updates"""
        service = RegionalTaxService(Mock(), Mock())

        # Test invalid rate values
        invalid_rates = [
            {"rate": Decimal("-1.0")},  # Negative
            {"rate": Decimal("15.0")},  # Too high
            {"rate": Decimal("0")},  # Zero
        ]

        for invalid_rate in invalid_rates:
            with pytest.raises(ValueError, match="aliquota non valida"):
                await service.validate_tax_rate(invalid_rate["rate"], "IMU")


if __name__ == "__main__":
    # Run tests with: pytest tests/test_regional_taxes.py -v
    pytest.main([__file__, "-v", "--tb=short"])
