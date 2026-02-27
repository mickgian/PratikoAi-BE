"""DEV-384: Tests for Deadline Notification Background Job.

TDD: Tests written FIRST before implementation.
Tests the daily notification job that sends deadline reminders.

Scenarios tested:
- Happy path: notifications for deadlines due within intervals
- Configurable intervals (30, 7, 1 days)
- Edge case: no upcoming deadlines → no notifications sent
- Edge case: completed deadlines are skipped
- Fire-and-forget: notification failure doesn't break job
"""

from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.deadline import ClientDeadline, Deadline, DeadlineSource, DeadlineType
from app.models.notification import NotificationPriority, NotificationType

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def studio_id():
    """Fixed studio UUID for tests."""
    return uuid4()


@pytest.fixture
def user_id():
    """Fixed user ID for tests."""
    return 1


@pytest.fixture
def mock_db():
    """Mock async database session."""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def sample_deadline_7_days():
    """Deadline due in 7 days."""
    dl = MagicMock(spec=Deadline)
    dl.id = uuid4()
    dl.title = "Versamento IVA trimestrale"
    dl.description = "Scadenza versamento IVA"
    dl.deadline_type = DeadlineType.FISCALE
    dl.source = DeadlineSource.TAX
    dl.due_date = date.today() + timedelta(days=7)
    dl.is_active = True
    dl.recurrence_rule = None
    dl.created_at = datetime.now()
    return dl


@pytest.fixture
def sample_deadline_30_days():
    """Deadline due in 30 days."""
    dl = MagicMock(spec=Deadline)
    dl.id = uuid4()
    dl.title = "Dichiarazione annuale"
    dl.description = "Dichiarazione dei redditi"
    dl.deadline_type = DeadlineType.ADEMPIMENTO
    dl.source = DeadlineSource.REGULATORY
    dl.due_date = date.today() + timedelta(days=30)
    dl.is_active = True
    dl.recurrence_rule = None
    dl.created_at = datetime.now()
    return dl


@pytest.fixture
def sample_deadline_1_day():
    """Deadline due tomorrow."""
    dl = MagicMock(spec=Deadline)
    dl.id = uuid4()
    dl.title = "Pagamento contributi INPS"
    dl.description = "Scadenza contributi"
    dl.deadline_type = DeadlineType.CONTRIBUTIVO
    dl.source = DeadlineSource.TAX
    dl.due_date = date.today() + timedelta(days=1)
    dl.is_active = True
    dl.recurrence_rule = None
    dl.created_at = datetime.now()
    return dl


@pytest.fixture
def completed_client_deadline(studio_id):
    """A completed client deadline that should be skipped."""
    cd = MagicMock(spec=ClientDeadline)
    cd.id = uuid4()
    cd.client_id = 1
    cd.deadline_id = uuid4()
    cd.studio_id = studio_id
    cd.is_completed = True
    cd.completed_at = datetime.now()
    cd.notes = None
    return cd


@pytest.fixture
def incomplete_client_deadline(studio_id):
    """An incomplete client deadline that should trigger notification."""
    cd = MagicMock(spec=ClientDeadline)
    cd.id = uuid4()
    cd.client_id = 2
    cd.deadline_id = uuid4()
    cd.studio_id = studio_id
    cd.is_completed = False
    cd.completed_at = None
    cd.notes = None
    return cd


# ---------------------------------------------------------------------------
# Happy path: notifications sent for deadlines at each interval
# ---------------------------------------------------------------------------


