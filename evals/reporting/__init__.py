"""Report generation for evaluation results.

Provides generators and delivery for evaluation reports:
- JSON: Machine-readable format
- HTML: Human-readable web format
- Delivery: Slack, Email, GitHub comment
"""

from evals.reporting.generators import (
    HTMLReportGenerator,
    JSONReportGenerator,
    generate_html_report,
    generate_json_report,
)

__all__ = [
    "JSONReportGenerator",
    "HTMLReportGenerator",
    "generate_json_report",
    "generate_html_report",
]
