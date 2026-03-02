"""DEV-428: Tests for ClientProfile INPS/INAIL extension fields."""

import sys
from datetime import date
from types import ModuleType
from unittest.mock import MagicMock

import pytest

# Mock the database service to avoid needing a live PostgreSQL connection
if "app.services.database" not in sys.modules:
    _db_stub = ModuleType("app.services.database")
    _db_stub.database_service = MagicMock()  # type: ignore[attr-defined]
    sys.modules["app.services.database"] = _db_stub

from app.models.client_profile import (
    ClientProfile,
    PosizionePrevidenziale,
    RegimeFiscale,
)


def _make_profile(**overrides: object) -> ClientProfile:
    """Create a ClientProfile with sensible defaults, merging *overrides*."""
    defaults: dict = {
        "client_id": 1,
        "codice_ateco_principale": "62.01.00",
        "regime_fiscale": RegimeFiscale.ORDINARIO,
        "n_dipendenti": 0,
        "data_inizio_attivita": date(2020, 1, 1),
    }
    defaults.update(overrides)
    return ClientProfile(**defaults)


class TestPosizionePrevidenziale:
    """Test PosizionePrevidenziale enum values."""

    def test_enum_regolare(self) -> None:
        """REGOLARE value is 'regolare'."""
        assert PosizionePrevidenziale.REGOLARE == "regolare"

    def test_enum_irregolare(self) -> None:
        """IRREGOLARE value is 'irregolare'."""
        assert PosizionePrevidenziale.IRREGOLARE == "irregolare"

    def test_enum_non_iscritto(self) -> None:
        """NON_ISCRITTO value is 'non_iscritto'."""
        assert PosizionePrevidenziale.NON_ISCRITTO == "non_iscritto"

    def test_enum_sospeso(self) -> None:
        """SOSPESO value is 'sospeso'."""
        assert PosizionePrevidenziale.SOSPESO == "sospeso"

    def test_enum_member_count(self) -> None:
        """Enum has exactly 4 members."""
        assert len(PosizionePrevidenziale) == 4


class TestINPSINAILNullableDefaults:
    """All new INPS/INAIL fields default to None."""

    def test_all_inps_inail_fields_default_none(self) -> None:
        """All INPS/INAIL fields are None by default."""
        profile = _make_profile()

        assert profile.inps_matricola is None
        assert profile.inps_status is None
        assert profile.inps_ultimo_pagamento is None
        assert profile.inail_pat is None
        assert profile.inail_status is None

    def test_inps_matricola_default_none(self) -> None:
        """inps_matricola defaults to None."""
        profile = _make_profile()
        assert profile.inps_matricola is None

    def test_inps_status_default_none(self) -> None:
        """inps_status defaults to None."""
        profile = _make_profile()
        assert profile.inps_status is None

    def test_inps_ultimo_pagamento_default_none(self) -> None:
        """inps_ultimo_pagamento defaults to None."""
        profile = _make_profile()
        assert profile.inps_ultimo_pagamento is None

    def test_inail_pat_default_none(self) -> None:
        """inail_pat defaults to None."""
        profile = _make_profile()
        assert profile.inail_pat is None

    def test_inail_status_default_none(self) -> None:
        """inail_status defaults to None."""
        profile = _make_profile()
        assert profile.inail_status is None


class TestINPSMatricola:
    """Test inps_matricola string field."""

    def test_valid_inps_matricola(self) -> None:
        """A valid INPS matricola is stored correctly."""
        profile = _make_profile(inps_matricola="1234567890")
        assert profile.inps_matricola == "1234567890"

    def test_inps_matricola_alphanumeric(self) -> None:
        """Alphanumeric matricola is accepted."""
        profile = _make_profile(inps_matricola="ABC1234567")
        assert profile.inps_matricola == "ABC1234567"

    def test_inps_matricola_max_length_boundary(self) -> None:
        """Matricola at max length (20 chars) is stored."""
        matricola = "A" * 20
        profile = _make_profile(inps_matricola=matricola)
        assert profile.inps_matricola == matricola
        assert len(profile.inps_matricola) == 20


