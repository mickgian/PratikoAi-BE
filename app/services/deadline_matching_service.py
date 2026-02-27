"""DEV-383: Client-Deadline Matching — Match deadlines to clients using criteria engine.

Uses deadline type-based rules to determine which clients should be
assigned a given deadline. Creates ClientDeadline records for matches,
skipping duplicates.
"""

from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.client import Client
from app.models.client_profile import ClientProfile
from app.models.deadline import ClientDeadline, Deadline, DeadlineType


class DeadlineMatchingService:
    """Match deadlines to studio clients based on deadline type criteria."""

    async def match_deadline_to_clients(
        self,
        db: AsyncSession,
        *,
        deadline_id: UUID,
        studio_id: UUID,
    ) -> list[ClientDeadline]:
        """Match a deadline to all eligible clients in a studio.

        Criteria by deadline type:
        - FISCALE: all active clients (everyone has tax obligations)
        - ADEMPIMENTO: all active clients
        - CONTRIBUTIVO: clients with n_dipendenti > 0
        - SOCIETARIO: clients with tipo_cliente = SOCIETA

        Skips clients that already have this deadline assigned.

        Args:
            db: Async database session.
            deadline_id: UUID of the deadline to match.
            studio_id: UUID of the studio (tenant isolation).

        Returns:
            List of newly created ClientDeadline records.

        Raises:
            ValueError: If deadline_id does not exist.
        """
        deadline = await db.get(Deadline, deadline_id)
        if deadline is None:
            raise ValueError(f"Scadenza non trovata: {deadline_id}")

        # Fetch all active clients (with profiles) for this studio
        candidates = await self._fetch_studio_clients(db, studio_id=studio_id)

        if not candidates:
            logger.info(
                "deadline_matching_no_clients",
                deadline_id=str(deadline_id),
                studio_id=str(studio_id),
            )
            return []

        # Filter candidates based on deadline type
        eligible = self._filter_by_type(
            candidates,
            deadline_type=deadline.deadline_type,
        )

        if not eligible:
            logger.info(
                "deadline_matching_no_eligible",
                deadline_id=str(deadline_id),
                studio_id=str(studio_id),
                deadline_type=str(deadline.deadline_type),
            )
            return []

        # Create ClientDeadline records, skipping duplicates
        created: list[ClientDeadline] = []
        for client, _profile in eligible:
            already_exists = await self._check_existing_assignment(
                db,
                client_id=client.id,
                deadline_id=deadline_id,
            )
            if already_exists:
                logger.info(
                    "deadline_already_assigned",
                    client_id=client.id,
                    deadline_id=str(deadline_id),
                )
                continue

            cd = ClientDeadline(
                client_id=client.id,
                deadline_id=deadline_id,
                studio_id=studio_id,
            )
            db.add(cd)
            await db.flush()
            created.append(cd)

        logger.info(
            "deadline_matched_to_clients",
            deadline_id=str(deadline_id),
            studio_id=str(studio_id),
            matched_count=len(created),
            total_candidates=len(candidates),
        )
        return created

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _fetch_studio_clients(
        self,
        db: AsyncSession,
        *,
        studio_id: UUID,
    ) -> list[tuple]:
        """Fetch all active, non-deleted clients with their profiles."""
        result = await db.execute(
            select(Client, ClientProfile)
            .outerjoin(ClientProfile, Client.id == ClientProfile.client_id)
            .where(
                and_(
                    Client.studio_id == studio_id,
                    Client.deleted_at.is_(None),
                )
            )
        )
        return list(result.all())

    @staticmethod
    def _filter_by_type(
        candidates: list[tuple],
        *,
        deadline_type: DeadlineType,
    ) -> list[tuple]:
        """Filter client-profile pairs by deadline type criteria.

        Args:
            candidates: List of (Client, ClientProfile|None) tuples.
            deadline_type: The deadline type determining matching rules.

        Returns:
            Filtered list of eligible (Client, ClientProfile|None) tuples.
        """
        if deadline_type in (DeadlineType.FISCALE, DeadlineType.ADEMPIMENTO):
            # All active clients have tax/compliance obligations
            return candidates

        if deadline_type == DeadlineType.CONTRIBUTIVO:
            # Only clients with employees
            return [
                (client, profile)
                for client, profile in candidates
                if profile is not None and getattr(profile, "n_dipendenti", 0) > 0
            ]

        if deadline_type == DeadlineType.SOCIETARIO:
            # Only societa-type clients
            return [
                (client, profile)
                for client, profile in candidates
                if str(getattr(client, "tipo_cliente", "")).lower() == "societa"
            ]

        return candidates

    async def _check_existing_assignment(
        self,
        db: AsyncSession,
        *,
        client_id: int,
        deadline_id: UUID,
    ) -> bool:
        """Check if a client-deadline assignment already exists."""
        result = await db.execute(
            select(ClientDeadline).where(
                and_(
                    ClientDeadline.client_id == client_id,
                    ClientDeadline.deadline_id == deadline_id,
                )
            )
        )
        return result.scalar_one_or_none() is not None


deadline_matching_service = DeadlineMatchingService()
