"""DEV-312: Client API schemas."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.client import StatoCliente, TipoCliente
from app.models.client_profile import PosizionePrevidenziale


class ClientCreate(BaseModel):
    """Request to create a client."""

    codice_fiscale: str = Field(..., max_length=50, description="Codice Fiscale")
    nome: str = Field(..., max_length=200, description="Nome completo")
    tipo_cliente: TipoCliente
    comune: str = Field(..., max_length=100)
    provincia: str = Field(..., max_length=2)
    partita_iva: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    indirizzo: str | None = Field(default=None, max_length=300)
    cap: str | None = Field(default=None, max_length=5)
    stato_cliente: StatoCliente = StatoCliente.ATTIVO
    note_studio: str | None = None


class ClientUpdate(BaseModel):
    """Request to update a client."""

    nome: str | None = Field(default=None, max_length=200)
    tipo_cliente: TipoCliente | None = None
    comune: str | None = Field(default=None, max_length=100)
    provincia: str | None = Field(default=None, max_length=2)
    partita_iva: str | None = None
    email: str | None = None
    phone: str | None = None
    indirizzo: str | None = None
    cap: str | None = None
    stato_cliente: StatoCliente | None = None
    note_studio: str | None = None
    # INPS/INAIL fields (DEV-428)
    inps_matricola: str | None = Field(default=None, max_length=20)
    inps_status: PosizionePrevidenziale | None = None
    inps_ultimo_pagamento: date | None = None
    inail_pat: str | None = Field(default=None, max_length=20)
    inail_status: PosizionePrevidenziale | None = None


class ClientResponse(BaseModel):
    """Client response."""

    id: int
    studio_id: UUID
    codice_fiscale: str
    nome: str
    tipo_cliente: str
    stato_cliente: str
    comune: str
    provincia: str
    partita_iva: str | None = None
    email: str | None = None
    phone: str | None = None
    indirizzo: str | None = None
    cap: str | None = None
    note_studio: str | None = None
    # INPS/INAIL fields (DEV-428)
    inps_matricola: str | None = None
    inps_status: PosizionePrevidenziale | None = None
    inps_ultimo_pagamento: date | None = None
    inail_pat: str | None = None
    inail_status: PosizionePrevidenziale | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ClientListResponse(BaseModel):
    """Paginated client list response."""

    items: list[ClientResponse]
    total: int
    offset: int
    limit: int


class ClientImportErrorResponse(BaseModel):
    """Single row-level import error."""

    row_number: int
    field: str | None = None
    message: str


class ImportPreviewRow(BaseModel):
    """A single validated preview row."""

    row_number: int
    data: dict[str, str | None]
    is_valid: bool
    errors: list[str]


class SuggestedColumnMappingSchema(BaseModel):
    """Auto-detected mapping suggestion for a single target field."""

    file_column: str
    confidence: float = Field(ge=0.0, le=1.0)
    match_method: str  # "exact_alias" | "fuzzy" | "data_pattern"


class ImportPreviewResponse(BaseModel):
    """Server-side preview of an uploaded import file."""

    detected_columns: list[str]
    suggested_mappings: dict[str, SuggestedColumnMappingSchema] = Field(default_factory=dict)
    total_rows: int
    valid_rows: int
    invalid_rows: int
    rows: list[ImportPreviewRow]


class ClientMissingFieldWarning(BaseModel):
    """Warning about a missing field on an imported client."""

    client_id: int
    client_nome: str
    field: str
    priority: str  # "critico" | "importante"
    reason: str


class ClientImportWarningsSummary(BaseModel):
    """Summary of post-import data completeness warnings."""

    clients_without_profile: int
    clients_missing_partita_iva: int
    missing_fields: list[ClientMissingFieldWarning]


class ClientImportResponse(BaseModel):
    """Summary of a batch client import."""

    total: int
    success_count: int
    error_count: int
    profiles_created: int = 0
    errors: list[ClientImportErrorResponse] = Field(default_factory=list)
    warnings: ClientImportWarningsSummary | None = None
