"""DEV-313: Client Import Service — Excel and programmatic import.

Supports importing clients from Excel files (openpyxl) and structured
dict lists. Produces an import report with success/error counts.
"""

from __future__ import annotations

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

# Required columns that every import row must contain.
REQUIRED_COLUMNS = {"codice_fiscale", "nome", "comune", "provincia"}

# All columns recognised by the importer (required + optional).
ALL_COLUMNS = REQUIRED_COLUMNS | {"tipo_cliente", "partita_iva", "email", "phone", "indirizzo", "cap"}

# Mapping from user-facing tipo_cliente strings to the enum (case-insensitive).
_TIPO_CLIENTE_MAP: dict[str, TipoCliente] = {t.value.lower(): t for t in TipoCliente}


@dataclass
class ImportError:
    """A single row-level import error."""

    row_number: int
    field: str | None
    message: str


@dataclass
class ImportReport:
    """Summary produced after a batch import."""

    total: int = 0
    success_count: int = 0
    error_count: int = 0
    errors: list[ImportError] = field(default_factory=list)


def _resolve_tipo_cliente(raw: str | None) -> TipoCliente:
    """Map a raw string to TipoCliente, defaulting to PERSONA_FISICA."""
    if raw is None:
        return TipoCliente.PERSONA_FISICA
    normalised = str(raw).strip().lower()
    return _TIPO_CLIENTE_MAP.get(normalised, TipoCliente.PERSONA_FISICA)


class ClientImportService:
    """Service for importing clients from Excel files or dict lists."""

    def __init__(self) -> None:
        self._client_service = ClientService()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def import_from_excel(
        self,
        db: object,
        *,
        studio_id: UUID,
        file_content: bytes,
    ) -> ImportReport:
        """Parse an Excel workbook from *file_content* bytes and import rows.

        Raises:
            ValueError: If required columns are missing from the header row.
        """
        if openpyxl is None:  # pragma: no cover
            raise ImportError("openpyxl non è installato. Installa con: pip install openpyxl")

        wb = openpyxl.load_workbook(io.BytesIO(file_content), read_only=True, data_only=True)
        ws = wb.active

        rows_iter = ws.iter_rows(values_only=True)

        # First row is the header.
        try:
            header_raw = next(rows_iter)
        except StopIteration:
            return ImportReport()

        headers = [str(h).strip().lower() if h is not None else "" for h in header_raw]

        # Validate that all required columns are present.
        missing = REQUIRED_COLUMNS - set(headers)
        if missing:
            sorted_missing = sorted(missing)
            raise ValueError(f"Colonne obbligatorie mancanti nel file: {', '.join(sorted_missing)}")

        # Build records from remaining rows.
        records: list[dict] = []
        for row_values in rows_iter:
            record: dict[str, str | None] = {}
            for idx, col_name in enumerate(headers):
                if col_name in ALL_COLUMNS and idx < len(row_values):
                    val = row_values[idx]
                    record[col_name] = str(val).strip() if val is not None else None
            records.append(record)

        wb.close()

        return await self.import_from_records(db=db, studio_id=studio_id, records=records)

    async def import_from_records(
        self,
        db: object,
        *,
        studio_id: UUID,
        records: list[dict],
    ) -> ImportReport:
        """Import clients from a list of dicts.

        Each dict should contain at minimum the keys in *REQUIRED_COLUMNS*.
        Rows with missing required fields are skipped and recorded as errors.
        Duplicate codice_fiscale values within the batch are detected and
        skipped before calling ClientService.
        """
        report = ImportReport(total=len(records))
        seen_cf: set[str] = set()

        for idx, record in enumerate(records, start=1):
            # Validate required fields — one error per invalid row.
            missing_fields = self._missing_required_fields(record)
            if missing_fields:
                first_missing = sorted(missing_fields)[0]
                report.error_count += 1
                report.errors.append(
                    ImportError(
                        row_number=idx,
                        field=first_missing,
                        message=(f"Campi obbligatori mancanti alla riga {idx}: {', '.join(sorted(missing_fields))}."),
                    )
                )
                continue

            cf = record["codice_fiscale"].strip()

            # Detect batch-level duplicates before hitting the DB.
            if cf in seen_cf:
                report.error_count += 1
                report.errors.append(
                    ImportError(
                        row_number=idx,
                        field="codice_fiscale",
                        message=f"Codice fiscale duplicato nel batch alla riga {idx}: già presente in una riga precedente.",
                    )
                )
                continue

            seen_cf.add(cf)
            tipo_cliente = _resolve_tipo_cliente(record.get("tipo_cliente"))

            try:
                await self._client_service.create(
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
            except ValueError as exc:
                report.error_count += 1
                report.errors.append(
                    ImportError(
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
