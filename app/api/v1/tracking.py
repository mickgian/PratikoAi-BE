"""DEV-412: Email Tracking API Endpoints.

Link-based tracking redirect endpoint (GDPR-safe).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.services.email_tracking_service import email_tracking_service

router = APIRouter(prefix="/t", tags=["tracking"])


@router.get("/{tracking_type}/{token}")
async def track_redirect(
    tracking_type: str,
    token: str,
    dest: str = Query(..., description="URL di destinazione"),
    cid: UUID = Query(..., description="ID comunicazione"),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Registra evento di tracking e reindirizza alla destinazione."""
    await email_tracking_service.record_event(
        db,
        tracking_token=token,
        event_type=tracking_type,
        client_id=0,
    )
    return RedirectResponse(url=dest, status_code=302)


@router.get("/stats/{communication_id}")
async def get_tracking_stats(
    communication_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Statistiche di tracking per una comunicazione."""
    return await email_tracking_service.get_communication_stats(
        db,
        communication_id=communication_id,
    )
