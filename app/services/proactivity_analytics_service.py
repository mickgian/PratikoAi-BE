"""ProactivityAnalyticsService for PratikoAI v1.5 - DEV-156.

This service handles analytics tracking for proactive features:
- track_action_click(): Record when users click suggested actions
- track_question_answer(): Record when users answer interactive questions
- get_popular_actions(): Retrieve action popularity statistics

Design Principles:
- Non-blocking: DB failures are logged but don't raise exceptions
- GDPR compliant: User data deleted via ON DELETE CASCADE
- Performance: Simple writes, minimal query overhead
"""

import logging
from dataclasses import dataclass

from sqlmodel import Session, func, select

from app.models.proactivity_analytics import (
    InteractiveQuestionAnswer,
    SuggestedActionClick,
)
from app.schemas.proactivity import Action

logger = logging.getLogger(__name__)


@dataclass
class ActionStats:
    """Statistics for a suggested action.

    Attributes:
        action_template_id: ID of the action template
        action_label: Display label of the action
        click_count: Number of clicks on this action
    """

    action_template_id: str
    action_label: str
    click_count: int


class ProactivityAnalyticsService:
    """Service for tracking proactivity analytics.

    This service provides non-blocking analytics tracking for:
    - Suggested action clicks
    - Interactive question answers
    - Action popularity statistics

    Attributes:
        session: SQLModel database session
    """

    def __init__(self, session: Session):
        """Initialize the service with a database session.

        Args:
            session: SQLModel database session for persistence
        """
        self.session = session

    def track_action_click(
        self,
        session_id: str,
        user_id: int | None,
        action: Action,
        domain: str,
        context_hash: str | None = None,
    ) -> None:
        """Track when a user clicks a suggested action.

        Creates a SuggestedActionClick record. DB failures are logged
        but don't raise exceptions to avoid disrupting the user flow.

        Args:
            session_id: Session identifier
            user_id: User ID (None for anonymous users)
            action: The clicked Action object
            domain: Domain context (tax, labor, legal, etc.)
            context_hash: Optional hash for grouping similar contexts
        """
        try:
            click = SuggestedActionClick(
                session_id=session_id,
                user_id=user_id,
                action_template_id=action.id,
                action_label=action.label,
                domain=domain,
                context_hash=context_hash,
            )
            self.session.add(click)
            self.session.commit()

            logger.debug(
                "action_click_tracked",
                extra={
                    "session_id": session_id,
                    "action_id": action.id,
                    "domain": domain,
                },
            )

        except Exception as e:
            logger.warning(
                "action_click_tracking_failed",
                extra={
                    "session_id": session_id,
                    "action_id": action.id,
                    "error": str(e),
                },
            )
            self.session.rollback()

    def track_question_answer(
        self,
        session_id: str,
        user_id: int | None,
        question_id: str,
        option_id: str,
        custom_input: str | None = None,
    ) -> None:
        """Track when a user answers an interactive question.

        Creates an InteractiveQuestionAnswer record. DB failures are logged
        but don't raise exceptions to avoid disrupting the user flow.

        Args:
            session_id: Session identifier
            user_id: User ID (None for anonymous users)
            question_id: ID of the answered question
            option_id: ID of the selected option
            custom_input: Custom text if "altro" was selected
        """
        try:
            answer = InteractiveQuestionAnswer(
                session_id=session_id,
                user_id=user_id,
                question_id=question_id,
                selected_option=option_id,
                custom_input=custom_input,
            )
            self.session.add(answer)
            self.session.commit()

            logger.debug(
                "question_answer_tracked",
                extra={
                    "session_id": session_id,
                    "question_id": question_id,
                    "option_id": option_id,
                },
            )

        except Exception as e:
            logger.warning(
                "question_answer_tracking_failed",
                extra={
                    "session_id": session_id,
                    "question_id": question_id,
                    "error": str(e),
                },
            )
            self.session.rollback()

    def get_popular_actions(
        self,
        domain: str,
        limit: int = 10,
    ) -> list[ActionStats]:
        """Get the most popular actions for a domain.

        Queries the database for action click counts grouped by
        action_template_id, ordered by click count descending.

        Args:
            domain: Domain to filter by
            limit: Maximum number of results to return

        Returns:
            List of ActionStats ordered by popularity
        """
        statement = (
            select(
                SuggestedActionClick.action_template_id,
                SuggestedActionClick.action_label,
                func.count(SuggestedActionClick.id).label("click_count"),
            )
            .where(SuggestedActionClick.domain == domain)
            .group_by(
                SuggestedActionClick.action_template_id,
                SuggestedActionClick.action_label,
            )
            .order_by(func.count(SuggestedActionClick.id).desc())
            .limit(limit)
        )

        results = self.session.exec(statement).all()

        return [
            ActionStats(
                action_template_id=row[0],
                action_label=row[1],
                click_count=row[2],
            )
            for row in results
        ]
