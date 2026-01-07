"""Action Quality Metrics Service (DEV-240).

Tracks action quality metrics including:
- Validation pass rate: % of actions passing validation
- Regeneration rate: % of requests requiring action regeneration
- Click-through rate: % of displayed actions that get clicked

Coverage Target: 90%+ for new code.
"""

from __future__ import annotations

import threading
from datetime import datetime
from typing import Any

from app.core.logging import logger


class ActionQualityMetrics:
    """Service for tracking and reporting action quality metrics.

    Tracks:
    - Validation pass rate (from ActionValidator)
    - Regeneration rate (from ActionRegenerator)
    - Click-through rate (from user interactions)

    Thread-safe for concurrent access.
    """

    def __init__(self):
        """Initialize action quality metrics."""
        self._lock = threading.Lock()
        self._start_time = datetime.utcnow()
        self._reset_counters()

    def _reset_counters(self) -> None:
        """Reset all counters to zero."""
        # Validation metrics
        self._total_validations = 0
        self._total_actions_validated = 0
        self._total_actions_passed = 0
        self._total_actions_rejected = 0

        # Regeneration metrics
        self._total_requests = 0
        self._regenerations_triggered = 0
        self._regeneration_successes = 0
        self._regeneration_failures = 0

        # Click metrics
        self._actions_displayed = 0
        self._actions_clicked = 0

    def record_validation_result(
        self,
        total_actions: int,
        valid_actions: int,
        rejected_actions: int,
    ) -> None:
        """Record the result of an action validation batch.

        Args:
            total_actions: Total number of actions validated
            valid_actions: Number of actions that passed validation
            rejected_actions: Number of actions that failed validation
        """
        with self._lock:
            self._total_validations += 1
            self._total_actions_validated += total_actions
            self._total_actions_passed += valid_actions
            self._total_actions_rejected += rejected_actions

        logger.debug(
            "action_quality_validation_recorded",
            total_actions=total_actions,
            valid_actions=valid_actions,
            rejected_actions=rejected_actions,
        )

    def record_regeneration_attempt(
        self,
        triggered: bool,
        attempt_number: int = 0,
        success: bool = True,
    ) -> None:
        """Record a regeneration attempt or skip.

        Args:
            triggered: Whether regeneration was triggered
            attempt_number: Which attempt number (0 if not triggered)
            success: Whether regeneration succeeded (only relevant if triggered)
        """
        with self._lock:
            self._total_requests += 1

            if triggered:
                self._regenerations_triggered += 1
                if success:
                    self._regeneration_successes += 1
                else:
                    self._regeneration_failures += 1

        logger.debug(
            "action_quality_regeneration_recorded",
            triggered=triggered,
            attempt_number=attempt_number,
            success=success,
        )

    def record_actions_displayed(self, count: int) -> None:
        """Record number of actions displayed to user.

        Args:
            count: Number of actions displayed
        """
        with self._lock:
            self._actions_displayed += count

        logger.debug("action_quality_displayed_recorded", count=count)

    def record_action_clicked(self) -> None:
        """Record that a user clicked on an action."""
        with self._lock:
            self._actions_clicked += 1

        logger.debug("action_quality_click_recorded")

    def get_validation_summary(self) -> dict[str, Any]:
        """Get validation metrics summary.

        Returns:
            Dict with validation metrics
        """
        with self._lock:
            total_actions = self._total_actions_validated
            passed = self._total_actions_passed

            pass_rate = passed / total_actions if total_actions > 0 else 0.0

            return {
                "total_validations": self._total_validations,
                "total_actions": total_actions,
                "actions_passed": passed,
                "actions_rejected": self._total_actions_rejected,
                "pass_rate": pass_rate,
            }

    def get_regeneration_summary(self) -> dict[str, Any]:
        """Get regeneration metrics summary.

        Returns:
            Dict with regeneration metrics
        """
        with self._lock:
            total = self._total_requests
            triggered = self._regenerations_triggered
            successes = self._regeneration_successes

            regen_rate = triggered / total if total > 0 else 0.0
            success_rate = successes / triggered if triggered > 0 else 0.0

            return {
                "total_requests": total,
                "regenerations_triggered": triggered,
                "regeneration_rate": regen_rate,
                "regeneration_successes": successes,
                "regeneration_failures": self._regeneration_failures,
                "regeneration_success_rate": success_rate,
            }

    def get_click_summary(self) -> dict[str, Any]:
        """Get click metrics summary.

        Returns:
            Dict with click metrics
        """
        with self._lock:
            displayed = self._actions_displayed
            clicked = self._actions_clicked

            ctr = clicked / displayed if displayed > 0 else 0.0

            return {
                "actions_displayed": displayed,
                "actions_clicked": clicked,
                "click_through_rate": ctr,
            }

    def get_dashboard_summary(self) -> dict[str, Any]:
        """Get complete dashboard summary with all metrics.

        Returns:
            Complete dashboard data with all sections
        """
        return {
            "period_start": self._start_time.isoformat(),
            "period_end": datetime.utcnow().isoformat(),
            "validation": self.get_validation_summary(),
            "regeneration": self.get_regeneration_summary(),
            "clicks": self.get_click_summary(),
        }

    def reset(self) -> None:
        """Reset all metrics to zero and update start time."""
        with self._lock:
            self._reset_counters()
            self._start_time = datetime.utcnow()

        logger.info("action_quality_metrics_reset")


# Global singleton instance
_action_quality_metrics: ActionQualityMetrics | None = None


def get_action_quality_metrics() -> ActionQualityMetrics:
    """Get the global ActionQualityMetrics instance.

    Returns:
        ActionQualityMetrics singleton
    """
    global _action_quality_metrics
    if _action_quality_metrics is None:
        _action_quality_metrics = ActionQualityMetrics()
    return _action_quality_metrics
