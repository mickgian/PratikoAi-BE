"""Tests for ClientProfile creation during client import.

TDD: Tests written FIRST before implementation.
Tests cover:
- Profile creation when profile fields present in import data
- Profile skipped when required profile fields missing
- Profile creation failure (bad ATECO) doesn't block client creation
- profiles_created counter in ImportReport
- Auto-detection aliases for profile fields (regime_fiscale, codice_ateco, etc.)
- Data pattern detection for ATECO codes
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.client_import_service import (
    ClientImportService,
    SuggestedColumnMapping,
)


@pytest.fixture
def svc() -> ClientImportService:
    return ClientImportService()


@pytest.fixture
def studio_id():
    return uuid4()


class TestProfileCreationDuringImport:
    """Profile is created alongside Client when profile fields are present."""

    @pytest.mark.asyncio
    async def test_profile_created_when_all_profile_fields_present(self, svc, studio_id) -> None:
        """When regime_fiscale, codice_ateco, data_inizio_attivita are present, profile is created."""
        mock_db = AsyncMock()
        mock_client = MagicMock()
        mock_client.id = 42

        records = [
            {
                "codice_fiscale": "RSSMRA85M01H501Z",
                "nome": "Mario Rossi",
                "comune": "Roma",
                "provincia": "RM",
                "regime_fiscale": "ordinario",
                "codice_ateco_principale": "62.01.00",
                "data_inizio_attivita": "2020-01-15",
            },
        ]

        with (
            patch.object(svc, "_client_service") as mock_cs,
            patch("app.services.client_import_service.client_profile_service") as mock_ps,
        ):
            mock_cs.create = AsyncMock(return_value=mock_client)
            mock_ps.create = AsyncMock()
            report = await svc.import_from_records(
                db=mock_db,
                studio_id=studio_id,
                records=records,
            )

        assert report.success_count == 1
        assert report.profiles_created == 1
        mock_ps.create.assert_awaited_once()
        call_kwargs = mock_ps.create.call_args.kwargs
        assert call_kwargs["client_id"] == 42
        assert call_kwargs["codice_ateco_principale"] == "62.01.00"
        assert call_kwargs["data_inizio_attivita"] == date(2020, 1, 15)

    @pytest.mark.asyncio
    async def test_profile_skipped_when_required_fields_missing(self, svc, studio_id) -> None:
        """When only some profile fields are present (missing data_inizio_attivita), profile is NOT created."""
        mock_db = AsyncMock()
        mock_client = MagicMock()
        mock_client.id = 42

        records = [
            {
                "codice_fiscale": "RSSMRA85M01H501Z",
                "nome": "Mario Rossi",
                "comune": "Roma",
                "provincia": "RM",
                "regime_fiscale": "ordinario",
                # missing codice_ateco_principale and data_inizio_attivita
            },
        ]

        with (
            patch.object(svc, "_client_service") as mock_cs,
            patch("app.services.client_import_service.client_profile_service") as mock_ps,
        ):
            mock_cs.create = AsyncMock(return_value=mock_client)
            report = await svc.import_from_records(
                db=mock_db,
                studio_id=studio_id,
                records=records,
            )

        assert report.success_count == 1
        assert report.profiles_created == 0
        mock_ps.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_profile_failure_does_not_block_client(self, svc, studio_id) -> None:
        """If profile creation raises ValueError (bad ATECO), client is still imported."""
        mock_db = AsyncMock()
        mock_client = MagicMock()
        mock_client.id = 42

        records = [
            {
                "codice_fiscale": "RSSMRA85M01H501Z",
                "nome": "Mario Rossi",
                "comune": "Roma",
                "provincia": "RM",
                "regime_fiscale": "ordinario",
                "codice_ateco_principale": "INVALID",
                "data_inizio_attivita": "2020-01-15",
            },
        ]

        with (
            patch.object(svc, "_client_service") as mock_cs,
            patch("app.services.client_import_service.client_profile_service") as mock_ps,
        ):
            mock_cs.create = AsyncMock(return_value=mock_client)
            mock_ps.create = AsyncMock(side_effect=ValueError("Formato codice ATECO non valido"))
            report = await svc.import_from_records(
                db=mock_db,
                studio_id=studio_id,
                records=records,
            )

        assert report.success_count == 1
        assert report.profiles_created == 0
        # Client still created despite profile failure
        assert len(report.created_client_ids) == 1

    @pytest.mark.asyncio
    async def test_optional_profile_fields_passed(self, svc, studio_id) -> None:
        """Optional profile fields (n_dipendenti, ccnl_applicato) are passed when present."""
        mock_db = AsyncMock()
        mock_client = MagicMock()
        mock_client.id = 42

        records = [
            {
                "codice_fiscale": "RSSMRA85M01H501Z",
                "nome": "Mario Rossi",
                "comune": "Roma",
                "provincia": "RM",
                "regime_fiscale": "forfettario",
                "codice_ateco_principale": "62.01.00",
                "data_inizio_attivita": "2020-06-01",
                "n_dipendenti": "5",
                "ccnl_applicato": "METALMECCANICI",
            },
        ]

        with (
            patch.object(svc, "_client_service") as mock_cs,
            patch("app.services.client_import_service.client_profile_service") as mock_ps,
        ):
            mock_cs.create = AsyncMock(return_value=mock_client)
            mock_ps.create = AsyncMock()
            report = await svc.import_from_records(
                db=mock_db,
                studio_id=studio_id,
                records=records,
            )

        assert report.profiles_created == 1
        call_kwargs = mock_ps.create.call_args.kwargs
        assert call_kwargs["n_dipendenti"] == 5
        assert call_kwargs["ccnl_applicato"] == "METALMECCANICI"

    @pytest.mark.asyncio
    async def test_multiple_records_mixed_profile_creation(self, svc, studio_id) -> None:
        """Batch import: some records have profile fields, some don't."""
        mock_db = AsyncMock()
        client1 = MagicMock()
        client1.id = 1
        client2 = MagicMock()
        client2.id = 2

        records = [
            {
                "codice_fiscale": "RSSMRA85M01H501Z",
                "nome": "Mario Rossi",
                "comune": "Roma",
                "provincia": "RM",
                "regime_fiscale": "ordinario",
                "codice_ateco_principale": "62.01.00",
                "data_inizio_attivita": "2020-01-15",
            },
            {
                "codice_fiscale": "BNCLGU90A01F205X",
                "nome": "Luigi Bianchi",
                "comune": "Milano",
                "provincia": "MI",
                # No profile fields
            },
        ]

        with (
            patch.object(svc, "_client_service") as mock_cs,
            patch("app.services.client_import_service.client_profile_service") as mock_ps,
        ):
            mock_cs.create = AsyncMock(side_effect=[client1, client2])
            mock_ps.create = AsyncMock()
            report = await svc.import_from_records(
                db=mock_db,
                studio_id=studio_id,
                records=records,
            )

        assert report.success_count == 2
        assert report.profiles_created == 1
        mock_ps.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_invalid_date_skips_profile(self, svc, studio_id) -> None:
        """If data_inizio_attivita can't be parsed, profile is skipped."""
        mock_db = AsyncMock()
        mock_client = MagicMock()
        mock_client.id = 42

        records = [
            {
                "codice_fiscale": "RSSMRA85M01H501Z",
                "nome": "Mario Rossi",
                "comune": "Roma",
                "provincia": "RM",
                "regime_fiscale": "ordinario",
                "codice_ateco_principale": "62.01.00",
                "data_inizio_attivita": "not-a-date",
            },
        ]

        with (
            patch.object(svc, "_client_service") as mock_cs,
            patch("app.services.client_import_service.client_profile_service") as mock_ps,
        ):
            mock_cs.create = AsyncMock(return_value=mock_client)
            report = await svc.import_from_records(
                db=mock_db,
                studio_id=studio_id,
                records=records,
            )

        assert report.success_count == 1
        assert report.profiles_created == 0
        mock_ps.create.assert_not_called()


