#!/usr/bin/env python3
"""
Weekly Sandbox Security Review Script.

Parses sandbox log files and generates a security report.
Sends report via email to METRICS_REPORT_RECIPIENTS_ADMIN if configured.

Usage:
    python scripts/weekly_sandbox_review.py
    uv run python scripts/weekly_sandbox_review.py

    # With custom log directory
    python scripts/weekly_sandbox_review.py --log-dir /custom/path

    # Skip email notification (dry run)
    python scripts/weekly_sandbox_review.py --dry-run

Cron setup (Monday 9AM):
    0 9 * * 1 cd /Users/micky/PycharmProjects/PratikoAi-BE && uv run python scripts/weekly_sandbox_review.py
"""

import argparse
import json
import os
import smtplib
import sys
from collections import Counter
from datetime import UTC, datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def parse_log_file(log_path: Path, days: int = 7) -> list[dict]:
    """Parse a JSON lines log file.

    Args:
        log_path: Path to the log file
        days: Only include entries from the last N days

    Returns:
        List of parsed log entries
    """
    if not log_path.exists():
        return []

    cutoff = datetime.now(UTC) - timedelta(days=days)
    entries = []

    try:
        with open(log_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    # Parse timestamp if present
                    if "timestamp" in entry:
                        try:
                            ts = datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00"))
                            if ts < cutoff:
                                continue
                        except (ValueError, TypeError):
                            pass
                    entries.append(entry)
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"Warning: Error reading {log_path}: {e}")

    return entries


def analyze_network_logs(entries: list[dict]) -> dict:
    """Analyze network log entries.

    Returns:
        Dict with analysis results
    """
    allowed_domains: Counter[str] = Counter()
    blocked_domains: Counter[str] = Counter()
    blocked_details = []

    for entry in entries:
        entry_type = entry.get("type", "")
        domain = entry.get("domain", "unknown")

        if entry_type == "allowed":
            allowed_domains[domain] += 1
        elif entry_type == "blocked":
            blocked_domains[domain] += 1
            blocked_details.append(
                {
                    "domain": domain,
                    "reason": entry.get("reason", "unknown"),
                    "requested_by": entry.get("requested_by", "unknown"),
                    "timestamp": entry.get("timestamp", "unknown"),
                }
            )

    return {
        "allowed_domains": allowed_domains,
        "blocked_domains": blocked_domains,
        "blocked_details": blocked_details[:10],  # Limit to 10 most recent
        "total_allowed": sum(allowed_domains.values()),
        "total_blocked": sum(blocked_domains.values()),
    }


def analyze_filesystem_logs(entries: list[dict]) -> dict:
    """Analyze filesystem log entries.

    Returns:
        Dict with analysis results
    """
    blocked_paths: Counter[str] = Counter()
    blocked_details = []

    for entry in entries:
        if entry.get("type") == "blocked":
            path = entry.get("path", "unknown")
            blocked_paths[path] += 1
            blocked_details.append(
                {
                    "path": path,
                    "reason": entry.get("reason", "unknown"),
                    "requested_by": entry.get("requested_by", "unknown"),
                    "timestamp": entry.get("timestamp", "unknown"),
                }
            )

    return {
        "blocked_paths": blocked_paths,
        "blocked_details": blocked_details[:10],
        "total_blocked": sum(blocked_paths.values()),
    }


def generate_report(network_analysis: dict, filesystem_analysis: dict, days: int = 7) -> str:
    """Generate a formatted security report (plain text).

    Args:
        network_analysis: Results from analyze_network_logs
        filesystem_analysis: Results from analyze_filesystem_logs
        days: Number of days covered

    Returns:
        Formatted report string
    """
    report = []
    report.append("=" * 60)
    report.append("WEEKLY SANDBOX SECURITY REVIEW")
    report.append(f"Period: Last {days} days")
    report.append(f"Generated: {datetime.now(UTC).isoformat()}")
    report.append("=" * 60)
    report.append("")

    # Network summary
    report.append("NETWORK ACTIVITY")
    report.append("-" * 40)
    report.append(f"Total allowed requests: {network_analysis['total_allowed']}")
    report.append(f"Total blocked requests: {network_analysis['total_blocked']}")
    report.append("")

    if network_analysis["allowed_domains"]:
        report.append("Top allowed domains:")
        for domain, count in network_analysis["allowed_domains"].most_common(5):
            report.append(f"  {domain}: {count} requests")
        report.append("")

    if network_analysis["blocked_domains"]:
        report.append("BLOCKED DOMAINS (INVESTIGATE)")
        for domain, count in network_analysis["blocked_domains"].most_common(5):
            report.append(f"  {domain}: {count} attempts")
        report.append("")

    # Filesystem summary
    report.append("FILESYSTEM ACTIVITY")
    report.append("-" * 40)
    report.append(f"Total blocked access attempts: {filesystem_analysis['total_blocked']}")
    report.append("")

    if filesystem_analysis["blocked_paths"]:
        report.append("BLOCKED PATHS (INVESTIGATE)")
        for path, count in filesystem_analysis["blocked_paths"].most_common(5):
            report.append(f"  {path}: {count} attempts")
        report.append("")

    # Security assessment
    report.append("SECURITY ASSESSMENT")
    report.append("-" * 40)

    total_blocked = network_analysis["total_blocked"] + filesystem_analysis["total_blocked"]
    if total_blocked == 0:
        report.append("STATUS: NORMAL")
        report.append("No blocked attempts detected. Sandbox is working as expected.")
    elif total_blocked < 10:
        report.append("STATUS: LOW ACTIVITY")
        report.append(f"{total_blocked} blocked attempts. Review recommended.")
    elif total_blocked < 50:
        report.append("STATUS: MODERATE ACTIVITY")
        report.append(f"{total_blocked} blocked attempts. Investigation recommended.")
    else:
        report.append("STATUS: HIGH ACTIVITY - REVIEW IMMEDIATELY")
        report.append(f"{total_blocked} blocked attempts. Possible security concern.")

    report.append("")
    report.append("=" * 60)

    return "\n".join(report)


