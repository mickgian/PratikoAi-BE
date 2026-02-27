"""Tests for Studio API endpoints (DEV-311).

TDD: Tests written FIRST before implementation validation.
Tests all Studio CRUD endpoints with mocked StudioService.

Endpoints tested:
- POST /studios
- GET /studios/{studio_id}
- GET /studios/by-slug/{slug}
- PUT /studios/{studio_id}
- DELETE /studios/{studio_id}
"""

from datetime import UTC, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def studio_id() -> UUID:
    """Fixed studio UUID for deterministic tests."""
    return uuid4()


@pytest.fixture
def mock_db() -> AsyncMock:
    """Mock async database session."""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def sample_studio(studio_id: UUID) -> MagicMock:
    """Return a mock Studio object with standard fields."""
    studio = MagicMock()
    studio.id = studio_id
    studio.name = "Studio Rossi"
    studio.slug = "studio-rossi"
    studio.max_clients = 100
    studio.settings = {"theme": "dark"}
    studio.created_at = datetime.now(UTC)
    studio.updated_at = None
    return studio


# ---------------------------------------------------------------------------
# POST /studios — Create
# ---------------------------------------------------------------------------


class TestCreateStudio:
    """Tests for POST /studios endpoint."""

    @pytest.mark.asyncio
    async def test_create_studio_success(self, mock_db: AsyncMock, sample_studio: MagicMock) -> None:
        """Happy path: creates a studio and returns 201."""
        from app.api.v1.studio import create_studio
        from app.schemas.studio import StudioCreate

        body = StudioCreate(
            name="Studio Rossi",
            slug="studio-rossi",
            max_clients=100,
            settings={"theme": "dark"},
        )

        with patch("app.api.v1.studio.studio_service") as mock_svc:
            mock_svc.create = AsyncMock(return_value=sample_studio)
            result = await create_studio(body=body, db=mock_db)

        assert result.name == "Studio Rossi"
        assert result.slug == "studio-rossi"
        assert result.max_clients == 100
        mock_svc.create.assert_awaited_once()
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_studio_duplicate_slug_returns_400(self, mock_db: AsyncMock) -> None:
        """Error case: duplicate slug raises HTTPException 400."""
        from app.api.v1.studio import create_studio
        from app.schemas.studio import StudioCreate

        body = StudioCreate(name="Studio Rossi", slug="studio-rossi")

        with patch("app.api.v1.studio.studio_service") as mock_svc:
            mock_svc.create = AsyncMock(
                side_effect=ValueError("Lo slug 'studio-rossi' e' gia' in uso da un altro studio.")
            )
            with pytest.raises(HTTPException) as exc_info:
                await create_studio(body=body, db=mock_db)

        assert exc_info.value.status_code == 400
        assert "slug" in exc_info.value.detail.lower() or "studio" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_create_studio_with_default_max_clients(self, mock_db: AsyncMock, sample_studio: MagicMock) -> None:
        """Edge case: max_clients defaults to 100 when not provided."""
        from app.api.v1.studio import create_studio
        from app.schemas.studio import StudioCreate

        body = StudioCreate(name="Studio Bianchi", slug="studio-bianchi")

        with patch("app.api.v1.studio.studio_service") as mock_svc:
            mock_svc.create = AsyncMock(return_value=sample_studio)
            result = await create_studio(body=body, db=mock_db)

        # Verify the service was called with default max_clients
        call_kwargs = mock_svc.create.call_args
        assert call_kwargs.kwargs.get("max_clients", 100) == 100


# ---------------------------------------------------------------------------
# GET /studios/{studio_id} — Read by ID
# ---------------------------------------------------------------------------


