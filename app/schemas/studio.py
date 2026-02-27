"""DEV-311: Studio API schemas."""

from uuid import UUID

from pydantic import BaseModel, Field


class StudioCreate(BaseModel):
    """Request to create a studio."""

    name: str = Field(..., max_length=200, description="Nome dello studio")
    slug: str = Field(..., max_length=100, description="Identificativo URL-safe univoco")
    max_clients: int = Field(default=100, ge=1, le=1000, description="Limite massimo clienti")
    settings: dict | None = Field(default=None, description="Impostazioni JSONB")


class StudioUpdate(BaseModel):
    """Request to update a studio."""

    name: str | None = Field(default=None, max_length=200)
    slug: str | None = Field(default=None, max_length=100)
    max_clients: int | None = Field(default=None, ge=1, le=1000)
    settings: dict | None = None


class StudioResponse(BaseModel):
    """Studio response."""

    id: UUID
    name: str
    slug: str
    max_clients: int
    settings: dict | None = None

    model_config = {"from_attributes": True}
