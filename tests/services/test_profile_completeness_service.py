"""Tests for ProfileCompletenessService.

Tests cover:
- Happy path: all clients have profiles and full data → empty report
- Edge case: client without profile → flags critico fields
- Edge case: societa without partita_iva → flags importante
- Edge case: client without email → flags importante
- Edge case: empty client_ids list → empty report
- Combined: multiple clients with various missing fields
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.client import Client, TipoCliente
from app.models.client_profile import ClientProfile, RegimeFiscale
from app.services.profile_completeness_service import (
    CompletenessReport,
    ProfileCompletenessService,
)


@pytest.fixture
def service() -> ProfileCompletenessService:
    return ProfileCompletenessService()


@pytest.fixture
def studio_id():
    return uuid4()


def _make_mock_db(rows: list[tuple]) -> AsyncMock:
    """Build a mock AsyncSession that returns the given rows from execute()."""
    mock_result = MagicMock()
    mock_result.all.return_value = rows

    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)
    return db


class TestProfileCompletenessService:
    """Test ProfileCompletenessService.analyze_imported_clients()."""

    @pytest.mark.asyncio
    async def test_empty_client_ids_returns_empty_report(self, service: ProfileCompletenessService, studio_id) -> None:
        """Edge case: empty client_ids returns empty report without DB query."""
        db = AsyncMock()
        report = await service.analyze_imported_clients(db, client_ids=[], studio_id=studio_id)
        assert isinstance(report, CompletenessReport)
        assert report.clients_without_profile == 0
        assert report.clients_missing_partita_iva == 0
        assert len(report.missing_fields) == 0
        db.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_client_with_profile_and_full_data(self, service: ProfileCompletenessService, studio_id) -> None:
        """Happy path: client with profile and all fields → no warnings."""
        client = Client(
            id=1,
            studio_id=studio_id,
            codice_fiscale="RSSMRA85M01H501Z",
            nome="Mario Rossi",
            tipo_cliente=TipoCliente.PERSONA_FISICA,
            comune="Roma",
            provincia="RM",
            email="mario@example.com",
            partita_iva="12345678901",
        )
        profile = ClientProfile(
            id=1,
            client_id=1,
            regime_fiscale=RegimeFiscale.ORDINARIO,
            codice_ateco_principale="69.10.10",
            data_inizio_attivita="2020-01-01",
        )
        db = _make_mock_db([(client, profile)])

        report = await service.analyze_imported_clients(db, client_ids=[1], studio_id=studio_id)
        assert report.clients_without_profile == 0
        assert report.clients_missing_partita_iva == 0
        assert len(report.missing_fields) == 0

    @pytest.mark.asyncio
    async def test_client_without_profile_flags_critico_fields(
        self, service: ProfileCompletenessService, studio_id
    ) -> None:
        """Client without ClientProfile → flags regime_fiscale, codice_ateco, data_inizio."""
        client = Client(
            id=1,
            studio_id=studio_id,
            codice_fiscale="RSSMRA85M01H501Z",
            nome="Mario Rossi",
            tipo_cliente=TipoCliente.PERSONA_FISICA,
            comune="Roma",
            provincia="RM",
            email="mario@example.com",
        )
        db = _make_mock_db([(client, None)])

        report = await service.analyze_imported_clients(db, client_ids=[1], studio_id=studio_id)
        assert report.clients_without_profile == 1

        field_names = [w.field for w in report.missing_fields]
        assert "regime_fiscale" in field_names
        assert "codice_ateco_principale" in field_names
        assert "data_inizio_attivita" in field_names

        # Check priorities
        critico_fields = [w for w in report.missing_fields if w.priority == "critico"]
        assert len(critico_fields) >= 2

    @pytest.mark.asyncio
    async def test_societa_without_partita_iva(self, service: ProfileCompletenessService, studio_id) -> None:
        """Societa without partita_iva → flags importante."""
        client = Client(
            id=2,
            studio_id=studio_id,
            codice_fiscale="12345678901",
            nome="Verdi S.r.l.",
            tipo_cliente=TipoCliente.SOCIETA,
            comune="Milano",
            provincia="MI",
            partita_iva=None,
            email="info@verdi.it",
        )
        profile = ClientProfile(
            id=2,
            client_id=2,
            regime_fiscale=RegimeFiscale.ORDINARIO,
            codice_ateco_principale="47.11.30",
            data_inizio_attivita="2015-06-01",
        )
        db = _make_mock_db([(client, profile)])

        report = await service.analyze_imported_clients(db, client_ids=[2], studio_id=studio_id)
        assert report.clients_missing_partita_iva == 1
        piva_warnings = [w for w in report.missing_fields if w.field == "partita_iva"]
        assert len(piva_warnings) == 1
        assert piva_warnings[0].priority == "importante"

    @pytest.mark.asyncio
    async def test_client_without_email(self, service: ProfileCompletenessService, studio_id) -> None:
        """Client without email → flags importante."""
        client = Client(
            id=3,
            studio_id=studio_id,
            codice_fiscale="RSSMRA85M01H501Z",
            nome="Mario Rossi",
            tipo_cliente=TipoCliente.PERSONA_FISICA,
            comune="Roma",
            provincia="RM",
            email=None,
        )
        profile = ClientProfile(
            id=3,
            client_id=3,
            regime_fiscale=RegimeFiscale.ORDINARIO,
            codice_ateco_principale="69.10.10",
            data_inizio_attivita="2020-01-01",
        )
        db = _make_mock_db([(client, profile)])

        report = await service.analyze_imported_clients(db, client_ids=[3], studio_id=studio_id)
        email_warnings = [w for w in report.missing_fields if w.field == "email"]
        assert len(email_warnings) == 1
        assert email_warnings[0].priority == "importante"

    @pytest.mark.asyncio
    async def test_multiple_clients_combined_warnings(self, service: ProfileCompletenessService, studio_id) -> None:
        """Multiple clients: one without profile, one societa without piva."""
        client1 = Client(
            id=1,
            studio_id=studio_id,
            codice_fiscale="RSSMRA85M01H501Z",
            nome="Mario Rossi",
            tipo_cliente=TipoCliente.PERSONA_FISICA,
            comune="Roma",
            provincia="RM",
            email="mario@example.com",
        )
        client2 = Client(
            id=2,
            studio_id=studio_id,
            codice_fiscale="12345678901",
            nome="Verdi S.r.l.",
            tipo_cliente=TipoCliente.SOCIETA,
            comune="Milano",
            provincia="MI",
            partita_iva=None,
            email=None,
        )
        profile2 = ClientProfile(
            id=2,
            client_id=2,
            regime_fiscale=RegimeFiscale.ORDINARIO,
            codice_ateco_principale="47.11.30",
            data_inizio_attivita="2015-06-01",
        )
        db = _make_mock_db(
            [
                (client1, None),
                (client2, profile2),
            ]
        )

        report = await service.analyze_imported_clients(db, client_ids=[1, 2], studio_id=studio_id)
        assert report.clients_without_profile == 1
        assert report.clients_missing_partita_iva == 1
        # client1: 3 profile fields (has email) = 3 warnings
        # client2: partita_iva + email = 2 warnings
        assert len(report.missing_fields) == 5

    @pytest.mark.asyncio
    async def test_persona_fisica_without_partita_iva_not_flagged(
        self, service: ProfileCompletenessService, studio_id
    ) -> None:
        """Persona fisica without partita_iva is NOT flagged (only societa/ditta)."""
        client = Client(
            id=4,
            studio_id=studio_id,
            codice_fiscale="RSSMRA85M01H501Z",
            nome="Mario Rossi",
            tipo_cliente=TipoCliente.PERSONA_FISICA,
            comune="Roma",
            provincia="RM",
            partita_iva=None,
            email="mario@example.com",
        )
        profile = ClientProfile(
            id=4,
            client_id=4,
            regime_fiscale=RegimeFiscale.FORFETTARIO,
            codice_ateco_principale="62.01.00",
            data_inizio_attivita="2022-01-01",
        )
        db = _make_mock_db([(client, profile)])

        report = await service.analyze_imported_clients(db, client_ids=[4], studio_id=studio_id)
        assert report.clients_missing_partita_iva == 0
        piva_warnings = [w for w in report.missing_fields if w.field == "partita_iva"]
        assert len(piva_warnings) == 0
