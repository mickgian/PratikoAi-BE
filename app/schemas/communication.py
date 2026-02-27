"""DEV-332: Communication API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.communication import CanaleInvio, StatoComunicazione


class CommunicationCreate(BaseModel):
    """Request to create a communication draft."""

    subject: str = Field(..., max_length=300, description="Oggetto della comunicazione")
    content: str = Field(..., description="Corpo della comunicazione")
    channel: CanaleInvio
    client_id: int | None = None
    normativa_riferimento: str | None = Field(default=None, max_length=200)
    matching_rule_id: UUID | None = None


class CommunicationResponse(BaseModel):
    """Communication response."""

    id: UUID
    studio_id: UUID
    client_id: int | None = None
    subject: str
    content: str
    channel: str
    status: str
    created_by: int
    approved_by: int | None = None
    approved_at: datetime | None = None
    sent_at: datetime | None = None
    normativa_riferimento: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CommunicationApprove(BaseModel):
    """Request body is empty — approved_by comes from auth."""

    pass


class BulkCommunicationCreate(BaseModel):
    """DEV-335: Bulk communication creation request."""

    client_ids: list[int] = Field(..., min_length=1, description="ID dei clienti destinatari")
    subject: str = Field(..., max_length=300)
    content: str
    channel: CanaleInvio
    normativa_riferimento: str | None = None
    matching_rule_id: UUID | None = None
