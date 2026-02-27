"""DEV-311: Studio API Endpoints — CRUD for Studio entity.

Thin route handlers delegating to StudioService.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.schemas.studio import StudioCreate, StudioResponse, StudioUpdate
from app.services.studio_service import studio_service

router = APIRouter(prefix="/studios", tags=["studios"])


@router.post("", response_model=StudioResponse, status_code=201)
async def create_studio(
    body: StudioCreate,
    db: AsyncSession = Depends(get_db),
) -> StudioResponse:
    """Crea un nuovo studio professionale."""
    try:
        studio = await studio_service.create(
            db,
            name=body.name,
            slug=body.slug,
            max_clients=body.max_clients,
            settings=body.settings,
        )
        await db.commit()
        return StudioResponse.model_validate(studio)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{studio_id}", response_model=StudioResponse)
async def get_studio(
    studio_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> StudioResponse:
    """Recupera uno studio per ID."""
    studio = await studio_service.get_by_id(db, studio_id=studio_id)
    if studio is None:
        raise HTTPException(status_code=404, detail="Studio non trovato.")
    return StudioResponse.model_validate(studio)


@router.get("/by-slug/{slug}", response_model=StudioResponse)
async def get_studio_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db),
) -> StudioResponse:
    """Recupera uno studio per slug."""
    studio = await studio_service.get_by_slug(db, slug=slug)
    if studio is None:
        raise HTTPException(status_code=404, detail="Studio non trovato.")
    return StudioResponse.model_validate(studio)


@router.put("/{studio_id}", response_model=StudioResponse)
async def update_studio(
    studio_id: UUID,
    body: StudioUpdate,
    db: AsyncSession = Depends(get_db),
) -> StudioResponse:
    """Aggiorna i dati di uno studio."""
    try:
        studio = await studio_service.update(
            db,
            studio_id=studio_id,
            name=body.name,
            slug=body.slug,
            max_clients=body.max_clients,
            settings=body.settings,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if studio is None:
        raise HTTPException(status_code=404, detail="Studio non trovato.")

    await db.commit()
    return StudioResponse.model_validate(studio)


@router.delete("/{studio_id}", status_code=204)
async def deactivate_studio(
    studio_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Disattiva uno studio (soft-delete)."""
    studio = await studio_service.deactivate(db, studio_id=studio_id)
    if studio is None:
        raise HTTPException(status_code=404, detail="Studio non trovato.")
    await db.commit()
