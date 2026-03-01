"""DEV-430: Quick Action Counts API — Live counts for 6 Quick Action cards."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.services.quick_action_counts_service import quick_action_counts_service

router = APIRouter(prefix="/quick-actions", tags=["quick-actions"])


@router.get("/counts")
async def get_quick_action_counts(
    x_studio_id: UUID = Header(..., description="ID dello studio"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """Restituisce i conteggi per le 6 card Quick Action."""
    return await quick_action_counts_service.get_counts(db, studio_id=x_studio_id)
