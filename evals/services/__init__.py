"""Services for the evaluation framework.

Provides integration with existing PratikoAI infrastructure:
- Email delivery for nightly/weekly evaluation reports
- System invocation for RAG pipeline testing
"""

from evals.services.email_delivery import EvalReportEmailService, eval_email_service
from evals.services.system_invoker import SystemInvoker

__all__ = ["EvalReportEmailService", "eval_email_service", "SystemInvoker"]
