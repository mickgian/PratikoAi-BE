"""DEV-438: Deadline Reminder API — Per-deadline custom user reminders."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.services.deadline_reminder_service import deadline_reminder_service

router = APIRouter(prefix="/deadlines", tags=["deadline-reminders"])


class ReminderRequest(BaseModel):
    remind_at: datetime


class ReminderResponse(BaseModel):
    id: UUID
    deadline_id: UUID
    user_id: int
    studio_id: UUID
    remind_at: datetime
    is_active: bool
    notification_sent: bool

    model_config = {"from_attributes": True}


@router.post("/{deadline_id}/reminder", response_model=ReminderResponse, status_code=201)
async def set_reminder(
    deadline_id: UUID,
    body: ReminderRequest,
    x_user_id: int = Header(..., description="ID utente"),
    x_studio_id: UUID = Header(..., description="ID studio"),
    db: AsyncSession = Depends(get_db),
) -> ReminderResponse:
    """Imposta un promemoria per una scadenza."""
    try:
        reminder = await deadline_reminder_service.set_reminder(
            db,
            deadline_id=deadline_id,
            user_id=x_user_id,
            studio_id=x_studio_id,
            remind_at=body.remind_at,
        )
        await db.commit()
        return ReminderResponse.model_validate(reminder)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/{deadline_id}/reminder", status_code=204)
async def delete_reminder(
    deadline_id: UUID,
    x_user_id: int = Header(..., description="ID utente"),
    x_studio_id: UUID = Header(..., description="ID studio"),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Rimuovi un promemoria per una scadenza."""
    deleted = await deadline_reminder_service.delete_reminder(
        db,
        deadline_id=deadline_id,
        user_id=x_user_id,
        studio_id=x_studio_id,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Promemoria non trovato.")
    await db.commit()


@router.get("/{deadline_id}/reminder", response_model=ReminderResponse)
async def get_reminder(
    deadline_id: UUID,
    x_user_id: int = Header(..., description="ID utente"),
    x_studio_id: UUID = Header(..., description="ID studio"),
    db: AsyncSession = Depends(get_db),
) -> ReminderResponse:
    """Recupera promemoria per una scadenza."""
    reminder = await deadline_reminder_service.get_reminder(
        db,
        deadline_id=deadline_id,
        user_id=x_user_id,
        studio_id=x_studio_id,
    )
    if reminder is None:
        raise HTTPException(status_code=404, detail="Promemoria non trovato.")
    return ReminderResponse.model_validate(reminder)
