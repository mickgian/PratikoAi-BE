"""DEV-431: FormularioService — List, search, count, seed for formulari library."""

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.formulario import Formulario, FormularioCategory


class FormularioService:
    """Service for formulari document template library."""

    async def list_formulari(
        self,
        db: AsyncSession,
        *,
        category: FormularioCategory | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Formulario]:
        """List formulari with optional category filter and text search."""
        query = select(Formulario).where(Formulario.is_active.is_(True))

        if category is not None:
            query = query.where(Formulario.category == category)

        if search:
            pattern = f"%{search}%"
            query = query.where(
                or_(
                    Formulario.name.ilike(pattern),
                    Formulario.code.ilike(pattern),
                    Formulario.description.ilike(pattern),
                )
            )

        query = query.offset(offset).limit(limit).order_by(Formulario.name)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_formulario(self, db: AsyncSession, *, formulario_id: UUID) -> Formulario | None:
        """Get a single formulario by ID."""
        return await db.get(Formulario, formulario_id)

    async def count_formulari(
        self,
        db: AsyncSession,
        *,
        category: FormularioCategory | None = None,
    ) -> int:
        """Count active formulari, optionally filtered by category."""
        query = select(func.count(Formulario.id)).where(Formulario.is_active.is_(True))
        if category is not None:
            query = query.where(Formulario.category == category)
        result = await db.execute(query)
        return result.scalar_one()

    async def seed_formulari(self, db: AsyncSession) -> int:
        """Seed default Italian formulari. Returns count of created records."""
        defaults = [
            {
                "code": "AA9-12",
                "name": "Modello AA9/12",
                "description": "Dichiarazione di inizio attività per persone fisiche",
                "category": FormularioCategory.APERTURA,
                "issuing_authority": "Agenzia delle Entrate",
            },
            {
                "code": "F24",
                "name": "Modello F24",
                "description": "Modello di pagamento unificato per imposte, contributi e premi",
                "category": FormularioCategory.VERSAMENTI,
                "issuing_authority": "Agenzia delle Entrate",
            },
            {
                "code": "CU",
                "name": "Certificazione Unica",
                "description": "Certificazione dei redditi di lavoro dipendente e assimilati",
                "category": FormularioCategory.DICHIARAZIONI,
                "issuing_authority": "Agenzia delle Entrate",
            },
            {
                "code": "770",
                "name": "Modello 770",
                "description": "Dichiarazione dei sostituti d'imposta",
                "category": FormularioCategory.DICHIARAZIONI,
                "issuing_authority": "Agenzia delle Entrate",
            },
            {
                "code": "UNICO-PF",
                "name": "Modello Redditi PF",
                "description": "Dichiarazione dei redditi per persone fisiche",
                "category": FormularioCategory.DICHIARAZIONI,
                "issuing_authority": "Agenzia delle Entrate",
            },
            {
                "code": "DM10",
                "name": "Modello DM10",
                "description": "Denuncia mensile contributiva INPS",
                "category": FormularioCategory.PREVIDENZA,
                "issuing_authority": "INPS",
            },
            {
                "code": "UNILAV",
                "name": "Comunicazione UniLav",
                "description": "Comunicazione obbligatoria di assunzione, cessazione, trasformazione",
                "category": FormularioCategory.LAVORO,
                "issuing_authority": "Ministero del Lavoro",
            },
        ]

        created = 0
        for data in defaults:
            existing = await db.execute(select(Formulario).where(Formulario.code == data["code"]))
            if existing.scalar_one_or_none() is None:
                db.add(Formulario(**data))
                created += 1

        if created:
            await db.flush()
            logger.info("formulari_seeded", count=created)

        return created


formulario_service = FormularioService()
