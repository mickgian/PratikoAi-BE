"""DEV-332: Communication API Endpoints — Workflow endpoints.

Supports create, review, approve, reject, send workflow.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.communication import StatoComunicazione
from app.models.database import get_db
from app.schemas.communication import BulkCommunicationCreate, CommunicationCreate, CommunicationResponse
from app.services.communication_service import communication_service

router = APIRouter(prefix="/communications", tags=["communications"])


@router.post("", response_model=CommunicationResponse, status_code=201)
async def create_communication(
    body: CommunicationCreate,
    studio_id: UUID = Query(...),
    created_by: int = Query(..., description="ID dell'utente creatore"),
    db: AsyncSession = Depends(get_db),
) -> CommunicationResponse:
    """Crea una nuova bozza di comunicazione."""
    comm = await communication_service.create_draft(
        db,
        studio_id=studio_id,
        subject=body.subject,
        content=body.content,
        channel=body.channel,
        created_by=created_by,
        client_id=body.client_id,
        normativa_riferimento=body.normativa_riferimento,
        matching_rule_id=body.matching_rule_id,
    )
    await db.commit()
    return CommunicationResponse.model_validate(comm)


@router.get("", response_model=list[CommunicationResponse])
async def list_communications(
    studio_id: UUID = Query(...),
    status: StatoComunicazione | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[CommunicationResponse]:
    """Elenco comunicazioni dello studio."""
    comms = await communication_service.list_by_studio(
        db, studio_id=studio_id, status=status, offset=offset, limit=limit
    )
    return [CommunicationResponse.model_validate(c) for c in comms]


@router.get("/{communication_id}", response_model=CommunicationResponse)
async def get_communication(
    communication_id: UUID,
    studio_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
) -> CommunicationResponse:
    """Recupera una comunicazione per ID."""
    comm = await communication_service.get_by_id(db, communication_id=communication_id, studio_id=studio_id)
    if comm is None:
        raise HTTPException(status_code=404, detail="Comunicazione non trovata.")
    return CommunicationResponse.model_validate(comm)


@router.post("/{communication_id}/submit", response_model=CommunicationResponse)
async def submit_for_review(
    communication_id: UUID,
    studio_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
) -> CommunicationResponse:
    """Invia comunicazione per revisione (DRAFT → PENDING_REVIEW)."""
    try:
        comm = await communication_service.submit_for_review(
            db, communication_id=communication_id, studio_id=studio_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if comm is None:
        raise HTTPException(status_code=404, detail="Comunicazione non trovata.")
    await db.commit()
    return CommunicationResponse.model_validate(comm)


@router.post("/{communication_id}/approve", response_model=CommunicationResponse)
async def approve_communication(
    communication_id: UUID,
    studio_id: UUID = Query(...),
    approved_by: int = Query(..., description="ID dell'utente approvatore"),
    db: AsyncSession = Depends(get_db),
) -> CommunicationResponse:
    """Approva comunicazione (PENDING_REVIEW → APPROVED)."""
    try:
        comm = await communication_service.approve(
            db,
            communication_id=communication_id,
            studio_id=studio_id,
            approved_by=approved_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if comm is None:
        raise HTTPException(status_code=404, detail="Comunicazione non trovata.")
    await db.commit()
    return CommunicationResponse.model_validate(comm)


@router.post("/{communication_id}/reject", response_model=CommunicationResponse)
async def reject_communication(
    communication_id: UUID,
    studio_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
) -> CommunicationResponse:
    """Rifiuta comunicazione (PENDING_REVIEW → REJECTED)."""
    try:
        comm = await communication_service.reject(db, communication_id=communication_id, studio_id=studio_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if comm is None:
        raise HTTPException(status_code=404, detail="Comunicazione non trovata.")
    await db.commit()
    return CommunicationResponse.model_validate(comm)


@router.post("/{communication_id}/send", response_model=CommunicationResponse)
async def mark_sent(
    communication_id: UUID,
    studio_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
) -> CommunicationResponse:
    """Segna comunicazione come inviata (APPROVED → SENT)."""
    try:
        comm = await communication_service.mark_sent(db, communication_id=communication_id, studio_id=studio_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if comm is None:
        raise HTTPException(status_code=404, detail="Comunicazione non trovata.")
    await db.commit()
    return CommunicationResponse.model_validate(comm)


@router.post("/bulk", response_model=list[CommunicationResponse], status_code=201)
async def create_bulk_communications(
    body: BulkCommunicationCreate,
    studio_id: UUID = Query(...),
    created_by: int = Query(...),
    db: AsyncSession = Depends(get_db),
) -> list[CommunicationResponse]:
    """DEV-335: Crea bozze di comunicazione per più clienti."""
    comms = await communication_service.create_bulk_drafts(
        db,
        studio_id=studio_id,
        client_ids=body.client_ids,
        subject=body.subject,
        content=body.content,
        channel=body.channel,
        created_by=created_by,
        normativa_riferimento=body.normativa_riferimento,
        matching_rule_id=body.matching_rule_id,
    )
    await db.commit()
    return [CommunicationResponse.model_validate(c) for c in comms]
