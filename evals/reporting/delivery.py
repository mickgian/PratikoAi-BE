"""Report delivery for evaluation results.

Delivers reports via:
- GitHub PR comments
- Slack notifications
- Email
"""

from datetime import datetime
from typing import Any

from evals.metrics.aggregate import AggregateMetrics


def format_pr_comment(
    metrics: AggregateMetrics,
    duration_seconds: float,
) -> str:
    """Format evaluation results as GitHub PR comment.

    Args:
        metrics: Aggregate metrics
        duration_seconds: Total duration

    Returns:
        Markdown-formatted comment
    """
    status = "✅" if metrics.overall_pass_rate >= 1.0 else "❌"

    # Build category table
    category_rows = ""
    for cat, cat_metrics in metrics.by_category.items():
        cat_status = "✅" if cat_metrics.pass_rate >= 1.0 else "❌"
        category_rows += (
            f"| {cat.value.title()} | {cat_metrics.passed} | "
            f"{cat_metrics.total} | {cat_metrics.pass_rate:.0%} {cat_status} |\n"
        )

    failures_section = ""
    if metrics.failures:
        failures_section = "\n### Failures\n\n"
        for failure in metrics.failures[:5]:  # Limit to 5
            failures_section += (
                f"- **{failure.test_case.id}** ({failure.test_case.category.value}): "
                f"score={failure.grade.score:.2f}\n"
            )

    return f"""## 🧪 Evaluation Results {status}

| Category | Passed | Total | Rate |
|----------|--------|-------|------|
{category_rows}| **Total** | **{metrics.passed}** | **{metrics.total}** | **{metrics.overall_pass_rate:.0%}** |

⏱️ Duration: {duration_seconds:.0f}s
{failures_section}
---
🤖 Generated with [Claude Code](https://claude.com/claude-code)
"""


def format_slack_message(
    metrics: AggregateMetrics,
    run_mode: str,
    report_url: str | None = None,
) -> dict[str, Any]:
    """Format evaluation results as Slack message.

    Args:
        metrics: Aggregate metrics
        run_mode: Run mode (nightly, weekly)
        report_url: Optional link to full report

    Returns:
        Slack message payload
    """
    status_emoji = ":white_check_mark:" if metrics.overall_pass_rate >= 1.0 else ":warning:"
    status_text = "Passed" if metrics.overall_pass_rate >= 1.0 else "Failed"

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{status_emoji} {run_mode.title()} Evaluation {status_text}",
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Pass Rate:*\n{metrics.overall_pass_rate:.0%}"},
                {"type": "mrkdwn", "text": f"*Total Tests:*\n{metrics.total}"},
                {"type": "mrkdwn", "text": f"*Passed:*\n{metrics.passed}"},
                {"type": "mrkdwn", "text": f"*Failed:*\n{metrics.failed}"},
            ],
        },
    ]

    if metrics.failures:
        failure_text = "\n".join(f"• {f.test_case.id}: {f.grade.score:.2f}" for f in metrics.failures[:3])
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Failures:*\n{failure_text}",
                },
            }
        )

    if report_url:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"<{report_url}|View Full Report>",
                },
            }
        )

    return {"blocks": blocks}


def format_email_body(
    metrics: AggregateMetrics,
    run_mode: str,
) -> str:
    """Format evaluation results as email body.

    Args:
        metrics: Aggregate metrics
        run_mode: Run mode

    Returns:
        HTML email body
    """
    status_emoji = "✅" if metrics.overall_pass_rate >= 1.0 else "⚠️"
    status_color = "#22c55e" if metrics.overall_pass_rate >= 1.0 else "#f59e0b"

    failures_html = ""
    if metrics.failures:
        failures_html = "<h3>Failures</h3><ul>"
        for f in metrics.failures[:5]:
            failures_html += f"<li><strong>{f.test_case.id}</strong>: score={f.grade.score:.2f}</li>"
        failures_html += "</ul>"

    return f"""
<html>
<body style="font-family: Arial, sans-serif;">
    <h1 style="color: {status_color};">
        {status_emoji} PratikoAI {run_mode.title()} Evaluation Report
    </h1>

    <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

    <table border="1" cellpadding="8" style="border-collapse: collapse;">
        <tr>
            <th>Metric</th>
            <th>Value</th>
        </tr>
        <tr>
            <td>Pass Rate</td>
            <td><strong>{metrics.overall_pass_rate:.0%}</strong></td>
        </tr>
        <tr>
            <td>Total Tests</td>
            <td>{metrics.total}</td>
        </tr>
        <tr>
            <td>Passed</td>
            <td>{metrics.passed}</td>
        </tr>
        <tr>
            <td>Failed</td>
            <td>{metrics.failed}</td>
        </tr>
    </table>

    {failures_html}

    <p style="color: #6b7280; font-size: 12px;">
        Generated by PratikoAI Evaluation Framework
    </p>
</body>
</html>
"""
