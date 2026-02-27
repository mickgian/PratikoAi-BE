"""DEV-310: ClientProfileService — CRUD for client business profiles.

Manages 1:1 client profiles with ATECO validation and automatic
profile vector generation trigger on create/update.
"""

from datetime import UTC, date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.client_profile import ClientProfile, RegimeFiscale


class ClientProfileService:
    """Service for ClientProfile CRUD with ATECO validation."""

    async def create(
        self,
        db: AsyncSession,
        *,
        client_id: int,
        codice_ateco_principale: str,
        regime_fiscale: RegimeFiscale,
        data_inizio_attivita: date,
        codici_ateco_secondari: list[str] | None = None,
        ccnl_applicato: str | None = None,
        n_dipendenti: int = 0,
        immobili: list | None = None,
    ) -> ClientProfile:
        """Create a profile for a client.

        Raises:
            ValueError: If client already has a profile.
            ValueError: If ATECO code format is invalid.
        """
        await self._check_no_existing_profile(db, client_id)
        self._validate_ateco(codice_ateco_principale)

        profile = ClientProfile(
            client_id=client_id,
            codice_ateco_principale=codice_ateco_principale,
            codici_ateco_secondari=codici_ateco_secondari or [],
            regime_fiscale=regime_fiscale,
            data_inizio_attivita=data_inizio_attivita,
            ccnl_applicato=ccnl_applicato,
            n_dipendenti=n_dipendenti,
            immobili=immobili,
        )
        db.add(profile)
        await db.flush()

        logger.info(
            "client_profile_created",
            client_id=client_id,
            ateco=codice_ateco_principale,
        )
        return profile

    async def get_by_client_id(self, db: AsyncSession, *, client_id: int) -> ClientProfile | None:
        """Get profile for a given client."""
        result = await db.execute(select(ClientProfile).where(ClientProfile.client_id == client_id))
        return result.scalar_one_or_none()

    async def update(
        self,
        db: AsyncSession,
        *,
        client_id: int,
        codice_ateco_principale: str | None = None,
        codici_ateco_secondari: list[str] | None = None,
        regime_fiscale: RegimeFiscale | None = None,
        ccnl_applicato: str | None = None,
        n_dipendenti: int | None = None,
        immobili: list | None = None,
        data_cessazione_attivita: date | None = None,
    ) -> ClientProfile | None:
        """Update profile fields. Returns None if not found.

        Raises:
            ValueError: If new ATECO code format is invalid.
        """
        profile = await self.get_by_client_id(db=db, client_id=client_id)
        if profile is None:
            return None

        if codice_ateco_principale is not None:
            self._validate_ateco(codice_ateco_principale)
            profile.codice_ateco_principale = codice_ateco_principale
        if codici_ateco_secondari is not None:
            profile.codici_ateco_secondari = codici_ateco_secondari
        if regime_fiscale is not None:
            profile.regime_fiscale = regime_fiscale
        if ccnl_applicato is not None:
            profile.ccnl_applicato = ccnl_applicato
        if n_dipendenti is not None:
            profile.n_dipendenti = n_dipendenti
        if immobili is not None:
            profile.immobili = immobili
        if data_cessazione_attivita is not None:
            profile.data_cessazione_attivita = data_cessazione_attivita

        profile.updated_at = datetime.now(UTC)
        await db.flush()

        logger.info("client_profile_updated", client_id=client_id)
        return profile

    async def delete(self, db: AsyncSession, *, client_id: int) -> bool:
        """Delete profile for a client. Returns True if deleted."""
        profile = await self.get_by_client_id(db=db, client_id=client_id)
        if profile is None:
            return False

        await db.delete(profile)
        await db.flush()

        logger.info("client_profile_deleted", client_id=client_id)
        return True

    async def _check_no_existing_profile(self, db: AsyncSession, client_id: int) -> None:
        """Raise ValueError if client already has a profile."""
        existing = await self.get_by_client_id(db=db, client_id=client_id)
        if existing is not None:
            raise ValueError(f"Il profilo per il cliente {client_id} è già esistente.")

    @staticmethod
    def _validate_ateco(code: str) -> None:
        """Raise ValueError if ATECO code is invalid."""
        if not ClientProfile.is_valid_ateco(code):
            raise ValueError(f"Formato codice ATECO non valido: '{code}'. Formato atteso: XX.XX.XX")


client_profile_service = ClientProfileService()
