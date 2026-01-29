"""Email delivery for evaluation reports.

Integrates with existing EmailService infrastructure to send
nightly and weekly evaluation reports.
"""

import logging
from datetime import datetime

from app.core.config import settings
from app.services.email_service import EmailService
from evals.metrics.aggregate import AggregateMetrics
from evals.reporting.delivery import format_email_body

logger = logging.getLogger(__name__)


class EvalReportEmailService:
    """Send evaluation reports via email using existing infrastructure."""

    def __init__(self):
        self.email_service = EmailService()
        self.recipients = self._get_recipients()

    def _get_recipients(self) -> list[str]:
        """Get email recipients from settings."""
        recipients_str = getattr(settings, "EVAL_REPORT_RECIPIENTS", "")
        if recipients_str:
            return [r.strip() for r in recipients_str.split(",") if r.strip()]
        # Fallback to stakeholder email
        stakeholder = getattr(settings, "STAKEHOLDER_EMAIL", "")
        return [stakeholder] if stakeholder else []

    async def send_eval_report(
        self,
        metrics: AggregateMetrics,
        run_mode: str,
    ) -> bool:
        """Send evaluation report email.

        Args:
            metrics: Aggregate evaluation metrics
            run_mode: Run mode (nightly, weekly)

        Returns:
            True if email sent successfully
        """
        if not self.recipients:
            logger.warning("No email recipients configured for eval reports")
            return False

        if not getattr(settings, "EVAL_REPORT_ENABLED", True):
            logger.info("Eval report emails disabled")
            return True

        html_content = format_email_body(metrics, run_mode)
        subject = f"PratikoAI {run_mode.title()} Eval Report - {datetime.now().strftime('%Y-%m-%d')}"

        success = True
        for recipient in self.recipients:
            result = await self.email_service._send_email(
                recipient_email=recipient,
                subject=subject,
                html_content=html_content,
            )
            if not result:
                logger.error(f"Failed to send eval report to {recipient}")
                success = False
            else:
                logger.info(f"Eval report sent to {recipient}")

        return success


# Global instance
eval_email_service = EvalReportEmailService()