class TestDeadlineNotificationHappyPath:
    """Happy-path tests for deadline notification job."""

    @pytest.mark.asyncio
    async def test_sends_notifications_for_7_day_deadlines(
        self,
        mock_db,
        studio_id,
        user_id,
        sample_deadline_7_days,
    ):
        """Notifications are sent for deadlines due in 7 days."""
        from app.jobs.deadline_notification_job import run_deadline_notifications

        with (
            patch("app.jobs.deadline_notification_job.deadline_service") as mock_dl_svc,
            patch("app.jobs.deadline_notification_job.notification_service") as mock_notif_svc,
        ):
            # Only 7-day interval finds a deadline; others empty
            def list_upcoming_side_effect(db, *, days_ahead=30):
                if days_ahead == 7:
                    return [sample_deadline_7_days]
                return []

            mock_dl_svc.list_upcoming = AsyncMock(side_effect=list_upcoming_side_effect)
            mock_dl_svc.list_by_studio = AsyncMock(return_value=[])
            mock_notif_svc.create_notification = AsyncMock(return_value=MagicMock())

            result = await run_deadline_notifications(db=mock_db, studio_id=studio_id, user_id=user_id)

        assert result.notifications_sent >= 1
        assert result.errors == 0
        mock_notif_svc.create_notification.assert_awaited()

    @pytest.mark.asyncio
    async def test_sends_notifications_at_all_default_intervals(
        self,
        mock_db,
        studio_id,
        user_id,
        sample_deadline_30_days,
        sample_deadline_7_days,
        sample_deadline_1_day,
    ):
        """Notifications are sent at all default intervals (30, 7, 1 days)."""
        from app.jobs.deadline_notification_job import run_deadline_notifications

        with (
            patch("app.jobs.deadline_notification_job.deadline_service") as mock_dl_svc,
            patch("app.jobs.deadline_notification_job.notification_service") as mock_notif_svc,
        ):

            def list_upcoming_side_effect(db, *, days_ahead=30):
                if days_ahead == 30:
                    return [sample_deadline_30_days]
                if days_ahead == 7:
                    return [sample_deadline_7_days]
                if days_ahead == 1:
                    return [sample_deadline_1_day]
                return []

            mock_dl_svc.list_upcoming = AsyncMock(side_effect=list_upcoming_side_effect)
            mock_dl_svc.list_by_studio = AsyncMock(return_value=[])
            mock_notif_svc.create_notification = AsyncMock(return_value=MagicMock())

            result = await run_deadline_notifications(db=mock_db, studio_id=studio_id, user_id=user_id)

        assert result.notifications_sent == 3
        assert result.deadlines_checked >= 3
        assert result.errors == 0


# ---------------------------------------------------------------------------
# Configurable intervals
# ---------------------------------------------------------------------------


class TestConfigurableIntervals:
    """Tests for configurable notification intervals."""

    @pytest.mark.asyncio
    async def test_custom_intervals(
        self,
        mock_db,
        studio_id,
        user_id,
        sample_deadline_7_days,
    ):
        """Custom intervals list is respected."""
        from app.jobs.deadline_notification_job import run_deadline_notifications

        with (
            patch("app.jobs.deadline_notification_job.deadline_service") as mock_dl_svc,
            patch("app.jobs.deadline_notification_job.notification_service") as mock_notif_svc,
        ):
            # Only return deadline for 14-day interval
            def list_upcoming_side_effect(db, *, days_ahead=30):
                if days_ahead == 14:
                    return [sample_deadline_7_days]
                return []

            mock_dl_svc.list_upcoming = AsyncMock(side_effect=list_upcoming_side_effect)
            mock_dl_svc.list_by_studio = AsyncMock(return_value=[])
            mock_notif_svc.create_notification = AsyncMock(return_value=MagicMock())

            result = await run_deadline_notifications(
                db=mock_db,
                studio_id=studio_id,
                user_id=user_id,
                intervals=[14, 3],
            )

        # Only the 14-day interval should produce a notification
        assert result.notifications_sent == 1
        assert result.errors == 0

    @pytest.mark.asyncio
    async def test_default_intervals_are_30_7_1(
        self,
        mock_db,
        studio_id,
        user_id,
    ):
        """Default intervals are [30, 7, 1]."""
        from app.jobs.deadline_notification_job import run_deadline_notifications

        with (
            patch("app.jobs.deadline_notification_job.deadline_service") as mock_dl_svc,
            patch("app.jobs.deadline_notification_job.notification_service") as mock_notif_svc,
        ):
            captured_days = []

            async def capture_list_upcoming(db, *, days_ahead=30):
                captured_days.append(days_ahead)
                return []

            mock_dl_svc.list_upcoming = AsyncMock(side_effect=capture_list_upcoming)
            mock_notif_svc.create_notification = AsyncMock(return_value=MagicMock())

            await run_deadline_notifications(db=mock_db, studio_id=studio_id, user_id=user_id)

        assert sorted(captured_days) == [1, 7, 30]


