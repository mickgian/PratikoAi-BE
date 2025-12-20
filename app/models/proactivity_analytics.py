"""Proactivity Analytics Models for PratikoAI v1.5 - DEV-156.

This module defines SQLModel tables for tracking user interactions:
- SuggestedActionClick: Tracks clicks on suggested actions
- InteractiveQuestionAnswer: Tracks answers to interactive questions

These models support:
- Analytics and usage tracking
- Future ML model training
- GDPR compliance with ON DELETE CASCADE
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field

from app.models.base import BaseModel


class SuggestedActionClick(BaseModel, table=True):  # type: ignore[call-arg]
    """Track clicks on suggested actions.

    Records when users click on suggested action buttons to:
    - Analyze popular actions per domain
    - Train future recommendation models
    - Understand user behavior patterns

    Attributes:
        id: Unique UUID for the click event
        session_id: Session identifier for grouping interactions
        user_id: User ID (nullable for anonymous users)
        action_template_id: ID of the clicked action template
        action_label: Display label of the action
        domain: Domain context (tax, labor, legal, etc.)
        clicked_at: Timestamp of the click
        context_hash: Hash for grouping similar contexts
    """

    __tablename__ = "suggested_action_clicks"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    session_id: str = Field(index=True)
    user_id: int | None = Field(
        default=None,
        foreign_key="user.id",
        index=True,
        ondelete="CASCADE",
    )
    action_template_id: str = Field(index=True)
    action_label: str
    domain: str | None = Field(default=None, index=True)
    clicked_at: datetime = Field(default_factory=datetime.utcnow)
    context_hash: str | None = Field(default=None)


class InteractiveQuestionAnswer(BaseModel, table=True):  # type: ignore[call-arg]
    """Track answers to interactive questions.

    Records when users answer interactive clarification questions to:
    - Analyze common user choices
    - Improve question templates
    - Train future classification models

    Attributes:
        id: Unique UUID for the answer event
        session_id: Session identifier for grouping interactions
        user_id: User ID (nullable for anonymous users)
        question_id: ID of the answered question template
        selected_option: ID of the selected option
        custom_input: Custom text input if "altro" was selected
        answered_at: Timestamp of the answer
    """

    __tablename__ = "interactive_question_answers"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    session_id: str = Field(index=True)
    user_id: int | None = Field(
        default=None,
        foreign_key="user.id",
        index=True,
        ondelete="CASCADE",
    )
    question_id: str = Field(index=True)
    selected_option: str
    custom_input: str | None = Field(default=None)
    answered_at: datetime = Field(default_factory=datetime.utcnow)