class TestINAILPat:
    """Test inail_pat string field."""

    def test_valid_inail_pat(self) -> None:
        """A valid INAIL PAT number is stored correctly."""
        profile = _make_profile(inail_pat="12345678")
        assert profile.inail_pat == "12345678"

    def test_inail_pat_alphanumeric(self) -> None:
        """Alphanumeric PAT is accepted."""
        profile = _make_profile(inail_pat="PAT12345678")
        assert profile.inail_pat == "PAT12345678"

    def test_inail_pat_max_length_boundary(self) -> None:
        """PAT at max length (20 chars) is stored."""
        pat = "P" * 20
        profile = _make_profile(inail_pat=pat)
        assert profile.inail_pat == pat
        assert len(profile.inail_pat) == 20


class TestINPSStatus:
    """Test inps_status enum field."""

    def test_inps_status_regolare(self) -> None:
        """inps_status can be set to REGOLARE."""
        profile = _make_profile(inps_status=PosizionePrevidenziale.REGOLARE)
        assert profile.inps_status == PosizionePrevidenziale.REGOLARE

    def test_inps_status_irregolare(self) -> None:
        """inps_status can be set to IRREGOLARE."""
        profile = _make_profile(inps_status=PosizionePrevidenziale.IRREGOLARE)
        assert profile.inps_status == PosizionePrevidenziale.IRREGOLARE

    def test_inps_status_non_iscritto(self) -> None:
        """inps_status can be set to NON_ISCRITTO."""
        profile = _make_profile(inps_status=PosizionePrevidenziale.NON_ISCRITTO)
        assert profile.inps_status == PosizionePrevidenziale.NON_ISCRITTO

    def test_inps_status_sospeso(self) -> None:
        """inps_status can be set to SOSPESO."""
        profile = _make_profile(inps_status=PosizionePrevidenziale.SOSPESO)
        assert profile.inps_status == PosizionePrevidenziale.SOSPESO


class TestINAILStatus:
    """Test inail_status enum field."""

    def test_inail_status_regolare(self) -> None:
        """inail_status can be set to REGOLARE."""
        profile = _make_profile(inail_status=PosizionePrevidenziale.REGOLARE)
        assert profile.inail_status == PosizionePrevidenziale.REGOLARE

    def test_inail_status_irregolare(self) -> None:
        """inail_status can be set to IRREGOLARE."""
        profile = _make_profile(inail_status=PosizionePrevidenziale.IRREGOLARE)
        assert profile.inail_status == PosizionePrevidenziale.IRREGOLARE

    def test_inail_status_non_iscritto(self) -> None:
        """inail_status can be set to NON_ISCRITTO."""
        profile = _make_profile(inail_status=PosizionePrevidenziale.NON_ISCRITTO)
        assert profile.inail_status == PosizionePrevidenziale.NON_ISCRITTO

    def test_inail_status_sospeso(self) -> None:
        """inail_status can be set to SOSPESO."""
        profile = _make_profile(inail_status=PosizionePrevidenziale.SOSPESO)
        assert profile.inail_status == PosizionePrevidenziale.SOSPESO


class TestINPSUltimoPagamento:
    """Test inps_ultimo_pagamento date field."""

    def test_valid_inps_ultimo_pagamento(self) -> None:
        """A valid date is stored correctly."""
        payment_date = date(2025, 6, 15)
        profile = _make_profile(inps_ultimo_pagamento=payment_date)
        assert profile.inps_ultimo_pagamento == date(2025, 6, 15)

    def test_inps_ultimo_pagamento_past_date(self) -> None:
        """A past date is accepted."""
        profile = _make_profile(inps_ultimo_pagamento=date(2020, 1, 1))
        assert profile.inps_ultimo_pagamento == date(2020, 1, 1)

    def test_inps_ultimo_pagamento_recent_date(self) -> None:
        """A recent date is accepted."""
        profile = _make_profile(inps_ultimo_pagamento=date(2026, 2, 28))
        assert profile.inps_ultimo_pagamento == date(2026, 2, 28)


