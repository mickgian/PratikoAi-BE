"""DEV-438: Tests for Deadline Reminder API endpoints.

TDD: Tests written FIRST before implementation.
Tests all deadline reminder endpoints with mocked services.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.deadline_reminder import DeadlineReminder


@pytest.fixture
def sample_deadline_id():
    """Sample deadline UUID."""
    return uuid4()


@pytest.fixture
def sample_studio_id():
    """Sample studio UUID."""
    return uuid4()


@pytest.fixture
def sample_reminder(sample_deadline_id, sample_studio_id):
    """Sample DeadlineReminder instance."""
    return DeadlineReminder(
        deadline_id=sample_deadline_id,
        user_id=1,
        studio_id=sample_studio_id,
        remind_at=datetime(2026, 6, 15, 9, 0, 0, tzinfo=UTC),
        is_active=True,
        notification_sent=False,
    )


class TestSetReminder:
    """Tests for POST /deadlines/{deadline_id}/reminder."""

    @pytest.mark.asyncio
    async def test_create_reminder_success(self, sample_deadline_id, sample_studio_id, sample_reminder):
        """Should create a reminder and return 201."""
        from app.api.v1.deadline_reminders import ReminderRequest, set_reminder

        mock_svc = AsyncMock()
        mock_svc.set_reminder.return_value = sample_reminder
        mock_db = AsyncMock()

        body = ReminderRequest(remind_at=datetime(2026, 6, 15, 9, 0, 0, tzinfo=UTC))

        with patch("app.api.v1.deadline_reminders.deadline_reminder_service", mock_svc):
            result = await set_reminder(
                deadline_id=sample_deadline_id,
                body=body,
                x_user_id=1,
                x_studio_id=sample_studio_id,
                db=mock_db,
            )

        assert result.deadline_id == sample_deadline_id
        assert result.user_id == 1
        assert result.is_active is True
        assert result.notification_sent is False
        mock_svc.set_reminder.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_reminder_past_date_rejected(self, sample_deadline_id, sample_studio_id):
        """Should return 400 when remind_at is in the past."""
        from app.api.v1.deadline_reminders import ReminderRequest, set_reminder

        mock_svc = AsyncMock()
        mock_svc.set_reminder.side_effect = ValueError("La data del promemoria deve essere nel futuro.")
        mock_db = AsyncMock()

        body = ReminderRequest(remind_at=datetime(2020, 1, 1, 0, 0, 0, tzinfo=UTC))

        with (
            patch("app.api.v1.deadline_reminders.deadline_reminder_service", mock_svc),
            pytest.raises(HTTPException) as exc_info,
        ):
            await set_reminder(
                deadline_id=sample_deadline_id,
                body=body,
                x_user_id=1,
                x_studio_id=sample_studio_id,
                db=mock_db,
            )

        assert exc_info.value.status_code == 400
        assert "futuro" in str(exc_info.value.detail)


class TestDeleteReminder:
    """Tests for DELETE /deadlines/{deadline_id}/reminder."""

    @pytest.mark.asyncio
    async def test_delete_reminder_success(self, sample_deadline_id, sample_studio_id):
        """Should delete reminder and return 204 (None)."""
        from app.api.v1.deadline_reminders import delete_reminder

        mock_svc = AsyncMock()
        mock_svc.delete_reminder.return_value = True
        mock_db = AsyncMock()

        with patch("app.api.v1.deadline_reminders.deadline_reminder_service", mock_svc):
            result = await delete_reminder(
                deadline_id=sample_deadline_id,
                x_user_id=1,
                x_studio_id=sample_studio_id,
                db=mock_db,
            )

        assert result is None
        mock_svc.delete_reminder.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_reminder_not_found(self, sample_deadline_id, sample_studio_id):
        """Should return 404 when reminder does not exist."""
        from app.api.v1.deadline_reminders import delete_reminder

        mock_svc = AsyncMock()
        mock_svc.delete_reminder.return_value = False
        mock_db = AsyncMock()

        with (
            patch("app.api.v1.deadline_reminders.deadline_reminder_service", mock_svc),
            pytest.raises(HTTPException) as exc_info,
        ):
            await delete_reminder(
                deadline_id=sample_deadline_id,
                x_user_id=1,
                x_studio_id=sample_studio_id,
                db=mock_db,
            )

        assert exc_info.value.status_code == 404


class TestGetReminder:
    """Tests for GET /deadlines/{deadline_id}/reminder."""

    @pytest.mark.asyncio
    async def test_get_reminder_success(self, sample_deadline_id, sample_studio_id, sample_reminder):
        """Should return the reminder when it exists."""
        from app.api.v1.deadline_reminders import get_reminder

        mock_svc = AsyncMock()
        mock_svc.get_reminder.return_value = sample_reminder
        mock_db = AsyncMock()

        with patch("app.api.v1.deadline_reminders.deadline_reminder_service", mock_svc):
            result = await get_reminder(
                deadline_id=sample_deadline_id,
                x_user_id=1,
                x_studio_id=sample_studio_id,
                db=mock_db,
            )

        assert result.deadline_id == sample_deadline_id
        assert result.user_id == 1
        assert result.is_active is True
        mock_svc.get_reminder.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_reminder_not_found(self, sample_deadline_id, sample_studio_id):
        """Should return 404 when reminder does not exist."""
        from app.api.v1.deadline_reminders import get_reminder

        mock_svc = AsyncMock()
        mock_svc.get_reminder.return_value = None
        mock_db = AsyncMock()

        with (
            patch("app.api.v1.deadline_reminders.deadline_reminder_service", mock_svc),
            pytest.raises(HTTPException) as exc_info,
        ):
            await get_reminder(
                deadline_id=sample_deadline_id,
                x_user_id=1,
                x_studio_id=sample_studio_id,
                db=mock_db,
            )

        assert exc_info.value.status_code == 404
        assert "non trovato" in str(exc_info.value.detail)
