"""DEV-330: CommunicationService — Draft/approve workflow state machine.

State transitions: DRAFT → PENDING_REVIEW → APPROVED → SENT (or REJECTED / FAILED).
Self-approval is forbidden: creator cannot approve their own communication.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.core.security.audit_logger import (
    SecurityEventType,
    SecuritySeverity,
    security_audit_logger,
)
from app.models.client import Client
from app.models.communication import CanaleInvio, Communication, StatoComunicazione

# Valid state transitions
_VALID_TRANSITIONS: dict[StatoComunicazione, set[StatoComunicazione]] = {
    StatoComunicazione.DRAFT: {StatoComunicazione.PENDING_REVIEW},
    StatoComunicazione.PENDING_REVIEW: {
        StatoComunicazione.APPROVED,
        StatoComunicazione.REJECTED,
    },
    StatoComunicazione.APPROVED: {
        StatoComunicazione.SENT,
        StatoComunicazione.FAILED,
    },
    StatoComunicazione.REJECTED: {StatoComunicazione.DRAFT},
    StatoComunicazione.SENT: set(),
    StatoComunicazione.FAILED: {StatoComunicazione.DRAFT},
}


class CommunicationService:
    """Service for communication workflow management."""

    def __init__(self) -> None:
        self._audit_logger = security_audit_logger

    async def _log_audit(
        self,
        action: str,
        details: dict[str, str | int | None],
    ) -> None:
        """Log a communication audit event via SecurityAuditLogger."""
        await self._audit_logger.log_security_event(
            event_type=SecurityEventType.DATA_EXPORT,
            severity=SecuritySeverity.LOW,
            action=action,
            resource="communication",
            outcome="success",
            details=details,
            compliance_tags=["communication", "audit"],
        )

    async def create_draft(
        self,
        db: AsyncSession,
        *,
        studio_id: UUID,
        subject: str,
        content: str,
        channel: CanaleInvio,
        created_by: int,
        client_id: int | None = None,
        normativa_riferimento: str | None = None,
        matching_rule_id: UUID | None = None,
    ) -> Communication:
        """Create a new communication draft."""
        comm = Communication(
            studio_id=studio_id,
            client_id=client_id,
            subject=subject,
            content=content,
            channel=channel,
            status=StatoComunicazione.DRAFT,
            created_by=created_by,
            normativa_riferimento=normativa_riferimento,
            matching_rule_id=matching_rule_id,
        )
        db.add(comm)
        await db.flush()

        logger.info(
            "communication_draft_created",
            communication_id=str(comm.id),
            studio_id=str(studio_id),
        )

        await self._log_audit(
            action="communication_created",
            details={
                "communication_id": str(comm.id),
                "studio_id": str(studio_id),
                "channel": str(channel),
                "created_by": created_by,
            },
        )
        return comm

    async def submit_for_review(
        self, db: AsyncSession, *, communication_id: UUID, studio_id: UUID
    ) -> Communication | None:
        """DRAFT → PENDING_REVIEW."""
        comm = await self._get_communication(db, communication_id, studio_id)
        if comm is None:
            return None

        self._validate_transition(comm.status, StatoComunicazione.PENDING_REVIEW)
        comm.status = StatoComunicazione.PENDING_REVIEW
        await db.flush()

        logger.info("communication_submitted", communication_id=str(communication_id))

        await self._log_audit(
            action="communication_submitted",
            details={
                "communication_id": str(communication_id),
                "studio_id": str(studio_id),
            },
        )
        return comm

    async def approve(
        self,
        db: AsyncSession,
        *,
        communication_id: UUID,
        studio_id: UUID,
        approved_by: int,
    ) -> Communication | None:
        """PENDING_REVIEW → APPROVED.

        Raises:
            ValueError: If approver is the creator (self-approval).
            ValueError: If current status is not PENDING_REVIEW.
        """
        comm = await self._get_communication(db, communication_id, studio_id)
        if comm is None:
            return None

        self._validate_transition(comm.status, StatoComunicazione.APPROVED)

        if approved_by == comm.created_by:
            raise ValueError(
                "L'auto-approvazione non è consentita: il creatore non può approvare la propria comunicazione."
            )

        comm.status = StatoComunicazione.APPROVED
        comm.approved_by = approved_by
        comm.approved_at = datetime.now(UTC)
        await db.flush()

        logger.info(
            "communication_approved",
            communication_id=str(communication_id),
            approved_by=approved_by,
        )

        await self._log_audit(
            action="communication_approved",
            details={
                "communication_id": str(communication_id),
                "studio_id": str(studio_id),
                "approved_by": approved_by,
            },
        )
        return comm

    async def reject(self, db: AsyncSession, *, communication_id: UUID, studio_id: UUID) -> Communication | None:
        """PENDING_REVIEW → REJECTED."""
        comm = await self._get_communication(db, communication_id, studio_id)
        if comm is None:
            return None

        self._validate_transition(comm.status, StatoComunicazione.REJECTED)
        comm.status = StatoComunicazione.REJECTED
        await db.flush()

        logger.info("communication_rejected", communication_id=str(communication_id))

        await self._log_audit(
            action="communication_rejected",
            details={
                "communication_id": str(communication_id),
                "studio_id": str(studio_id),
            },
        )
        return comm

    async def mark_sent(self, db: AsyncSession, *, communication_id: UUID, studio_id: UUID) -> Communication | None:
        """APPROVED → SENT."""
        comm = await self._get_communication(db, communication_id, studio_id)
        if comm is None:
            return None

        self._validate_transition(comm.status, StatoComunicazione.SENT)
        comm.status = StatoComunicazione.SENT
        comm.sent_at = datetime.now(UTC)
        await db.flush()

        logger.info("communication_sent", communication_id=str(communication_id))

        await self._log_audit(
            action="communication_sent",
            details={
                "communication_id": str(communication_id),
                "studio_id": str(studio_id),
            },
        )
        return comm

    async def mark_failed(self, db: AsyncSession, *, communication_id: UUID, studio_id: UUID) -> Communication | None:
        """APPROVED → FAILED."""
        comm = await self._get_communication(db, communication_id, studio_id)
        if comm is None:
            return None

        self._validate_transition(comm.status, StatoComunicazione.FAILED)
        comm.status = StatoComunicazione.FAILED
        await db.flush()

        logger.info("communication_failed", communication_id=str(communication_id))

        await self._log_audit(
            action="communication_failed",
            details={
                "communication_id": str(communication_id),
                "studio_id": str(studio_id),
            },
        )
        return comm

    async def get_by_id(self, db: AsyncSession, *, communication_id: UUID, studio_id: UUID) -> Communication | None:
        """Get communication by ID within studio."""
        return await self._get_communication(db, communication_id, studio_id)

    async def list_by_studio(
        self,
        db: AsyncSession,
        *,
        studio_id: UUID,
        status: StatoComunicazione | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Communication]:
        """List communications for a studio with optional status filter."""
        query = select(Communication).where(Communication.studio_id == studio_id)
        if status is not None:
            query = query.where(Communication.status == status)
        query = query.offset(offset).limit(limit).order_by(Communication.created_at.desc())

        result = await db.execute(query)
        return list(result.scalars().all())

    async def _get_communication(
        self, db: AsyncSession, communication_id: UUID, studio_id: UUID
    ) -> Communication | None:
        """Fetch communication enforcing tenant isolation."""
        result = await db.execute(
            select(Communication).where(
                and_(
                    Communication.id == communication_id,
                    Communication.studio_id == studio_id,
                )
            )
        )
        return result.scalar_one_or_none()

    # ---------------------------------------------------------------
    # DEV-335: Bulk communication creation
    # ---------------------------------------------------------------

    async def create_bulk_drafts(
        self,
        db: AsyncSession,
        *,
        studio_id: UUID,
        client_ids: list[int],
        subject: str,
        content: str,
        channel: CanaleInvio,
        created_by: int,
        normativa_riferimento: str | None = None,
        matching_rule_id: UUID | None = None,
    ) -> list[Communication]:
        """Create draft communications for multiple clients at once.

        Validates that client IDs belong to the given studio for tenant isolation.
        """
        if not client_ids:
            raise ValueError("La lista dei clienti non può essere vuota.")

        # Validate client IDs belong to studio (multi-tenant isolation)
        result = await db.execute(
            select(Client).where(
                and_(
                    Client.id.in_(client_ids),
                    Client.studio_id == studio_id,
                    Client.deleted_at.is_(None),
                )
            )
        )
        valid_clients = result.scalars().all()
        valid_client_ids = {c.id for c in valid_clients}

        communications = []
        for cid in client_ids:
            if cid not in valid_client_ids:
                logger.warning(
                    "bulk_draft_client_skipped",
                    client_id=cid,
                    studio_id=str(studio_id),
                )
                continue
            comm = Communication(
                studio_id=studio_id,
                client_id=cid,
                subject=subject,
                content=content,
                channel=channel,
                status=StatoComunicazione.DRAFT,
                created_by=created_by,
                normativa_riferimento=normativa_riferimento,
                matching_rule_id=matching_rule_id,
            )
            db.add(comm)
            communications.append(comm)

        await db.flush()

        logger.info(
            "bulk_communications_created",
            studio_id=str(studio_id),
            count=len(communications),
        )
        return communications

    @staticmethod
    def _validate_transition(current: StatoComunicazione, target: StatoComunicazione) -> None:
        """Raise ValueError if transition is not allowed."""
        allowed = _VALID_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise ValueError(f"La transizione da '{current.value}' a '{target.value}' non è valida.")


communication_service = CommunicationService()
