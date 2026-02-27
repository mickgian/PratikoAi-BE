"""DEV-385: Deadline API schemas — Request/response models for deadline endpoints."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class DeadlineResponse(BaseModel):
    """Response schema for a deadline."""

    id: UUID
    title: str
    description: str | None = None
    deadline_type: str
    source: str
    due_date: date
    recurrence_rule: str | None = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class DeadlineCreateRequest(BaseModel):
    """Request schema for creating a deadline."""

    title: str
    description: str | None = None
    deadline_type: str
    source: str
    due_date: date
    recurrence_rule: str | None = None


class ClientDeadlineResponse(BaseModel):
    """Response schema for a client-deadline association."""

    id: UUID
    client_id: int
    deadline_id: UUID
    studio_id: UUID
    is_completed: bool
    completed_at: datetime | None = None
    notes: str | None = None

    model_config = {"from_attributes": True}
