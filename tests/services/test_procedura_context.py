"""DEV-345: Tests for ProceduraContextService — Context injection into chat.

TDD RED phase: These tests define the expected behaviour of the procedura
context builder that enriches chat prompts with active procedura state and
client profile data.
"""

from unittest.mock import AsyncMock, MagicMock, PropertyMock
from uuid import uuid4

import pytest

from app.models.procedura import Procedura, ProceduraCategory
from app.models.procedura_progress import ProceduraProgress

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_db() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    return session


@pytest.fixture
def studio_id():
    return uuid4()


@pytest.fixture
def context_service():
    from app.services.procedura_context_service import ProceduraContextService

    return ProceduraContextService()


@pytest.fixture
def sample_procedura() -> Procedura:
    return Procedura(
        id=uuid4(),
        code="APERTURA_PIVA",
        title="Apertura Partita IVA",
        description="Procedura per apertura P.IVA.",
        category=ProceduraCategory.FISCALE,
        steps=[
            {"index": 0, "title": "Raccolta documenti", "checklist": ["CI", "CF"]},
            {"index": 1, "title": "Compilazione modello AA9/12", "checklist": ["Modello compilato"]},
        ],
        estimated_time_minutes=60,
        version=1,
        is_active=True,
    )


@pytest.fixture
def active_progress(studio_id, sample_procedura) -> ProceduraProgress:
    return ProceduraProgress(
        id=uuid4(),
        user_id=1,
        studio_id=studio_id,
        procedura_id=sample_procedura.id,
        client_id=None,
        current_step=0,
        completed_steps=[],
    )


# ---------------------------------------------------------------------------
# Tests — build_procedura_context
# ---------------------------------------------------------------------------


class TestBuildProceduraContext:
    """Test ProceduraContextService.build_procedura_context()."""

    @pytest.mark.asyncio
    async def test_build_procedura_context_with_active(
        self,
        context_service,
        mock_db: AsyncMock,
        active_progress: ProceduraProgress,
        sample_procedura: Procedura,
        studio_id,
    ) -> None:
        """Happy path: active procedura returns context dict with step info."""
        # build_procedura_context uses result.scalars().first() for progress
        scalars_mock = MagicMock()
        scalars_mock.first = MagicMock(return_value=active_progress)
        execute_result = MagicMock()
        execute_result.scalars = MagicMock(return_value=scalars_mock)
        mock_db.execute = AsyncMock(return_value=execute_result)

        # Then uses db.get() for the Procedura
        mock_db.get = AsyncMock(return_value=sample_procedura)

        context = await context_service.build_procedura_context(
            db=mock_db,
            user_id=1,
            studio_id=studio_id,
        )

        assert context is not None
        assert context["procedura_title"] == "Apertura Partita IVA"
        assert context["procedura_code"] == "APERTURA_PIVA"
        assert context["current_step"] == 0
        assert context["total_steps"] == 2
        assert context["current_step_info"]["title"] == "Raccolta documenti"

    @pytest.mark.asyncio
    async def test_build_procedura_context_none(
        self,
        context_service,
        mock_db: AsyncMock,
        studio_id,
    ) -> None:
        """Edge case: no active procedura returns None."""
        scalars_mock = MagicMock()
        scalars_mock.first = MagicMock(return_value=None)
        execute_result = MagicMock()
        execute_result.scalars = MagicMock(return_value=scalars_mock)
        mock_db.execute = AsyncMock(return_value=execute_result)

        context = await context_service.build_procedura_context(
            db=mock_db,
            user_id=1,
            studio_id=studio_id,
        )

        assert context is None


# ---------------------------------------------------------------------------
# Tests — resolve_client_mention
# ---------------------------------------------------------------------------


class TestResolveClientMention:
    """Test ProceduraContextService.resolve_client_mention()."""

    @pytest.mark.asyncio
    async def test_resolve_client_mention(
        self,
        context_service,
        mock_db: AsyncMock,
        studio_id,
    ) -> None:
        """Happy path: @NomeCliente mention resolves to client context dict."""
        # First query: list clients for studio
        mock_client = MagicMock()
        mock_client.id = 1
        mock_client.nome = "Mario Rossi"
        mock_client.studio_id = studio_id
        mock_client.tipo_cliente = "ditta_individuale"
        mock_client.comune = "Roma"
        mock_client.provincia = "RM"

        scalars_mock = MagicMock()
        scalars_mock.all = MagicMock(return_value=[mock_client])
        list_result = MagicMock()
        list_result.scalars = MagicMock(return_value=scalars_mock)

        # Second query: get client by ID (for _build_client_context)
        client_result_mock = MagicMock()
        client_result_mock.scalar_one_or_none = MagicMock(return_value=mock_client)

        # Third query: get client profile
        profile_result_mock = MagicMock()
        profile_result_mock.scalar_one_or_none = MagicMock(return_value=None)

        mock_db.execute = AsyncMock(side_effect=[list_result, client_result_mock, profile_result_mock])

        message = "Prepara comunicazione per @Mario, scadenza IVA."
        result = await context_service.resolve_client_mention(
            db=mock_db,
            message=message,
            studio_id=studio_id,
        )

        assert result is not None
        assert result["nome"] == "Mario Rossi"
        assert result["client_id"] == 1

    @pytest.mark.asyncio
    async def test_client_mention_not_found(
        self,
        context_service,
        mock_db: AsyncMock,
        studio_id,
    ) -> None:
        """Edge case: unknown client mention returns None."""
        scalars_mock = MagicMock()
        scalars_mock.all = MagicMock(return_value=[])
        list_result = MagicMock()
        list_result.scalars = MagicMock(return_value=scalars_mock)
        mock_db.execute = AsyncMock(return_value=list_result)

        message = "Prepara comunicazione per @ClienteInesistente."
        result = await context_service.resolve_client_mention(
            db=mock_db,
            message=message,
            studio_id=studio_id,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_no_mention_returns_none(
        self,
        context_service,
        mock_db: AsyncMock,
        studio_id,
    ) -> None:
        """Edge case: no @ mention in message returns None."""
        result = await context_service.resolve_client_mention(
            db=mock_db,
            message="Prepara comunicazione sulla scadenza IVA.",
            studio_id=studio_id,
        )

        assert result is None
