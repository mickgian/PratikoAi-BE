"""Tests for daily evaluation report scheduled task (DEV-252).

Tests the scheduled task function and registration for automatic daily
evaluation reports at 06:00 Europe/Rome timezone.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestSendDailyEvalReportTask:
    """Test send_daily_eval_report_task function."""

    @pytest.mark.asyncio
    async def test_task_skips_when_disabled(self):
        """Task should skip when EVAL_REPORT_ENABLED is false."""
        with patch("app.services.scheduler_service.settings") as mock_settings:
            mock_settings.EVAL_REPORT_ENABLED = False

            from app.services.scheduler_service import send_daily_eval_report_task

            # Should complete without error and not run evaluation
            with patch("app.services.scheduler_service.logger") as mock_logger:
                await send_daily_eval_report_task()
                mock_logger.info.assert_any_call("Daily evaluation report is disabled, skipping")

    @pytest.mark.asyncio
    async def test_task_skips_when_no_test_directory(self):
        """Task should skip gracefully when test directory doesn't exist."""
        with patch("app.services.scheduler_service.settings") as mock_settings:
            mock_settings.EVAL_REPORT_ENABLED = True

            from app.services.scheduler_service import send_daily_eval_report_task

            with (
                patch("evals.config.create_nightly_config"),
                patch("evals.runner.EvalRunner"),
                patch.object(Path, "exists", return_value=False),
                patch("app.services.scheduler_service.logger") as mock_logger,
            ):
                await send_daily_eval_report_task()
                # Should log warning about missing directory
                mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_task_skips_when_no_test_cases(self):
        """Task should skip gracefully when no test cases found."""
        with patch("app.services.scheduler_service.settings") as mock_settings:
            mock_settings.EVAL_REPORT_ENABLED = True

            from app.services.scheduler_service import send_daily_eval_report_task

            with (
                patch("evals.config.create_nightly_config"),
                patch("evals.runner.EvalRunner"),
                patch("evals.runner.load_test_cases", return_value=[]),  # No test cases
                patch.object(Path, "exists", return_value=True),
                patch("app.services.scheduler_service.logger") as mock_logger,
            ):
                await send_daily_eval_report_task()
                mock_logger.info.assert_any_call("No test cases found, skipping eval report")

    @pytest.mark.asyncio
    async def test_task_runs_evaluation_successfully(self):
        """Task should run evaluation and log results."""
        with patch("app.services.scheduler_service.settings") as mock_settings:
            mock_settings.EVAL_REPORT_ENABLED = True

            from app.services.scheduler_service import send_daily_eval_report_task

            # Mock the run result
            mock_result = MagicMock()
            mock_result.passed = 8
            mock_result.total = 10
            mock_result.pass_rate = 0.8

            mock_runner = AsyncMock()
            mock_runner.run.return_value = mock_result

            with (
                patch("evals.config.create_nightly_config"),
                patch("evals.runner.EvalRunner", return_value=mock_runner),
                patch("evals.runner.load_test_cases", return_value=["test1", "test2"]),
                patch.object(Path, "exists", return_value=True),
                patch("app.services.scheduler_service.logger") as mock_logger,
            ):
                await send_daily_eval_report_task()

                # Verify runner.run was called with test cases
                mock_runner.run.assert_called_once()

                # Verify success was logged
                mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_task_handles_evaluation_error(self):
        """Task should log error if evaluation fails."""
        with patch("app.services.scheduler_service.settings") as mock_settings:
            mock_settings.EVAL_REPORT_ENABLED = True

            from app.services.scheduler_service import send_daily_eval_report_task

            mock_runner = AsyncMock()
            mock_runner.run.side_effect = Exception("Eval failed")

            with (
                patch("evals.config.create_nightly_config"),
                patch("evals.runner.EvalRunner", return_value=mock_runner),
                patch("evals.runner.load_test_cases", return_value=["test1"]),
                patch.object(Path, "exists", return_value=True),
                patch("app.services.scheduler_service.logger") as mock_logger,
            ):
                # Should not raise, just log error
                await send_daily_eval_report_task()
                mock_logger.error.assert_called()


