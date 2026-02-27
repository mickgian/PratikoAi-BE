"""DEV-317: Client GDPR Deletion Service — Right to erasure with audit trail.

Implements GDPR Article 17 erasure: export data before deletion,
anonymize PII fields, cascade to communications, and log audit trail.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.core.security.audit_logger import security_audit_logger
from app.models.client import StatoCliente
from app.models.communication import Communication
from app.services.client_export_service import client_export_service
from app.services.client_service import client_service


@dataclass
class GDPRDeletionResult:
    """Result of a GDPR Article 17 erasure operation."""

    client_id: int
    export_data: dict
    anonymized_at: datetime
    communications_affected: int


class ClientGDPRService:
    """Service for GDPR Article 17 right-to-erasure operations.

    Workflow:
    1. Retrieve client (return None if not found or already deleted).
    2. Export data before deletion (GDPR data portability).
    3. Anonymize PII fields with "[REDACTED]" / None.
    4. Set deleted_at and stato_cliente = CESSATO.
    5. Cascade: nullify client_id on related communications.
    6. Log audit trail via SecurityAuditLogger.
    7. Return GDPRDeletionResult with summary.
    """

    async def delete_client_gdpr(
        self,
        db: AsyncSession,
        *,
        studio_id: UUID,
        client_id: int,
        requested_by: str,
    ) -> GDPRDeletionResult | None:
        """Execute full GDPR Article 17 erasure for a client.

        Args:
            db: Async database session.
            studio_id: Studio UUID for tenant isolation.
            client_id: Client PK to erase.
            requested_by: Identifier of the user who requested erasure.

        Returns:
            GDPRDeletionResult with export data and affected counts,
            or None if client not found / already deleted.
        """
        # Step 1: Retrieve client (filtered by tenant + not soft-deleted)
        client = await client_service.get_by_id(db=db, client_id=client_id, studio_id=studio_id)
        if client is None:
            logger.info(
                "gdpr_deletion_client_not_found",
                client_id=client_id,
                studio_id=str(studio_id),
            )
            return None

        # Step 2: Export data BEFORE anonymization (GDPR data portability)
        export_data = await client_export_service.export_client_by_id(db=db, studio_id=studio_id, client_id=client_id)
        if export_data is None:
            export_data = {}

        # Step 3: Anonymize PII fields
        client.codice_fiscale = "[REDACTED]"
        client.nome = "[REDACTED]"
        client.email = None
        client.phone = None
        client.partita_iva = None

        # Step 4: Soft-delete marker
        now = datetime.now(UTC)
        client.deleted_at = now
        client.stato_cliente = StatoCliente.CESSATO

        # Step 5: Cascade — nullify client_id on related communications
        comms_result = await db.execute(select(Communication).where(Communication.client_id == client_id))
        communications = comms_result.scalars().all()
        for comm in communications:
            comm.client_id = None

        communications_affected = len(communications)

        await db.flush()

        # Step 6: Audit trail
        await security_audit_logger.log_gdpr_event(
            action="erasure",
            user_id=requested_by,
            data_type="client_pii",
            legal_basis="GDPR Article 17",
            outcome="success",
            details={
                "client_id": client_id,
                "studio_id": str(studio_id),
                "communications_affected": communications_affected,
            },
        )

        logger.info(
            "gdpr_deletion_completed",
            client_id=client_id,
            studio_id=str(studio_id),
            communications_affected=communications_affected,
        )

        # Step 7: Return result
        return GDPRDeletionResult(
            client_id=client_id,
            export_data=export_data,
            anonymized_at=now,
            communications_affected=communications_affected,
        )


client_gdpr_service = ClientGDPRService()
