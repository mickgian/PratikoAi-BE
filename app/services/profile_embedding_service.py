"""DEV-322: ProfileEmbeddingService — Client profile vector generation.

Generates 1536-dim embedding vectors from client profile data (regime,
ATECO description, etc.) for semantic matching via pgvector.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.client_profile import ClientProfile


class ProfileEmbeddingService:
    """Generates and updates profile embedding vectors."""

    def build_profile_text(self, profile: ClientProfile) -> str:
        """Build a text representation from profile fields for embedding.

        Combines ATECO codes, regime, employment info into a single
        descriptive string suitable for embedding generation.
        """
        parts: list[str] = []

        parts.append(f"Codice ATECO principale: {profile.codice_ateco_principale}")

        if profile.codici_ateco_secondari:
            secondary = ", ".join(profile.codici_ateco_secondari)
            parts.append(f"Codici ATECO secondari: {secondary}")

        regime = (
            profile.regime_fiscale.value if hasattr(profile.regime_fiscale, "value") else str(profile.regime_fiscale)
        )
        parts.append(f"Regime fiscale: {regime}")

        if profile.ccnl_applicato:
            parts.append(f"CCNL applicato: {profile.ccnl_applicato}")

        parts.append(f"Numero dipendenti: {profile.n_dipendenti}")

        if profile.data_inizio_attivita:
            parts.append(f"Inizio attività: {profile.data_inizio_attivita.isoformat()}")

        if profile.immobili:
            parts.append(f"Immobili: {len(profile.immobili)} proprietà")

        return ". ".join(parts)

    async def generate_embedding(self, profile: ClientProfile) -> list[float]:
        """Generate a 1536-dim embedding vector from profile text.

        Raises:
            RuntimeError: If embedding API call fails.
        """
        text = self.build_profile_text(profile)
        return await self._call_embedding_api(text)

    async def update_profile_vector(self, db: AsyncSession, profile: ClientProfile) -> None:
        """Generate embedding and update the profile's profile_vector field."""
        vector = await self.generate_embedding(profile)
        profile.profile_vector = vector
        await db.flush()

        logger.info(
            "profile_vector_updated",
            client_id=profile.client_id,
            vector_dim=len(vector),
        )

    async def _call_embedding_api(self, text: str) -> list[float]:
        """Call the LLM embedding API to generate a vector.

        This method is designed to be overridden or mocked in tests.
        In production, it will use the configured LLM provider.
        """
        try:
            import openai

            from app.core.config import settings

            client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            response = await client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(
                "embedding_api_error",
                error_type=type(e).__name__,
                error_message=str(e),
            )
            raise RuntimeError(f"Errore API embedding: {e}") from e


profile_embedding_service = ProfileEmbeddingService()
