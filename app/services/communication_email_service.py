"""DEV-333: Communication Email Sending Integration.

Sends approved communications via email with retry logic and status tracking.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.models.communication import Communication, StatoComunicazione
from app.services.communication_service import communication_service

MAX_RETRIES = 3


class CommunicationEmailService:
    """Service for sending approved communications via email."""

    def __init__(self) -> None:
        self.smtp_server = getattr(settings, "SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = getattr(settings, "SMTP_PORT", 587)
        self.smtp_username = getattr(settings, "SMTP_USERNAME", None)
        self.smtp_password = getattr(settings, "SMTP_PASSWORD", None)
        self.from_email = getattr(settings, "FROM_EMAIL", "noreply@pratikoai.com")

    async def send_communication(
        self,
        db: AsyncSession,
        *,
        communication_id: UUID,
        studio_id: UUID,
        recipient_email: str,
    ) -> Communication | None:
        """Send an approved communication via email.

        Retries up to MAX_RETRIES on failure.
        Updates status to SENT on success or FAILED after exhausting retries.
        """
        comm = await communication_service.get_by_id(db, communication_id=communication_id, studio_id=studio_id)
        if comm is None:
            return None

        if comm.status != StatoComunicazione.APPROVED:
            raise ValueError("La comunicazione deve essere approvata prima dell'invio.")

        if not recipient_email or "@" not in recipient_email:
            raise ValueError("Indirizzo email del destinatario non valido.")

        success = False
        last_error: str | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                self._send_smtp(
                    to_email=recipient_email,
                    subject=comm.subject,
                    body=comm.content,
                )
                success = True
                break
            except (smtplib.SMTPException, OSError) as exc:
                last_error = str(exc)
                logger.warning(
                    "email_send_retry",
                    communication_id=str(communication_id),
                    attempt=attempt,
                    error=last_error,
                )

        if success:
            comm = await communication_service.mark_sent(db, communication_id=communication_id, studio_id=studio_id)
            logger.info(
                "email_sent",
                communication_id=str(communication_id),
                recipient=recipient_email,
            )
        else:
            comm = await communication_service.mark_failed(db, communication_id=communication_id, studio_id=studio_id)
            logger.error(
                "email_send_failed",
                communication_id=str(communication_id),
                error=last_error,
            )

        return comm

    def _send_smtp(self, *, to_email: str, subject: str, body: str) -> None:
        """Send email via SMTP. Raises on failure."""
        msg = MIMEMultipart()
        msg["From"] = self.from_email
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls()
            if self.smtp_username and self.smtp_password:
                server.login(self.smtp_username, self.smtp_password)
            server.sendmail(self.from_email, [to_email], msg.as_string())


communication_email_service = CommunicationEmailService()
