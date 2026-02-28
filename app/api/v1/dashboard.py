"""DEV-356: Dashboard API Endpoint.

Single endpoint returning all aggregated dashboard data.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.services.dashboard_service import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
async def get_dashboard(
    studio_id: UUID = Query(..., description="ID dello studio"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Restituisce dati aggregati della dashboard dello studio."""
    return await dashboard_service.get_dashboard_data(db, studio_id=studio_id)


@router.post("/invalidate-cache", status_code=204)
async def invalidate_dashboard_cache(
    studio_id: UUID = Query(..., description="ID dello studio"),
) -> None:
    """Invalida la cache della dashboard."""
    await dashboard_service.invalidate_cache(studio_id)
