"""DEV-438: Tests for DeadlineReminder SQLModel."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.models.deadline_reminder import DeadlineReminder


class TestDeadlineReminderModel:
    """Test DeadlineReminder model creation and defaults."""

    def test_create_valid_reminder(self) -> None:
        """Happy path: create reminder with all required fields."""
        deadline_id = uuid4()
        studio_id = uuid4()
        remind_at = datetime(2026, 6, 15, 9, 0, 0, tzinfo=UTC)

        reminder = DeadlineReminder(
            deadline_id=deadline_id,
            user_id=1,
            studio_id=studio_id,
            remind_at=remind_at,
        )

        assert reminder.deadline_id == deadline_id
        assert reminder.user_id == 1
        assert reminder.studio_id == studio_id
        assert reminder.remind_at == remind_at

    def test_default_active_and_not_sent(self) -> None:
        """Default: is_active=True, notification_sent=False."""
        reminder = DeadlineReminder(
            deadline_id=uuid4(),
            user_id=1,
            studio_id=uuid4(),
            remind_at=datetime(2026, 6, 15, 9, 0, 0, tzinfo=UTC),
        )

        assert reminder.is_active is True
        assert reminder.notification_sent is False

    def test_uuid_auto_generated(self) -> None:
        """ID is auto-generated UUID."""
        reminder = DeadlineReminder(
            deadline_id=uuid4(),
            user_id=1,
            studio_id=uuid4(),
            remind_at=datetime(2026, 6, 15, 9, 0, 0, tzinfo=UTC),
        )

        assert reminder.id is not None

    def test_uuid_uniqueness(self) -> None:
        """Two reminders get different UUIDs."""
        r1 = DeadlineReminder(
            deadline_id=uuid4(),
            user_id=1,
            studio_id=uuid4(),
            remind_at=datetime(2026, 6, 15, 9, 0, 0, tzinfo=UTC),
        )
        r2 = DeadlineReminder(
            deadline_id=uuid4(),
            user_id=2,
            studio_id=uuid4(),
            remind_at=datetime(2026, 7, 15, 9, 0, 0, tzinfo=UTC),
        )

        assert r1.id != r2.id

    def test_fields_correct(self) -> None:
        """All fields are assigned correctly including overrides."""
        deadline_id = uuid4()
        studio_id = uuid4()
        remind_at = datetime(2026, 12, 31, 23, 59, 0, tzinfo=UTC)

        reminder = DeadlineReminder(
            deadline_id=deadline_id,
            user_id=42,
            studio_id=studio_id,
            remind_at=remind_at,
            is_active=False,
            notification_sent=True,
        )

        assert reminder.deadline_id == deadline_id
        assert reminder.user_id == 42
        assert reminder.studio_id == studio_id
        assert reminder.remind_at == remind_at
        assert reminder.is_active is False
        assert reminder.notification_sent is True

    def test_repr(self) -> None:
        """__repr__ includes deadline_id and user_id."""
        deadline_id = uuid4()
        reminder = DeadlineReminder(
            deadline_id=deadline_id,
            user_id=7,
            studio_id=uuid4(),
            remind_at=datetime(2026, 6, 15, 9, 0, 0, tzinfo=UTC),
        )

        repr_str = repr(reminder)
        assert str(deadline_id) in repr_str
        assert "7" in repr_str

    def test_updated_at_default_none(self) -> None:
        """updated_at defaults to None."""
        reminder = DeadlineReminder(
            deadline_id=uuid4(),
            user_id=1,
            studio_id=uuid4(),
            remind_at=datetime(2026, 6, 15, 9, 0, 0, tzinfo=UTC),
        )

        assert reminder.updated_at is None
