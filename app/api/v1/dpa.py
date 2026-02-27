"""DEV-373: DPA API Endpoints — DPA acceptance workflow.

Users must accept DPA before adding clients.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.services.dpa_service import dpa_service

router = APIRouter(prefix="/dpa", tags=["dpa"])


class DPAResponse(BaseModel):
    """DPA response."""

    id: UUID
    title: str
    version: str
    status: str
    effective_from: str | None = None

    model_config = {"from_attributes": True}


class DPAAcceptanceRequest(BaseModel):
    """Request to accept a DPA."""

    dpa_id: UUID


class DPAAcceptanceResponse(BaseModel):
    """DPA acceptance confirmation."""

    id: UUID
    dpa_id: UUID
    studio_id: UUID
    accepted_by: int
    ip_address: str

    model_config = {"from_attributes": True}


class DPAStatusResponse(BaseModel):
    """DPA acceptance status check."""

    accepted: bool


@router.get("/active", response_model=DPAResponse | None)
async def get_active_dpa(
    db: AsyncSession = Depends(get_db),
) -> DPAResponse | None:
    """Recupera il DPA attivo corrente."""
    dpa = await dpa_service.get_active_dpa(db)
    if dpa is None:
        return None
    return DPAResponse.model_validate(dpa)


@router.post("/accept", response_model=DPAAcceptanceResponse, status_code=201)
async def accept_dpa(
    body: DPAAcceptanceRequest,
    request: Request,
    studio_id: UUID = Query(...),
    accepted_by: int = Query(...),
    db: AsyncSession = Depends(get_db),
) -> DPAAcceptanceResponse:
    """Accetta il DPA per lo studio."""
    try:
        ip = request.client.host if request.client else "unknown"
        ua = request.headers.get("user-agent")

        acceptance = await dpa_service.accept(
            db,
            dpa_id=body.dpa_id,
            studio_id=studio_id,
            accepted_by=accepted_by,
            ip_address=ip,
            user_agent=ua,
        )
        await db.commit()
        return DPAAcceptanceResponse.model_validate(acceptance)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/status", response_model=DPAStatusResponse)
async def check_dpa_status(
    studio_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
) -> DPAStatusResponse:
    """Verifica se lo studio ha accettato il DPA corrente."""
    accepted = await dpa_service.check_accepted(db, studio_id=studio_id)
    return DPAStatusResponse(accepted=accepted)
