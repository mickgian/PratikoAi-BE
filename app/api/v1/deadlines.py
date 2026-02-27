"""DEV-385: Deadline API Endpoints -- CRUD for deadlines and client-deadline associations.

Thin route handlers delegating to DeadlineService.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.deadline import DeadlineSource, DeadlineType
from app.schemas.deadline import ClientDeadlineResponse, DeadlineCreateRequest, DeadlineResponse
from app.services.deadline_service import deadline_service

router = APIRouter(prefix="/deadlines", tags=["deadlines"])


# ---------------------------------------------------------------------------
# GET /deadlines/upcoming -- List upcoming deadlines
# ---------------------------------------------------------------------------


@router.get("/upcoming", response_model=list[DeadlineResponse])
async def list_upcoming_deadlines(
    days_ahead: int = Query(default=30, ge=1, le=365, description="Giorni in avanti"),
    deadline_type: DeadlineType | None = Query(default=None, description="Filtra per tipo"),
    db: AsyncSession = Depends(get_db),
) -> list[DeadlineResponse]:
    """Elenco scadenze in arrivo entro N giorni."""
    deadlines = await deadline_service.list_upcoming(db, days_ahead=days_ahead)

    if deadline_type is not None:
        deadlines = [d for d in deadlines if d.deadline_type == deadline_type]

    return [DeadlineResponse.model_validate(d) for d in deadlines]


# ---------------------------------------------------------------------------
# GET /deadlines/{deadline_id} -- Get single deadline
# ---------------------------------------------------------------------------


@router.get("/{deadline_id}", response_model=DeadlineResponse)
async def get_deadline(
    deadline_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> DeadlineResponse:
    """Recupera una scadenza per ID."""
    deadline = await deadline_service.get_by_id(db, deadline_id=deadline_id)
    if deadline is None:
        raise HTTPException(status_code=404, detail="Scadenza non trovata.")
    return DeadlineResponse.model_validate(deadline)


# ---------------------------------------------------------------------------
# POST /deadlines -- Create deadline
# ---------------------------------------------------------------------------


@router.post("", response_model=DeadlineResponse, status_code=201)
async def create_deadline(
    body: DeadlineCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> DeadlineResponse:
    """Crea una nuova scadenza."""
    try:
        deadline = await deadline_service.create(
            db,
            title=body.title,
            description=body.description,
            deadline_type=DeadlineType(body.deadline_type),
            source=DeadlineSource(body.source),
            due_date=body.due_date,
            recurrence_rule=body.recurrence_rule,
        )
        await db.commit()
        return DeadlineResponse.model_validate(deadline)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /deadlines/studio/{studio_id}/client-deadlines -- List client deadlines
# ---------------------------------------------------------------------------


@router.get(
    "/studio/{studio_id}/client-deadlines",
    response_model=list[ClientDeadlineResponse],
)
async def list_client_deadlines(
    studio_id: UUID,
    completed: bool | None = Query(default=None, description="Filtra per stato completamento"),
    db: AsyncSession = Depends(get_db),
) -> list[ClientDeadlineResponse]:
    """Elenco scadenze cliente per studio."""
    client_deadlines = await deadline_service.list_by_studio(db, studio_id=studio_id, completed=completed)
    return [ClientDeadlineResponse.model_validate(cd) for cd in client_deadlines]


# ---------------------------------------------------------------------------
# PUT /deadlines/client-deadlines/{id}/complete -- Mark as complete
# ---------------------------------------------------------------------------


@router.put(
    "/client-deadlines/{client_deadline_id}/complete",
    response_model=ClientDeadlineResponse,
)
async def mark_client_deadline_complete(
    client_deadline_id: UUID,
    x_studio_id: UUID = Header(..., description="ID dello studio"),
    db: AsyncSession = Depends(get_db),
) -> ClientDeadlineResponse:
    """Segna una scadenza cliente come completata."""
    cd = await deadline_service.mark_completed(db, client_deadline_id=client_deadline_id)
    if cd is None:
        raise HTTPException(status_code=404, detail="Scadenza cliente non trovata.")
    await db.commit()
    return ClientDeadlineResponse.model_validate(cd)
