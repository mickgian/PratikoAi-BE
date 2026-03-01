"""DEV-441: Settings API — Studio preferences (notification toggles, display prefs)."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.database import get_db

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsResponse(BaseModel):
    """Current studio settings."""

    studio_id: UUID
    notification_preferences: dict[str, bool]
    display_preferences: dict[str, Any]


class SettingsUpdateRequest(BaseModel):
    """Update studio settings."""

    notification_preferences: dict[str, bool] | None = None
    display_preferences: dict[str, Any] | None = None


DEFAULT_NOTIFICATION_PREFS: dict[str, bool] = {
    "scadenza": True,
    "match": True,
    "comunicazione": True,
    "normativa": True,
}

DEFAULT_DISPLAY_PREFS: dict[str, Any] = {
    "theme": "light",
    "language": "it",
    "items_per_page": 25,
}


@router.get("", response_model=SettingsResponse)
async def get_settings(
    x_studio_id: UUID = Header(..., description="ID studio"),
    db: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    """Recupera le impostazioni dello studio."""
    settings = await _load_studio_settings(db, studio_id=x_studio_id)
    return SettingsResponse(
        studio_id=x_studio_id,
        notification_preferences=settings.get("notification_preferences", DEFAULT_NOTIFICATION_PREFS),
        display_preferences=settings.get("display_preferences", DEFAULT_DISPLAY_PREFS),
    )


@router.put("", response_model=SettingsResponse)
async def update_settings(
    body: SettingsUpdateRequest,
    x_studio_id: UUID = Header(..., description="ID studio"),
    db: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    """Aggiorna le impostazioni dello studio."""
    from app.models.studio import Studio

    result = await db.execute(select(Studio).where(Studio.id == x_studio_id))
    studio = result.scalar_one_or_none()
    if studio is None:
        raise HTTPException(status_code=404, detail="Studio non trovato.")

    current = studio.settings if isinstance(studio.settings, dict) else {}

    if body.notification_preferences is not None:
        current["notification_preferences"] = body.notification_preferences
    if body.display_preferences is not None:
        current["display_preferences"] = body.display_preferences

    studio.settings = current
    await db.flush()
    await db.commit()

    logger.info("studio_settings_updated", studio_id=str(x_studio_id))

    return SettingsResponse(
        studio_id=x_studio_id,
        notification_preferences=current.get("notification_preferences", DEFAULT_NOTIFICATION_PREFS),
        display_preferences=current.get("display_preferences", DEFAULT_DISPLAY_PREFS),
    )


async def _load_studio_settings(db: AsyncSession, *, studio_id: UUID) -> dict:
    """Load settings from Studio.settings JSONB."""
    try:
        from app.models.studio import Studio

        result = await db.execute(select(Studio).where(Studio.id == studio_id))
        studio = result.scalar_one_or_none()
        if studio and isinstance(studio.settings, dict):
            return studio.settings
    except Exception as e:
        logger.warning("settings_load_failed", error=str(e))
    return {}
