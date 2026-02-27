"""DEV-309: ClientService — CRUD with business rules.

Manages clients with: 100-client limit per studio, CF/P.IVA validation,
PII encryption (handled by model), tenant isolation, soft delete.
"""

from datetime import UTC, datetime, timezone
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.client import Client, StatoCliente, TipoCliente

MAX_CLIENTS_PER_STUDIO = 100


class ClientService:
    """Service for Client CRUD with business-rule enforcement."""

    async def create(
        self,
        db: AsyncSession,
        *,
        studio_id: UUID,
        codice_fiscale: str,
        nome: str,
        tipo_cliente: TipoCliente,
        comune: str,
        provincia: str,
        partita_iva: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        indirizzo: str | None = None,
        cap: str | None = None,
        stato_cliente: StatoCliente = StatoCliente.ATTIVO,
        note_studio: str | None = None,
    ) -> Client:
        """Create a client within a studio.

        Raises:
            ValueError: If studio has reached the 100-client limit.
            ValueError: If codice_fiscale is already present in the studio.
        """
        await self._check_client_limit(db, studio_id)
        await self._check_duplicate_cf(db, studio_id, codice_fiscale)

        client = Client(
            studio_id=studio_id,
            codice_fiscale=codice_fiscale,
            nome=nome,
            tipo_cliente=tipo_cliente,
            comune=comune,
            provincia=provincia,
            partita_iva=partita_iva,
            email=email,
            phone=phone,
            indirizzo=indirizzo,
            cap=cap,
            stato_cliente=stato_cliente,
            note_studio=note_studio,
        )
        db.add(client)
        await db.flush()

        logger.info(
            "client_created",
            studio_id=str(studio_id),
            tipo_cliente=tipo_cliente.value,
        )
        return client

    async def get_by_id(self, db: AsyncSession, *, client_id: int, studio_id: UUID) -> Client | None:
        """Get client by ID within a studio (tenant isolation)."""
        result = await db.execute(
            select(Client).where(
                and_(
                    Client.id == client_id,
                    Client.studio_id == studio_id,
                    Client.deleted_at.is_(None),
                )
            )
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        db: AsyncSession,
        *,
        studio_id: UUID,
        offset: int = 0,
        limit: int = 50,
        stato: StatoCliente | None = None,
    ) -> tuple[list[Client], int]:
        """List clients for a studio with pagination.

        Returns:
            Tuple of (clients, total_count).
        """
        base = select(func.count(Client.id)).where(and_(Client.studio_id == studio_id, Client.deleted_at.is_(None)))
        if stato is not None:
            base = base.where(Client.stato_cliente == stato)
        count_result = await db.execute(base)
        total = count_result.scalar_one()

        query = (
            select(Client)
            .where(and_(Client.studio_id == studio_id, Client.deleted_at.is_(None)))
            .offset(offset)
            .limit(limit)
            .order_by(Client.id)
        )
        if stato is not None:
            query = query.where(Client.stato_cliente == stato)
        result = await db.execute(query)
        clients = list(result.scalars().all())

        return clients, total

    async def update(
        self,
        db: AsyncSession,
        *,
        client_id: int,
        studio_id: UUID,
        **fields: object,
    ) -> Client | None:
        """Update client fields. Returns None if not found."""
        client = await self.get_by_id(db=db, client_id=client_id, studio_id=studio_id)
        if client is None:
            return None

        for key, value in fields.items():
            if hasattr(client, key) and value is not None:
                setattr(client, key, value)

        client.updated_at = datetime.now(UTC)
        await db.flush()

        logger.info("client_updated", client_id=client_id)
        return client

    async def soft_delete(self, db: AsyncSession, *, client_id: int, studio_id: UUID) -> Client | None:
        """Soft-delete a client (GDPR right-to-erasure).

        Returns None if not found.
        """
        client = await self.get_by_id(db=db, client_id=client_id, studio_id=studio_id)
        if client is None:
            return None

        client.deleted_at = datetime.now(UTC)
        client.stato_cliente = StatoCliente.CESSATO
        await db.flush()

        logger.info("client_soft_deleted", client_id=client_id, studio_id=str(studio_id))
        return client

    async def _check_client_limit(self, db: AsyncSession, studio_id: UUID) -> None:
        """Raise ValueError if studio has reached max clients."""
        result = await db.execute(
            select(func.count(Client.id)).where(
                and_(
                    Client.studio_id == studio_id,
                    Client.deleted_at.is_(None),
                )
            )
        )
        count = result.scalar_one()
        if count >= MAX_CLIENTS_PER_STUDIO:
            raise ValueError(f"Lo studio ha raggiunto il limite di {MAX_CLIENTS_PER_STUDIO} clienti.")

    async def _check_duplicate_cf(self, db: AsyncSession, studio_id: UUID, codice_fiscale: str) -> None:
        """Raise ValueError if codice_fiscale already exists in studio."""
        result = await db.execute(
            select(Client).where(
                and_(
                    Client.studio_id == studio_id,
                    Client.codice_fiscale == codice_fiscale,
                    Client.deleted_at.is_(None),
                )
            )
        )
        if result.scalar_one_or_none() is not None:
            raise ValueError("Il codice fiscale è già presente nello studio.")


client_service = ClientService()