class TestAllINPSINAILFieldsTogether:
    """Test setting all INPS/INAIL fields simultaneously."""

    def test_all_fields_set(self) -> None:
        """All INPS/INAIL fields can be set together."""
        profile = _make_profile(
            inps_matricola="1234567890",
            inps_status=PosizionePrevidenziale.REGOLARE,
            inps_ultimo_pagamento=date(2025, 12, 31),
            inail_pat="PAT9876543",
            inail_status=PosizionePrevidenziale.IRREGOLARE,
        )

        assert profile.inps_matricola == "1234567890"
        assert profile.inps_status == PosizionePrevidenziale.REGOLARE
        assert profile.inps_ultimo_pagamento == date(2025, 12, 31)
        assert profile.inail_pat == "PAT9876543"
        assert profile.inail_status == PosizionePrevidenziale.IRREGOLARE

    def test_inps_inail_with_existing_fields(self) -> None:
        """INPS/INAIL fields coexist with all existing ClientProfile fields."""
        profile = _make_profile(
            client_id=42,
            codice_ateco_principale="47.11.00",
            regime_fiscale=RegimeFiscale.FORFETTARIO,
            n_dipendenti=3,
            ccnl_applicato="Commercio",
            data_inizio_attivita=date(2019, 3, 1),
            inps_matricola="INPS001",
            inps_status=PosizionePrevidenziale.REGOLARE,
            inps_ultimo_pagamento=date(2025, 11, 30),
            inail_pat="INAIL001",
            inail_status=PosizionePrevidenziale.REGOLARE,
        )

        # Existing fields intact
        assert profile.client_id == 42
        assert profile.codice_ateco_principale == "47.11.00"
        assert profile.regime_fiscale == RegimeFiscale.FORFETTARIO
        assert profile.n_dipendenti == 3
        assert profile.ccnl_applicato == "Commercio"

        # New fields set
        assert profile.inps_matricola == "INPS001"
        assert profile.inps_status == PosizionePrevidenziale.REGOLARE
        assert profile.inps_ultimo_pagamento == date(2025, 11, 30)
        assert profile.inail_pat == "INAIL001"
        assert profile.inail_status == PosizionePrevidenziale.REGOLARE

    def test_mixed_inps_inail_statuses(self) -> None:
        """INPS and INAIL can have different statuses."""
        profile = _make_profile(
            inps_status=PosizionePrevidenziale.REGOLARE,
            inail_status=PosizionePrevidenziale.SOSPESO,
        )
        assert profile.inps_status == PosizionePrevidenziale.REGOLARE
        assert profile.inail_status == PosizionePrevidenziale.SOSPESO

    def test_partial_inps_only(self) -> None:
        """Only INPS fields set, INAIL fields remain None."""
        profile = _make_profile(
            inps_matricola="1234567890",
            inps_status=PosizionePrevidenziale.NON_ISCRITTO,
            inps_ultimo_pagamento=date(2024, 6, 15),
        )
        assert profile.inps_matricola == "1234567890"
        assert profile.inps_status == PosizionePrevidenziale.NON_ISCRITTO
        assert profile.inps_ultimo_pagamento == date(2024, 6, 15)
        assert profile.inail_pat is None
        assert profile.inail_status is None

    def test_partial_inail_only(self) -> None:
        """Only INAIL fields set, INPS fields remain None."""
        profile = _make_profile(
            inail_pat="PAT5555555",
            inail_status=PosizionePrevidenziale.SOSPESO,
        )
        assert profile.inps_matricola is None
        assert profile.inps_status is None
        assert profile.inps_ultimo_pagamento is None
        assert profile.inail_pat == "PAT5555555"
        assert profile.inail_status == PosizionePrevidenziale.SOSPESO
