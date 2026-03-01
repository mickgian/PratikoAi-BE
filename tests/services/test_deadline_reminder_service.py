"""DEV-438: Tests for DeadlineReminderService — CRUD for per-deadline user reminders.

TDD: Tests for service-layer set_reminder, delete_reminder, get_reminder.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.deadline_reminder import DeadlineReminder
from app.services.deadline_reminder_service import DeadlineReminderService


@pytest.fixture
def svc() -> DeadlineReminderService:
    return DeadlineReminderService()


@pytest.fixture
def studio_id():
    return uuid4()


@pytest.fixture
def deadline_id():
    return uuid4()


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.delete = AsyncMock()
    return db


class TestSetReminder:
    """Tests for DeadlineReminderService.set_reminder."""

    @pytest.mark.asyncio
    async def test_create_new_reminder(self, svc, mock_db, studio_id, deadline_id) -> None:
        """Creates a new reminder when none exists."""
        future = datetime.now(UTC) + timedelta(days=3)

        # No existing reminder
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await svc.set_reminder(
            mock_db,
            deadline_id=deadline_id,
            user_id=1,
            studio_id=studio_id,
            remind_at=future,
        )

        assert isinstance(result, DeadlineReminder)
        assert result.deadline_id == deadline_id
        assert result.user_id == 1
        assert result.studio_id == studio_id
        assert result.remind_at == future
        mock_db.add.assert_called_once()
        mock_db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_existing_reminder(self, svc, mock_db, studio_id, deadline_id) -> None:
        """Updates an existing reminder (upsert)."""
        future = datetime.now(UTC) + timedelta(days=5)
        existing = DeadlineReminder(
            deadline_id=deadline_id,
            user_id=1,
            studio_id=studio_id,
            remind_at=datetime.now(UTC) + timedelta(days=1),
            is_active=False,
            notification_sent=True,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_db.execute.return_value = mock_result

        result = await svc.set_reminder(
            mock_db,
            deadline_id=deadline_id,
            user_id=1,
            studio_id=studio_id,
            remind_at=future,
        )

        assert result is existing
        assert result.remind_at == future
        assert result.is_active is True
        assert result.notification_sent is False
        mock_db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_past_date_rejected(self, svc, mock_db, studio_id, deadline_id) -> None:
        """Rejects remind_at in the past."""
        past = datetime.now(UTC) - timedelta(hours=1)

        with pytest.raises(ValueError, match="futuro"):
            await svc.set_reminder(
                mock_db,
                deadline_id=deadline_id,
                user_id=1,
                studio_id=studio_id,
                remind_at=past,
            )


class TestDeleteReminder:
    """Tests for DeadlineReminderService.delete_reminder."""

    @pytest.mark.asyncio
    async def test_delete_existing_returns_true(self, svc, mock_db, studio_id, deadline_id) -> None:
        """Deletes an existing reminder and returns True."""
        existing = DeadlineReminder(
            deadline_id=deadline_id,
            user_id=1,
            studio_id=studio_id,
            remind_at=datetime.now(UTC) + timedelta(days=1),
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_db.execute.return_value = mock_result

        result = await svc.delete_reminder(
            mock_db,
            deadline_id=deadline_id,
            user_id=1,
            studio_id=studio_id,
        )

        assert result is True
        mock_db.delete.assert_awaited_once_with(existing)
        mock_db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_false(self, svc, mock_db, studio_id, deadline_id) -> None:
        """Returns False when reminder not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await svc.delete_reminder(
            mock_db,
            deadline_id=deadline_id,
            user_id=1,
            studio_id=studio_id,
        )

        assert result is False
        mock_db.delete.assert_not_called()


class TestGetReminder:
    """Tests for DeadlineReminderService.get_reminder."""

    @pytest.mark.asyncio
    async def test_get_existing_reminder(self, svc, mock_db, studio_id, deadline_id) -> None:
        """Returns existing reminder."""
        existing = DeadlineReminder(
            deadline_id=deadline_id,
            user_id=1,
            studio_id=studio_id,
            remind_at=datetime.now(UTC) + timedelta(days=1),
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_db.execute.return_value = mock_result

        result = await svc.get_reminder(
            mock_db,
            deadline_id=deadline_id,
            user_id=1,
            studio_id=studio_id,
        )

        assert result is existing

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(self, svc, mock_db, studio_id, deadline_id) -> None:
        """Returns None when reminder not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await svc.get_reminder(
            mock_db,
            deadline_id=deadline_id,
            user_id=1,
            studio_id=studio_id,
        )

        assert result is None
