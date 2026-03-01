"""User feedback API endpoints for recording feedback on AI responses (DEV-255, DEV-433).

DEV-255: Thumbs-up/down scores sent to Langfuse.
DEV-433: Detailed feedback with category/type, dual-write to DB + Langfuse.
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_session
from app.models.chat_feedback import ChatFeedback, FeedbackType
from app.models.database import get_db
from app.models.session import Session
from app.schemas.feedback import DetailedFeedbackRequest, UserFeedbackRequest, UserFeedbackResponse
from app.services.feedback_service import feedback_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=UserFeedbackResponse, status_code=201)
async def submit_feedback(
    body: UserFeedbackRequest,
    session: Session = Depends(get_current_session),
) -> UserFeedbackResponse:
    """Submit user feedback (thumbs up/down) on an AI response.

    Args:
        body: Feedback request with trace_id, score, and optional comment.
        session: Authenticated user session.

    Returns:
        UserFeedbackResponse with success status.
    """
    success = feedback_service.submit_feedback(
        trace_id=body.trace_id,
        score=body.score,
        comment=body.comment,
    )

    if success:
        return UserFeedbackResponse(
            success=True,
            message="Feedback registrato con successo.",
        )

    return UserFeedbackResponse(
        success=False,
        message="Feedback ricevuto.",
    )


@router.post("/detailed", response_model=UserFeedbackResponse, status_code=201)
async def submit_detailed_feedback(
    body: DetailedFeedbackRequest,
    db: AsyncSession = Depends(get_db),
) -> UserFeedbackResponse:
    """Submit detailed feedback with category and type, persisted to DB + Langfuse.

    Dual-write: DB is authoritative; Langfuse failure does not block persistence.

    Args:
        body: Detailed feedback request with type, category, and comment.
        db: Async database session.

    Returns:
        UserFeedbackResponse with success status.
    """
    fb = ChatFeedback(
        user_id=body.user_id,
        studio_id=body.studio_id,
        trace_id=body.trace_id,
        message_id=body.message_id,
        feedback_type=FeedbackType(body.feedback_type),
        category=body.category,
        comment=body.comment,
        score=body.score,
    )
    db.add(fb)
    await db.flush()
    await db.commit()

    # Fire-and-forget Langfuse — failure must not block DB persistence
    try:
        feedback_service.submit_feedback(
            trace_id=body.trace_id,
            score=body.score,
            comment=body.comment,
        )
    except Exception:
        logger.warning(
            "detailed_feedback_langfuse_failed",
            extra={"trace_id": body.trace_id},
        )

    return UserFeedbackResponse(
        success=True,
        message="Feedback registrato con successo.",
    )
