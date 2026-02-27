"""DEV-325: Tests for Background Matching Job.

Tests cover:
- Happy path: run matching job creates ProactiveSuggestion records
- Happy path: notifications created for matched clients
- Edge case: no active rules found (no matches)
- Edge case: rule has no matching clients (empty result)
- Error: matching service raises exception (gracefully handled, logged)
- Fire-and-forget pattern: notification failure doesn't break job
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.matching_rule import MatchingRule, RuleType


@pytest.fixture
def mock_db() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def studio_id():
    return uuid4()


@pytest.fixture
def sample_rules() -> list[MatchingRule]:
    """Two active matching rules for testing."""
    return [
        MatchingRule(
            id=uuid4(),
            name="R001 — Rottamazione Quater",
            description="Rottamazione cartelle esattoriali quater.",
            rule_type=RuleType.NORMATIVA,
            conditions={
                "operator": "AND",
                "rules": [
                    {"field": "tipo_cliente", "op": "eq", "value": "persona_fisica"},
                ],
            },
            priority=80,
            is_active=True,
            valid_from=date(2026, 1, 1),
            valid_to=date(2026, 12, 31),
            categoria="fiscale",
            fonte_normativa="DL 34/2023",
        ),
        MatchingRule(
            id=uuid4(),
            name="R002 — Bonus Energia",
            description="Agevolazione bollette energia 2026.",
            rule_type=RuleType.OPPORTUNITA,
            conditions={
                "operator": "AND",
                "rules": [
                    {"field": "tipo_cliente", "op": "eq", "value": "societa"},
                ],
            },
            priority=60,
            is_active=True,
            valid_from=date(2026, 1, 1),
            valid_to=None,
            categoria="energia",
            fonte_normativa="DL 50/2026",
        ),
    ]


class TestRunMatchingJobHappyPath:
    """Happy path: job processes rules, creates suggestions and notifications."""

    @pytest.mark.asyncio
    async def test_creates_proactive_suggestions(
        self,
        mock_db: AsyncMock,
        studio_id,
        sample_rules: list[MatchingRule],
    ) -> None:
        """Job creates ProactiveSuggestion records for each matched rule."""
        from app.jobs.matching_job import run_matching_job

        # Mock: fetch active rules returns 2 rules
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = sample_rules
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_execute_result)

        # Mock: matching service returns matches for each rule
        with (
            patch("app.jobs.matching_job.normative_matching_service") as mock_matching_svc,
            patch("app.jobs.matching_job.notification_service") as mock_notif_svc,
        ):
            mock_matching_svc.match_rule_to_clients = AsyncMock(
                side_effect=[
                    [
                        {"client_id": 1, "score": 0.95, "method": "structured"},
                        {"client_id": 2, "score": 0.80, "method": "structured"},
                    ],
                    [
                        {"client_id": 3, "score": 0.70, "method": "semantic"},
                    ],
                ]
            )
            mock_notif_svc.create_notification = AsyncMock()

            result = await run_matching_job(
                db=mock_db,
                studio_id=studio_id,
                knowledge_item_id=42,
                trigger="rss",
            )

        assert result.rules_processed == 2
        assert result.matches_found == 3
        assert result.suggestions_created == 3
        # db.add called once per suggestion
        assert mock_db.add.call_count == 3

    @pytest.mark.asyncio
    async def test_notifications_created_for_matches(
        self,
        mock_db: AsyncMock,
        studio_id,
        sample_rules: list[MatchingRule],
    ) -> None:
        """Notifications are created for each match via NotificationService."""
        from app.jobs.matching_job import run_matching_job

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = sample_rules[:1]  # one rule
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_execute_result)

        with (
            patch("app.jobs.matching_job.normative_matching_service") as mock_matching_svc,
            patch("app.jobs.matching_job.notification_service") as mock_notif_svc,
        ):
            mock_matching_svc.match_rule_to_clients = AsyncMock(
                return_value=[
                    {"client_id": 1, "score": 0.90, "method": "structured"},
                ]
            )
            mock_notif_svc.create_notification = AsyncMock()

            result = await run_matching_job(
                db=mock_db,
                studio_id=studio_id,
                knowledge_item_id=10,
                trigger="chat",
            )

        assert result.notifications_sent == 1
        mock_notif_svc.create_notification.assert_called_once()
        # Verify notification type is MATCH
        call_kwargs = mock_notif_svc.create_notification.call_args
        assert call_kwargs.kwargs["notification_type"].value == "match"

    @pytest.mark.asyncio
    async def test_result_dataclass_fields(
        self,
        mock_db: AsyncMock,
        studio_id,
        sample_rules: list[MatchingRule],
    ) -> None:
        """MatchingJobResult has all expected fields."""
        from app.jobs.matching_job import MatchingJobResult, run_matching_job

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = sample_rules
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_execute_result)

        with (
            patch("app.jobs.matching_job.normative_matching_service") as mock_matching_svc,
            patch("app.jobs.matching_job.notification_service"),
        ):
            mock_matching_svc.match_rule_to_clients = AsyncMock(return_value=[])

            result = await run_matching_job(
                db=mock_db,
                studio_id=studio_id,
            )

        assert isinstance(result, MatchingJobResult)
        assert hasattr(result, "rules_processed")
        assert hasattr(result, "matches_found")
        assert hasattr(result, "suggestions_created")
        assert hasattr(result, "notifications_sent")


class TestRunMatchingJobEdgeCases:
    """Edge cases: no rules, no matches."""

    @pytest.mark.asyncio
    async def test_no_active_rules_returns_zero(
        self,
        mock_db: AsyncMock,
        studio_id,
    ) -> None:
        """No active rules returns result with all zeros."""
        from app.jobs.matching_job import run_matching_job

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_execute_result)

        result = await run_matching_job(
            db=mock_db,
            studio_id=studio_id,
        )

        assert result.rules_processed == 0
        assert result.matches_found == 0
        assert result.suggestions_created == 0
        assert result.notifications_sent == 0

    @pytest.mark.asyncio
    async def test_rule_with_no_matching_clients(
        self,
        mock_db: AsyncMock,
        studio_id,
        sample_rules: list[MatchingRule],
    ) -> None:
        """Rule exists but has no matching clients: suggestions_created = 0."""
        from app.jobs.matching_job import run_matching_job

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = sample_rules[:1]
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_execute_result)

        with (
            patch("app.jobs.matching_job.normative_matching_service") as mock_matching_svc,
            patch("app.jobs.matching_job.notification_service"),
        ):
            mock_matching_svc.match_rule_to_clients = AsyncMock(return_value=[])

            result = await run_matching_job(
                db=mock_db,
                studio_id=studio_id,
                knowledge_item_id=42,
            )

        assert result.rules_processed == 1
        assert result.matches_found == 0
        assert result.suggestions_created == 0
        assert result.notifications_sent == 0

    @pytest.mark.asyncio
    async def test_default_trigger_is_rss(
        self,
        mock_db: AsyncMock,
        studio_id,
    ) -> None:
        """Default trigger parameter is 'rss'."""
        from app.jobs.matching_job import run_matching_job

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_execute_result)

        # Should not raise; trigger defaults to "rss"
        result = await run_matching_job(db=mock_db, studio_id=studio_id)
        assert result.rules_processed == 0


class TestRunMatchingJobErrorHandling:
    """Error handling: matching service errors, notification failures."""

    @pytest.mark.asyncio
    async def test_matching_service_error_logged_not_raised(
        self,
        mock_db: AsyncMock,
        studio_id,
        sample_rules: list[MatchingRule],
    ) -> None:
        """If matching service raises for one rule, job continues with next rule."""
        from app.jobs.matching_job import run_matching_job

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = sample_rules  # 2 rules
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_execute_result)

        with (
            patch("app.jobs.matching_job.normative_matching_service") as mock_matching_svc,
            patch("app.jobs.matching_job.notification_service") as mock_notif_svc,
            patch("app.jobs.matching_job.logger") as mock_logger,
        ):
            # First rule raises, second succeeds
            mock_matching_svc.match_rule_to_clients = AsyncMock(
                side_effect=[
                    RuntimeError("Errore DB temporaneo"),
                    [{"client_id": 5, "score": 0.85, "method": "structured"}],
                ]
            )
            mock_notif_svc.create_notification = AsyncMock()

            result = await run_matching_job(
                db=mock_db,
                studio_id=studio_id,
                knowledge_item_id=42,
            )

        # First rule failed, second succeeded
        assert result.rules_processed == 2
        assert result.matches_found == 1
        assert result.suggestions_created == 1
        # Error was logged
        mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_notification_failure_does_not_break_job(
        self,
        mock_db: AsyncMock,
        studio_id,
        sample_rules: list[MatchingRule],
    ) -> None:
        """Fire-and-forget: notification failure doesn't prevent suggestion creation."""
        from app.jobs.matching_job import run_matching_job

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = sample_rules[:1]
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_execute_result)

        with (
            patch("app.jobs.matching_job.normative_matching_service") as mock_matching_svc,
            patch("app.jobs.matching_job.notification_service") as mock_notif_svc,
            patch("app.jobs.matching_job.logger") as mock_logger,
        ):
            mock_matching_svc.match_rule_to_clients = AsyncMock(
                return_value=[
                    {"client_id": 1, "score": 0.90, "method": "structured"},
                    {"client_id": 2, "score": 0.85, "method": "structured"},
                ]
            )
            # Notification service fails for both
            mock_notif_svc.create_notification = AsyncMock(
                side_effect=RuntimeError("Servizio notifiche non disponibile")
            )

            result = await run_matching_job(
                db=mock_db,
                studio_id=studio_id,
                knowledge_item_id=42,
            )

        # Suggestions were still created despite notification failures
        assert result.suggestions_created == 2
        assert result.notifications_sent == 0
        # Notification errors logged as warnings
        assert mock_logger.warning.call_count >= 2

    @pytest.mark.asyncio
    async def test_multiple_rules_partial_failure(
        self,
        mock_db: AsyncMock,
        studio_id,
        sample_rules: list[MatchingRule],
    ) -> None:
        """One rule fails, one succeeds: job result reflects partial success."""
        from app.jobs.matching_job import run_matching_job

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = sample_rules
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_execute_result)

        with (
            patch("app.jobs.matching_job.normative_matching_service") as mock_matching_svc,
            patch("app.jobs.matching_job.notification_service") as mock_notif_svc,
        ):
            mock_matching_svc.match_rule_to_clients = AsyncMock(
                side_effect=[
                    ValueError("Regola di matching non trovata"),
                    [
                        {"client_id": 10, "score": 0.75, "method": "semantic"},
                    ],
                ]
            )
            mock_notif_svc.create_notification = AsyncMock()

            result = await run_matching_job(
                db=mock_db,
                studio_id=studio_id,
            )

        assert result.rules_processed == 2
        assert result.matches_found == 1
        assert result.suggestions_created == 1
        assert result.notifications_sent == 1
