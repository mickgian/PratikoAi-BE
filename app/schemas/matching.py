"""DEV-326: Matching API schemas — Suggestion responses and trigger requests."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SuggestionResponse(BaseModel):
    """Response schema for a proactive suggestion."""

    id: UUID
    studio_id: UUID
    knowledge_item_id: int
    matched_client_ids: list = Field(default_factory=list)
    match_score: float
    suggestion_text: str
    is_read: bool
    is_dismissed: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TriggerMatchingRequest(BaseModel):
    """Request to trigger a matching job."""

    knowledge_item_id: int | None = Field(
        default=None,
        description="ID dell'elemento di conoscenza specifico (opzionale)",
    )
    trigger: str = Field(
        default="manual",
        description="Tipo di trigger (manual, scheduled, webhook)",
    )


class TriggerMatchingResponse(BaseModel):
    """Response after triggering a matching job."""

    status: str = Field(description="Stato della richiesta (accepted)")
    studio_id: UUID = Field(description="ID dello studio")
    knowledge_item_id: int | None = Field(
        default=None,
        description="ID dell'elemento di conoscenza se specificato",
    )
    trigger: str = Field(description="Tipo di trigger utilizzato")
    message: str = Field(description="Messaggio descrittivo")
