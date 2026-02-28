"""DEV-314/DEV-420: Client Export — GDPR data portability.

Exports all client data (decrypted for export) to structured format.
Supports Excel rows and JSON export (DEV-420).
"""

import json
from datetime import UTC, datetime
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

    async def export_client_by_id(
        self,
        db: AsyncSession,
        *,
        studio_id: UUID,
        client_id: int,
    ) -> dict | None:
        """Export a single client's data for GDPR data portability.

        Returns the client data as a dict, or None if the client is not found.
        PII fields are decrypted at the ORM layer (transparent encryption).
        """
        result = await db.execute(
            select(Client, ClientProfile)
            .outerjoin(ClientProfile, Client.id == ClientProfile.client_id)
            .where(
                and_(
                    Client.studio_id == studio_id,
                    Client.id == client_id,
                    Client.deleted_at.is_(None),
                )
            )
        )
        row = result.one_or_none()
        if row is None:
            return None

        client, profile = row

        record: dict = {
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

        logger.info(
            "client_export_by_id_completed",
            studio_id=str(studio_id),
            client_id=client_id,
        )
        return record

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

    async def export_to_json(
        self,
        db: AsyncSession,
        *,
        studio_id: UUID,
    ) -> str:
        """Export clients as GDPR-compliant JSON (DEV-420).

        Returns a JSON string containing all client data, export metadata,
        and timestamp for audit trail.

        Args:
            db: Database session.
            studio_id: Studio whose clients to export.

        Returns:
            JSON string with clients data, studio_id, and export_date.
        """
        data = await self.export_clients(db, studio_id=studio_id)

        export_payload = {
            "studio_id": str(studio_id),
            "export_date": datetime.now(UTC).isoformat(),
            "format_version": "1.0",
            "clients": data,
        }

        logger.info(
            "client_json_export_completed",
            studio_id=str(studio_id),
            client_count=len(data),
        )

        return json.dumps(export_payload, default=str, ensure_ascii=False, indent=2)


client_export_service = ClientExportService()
