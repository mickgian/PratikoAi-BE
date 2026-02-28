"""Comprehensive tests for SlackNotificationService.

Tests cover:
- Constructor attribute storage
- _send_slack_message: disabled, no URL, success, non-200, timeout, generic exception
- send_architect_veto: payload structure with/without alternative_approach
- send_scrum_progress_update: ON TRACK/AT RISK/DELAYED statuses, with/without blockers/velocity
- send_task_completion: payload structure and delegation
- send_blocker_alert: payload structure and delegation
- send_sprint_summary: severity thresholds at 90%+, 70-89%, <70%, zero total tasks
- send_daily_standup: with/without blockers, custom sprint_day and progress
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import httpx
import pytest

from app.services.slack_notification_service import (
    NotificationSeverity,
    SlackNotificationService,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def service() -> SlackNotificationService:
    """Return a fully-configured, enabled service instance."""
    return SlackNotificationService(
        architect_webhook_url="https://hooks.slack.com/architect",
        scrum_webhook_url="https://hooks.slack.com/scrum",
        enabled=True,
    )


@pytest.fixture
def disabled_service() -> SlackNotificationService:
    """Return a disabled service instance."""
    return SlackNotificationService(
        architect_webhook_url="https://hooks.slack.com/architect",
        scrum_webhook_url="https://hooks.slack.com/scrum",
        enabled=False,
    )


@pytest.fixture
def no_url_service() -> SlackNotificationService:
    """Return a service instance with empty webhook URLs."""
    return SlackNotificationService(
        architect_webhook_url="",
        scrum_webhook_url="",
        enabled=True,
    )


# ---------------------------------------------------------------------------
# NotificationSeverity enum
# ---------------------------------------------------------------------------


class TestNotificationSeverity:
    """Tests for the NotificationSeverity enum."""

    def test_info_value(self):
        assert NotificationSeverity.INFO.value == "info"

    def test_warning_value(self):
        assert NotificationSeverity.WARNING.value == "warning"

    def test_error_value(self):
        assert NotificationSeverity.ERROR.value == "error"

    def test_critical_value(self):
        assert NotificationSeverity.CRITICAL.value == "critical"

    def test_all_members_present(self):
        members = {m.name for m in NotificationSeverity}
        assert members == {"INFO", "WARNING", "ERROR", "CRITICAL"}


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


class TestSlackNotificationServiceInit:
    """Tests for constructor attribute storage."""

    def test_stores_architect_webhook_url(self, service: SlackNotificationService):
        assert service.architect_webhook_url == "https://hooks.slack.com/architect"

    def test_stores_scrum_webhook_url(self, service: SlackNotificationService):
        assert service.scrum_webhook_url == "https://hooks.slack.com/scrum"

    def test_stores_enabled_true(self, service: SlackNotificationService):
        assert service.enabled is True

    def test_stores_enabled_false(self, disabled_service: SlackNotificationService):
        assert disabled_service.enabled is False

    def test_default_enabled_is_true(self):
        svc = SlackNotificationService(architect_webhook_url="x", scrum_webhook_url="y")
        assert svc.enabled is True

    def test_color_map_has_all_severities(self, service: SlackNotificationService):
        for severity in NotificationSeverity:
            assert severity in service.color_map


# ---------------------------------------------------------------------------
# _send_slack_message
# ---------------------------------------------------------------------------


class TestSendSlackMessage:
    """Tests for the private _send_slack_message method."""

    @pytest.mark.asyncio
    async def test_disabled_returns_false(self, disabled_service: SlackNotificationService):
        result = await disabled_service._send_slack_message({"text": "hi"}, "https://hooks.slack.com/test")
        assert result is False

    @pytest.mark.asyncio
    async def test_no_url_returns_false(self, service: SlackNotificationService):
        result = await service._send_slack_message({"text": "hi"}, "")
        assert result is False

    @pytest.mark.asyncio
    async def test_none_url_returns_false(self, service: SlackNotificationService):
        result = await service._send_slack_message({"text": "hi"}, None)
        assert result is False

    @pytest.mark.asyncio
    @patch("app.services.slack_notification_service.httpx.AsyncClient")
    async def test_success_returns_true(self, mock_client_cls: MagicMock, service: SlackNotificationService):
        mock_response = Mock(status_code=200)
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        result = await service._send_slack_message({"text": "hello"}, "https://hooks.slack.com/test")
        assert result is True
        mock_client.post.assert_awaited_once_with("https://hooks.slack.com/test", json={"text": "hello"}, timeout=30)

    @pytest.mark.asyncio
    @patch("app.services.slack_notification_service.httpx.AsyncClient")
    async def test_non_200_returns_false(self, mock_client_cls: MagicMock, service: SlackNotificationService):
        mock_response = Mock(status_code=500)
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        result = await service._send_slack_message({"text": "hello"}, "https://hooks.slack.com/test")
        assert result is False

    @pytest.mark.asyncio
    @patch("app.services.slack_notification_service.httpx.AsyncClient")
    async def test_timeout_returns_false(self, mock_client_cls: MagicMock, service: SlackNotificationService):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        result = await service._send_slack_message({"text": "hello"}, "https://hooks.slack.com/test")
        assert result is False

    @pytest.mark.asyncio
    @patch("app.services.slack_notification_service.httpx.AsyncClient")
    async def test_generic_exception_returns_false(
        self, mock_client_cls: MagicMock, service: SlackNotificationService
    ):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=ConnectionError("conn refused"))
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        result = await service._send_slack_message({"text": "hello"}, "https://hooks.slack.com/test")
        assert result is False


# ---------------------------------------------------------------------------
# send_architect_veto
# ---------------------------------------------------------------------------


class TestSendArchitectVeto:
    """Tests for send_architect_veto."""

    @pytest.mark.asyncio
    async def test_calls_send_slack_message_with_architect_url(self, service: SlackNotificationService):
        with patch.object(service, "_send_slack_message", new_callable=AsyncMock, return_value=True) as mock_send:
            result = await service.send_architect_veto(
                task_id="DEV-BE-42",
                task_description="Add Redis caching",
                proposed_by="@ezio",
                veto_reason="Violates ADR-033",
                violated_principle="ADR-033 Redis security",
                risk_introduced="Unsecured Redis in production",
            )
            assert result is True
            mock_send.assert_awaited_once()
            webhook_url = mock_send.call_args[0][1]
            assert webhook_url == "https://hooks.slack.com/architect"

    @pytest.mark.asyncio
    async def test_payload_contains_required_fields(self, service: SlackNotificationService):
        with patch.object(service, "_send_slack_message", new_callable=AsyncMock, return_value=True) as mock_send:
            await service.send_architect_veto(
                task_id="DEV-BE-42",
                task_description="Add Redis caching",
                proposed_by="@ezio",
                veto_reason="Violates ADR-033",
                violated_principle="ADR-033",
                risk_introduced="Security risk",
            )
            payload = mock_send.call_args[0][0]
            assert "ARCHITECT VETO" in payload["text"]
            attachment = payload["attachments"][0]
            assert attachment["color"] == service.color_map[NotificationSeverity.CRITICAL]
            field_titles = [f["title"] for f in attachment["fields"]]
            assert "Task" in field_titles
            assert "Proposed By" in field_titles
            assert "Veto Reason" in field_titles
            assert "Violated Principle" in field_titles
            assert "Risk Introduced" in field_titles

    @pytest.mark.asyncio
    async def test_without_alternative_approach(self, service: SlackNotificationService):
        with patch.object(service, "_send_slack_message", new_callable=AsyncMock, return_value=True) as mock_send:
            await service.send_architect_veto(
                task_id="DEV-42",
                task_description="desc",
                proposed_by="@ezio",
                veto_reason="reason",
                violated_principle="ADR-001",
                risk_introduced="risk",
                alternative_approach=None,
            )
            payload = mock_send.call_args[0][0]
            field_titles = [f["title"] for f in payload["attachments"][0]["fields"]]
            assert "Alternative Approach" not in field_titles

    @pytest.mark.asyncio
    async def test_with_alternative_approach(self, service: SlackNotificationService):
        with patch.object(service, "_send_slack_message", new_callable=AsyncMock, return_value=True) as mock_send:
            await service.send_architect_veto(
                task_id="DEV-42",
                task_description="desc",
                proposed_by="@ezio",
                veto_reason="reason",
                violated_principle="ADR-001",
                risk_introduced="risk",
                alternative_approach="Use a different approach",
            )
            payload = mock_send.call_args[0][0]
            field_titles = [f["title"] for f in payload["attachments"][0]["fields"]]
            assert "Alternative Approach" in field_titles
            alt_field = [f for f in payload["attachments"][0]["fields"] if f["title"] == "Alternative Approach"][0]
            assert alt_field["value"] == "Use a different approach"


# ---------------------------------------------------------------------------
# send_scrum_progress_update
# ---------------------------------------------------------------------------


class TestSendScrumProgressUpdate:
    """Tests for send_scrum_progress_update."""

    @pytest.mark.asyncio
    async def test_on_track_status(self, service: SlackNotificationService):
        with patch.object(service, "_send_slack_message", new_callable=AsyncMock, return_value=True) as mock_send:
            await service.send_scrum_progress_update(
                sprint_name="Sprint 1",
                sprint_progress="5/12 (42%)",
                tasks_in_progress=[{"id": "DEV-01", "description": "Task 1", "assignee": "@ezio", "progress": "50%"}],
                tasks_completed_today=["DEV-02"],
                tasks_next_up=["DEV-03"],
                sprint_status="ON TRACK",
            )
            payload = mock_send.call_args[0][0]
            webhook_url = mock_send.call_args[0][1]
            assert webhook_url == "https://hooks.slack.com/scrum"
            # Check blocks contain status emoji for ON TRACK
            status_block = payload["blocks"][1]
            fields_text = " ".join(f["text"] for f in status_block["fields"])
            assert "ON TRACK" in fields_text

    @pytest.mark.asyncio
    async def test_at_risk_status(self, service: SlackNotificationService):
        with patch.object(service, "_send_slack_message", new_callable=AsyncMock, return_value=True) as mock_send:
            await service.send_scrum_progress_update(
                sprint_name="Sprint 1",
                sprint_progress="3/12 (25%)",
                tasks_in_progress=[],
                tasks_completed_today=[],
                tasks_next_up=[],
                sprint_status="AT RISK",
            )
            payload = mock_send.call_args[0][0]
            status_block = payload["blocks"][1]
            fields_text = " ".join(f["text"] for f in status_block["fields"])
            assert "AT RISK" in fields_text

    @pytest.mark.asyncio
    async def test_delayed_status(self, service: SlackNotificationService):
        with patch.object(service, "_send_slack_message", new_callable=AsyncMock, return_value=True) as mock_send:
            await service.send_scrum_progress_update(
                sprint_name="Sprint 1",
                sprint_progress="1/12 (8%)",
                tasks_in_progress=[],
                tasks_completed_today=[],
                tasks_next_up=[],
                sprint_status="DELAYED",
            )
            payload = mock_send.call_args[0][0]
            status_block = payload["blocks"][1]
            fields_text = " ".join(f["text"] for f in status_block["fields"])
            assert "DELAYED" in fields_text

    @pytest.mark.asyncio
    async def test_unknown_status_defaults(self, service: SlackNotificationService):
        with patch.object(service, "_send_slack_message", new_callable=AsyncMock, return_value=True) as mock_send:
            await service.send_scrum_progress_update(
                sprint_name="Sprint 1",
                sprint_progress="0/0",
                tasks_in_progress=[],
                tasks_completed_today=[],
                tasks_next_up=[],
                sprint_status="UNKNOWN",
            )
            payload = mock_send.call_args[0][0]
            # Should still produce a valid payload
            assert "blocks" in payload

    @pytest.mark.asyncio
    async def test_with_blockers(self, service: SlackNotificationService):
        with patch.object(service, "_send_slack_message", new_callable=AsyncMock, return_value=True) as mock_send:
            await service.send_scrum_progress_update(
                sprint_name="Sprint 1",
                sprint_progress="5/12 (42%)",
                tasks_in_progress=[],
                tasks_completed_today=[],
                tasks_next_up=[],
                blockers=["DB migration conflict", "Waiting on API key"],
            )
            payload = mock_send.call_args[0][0]
            blocks_text = str(payload["blocks"])
            assert "DB migration conflict" in blocks_text
            assert "Blockers" in blocks_text

    @pytest.mark.asyncio
    async def test_without_blockers(self, service: SlackNotificationService):
        with patch.object(service, "_send_slack_message", new_callable=AsyncMock, return_value=True) as mock_send:
            await service.send_scrum_progress_update(
                sprint_name="Sprint 1",
                sprint_progress="5/12 (42%)",
                tasks_in_progress=[],
                tasks_completed_today=[],
                tasks_next_up=[],
                blockers=None,
            )
            payload = mock_send.call_args[0][0]
            blocks_text = str(payload["blocks"])
            assert "Blockers" not in blocks_text

    @pytest.mark.asyncio
    async def test_with_velocity(self, service: SlackNotificationService):
        with patch.object(service, "_send_slack_message", new_callable=AsyncMock, return_value=True) as mock_send:
            await service.send_scrum_progress_update(
                sprint_name="Sprint 1",
                sprint_progress="5/12",
                tasks_in_progress=[],
                tasks_completed_today=[],
                tasks_next_up=[],
                velocity="2.5 points/day",
            )
            payload = mock_send.call_args[0][0]
            blocks_text = str(payload["blocks"])
            assert "2.5 points/day" in blocks_text

    @pytest.mark.asyncio
    async def test_without_velocity(self, service: SlackNotificationService):
        with patch.object(service, "_send_slack_message", new_callable=AsyncMock, return_value=True) as mock_send:
            await service.send_scrum_progress_update(
                sprint_name="Sprint 1",
                sprint_progress="5/12",
                tasks_in_progress=[],
                tasks_completed_today=[],
                tasks_next_up=[],
                velocity=None,
            )
            payload = mock_send.call_args[0][0]
            blocks_text = str(payload["blocks"])
            assert "Velocity" not in blocks_text


# ---------------------------------------------------------------------------
# send_task_completion
# ---------------------------------------------------------------------------


class TestSendTaskCompletion:
    """Tests for send_task_completion."""

    @pytest.mark.asyncio
    async def test_sends_to_scrum_webhook(self, service: SlackNotificationService):
        with patch.object(service, "_send_slack_message", new_callable=AsyncMock, return_value=True) as mock_send:
            result = await service.send_task_completion(
                task_id="DEV-BE-67",
                task_description="Implement search",
                assigned_to="@ezio",
                duration="3 days",
            )
            assert result is True
            webhook_url = mock_send.call_args[0][1]
            assert webhook_url == "https://hooks.slack.com/scrum"

    @pytest.mark.asyncio
    async def test_payload_structure(self, service: SlackNotificationService):
        with patch.object(service, "_send_slack_message", new_callable=AsyncMock, return_value=True) as mock_send:
            await service.send_task_completion(
                task_id="DEV-BE-67",
                task_description="Implement search",
                assigned_to="@ezio",
                duration="3 days",
            )
            payload = mock_send.call_args[0][0]
            assert "TASK COMPLETED" in payload["text"]
            attachment = payload["attachments"][0]
            assert attachment["color"] == service.color_map[NotificationSeverity.INFO]
            field_titles = [f["title"] for f in attachment["fields"]]
            assert "Task" in field_titles
            assert "Completed By" in field_titles
            assert "Duration" in field_titles
            assert "Completed At" in field_titles

    @pytest.mark.asyncio
    async def test_task_field_combines_id_and_description(self, service: SlackNotificationService):
        with patch.object(service, "_send_slack_message", new_callable=AsyncMock, return_value=True) as mock_send:
            await service.send_task_completion(
                task_id="DEV-99",
                task_description="Fix bug",
                assigned_to="@tiziano",
                duration="1 day",
            )
            payload = mock_send.call_args[0][0]
            task_field = [f for f in payload["attachments"][0]["fields"] if f["title"] == "Task"][0]
            assert "DEV-99" in task_field["value"]
            assert "Fix bug" in task_field["value"]


# ---------------------------------------------------------------------------
# send_blocker_alert
# ---------------------------------------------------------------------------


class TestSendBlockerAlert:
    """Tests for send_blocker_alert."""

    @pytest.mark.asyncio
    async def test_sends_to_scrum_webhook(self, service: SlackNotificationService):
        with patch.object(service, "_send_slack_message", new_callable=AsyncMock, return_value=True) as mock_send:
            result = await service.send_blocker_alert(
                task_id="DEV-BE-42",
                blocker_description="Database migration fails",
                escalated_to="Architect",
                impact="Blocks Sprint 1 completion",
            )
            assert result is True
            webhook_url = mock_send.call_args[0][1]
            assert webhook_url == "https://hooks.slack.com/scrum"

    @pytest.mark.asyncio
    async def test_payload_structure(self, service: SlackNotificationService):
        with patch.object(service, "_send_slack_message", new_callable=AsyncMock, return_value=True) as mock_send:
            await service.send_blocker_alert(
                task_id="DEV-42",
                blocker_description="Migration fails",
                escalated_to="Architect",
                impact="Blocks sprint",
            )
            payload = mock_send.call_args[0][0]
            assert "BLOCKER DETECTED" in payload["text"]
            attachment = payload["attachments"][0]
            assert attachment["color"] == service.color_map[NotificationSeverity.WARNING]
            field_titles = [f["title"] for f in attachment["fields"]]
            assert "Task" in field_titles
            assert "Escalated To" in field_titles
            assert "Blocker Description" in field_titles
            assert "Impact" in field_titles
            assert "Detected At" in field_titles


# ---------------------------------------------------------------------------
# send_sprint_summary
# ---------------------------------------------------------------------------


class TestSendSprintSummary:
    """Tests for send_sprint_summary."""

    @pytest.mark.asyncio
    async def test_high_completion_rate_uses_info_severity(self, service: SlackNotificationService):
        """Completion rate >= 90% should use INFO (green) severity."""
        with patch.object(service, "_send_slack_message", new_callable=AsyncMock, return_value=True) as mock_send:
            await service.send_sprint_summary(
                sprint_name="Sprint 1",
                sprint_dates="2025-11-15 to 2025-11-21",
                tasks_completed=9,
                tasks_total=10,
                velocity="3 pts/day",
                completed_tasks_list=["DEV-01", "DEV-02"],
                incomplete_tasks_list=["DEV-03"],
                blockers_encountered=["None"],
                lessons_learned=["TDD works"],
            )
            payload = mock_send.call_args[0][0]
            attachment = payload["attachments"][0]
            assert attachment["color"] == service.color_map[NotificationSeverity.INFO]

    @pytest.mark.asyncio
    async def test_medium_completion_rate_uses_warning_severity(self, service: SlackNotificationService):
        """Completion rate 70-89% should use WARNING (orange) severity."""
        with patch.object(service, "_send_slack_message", new_callable=AsyncMock, return_value=True) as mock_send:
            await service.send_sprint_summary(
                sprint_name="Sprint 2",
                sprint_dates="2025-11-22 to 2025-11-28",
                tasks_completed=7,
                tasks_total=10,
                velocity="2 pts/day",
                completed_tasks_list=["DEV-01"],
                incomplete_tasks_list=["DEV-02", "DEV-03"],
                blockers_encountered=[],
                lessons_learned=[],
            )
            payload = mock_send.call_args[0][0]
            attachment = payload["attachments"][0]
            assert attachment["color"] == service.color_map[NotificationSeverity.WARNING]

    @pytest.mark.asyncio
    async def test_low_completion_rate_uses_error_severity(self, service: SlackNotificationService):
        """Completion rate < 70% should use ERROR (red) severity."""
        with patch.object(service, "_send_slack_message", new_callable=AsyncMock, return_value=True) as mock_send:
            await service.send_sprint_summary(
                sprint_name="Sprint 3",
                sprint_dates="2025-12-01 to 2025-12-07",
                tasks_completed=3,
                tasks_total=10,
                velocity="1 pt/day",
                completed_tasks_list=["DEV-01"],
                incomplete_tasks_list=["DEV-02"],
                blockers_encountered=["Infra down"],
                lessons_learned=["Need better monitoring"],
            )
            payload = mock_send.call_args[0][0]
            attachment = payload["attachments"][0]
            assert attachment["color"] == service.color_map[NotificationSeverity.ERROR]

    @pytest.mark.asyncio
    async def test_zero_total_tasks_results_in_zero_completion(self, service: SlackNotificationService):
        """Zero total tasks should not raise ZeroDivisionError and should use ERROR."""
        with patch.object(service, "_send_slack_message", new_callable=AsyncMock, return_value=True) as mock_send:
            await service.send_sprint_summary(
                sprint_name="Sprint X",
                sprint_dates="N/A",
                tasks_completed=0,
                tasks_total=0,
                velocity="0",
                completed_tasks_list=[],
                incomplete_tasks_list=[],
                blockers_encountered=[],
                lessons_learned=[],
            )
            payload = mock_send.call_args[0][0]
            attachment = payload["attachments"][0]
            # 0% completion → ERROR severity
            assert attachment["color"] == service.color_map[NotificationSeverity.ERROR]

    @pytest.mark.asyncio
    async def test_completion_rate_calculation(self, service: SlackNotificationService):
        with patch.object(service, "_send_slack_message", new_callable=AsyncMock, return_value=True) as mock_send:
            await service.send_sprint_summary(
                sprint_name="Sprint 1",
                sprint_dates="dates",
                tasks_completed=5,
                tasks_total=10,
                velocity="v",
                completed_tasks_list=[],
                incomplete_tasks_list=[],
                blockers_encountered=[],
                lessons_learned=[],
            )
            payload = mock_send.call_args[0][0]
            # Find the Completion Rate field
            completion_field = [f for f in payload["attachments"][0]["fields"] if f["title"] == "Completion Rate"][0]
            assert "5/10 (50%)" in completion_field["value"]

    @pytest.mark.asyncio
    async def test_empty_lists_show_none(self, service: SlackNotificationService):
        with patch.object(service, "_send_slack_message", new_callable=AsyncMock, return_value=True) as mock_send:
            await service.send_sprint_summary(
                sprint_name="Sprint 1",
                sprint_dates="dates",
                tasks_completed=0,
                tasks_total=0,
                velocity="0",
                completed_tasks_list=[],
                incomplete_tasks_list=[],
                blockers_encountered=[],
                lessons_learned=[],
            )
            payload = mock_send.call_args[0][0]
            fields = payload["attachments"][0]["fields"]
            completed_field = [f for f in fields if "Completed Tasks" in f["title"]][0]
            assert completed_field["value"] == "None"
            incomplete_field = [f for f in fields if "Incomplete Tasks" in f["title"]][0]
            assert incomplete_field["value"] == "None"

    @pytest.mark.asyncio
    async def test_sends_to_scrum_webhook(self, service: SlackNotificationService):
        with patch.object(service, "_send_slack_message", new_callable=AsyncMock, return_value=True) as mock_send:
            await service.send_sprint_summary(
                sprint_name="S",
                sprint_dates="d",
                tasks_completed=1,
                tasks_total=1,
                velocity="v",
                completed_tasks_list=[],
                incomplete_tasks_list=[],
                blockers_encountered=[],
                lessons_learned=[],
            )
            webhook_url = mock_send.call_args[0][1]
            assert webhook_url == "https://hooks.slack.com/scrum"

    @pytest.mark.asyncio
    async def test_exactly_90_percent_is_info(self, service: SlackNotificationService):
        """Boundary: exactly 90% should be INFO."""
        with patch.object(service, "_send_slack_message", new_callable=AsyncMock, return_value=True) as mock_send:
            await service.send_sprint_summary(
                sprint_name="S",
                sprint_dates="d",
                tasks_completed=9,
                tasks_total=10,
                velocity="v",
                completed_tasks_list=[],
                incomplete_tasks_list=[],
                blockers_encountered=[],
                lessons_learned=[],
            )
            payload = mock_send.call_args[0][0]
            assert payload["attachments"][0]["color"] == service.color_map[NotificationSeverity.INFO]

    @pytest.mark.asyncio
    async def test_exactly_70_percent_is_warning(self, service: SlackNotificationService):
        """Boundary: exactly 70% should be WARNING."""
        with patch.object(service, "_send_slack_message", new_callable=AsyncMock, return_value=True) as mock_send:
            await service.send_sprint_summary(
                sprint_name="S",
                sprint_dates="d",
                tasks_completed=7,
                tasks_total=10,
                velocity="v",
                completed_tasks_list=[],
                incomplete_tasks_list=[],
                blockers_encountered=[],
                lessons_learned=[],
            )
            payload = mock_send.call_args[0][0]
            assert payload["attachments"][0]["color"] == service.color_map[NotificationSeverity.WARNING]

    @pytest.mark.asyncio
    async def test_69_percent_is_error(self, service: SlackNotificationService):
        """Boundary: 69% (< 70%) should be ERROR."""
        with patch.object(service, "_send_slack_message", new_callable=AsyncMock, return_value=True) as mock_send:
            # 69/100 = 69%
            await service.send_sprint_summary(
                sprint_name="S",
                sprint_dates="d",
                tasks_completed=69,
                tasks_total=100,
                velocity="v",
                completed_tasks_list=[],
                incomplete_tasks_list=[],
                blockers_encountered=[],
                lessons_learned=[],
            )
            payload = mock_send.call_args[0][0]
            assert payload["attachments"][0]["color"] == service.color_map[NotificationSeverity.ERROR]


# ---------------------------------------------------------------------------
# send_daily_standup
# ---------------------------------------------------------------------------


class TestSendDailyStandup:
    """Tests for send_daily_standup."""

    @pytest.mark.asyncio
    async def test_sends_to_scrum_webhook(self, service: SlackNotificationService):
        with patch.object(service, "_send_slack_message", new_callable=AsyncMock, return_value=True) as mock_send:
            result = await service.send_daily_standup(
                sprint_name="Sprint 1",
                yesterday_completed=["DEV-01"],
                today_active=["DEV-02"],
                next_up=["DEV-03"],
            )
            assert result is True
            webhook_url = mock_send.call_args[0][1]
            assert webhook_url == "https://hooks.slack.com/scrum"

    @pytest.mark.asyncio
    async def test_payload_contains_standup_text(self, service: SlackNotificationService):
        with patch.object(service, "_send_slack_message", new_callable=AsyncMock, return_value=True) as mock_send:
            await service.send_daily_standup(
                sprint_name="Sprint 1",
                yesterday_completed=["DEV-01"],
                today_active=["DEV-02"],
                next_up=["DEV-03"],
            )
            payload = mock_send.call_args[0][0]
            assert "DAILY STANDUP" in payload["text"]

    @pytest.mark.asyncio
    async def test_with_blockers(self, service: SlackNotificationService):
        with patch.object(service, "_send_slack_message", new_callable=AsyncMock, return_value=True) as mock_send:
            await service.send_daily_standup(
                sprint_name="Sprint 1",
                yesterday_completed=[],
                today_active=[],
                next_up=[],
                blockers=["CI pipeline broken", "Need code review"],
            )
            payload = mock_send.call_args[0][0]
            fields = payload["attachments"][0]["fields"]
            blocker_field = [f for f in fields if "Blockers" in f["title"]][0]
            assert "CI pipeline broken" in blocker_field["value"]
            assert "Need code review" in blocker_field["value"]

    @pytest.mark.asyncio
    async def test_without_blockers(self, service: SlackNotificationService):
        with patch.object(service, "_send_slack_message", new_callable=AsyncMock, return_value=True) as mock_send:
            await service.send_daily_standup(
                sprint_name="Sprint 1",
                yesterday_completed=[],
                today_active=[],
                next_up=[],
                blockers=None,
            )
            payload = mock_send.call_args[0][0]
            fields = payload["attachments"][0]["fields"]
            blocker_field = [f for f in fields if "Blockers" in f["title"]][0]
            assert blocker_field["value"] == "None"

    @pytest.mark.asyncio
    async def test_custom_sprint_day_and_progress(self, service: SlackNotificationService):
        with patch.object(service, "_send_slack_message", new_callable=AsyncMock, return_value=True) as mock_send:
            await service.send_daily_standup(
                sprint_name="Sprint 2",
                yesterday_completed=["DEV-10"],
                today_active=["DEV-11"],
                next_up=["DEV-12"],
                sprint_day=5,
                sprint_progress="75%",
            )
            payload = mock_send.call_args[0][0]
            fields = payload["attachments"][0]["fields"]
            sprint_field = [f for f in fields if f["title"] == "Sprint"][0]
            assert "Day 5" in sprint_field["value"]
            progress_field = [f for f in fields if f["title"] == "Progress"][0]
            assert progress_field["value"] == "75%"

    @pytest.mark.asyncio
    async def test_default_sprint_day_and_progress(self, service: SlackNotificationService):
        with patch.object(service, "_send_slack_message", new_callable=AsyncMock, return_value=True) as mock_send:
            await service.send_daily_standup(
                sprint_name="Sprint 1",
                yesterday_completed=[],
                today_active=[],
                next_up=[],
            )
            payload = mock_send.call_args[0][0]
            fields = payload["attachments"][0]["fields"]
            sprint_field = [f for f in fields if f["title"] == "Sprint"][0]
            assert "Day 1" in sprint_field["value"]
            progress_field = [f for f in fields if f["title"] == "Progress"][0]
            assert progress_field["value"] == "0%"

    @pytest.mark.asyncio
    async def test_empty_yesterday_shows_none(self, service: SlackNotificationService):
        with patch.object(service, "_send_slack_message", new_callable=AsyncMock, return_value=True) as mock_send:
            await service.send_daily_standup(
                sprint_name="Sprint 1",
                yesterday_completed=[],
                today_active=["DEV-01"],
                next_up=["DEV-02"],
            )
            payload = mock_send.call_args[0][0]
            fields = payload["attachments"][0]["fields"]
            yesterday_field = [f for f in fields if "Yesterday" in f["title"]][0]
            assert yesterday_field["value"] == "None"

    @pytest.mark.asyncio
    async def test_uses_info_color(self, service: SlackNotificationService):
        with patch.object(service, "_send_slack_message", new_callable=AsyncMock, return_value=True) as mock_send:
            await service.send_daily_standup(
                sprint_name="Sprint 1",
                yesterday_completed=[],
                today_active=[],
                next_up=[],
            )
            payload = mock_send.call_args[0][0]
            attachment = payload["attachments"][0]
            assert attachment["color"] == service.color_map[NotificationSeverity.INFO]