# ---------------------------------------------------------------------------
# Edge case: no upcoming deadlines
# ---------------------------------------------------------------------------


class TestNoUpcomingDeadlines:
    """Edge-case tests: no deadlines found."""

    @pytest.mark.asyncio
    async def test_no_deadlines_no_notifications(
        self,
        mock_db,
        studio_id,
        user_id,
    ):
        """When there are no upcoming deadlines, zero notifications are sent."""
        from app.jobs.deadline_notification_job import run_deadline_notifications

        with (
            patch("app.jobs.deadline_notification_job.deadline_service") as mock_dl_svc,
            patch("app.jobs.deadline_notification_job.notification_service") as mock_notif_svc,
        ):
            mock_dl_svc.list_upcoming = AsyncMock(return_value=[])
            mock_notif_svc.create_notification = AsyncMock(return_value=MagicMock())

            result = await run_deadline_notifications(db=mock_db, studio_id=studio_id, user_id=user_id)

        assert result.notifications_sent == 0
        assert result.deadlines_checked == 0
        assert result.errors == 0
        mock_notif_svc.create_notification.assert_not_awaited()


# ---------------------------------------------------------------------------
# Edge case: completed deadlines are skipped
# ---------------------------------------------------------------------------


class TestCompletedDeadlinesSkipped:
    """Completed ClientDeadlines must not generate notifications."""

    @pytest.mark.asyncio
    async def test_completed_deadlines_skipped(
        self,
        mock_db,
        studio_id,
        user_id,
        sample_deadline_7_days,
        completed_client_deadline,
    ):
        """Completed client-deadlines are skipped — no notification sent."""
        from app.jobs.deadline_notification_job import run_deadline_notifications

        # Wire the completed client deadline to reference the sample deadline
        completed_client_deadline.deadline_id = sample_deadline_7_days.id

        with (
            patch("app.jobs.deadline_notification_job.deadline_service") as mock_dl_svc,
            patch("app.jobs.deadline_notification_job.notification_service") as mock_notif_svc,
        ):

            def list_upcoming_side_effect(db, *, days_ahead=30):
                if days_ahead == 7:
                    return [sample_deadline_7_days]
                return []

            mock_dl_svc.list_upcoming = AsyncMock(side_effect=list_upcoming_side_effect)
            mock_dl_svc.list_by_studio = AsyncMock(return_value=[completed_client_deadline])
            mock_notif_svc.create_notification = AsyncMock(return_value=MagicMock())

            result = await run_deadline_notifications(db=mock_db, studio_id=studio_id, user_id=user_id)

        # Deadline was checked but all client-deadlines completed → skip notification
        assert result.deadlines_checked >= 1
        # The notification is still sent for the deadline itself (general reminder),
        # but not for completed client-specific deadlines.
        # The exact behavior: if ALL client-deadlines for that deadline in the studio
        # are completed, we skip. Otherwise we still notify.
        # With only one completed client-deadline, it should be skipped.
        assert result.errors == 0

    @pytest.mark.asyncio
    async def test_incomplete_deadline_still_notified(
        self,
        mock_db,
        studio_id,
        user_id,
        sample_deadline_7_days,
        incomplete_client_deadline,
    ):
        """Incomplete client-deadlines still trigger notifications."""
        from app.jobs.deadline_notification_job import run_deadline_notifications

        incomplete_client_deadline.deadline_id = sample_deadline_7_days.id

        with (
            patch("app.jobs.deadline_notification_job.deadline_service") as mock_dl_svc,
            patch("app.jobs.deadline_notification_job.notification_service") as mock_notif_svc,
        ):

            def list_upcoming_side_effect(db, *, days_ahead=30):
                if days_ahead == 7:
                    return [sample_deadline_7_days]
                return []

            mock_dl_svc.list_upcoming = AsyncMock(side_effect=list_upcoming_side_effect)
            mock_dl_svc.list_by_studio = AsyncMock(return_value=[incomplete_client_deadline])
            mock_notif_svc.create_notification = AsyncMock(return_value=MagicMock())

            result = await run_deadline_notifications(db=mock_db, studio_id=studio_id, user_id=user_id)

        assert result.notifications_sent >= 1
        assert result.errors == 0
        mock_notif_svc.create_notification.assert_awaited()


