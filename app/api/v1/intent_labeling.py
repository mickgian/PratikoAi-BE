"""Intent Labeling API Endpoints.

DEV-253: Expert labeling UI for intent classifier training.

Provides REST API endpoints for:
- Retrieving the labeling queue (low-confidence predictions)
- Submitting expert labels
- Viewing labeling statistics
- Exporting labeled data for model training
- Skipping queries in the queue

Access control (DEV-253c):
- Queue, label, skip, stats: SUPER_USER or ADMIN with verified ExpertProfile
- Export: ADMIN only (training data export)
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.core.logging import logger
from app.models.database import get_db
from app.models.quality_analysis import ExpertProfile
from app.models.user import User, UserRole
from app.schemas.intent_labeling import (
    LabeledQueryResponse,
    LabelingStatsResponse,
    LabelSubmission,
    QueueResponse,
    SkipResponse,
)
from app.services.intent_labeling_service import intent_labeling_service

router = APIRouter(prefix="/labeling", tags=["Intent Labeling"])


async def _require_verified_expert(user: User, db: AsyncSession) -> None:
    """Validate user has SUPER_USER or ADMIN role with a verified ExpertProfile.

    Matches the access control pattern from expert_feedback.py (DEV-253c).

    Args:
        user: Authenticated user
        db: Database session

    Raises:
        HTTPException: 403 if user lacks required role or expert profile
    """
    if user.role not in [UserRole.SUPER_USER.value, UserRole.ADMIN.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accesso non autorizzato",
        )

    result = await db.execute(select(ExpertProfile).where(ExpertProfile.user_id == user.id))
    expert = result.scalar_one_or_none()

    if not expert:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Profilo esperto non trovato",
        )

    if not expert.is_active or not expert.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Profilo esperto non attivo o non verificato",
        )


def _require_admin(user: User) -> None:
    """Validate user has ADMIN role.

    Args:
        user: Authenticated user

    Raises:
        HTTPException: 403 if user is not admin
    """
    if user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accesso non autorizzato",
        )


@router.get("/queue", response_model=QueueResponse)
async def get_labeling_queue(
    page: int = 1,
    page_size: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QueueResponse:
    """Get the labeling queue of unlabeled queries.

    Returns queries ordered by confidence (lowest first) so experts
    can prioritize the most uncertain classifications.

    Args:
        page: Page number (1-indexed, default 1)
        page_size: Items per page (default 50, max 100)
        current_user: Authenticated user
        db: Database session

    Returns:
        QueueResponse with paginated unlabeled queries
    """
    await _require_verified_expert(current_user, db)

    # Validate pagination
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 50
    if page_size > 100:
        page_size = 100

    try:
        return await intent_labeling_service.get_queue(
            page=page,
            page_size=page_size,
            db=db,
        )
    except Exception as e:
        logger.error(
            "intent_labeling_queue_error",
            error_type=type(e).__name__,
            error_message=str(e),
            user_id=current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore nel recupero della coda: {e}",
        )


@router.post("/label", response_model=LabeledQueryResponse)
async def submit_label(
    submission: LabelSubmission,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LabeledQueryResponse:
    """Submit an expert label for a query.

    Allows experts to assign the correct intent to a query that was
    classified with low confidence by the HF classifier.

    Args:
        submission: Label submission data
        current_user: Authenticated user
        db: Database session

    Returns:
        LabeledQueryResponse with updated query data

    Raises:
        400: Invalid intent
        403: User not authorized
        404: Query not found
    """
    await _require_verified_expert(current_user, db)

    try:
        result = await intent_labeling_service.submit_label(
            query_id=submission.query_id,
            expert_intent=submission.expert_intent,
            labeled_by=current_user.id,
            notes=submission.notes,
            db=db,
        )

        logger.info(
            "intent_label_submitted",
            query_id=str(submission.query_id),
            expert_intent=submission.expert_intent,
            user_id=current_user.id,
        )

        return result

    except ValueError as e:
        error_msg = str(e)
        if "non trovata" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        )
    except Exception as e:
        logger.error(
            "intent_label_submission_error",
            error_type=type(e).__name__,
            error_message=str(e),
            user_id=current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore nell'invio dell'etichetta: {e}",
        )


@router.get("/stats", response_model=LabelingStatsResponse)
async def get_labeling_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LabelingStatsResponse:
    """Get labeling progress statistics.

    Returns metrics about the labeling progress including total queries,
    labeled count, and per-intent distribution.

    Args:
        current_user: Authenticated user
        db: Database session

    Returns:
        LabelingStatsResponse with progress metrics
    """
    await _require_verified_expert(current_user, db)

    try:
        return await intent_labeling_service.get_stats(db=db)
    except Exception as e:
        logger.error(
            "intent_labeling_stats_error",
            error_type=type(e).__name__,
            error_message=str(e),
            user_id=current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore nel calcolo delle statistiche: {e}",
        )


@router.get("/export")
async def export_training_data(
    format: str = "jsonl",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Export labeled data for HuggingFace model training.

    Only accessible to ADMIN users. Exports labeled queries in JSONL
    (HuggingFace-compatible) or CSV format.

    Args:
        format: Export format ("jsonl" or "csv", default "jsonl")
        current_user: Authenticated user
        db: Database session

    Returns:
        File download response with exported data
    """
    _require_admin(current_user)

    if format not in ("jsonl", "csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato non supportato. Usare 'jsonl' o 'csv'.",
        )

    try:
        content, count = await intent_labeling_service.export_training_data(
            format=format,
            db=db,
        )

        if count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Nessun dato etichettato disponibile per l'esportazione",
            )

        # Set content type and filename based on format
        if format == "jsonl":
            media_type = "application/x-ndjson"
            filename = "intent_training_data.jsonl"
        else:
            media_type = "text/csv"
            filename = "intent_training_data.csv"

        logger.info(
            "intent_labeling_export_complete",
            format=format,
            count=count,
            user_id=current_user.id,
        )

        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "intent_labeling_export_error",
            error_type=type(e).__name__,
            error_message=str(e),
            user_id=current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore nell'esportazione: {e}",
        )


@router.post("/skip/{query_id}", response_model=SkipResponse)
async def skip_query(
    query_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SkipResponse:
    """Skip a query in the labeling queue.

    Increments the skip count, allowing experts to move past difficult
    or ambiguous queries.

    Args:
        query_id: UUID of the query to skip
        current_user: Authenticated user
        db: Database session

    Returns:
        SkipResponse with updated skip count
    """
    await _require_verified_expert(current_user, db)

    try:
        skip_count = await intent_labeling_service.skip_query(
            query_id=query_id,
            db=db,
        )

        return SkipResponse(
            id=query_id,
            skip_count=skip_count,
            message="Query saltata con successo",
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "intent_labeling_skip_error",
            error_type=type(e).__name__,
            error_message=str(e),
            user_id=current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore nel saltare la query: {e}",
        )
