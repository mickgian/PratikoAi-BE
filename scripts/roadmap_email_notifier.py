#!/usr/bin/env python3
"""
Roadmap Timeline Email Notifier

Sends email notifications to stakeholders when the roadmap timeline changes.

Usage:
    from roadmap_email_notifier import send_timeline_notification
    send_timeline_notification(timelines, blockers, tasks)
"""

import logging
import os
import smtplib
from datetime import datetime
from email.generator import BytesGenerator
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from io import BytesIO
from pathlib import Path
from typing import Dict, Optional

# Load environment variables from .env.development
try:
    from dotenv import load_dotenv

    env_file = Path(__file__).parent.parent / ".env.development"
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    pass

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def send_timeline_notification(combined_data: dict[str, any], recipient_email: str | None = None) -> bool:
    """
    Send email notification about updated roadmap timeline (both frontend and backend).

    Args:
        combined_data: Dictionary with keys:
            - backend: {timelines, blockers, tasks}
            - frontend: {timelines, blockers, tasks}
            - changes: {new_tasks, removed_tasks, timeline_changes}
        recipient_email: Override email recipients (defaults to env var, comma-separated)

    Returns:
        True if email sent successfully, False otherwise
    """
    # Get email configuration from environment
    recipients_str = recipient_email or os.getenv("ROADMAP_NOTIFICATION_EMAIL")
    auto_update_enabled = os.getenv("ROADMAP_AUTO_UPDATE", "true").lower() == "true"

    if not recipients_str:
        logger.warning("ROADMAP_NOTIFICATION_EMAIL not configured - skipping email notification")
        return False

    if not auto_update_enabled:
        logger.info("Roadmap auto-update disabled via ROADMAP_AUTO_UPDATE env var")
        return False

    # Parse multiple recipients (comma-separated)
    recipients = [r.strip() for r in recipients_str.split(",") if r.strip()]
    if not recipients:
        logger.warning("No valid email recipients found")
        return False

    # SMTP configuration
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME", "").strip()
    # Remove ALL spaces (including non-breaking spaces) from password
    # Gmail App Passwords work without spaces
    smtp_password = os.getenv("SMTP_PASSWORD", "").replace(" ", "").replace("\xa0", "").replace("\u00a0", "")
    from_email = os.getenv("FROM_EMAIL", "noreply@pratikoai.com")

    # Validate SMTP credentials
    if not smtp_username or not smtp_password:
        logger.warning("SMTP credentials not configured - skipping email notification")
        return False

    try:
        logger.info(f"📧 Preparing email notification to {len(recipients)} recipient(s): {', '.join(recipients)}")
        logger.info(f"   SMTP: {smtp_server}:{smtp_port}")
        logger.info(f"   From: {from_email}")

        # Generate email content
        subject = f"🗓️ Roadmap Timeline Updated - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        html_content = _generate_email_html(combined_data)
        logger.info("✅ Email content generated")

        # Create message
        message = MIMEMultipart("alternative")
        message["Subject"] = Header(subject, "utf-8")
        message["From"] = from_email
        message["To"] = ", ".join(recipients)

        # Attach HTML content with UTF-8 encoding
        html_part = MIMEText(html_content, "html", "utf-8")
        message.attach(html_part)
        logger.info("✅ Email message created")

        # Send email via SMTP using BytesGenerator for proper UTF-8 encoding
        logger.info("🔌 Connecting to SMTP server...")
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            logger.info("✅ Connected to SMTP")
            server.starttls()
            logger.info("✅ TLS started")
            server.login(smtp_username, smtp_password)
            logger.info("✅ SMTP login successful")
            # Use BytesGenerator to properly encode the message
            fp = BytesIO()
            g = BytesGenerator(fp, mangle_from_=False)
            g.flatten(message)
            logger.info("✅ Message flattened")
            server.sendmail(from_email, recipients, fp.getvalue())
            logger.info("✅ Email sent via SMTP")

        logger.info(f"✅ Timeline notification sent to {len(recipients)} recipient(s)")
        return True

    except Exception as e:
        import traceback

        logger.error(f"❌ Failed to send email notification: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False


def _generate_email_html(combined_data: dict[str, any]) -> str:
    """Generate unified HTML email content for frontend + backend timeline updates."""

    backend_data = combined_data.get("backend", {})
    frontend_data = combined_data.get("frontend", {})
    changes = combined_data.get("changes", {})

    backend_timelines = backend_data.get("timelines", {})
    backend_blockers = backend_data.get("blockers", [])
    backend_tasks = backend_data.get("tasks", {})

    frontend_timelines = frontend_data.get("timelines", {})
    frontend_blockers = frontend_data.get("blockers", [])
    frontend_tasks = frontend_data.get("tasks", {})

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Build HTML email
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Roadmap Timeline Update</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f4f4f4;
        }}
        .container {{
            max-width: 800px;
            margin: 20px auto;
            background-color: #ffffff;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0 0 10px 0;
            font-size: 28px;
            font-weight: 600;
        }}
        .header p {{
            margin: 0;
            opacity: 0.9;
            font-size: 14px;
        }}
        .content {{
            padding: 30px;
        }}
        .changes-section {{
            margin-bottom: 30px;
            padding: 20px;
            background-color: #f0f8ff;
            border-left: 4px solid #2196F3;
            border-radius: 4px;
        }}
        .changes-section h2 {{
            margin: 0 0 15px 0;
            font-size: 20px;
            color: #0d47a1;
        }}
        .change-item {{
            margin: 8px 0;
            padding: 8px;
            font-size: 14px;
        }}
        .change-new {{
            color: #2e7d32;
            background-color: #e8f5e9;
            padding: 6px 10px;
            border-radius: 4px;
            display: inline-block;
        }}
        .change-removed {{
            color: #c62828;
            background-color: #ffebee;
            padding: 6px 10px;
            border-radius: 4px;
            display: inline-block;
        }}
        .change-increase {{
            color: #d32f2f;
        }}
        .change-decrease {{
            color: #388e3c;
        }}
        .section-divider {{
            margin: 30px 0;
            padding: 15px;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            color: white;
            font-weight: 600;
            font-size: 18px;
            text-align: center;
            border-radius: 4px;
        }}
        .timeline-section {{
            margin-bottom: 20px;
            padding: 20px;
            background-color: #f9f9f9;
            border-left: 4px solid #667eea;
            border-radius: 4px;
        }}
        .timeline-section h3 {{
            margin: 0 0 15px 0;
            font-size: 18px;
            color: #333;
        }}
        .timeline-row {{
            margin: 8px 0;
            font-size: 14px;
            line-height: 1.6;
        }}
        .timeline-label {{
            font-weight: 600;
            color: #555;
        }}
        .timeline-value {{
            color: #667eea;
            font-weight: 600;
        }}
        .blocker-section {{
            margin-top: 20px;
            padding: 20px;
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            border-radius: 4px;
        }}
        .blocker-section h3 {{
            margin: 0 0 15px 0;
            font-size: 18px;
            color: #856404;
        }}
        .blocker-item {{
            margin: 10px 0;
            padding: 10px;
            background-color: #ffffff;
            border-radius: 4px;
            font-size: 14px;
        }}
        .footer {{
            padding: 20px;
            text-align: center;
            background-color: #f4f4f4;
            color: #666;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🗓️ Roadmap Timeline Updated</h1>
            <p>PratikoAI Frontend + Backend - {current_time}</p>
        </div>
        <div class="content">
"""

    # Add changes summary section
    if changes.get("new_tasks") or changes.get("removed_tasks") or changes.get("timeline_changes"):
        html += """
            <div class="changes-section">
                <h2>📊 Changes Summary</h2>
"""
        if changes.get("new_tasks"):
            html += f"""
                <div class="change-item">
                    <strong>🆕 New Tasks ({len(changes["new_tasks"])}):</strong><br/>
"""
            for task_id in changes["new_tasks"]:
                # Get task title from backend or frontend
                task_title = None
                if task_id in backend_tasks:
                    task_title = backend_tasks[task_id].title
                elif task_id in frontend_tasks:
                    task_title = frontend_tasks[task_id].title

                if task_title:
                    html += f"""                    <span class="change-new">{task_id}: {task_title}</span><br/>
"""
                else:
                    html += f"""                    <span class="change-new">{task_id}</span><br/>
"""
            html += """
                </div>
"""

        if changes.get("removed_tasks"):
            html += f"""
                <div class="change-item">
                    <strong>❌ Removed Tasks ({len(changes["removed_tasks"])}):</strong><br/>
"""
            for task_id in changes["removed_tasks"]:
                html += f"""                    <span class="change-removed">{task_id}</span><br/>
"""
            html += """
                </div>
"""

        if changes.get("timeline_changes"):
            html += """
                <div class="change-item">
                    <strong>📈 Timeline Changes:</strong><br/>
"""
            for _key, change in changes["timeline_changes"].items():
                repo = change["repository"].upper()
                env = change["environment"].upper()
                opt_change = change["optimistic_change"]
                cons_change = change["conservative_change"]

                opt_icon = "🔴" if opt_change > 0 else "🟢"
                opt_class = "change-increase" if opt_change > 0 else "change-decrease"
                cons_class = "change-increase" if cons_change > 0 else "change-decrease"

                html += f"""
                    {opt_icon} <strong>{repo} {env}:</strong>
                    Optimistic <span class="{opt_class}">{opt_change:+.1f}w</span>,
                    Conservative <span class="{cons_class}">{cons_change:+.1f}w</span><br/>
"""
            html += """
                </div>
"""
        html += """
            </div>
"""

    # Add Backend Timeline Section
    if backend_timelines:
        html += """
            <div class="section-divider">🔧 Backend Timeline</div>
"""
        for env_name, env_label in [
            ("qa", "QA Environment (DEV-75)"),
            ("preprod", "Preprod Environment (DEV-88)"),
            ("production", "Production Environment (DEV-90)"),
        ]:
            if env_name in backend_timelines:
                timeline = backend_timelines[env_name]
                html += f"""
            <div class="timeline-section">
                <h3>📅 {env_label}</h3>
                <div class="timeline-row">
                    <span class="timeline-label">Optimistic:</span>
                    <span class="timeline-value">~{timeline["optimistic_weeks"]:.0f}w ({timeline.get("optimistic_date_range", "N/A")})</span>
                </div>
                <div class="timeline-row">
                    <span class="timeline-label">Conservative:</span>
                    <span class="timeline-value">~{timeline["conservative_weeks"]:.0f}w ({timeline.get("conservative_date_range", "N/A")})</span>
                </div>
                <div class="timeline-row">
                    <span class="timeline-label">Critical path:</span>
                    <span class="timeline-value">{timeline["critical_path_days"]:.0f} days ({timeline["critical_path_days"] / 7:.1f} weeks)</span>
                </div>
            </div>
"""

    # Add Frontend Timeline Section
    if frontend_timelines:
        html += """
            <div class="section-divider">💻 Frontend Timeline</div>
"""
        for env_name, env_label in [
            ("qa", "QA Environment (DEV-005)"),
            ("preprod", "Preprod Environment (DEV-010)"),
            ("production", "Production Environment (DEV-010)"),
        ]:
            if env_name in frontend_timelines:
                timeline = frontend_timelines[env_name]
                html += f"""
            <div class="timeline-section">
                <h3>📅 {env_label}</h3>
                <div class="timeline-row">
                    <span class="timeline-label">Optimistic:</span>
                    <span class="timeline-value">~{timeline["optimistic_weeks"]:.0f}w ({timeline.get("optimistic_date_range", "N/A")})</span>
                </div>
                <div class="timeline-row">
                    <span class="timeline-label">Conservative:</span>
                    <span class="timeline-value">~{timeline["conservative_weeks"]:.0f}w ({timeline.get("conservative_date_range", "N/A")})</span>
                </div>
                <div class="timeline-row">
                    <span class="timeline-label">Critical path:</span>
                    <span class="timeline-value">{timeline["critical_path_days"]:.0f} days ({timeline["critical_path_days"] / 7:.1f} weeks)</span>
                </div>
            </div>
"""

    # Add Blockers Section
    all_blockers = []
    if backend_blockers:
        all_blockers.extend([{**b, "source": "Backend"} for b in backend_blockers])
    if frontend_blockers:
        all_blockers.extend([{**b, "source": "Frontend"} for b in frontend_blockers])

    if all_blockers:
        html += f"""
            <div class="blocker-section">
                <h3>⚠️ Critical Blockers ({len(all_blockers)})</h3>
"""
        for blocker in all_blockers:
            html += f"""
                <div class="blocker-item">
                    <strong>[{blocker.get("source", "Unknown")}] {blocker["id"]}</strong>: {blocker.get("title", "N/A")}<br/>
                    <span style="color: #666;">{blocker["reason"]}</span>
                </div>
"""
        html += """
            </div>
"""

    html += """
        </div>
        <div class="footer">
            <p>This is an automated notification from the PratikoAI roadmap timeline tracker.</p>
            <p>Backend: /Users/micky/PycharmProjects/PratikoAi-BE/ARCHITECTURE_ROADMAP.md</p>
            <p>Frontend: /Users/micky/WebstormProjects/PratikoAiWebApp/ARCHITECTURE_ROADMAP.md</p>
        </div>
    </div>
</body>
</html>
"""

    return html


if __name__ == "__main__":
    # Example usage for testing
    from dataclasses import dataclass

    @dataclass
    class MockTask:
        title: str
        effort_days_avg: float
        is_deployment: bool = False
        is_gdpr_audit: bool = False
        priority: str = "MEDIUM"

    test_combined_data = {
        "backend": {
            "timelines": {
                "qa": {
                    "optimistic_weeks": 3.5,
                    "conservative_weeks": 5.2,
                    "prerequisites": ["DEV-67", "DEV-68"],
                    "critical_path_days": 24.5,
                    "optimistic_date_range": "15 Nov - 6 Dec",
                    "conservative_date_range": "15 Nov - 20 Dec",
                },
                "preprod": {
                    "optimistic_weeks": 6.8,
                    "conservative_weeks": 10.2,
                    "prerequisites": ["DEV-75", "DEV-87"],
                    "critical_path_days": 47.6,
                    "optimistic_date_range": "15 Nov - 27 Dec",
                    "conservative_date_range": "15 Nov - 24 Gen",
                },
                "production": {
                    "optimistic_weeks": 7.5,
                    "conservative_weeks": 11.2,
                    "prerequisites": ["DEV-88", "DEV-89"],
                    "critical_path_days": 52.5,
                    "optimistic_date_range": "15 Nov - 3 Gen",
                    "conservative_date_range": "15 Nov - 31 Gen",
                },
            },
            "blockers": [
                {"id": "DEV-87", "title": "Payment System", "reason": "Blocks Preprod/Production deployment"},
                {"id": "DEV-72", "title": "Expert Feedback", "reason": "Blocks QA deployment"},
            ],
            "tasks": {
                "DEV-67": MockTask("Migrate FAQ Embeddings", 14),
                "DEV-68": MockTask("Implement RAG System", 10),
                "DEV-75": MockTask("Deploy QA Environment", 3, is_deployment=True),
                "DEV-87": MockTask("Payment Management", 7, priority="CRITICAL"),
            },
        },
        "frontend": {
            "timelines": {
                "qa": {
                    "optimistic_weeks": 2.5,
                    "conservative_weeks": 3.5,
                    "critical_path_days": 17.5,
                    "optimistic_date_range": "15 Nov - 29 Nov",
                    "conservative_date_range": "15 Nov - 6 Dec",
                }
            },
            "blockers": [{"id": "DEV-004", "title": "Expert Feedback UI", "reason": "Blocks QA deployment"}],
            "tasks": {
                "DEV-002": MockTask("Adjust UI for Citations", 4),
                "DEV-004": MockTask("Expert Feedback System", 7),
            },
        },
        "changes": {
            "new_tasks": ["DEV-87"],
            "removed_tasks": [],
            "timeline_changes": {
                "backend_qa": {
                    "environment": "qa",
                    "repository": "backend",
                    "optimistic_change": 0.5,
                    "conservative_change": 0.7,
                    "old_optimistic": 3.0,
                    "new_optimistic": 3.5,
                    "old_conservative": 4.5,
                    "new_conservative": 5.2,
                }
            },
        },
    }

    send_timeline_notification(test_combined_data)
