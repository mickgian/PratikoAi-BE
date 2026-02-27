"""DEV-322: Tests for Client Profile Vector Generation."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.client_profile import ClientProfile, RegimeFiscale
from app.services.profile_embedding_service import ProfileEmbeddingService


@pytest.fixture
def embedding_service() -> ProfileEmbeddingService:
    return ProfileEmbeddingService()


@pytest.fixture
def mock_db() -> AsyncMock:
    session = AsyncMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def sample_profile() -> ClientProfile:
    return ClientProfile(
        id=1,
        client_id=1,
        codice_ateco_principale="62.01.00",
        codici_ateco_secondari=["63.11.00"],
        regime_fiscale=RegimeFiscale.ORDINARIO,
        data_inizio_attivita=date(2020, 1, 1),
        n_dipendenti=5,
        ccnl_applicato="Commercio",
    )


class TestProfileEmbeddingService:
    """Test ProfileEmbeddingService."""

    def test_build_profile_text(
        self, embedding_service: ProfileEmbeddingService, sample_profile: ClientProfile
    ) -> None:
        """Happy path: build text representation from profile."""
        text = embedding_service.build_profile_text(sample_profile)

        assert "62.01.00" in text
        assert "ordinario" in text
        assert "Commercio" in text
        assert "5" in text

    def test_build_profile_text_minimal(self, embedding_service: ProfileEmbeddingService) -> None:
        """Edge case: profile with minimal fields."""
        profile = ClientProfile(
            id=2,
            client_id=2,
            codice_ateco_principale="01.11.00",
            regime_fiscale=RegimeFiscale.FORFETTARIO,
            data_inizio_attivita=date(2023, 6, 1),
        )
        text = embedding_service.build_profile_text(profile)

        assert "01.11.00" in text
        assert "forfettario" in text

    @pytest.mark.asyncio
    async def test_generate_embedding_returns_vector(
        self,
        embedding_service: ProfileEmbeddingService,
        sample_profile: ClientProfile,
    ) -> None:
        """Happy path: generate_embedding returns a 1536-dim vector."""
        fake_vector = [0.1] * 1536
        with patch.object(embedding_service, "_call_embedding_api", new_callable=AsyncMock, return_value=fake_vector):
            result = await embedding_service.generate_embedding(sample_profile)

        assert len(result) == 1536

    @pytest.mark.asyncio
    async def test_update_profile_vector(
        self,
        embedding_service: ProfileEmbeddingService,
        mock_db: AsyncMock,
        sample_profile: ClientProfile,
    ) -> None:
        """Happy path: update profile with generated vector."""
        fake_vector = [0.01] * 1536
        with patch.object(embedding_service, "_call_embedding_api", new_callable=AsyncMock, return_value=fake_vector):
            await embedding_service.update_profile_vector(mock_db, sample_profile)

        assert sample_profile.profile_vector == fake_vector
        mock_db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_generate_embedding_api_failure(
        self,
        embedding_service: ProfileEmbeddingService,
        sample_profile: ClientProfile,
    ) -> None:
        """Error: API failure raises RuntimeError."""
        with (
            patch.object(
                embedding_service,
                "_call_embedding_api",
                new_callable=AsyncMock,
                side_effect=RuntimeError("API unavailable"),
            ),
            pytest.raises(RuntimeError, match="API unavailable"),
        ):
            await embedding_service.generate_embedding(sample_profile)
