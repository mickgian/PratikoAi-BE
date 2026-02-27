"""Daily Digest Email Service for Expert Generated Tasks.

Sends a daily email to admin with all tasks created yesterday from expert
feedback. Email is only sent if tasks exist.

This service is intended to be run as a cron job at 9:00 AM daily.
"""

import os
from datetime import datetime, timedelta
from typing import List

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.logging import logger
from app.models.quality_analysis import ExpertGeneratedTask, ExpertProfile
from app.services.email_service import EmailService


class TaskDigestEmailService:
    """Service for sending daily digest emails with expert-generated tasks.

    Queries all tasks created yesterday and sends an HTML email summary.
    Skips sending if no tasks were created.
    """

    def __init__(self, db: AsyncSession, email_service: EmailService):
        """Initialize digest email service.

        Args:
            db: Async database session
            email_service: Email service for sending emails
        """
        self.db = db
        self.email_service = email_service
        self.recipient_email = os.getenv("ADMIN_EMAIL", "admin@example.com")

    async def send_daily_digest(self) -> bool:
        """Send daily digest email with tasks created yesterday.

        Returns:
            bool: True if email sent successfully, False if no tasks or error
        """
        yesterday = datetime.now().date() - timedelta(days=1)

        try:
            # Query tasks created yesterday with expert profile eagerly loaded
            result = await self.db.execute(
                select(ExpertGeneratedTask)
                .options(joinedload(ExpertGeneratedTask.expert))
                .where(func.date(ExpertGeneratedTask.created_at) == yesterday)
                .order_by(ExpertGeneratedTask.created_at.desc())
            )
            tasks = result.scalars().unique().all()

            if not tasks:
                logger.info(f"No tasks created on {yesterday}, skipping digest email")
                return False

            logger.info(f"Found {len(tasks)} tasks created on {yesterday}, preparing digest email")

            # Build email
            subject = f"Tasks generati dal feedback esperti - {yesterday.strftime('%d/%m/%Y')}"
            html_body = self._build_email_html(tasks, yesterday)

            # Send email
            success = await self.email_service.send_email(
                to=self.recipient_email, subject=subject, html_body=html_body
            )

            if success:
                logger.info(f"Digest email sent successfully: {len(tasks)} tasks for {yesterday}")
            else:
                logger.error(f"Failed to send digest email for {yesterday}")

            return success

        except Exception as e:
            logger.error(f"Failed to send daily digest email: {e}", exc_info=True)
            return False

    def _build_email_html(self, tasks: list[ExpertGeneratedTask], date: datetime.date) -> str:
        """Build HTML email body with task summary.

        Args:
            tasks: List of ExpertGeneratedTask records
            date: Date for which tasks were created

        Returns:
            str: HTML email body
        """
        # Build task list HTML
        task_list_html = "\n".join(
            [
                f"""
                <li style="margin-bottom: 15px; padding: 10px; background-color: #f8f9fa; border-left: 4px solid #667eea; border-radius: 4px;">
                    <strong style="color: #667eea; font-size: 16px;">{task.task_id}</strong>: {task.task_name}
                    <br>
                    <small style="color: #6c757d;">
                        Expert Trust Score: {task.expert.trust_score:.2f} |
                        Feedback ID: {str(task.feedback_id)[:8]}... |
                        Created: {task.created_at.strftime("%H:%M")}
                    </small>
                    <br>
                    <span style="color: #495057; font-size: 14px; margin-top: 5px; display: block;">
                        Question: {task.question[:100]}{"..." if len(task.question) > 100 else ""}
                    </span>
                </li>
                """
                for task in tasks
            ]
        )

        # Build complete HTML email
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tasks Generati dal Feedback Esperti</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
             background-color: #f5f7fa; margin: 0; padding: 20px;">

    <div style="max-width: 800px; margin: 0 auto; background-color: white; border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1); overflow: hidden;">

        <!-- Header -->
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white; padding: 30px; text-align: center;">
            <h1 style="margin: 0; font-size: 28px; font-weight: 600;">
                Tasks Generati dal Feedback Esperti
            </h1>
            <p style="margin: 10px 0 0 0; opacity: 0.9; font-size: 16px;">
                {date.strftime("%d/%m/%Y")}
            </p>
        </div>

        <!-- Body -->
        <div style="padding: 30px;">

            <!-- Summary -->
            <div style="background-color: #e8eaf6; border-radius: 8px; padding: 20px; margin-bottom: 30px;">
                <h2 style="margin: 0 0 10px 0; color: #333; font-size: 20px;">
                    📊 Riepilogo
                </h2>
                <p style="margin: 0; color: #555; font-size: 16px;">
                    <strong style="color: #667eea; font-size: 24px;">{len(tasks)}</strong>
                    task{"s" if len(tasks) != 1 else ""}
                    {"sono stati creati" if len(tasks) != 1 else "è stato creato"}
                    automaticamente dal sistema di feedback esperti.
                </p>
            </div>

            <!-- Tasks List -->
            <h2 style="color: #333; font-size: 20px; margin-bottom: 15px; border-bottom: 2px solid #667eea; padding-bottom: 10px;">
                🎯 Tasks Creati
            </h2>

            <ul style="list-style: none; padding: 0; margin: 0;">
                {task_list_html}
            </ul>

            <!-- Instructions -->
            <div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin-top: 30px; border-radius: 4px;">
                <h3 style="margin: 0 0 10px 0; color: #856404; font-size: 16px;">
                    📝 Azioni Richieste
                </h3>
                <p style="margin: 0; color: #856404; font-size: 14px;">
                    Controlla il file <code style="background-color: #fff; padding: 2px 6px; border-radius: 3px;
                    font-family: 'Courier New', monospace;">SUPER_USER_TASKS.md</code> nella root del repository
                    backend per i dettagli completi di ogni task.
                </p>
                <p style="margin: 10px 0 0 0; color: #856404; font-size: 14px;">
                    Ogni task include:
                </p>
                <ul style="margin: 5px 0 0 0; color: #856404; font-size: 14px;">
                    <li>Domanda originale e risposta incompleta/errata</li>
                    <li>Dettagli forniti dall'esperto per la correzione</li>
                    <li>Riferimenti normativi (se disponibili)</li>
                    <li>Suggerimenti per il miglioramento</li>
                </ul>
            </div>

        </div>

        <!-- Footer -->
        <div style="background-color: #f8f9fa; padding: 20px; text-align: center; border-top: 1px solid #dee2e6;">
            <p style="margin: 0; color: #6c757d; font-size: 12px;">
                Questa email è generata automaticamente ogni giorno alle 09:00 dal sistema
                <strong>PratikoAI Expert Feedback</strong>.
            </p>
            <p style="margin: 10px 0 0 0; color: #6c757d; font-size: 12px;">
                Per domande o problemi, contattare il team di sviluppo.
            </p>
        </div>

    </div>

</body>
</html>
        """

        return html.strip()