class TestProfileFieldAutoDetection:
    """Auto-detection aliases and patterns for profile fields."""

    def test_alias_regime_fiscale(self, svc: ClientImportService) -> None:
        """'regime fiscale' and variants are detected as regime_fiscale."""
        headers = ["regime fiscale", "codice_fiscale", "nome"]
        result = svc.auto_detect_column_mapping(headers, [])
        assert "regime_fiscale" in result
        assert result["regime_fiscale"].confidence == 1.0

    def test_alias_codice_ateco(self, svc: ClientImportService) -> None:
        """'codice ateco' and variants are detected as codice_ateco_principale."""
        headers = ["codice ateco", "codice_fiscale"]
        result = svc.auto_detect_column_mapping(headers, [])
        assert "codice_ateco_principale" in result
        assert result["codice_ateco_principale"].confidence == 1.0

    def test_alias_n_dipendenti(self, svc: ClientImportService) -> None:
        """'n. dipendenti' and variants are detected as n_dipendenti."""
        headers = ["n. dipendenti"]
        result = svc.auto_detect_column_mapping(headers, [])
        assert "n_dipendenti" in result
        assert result["n_dipendenti"].confidence == 1.0

    def test_alias_ccnl(self, svc: ClientImportService) -> None:
        """'ccnl' is detected as ccnl_applicato."""
        headers = ["ccnl"]
        result = svc.auto_detect_column_mapping(headers, [])
        assert "ccnl_applicato" in result
        assert result["ccnl_applicato"].confidence == 1.0

    def test_alias_data_inizio_attivita(self, svc: ClientImportService) -> None:
        """'data inizio attività' is detected as data_inizio_attivita."""
        headers = ["data inizio attività"]
        result = svc.auto_detect_column_mapping(headers, [])
        assert "data_inizio_attivita" in result
        assert result["data_inizio_attivita"].confidence == 1.0

    def test_pattern_detects_ateco_code(self, svc: ClientImportService) -> None:
        """Column with XX.XX.XX values is detected as codice_ateco_principale via data pattern."""
        headers = ["settore"]
        sample_rows = [
            {"settore": "62.01.00"},
            {"settore": "47.11.40"},
            {"settore": "56.10.11"},
        ]
        result = svc.auto_detect_column_mapping(headers, sample_rows)
        assert "codice_ateco_principale" in result
        assert result["codice_ateco_principale"].match_method == "data_pattern"

    def test_all_15_fields_detected_standard_file(self, svc: ClientImportService) -> None:
        """A file with all 15 standard headers gets all columns auto-mapped."""
        headers = [
            "codice_fiscale",
            "nome",
            "tipo_cliente",
            "comune",
            "provincia",
            "partita_iva",
            "email",
            "phone",
            "indirizzo",
            "cap",
            "regime_fiscale",
            "codice_ateco_principale",
            "n_dipendenti",
            "ccnl_applicato",
            "data_inizio_attivita",
        ]
        result = svc.auto_detect_column_mapping(headers, [])
        for field in headers:
            assert field in result, f"Missing auto-detection for {field}"
            assert result[field].confidence == 1.0