class TestGetStudio:
    """Tests for GET /studios/{studio_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_studio_success(self, mock_db: AsyncMock, studio_id: UUID, sample_studio: MagicMock) -> None:
        """Happy path: returns studio when found."""
        from app.api.v1.studio import get_studio

        with patch("app.api.v1.studio.studio_service") as mock_svc:
            mock_svc.get_by_id = AsyncMock(return_value=sample_studio)
            result = await get_studio(studio_id=studio_id, db=mock_db)

        assert result.id == studio_id
        assert result.name == "Studio Rossi"
        mock_svc.get_by_id.assert_awaited_once_with(mock_db, studio_id=studio_id)

    @pytest.mark.asyncio
    async def test_get_studio_not_found_returns_404(self, mock_db: AsyncMock) -> None:
        """Error case: nonexistent studio raises HTTPException 404."""
        from app.api.v1.studio import get_studio

        fake_id = uuid4()

        with patch("app.api.v1.studio.studio_service") as mock_svc:
            mock_svc.get_by_id = AsyncMock(return_value=None)
            with pytest.raises(HTTPException) as exc_info:
                await get_studio(studio_id=fake_id, db=mock_db)

        assert exc_info.value.status_code == 404
        assert "non trovato" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_get_studio_returns_settings(
        self, mock_db: AsyncMock, studio_id: UUID, sample_studio: MagicMock
    ) -> None:
        """Edge case: settings JSONB is correctly serialized."""
        from app.api.v1.studio import get_studio

        sample_studio.settings = {"locale": "it_IT", "notifications": True}

        with patch("app.api.v1.studio.studio_service") as mock_svc:
            mock_svc.get_by_id = AsyncMock(return_value=sample_studio)
            result = await get_studio(studio_id=studio_id, db=mock_db)

        assert result.settings == {"locale": "it_IT", "notifications": True}


# ---------------------------------------------------------------------------
# GET /studios/by-slug/{slug} — Read by slug
# ---------------------------------------------------------------------------


class TestGetStudioBySlug:
    """Tests for GET /studios/by-slug/{slug} endpoint."""

    @pytest.mark.asyncio
    async def test_get_by_slug_success(self, mock_db: AsyncMock, sample_studio: MagicMock) -> None:
        """Happy path: returns studio when slug matches."""
        from app.api.v1.studio import get_studio_by_slug

        with patch("app.api.v1.studio.studio_service") as mock_svc:
            mock_svc.get_by_slug = AsyncMock(return_value=sample_studio)
            result = await get_studio_by_slug(slug="studio-rossi", db=mock_db)

        assert result.slug == "studio-rossi"
        mock_svc.get_by_slug.assert_awaited_once_with(mock_db, slug="studio-rossi")

    @pytest.mark.asyncio
    async def test_get_by_slug_not_found_returns_404(self, mock_db: AsyncMock) -> None:
        """Error case: nonexistent slug raises HTTPException 404."""
        from app.api.v1.studio import get_studio_by_slug

        with patch("app.api.v1.studio.studio_service") as mock_svc:
            mock_svc.get_by_slug = AsyncMock(return_value=None)
            with pytest.raises(HTTPException) as exc_info:
                await get_studio_by_slug(slug="non-esiste", db=mock_db)

        assert exc_info.value.status_code == 404
        assert "non trovato" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_get_by_slug_with_special_characters(self, mock_db: AsyncMock, sample_studio: MagicMock) -> None:
        """Edge case: slug with hyphens and numbers."""
        from app.api.v1.studio import get_studio_by_slug

        sample_studio.slug = "studio-rossi-2024"

        with patch("app.api.v1.studio.studio_service") as mock_svc:
            mock_svc.get_by_slug = AsyncMock(return_value=sample_studio)
            result = await get_studio_by_slug(slug="studio-rossi-2024", db=mock_db)

        assert result.slug == "studio-rossi-2024"


# ---------------------------------------------------------------------------
# PUT /studios/{studio_id} — Update
# ---------------------------------------------------------------------------


class TestUpdateStudio:
    """Tests for PUT /studios/{studio_id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_studio_success(self, mock_db: AsyncMock, studio_id: UUID, sample_studio: MagicMock) -> None:
        """Happy path: update name and settings."""
        from app.api.v1.studio import update_studio
        from app.schemas.studio import StudioUpdate

        sample_studio.name = "Studio Rossi Aggiornato"
        body = StudioUpdate(name="Studio Rossi Aggiornato")

        with patch("app.api.v1.studio.studio_service") as mock_svc:
            mock_svc.update = AsyncMock(return_value=sample_studio)
            result = await update_studio(studio_id=studio_id, body=body, db=mock_db)

        assert result.name == "Studio Rossi Aggiornato"
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_studio_not_found_returns_404(self, mock_db: AsyncMock) -> None:
        """Error case: update on nonexistent studio raises 404."""
        from app.api.v1.studio import update_studio
        from app.schemas.studio import StudioUpdate

        fake_id = uuid4()
        body = StudioUpdate(name="Nuovo Nome")

        with patch("app.api.v1.studio.studio_service") as mock_svc:
            mock_svc.update = AsyncMock(return_value=None)
            with pytest.raises(HTTPException) as exc_info:
                await update_studio(studio_id=fake_id, body=body, db=mock_db)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_studio_duplicate_slug_returns_400(self, mock_db: AsyncMock, studio_id: UUID) -> None:
        """Error case: slug conflict during update raises 400."""
        from app.api.v1.studio import update_studio
        from app.schemas.studio import StudioUpdate

        body = StudioUpdate(slug="slug-duplicato")

        with patch("app.api.v1.studio.studio_service") as mock_svc:
            mock_svc.update = AsyncMock(
                side_effect=ValueError("Lo slug 'slug-duplicato' e' gia' in uso da un altro studio.")
            )
            with pytest.raises(HTTPException) as exc_info:
                await update_studio(studio_id=studio_id, body=body, db=mock_db)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_update_studio_partial_fields(
        self, mock_db: AsyncMock, studio_id: UUID, sample_studio: MagicMock
    ) -> None:
        """Edge case: only update max_clients, leave other fields untouched."""
        from app.api.v1.studio import update_studio
        from app.schemas.studio import StudioUpdate

        sample_studio.max_clients = 200
        body = StudioUpdate(max_clients=200)

        with patch("app.api.v1.studio.studio_service") as mock_svc:
            mock_svc.update = AsyncMock(return_value=sample_studio)
            result = await update_studio(studio_id=studio_id, body=body, db=mock_db)

        assert result.max_clients == 200
        call_kwargs = mock_svc.update.call_args.kwargs
        assert call_kwargs["max_clients"] == 200


# ---------------------------------------------------------------------------
# DELETE /studios/{studio_id} — Deactivate
# ---------------------------------------------------------------------------


class TestDeactivateStudio:
    """Tests for DELETE /studios/{studio_id} endpoint."""

    @pytest.mark.asyncio
    async def test_deactivate_studio_success(
        self, mock_db: AsyncMock, studio_id: UUID, sample_studio: MagicMock
    ) -> None:
        """Happy path: deactivation returns 204 (None)."""
        from app.api.v1.studio import deactivate_studio

        with patch("app.api.v1.studio.studio_service") as mock_svc:
            mock_svc.deactivate = AsyncMock(return_value=sample_studio)
            result = await deactivate_studio(studio_id=studio_id, db=mock_db)

        assert result is None
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_deactivate_studio_not_found_returns_404(self, mock_db: AsyncMock) -> None:
        """Error case: deactivate nonexistent studio raises 404."""
        from app.api.v1.studio import deactivate_studio

        fake_id = uuid4()

        with patch("app.api.v1.studio.studio_service") as mock_svc:
            mock_svc.deactivate = AsyncMock(return_value=None)
            with pytest.raises(HTTPException) as exc_info:
                await deactivate_studio(studio_id=fake_id, db=mock_db)

        assert exc_info.value.status_code == 404
        assert "non trovato" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_deactivate_studio_commits_transaction(
        self, mock_db: AsyncMock, studio_id: UUID, sample_studio: MagicMock
    ) -> None:
        """Edge case: verify db.commit() is called after successful deactivation."""
        from app.api.v1.studio import deactivate_studio

        with patch("app.api.v1.studio.studio_service") as mock_svc:
            mock_svc.deactivate = AsyncMock(return_value=sample_studio)
            await deactivate_studio(studio_id=studio_id, db=mock_db)

        mock_db.commit.assert_awaited_once()
