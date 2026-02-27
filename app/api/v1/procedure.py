"""DEV-342: Procedura API Endpoints — List, progress, completion tracking.

Endpoints for procedure management and user progress tracking.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.procedura import ProceduraCategory
from app.schemas.procedura import (
    ChecklistItemUpdate,
    DocumentChecklistUpdate,
    ProceduraNotesUpdate,
    ProceduraProgressCreate,
    ProceduraProgressResponse,
    ProceduraResponse,
)
from app.services.procedura_service import procedura_service

router = APIRouter(prefix="/procedure", tags=["procedure"])


@router.get("", response_model=list[ProceduraResponse])
async def list_procedure(
    category: ProceduraCategory | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[ProceduraResponse]:
    """Elenco procedure attive, opzionalmente filtrate per categoria."""
    procedures = await procedura_service.list_active(db, category=category)
    return [ProceduraResponse.model_validate(p) for p in procedures]


@router.get("/{code}", response_model=ProceduraResponse)
async def get_procedura_by_code(
    code: str,
    db: AsyncSession = Depends(get_db),
) -> ProceduraResponse:
    """Recupera una procedura per codice."""
    proc = await procedura_service.get_by_code(db, code=code)
    if proc is None:
        raise HTTPException(status_code=404, detail="Procedura non trovata.")
    return ProceduraResponse.model_validate(proc)


@router.post("/progress", response_model=ProceduraProgressResponse, status_code=201)
async def start_progress(
    body: ProceduraProgressCreate,
    user_id: int = Query(...),
    studio_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
) -> ProceduraProgressResponse:
    """Inizia il tracciamento di una procedura."""
    try:
        progress = await procedura_service.start_progress(
            db,
            user_id=user_id,
            studio_id=studio_id,
            procedura_id=body.procedura_id,
            client_id=body.client_id,
        )
        await db.commit()
        return ProceduraProgressResponse.model_validate(progress)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/progress/{progress_id}/advance", response_model=ProceduraProgressResponse)
async def advance_step(
    progress_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ProceduraProgressResponse:
    """Avanza allo step successivo della procedura."""
    progress = await procedura_service.advance_step(db, progress_id=progress_id)
    if progress is None:
        raise HTTPException(status_code=404, detail="Progresso non trovato.")
    await db.commit()
    return ProceduraProgressResponse.model_validate(progress)


@router.get("/progress/list", response_model=list[ProceduraProgressResponse])
async def list_user_progress(
    user_id: int = Query(...),
    studio_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
) -> list[ProceduraProgressResponse]:
    """Elenco progressi dell'utente per tutte le procedure."""
    progress_list = await procedura_service.list_user_progress(db, user_id=user_id, studio_id=studio_id)
    return [ProceduraProgressResponse.model_validate(p) for p in progress_list]


@router.put("/progress/{progress_id}/checklist", response_model=ProceduraProgressResponse)
async def update_checklist_item(
    progress_id: UUID,
    body: ChecklistItemUpdate,
    db: AsyncSession = Depends(get_db),
) -> ProceduraProgressResponse:
    """DEV-343: Aggiorna stato di un elemento checklist."""
    try:
        progress = await procedura_service.update_checklist_item(
            db,
            progress_id=progress_id,
            step_index=body.step_index,
            item_index=body.item_index,
            completed=body.completed,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if progress is None:
        raise HTTPException(status_code=404, detail="Progresso non trovato.")
    await db.commit()
    return ProceduraProgressResponse.model_validate(progress)


@router.put("/progress/{progress_id}/notes", response_model=ProceduraProgressResponse)
async def update_notes(
    progress_id: UUID,
    body: ProceduraNotesUpdate,
    db: AsyncSession = Depends(get_db),
) -> ProceduraProgressResponse:
    """DEV-344: Aggiorna le note della procedura."""
    progress = await procedura_service.update_notes(db, progress_id=progress_id, notes=body.notes)
    if progress is None:
        raise HTTPException(status_code=404, detail="Progresso non trovato.")
    await db.commit()
    return ProceduraProgressResponse.model_validate(progress)


@router.put("/progress/{progress_id}/document", response_model=ProceduraProgressResponse)
async def update_document_status(
    progress_id: UUID,
    body: DocumentChecklistUpdate,
    db: AsyncSession = Depends(get_db),
) -> ProceduraProgressResponse:
    """DEV-344: Aggiorna stato di verifica di un documento."""
    try:
        progress = await procedura_service.update_document_status(
            db,
            progress_id=progress_id,
            document_name=body.document_name,
            verified=body.verified,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if progress is None:
        raise HTTPException(status_code=404, detail="Progresso non trovato.")
    await db.commit()
    return ProceduraProgressResponse.model_validate(progress)
