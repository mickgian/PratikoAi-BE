"""Email Service for Automated Reporting

This service handles automated email reporting for system metrics across all environments.
Supports HTML email templates, scheduled reports, and multi-environment monitoring.
"""

import asyncio
import logging
import os
import smtplib
from dataclasses import asdict
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.services.metrics_service import Environment, MetricsReport, MetricsService, MetricStatus

logger = logging.getLogger(__name__)


class EmailService:
    """Email service for automated reporting."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.metrics_service = MetricsService()

        # Email configuration
        self.smtp_server = settings.SMTP_SERVER if hasattr(settings, "SMTP_SERVER") else "smtp.gmail.com"
        self.smtp_port = settings.SMTP_PORT if hasattr(settings, "SMTP_PORT") else 587
        self.smtp_username = settings.SMTP_USERNAME if hasattr(settings, "SMTP_USERNAME") else None
        self.smtp_password = settings.SMTP_PASSWORD if hasattr(settings, "SMTP_PASSWORD") else None
        self.from_email = settings.FROM_EMAIL if hasattr(settings, "FROM_EMAIL") else "noreply@pratikoai.com"

    async def send_metrics_report(self, recipient_emails: list[str], environments: list[Environment]) -> bool:
        """Send comprehensive metrics report for all specified environments to multiple recipients."""
        try:
            # Validate recipient emails
            if not recipient_emails:
                self.logger.error("No recipient emails provided, skipping email")
                return False

            # Collect metrics for all environments
            reports = {}
            for env in environments:
                try:
                    report = await self.metrics_service.generate_metrics_report(env)
                    reports[env.value] = report
                    self.logger.info(f"Generated metrics report for {env.value}")
                except Exception as e:
                    self.logger.error(f"Failed to generate report for {env.value}: {e}")
                    continue

            if not reports:
                self.logger.error("No reports generated, skipping email")
                return False

            # Generate HTML email content
            html_content = self._generate_html_report(reports)
            subject = f"PratikoAI System Metrics Report - {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"

            # Send email to all recipients
            all_success = True
            for recipient_email in recipient_emails:
                success = await self._send_email(
                    recipient_email=recipient_email, subject=subject, html_content=html_content
                )

                if success:
                    self.logger.info(f"Metrics report sent successfully to {recipient_email}")
                else:
                    self.logger.error(f"Failed to send metrics report to {recipient_email}")
                    all_success = False

            return all_success

        except Exception as e:
            self.logger.error(f"Error sending metrics report: {e}")
            return False

    def _generate_html_report(self, reports: dict[str, MetricsReport]) -> str:
        """Generate HTML email content from metrics reports."""
        current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>NormoAI System Metrics Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .header p {{ margin: 5px 0 0 0; opacity: 0.9; }}
                .environment {{ margin-bottom: 30px; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; }}
                .env-header {{ background-color: #f8f9fa; padding: 15px; border-bottom: 1px solid #ddd; }}
                .env-header h2 {{ margin: 0; color: #333; text-transform: capitalize; }}
                .health-score {{ display: inline-block; margin-left: 10px; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 14px; }}
                .health-excellent {{ background-color: #d4edda; color: #155724; }}
                .health-good {{ background-color: #fff3cd; color: #856404; }}
                .health-poor {{ background-color: #f8d7da; color: #721c24; }}
                .metrics-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; padding: 20px; }}
                .metrics-section {{ background-color: #f8f9fa; padding: 15px; border-radius: 6px; }}
                .metrics-section h3 {{ margin-top: 0; color: #495057; }}
                .metric {{ display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #e9ecef; }}
                .metric:last-child {{ border-bottom: none; }}
                .metric-name {{ font-weight: 500; }}
                .metric-value {{ display: flex; align-items: center; gap: 8px; }}
                .status-pass {{ color: #28a745; font-weight: bold; }}
                .status-fail {{ color: #dc3545; font-weight: bold; }}
                .status-warning {{ color: #ffc107; font-weight: bold; }}
                .status-unknown {{ color: #6c757d; font-weight: bold; }}
                .alerts {{ background-color: #f8d7da; border: 1px solid #f5c6cb; border-radius: 6px; padding: 15px; margin: 20px; }}
                .alerts h3 {{ margin-top: 0; color: #721c24; }}
                .alert-item {{ margin: 5px 0; color: #721c24; }}
                .recommendations {{ background-color: #d1ecf1; border: 1px solid #bee5eb; border-radius: 6px; padding: 15px; margin: 20px; }}
                .recommendations h3 {{ margin-top: 0; color: #0c5460; }}
                .recommendation-item {{ margin: 8px 0; color: #0c5460; }}
                .summary {{ background-color: #e2e3e5; padding: 15px; border-radius: 6px; margin: 20px 0; }}
                .footer {{ text-align: center; color: #6c757d; font-size: 12px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚀 PratikoAI System Metrics Report</h1>
                    <p>Generated on {current_time}</p>
                </div>
        """

        # Add summary section
        html += self._generate_summary_section(reports)

        # Add environment sections
        for env_name, report in reports.items():
            html += self._generate_environment_section(env_name, report)

        html += """
                <div class="footer">
                    <p>This is an automated report generated by PratikoAI System Monitoring</p>
                    <p>For technical support, contact the development team</p>
                </div>
            </div>
        </body>
        </html>
        """

        return html

    def _generate_summary_section(self, reports: dict[str, MetricsReport]) -> str:
        """Generate summary section for all environments."""
        total_environments = len(reports)
        healthy_environments = sum(1 for report in reports.values() if report.overall_health_score >= 90)

        html = f"""
        <div class="summary">
            <h2>📊 Overall System Health</h2>
            <p><strong>Environments Monitored:</strong> {total_environments}</p>
            <p><strong>Healthy Environments:</strong> {healthy_environments}/{total_environments}</p>
            <div style="margin-top: 15px;">
        """

        for env_name, report in reports.items():
            health_class = self._get_health_class(report.overall_health_score)
            html += f"""
                <div style="display: inline-block; margin: 5px 10px 5px 0;">
                    <strong>{env_name.title()}:</strong>
                    <span class="health-score {health_class}">{report.overall_health_score:.1f}%</span>
                </div>
            """

        html += """
            </div>
        </div>
        """

        return html

    def _generate_environment_section(self, env_name: str, report: MetricsReport) -> str:
        """Generate HTML section for a single environment."""
        health_class = self._get_health_class(report.overall_health_score)

        html = f"""
        <div class="environment">
            <div class="env-header">
                <h2>{env_name.title()} Environment</h2>
                <span class="health-score {health_class}">Health Score: {report.overall_health_score:.1f}%</span>
            </div>
            <div class="metrics-grid">
                <div class="metrics-section">
                    <h3>🔧 Technical Metrics</h3>
        """

        # Add technical metrics
        for metric in report.technical_metrics:
            status_class = f"status-{metric.status.value.lower()}"
            html += f"""
                    <div class="metric">
                        <span class="metric-name">{metric.name}</span>
                        <div class="metric-value">
                            <span>{metric.value:.1f} {metric.unit}</span>
                            <span class="{status_class}">{metric.status.value}</span>
                        </div>
                    </div>
            """

        html += """
                </div>
                <div class="metrics-section">
                    <h3>💼 Business Metrics</h3>
        """

        # Add business metrics
        for metric in report.business_metrics:
            status_class = f"status-{metric.status.value.lower()}"
            html += f"""
                    <div class="metric">
                        <span class="metric-name">{metric.name}</span>
                        <div class="metric-value">
                            <span>{metric.value:.1f} {metric.unit}</span>
                            <span class="{status_class}">{metric.status.value}</span>
                        </div>
                    </div>
            """

        html += """
                </div>
            </div>
        """

        # Add alerts if any
        if report.alerts:
            html += """
            <div class="alerts">
                <h3>🚨 Alerts</h3>
            """
            for alert in report.alerts:
                html += f'<div class="alert-item">• {alert}</div>'
            html += "</div>"

        # Add recommendations if any
        if report.recommendations:
            html += """
            <div class="recommendations">
                <h3>💡 Recommendations</h3>
            """
            for recommendation in report.recommendations:
                html += f'<div class="recommendation-item">• {recommendation}</div>'
            html += "</div>"

        html += "</div>"

        return html

    def _get_health_class(self, health_score: float) -> str:
        """Get CSS class for health score."""
        if health_score >= 90:
            return "health-excellent"
        elif health_score >= 70:
            return "health-good"
        else:
            return "health-poor"

    async def send_welcome_email(self, recipient_email: str, password: str) -> bool:
        """Send welcome email with credentials after registration."""
        try:
            login_url = os.getenv("FRONTEND_URL", "http://localhost:3000") + "/login"
            subject = "Benvenuto su PratikoAI - Le tue credenziali"
            html_content = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;margin:0;padding:20px;background:#f5f5f5;">
  <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:8px;
              box-shadow:0 2px 4px rgba(0,0,0,.1);overflow:hidden;">
    <div style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);
                color:#fff;padding:30px;text-align:center;">
      <h1 style="margin:0;">Benvenuto su PratikoAI</h1>
    </div>
    <div style="padding:30px;">
      <p>Ciao,</p>
      <p>Il tuo account è stato creato con successo. Ecco le tue credenziali di accesso:</p>
      <table style="width:100%;border-collapse:collapse;margin:20px 0;">
        <tr>
          <td style="padding:10px;border:1px solid #ddd;font-weight:bold;background:#f8f9fa;">
            Email (username)
          </td>
          <td style="padding:10px;border:1px solid #ddd;">{recipient_email}</td>
        </tr>
        <tr>
          <td style="padding:10px;border:1px solid #ddd;font-weight:bold;background:#f8f9fa;">
            Password
          </td>
          <td style="padding:10px;border:1px solid #ddd;">{password}</td>
        </tr>
      </table>
      <p style="text-align:center;margin:30px 0;">
        <a href="{login_url}"
           style="background:#667eea;color:#fff;padding:12px 30px;border-radius:6px;
                  text-decoration:none;font-weight:bold;">Accedi a PratikoAI</a>
      </p>
      <p style="color:#6c757d;font-size:13px;">
        Ti consigliamo di conservare questa email e di cambiare la password al primo accesso.
      </p>
    </div>
    <div style="text-align:center;color:#6c757d;font-size:12px;padding:15px;
                border-top:1px solid #dee2e6;">
      PratikoAI - Il tuo assistente fiscale intelligente
    </div>
  </div>
</body>
</html>"""
            return await self._send_email(
                recipient_email=recipient_email,
                subject=subject,
                html_content=html_content,
            )
        except Exception as e:
            self.logger.error(
                "welcome_email_failed recipient=%s error=%s",
                recipient_email,
                str(e),
            )
            return False

    async def _send_email(self, recipient_email: str, subject: str, html_content: str) -> bool:
        """Send HTML email using SMTP."""
        try:
            # Check if email configuration is available
            if not self.smtp_username or not self.smtp_password:
                self.logger.warning("SMTP credentials not configured, email not sent")
                # In development, log the email content instead
                self.logger.info(f"EMAIL CONTENT (would be sent to {recipient_email}):")
                self.logger.info(f"Subject: {subject}")
                # Don't log full HTML content to avoid log spam
                return True

            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = recipient_email

            # Create HTML part
            html_part = MIMEText(html_content, "html")
            msg.attach(html_part)

            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)

            return True

        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")
            return False


# Global email service instance
email_service = EmailService()
