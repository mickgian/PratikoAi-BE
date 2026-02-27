"""DEV-314: Client Export to Excel — GDPR data portability.

Exports all client data (decrypted for export) to structured format.
"""

from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.client import Client
from app.models.client_profile import ClientProfile


class ClientExportService:
    """Service for exporting client data for GDPR data portability."""

    async def export_clients(
        self,
        db: AsyncSession,
        *,
        studio_id: UUID,
    ) -> list[dict]:
        """Export all active clients for a studio as a list of dicts.

        PII fields are decrypted at the ORM layer (transparent encryption).
        Soft-deleted clients are excluded.
        """
        result = await db.execute(
            select(Client, ClientProfile)
            .outerjoin(ClientProfile, Client.id == ClientProfile.client_id)
            .where(
                and_(
                    Client.studio_id == studio_id,
                    Client.deleted_at.is_(None),
                )
            )
            .order_by(Client.id)
        )
        rows = result.all()

        export_data = []
        for client, profile in rows:
            record = {
                "id": client.id,
                "codice_fiscale": client.codice_fiscale,
                "nome": client.nome,
                "tipo_cliente": (
                    client.tipo_cliente.value if hasattr(client.tipo_cliente, "value") else str(client.tipo_cliente)
                ),
                "stato_cliente": (
                    client.stato_cliente.value if hasattr(client.stato_cliente, "value") else str(client.stato_cliente)
                ),
                "partita_iva": client.partita_iva,
                "email": client.email,
                "phone": client.phone,
                "indirizzo": client.indirizzo,
                "cap": client.cap,
                "comune": client.comune,
                "provincia": client.provincia,
                "note_studio": client.note_studio,
            }

            if profile is not None:
                record.update(
                    {
                        "codice_ateco_principale": profile.codice_ateco_principale,
                        "regime_fiscale": (
                            profile.regime_fiscale.value
                            if hasattr(profile.regime_fiscale, "value")
                            else str(profile.regime_fiscale)
                        ),
                        "ccnl_applicato": profile.ccnl_applicato,
                        "n_dipendenti": profile.n_dipendenti,
                        "data_inizio_attivita": (
                            profile.data_inizio_attivita.isoformat() if profile.data_inizio_attivita else None
                        ),
                    }
                )

            export_data.append(record)

        logger.info(
            "client_export_completed",
            studio_id=str(studio_id),
            export_count=len(export_data),
        )
        return export_data

    async def export_to_rows(
        self,
        db: AsyncSession,
        *,
        studio_id: UUID,
    ) -> tuple[list[str], list[list]]:
        """Export clients as headers + rows for Excel generation.

        Returns (headers, rows) tuple.
        """
        data = await self.export_clients(db, studio_id=studio_id)
        if not data:
            return [], []

        headers = list(data[0].keys())
        rows = [[record.get(h) for h in headers] for record in data]

        return headers, rows


client_export_service = ClientExportService()
