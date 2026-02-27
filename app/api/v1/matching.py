"""DEV-326: Matching API Endpoints — Suggestions management.

Thin route handlers for proactive matching suggestions.
Supports listing, triggering background matching, and marking read/dismissed.
"""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.database import get_db
from app.models.proactive_suggestion import ProactiveSuggestion
from app.schemas.matching import SuggestionResponse, TriggerMatchingRequest, TriggerMatchingResponse

router = APIRouter(prefix="/matching", tags=["matching"])


# ---------------------------------------------------------------------------
# GET /matching/suggestions — List suggestions
# ---------------------------------------------------------------------------


@router.get("/suggestions", response_model=list[SuggestionResponse])
async def list_suggestions(
    x_studio_id: UUID = Header(..., description="ID dello studio"),
    unread_only: bool = Query(default=False, description="Filtra solo suggerimenti non letti"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[SuggestionResponse]:
    """Elenco suggerimenti proattivi per lo studio."""
    stmt = (
        select(ProactiveSuggestion)
        .where(ProactiveSuggestion.studio_id == x_studio_id)
        .order_by(ProactiveSuggestion.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    if unread_only:
        stmt = stmt.where(ProactiveSuggestion.is_read.is_(False))

    result = await db.execute(stmt)
    suggestions = result.scalars().all()

    return [SuggestionResponse.model_validate(s) for s in suggestions]


# ---------------------------------------------------------------------------
# POST /matching/trigger — Trigger matching job
# ---------------------------------------------------------------------------


@router.post("/trigger", response_model=TriggerMatchingResponse, status_code=202)
async def trigger_matching(
    body: TriggerMatchingRequest,
    x_studio_id: UUID = Header(..., description="ID dello studio"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
) -> TriggerMatchingResponse:
    """Avvia il job di matching in background."""
    logger.info(
        "matching_trigger_requested",
        studio_id=str(x_studio_id),
        knowledge_item_id=body.knowledge_item_id,
        trigger=body.trigger,
    )

    background_tasks.add_task(
        _run_matching_background,
        studio_id=x_studio_id,
        knowledge_item_id=body.knowledge_item_id,
        trigger=body.trigger,
    )

    return TriggerMatchingResponse(
        status="accepted",
        studio_id=x_studio_id,
        knowledge_item_id=body.knowledge_item_id,
        trigger=body.trigger,
        message="Job di matching avviato in background.",
    )


async def _run_matching_background(
    studio_id: UUID,
    knowledge_item_id: int | None,
    trigger: str,
) -> None:
    """Execute matching job in the background with its own DB session.

    Imports run_matching_job lazily to avoid circular imports
    and to allow the job module to be created independently.
    """
    try:
        from app.jobs.matching_job import run_matching_job
        from app.models.database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            await run_matching_job(
                db=db,
                studio_id=studio_id,
                knowledge_item_id=knowledge_item_id,
                trigger=trigger,
            )
            await db.commit()
    except ImportError:
        logger.warning(
            "matching_job_not_available",
            studio_id=str(studio_id),
            message="Il modulo matching_job non è ancora disponibile.",
        )
    except Exception as exc:
        logger.error(
            "matching_job_failed",
            studio_id=str(studio_id),
            knowledge_item_id=knowledge_item_id,
            trigger=trigger,
            error_type=type(exc).__name__,
            error_message=str(exc),
        )


# ---------------------------------------------------------------------------
# PUT /matching/suggestions/{id}/read — Mark as read
# ---------------------------------------------------------------------------


@router.put("/suggestions/{suggestion_id}/read", response_model=SuggestionResponse)
async def mark_suggestion_read(
    suggestion_id: UUID,
    x_studio_id: UUID = Header(..., description="ID dello studio"),
    db: AsyncSession = Depends(get_db),
) -> SuggestionResponse:
    """Segna un suggerimento come letto."""
    suggestion = await db.get(ProactiveSuggestion, suggestion_id)

    if suggestion is None or suggestion.studio_id != x_studio_id:
        raise HTTPException(status_code=404, detail="Suggerimento non trovato.")

    suggestion.is_read = True
    await db.commit()

    return SuggestionResponse.model_validate(suggestion)


# ---------------------------------------------------------------------------
# PUT /matching/suggestions/{id}/dismiss — Mark as dismissed
# ---------------------------------------------------------------------------


@router.put("/suggestions/{suggestion_id}/dismiss", response_model=SuggestionResponse)
async def mark_suggestion_dismissed(
    suggestion_id: UUID,
    x_studio_id: UUID = Header(..., description="ID dello studio"),
    db: AsyncSession = Depends(get_db),
) -> SuggestionResponse:
    """Segna un suggerimento come ignorato."""
    suggestion = await db.get(ProactiveSuggestion, suggestion_id)

    if suggestion is None or suggestion.studio_id != x_studio_id:
        raise HTTPException(status_code=404, detail="Suggerimento non trovato.")

    suggestion.is_dismissed = True
    await db.commit()

    return SuggestionResponse.model_validate(suggestion)
