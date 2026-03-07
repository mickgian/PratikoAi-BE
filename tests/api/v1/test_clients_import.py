"""Tests for POST /clients/import and POST /clients/import/preview endpoints.

TDD: Tests written FIRST before implementation.
Tests cover Excel, CSV upload, unsupported format rejection,
preview endpoint, column mapping, and post-import warnings.
"""

import io
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import UploadFile

from app.services.client_import_service import ImportReport, ImportRowError, PreviewRow


@pytest.fixture
def mock_db() -> AsyncMock:
    session = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def studio_id():
    return uuid4()


def _make_upload_file(filename: str, content: bytes) -> UploadFile:
    """Build a FastAPI UploadFile from in-memory content."""
    return UploadFile(filename=filename, file=io.BytesIO(content))


class TestImportClientsEndpoint:
    """Tests for the import_clients endpoint."""

    @pytest.mark.asyncio
    async def test_excel_upload_returns_200(self, mock_db, studio_id) -> None:
        """Excel file upload returns 200 with correct response shape."""
        from app.api.v1.clients import import_clients

        report = ImportReport(
            total=3,
            success_count=2,
            error_count=1,
            errors=[
                ImportRowError(row_number=2, field="codice_fiscale", message="Duplicato"),
            ],
        )
        upload = _make_upload_file("clienti.xlsx", b"fake-excel")

        with (
            patch("app.api.v1.clients.client_import_service") as mock_svc,
            patch("app.api.v1.clients.profile_completeness_service"),
        ):
            mock_svc.import_from_excel = AsyncMock(return_value=report)
            result = await import_clients(
                studio_id=studio_id,
                file=upload,
                column_mapping=None,
                x_user_id=None,
                db=mock_db,
            )

        assert result.total == 3
        assert result.success_count == 2
        assert result.error_count == 1
        assert len(result.errors) == 1
        assert result.errors[0].row_number == 2
        mock_db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_csv_upload_returns_200(self, mock_db, studio_id) -> None:
        """CSV file upload returns 200."""
        from app.api.v1.clients import import_clients

        report = ImportReport(total=2, success_count=2, error_count=0)
        upload = _make_upload_file("clienti.csv", b"fake-csv")

        with (
            patch("app.api.v1.clients.client_import_service") as mock_svc,
            patch("app.api.v1.clients.profile_completeness_service"),
        ):
            mock_svc.import_from_csv = AsyncMock(return_value=report)
            result = await import_clients(
                studio_id=studio_id,
                file=upload,
                column_mapping=None,
                x_user_id=None,
                db=mock_db,
            )

        assert result.total == 2
        assert result.success_count == 2

    @pytest.mark.asyncio
    async def test_unsupported_format_returns_400(self, mock_db, studio_id) -> None:
        """Unsupported file format (.txt) raises HTTPException 400."""
        from fastapi import HTTPException

        from app.api.v1.clients import import_clients

        upload = _make_upload_file("data.txt", b"some text")

        with pytest.raises(HTTPException) as exc_info:
            await import_clients(
                studio_id=studio_id,
                file=upload,
                column_mapping=None,
                x_user_id=None,
                db=mock_db,
            )

        assert exc_info.value.status_code == 400
        assert "non supportato" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_import_with_column_mapping(self, mock_db, studio_id) -> None:
        """Import endpoint passes column mapping to service."""
        from app.api.v1.clients import import_clients

        report = ImportReport(total=1, success_count=1, error_count=0)
        upload = _make_upload_file("clienti.csv", b"fake-csv")
        mapping_json = '{"cf": "codice_fiscale", "ragione_sociale": "nome"}'

        with (
            patch("app.api.v1.clients.client_import_service") as mock_svc,
            patch("app.api.v1.clients.profile_completeness_service"),
        ):
            mock_svc.import_from_csv = AsyncMock(return_value=report)
            result = await import_clients(
                studio_id=studio_id,
                file=upload,
                column_mapping=mapping_json,
                x_user_id=None,
                db=mock_db,
            )

        assert result.total == 1
        assert result.success_count == 1
        # Verify mapping was passed
        call_kwargs = mock_svc.import_from_csv.call_args
        assert call_kwargs.kwargs["column_mapping"] == {
            "cf": "codice_fiscale",
            "ragione_sociale": "nome",
        }

    @pytest.mark.asyncio
    async def test_import_returns_warnings(self, mock_db, studio_id) -> None:
        """Import with created_client_ids returns completeness warnings."""
        from app.api.v1.clients import import_clients
        from app.services.profile_completeness_service import (
            CompletenessReport,
            MissingFieldWarning,
        )

        report = ImportReport(
            total=1,
            success_count=1,
            error_count=0,
            created_client_ids=[42],
        )
        completeness = CompletenessReport(
            clients_without_profile=1,
            clients_missing_partita_iva=0,
            missing_fields=[
                MissingFieldWarning(
                    client_id=42,
                    client_nome="Mario Rossi",
                    field="regime_fiscale",
                    priority="critico",
                    reason="Profilo aziendale mancante",
                ),
            ],
        )
        upload = _make_upload_file("clienti.xlsx", b"fake-excel")

        with (
            patch("app.api.v1.clients.client_import_service") as mock_svc,
            patch("app.api.v1.clients.profile_completeness_service") as mock_pcs,
        ):
            mock_svc.import_from_excel = AsyncMock(return_value=report)
            mock_pcs.analyze_imported_clients = AsyncMock(return_value=completeness)
            result = await import_clients(
                studio_id=studio_id,
                file=upload,
                column_mapping=None,
                x_user_id=None,
                db=mock_db,
            )

        assert result.warnings is not None
        assert result.warnings.clients_without_profile == 1
        assert len(result.warnings.missing_fields) == 1
        assert result.warnings.missing_fields[0].field == "regime_fiscale"


