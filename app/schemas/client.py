"""DEV-312: Client API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.client import StatoCliente, TipoCliente


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
    created_at: datetime

    model_config = {"from_attributes": True}


class ClientListResponse(BaseModel):
    """Paginated client list response."""

    items: list[ClientResponse]
    total: int
    offset: int
    limit: int
