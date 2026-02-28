"""Report generators for evaluation results.

Generates JSON and HTML reports from aggregate metrics.
"""

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from evals.metrics.aggregate import AggregateMetrics
from evals.schemas.test_case import TestCaseResult


class JSONReportGenerator:
    """Generate JSON reports from evaluation results."""

    def generate(
        self,
        metrics: AggregateMetrics,
        results: list[TestCaseResult],
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate JSON report data.

        Args:
            metrics: Aggregate metrics
            results: Individual test case results
            config: Optional configuration used for the run

        Returns:
            Dict containing report data
        """
        return {
            "run_id": f"eval-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_cases": metrics.total,
                "passed": metrics.passed,
                "failed": metrics.failed,
                "pass_rate": metrics.overall_pass_rate,
                "mean_score": metrics.overall_mean_score,
                "total_duration_ms": metrics.total_duration_ms,
                "mean_duration_ms": metrics.mean_duration_ms,
            },
            "by_category": {
                cat.value: {
                    "total": cat_metrics.total,
                    "passed": cat_metrics.passed,
                    "failed": cat_metrics.failed,
                    "pass_rate": cat_metrics.pass_rate,
                    "mean_score": cat_metrics.mean_score,
                    "min_score": cat_metrics.min_score,
                    "max_score": cat_metrics.max_score,
                }
                for cat, cat_metrics in metrics.by_category.items()
            },
            "failures": [
                {
                    "case_id": r.test_case.id,
                    "category": r.test_case.category.value,
                    "query": r.test_case.query[:200],  # Truncate long queries
                    "score": r.grade.score,
                    "reasoning": r.grade.reasoning,
                    "is_regression": r.test_case.is_regression,
                }
                for r in metrics.failures
            ],
            "regressions_detected": [
                {
                    "case_id": r.test_case.id,
                    "category": r.test_case.category.value,
                    "score": r.grade.score,
                }
                for r in metrics.regressions_detected
            ],
            "config": config or {},
        }

    def save(
        self,
        report_data: dict[str, Any],
        output_path: Path,
    ) -> Path:
        """Save report to JSON file.

        Args:
            report_data: Report data dict
            output_path: Path to save file

        Returns:
            Path to saved file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(report_data, f, indent=2)
        return output_path


class HTMLReportGenerator:
    """Generate HTML reports from evaluation results."""

    def generate(
        self,
        metrics: AggregateMetrics,
        results: list[TestCaseResult],
        title: str = "PratikoAI Evaluation Report",
    ) -> str:
        """Generate HTML report.

        Args:
            metrics: Aggregate metrics
            results: Individual test case results
            title: Report title

        Returns:
            HTML string
        """
        status_emoji = "✅" if metrics.overall_pass_rate >= 1.0 else "⚠️"
        status_color = "#22c55e" if metrics.overall_pass_rate >= 1.0 else "#f59e0b"

        # Build category table rows
        category_rows = ""
        for cat, cat_metrics in metrics.by_category.items():
            cat_status = "✅" if cat_metrics.pass_rate >= 1.0 else "❌"
            category_rows += f"""
            <tr>
                <td>{cat.value.title()}</td>
                <td>{cat_metrics.passed}</td>
                <td>{cat_metrics.total}</td>
                <td>{cat_metrics.pass_rate:.0%} {cat_status}</td>
            </tr>
            """

        # Build failures list
        failures_html = ""
        if metrics.failures:
            failures_html = "<h2>Failures</h2><ul>"
            for failure in metrics.failures[:10]:  # Limit to 10
                failures_html += f"""
                <li>
                    <strong>{failure.test_case.id}</strong>
                    ({failure.test_case.category.value})<br>
                    <small>Score: {failure.grade.score:.2f}</small><br>
                    <small>{failure.grade.reasoning[:200]}...</small>
                </li>
                """
            failures_html += "</ul>"

        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: #f8fafc;
        }}
        h1 {{ color: #1e293b; }}
        .summary {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .summary h2 {{
            margin-top: 0;
            color: {status_color};
        }}
        .stat {{
            display: inline-block;
            margin-right: 30px;
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: bold;
            color: #1e293b;
        }}
        .stat-label {{
            color: #64748b;
            font-size: 14px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        th, td {{
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }}
        th {{
            background: #f1f5f9;
            font-weight: 600;
            color: #475569;
        }}
        .timestamp {{
            color: #94a3b8;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <h1>{status_emoji} {title}</h1>
    <p class="timestamp">Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>

    <div class="summary">
        <h2>Overall: {metrics.overall_pass_rate:.0%}</h2>
        <div class="stat">
            <div class="stat-value">{metrics.total}</div>
            <div class="stat-label">Total</div>
        </div>
        <div class="stat">
            <div class="stat-value">{metrics.passed}</div>
            <div class="stat-label">Passed</div>
        </div>
        <div class="stat">
            <div class="stat-value">{metrics.failed}</div>
            <div class="stat-label">Failed</div>
        </div>
        <div class="stat">
            <div class="stat-value">{metrics.total_duration_ms / 1000:.1f}s</div>
            <div class="stat-label">Duration</div>
        </div>
    </div>

    <h2>Results by Category</h2>
    <table>
        <thead>
            <tr>
                <th>Category</th>
                <th>Passed</th>
                <th>Total</th>
                <th>Rate</th>
            </tr>
        </thead>
        <tbody>
            {category_rows}
        </tbody>
    </table>

    {failures_html}

    <footer style="margin-top: 40px; color: #94a3b8; font-size: 12px;">
        Generated by PratikoAI Evaluation Framework
    </footer>
</body>
</html>
"""

    def save(
        self,
        html: str,
        output_path: Path,
    ) -> Path:
        """Save HTML report to file.

        Args:
            html: HTML content
            output_path: Path to save file

        Returns:
            Path to saved file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(html)
        return output_path


def generate_json_report(
    metrics: AggregateMetrics,
    results: list[TestCaseResult],
    output_path: Path,
    config: dict[str, Any] | None = None,
) -> Path:
    """Convenience function to generate and save JSON report.

    Args:
        metrics: Aggregate metrics
        results: Individual results
        output_path: Path to save file
        config: Optional config dict

    Returns:
        Path to saved file
    """
    generator = JSONReportGenerator()
    data = generator.generate(metrics, results, config)
    return generator.save(data, output_path)


def generate_html_report(
    metrics: AggregateMetrics,
    results: list[TestCaseResult],
    output_path: Path,
    title: str = "PratikoAI Evaluation Report",
) -> Path:
    """Convenience function to generate and save HTML report.

    Args:
        metrics: Aggregate metrics
        results: Individual results
        output_path: Path to save file
        title: Report title

    Returns:
        Path to saved file
    """
    generator = HTMLReportGenerator()
    html = generator.generate(metrics, results, title)
    return generator.save(html, output_path)
