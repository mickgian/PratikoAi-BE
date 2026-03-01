"""DEV-385: Deadline API schemas — Request/response models for deadline endpoints.

DEV-437: Added importo (Decimal) and sanzioni (SanzioniInfo) fields.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class SanzioniInfo(BaseModel):
    """Penalty information for a deadline.

    All fields are optional to allow partial penalty specifications.
    """

    percentuale: float | None = Field(
        default=None,
        ge=0.0,
        description="Percentuale della sanzione (es. 30.0 per il 30%)",
    )
    importo_fisso: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        description="Importo fisso della sanzione in EUR",
    )
    descrizione: str | None = Field(
        default=None,
        max_length=500,
        description="Descrizione testuale della sanzione",
    )


class DeadlineResponse(BaseModel):
    """Response schema for a deadline."""

    id: UUID
    title: str
    description: str | None = None
    deadline_type: str
    source: str
    due_date: date
    recurrence_rule: str | None = None
    importo: Decimal | None = None
    sanzioni: dict[str, Any] | None = None
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
    importo: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        description="Importo in EUR (deve essere >= 0)",
    )
    sanzioni: SanzioniInfo | None = Field(
        default=None,
        description="Informazioni sulle sanzioni",
    )


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
