"""DEV-433: Tests for ChatFeedback SQLModel.

Covers: valid creation, feedback type enum, nullable user/studio,
categories, default score, UUID auto-generated.
"""

from uuid import UUID, uuid4

import pytest

from app.models.chat_feedback import ChatFeedback, FeedbackType


class TestChatFeedbackModel:
    """Test ChatFeedback model creation and defaults."""

    def test_create_valid_feedback(self) -> None:
        """Happy path: create feedback with all required fields."""
        studio_id = uuid4()
        fb = ChatFeedback(
            user_id=1,
            studio_id=studio_id,
            trace_id="trace-abc-123",
            message_id="msg-def-456",
            feedback_type=FeedbackType.CORRECT,
            category="accuracy",
            comment="La risposta era perfetta.",
            score=1,
        )
        assert fb.user_id == 1
        assert fb.studio_id == studio_id
        assert fb.trace_id == "trace-abc-123"
        assert fb.message_id == "msg-def-456"
        assert fb.feedback_type == FeedbackType.CORRECT
        assert fb.category == "accuracy"
        assert fb.comment == "La risposta era perfetta."
        assert fb.score == 1

    def test_feedback_type_enum_correct(self) -> None:
        """FeedbackType.CORRECT has value 'correct'."""
        assert FeedbackType.CORRECT == "correct"
        assert FeedbackType.CORRECT.value == "correct"

    def test_feedback_type_enum_incomplete(self) -> None:
        """FeedbackType.INCOMPLETE has value 'incomplete'."""
        assert FeedbackType.INCOMPLETE == "incomplete"
        assert FeedbackType.INCOMPLETE.value == "incomplete"

    def test_feedback_type_enum_incorrect(self) -> None:
        """FeedbackType.INCORRECT has value 'incorrect'."""
        assert FeedbackType.INCORRECT == "incorrect"
        assert FeedbackType.INCORRECT.value == "incorrect"

    def test_all_feedback_types(self) -> None:
        """All 3 feedback types are valid and can be used in model creation."""
        types = [FeedbackType.CORRECT, FeedbackType.INCOMPLETE, FeedbackType.INCORRECT]
        assert len(types) == 3
        for ft in types:
            fb = ChatFeedback(
                trace_id="trace-1",
                message_id="msg-1",
                feedback_type=ft,
            )
            assert fb.feedback_type == ft

    def test_nullable_user_id(self) -> None:
        """user_id defaults to None (anonymous feedback)."""
        fb = ChatFeedback(
            trace_id="trace-anon",
            message_id="msg-anon",
            feedback_type=FeedbackType.CORRECT,
        )
        assert fb.user_id is None

    def test_nullable_studio_id(self) -> None:
        """studio_id defaults to None."""
        fb = ChatFeedback(
            trace_id="trace-no-studio",
            message_id="msg-no-studio",
            feedback_type=FeedbackType.INCOMPLETE,
        )
        assert fb.studio_id is None

    def test_nullable_user_and_studio(self) -> None:
        """Both user_id and studio_id can be None simultaneously."""
        fb = ChatFeedback(
            trace_id="trace-both-null",
            message_id="msg-both-null",
            feedback_type=FeedbackType.INCORRECT,
        )
        assert fb.user_id is None
        assert fb.studio_id is None

    def test_explicit_user_and_studio(self) -> None:
        """user_id and studio_id can be set explicitly."""
        sid = uuid4()
        fb = ChatFeedback(
            user_id=42,
            studio_id=sid,
            trace_id="trace-explicit",
            message_id="msg-explicit",
            feedback_type=FeedbackType.CORRECT,
        )
        assert fb.user_id == 42
        assert fb.studio_id == sid

    def test_nullable_category(self) -> None:
        """category defaults to None."""
        fb = ChatFeedback(
            trace_id="trace-cat",
            message_id="msg-cat",
            feedback_type=FeedbackType.CORRECT,
        )
        assert fb.category is None

    def test_category_set(self) -> None:
        """category can be set to a string value."""
        fb = ChatFeedback(
            trace_id="trace-cat-set",
            message_id="msg-cat-set",
            feedback_type=FeedbackType.CORRECT,
            category="normativa",
        )
        assert fb.category == "normativa"

    def test_nullable_comment(self) -> None:
        """comment defaults to None."""
        fb = ChatFeedback(
            trace_id="trace-comm",
            message_id="msg-comm",
            feedback_type=FeedbackType.INCOMPLETE,
        )
        assert fb.comment is None

    def test_comment_set(self) -> None:
        """comment can hold free-text."""
        fb = ChatFeedback(
            trace_id="trace-comm-set",
            message_id="msg-comm-set",
            feedback_type=FeedbackType.INCORRECT,
            comment="Manca il riferimento normativo.",
        )
        assert fb.comment == "Manca il riferimento normativo."

    def test_default_score(self) -> None:
        """score defaults to 0."""
        fb = ChatFeedback(
            trace_id="trace-score",
            message_id="msg-score",
            feedback_type=FeedbackType.CORRECT,
        )
        assert fb.score == 0

    def test_score_explicit(self) -> None:
        """score can be set explicitly."""
        fb = ChatFeedback(
            trace_id="trace-score-1",
            message_id="msg-score-1",
            feedback_type=FeedbackType.CORRECT,
            score=1,
        )
        assert fb.score == 1

    def test_uuid_auto_generated(self) -> None:
        """ID is auto-generated UUID."""
        fb = ChatFeedback(
            trace_id="trace-uuid",
            message_id="msg-uuid",
            feedback_type=FeedbackType.CORRECT,
        )
        assert fb.id is not None
        assert isinstance(fb.id, UUID)

    def test_uuid_unique_per_instance(self) -> None:
        """Each instance gets a unique UUID."""
        fb1 = ChatFeedback(
            trace_id="trace-u1",
            message_id="msg-u1",
            feedback_type=FeedbackType.CORRECT,
        )
        fb2 = ChatFeedback(
            trace_id="trace-u2",
            message_id="msg-u2",
            feedback_type=FeedbackType.INCORRECT,
        )
        assert fb1.id != fb2.id

    def test_repr(self) -> None:
        """__repr__ includes trace_id and feedback_type."""
        fb = ChatFeedback(
            trace_id="trace-repr",
            message_id="msg-repr",
            feedback_type=FeedbackType.INCOMPLETE,
        )
        r = repr(fb)
        assert "trace-repr" in r
        assert "incomplete" in r

    def test_tablename(self) -> None:
        """Table name is 'chat_feedback'."""
        assert ChatFeedback.__tablename__ == "chat_feedback"
