"""User feedback API endpoint for recording thumbs-up/down on AI responses (DEV-255).

Sends user satisfaction scores to Langfuse for quality monitoring.
"""

import logging

from fastapi import APIRouter, Depends

from app.api.v1.auth import get_current_session
from app.models.session import Session
from app.schemas.feedback import UserFeedbackRequest, UserFeedbackResponse
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
