"""DEV-424: Notification API Endpoints — CRUD for in-app notifications.

Thin route handlers delegating to NotificationService.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.services.notification_service import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class NotificationResponse(BaseModel):
    """Response schema for a notification."""

    id: UUID
    user_id: int
    studio_id: UUID
    notification_type: str
    priority: str
    title: str
    description: str | None = None
    reference_id: UUID | None = None
    reference_type: str | None = None
    is_read: bool
    read_at: str | None = None
    dismissed: bool

    model_config = {"from_attributes": True}


class UnreadCountResponse(BaseModel):
    """Response for unread notification count."""

    count: int


class MarkAllReadResponse(BaseModel):
    """Response for bulk mark-as-read."""

    updated: int


# ---------------------------------------------------------------------------
# GET /notifications — List notifications (paginated)
# ---------------------------------------------------------------------------


@router.get("", response_model=list[NotificationResponse])
async def list_notifications(
    x_user_id: int = Header(..., description="ID utente"),
    x_studio_id: UUID = Header(..., description="ID studio"),
    unread_only: bool = Query(default=False, description="Solo non lette"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[NotificationResponse]:
    """Elenco notifiche per l'utente corrente."""
    notifs = await notification_service.list_notifications(
        db,
        user_id=x_user_id,
        studio_id=x_studio_id,
        unread_only=unread_only,
        offset=offset,
        limit=limit,
    )
    return [NotificationResponse.model_validate(n) for n in notifs]


# ---------------------------------------------------------------------------
# GET /notifications/unread-count
# ---------------------------------------------------------------------------


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    x_user_id: int = Header(..., description="ID utente"),
    x_studio_id: UUID = Header(..., description="ID studio"),
    db: AsyncSession = Depends(get_db),
) -> UnreadCountResponse:
    """Conteggio notifiche non lette."""
    count = await notification_service.get_unread_count(
        db,
        user_id=x_user_id,
        studio_id=x_studio_id,
    )
    return UnreadCountResponse(count=count)


# ---------------------------------------------------------------------------
# PUT /notifications/{id}/read — Mark single as read
# ---------------------------------------------------------------------------


@router.put("/{notification_id}/read", response_model=NotificationResponse)
async def mark_as_read(
    notification_id: UUID,
    x_user_id: int = Header(..., description="ID utente"),
    x_studio_id: UUID = Header(..., description="ID studio"),
    db: AsyncSession = Depends(get_db),
) -> NotificationResponse:
    """Segna una notifica come letta."""
    notif = await notification_service.mark_as_read(
        db,
        notification_id=notification_id,
        user_id=x_user_id,
        studio_id=x_studio_id,
    )
    if notif is None:
        raise HTTPException(status_code=404, detail="Notifica non trovata.")
    await db.commit()
    return NotificationResponse.model_validate(notif)


# ---------------------------------------------------------------------------
# PUT /notifications/mark-all-read — Bulk mark as read
# ---------------------------------------------------------------------------


@router.put("/mark-all-read", response_model=MarkAllReadResponse)
async def mark_all_as_read(
    x_user_id: int = Header(..., description="ID utente"),
    x_studio_id: UUID = Header(..., description="ID studio"),
    db: AsyncSession = Depends(get_db),
) -> MarkAllReadResponse:
    """Segna tutte le notifiche come lette."""
    count = await notification_service.mark_all_as_read(
        db,
        user_id=x_user_id,
        studio_id=x_studio_id,
    )
    await db.commit()
    return MarkAllReadResponse(updated=count)


# ---------------------------------------------------------------------------
# DELETE /notifications/{id} — Dismiss notification
# ---------------------------------------------------------------------------


@router.delete("/{notification_id}", status_code=204)
async def dismiss_notification(
    notification_id: UUID,
    x_user_id: int = Header(..., description="ID utente"),
    x_studio_id: UUID = Header(..., description="ID studio"),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Elimina (nascondi) una notifica."""
    notif = await notification_service.dismiss_notification(
        db,
        notification_id=notification_id,
        user_id=x_user_id,
        studio_id=x_studio_id,
    )
    if notif is None:
        raise HTTPException(status_code=404, detail="Notifica non trovata.")
    await db.commit()
