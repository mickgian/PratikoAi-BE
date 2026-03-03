"""DEV-313: Client Import Service — Excel, CSV, PDF and programmatic import.

Supports importing clients from Excel files (openpyxl), CSV files,
PDF files (pdfplumber) and structured dict lists.
Produces an import report with success/error counts.
Provides preview (parse + validate) without importing.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from uuid import UUID

from app.core.logging import logger
from app.models.client import TipoCliente
from app.services.client_service import ClientService

try:
    import openpyxl
except ImportError:  # pragma: no cover
    openpyxl = None  # type: ignore[assignment]

try:
    import pdfplumber
except ImportError:  # pragma: no cover
    pdfplumber = None  # type: ignore[assignment]

# Required columns that every import row must contain.
REQUIRED_COLUMNS = {"codice_fiscale", "nome", "comune", "provincia"}

# All columns recognised by the importer (required + optional).
ALL_COLUMNS = REQUIRED_COLUMNS | {"tipo_cliente", "partita_iva", "email", "phone", "indirizzo", "cap"}

# Mapping from user-facing tipo_cliente strings to the enum (case-insensitive).
_TIPO_CLIENTE_MAP: dict[str, TipoCliente] = {t.value.lower(): t for t in TipoCliente}


@dataclass
class ImportRowError:
    """A single row-level import error."""

    row_number: int
    field: str | None
    message: str


@dataclass
class PreviewRow:
    """A single validated preview row (no DB write)."""

    row_number: int
    data: dict[str, str | None]
    is_valid: bool
    errors: list[str]


@dataclass
class ImportReport:
    """Summary produced after a batch import."""

    total: int = 0
    success_count: int = 0
    error_count: int = 0
    errors: list[ImportRowError] = field(default_factory=list)
    created_client_ids: list[int] = field(default_factory=list)


def _resolve_tipo_cliente(raw: str | None) -> TipoCliente:
    """Map a raw string to TipoCliente, defaulting to PERSONA_FISICA."""
    if raw is None:
        return TipoCliente.PERSONA_FISICA
    normalised = str(raw).strip().lower()
    return _TIPO_CLIENTE_MAP.get(normalised, TipoCliente.PERSONA_FISICA)


class ClientImportService:
    """Service for importing clients from Excel, CSV, PDF files or dict lists."""

    def __init__(self) -> None:
        self._client_service = ClientService()

    # ------------------------------------------------------------------
    # Parsing — reusable by both preview and import
    # ------------------------------------------------------------------

    def parse_excel(self, file_content: bytes) -> tuple[list[str], list[dict]]:
        """Parse an Excel workbook and return (headers, records) without importing."""
        if openpyxl is None:  # pragma: no cover
            raise RuntimeError("openpyxl non è installato. Installa con: pip install openpyxl")

        wb = openpyxl.load_workbook(io.BytesIO(file_content), read_only=True, data_only=True)
        ws = wb.active
        rows_iter = ws.iter_rows(values_only=True)

        try:
            header_raw = next(rows_iter)
        except StopIteration:
            wb.close()
            return [], []

        headers = [str(h).strip() if h is not None else "" for h in header_raw]
        headers_lower = [h.lower() for h in headers]

        records: list[dict] = []
        for row_values in rows_iter:
            record: dict[str, str | None] = {}
            for idx, col_name in enumerate(headers_lower):
                if idx < len(row_values):
                    val = row_values[idx]
                    record[col_name] = str(val).strip() if val is not None else None
            records.append(record)

        wb.close()
        return headers, records

    def parse_csv(self, file_content: bytes) -> tuple[list[str], list[dict]]:
        """Parse a CSV file and return (headers, records) without importing."""
        try:
            text = file_content.decode("utf-8")
        except UnicodeDecodeError:
            text = file_content.decode("latin-1")

        try:
            dialect = csv.Sniffer().sniff(text[:2048], delimiters=",;")
            delimiter = dialect.delimiter
        except csv.Error:
            delimiter = ","

        reader = csv.reader(io.StringIO(text), delimiter=delimiter)

        try:
            header_raw = next(reader)
        except StopIteration:
            return [], []

        headers = [h.strip() for h in header_raw]
        headers_lower = [h.lower() for h in headers]

        records: list[dict] = []
        for row_values in reader:
            if not any(cell.strip() for cell in row_values):
                continue
            record: dict[str, str | None] = {}
            for idx, col_name in enumerate(headers_lower):
                if idx < len(row_values):
                    val = row_values[idx].strip()
                    record[col_name] = val if val else None
            records.append(record)

        return headers, records

    def parse_pdf(self, file_content: bytes) -> tuple[list[str], list[dict]]:
        """Parse a PDF table and return (headers, records) without importing."""
        if pdfplumber is None:  # pragma: no cover
            raise RuntimeError("pdfplumber non è installato. Installa con: pip install pdfplumber")

        table_data: list[list] | None = None
        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                if tables:
                    table_data = tables[0]
                    break

        if not table_data:
            raise ValueError("Nessuna tabella trovata nel file PDF.")

        header_raw = table_data[0]
        headers = [str(h).strip() if h else "" for h in header_raw]
        headers_lower = [h.lower() for h in headers]

        records: list[dict] = []
        for row_values in table_data[1:]:
            record: dict[str, str | None] = {}
            for idx, col_name in enumerate(headers_lower):
                if idx < len(row_values):
                    val = row_values[idx]
                    record[col_name] = str(val).strip() if val else None
            records.append(record)

        return headers, records

    # ------------------------------------------------------------------
    # Validation (preview without DB writes)
    # ------------------------------------------------------------------

    def validate_records(
        self,
        records: list[dict],
        column_mapping: dict[str, str] | None = None,
    ) -> list[PreviewRow]:
        """Validate records and return preview rows with per-row errors.

        If *column_mapping* is provided, keys are remapped first
        (source_column → target_field).
        """
        if column_mapping:
            records = self._apply_column_mapping(records, column_mapping)

        preview_rows: list[PreviewRow] = []
        seen_cf: set[str] = set()

        for idx, record in enumerate(records, start=1):
            errors: list[str] = []
            missing_fields = self._missing_required_fields(record)
            if missing_fields:
                errors.append(f"Campi obbligatori mancanti: {', '.join(sorted(missing_fields))}")

            cf_raw = record.get("codice_fiscale")
            cf = str(cf_raw).strip() if cf_raw else ""
            if cf and cf in seen_cf:
                errors.append("Codice fiscale duplicato nel batch")
            if cf:
                seen_cf.add(cf)

            preview_rows.append(
                PreviewRow(
                    row_number=idx,
                    data=record,
                    is_valid=len(errors) == 0,
                    errors=errors,
                )
            )

        return preview_rows

    # ------------------------------------------------------------------
    # Import (with DB writes)
    # ------------------------------------------------------------------

    async def import_from_excel(
        self,
        db: object,
        *,
        studio_id: UUID,
        file_content: bytes,
        column_mapping: dict[str, str] | None = None,
    ) -> ImportReport:
        """Parse an Excel workbook and import rows."""
        _headers, records = self.parse_excel(file_content)

        headers_lower = [h.lower() for h in _headers]
        missing = REQUIRED_COLUMNS - set(headers_lower)
        if column_mapping:
            mapped_targets = set(column_mapping.values())
            missing = REQUIRED_COLUMNS - set(headers_lower) - mapped_targets
        if missing and not column_mapping:
            sorted_missing = sorted(missing)
            raise ValueError(f"Colonne obbligatorie mancanti nel file: {', '.join(sorted_missing)}")

        return await self.import_from_records(
            db=db,
            studio_id=studio_id,
            records=records,
            column_mapping=column_mapping,
        )

    async def import_from_csv(
        self,
        db: object,
        *,
        studio_id: UUID,
        file_content: bytes,
        column_mapping: dict[str, str] | None = None,
    ) -> ImportReport:
        """Parse a CSV file and import rows."""
        _headers, records = self.parse_csv(file_content)

        headers_lower = [h.lower() for h in _headers]
        missing = REQUIRED_COLUMNS - set(headers_lower)
        if column_mapping:
            mapped_targets = set(column_mapping.values())
            missing = REQUIRED_COLUMNS - set(headers_lower) - mapped_targets
        if missing and not column_mapping:
            sorted_missing = sorted(missing)
            raise ValueError(f"Colonne obbligatorie mancanti nel file: {', '.join(sorted_missing)}")

        return await self.import_from_records(
            db=db,
            studio_id=studio_id,
            records=records,
            column_mapping=column_mapping,
        )

    async def import_from_pdf(
        self,
        db: object,
        *,
        studio_id: UUID,
        file_content: bytes,
        column_mapping: dict[str, str] | None = None,
    ) -> ImportReport:
        """Parse a PDF table and import rows."""
        _headers, records = self.parse_pdf(file_content)

        headers_lower = [h.lower() for h in _headers]
        missing = REQUIRED_COLUMNS - set(headers_lower)
        if column_mapping:
            mapped_targets = set(column_mapping.values())
            missing = REQUIRED_COLUMNS - set(headers_lower) - mapped_targets
        if missing and not column_mapping:
            sorted_missing = sorted(missing)
            raise ValueError(f"Colonne obbligatorie mancanti nel file: {', '.join(sorted_missing)}")

        return await self.import_from_records(
            db=db,
            studio_id=studio_id,
            records=records,
            column_mapping=column_mapping,
        )

    async def import_from_records(
        self,
        db: object,
        *,
        studio_id: UUID,
        records: list[dict],
        column_mapping: dict[str, str] | None = None,
    ) -> ImportReport:
        """Import clients from a list of dicts.

        Each dict should contain at minimum the keys in *REQUIRED_COLUMNS*.
        Rows with missing required fields are skipped and recorded as errors.
        Duplicate codice_fiscale values within the batch are detected and
        skipped before calling ClientService.

        If *column_mapping* is provided (source→target), record keys are
        remapped before processing.
        """
        if column_mapping:
            records = self._apply_column_mapping(records, column_mapping)

        report = ImportReport(total=len(records))
        seen_cf: set[str] = set()

        for idx, record in enumerate(records, start=1):
            missing_fields = self._missing_required_fields(record)
            if missing_fields:
                first_missing = sorted(missing_fields)[0]
                report.error_count += 1
                report.errors.append(
                    ImportRowError(
                        row_number=idx,
                        field=first_missing,
                        message=(f"Campi obbligatori mancanti alla riga {idx}: {', '.join(sorted(missing_fields))}."),
                    )
                )
                continue

            cf = record["codice_fiscale"].strip()

            if cf in seen_cf:
                report.error_count += 1
                report.errors.append(
                    ImportRowError(
                        row_number=idx,
                        field="codice_fiscale",
                        message=f"Codice fiscale duplicato nel batch alla riga {idx}: già presente in una riga precedente.",
                    )
                )
                continue

            seen_cf.add(cf)
            tipo_cliente = _resolve_tipo_cliente(record.get("tipo_cliente"))

            try:
                client = await self._client_service.create(
                    db,
                    studio_id=studio_id,
                    codice_fiscale=cf,
                    nome=record["nome"].strip(),
                    tipo_cliente=tipo_cliente,
                    comune=record["comune"].strip(),
                    provincia=record["provincia"].strip(),
                    partita_iva=self._clean_optional(record.get("partita_iva")),
                    email=self._clean_optional(record.get("email")),
                    phone=self._clean_optional(record.get("phone")),
                    indirizzo=self._clean_optional(record.get("indirizzo")),
                    cap=self._clean_optional(record.get("cap")),
                )
                report.success_count += 1
                if client and hasattr(client, "id") and client.id is not None:
                    report.created_client_ids.append(client.id)
            except ValueError as exc:
                report.error_count += 1
                report.errors.append(
                    ImportRowError(
                        row_number=idx,
                        field="codice_fiscale",
                        message=str(exc),
                    )
                )

        logger.info(
            "client_import_completed",
            studio_id=str(studio_id),
            total=report.total,
            success=report.success_count,
            errors=report.error_count,
        )
        return report

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_column_mapping(
        records: list[dict],
        column_mapping: dict[str, str],
    ) -> list[dict]:
        """Remap record keys using source→target mapping."""
        return [{column_mapping.get(k, k): v for k, v in record.items()} for record in records]

    @staticmethod
    def _missing_required_fields(record: dict) -> set[str]:
        """Return the set of required column names that are missing or blank."""
        missing: set[str] = set()
        for col in REQUIRED_COLUMNS:
            value = record.get(col)
            if value is None or str(value).strip() == "":
                missing.add(col)
        return missing

    @staticmethod
    def _clean_optional(value: str | None) -> str | None:
        """Return stripped value or None for blank/missing optionals."""
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned if cleaned else None


client_import_service = ClientImportService()
