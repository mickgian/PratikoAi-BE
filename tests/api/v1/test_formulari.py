"""DEV-432: Tests for Formulari API Endpoint."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest


@pytest.fixture
def sample_formulario():
    return SimpleNamespace(
        id=uuid4(),
        code="F24",
        name="Modello F24",
        description="Modello di pagamento unificato",
        category="versamenti",
        issuing_authority="Agenzia delle Entrate",
        external_url=None,
        is_active=True,
    )


class TestListFormulari:
    """Test GET /formulari."""

    @pytest.mark.asyncio
    async def test_list_200(self, sample_formulario) -> None:
        """Happy path: list formulari."""
        with patch("app.api.v1.formulari.formulario_service") as mock_svc:
            mock_svc.list_formulari = AsyncMock(return_value=[sample_formulario])
            mock_db = AsyncMock()

            from app.api.v1.formulari import list_formulari

            result = await list_formulari(
                category=None,
                search=None,
                offset=0,
                limit=50,
                db=mock_db,
            )
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_category_filter(self, sample_formulario) -> None:
        """Filter by category passes to service."""
        with patch("app.api.v1.formulari.formulario_service") as mock_svc:
            mock_svc.list_formulari = AsyncMock(return_value=[sample_formulario])
            mock_db = AsyncMock()

            from app.api.v1.formulari import list_formulari

            result = await list_formulari(
                category="versamenti",
                search=None,
                offset=0,
                limit=50,
                db=mock_db,
            )
            assert len(result) == 1


class TestGetFormulario:
    """Test GET /formulari/{id}."""

    @pytest.mark.asyncio
    async def test_get_detail(self, sample_formulario) -> None:
        """Happy path: get single formulario."""
        with patch("app.api.v1.formulari.formulario_service") as mock_svc:
            mock_svc.get_formulario = AsyncMock(return_value=sample_formulario)
            mock_db = AsyncMock()

            from app.api.v1.formulari import get_formulario

            result = await get_formulario(formulario_id=sample_formulario.id, db=mock_db)
            assert result.code == "F24"

    @pytest.mark.asyncio
    async def test_not_found_404(self) -> None:
        """Not found returns 404."""
        with patch("app.api.v1.formulari.formulario_service") as mock_svc:
            mock_svc.get_formulario = AsyncMock(return_value=None)
            mock_db = AsyncMock()

            from app.api.v1.formulari import get_formulario

            with pytest.raises(Exception) as exc_info:
                await get_formulario(formulario_id=uuid4(), db=mock_db)
            assert exc_info.value.status_code == 404


class TestCountFormulari:
    """Test GET /formulari/count."""

    @pytest.mark.asyncio
    async def test_count(self) -> None:
        """Happy path: count formulari."""
        with patch("app.api.v1.formulari.formulario_service") as mock_svc:
            mock_svc.count_formulari = AsyncMock(return_value=7)
            mock_db = AsyncMock()

            from app.api.v1.formulari import count_formulari

            result = await count_formulari(category=None, db=mock_db)
            assert result.count == 7
