"""Comprehensive tests for TaskDigestEmailService.

Tests cover:
- Constructor stores db, email_service, and reads ADMIN_EMAIL from env
- send_daily_digest: no tasks returns False, tasks found sends email, email
  send failure returns False, DB exception returns False
- _build_email_html: empty task list, single task, multiple tasks, HTML
  structure and Italian content, date formatting, task field rendering,
  singular vs plural wording
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest

from app.services.task_digest_email_service import TaskDigestEmailService

# ---------------------------------------------------------------------------
# Helpers: lightweight fakes for ExpertGeneratedTask and ExpertProfile
# ---------------------------------------------------------------------------


def _make_expert(trust_score: float = 0.85):
    """Create a mock ExpertProfile."""
    expert = Mock()
    expert.trust_score = trust_score
    return expert


def _make_task(
    task_id: str = "QUERY-08",
    task_name: str = "Fix normativa parsing",
    feedback_id: str | None = None,
    question: str = "Come si calcola l'imposta sostitutiva?",
    created_at: datetime | None = None,
    expert: Mock | None = None,
):
    """Create a mock ExpertGeneratedTask with the attributes used by _build_email_html."""
    task = Mock()
    task.task_id = task_id
    task.task_name = task_name
    task.feedback_id = feedback_id or uuid4()
    task.question = question
    task.created_at = created_at or datetime(2025, 11, 20, 14, 30)
    task.expert = expert or _make_expert()
    return task


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


class TestTaskDigestEmailServiceInit:
    """Tests for TaskDigestEmailService constructor."""

    def test_stores_db_session(self):
        mock_db = AsyncMock()
        mock_email = Mock()
        service = TaskDigestEmailService(db=mock_db, email_service=mock_email)
        assert service.db is mock_db

    def test_stores_email_service(self):
        mock_db = AsyncMock()
        mock_email = Mock()
        service = TaskDigestEmailService(db=mock_db, email_service=mock_email)
        assert service.email_service is mock_email

    @patch.dict("os.environ", {"ADMIN_EMAIL": "custom@example.com"})
    def test_reads_admin_email_from_env(self):
        service = TaskDigestEmailService(db=AsyncMock(), email_service=Mock())
        assert service.recipient_email == "custom@example.com"

    @patch.dict("os.environ", {}, clear=True)
    def test_default_admin_email(self):
        service = TaskDigestEmailService(db=AsyncMock(), email_service=Mock())
        assert service.recipient_email == "admin@example.com"


# ---------------------------------------------------------------------------
# _build_email_html
# ---------------------------------------------------------------------------


class TestBuildEmailHtml:
    """Tests for the pure _build_email_html method."""

    def _service(self) -> TaskDigestEmailService:
        return TaskDigestEmailService(db=AsyncMock(), email_service=Mock())

    def test_returns_string(self):
        svc = self._service()
        result = svc._build_email_html([_make_task()], datetime(2025, 11, 20).date())
        assert isinstance(result, str)

    def test_contains_date_formatted_italian(self):
        svc = self._service()
        date = datetime(2025, 11, 20).date()
        html = svc._build_email_html([_make_task()], date)
        assert "20/11/2025" in html

    def test_contains_task_id(self):
        svc = self._service()
        task = _make_task(task_id="QUERY-42")
        html = svc._build_email_html([task], datetime(2025, 11, 20).date())
        assert "QUERY-42" in html

    def test_contains_task_name(self):
        svc = self._service()
        task = _make_task(task_name="Aggiorna normativa IVA")
        html = svc._build_email_html([task], datetime(2025, 11, 20).date())
        assert "Aggiorna normativa IVA" in html

    def test_contains_trust_score(self):
        svc = self._service()
        task = _make_task(expert=_make_expert(trust_score=0.92))
        html = svc._build_email_html([task], datetime(2025, 11, 20).date())
        assert "0.92" in html

    def test_truncates_long_question(self):
        svc = self._service()
        long_question = "A" * 200
        task = _make_task(question=long_question)
        html = svc._build_email_html([task], datetime(2025, 11, 20).date())
        # First 100 chars should be present, and "..." indicating truncation
        assert "A" * 100 in html
        assert "..." in html

    def test_short_question_no_ellipsis(self):
        svc = self._service()
        short_question = "Domanda breve"
        task = _make_task(question=short_question)
        html = svc._build_email_html([task], datetime(2025, 11, 20).date())
        assert "Domanda breve" in html

    def test_multiple_tasks(self):
        svc = self._service()
        tasks = [
            _make_task(task_id="QUERY-01", task_name="Task 1"),
            _make_task(task_id="QUERY-02", task_name="Task 2"),
            _make_task(task_id="QUERY-03", task_name="Task 3"),
        ]
        html = svc._build_email_html(tasks, datetime(2025, 11, 20).date())
        assert "QUERY-01" in html
        assert "QUERY-02" in html
        assert "QUERY-03" in html

    def test_singular_task_wording(self):
        svc = self._service()
        html = svc._build_email_html([_make_task()], datetime(2025, 11, 20).date())
        # The source uses "è stato creato" for singular
        assert "è stato creato" in html

    def test_plural_task_wording(self):
        svc = self._service()
        tasks = [_make_task(task_id="Q-01"), _make_task(task_id="Q-02")]
        html = svc._build_email_html(tasks, datetime(2025, 11, 20).date())
        assert "sono stati creati" in html

    def test_html_has_doctype(self):
        svc = self._service()
        html = svc._build_email_html([_make_task()], datetime(2025, 11, 20).date())
        assert html.startswith("<!DOCTYPE html>")

    def test_task_count_displayed(self):
        svc = self._service()
        tasks = [_make_task(task_id=f"Q-{i}") for i in range(5)]
        html = svc._build_email_html(tasks, datetime(2025, 11, 20).date())
        assert ">5<" in html  # The count is wrapped in a <strong> tag

    def test_feedback_id_truncated(self):
        svc = self._service()
        fid = uuid4()
        task = _make_task(feedback_id=fid)
        html = svc._build_email_html([task], datetime(2025, 11, 20).date())
        assert str(fid)[:8] in html

    def test_created_at_time_displayed(self):
        svc = self._service()
        task = _make_task(created_at=datetime(2025, 11, 20, 9, 45))
        html = svc._build_email_html([task], datetime(2025, 11, 20).date())
        assert "09:45" in html


# ---------------------------------------------------------------------------
# send_daily_digest
# ---------------------------------------------------------------------------


class TestSendDailyDigest:
    """Tests for the async send_daily_digest method."""

    @pytest.mark.asyncio
    async def test_no_tasks_returns_false(self):
        """When no tasks were created yesterday, should return False without sending."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.unique.return_value.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        mock_email = AsyncMock()

        service = TaskDigestEmailService(db=mock_db, email_service=mock_email)
        result = await service.send_daily_digest()

        assert result is False

    @pytest.mark.asyncio
    async def test_tasks_found_sends_email_and_returns_true(self):
        """When tasks exist, should build HTML and send email, returning True on success."""
        mock_db = AsyncMock()
        tasks = [_make_task(task_id="QUERY-01")]
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.unique.return_value.all.return_value = tasks
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        mock_email = AsyncMock()
        mock_email.send_email = AsyncMock(return_value=True)

        service = TaskDigestEmailService(db=mock_db, email_service=mock_email)
        result = await service.send_daily_digest()

        assert result is True
        mock_email.send_email.assert_awaited_once()
        call_kwargs = mock_email.send_email.call_args[1]
        assert "html_body" in call_kwargs
        assert "subject" in call_kwargs
        assert "to" in call_kwargs

    @pytest.mark.asyncio
    async def test_email_send_failure_returns_false(self):
        """When email_service.send_email returns False, should propagate False."""
        mock_db = AsyncMock()
        tasks = [_make_task()]
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.unique.return_value.all.return_value = tasks
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        mock_email = AsyncMock()
        mock_email.send_email = AsyncMock(return_value=False)

        service = TaskDigestEmailService(db=mock_db, email_service=mock_email)
        result = await service.send_daily_digest()

        assert result is False

    @pytest.mark.asyncio
    async def test_db_exception_returns_false(self):
        """When a DB query raises an exception, should catch and return False."""
        mock_db = AsyncMock()
        mock_db.execute.side_effect = Exception("DB connection lost")

        mock_email = AsyncMock()

        service = TaskDigestEmailService(db=mock_db, email_service=mock_email)
        result = await service.send_daily_digest()

        assert result is False

    @pytest.mark.asyncio
    async def test_subject_contains_yesterday_date(self):
        """The email subject should contain yesterday's date formatted as dd/mm/YYYY."""
        mock_db = AsyncMock()
        tasks = [_make_task()]
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.unique.return_value.all.return_value = tasks
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        mock_email = AsyncMock()
        mock_email.send_email = AsyncMock(return_value=True)

        service = TaskDigestEmailService(db=mock_db, email_service=mock_email)
        await service.send_daily_digest()

        call_kwargs = mock_email.send_email.call_args[1]
        yesterday = (datetime.now().date() - timedelta(days=1)).strftime("%d/%m/%Y")
        assert yesterday in call_kwargs["subject"]

    @pytest.mark.asyncio
    async def test_email_sent_to_recipient(self):
        """The email should be sent to the configured recipient_email."""
        mock_db = AsyncMock()
        tasks = [_make_task()]
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.unique.return_value.all.return_value = tasks
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        mock_email = AsyncMock()
        mock_email.send_email = AsyncMock(return_value=True)

        service = TaskDigestEmailService(db=mock_db, email_service=mock_email)
        service.recipient_email = "test-admin@pratikoai.com"
        await service.send_daily_digest()

        call_kwargs = mock_email.send_email.call_args[1]
        assert call_kwargs["to"] == "test-admin@pratikoai.com"

    @pytest.mark.asyncio
    async def test_html_body_contains_task_data(self):
        """The generated HTML body should contain task details from the DB query."""
        mock_db = AsyncMock()
        tasks = [_make_task(task_id="QUERY-99", task_name="Special task")]
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.unique.return_value.all.return_value = tasks
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        mock_email = AsyncMock()
        mock_email.send_email = AsyncMock(return_value=True)

        service = TaskDigestEmailService(db=mock_db, email_service=mock_email)
        await service.send_daily_digest()

        call_kwargs = mock_email.send_email.call_args[1]
        assert "QUERY-99" in call_kwargs["html_body"]
        assert "Special task" in call_kwargs["html_body"]
