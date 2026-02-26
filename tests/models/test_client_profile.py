"""DEV-302: Tests for ClientProfile SQLModel."""

import re
import sys
from datetime import date
from types import ModuleType
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

# Mock the database service to avoid needing a live PostgreSQL connection
if "app.services.database" not in sys.modules:
    _db_stub = ModuleType("app.services.database")
    _db_stub.database_service = MagicMock()  # type: ignore[attr-defined]
    sys.modules["app.services.database"] = _db_stub

from app.models.client_profile import (
    ClientProfile,
    PosizioneAgenziaEntrate,
    RegimeFiscale,
)


class TestClientProfileCreation:
    """Test ClientProfile model creation and field defaults."""

    def test_client_profile_creation_valid(self) -> None:
        """Valid profile with all required fields."""
        profile = ClientProfile(
            client_id=1,
            codice_ateco_principale="62.01.00",
            regime_fiscale=RegimeFiscale.ORDINARIO,
            n_dipendenti=5,
            data_inizio_attivita=date(2020, 1, 15),
        )

        assert profile.client_id == 1
        assert profile.codice_ateco_principale == "62.01.00"
        assert profile.regime_fiscale == RegimeFiscale.ORDINARIO
        assert profile.n_dipendenti == 5
        assert profile.data_inizio_attivita == date(2020, 1, 15)

    def test_client_profile_one_to_one_fk(self) -> None:
        """client_id references Client table."""
        profile = ClientProfile(
            client_id=42,
            codice_ateco_principale="47.11.00",
            regime_fiscale=RegimeFiscale.FORFETTARIO,
            n_dipendenti=0,
            data_inizio_attivita=date(2021, 6, 1),
        )
        assert profile.client_id == 42


class TestClientProfileEnums:
    """Test enum field values."""

    def test_regime_fiscale_enum_values(self) -> None:
        """All RegimeFiscale enum values are valid."""
        assert RegimeFiscale.ORDINARIO == "ordinario"
        assert RegimeFiscale.SEMPLIFICATO == "semplificato"
        assert RegimeFiscale.FORFETTARIO == "forfettario"
        assert RegimeFiscale.AGRICOLO == "agricolo"
        assert RegimeFiscale.MINIMI == "minimi"

    def test_posizione_agenzia_entrate_enum_values(self) -> None:
        """All PosizioneAgenziaEntrate enum values are valid."""
        assert PosizioneAgenziaEntrate.REGOLARE == "regolare"
        assert PosizioneAgenziaEntrate.IRREGOLARE == "irregolare"
        assert PosizioneAgenziaEntrate.IN_VERIFICA == "in_verifica"


class TestClientProfileATECO:
    """Test ATECO code format validation."""

    def test_ateco_format_valid(self) -> None:
        """XX.XX.XX is a valid ATECO code format."""
        profile = ClientProfile(
            client_id=1,
            codice_ateco_principale="62.01.00",
            regime_fiscale=RegimeFiscale.ORDINARIO,
            n_dipendenti=0,
            data_inizio_attivita=date(2020, 1, 1),
        )
        assert profile.is_valid_ateco(profile.codice_ateco_principale)

    def test_ateco_format_invalid(self) -> None:
        """Invalid ATECO format is rejected by helper."""
        profile = ClientProfile(
            client_id=1,
            codice_ateco_principale="INVALID",
            regime_fiscale=RegimeFiscale.ORDINARIO,
            n_dipendenti=0,
            data_inizio_attivita=date(2020, 1, 1),
        )
        assert not profile.is_valid_ateco(profile.codice_ateco_principale)

    def test_ateco_format_partial(self) -> None:
        """Partial code (e.g. XX.XX) fails validation."""
        profile = ClientProfile(
            client_id=1,
            codice_ateco_principale="62.01",
            regime_fiscale=RegimeFiscale.ORDINARIO,
            n_dipendenti=0,
            data_inizio_attivita=date(2020, 1, 1),
        )
        assert not profile.is_valid_ateco(profile.codice_ateco_principale)