def generate_html_report(network_analysis: dict, filesystem_analysis: dict, days: int = 7) -> str:
    """Generate an HTML-formatted security report for email.

    Args:
        network_analysis: Results from analyze_network_logs
        filesystem_analysis: Results from analyze_filesystem_logs
        days: Number of days covered

    Returns:
        HTML-formatted report string
    """
    total_blocked = network_analysis["total_blocked"] + filesystem_analysis["total_blocked"]

    # Determine status
    if total_blocked == 0:
        status_color = "#28a745"  # green
        status_text = "NORMAL"
        status_icon = "✅"
    elif total_blocked < 10:
        status_color = "#ffc107"  # yellow
        status_text = "LOW ACTIVITY"
        status_icon = "⚠️"
    elif total_blocked < 50:
        status_color = "#fd7e14"  # orange
        status_text = "MODERATE ACTIVITY"
        status_icon = "⚠️"
    else:
        status_color = "#dc3545"  # red
        status_text = "HIGH ACTIVITY"
        status_icon = "🚨"

    current_time = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Weekly Sandbox Security Review</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
            .container {{ max-width: 800px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
            .header h1 {{ margin: 0; font-size: 24px; }}
            .header p {{ margin: 5px 0 0 0; opacity: 0.9; }}
            .status-badge {{ display: inline-block; padding: 8px 16px; border-radius: 20px; font-weight: bold; color: white; background-color: {status_color}; }}
            .section {{ margin-bottom: 20px; padding: 15px; background-color: #f8f9fa; border-radius: 6px; }}
            .section h3 {{ margin-top: 0; color: #495057; }}
            .metric {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #e9ecef; }}
            .metric:last-child {{ border-bottom: none; }}
            .blocked {{ background-color: #f8d7da; border: 1px solid #f5c6cb; }}
            .blocked h3 {{ color: #721c24; }}
            .domain-list {{ margin: 10px 0; padding-left: 20px; }}
            .domain-list li {{ margin: 5px 0; }}
            .footer {{ text-align: center; color: #6c757d; font-size: 12px; margin-top: 20px; padding-top: 20px; border-top: 1px solid #dee2e6; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>{status_icon} Weekly Sandbox Security Review</h1>
                <p>Period: Last {days} days | Generated: {current_time}</p>
            </div>

            <div style="text-align: center; margin-bottom: 20px;">
                <span class="status-badge">{status_text}</span>
            </div>

            <div class="section">
                <h3>🌐 Network Activity</h3>
                <div class="metric">
                    <span>Allowed requests:</span>
                    <strong>{network_analysis["total_allowed"]}</strong>
                </div>
                <div class="metric">
                    <span>Blocked requests:</span>
                    <strong style="color: {"#dc3545" if network_analysis["total_blocked"] > 0 else "#28a745"};">{network_analysis["total_blocked"]}</strong>
                </div>
    """

    if network_analysis["allowed_domains"]:
        html += """
                <h4>Top Allowed Domains:</h4>
                <ul class="domain-list">
        """
        for domain, count in network_analysis["allowed_domains"].most_common(5):
            html += f"<li>{domain}: {count} requests</li>"
        html += "</ul>"

    if network_analysis["blocked_domains"]:
        html += """
            </div>
            <div class="section blocked">
                <h3>🚫 Blocked Network Domains (Investigate)</h3>
                <ul class="domain-list">
        """
        for domain, count in network_analysis["blocked_domains"].most_common(5):
            html += f"<li><code>{domain}</code>: {count} attempts</li>"
        html += "</ul>"

    html += f"""
            </div>

            <div class="section">
                <h3>📁 Filesystem Activity</h3>
                <div class="metric">
                    <span>Blocked access attempts:</span>
                    <strong style="color: {"#dc3545" if filesystem_analysis["total_blocked"] > 0 else "#28a745"};">{filesystem_analysis["total_blocked"]}</strong>
                </div>
    """

    if filesystem_analysis["blocked_paths"]:
        html += """
            </div>
            <div class="section blocked">
                <h3>🚫 Blocked Filesystem Paths (Investigate)</h3>
                <ul class="domain-list">
        """
        for path, count in filesystem_analysis["blocked_paths"].most_common(5):
            html += f"<li><code>{path}</code>: {count} attempts</li>"
        html += "</ul>"

    html += """
            </div>

            <div class="footer">
                <p>This is an automated report from PratikoAI Sandbox Security Monitoring</p>
                <p>For configuration details, see .claude/docs/SANDBOXING_GUIDE.md</p>
            </div>
        </div>
    </body>
    </html>
    """

    return html


def send_email_notification(
    recipients: list[str],
    subject: str,
    html_content: str,
    text_content: str,
) -> bool:
    """Send security report via email.

    Args:
        recipients: List of email addresses
        subject: Email subject
        html_content: HTML version of the report
        text_content: Plain text version of the report

    Returns:
        True if successful, False otherwise
    """
    # Get SMTP settings from environment
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_username = os.environ.get("SMTP_USERNAME")
    smtp_password = os.environ.get("SMTP_PASSWORD")
    from_email = os.environ.get("FROM_EMAIL", "noreply@pratikoai.com")

    if not smtp_username or not smtp_password:
        print("Warning: SMTP credentials not configured. Email not sent.")
        print("Set SMTP_USERNAME and SMTP_PASSWORD environment variables.")
        return False

    if not recipients:
        print("Warning: No recipients configured. Email not sent.")
        return False

    try:
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_email
        msg["To"] = ", ".join(recipients)

        # Attach both plain text and HTML versions
        text_part = MIMEText(text_content, "plain")
        html_part = MIMEText(html_content, "html")
        msg.attach(text_part)
        msg.attach(html_part)

        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)

        return True

    except Exception as e:
        print(f"Error: Failed to send email: {e}")
        return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Generate weekly sandbox security review",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--log-dir",
        default="/tmp",
        help="Directory containing sandbox log files (default: /tmp)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to analyze (default: 7)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print report but don't send email",
    )
    args = parser.parse_args()

    log_dir = Path(args.log_dir)

    print(f"Analyzing sandbox logs from {log_dir}...")
    print(f"Period: Last {args.days} days")
    print()

    # Parse log files
    network_log = log_dir / "claude-sandbox-network.log"
    filesystem_log = log_dir / "claude-sandbox-filesystem.log"

    network_entries = parse_log_file(network_log, args.days)
    filesystem_entries = parse_log_file(filesystem_log, args.days)

    if not network_entries and not filesystem_entries:
        print("No sandbox log entries found.")
        print()
        print("This could mean:")
        print("  1. Sandbox has not been enabled yet (/sandbox)")
        print("  2. Log files are in a different location")
        print("  3. No activity in the specified period")
        print()
        print("Log files checked:")
        print(f"  - {network_log} (exists: {network_log.exists()})")
        print(f"  - {filesystem_log} (exists: {filesystem_log.exists()})")
        return 0

    # Analyze logs
    network_analysis = analyze_network_logs(network_entries)
    filesystem_analysis = analyze_filesystem_logs(filesystem_entries)

    # Generate and print report
    text_report = generate_report(network_analysis, filesystem_analysis, args.days)
    print(text_report)

    # Send email if configured
    recipients_str = os.environ.get("METRICS_REPORT_RECIPIENTS_ADMIN", "")
    recipients = [r.strip() for r in recipients_str.split(",") if r.strip()]

    if recipients and not args.dry_run:
        print("\nSending email report...")

        html_report = generate_html_report(network_analysis, filesystem_analysis, args.days)
        subject = f"PratikoAI Sandbox Security Review - {datetime.now(UTC).strftime('%Y-%m-%d')}"

        if send_email_notification(recipients, subject, html_report, text_report):
            print(f"Email sent successfully to: {', '.join(recipients)}")
        else:
            print("Failed to send email notification.")
    elif args.dry_run:
        print("\n[DRY RUN] Email notification skipped.")
    else:
        print("\nMETRICS_REPORT_RECIPIENTS_ADMIN not configured. Skipping email notification.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
