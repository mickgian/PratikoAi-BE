"""DEV-415: Unsubscribe API Endpoints.

Handles email unsubscribe link processing.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.services.unsubscribe_service import unsubscribe_service

router = APIRouter(prefix="/unsubscribe", tags=["unsubscribe"])


@router.get("/{client_id}")
async def unsubscribe_client(
    client_id: int,
    token: str = Query(..., description="Token di verifica"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Elabora richiesta di disiscrizione dalla comunicazione."""
    success = await unsubscribe_service.unsubscribe(
        db,
        token=token,
        client_id=client_id,
    )
    if not success:
        raise HTTPException(status_code=404, detail="Cliente non trovato.")
    return {"message": "Disiscrizione completata con successo."}


@router.post("/{client_id}")
async def unsubscribe_client_post(
    client_id: int,
    token: str = Query(..., description="Token di verifica"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """One-click unsubscribe (List-Unsubscribe-Post support)."""
    success = await unsubscribe_service.unsubscribe(
        db,
        token=token,
        client_id=client_id,
    )
    if not success:
        raise HTTPException(status_code=404, detail="Cliente non trovato.")
    return {"message": "Disiscrizione completata con successo."}
