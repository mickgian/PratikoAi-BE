"""DEV-313: Client Import Service — Excel, CSV, PDF and programmatic import.

Supports importing clients from Excel files (openpyxl), CSV files,
PDF files (pdfplumber) and structured dict lists.
Produces an import report with success/error counts.
Provides preview (parse + validate) without importing.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
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

# ---------------------------------------------------------------------------
# Auto-detection: Tier 1 — known aliases per target field
# ---------------------------------------------------------------------------
_COLUMN_ALIASES: dict[str, list[str]] = {
    "nome": [
        "nome",
        "denominazione",
        "ragione_sociale",
        "ragione sociale",
        "rag_sociale",
        "rag sociale",
        "denominazione/ragione sociale",
        "nome_completo",
        "nome completo",
        "nome cliente",
    ],
    "codice_fiscale": [
        "codice_fiscale",
        "codice fiscale",
        "cf",
        "cod_fiscale",
        "cod fiscale",
        "cod. fiscale",
        "c.f.",
        "c.f",
    ],
    "partita_iva": [
        "partita_iva",
        "partita iva",
        "p_iva",
        "p.iva",
        "piva",
        "p. iva",
        "p iva",
        "partitaiva",
    ],
    "tipo_cliente": [
        "tipo_cliente",
        "tipo cliente",
        "tipo_soggetto",
        "tipo soggetto",
        "tipologia",
        "tipo",
    ],
    "comune": ["comune", "citta", "città", "city"],
    "provincia": ["provincia", "prov", "prov."],
    "email": ["email", "e-mail", "mail", "pec", "indirizzo_email", "indirizzo email"],
    "phone": [
        "phone",
        "telefono",
        "tel",
        "tel.",
        "cellulare",
        "cell",
        "cell.",
        "numero_telefono",
        "numero telefono",
    ],
    "indirizzo": ["indirizzo", "via", "address", "sede", "indirizzo_sede"],
    "cap": ["cap", "codice_postale", "codice postale", "zip", "zipcode"],
}

# Flattened reverse lookup: normalised alias → target field.
_ALIAS_LOOKUP: dict[str, str] = {}
for _field, _aliases in _COLUMN_ALIASES.items():
    for _alias in _aliases:
        _ALIAS_LOOKUP[_alias.lower().strip()] = _field

# All alias strings for fuzzy matching (grouped by target field).
_FUZZY_CANDIDATES: dict[str, list[str]] = {
    _field: [a.lower().strip() for a in _aliases] for _field, _aliases in _COLUMN_ALIASES.items()
}

# ---------------------------------------------------------------------------
# Auto-detection: Tier 3 — data-pattern regexes
# ---------------------------------------------------------------------------
_CF_PERSONA_RE = re.compile(r"^[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]$", re.IGNORECASE)
_PIVA_RE = re.compile(r"^\d{11}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_CAP_RE = re.compile(r"^\d{5}$")
_PROVINCIA_RE = re.compile(r"^[A-Z]{2}$")
_PHONE_RE = re.compile(r"^(\+39[\s]?)?\d[\d\s]{6,14}$")

# Minimum fraction of non-null sample values that must match a pattern.
_PATTERN_THRESHOLD = 0.5


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
class SuggestedColumnMapping:
    """Auto-detected mapping of a file column to a target field."""

    file_column: str
    confidence: float  # 0.0–1.0
    match_method: str  # "exact_alias" | "fuzzy" | "data_pattern"


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
    # Auto-detection of column mappings
    # ------------------------------------------------------------------

    def auto_detect_column_mapping(
        self,
        headers: list[str],
        sample_rows: list[dict],
    ) -> dict[str, SuggestedColumnMapping]:
        """Auto-detect column mapping using a 3-tier strategy.

        Returns a dict of target_field → SuggestedColumnMapping.
        Each file column is assigned to at most one target field.
        """
        if not headers:
            return {}

        result: dict[str, SuggestedColumnMapping] = {}
        used_columns: set[str] = set()  # track assigned file columns
        headers_lower = [h.lower().strip() for h in headers]

        # --- Tier 1: exact alias matching ---
        for h_lower, h_orig in zip(headers_lower, headers, strict=True):
            target = _ALIAS_LOOKUP.get(h_lower)
            if target and target not in result and h_lower not in used_columns:
                result[target] = SuggestedColumnMapping(
                    file_column=h_orig,
                    confidence=1.0,
                    match_method="exact_alias",
                )
                used_columns.add(h_lower)

        # --- Tier 2: fuzzy matching for remaining headers ---
        unmatched_headers = [
            (h_lower, h_orig)
            for h_lower, h_orig in zip(headers_lower, headers, strict=True)
            if h_lower not in used_columns
        ]
        unmatched_fields = [f for f in ALL_COLUMNS if f not in result]

        for h_lower, h_orig in unmatched_headers:
            best_field: str | None = None
            best_score = 0.0
            for target_field in unmatched_fields:
                if target_field in result:
                    continue
                for alias in _FUZZY_CANDIDATES.get(target_field, []):
                    score = SequenceMatcher(None, h_lower, alias).ratio()
                    if score > best_score:
                        best_score = score
                        best_field = target_field
            if best_field and best_score >= 0.6 and best_field not in result:
                result[best_field] = SuggestedColumnMapping(
                    file_column=h_orig,
                    confidence=round(best_score, 2),
                    match_method="fuzzy",
                )
                used_columns.add(h_lower)

        # --- Tier 3: data-pattern analysis for remaining fields ---
        # Order matters: check more specific patterns first (P.IVA before phone).
        _PATTERN_FIELD_ORDER = [
            "codice_fiscale",
            "partita_iva",
            "email",
            "cap",
            "provincia",
            "phone",
        ]
        if sample_rows:
            remaining_fields = [f for f in _PATTERN_FIELD_ORDER if f not in result]
            remaining_headers = [
                (h_lower, h_orig)
                for h_lower, h_orig in zip(headers_lower, headers, strict=True)
                if h_lower not in used_columns
            ]
            for target_field in remaining_fields:
                best_col: tuple[str, str] | None = None
                best_match_rate = 0.0
                for h_lower, h_orig in remaining_headers:
                    if h_lower in used_columns:
                        continue
                    match_rate = self._check_data_pattern(
                        target_field,
                        h_lower,
                        sample_rows,
                    )
                    if match_rate > best_match_rate:
                        best_match_rate = match_rate
                        best_col = (h_lower, h_orig)

                if best_col and best_match_rate >= _PATTERN_THRESHOLD:
                    result[target_field] = SuggestedColumnMapping(
                        file_column=best_col[1],
                        confidence=round(min(best_match_rate * 0.9, 0.85), 2),
                        match_method="data_pattern",
                    )
                    used_columns.add(best_col[0])

        return result

    @staticmethod
    def _check_data_pattern(
        target_field: str,
        header_lower: str,
        sample_rows: list[dict],
    ) -> float:
        """Check what fraction of sample values match the expected pattern for target_field."""
        values = [
            str(row.get(header_lower, "")).strip()
            for row in sample_rows
            if row.get(header_lower) and str(row[header_lower]).strip()
        ]
        if not values:
            return 0.0

        pattern_map: dict[str, list[re.Pattern]] = {  # type: ignore[type-arg]
            # Only match the 16-char persona fisica CF by data pattern.
            # 11-digit società CF is identical to P.IVA; use alias matching for that.
            "codice_fiscale": [_CF_PERSONA_RE],
            "partita_iva": [_PIVA_RE],
            "email": [_EMAIL_RE],
            "cap": [_CAP_RE],
            "provincia": [_PROVINCIA_RE],
            "phone": [_PHONE_RE],
        }
        patterns = pattern_map.get(target_field)
        if not patterns:
            return 0.0

        matches = sum(1 for v in values if any(p.match(v) for p in patterns))
        return matches / len(values)

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
