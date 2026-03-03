"""Post-import profile completeness analysis.

Analyzes imported clients for missing fields critical to the matching
normativo engine (ADR-018). Returns a report with per-client warnings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.client import Client, TipoCliente
from app.models.client_profile import ClientProfile


@dataclass
class MissingFieldWarning:
    """A single missing-field warning for one client."""

    client_id: int
    client_nome: str
    field: str
    priority: str  # "critico" | "importante"
    reason: str


@dataclass
class CompletenessReport:
    """Summary of profile completeness for a batch of imported clients."""

    clients_without_profile: int = 0
    clients_missing_partita_iva: int = 0
    missing_fields: list[MissingFieldWarning] = field(default_factory=list)


class ProfileCompletenessService:
    """Analyze imported clients for missing fields needed by matching normativo."""

    async def analyze_imported_clients(
        self,
        db: AsyncSession,
        *,
        client_ids: list[int],
        studio_id: UUID,
    ) -> CompletenessReport:
        """Check imported clients for missing critical fields.

        Fields flagged:
        - regime_fiscale (Profile) — critico — when no ClientProfile exists
        - codice_ateco_principale (Profile) — critico — when no ClientProfile exists
        - data_inizio_attivita (Profile) — importante — when no ClientProfile exists
        - partita_iva (Client) — importante — societa/ditta_individuale only
        - email (Client) — importante — when missing
        """
        if not client_ids:
            return CompletenessReport()

        # LEFT JOIN Client + ClientProfile for the imported IDs
        stmt = (
            select(Client, ClientProfile)
            .outerjoin(ClientProfile, Client.id == ClientProfile.client_id)
            .where(
                Client.id.in_(client_ids),  # type: ignore[union-attr]
                Client.studio_id == studio_id,
                Client.deleted_at.is_(None),  # type: ignore[union-attr]
            )
        )
        result = await db.execute(stmt)
        rows = result.all()

        report = CompletenessReport()

        for client, profile in rows:
            if profile is None:
                report.clients_without_profile += 1
                report.missing_fields.append(
                    MissingFieldWarning(
                        client_id=client.id,
                        client_nome=client.nome,
                        field="regime_fiscale",
                        priority="critico",
                        reason="Profilo aziendale mancante — necessario per il matching normativo",
                    )
                )
                report.missing_fields.append(
                    MissingFieldWarning(
                        client_id=client.id,
                        client_nome=client.nome,
                        field="codice_ateco_principale",
                        priority="critico",
                        reason="Profilo aziendale mancante — necessario per il matching normativo",
                    )
                )
                report.missing_fields.append(
                    MissingFieldWarning(
                        client_id=client.id,
                        client_nome=client.nome,
                        field="data_inizio_attivita",
                        priority="importante",
                        reason="Profilo aziendale mancante — utile per il matching normativo",
                    )
                )

            # partita_iva required for societa/ditta_individuale
            needs_piva = client.tipo_cliente in (
                TipoCliente.SOCIETA,
                TipoCliente.DITTA_INDIVIDUALE,
            )
            if needs_piva and not client.partita_iva:
                report.clients_missing_partita_iva += 1
                report.missing_fields.append(
                    MissingFieldWarning(
                        client_id=client.id,
                        client_nome=client.nome,
                        field="partita_iva",
                        priority="importante",
                        reason="Partita IVA mancante per società/ditta individuale",
                    )
                )

            # email always flagged when missing
            if not client.email:
                report.missing_fields.append(
                    MissingFieldWarning(
                        client_id=client.id,
                        client_nome=client.nome,
                        field="email",
                        priority="importante",
                        reason="Email mancante",
                    )
                )

        logger.info(
            "profile_completeness_analyzed",
            studio_id=str(studio_id),
            total_clients=len(client_ids),
            without_profile=report.clients_without_profile,
            missing_partita_iva=report.clients_missing_partita_iva,
        )
        return report


profile_completeness_service = ProfileCompletenessService()
