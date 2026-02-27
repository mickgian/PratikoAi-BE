"""DEV-313: Tests for ClientImportService — Excel and programmatic client import.

Tests cover:
- Happy path: import from Excel with valid data
- Error: empty file (no data rows)
- Error: missing required columns
- Happy path: import from dict list (programmatic API)
- Edge case: duplicate codice_fiscale in batch (skip duplicates)
- Edge case: invalid tipo_cliente value defaults gracefully
- Import report (success count, error count, error details)
- Edge case: row missing required fields is skipped with error
- Error: ClientService ValueError (duplicate CF in DB) recorded in report
"""

import io
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import openpyxl
import pytest

from app.models.client import Client, StatoCliente, TipoCliente
from app.services.client_import_service import (
    ClientImportService,
    ImportReport,
)
from app.services.client_import_service import (
    ImportError as ImportRowError,
)


@pytest.fixture
def import_service() -> ClientImportService:
    return ClientImportService()


@pytest.fixture
def mock_db() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    return session


@pytest.fixture
def studio_id():
    return uuid4()


def _make_excel_bytes(rows: list[list], sheet_name: str = "Clienti") -> bytes:
    """Helper: create an Excel file in memory from header + data rows."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet_name
    for row in rows:
        ws.append(row)
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


@pytest.fixture
def valid_excel_bytes() -> bytes:
    """Excel file with two valid client rows."""
    header = [
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
    ]
    row1 = [
        "RSSMRA85M01H501Z",
        "Mario Rossi",
        "persona_fisica",
        "Roma",
        "RM",
        "12345678901",
        "mario@example.com",
        "+39 333 1234567",
        "Via Roma 1",
        "00100",
    ]
    row2 = [
        "BNCLGU90A01F205X",
        "Luigi Bianchi",
        "societa",
        "Milano",
        "MI",
        None,
        "luigi@example.com",
        None,
        None,
        None,
    ]
    return _make_excel_bytes([header, row1, row2])


@pytest.fixture
def empty_excel_bytes() -> bytes:
    """Excel file with header only, no data rows."""
    header = ["codice_fiscale", "nome", "tipo_cliente", "comune", "provincia"]
    return _make_excel_bytes([header])


@pytest.fixture
def missing_columns_excel_bytes() -> bytes:
    """Excel file missing required columns."""
    header = ["codice_fiscale", "nome"]  # Missing comune, provincia
    row1 = ["RSSMRA85M01H501Z", "Mario Rossi"]
    return _make_excel_bytes([header, row1])


def _mock_client_service_create(studio_id):
    """Return an AsyncMock that simulates ClientService.create()."""
    created_clients = {}

    async def _create(db, *, studio_id, codice_fiscale, nome, tipo_cliente, comune, provincia, **kwargs):
        if codice_fiscale in created_clients:
            raise ValueError("Il codice fiscale e' gia' presente nello studio.")
        client = Client(
            id=len(created_clients) + 1,
            studio_id=studio_id,
            codice_fiscale=codice_fiscale,
            nome=nome,
            tipo_cliente=tipo_cliente,
            comune=comune,
            provincia=provincia,
            **{k: v for k, v in kwargs.items() if v is not None},
        )
        created_clients[codice_fiscale] = client
        return client

    return _create


class TestClientImportFromExcel:
    """Test ClientImportService.import_from_excel()."""

    @pytest.mark.asyncio
    async def test_import_excel_happy_path(
        self,
        import_service: ClientImportService,
        mock_db: AsyncMock,
        studio_id,
        valid_excel_bytes: bytes,
    ) -> None:
        """Happy path: import from Excel with valid data creates clients."""
        with patch.object(
            import_service._client_service,
            "create",
            side_effect=_mock_client_service_create(studio_id),
        ):
            report = await import_service.import_from_excel(
                db=mock_db,
                studio_id=studio_id,
                file_content=valid_excel_bytes,
            )

        assert isinstance(report, ImportReport)
        assert report.total == 2
        assert report.success_count == 2
        assert report.error_count == 0
        assert len(report.errors) == 0

    @pytest.mark.asyncio
    async def test_import_excel_empty_file(
        self,
        import_service: ClientImportService,
        mock_db: AsyncMock,
        studio_id,
        empty_excel_bytes: bytes,
    ) -> None:
        """Error: empty file (no data rows) returns report with zero total."""
        report = await import_service.import_from_excel(
            db=mock_db,
            studio_id=studio_id,
            file_content=empty_excel_bytes,
        )

        assert report.total == 0
        assert report.success_count == 0
        assert report.error_count == 0

    @pytest.mark.asyncio
    async def test_import_excel_missing_required_columns(
        self,
        import_service: ClientImportService,
        mock_db: AsyncMock,
        studio_id,
        missing_columns_excel_bytes: bytes,
    ) -> None:
        """Error: missing required columns raises ValueError."""
        with pytest.raises(ValueError, match="[Cc]olonne.*mancanti|[Mm]ancano.*colonne"):
            await import_service.import_from_excel(
                db=mock_db,
                studio_id=studio_id,
                file_content=missing_columns_excel_bytes,
            )


class TestClientImportFromRecords:
    """Test ClientImportService.import_from_records()."""

    @pytest.mark.asyncio
    async def test_import_records_happy_path(
        self,
        import_service: ClientImportService,
        mock_db: AsyncMock,
        studio_id,
    ) -> None:
        """Happy path: import from dict list creates all clients."""
        records = [
            {
                "codice_fiscale": "RSSMRA85M01H501Z",
                "nome": "Mario Rossi",
                "tipo_cliente": "persona_fisica",
                "comune": "Roma",
                "provincia": "RM",
                "email": "mario@example.com",
            },
            {
                "codice_fiscale": "BNCLGU90A01F205X",
                "nome": "Luigi Bianchi",
                "tipo_cliente": "societa",
                "comune": "Milano",
                "provincia": "MI",
            },
        ]

        with patch.object(
            import_service._client_service,
            "create",
            side_effect=_mock_client_service_create(studio_id),
        ):
            report = await import_service.import_from_records(
                db=mock_db,
                studio_id=studio_id,
                records=records,
            )

        assert report.total == 2
        assert report.success_count == 2
        assert report.error_count == 0

    @pytest.mark.asyncio
    async def test_import_records_duplicate_cf_in_batch(
        self,
        import_service: ClientImportService,
        mock_db: AsyncMock,
        studio_id,
    ) -> None:
        """Edge case: duplicate codice_fiscale in batch skips the duplicate."""
        records = [
            {
                "codice_fiscale": "RSSMRA85M01H501Z",
                "nome": "Mario Rossi",
                "tipo_cliente": "persona_fisica",
                "comune": "Roma",
                "provincia": "RM",
            },
            {
                "codice_fiscale": "RSSMRA85M01H501Z",
                "nome": "Mario Rossi Duplicato",
                "tipo_cliente": "persona_fisica",
                "comune": "Roma",
                "provincia": "RM",
            },
        ]

        with patch.object(
            import_service._client_service,
            "create",
            side_effect=_mock_client_service_create(studio_id),
        ):
            report = await import_service.import_from_records(
                db=mock_db,
                studio_id=studio_id,
                records=records,
            )

        assert report.total == 2
        assert report.success_count == 1
        assert report.error_count == 1
        assert any("duplicato" in e.message.lower() or "già presente" in e.message.lower() for e in report.errors)

    @pytest.mark.asyncio
    async def test_import_records_invalid_tipo_defaults(
        self,
        import_service: ClientImportService,
        mock_db: AsyncMock,
        studio_id,
    ) -> None:
        """Edge case: invalid tipo_cliente value defaults to PERSONA_FISICA."""
        records = [
            {
                "codice_fiscale": "RSSMRA85M01H501Z",
                "nome": "Mario Rossi",
                "tipo_cliente": "INVALID_TYPE",
                "comune": "Roma",
                "provincia": "RM",
            },
        ]

        created_tipo = None

        async def capture_create(db, *, studio_id, tipo_cliente, **kwargs):
            nonlocal created_tipo
            created_tipo = tipo_cliente
            return Client(
                id=1,
                studio_id=studio_id,
                tipo_cliente=tipo_cliente,
                **kwargs,
            )

        with patch.object(
            import_service._client_service,
            "create",
            side_effect=capture_create,
        ):
            report = await import_service.import_from_records(
                db=mock_db,
                studio_id=studio_id,
                records=records,
            )

        assert report.success_count == 1
        assert created_tipo == TipoCliente.PERSONA_FISICA

    @pytest.mark.asyncio
    async def test_import_records_missing_required_fields_skips_row(
        self,
        import_service: ClientImportService,
        mock_db: AsyncMock,
        studio_id,
    ) -> None:
        """Edge case: row missing required fields is skipped with error."""
        records = [
            {
                "codice_fiscale": "RSSMRA85M01H501Z",
                "nome": "Mario Rossi",
                # Missing comune and provincia
            },
            {
                "codice_fiscale": "BNCLGU90A01F205X",
                "nome": "Luigi Bianchi",
                "tipo_cliente": "persona_fisica",
                "comune": "Milano",
                "provincia": "MI",
            },
        ]

        with patch.object(
            import_service._client_service,
            "create",
            side_effect=_mock_client_service_create(studio_id),
        ):
            report = await import_service.import_from_records(
                db=mock_db,
                studio_id=studio_id,
                records=records,
            )

        assert report.total == 2
        assert report.success_count == 1
        assert report.error_count == 1
        assert report.errors[0].row_number == 1

    @pytest.mark.asyncio
    async def test_import_records_client_service_error_recorded(
        self,
        import_service: ClientImportService,
        mock_db: AsyncMock,
        studio_id,
    ) -> None:
        """Error: ClientService ValueError (e.g. limit exceeded) is recorded in report."""
        records = [
            {
                "codice_fiscale": "RSSMRA85M01H501Z",
                "nome": "Mario Rossi",
                "tipo_cliente": "persona_fisica",
                "comune": "Roma",
                "provincia": "RM",
            },
        ]

        with patch.object(
            import_service._client_service,
            "create",
            side_effect=ValueError("Lo studio ha raggiunto il limite di 100 clienti."),
        ):
            report = await import_service.import_from_records(
                db=mock_db,
                studio_id=studio_id,
                records=records,
            )

        assert report.total == 1
        assert report.success_count == 0
        assert report.error_count == 1
        assert "limite" in report.errors[0].message.lower() or "100" in report.errors[0].message

    @pytest.mark.asyncio
    async def test_import_report_structure(
        self,
        import_service: ClientImportService,
        mock_db: AsyncMock,
        studio_id,
    ) -> None:
        """Import report contains correct structure with error details."""
        records = [
            {
                "codice_fiscale": "RSSMRA85M01H501Z",
                "nome": "Mario Rossi",
                "tipo_cliente": "persona_fisica",
                "comune": "Roma",
                "provincia": "RM",
            },
            {
                # Missing nome (required)
                "codice_fiscale": "VRDLGU80A01H501X",
                "comune": "Roma",
                "provincia": "RM",
            },
        ]

        with patch.object(
            import_service._client_service,
            "create",
            side_effect=_mock_client_service_create(studio_id),
        ):
            report = await import_service.import_from_records(
                db=mock_db,
                studio_id=studio_id,
                records=records,
            )

        assert report.total == 2
        assert report.success_count == 1
        assert report.error_count == 1
        # Error should have row_number, field, message
        err = report.errors[0]
        assert isinstance(err, ImportRowError)
        assert err.row_number == 2
        assert err.field is not None
        assert len(err.message) > 0

    @pytest.mark.asyncio
    async def test_import_records_tipo_cliente_case_insensitive(
        self,
        import_service: ClientImportService,
        mock_db: AsyncMock,
        studio_id,
    ) -> None:
        """tipo_cliente mapping is case-insensitive."""
        records = [
            {
                "codice_fiscale": "RSSMRA85M01H501Z",
                "nome": "Mario Rossi",
                "tipo_cliente": "SOCIETA",
                "comune": "Roma",
                "provincia": "RM",
            },
        ]

        created_tipo = None

        async def capture_create(db, *, studio_id, tipo_cliente, **kwargs):
            nonlocal created_tipo
            created_tipo = tipo_cliente
            return Client(
                id=1,
                studio_id=studio_id,
                tipo_cliente=tipo_cliente,
                **kwargs,
            )

        with patch.object(
            import_service._client_service,
            "create",
            side_effect=capture_create,
        ):
            report = await import_service.import_from_records(
                db=mock_db,
                studio_id=studio_id,
                records=records,
            )

        assert report.success_count == 1
        assert created_tipo == TipoCliente.SOCIETA