class TestProfileOverrides:
    """Per-client profile overrides keyed by codice_fiscale."""

    @pytest.mark.asyncio
    async def test_overrides_applied_per_client(self, svc, studio_id) -> None:
        """Each client gets their own profile data via codice_fiscale key."""
        mock_db = AsyncMock()
        client1 = MagicMock()
        client1.id = 1
        client2 = MagicMock()
        client2.id = 2

        records = [
            {
                "codice_fiscale": "RSSMRA85M01H501Z",
                "nome": "Mario Rossi",
                "comune": "Roma",
                "provincia": "RM",
            },
            {
                "codice_fiscale": "BNCLGU90A01F205X",
                "nome": "Luigi Bianchi",
                "comune": "Milano",
                "provincia": "MI",
            },
        ]

        profile_overrides = {
            "RSSMRA85M01H501Z": {
                "regime_fiscale": "ordinario",
                "codice_ateco_principale": "62.01.00",
                "data_inizio_attivita": "2020-01-15",
            },
            "BNCLGU90A01F205X": {
                "regime_fiscale": "forfettario",
                "codice_ateco_principale": "47.11.40",
                "data_inizio_attivita": "2019-06-01",
            },
        }

        with (
            patch.object(svc, "_client_service") as mock_cs,
            patch("app.services.client_import_service.client_profile_service") as mock_ps,
        ):
            mock_cs.create = AsyncMock(side_effect=[client1, client2])
            mock_ps.create = AsyncMock()
            report = await svc.import_from_records(
                db=mock_db,
                studio_id=studio_id,
                records=records,
                profile_overrides=profile_overrides,
            )

        assert report.success_count == 2
        assert report.profiles_created == 2
        # Check that different ATECO codes were used
        calls = mock_ps.create.call_args_list
        assert calls[0].kwargs["codice_ateco_principale"] == "62.01.00"
        assert calls[1].kwargs["codice_ateco_principale"] == "47.11.40"

    @pytest.mark.asyncio
    async def test_override_only_for_matching_cf(self, svc, studio_id) -> None:
        """Only clients with a matching override get profiles; others don't."""
        mock_db = AsyncMock()
        client1 = MagicMock()
        client1.id = 1
        client2 = MagicMock()
        client2.id = 2

        records = [
            {
                "codice_fiscale": "RSSMRA85M01H501Z",
                "nome": "Mario Rossi",
                "comune": "Roma",
                "provincia": "RM",
            },
            {
                "codice_fiscale": "BNCLGU90A01F205X",
                "nome": "Luigi Bianchi",
                "comune": "Milano",
                "provincia": "MI",
            },
        ]

        profile_overrides = {
            "RSSMRA85M01H501Z": {
                "regime_fiscale": "ordinario",
                "codice_ateco_principale": "62.01.00",
                "data_inizio_attivita": "2020-01-15",
            },
            # No override for BNCLGU90A01F205X
        }

        with (
            patch.object(svc, "_client_service") as mock_cs,
            patch("app.services.client_import_service.client_profile_service") as mock_ps,
        ):
            mock_cs.create = AsyncMock(side_effect=[client1, client2])
            mock_ps.create = AsyncMock()
            report = await svc.import_from_records(
                db=mock_db,
                studio_id=studio_id,
                records=records,
                profile_overrides=profile_overrides,
            )

        assert report.success_count == 2
        assert report.profiles_created == 1

    @pytest.mark.asyncio
    async def test_overrides_with_optional_fields(self, svc, studio_id) -> None:
        """Per-client overrides can include optional fields."""
        mock_db = AsyncMock()
        mock_client = MagicMock()
        mock_client.id = 42

        records = [
            {
                "codice_fiscale": "RSSMRA85M01H501Z",
                "nome": "Mario Rossi",
                "comune": "Roma",
                "provincia": "RM",
            },
        ]

        profile_overrides = {
            "RSSMRA85M01H501Z": {
                "regime_fiscale": "semplificato",
                "codice_ateco_principale": "62.01.00",
                "data_inizio_attivita": "2020-01-15",
                "n_dipendenti": "3",
                "ccnl_applicato": "COMMERCIO",
            },
        }

        with (
            patch.object(svc, "_client_service") as mock_cs,
            patch("app.services.client_import_service.client_profile_service") as mock_ps,
        ):
            mock_cs.create = AsyncMock(return_value=mock_client)
            mock_ps.create = AsyncMock()
            report = await svc.import_from_records(
                db=mock_db,
                studio_id=studio_id,
                records=records,
                profile_overrides=profile_overrides,
            )

        assert report.profiles_created == 1
        call_kwargs = mock_ps.create.call_args.kwargs
        assert call_kwargs["n_dipendenti"] == 3
        assert call_kwargs["ccnl_applicato"] == "COMMERCIO"

    @pytest.mark.asyncio
    async def test_no_overrides_no_profile_created(self, svc, studio_id) -> None:
        """Without overrides and without profile fields in file, no profile is created."""
        mock_db = AsyncMock()
        mock_client = MagicMock()
        mock_client.id = 42

        records = [
            {
                "codice_fiscale": "RSSMRA85M01H501Z",
                "nome": "Mario Rossi",
                "comune": "Roma",
                "provincia": "RM",
            },
        ]

        with (
            patch.object(svc, "_client_service") as mock_cs,
            patch("app.services.client_import_service.client_profile_service") as mock_ps,
        ):
            mock_cs.create = AsyncMock(return_value=mock_client)
            report = await svc.import_from_records(
                db=mock_db,
                studio_id=studio_id,
                records=records,
            )

        assert report.success_count == 1
        assert report.profiles_created == 0
        mock_ps.create.assert_not_called()
