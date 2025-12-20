"""TDD Tests for Proactivity Analytics Models - DEV-156.

This module tests the analytics models:
- SuggestedActionClick
- InteractiveQuestionAnswer

Test Files Reference: app/models/proactivity_analytics.py
"""

from datetime import datetime
from uuid import UUID

import pytest

from app.models.proactivity_analytics import (
    InteractiveQuestionAnswer,
    SuggestedActionClick,
)


class TestSuggestedActionClickModel:
    """Test SuggestedActionClick model."""

    def test_create_action_click_with_required_fields(self):
        """Test creating action click with required fields."""
        click = SuggestedActionClick(
            session_id="session-123",
            action_template_id="tax_calculate_irpef",
            action_label="Calcola IRPEF",
        )
        assert click.session_id == "session-123"
        assert click.action_template_id == "tax_calculate_irpef"
        assert click.action_label == "Calcola IRPEF"
        assert click.user_id is None
        assert click.domain is None

    def test_create_action_click_with_all_fields(self):
        """Test creating action click with all fields."""
        click = SuggestedActionClick(
            session_id="session-123",
            user_id=42,
            action_template_id="tax_calculate_irpef",
            action_label="Calcola IRPEF",
            domain="tax",
            context_hash="abc123",
        )
        assert click.user_id == 42
        assert click.domain == "tax"
        assert click.context_hash == "abc123"

    def test_action_click_has_uuid_id(self):
        """Test that action click has UUID id."""
        click = SuggestedActionClick(
            session_id="session-123",
            action_template_id="tax_calculate_irpef",
            action_label="Calcola IRPEF",
        )
        assert click.id is not None
        assert isinstance(click.id, UUID)

    def test_action_click_has_clicked_at_timestamp(self):
        """Test that action click has clicked_at timestamp."""
        click = SuggestedActionClick(
            session_id="session-123",
            action_template_id="tax_calculate_irpef",
            action_label="Calcola IRPEF",
        )
        assert click.clicked_at is not None
        assert isinstance(click.clicked_at, datetime)

    def test_action_click_anonymous_user(self):
        """Test action click for anonymous user (user_id=None)."""
        click = SuggestedActionClick(
            session_id="anonymous-session",
            user_id=None,
            action_template_id="default_search",
            action_label="Cerca",
        )
        assert click.user_id is None
        assert click.session_id == "anonymous-session"


class TestInteractiveQuestionAnswerModel:
    """Test InteractiveQuestionAnswer model."""

    def test_create_question_answer_with_required_fields(self):
        """Test creating question answer with required fields."""
        answer = InteractiveQuestionAnswer(
            session_id="session-123",
            question_id="irpef_tipo_contribuente",
            selected_option="dipendente",
        )
        assert answer.session_id == "session-123"
        assert answer.question_id == "irpef_tipo_contribuente"
        assert answer.selected_option == "dipendente"
        assert answer.user_id is None
        assert answer.custom_input is None

    def test_create_question_answer_with_all_fields(self):
        """Test creating question answer with all fields."""
        answer = InteractiveQuestionAnswer(
            session_id="session-123",
            user_id=42,
            question_id="irpef_tipo_contribuente",
            selected_option="altro",
            custom_input="Libero professionista con P.IVA forfettaria",
        )
        assert answer.user_id == 42
        assert answer.selected_option == "altro"
        assert answer.custom_input == "Libero professionista con P.IVA forfettaria"

    def test_question_answer_has_uuid_id(self):
        """Test that question answer has UUID id."""
        answer = InteractiveQuestionAnswer(
            session_id="session-123",
            question_id="irpef_tipo_contribuente",
            selected_option="dipendente",
        )
        assert answer.id is not None
        assert isinstance(answer.id, UUID)

    def test_question_answer_has_answered_at_timestamp(self):
        """Test that question answer has answered_at timestamp."""
        answer = InteractiveQuestionAnswer(
            session_id="session-123",
            question_id="irpef_tipo_contribuente",
            selected_option="dipendente",
        )
        assert answer.answered_at is not None
        assert isinstance(answer.answered_at, datetime)

    def test_question_answer_anonymous_user(self):
        """Test question answer for anonymous user (user_id=None)."""
        answer = InteractiveQuestionAnswer(
            session_id="anonymous-session",
            user_id=None,
            question_id="document_type",
            selected_option="fattura",
        )
        assert answer.user_id is None
        assert answer.session_id == "anonymous-session"