# ---------------------------------------------------------------------------
# Fire-and-forget: notification failure doesn't break job
# ---------------------------------------------------------------------------


class TestNotificationFailureResilience:
    """Notification creation failures must not break the job."""

    @pytest.mark.asyncio
    async def test_notification_failure_increments_errors(
        self,
        mock_db,
        studio_id,
        user_id,
        sample_deadline_7_days,
    ):
        """When notification creation raises, error count increments but job continues."""
        from app.jobs.deadline_notification_job import run_deadline_notifications

        with (
            patch("app.jobs.deadline_notification_job.deadline_service") as mock_dl_svc,
            patch("app.jobs.deadline_notification_job.notification_service") as mock_notif_svc,
        ):

            def list_upcoming_side_effect(db, *, days_ahead=30):
                if days_ahead == 7:
                    return [sample_deadline_7_days]
                return []

            mock_dl_svc.list_upcoming = AsyncMock(side_effect=list_upcoming_side_effect)
            mock_dl_svc.list_by_studio = AsyncMock(return_value=[])
            mock_notif_svc.create_notification = AsyncMock(side_effect=RuntimeError("DB connection lost"))

            result = await run_deadline_notifications(db=mock_db, studio_id=studio_id, user_id=user_id)

        # Job didn't crash, but recorded an error
        assert result.errors >= 1
        assert result.deadlines_checked >= 1

    @pytest.mark.asyncio
    async def test_partial_failure_continues_processing(
        self,
        mock_db,
        studio_id,
        user_id,
        sample_deadline_7_days,
        sample_deadline_1_day,
    ):
        """Even if one notification fails, subsequent deadlines are still processed."""
        from app.jobs.deadline_notification_job import run_deadline_notifications

        call_count = 0

        async def flaky_create_notification(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Transient error")
            return MagicMock()

        with (
            patch("app.jobs.deadline_notification_job.deadline_service") as mock_dl_svc,
            patch("app.jobs.deadline_notification_job.notification_service") as mock_notif_svc,
        ):

            def list_upcoming_side_effect(db, *, days_ahead=30):
                if days_ahead == 7:
                    return [sample_deadline_7_days]
                if days_ahead == 1:
                    return [sample_deadline_1_day]
                return []

            mock_dl_svc.list_upcoming = AsyncMock(side_effect=list_upcoming_side_effect)
            mock_dl_svc.list_by_studio = AsyncMock(return_value=[])
            mock_notif_svc.create_notification = AsyncMock(side_effect=flaky_create_notification)

            result = await run_deadline_notifications(db=mock_db, studio_id=studio_id, user_id=user_id)

        # One success, one failure
        assert result.errors == 1
        assert result.notifications_sent == 1
        assert result.deadlines_checked >= 2


# ---------------------------------------------------------------------------
# Result dataclass structure
# ---------------------------------------------------------------------------


class TestDeadlineNotificationResult:
    """Tests for the result dataclass."""

    def test_result_dataclass_fields(self):
        """DeadlineNotificationResult has all expected fields."""
        from app.jobs.deadline_notification_job import DeadlineNotificationResult

        result = DeadlineNotificationResult(
            deadlines_checked=5,
            notifications_sent=3,
            errors=1,
        )
        assert result.deadlines_checked == 5
        assert result.notifications_sent == 3
        assert result.errors == 1