class TestClientProfileOptionalFields:
    """Test optional fields and defaults."""

    def test_optional_fields_default_none(self) -> None:
        """Optional fields default to None."""
        profile = ClientProfile(
            client_id=1,
            codice_ateco_principale="62.01.00",
            regime_fiscale=RegimeFiscale.ORDINARIO,
            n_dipendenti=0,
            data_inizio_attivita=date(2020, 1, 1),
        )
        assert profile.ccnl_applicato is None
        assert profile.data_cessazione_attivita is None
        assert profile.immobili is None
        assert profile.posizione_agenzia_entrate is None

    def test_n_dipendenti_default_zero(self) -> None:
        """n_dipendenti defaults to 0."""
        profile = ClientProfile(
            client_id=1,
            codice_ateco_principale="62.01.00",
            regime_fiscale=RegimeFiscale.ORDINARIO,
            data_inizio_attivita=date(2020, 1, 1),
        )
        assert profile.n_dipendenti == 0

    def test_codici_ateco_secondari_default_empty(self) -> None:
        """codici_ateco_secondari defaults to empty list."""
        profile = ClientProfile(
            client_id=1,
            codice_ateco_principale="62.01.00",
            regime_fiscale=RegimeFiscale.ORDINARIO,
            n_dipendenti=0,
            data_inizio_attivita=date(2020, 1, 1),
        )
        assert profile.codici_ateco_secondari == []

    def test_codici_ateco_secondari_with_values(self) -> None:
        """codici_ateco_secondari can hold multiple codes."""
        profile = ClientProfile(
            client_id=1,
            codice_ateco_principale="62.01.00",
            codici_ateco_secondari=["63.11.19", "58.29.00"],
            regime_fiscale=RegimeFiscale.ORDINARIO,
            n_dipendenti=0,
            data_inizio_attivita=date(2020, 1, 1),
        )
        assert len(profile.codici_ateco_secondari) == 2
        assert "63.11.19" in profile.codici_ateco_secondari

    def test_immobili_jsonb(self) -> None:
        """Immobili field stores property JSONB."""
        immobili = [
            {
                "tipo": "ABITAZIONE_PRINCIPALE",
                "comune": "Roma",
                "rendita_catastale": 1000.00,
                "percentuale_possesso": 100,
            }
        ]
        profile = ClientProfile(
            client_id=1,
            codice_ateco_principale="62.01.00",
            regime_fiscale=RegimeFiscale.ORDINARIO,
            n_dipendenti=0,
            data_inizio_attivita=date(2020, 1, 1),
            immobili=immobili,
        )
        assert profile.immobili is not None
        assert profile.immobili[0]["tipo"] == "ABITAZIONE_PRINCIPALE"
        assert profile.immobili[0]["rendita_catastale"] == 1000.00

    def test_ccnl_applicato(self) -> None:
        """CCNL field stores contract name."""
        profile = ClientProfile(
            client_id=1,
            codice_ateco_principale="47.11.00",
            regime_fiscale=RegimeFiscale.SEMPLIFICATO,
            n_dipendenti=3,
            data_inizio_attivita=date(2019, 3, 1),
            ccnl_applicato="Commercio",
        )
        assert profile.ccnl_applicato == "Commercio"

    def test_data_cessazione(self) -> None:
        """Cessation date tracks business closure."""
        profile = ClientProfile(
            client_id=1,
            codice_ateco_principale="62.01.00",
            regime_fiscale=RegimeFiscale.ORDINARIO,
            n_dipendenti=0,
            data_inizio_attivita=date(2015, 1, 1),
            data_cessazione_attivita=date(2024, 12, 31),
        )
        assert profile.data_cessazione_attivita == date(2024, 12, 31)

    def test_posizione_agenzia_entrate_set(self) -> None:
        """Posizione enum can be set."""
        profile = ClientProfile(
            client_id=1,
            codice_ateco_principale="62.01.00",
            regime_fiscale=RegimeFiscale.ORDINARIO,
            n_dipendenti=0,
            data_inizio_attivita=date(2020, 1, 1),
            posizione_agenzia_entrate=PosizioneAgenziaEntrate.REGOLARE,
        )
        assert profile.posizione_agenzia_entrate == PosizioneAgenziaEntrate.REGOLARE


class TestClientProfileRepr:
    """Test __repr__ output."""

    def test_repr(self) -> None:
        """__repr__ includes client_id and regime."""
        profile = ClientProfile(
            client_id=7,
            codice_ateco_principale="62.01.00",
            regime_fiscale=RegimeFiscale.FORFETTARIO,
            n_dipendenti=0,
            data_inizio_attivita=date(2020, 1, 1),
        )
        r = repr(profile)
        assert "7" in r
        assert "forfettario" in r
