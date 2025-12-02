"""Test query_text field validation in FeedbackSubmission schema.

Tests ensure that placeholder strings are rejected to prevent frontend bugs
from propagating to the database.
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.expert_feedback import FeedbackSubmission


class TestQueryTextValidation:
    """Test query_text field validation in FeedbackSubmission schema."""

    def test_valid_query_text(self):
        """Valid query text should be accepted."""
        data = {
            "query_id": uuid4(),
            "feedback_type": "correct",
            "query_text": "Come si calcola l'IVA per il regime forfettario?",
            "original_answer": "Nel regime forfettario...",
            "confidence_score": 0.9,
            "time_spent_seconds": 120,
        }

        feedback = FeedbackSubmission(**data)
        assert feedback.query_text == data["query_text"]

    def test_reject_italian_placeholder(self):
        """Italian placeholder should be rejected."""
        data = {
            "query_id": uuid4(),
            "feedback_type": "correct",
            "query_text": "[Domanda precedente dell'utente]",
            "original_answer": "Some answer",
            "confidence_score": 0.9,
            "time_spent_seconds": 120,
        }

        with pytest.raises(ValidationError) as exc_info:
            FeedbackSubmission(**data)

        error = exc_info.value.errors()[0]
        assert error["loc"] == ("query_text",)
        assert "placeholder" in error["msg"].lower()

    def test_reject_english_placeholder(self):
        """English placeholder should be rejected."""
        data = {
            "query_id": uuid4(),
            "feedback_type": "correct",
            "query_text": "[User query]",
            "original_answer": "Some answer",
            "confidence_score": 0.9,
            "time_spent_seconds": 120,
        }

        with pytest.raises(ValidationError) as exc_info:
            FeedbackSubmission(**data)

        error = exc_info.value.errors()[0]
        assert error["loc"] == ("query_text",)

    def test_reject_todo_placeholder(self):
        """TODO placeholder should be rejected."""
        data = {
            "query_id": uuid4(),
            "feedback_type": "correct",
            "query_text": "[TODO]",
            "original_answer": "Some answer",
            "confidence_score": 0.9,
            "time_spent_seconds": 120,
        }

        with pytest.raises(ValidationError) as exc_info:
            FeedbackSubmission(**data)

    def test_reject_empty_query_text(self):
        """Empty query text should be rejected."""
        data = {
            "query_id": uuid4(),
            "feedback_type": "correct",
            "query_text": "   ",  # Whitespace only
            "original_answer": "Some answer",
            "confidence_score": 0.9,
            "time_spent_seconds": 120,
        }

        with pytest.raises(ValidationError) as exc_info:
            FeedbackSubmission(**data)

        error = exc_info.value.errors()[0]
        assert "empty" in error["msg"].lower()

    def test_case_insensitive_placeholder_rejection(self):
        """Placeholders should be rejected regardless of case."""
        data = {
            "query_id": uuid4(),
            "feedback_type": "correct",
            "query_text": "[DOMANDA PRECEDENTE DELL'UTENTE]",  # Uppercase
            "original_answer": "Some answer",
            "confidence_score": 0.9,
            "time_spent_seconds": 120,
        }

        with pytest.raises(ValidationError) as exc_info:
            FeedbackSubmission(**data)

    def test_reject_query_text_placeholder(self):
        """Generic [Query text] placeholder should be rejected."""
        data = {
            "query_id": uuid4(),
            "feedback_type": "correct",
            "query_text": "[Query text]",
            "original_answer": "Some answer",
            "confidence_score": 0.9,
            "time_spent_seconds": 120,
        }

        with pytest.raises(ValidationError) as exc_info:
            FeedbackSubmission(**data)

    def test_reject_todo_extract_placeholder(self):
        """TODO extract placeholder should be rejected."""
        data = {
            "query_id": uuid4(),
            "feedback_type": "correct",
            "query_text": "TODO: Extract from chat history",
            "original_answer": "Some answer",
            "confidence_score": 0.9,
            "time_spent_seconds": 120,
        }

        with pytest.raises(ValidationError) as exc_info:
            FeedbackSubmission(**data)
