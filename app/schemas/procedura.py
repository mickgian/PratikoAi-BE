"""DEV-342: Procedura API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ProceduraResponse(BaseModel):
    """Procedura definition response."""

    id: UUID
    code: str
    title: str
    description: str
    category: str
    steps: list
    estimated_time_minutes: int
    version: int
    is_active: bool

    model_config = {"from_attributes": True}


class ProceduraProgressCreate(BaseModel):
    """Request to start tracking progress."""

    procedura_id: UUID
    client_id: int | None = None


class ProceduraProgressResponse(BaseModel):
    """Progress tracking response."""

    id: UUID
    user_id: int
    studio_id: UUID
    procedura_id: UUID
    client_id: int | None = None
    current_step: int
    completed_steps: list
    notes: str | None = None
    started_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class ChecklistItemUpdate(BaseModel):
    """DEV-343: Update a checklist item within a step."""

    step_index: int = Field(..., ge=0, description="Indice dello step")
    item_index: int = Field(..., ge=0, description="Indice dell'elemento checklist")
    completed: bool = Field(..., description="Stato di completamento")


class ProceduraNotesUpdate(BaseModel):
    """DEV-344: Update notes for a progress record."""

    notes: str | None = Field(default=None, description="Note sulla procedura")


class DocumentChecklistUpdate(BaseModel):
    """DEV-344: Update document verification status."""

    document_name: str = Field(..., description="Nome del documento")
    verified: bool = Field(..., description="Stato di verifica del documento")
