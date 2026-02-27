"""DEV-419: Communication History Retention Policy (24 months).

Background job to enforce 24-month retention of sent communications.
Communications older than 24 months are anonymized (client PII removed,
aggregate stats kept). Configurable per studio.

Reference: §4.3.
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger

DEFAULT_RETENTION_MONTHS = 24


class CommunicationRetentionJob:
    """Background job for communication retention enforcement."""

    async def run(
        self,
        db: AsyncSession,
        *,
        studio_id: UUID,
        retention_months: int = DEFAULT_RETENTION_MONTHS,
    ) -> int:
        """Anonymize communications older than retention period.

        Args:
            db: Database session.
            studio_id: Studio whose communications to process.
            retention_months: Months to retain (default 24).

        Returns:
            Number of communications anonymized.
        """
        cutoff = datetime.now(UTC) - timedelta(days=retention_months * 30)

        from app.models.communication import Communication, StatoComunicazione

        result = await db.execute(
            select(Communication).where(
                and_(
                    Communication.studio_id == studio_id,
                    Communication.status == StatoComunicazione.SENT,
                    Communication.created_at < cutoff,
                )
            )
        )
        old_comms = result.scalars().all()

        count = 0
        for comm in old_comms:
            anonymized = self.anonymize(
                {
                    "subject": comm.subject,
                    "content": comm.content,
                    "client_id": comm.client_id,
                    "channel": comm.channel if hasattr(comm, "channel") else None,
                    "status": comm.status if hasattr(comm, "status") else None,
                }
            )
            comm.subject = "[ANONIMIZZATO]"
            comm.content = "[Contenuto rimosso per politica di conservazione]"
            comm.client_id = None
            count += 1

        if count > 0:
            await db.commit()

        logger.info(
            "communication_retention_completed",
            studio_id=str(studio_id),
            anonymized_count=count,
            retention_months=retention_months,
        )

        return count

    @staticmethod
    def anonymize(data: dict[str, Any]) -> dict[str, Any]:
        """Anonymize communication data.

        Removes PII (client_id, personal content) while preserving
        aggregate stats (channel, status).

        Args:
            data: Communication data dict.

        Returns:
            Anonymized data dict.
        """
        anonymized = dict(data)
        anonymized["client_id"] = None
        anonymized["subject"] = "[ANONIMIZZATO]"
        anonymized["content"] = "[ANONIMIZZATO]"

        # Preserve aggregate fields
        for key in ("channel", "status"):
            if key in data:
                anonymized[key] = data[key]

        return anonymized


communication_retention_job = CommunicationRetentionJob()
