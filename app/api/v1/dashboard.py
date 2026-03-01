"""DEV-356 + DEV-436: Dashboard API Endpoint with period filtering.

Returns all aggregated dashboard data with optional period selector.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.services.dashboard_service import DashboardPeriod, dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
async def get_dashboard(
    studio_id: UUID = Query(..., description="ID dello studio"),
    period: str = Query(default="month", description="Periodo: week, month, year"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Restituisce dati aggregati della dashboard dello studio con filtro periodo."""
    try:
        dash_period = DashboardPeriod(period.lower())
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Periodo non valido: {period}. Usa: week, month, year.")

    return await dashboard_service.get_dashboard_data_with_period(
        db,
        studio_id=studio_id,
        period=dash_period,
    )


@router.post("/invalidate-cache", status_code=204)
async def invalidate_dashboard_cache(
    studio_id: UUID = Query(..., description="ID dello studio"),
) -> None:
    """Invalida la cache della dashboard."""
    await dashboard_service.invalidate_cache(studio_id)