class TestPreviewEndpoint:
    """Tests for the preview_import endpoint."""

    @pytest.mark.asyncio
    async def test_preview_csv_returns_columns_and_rows(self, studio_id) -> None:
        """Preview parses CSV and returns detected columns, suggested mappings, and validated rows."""
        from app.api.v1.clients import preview_import
        from app.services.client_import_service import SuggestedColumnMapping

        headers = ["codice_fiscale", "nome", "comune", "provincia"]
        records = [
            {
                "codice_fiscale": "RSSMRA85M01H501Z",
                "nome": "Mario Rossi",
                "comune": "Roma",
                "provincia": "RM",
            },
        ]
        preview_rows = [
            PreviewRow(
                row_number=1,
                data=dict(records[0]),  # type: ignore[arg-type]
                is_valid=True,
                errors=[],
            ),
        ]
        suggested = {
            "codice_fiscale": SuggestedColumnMapping(
                file_column="codice_fiscale", confidence=1.0, match_method="exact_alias"
            ),
            "nome": SuggestedColumnMapping(file_column="nome", confidence=1.0, match_method="exact_alias"),
        }
        upload = _make_upload_file("clienti.csv", b"fake-csv")

        with patch("app.api.v1.clients.client_import_service") as mock_svc:
            mock_svc.parse_csv = MagicMock(return_value=(headers, records))
            mock_svc.validate_records = MagicMock(return_value=preview_rows)
            mock_svc.auto_detect_column_mapping = MagicMock(return_value=suggested)
            result = await preview_import(studio_id=studio_id, file=upload)

        assert result.detected_columns == headers
        assert result.suggested_mappings is not None
        assert "codice_fiscale" in result.suggested_mappings
        assert result.suggested_mappings["codice_fiscale"].confidence == 1.0
        assert result.suggested_mappings["codice_fiscale"].match_method == "exact_alias"
        assert result.total_rows == 1
        assert result.valid_rows == 1
        assert result.invalid_rows == 0
        assert len(result.rows) == 1
        assert result.rows[0].is_valid is True

    @pytest.mark.asyncio
    async def test_preview_unsupported_format_returns_400(self, studio_id) -> None:
        """Preview with unsupported format raises HTTPException 400."""
        from fastapi import HTTPException

        from app.api.v1.clients import preview_import

        upload = _make_upload_file("data.txt", b"some text")

        with pytest.raises(HTTPException) as exc_info:
            await preview_import(studio_id=studio_id, file=upload)

        assert exc_info.value.status_code == 400
        assert "non supportato" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_preview_with_invalid_rows(self, studio_id) -> None:
        """Preview correctly counts valid and invalid rows."""
        from app.api.v1.clients import preview_import

        headers = ["codice_fiscale", "nome", "comune", "provincia"]
        records = [
            {
                "codice_fiscale": "RSSMRA85M01H501Z",
                "nome": "Mario Rossi",
                "comune": "Roma",
                "provincia": "RM",
            },
            {
                "codice_fiscale": "INVALID",
                "nome": "",
            },
        ]
        preview_rows = [
            PreviewRow(row_number=1, data=dict(records[0]), is_valid=True, errors=[]),  # type: ignore[arg-type]
            PreviewRow(row_number=2, data=dict(records[1]), is_valid=False, errors=["Campi mancanti"]),  # type: ignore[arg-type]
        ]
        upload = _make_upload_file("clienti.xlsx", b"fake-excel")

        with patch("app.api.v1.clients.client_import_service") as mock_svc:
            mock_svc.parse_excel = MagicMock(return_value=(headers, records))
            mock_svc.validate_records = MagicMock(return_value=preview_rows)
            mock_svc.auto_detect_column_mapping = MagicMock(return_value={})
            result = await preview_import(studio_id=studio_id, file=upload)

        assert result.total_rows == 2
        assert result.valid_rows == 1
        assert result.invalid_rows == 1