class TestEvalReportTaskRegistration:
    """Test that daily_eval_report task is properly registered in setup_default_tasks."""

    def test_eval_report_task_registered(self):
        """Daily eval report task should be registered with correct settings."""
        with (
            patch("app.services.scheduler_service.settings") as mock_settings,
            patch("app.services.scheduler_service.scheduler_service") as mock_scheduler,
        ):
            # Configure settings
            mock_settings.EVAL_REPORT_ENABLED = True
            mock_settings.EVAL_REPORT_TIME = "06:00"
            mock_settings.RSS_COLLECTION_TIME = "01:00"
            mock_settings.INGESTION_REPORT_ENABLED = True
            mock_settings.INGESTION_REPORT_TIME = "06:00"
            mock_settings.DAILY_COST_REPORT_ENABLED = True
            mock_settings.DAILY_COST_REPORT_TIME = "07:00"

            from app.services.scheduler_service import setup_default_tasks

            setup_default_tasks()

            # Find the daily_eval_report task in add_task calls
            add_task_calls = mock_scheduler.add_task.call_args_list
            eval_task_calls = [call for call in add_task_calls if call[0][0].name == "daily_eval_report"]

            assert len(eval_task_calls) == 1, "Should register daily_eval_report task"

            eval_task = eval_task_calls[0][0][0]
            assert eval_task.name == "daily_eval_report"
            assert eval_task.enabled is True
            assert eval_task.target_time == "06:00"

    def test_eval_report_task_disabled_when_setting_false(self):
        """Eval report task should be disabled when EVAL_REPORT_ENABLED=false."""
        with (
            patch("app.services.scheduler_service.settings") as mock_settings,
            patch("app.services.scheduler_service.scheduler_service") as mock_scheduler,
        ):
            mock_settings.EVAL_REPORT_ENABLED = False
            mock_settings.EVAL_REPORT_TIME = "06:00"
            mock_settings.RSS_COLLECTION_TIME = "01:00"
            mock_settings.INGESTION_REPORT_ENABLED = True
            mock_settings.INGESTION_REPORT_TIME = "06:00"
            mock_settings.DAILY_COST_REPORT_ENABLED = True
            mock_settings.DAILY_COST_REPORT_TIME = "07:00"

            from app.services.scheduler_service import setup_default_tasks

            setup_default_tasks()

            # Find the daily_eval_report task
            add_task_calls = mock_scheduler.add_task.call_args_list
            eval_task_calls = [call for call in add_task_calls if call[0][0].name == "daily_eval_report"]

            assert len(eval_task_calls) == 1
            eval_task = eval_task_calls[0][0][0]
            assert eval_task.enabled is False


class TestEvalReportTimeConfig:
    """Test EVAL_REPORT_TIME configuration setting."""

    def test_eval_report_time_in_settings(self):
        """Settings should include EVAL_REPORT_TIME."""
        with patch.dict("os.environ", {"EVAL_REPORT_TIME": "08:00"}):
            # Re-import to pick up new env var
            from importlib import reload

            import app.core.config

            reload(app.core.config)

            from app.core.config import Settings

            settings = Settings()
            assert settings.EVAL_REPORT_TIME == "08:00"

    def test_eval_report_time_default(self):
        """EVAL_REPORT_TIME should default to 06:00."""
        with patch.dict("os.environ", {}, clear=False):
            # Ensure EVAL_REPORT_TIME is not set
            import os

            if "EVAL_REPORT_TIME" in os.environ:
                del os.environ["EVAL_REPORT_TIME"]

            from importlib import reload

            import app.core.config

            reload(app.core.config)

            from app.core.config import Settings

            settings = Settings()
            assert settings.EVAL_REPORT_TIME == "06:00"
