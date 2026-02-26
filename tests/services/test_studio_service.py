"""DEV-308: Tests for StudioService CRUD operations."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.studio import Studio
from app.services.studio_service import StudioService


@pytest.fixture
def studio_service() -> StudioService:
    return StudioService()


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
def sample_studio() -> Studio:
    return Studio(
        id=uuid4(),
        name="Studio Rossi",
        slug="studio-rossi",
        max_clients=100,
        settings={"theme": "dark"},
    )


class TestStudioServiceCreate:
    """Test StudioService.create()."""

    @pytest.mark.asyncio
    async def test_create_studio_success(self, studio_service: StudioService, mock_db: AsyncMock) -> None:
        """Happy path: create a studio with valid data."""
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

        result = await studio_service.create(db=mock_db, name="Studio Rossi", slug="studio-rossi")

        assert result.name == "Studio Rossi"
        assert result.slug == "studio-rossi"
        assert result.max_clients == 100
        mock_db.add.assert_called_once()
        mock_db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_studio_duplicate_slug_raises(
        self, studio_service: StudioService, mock_db: AsyncMock
    ) -> None:
        """Error: duplicate slug raises ValueError."""
        existing = Studio(name="Existing", slug="studio-rossi")
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=existing)))

        with pytest.raises(ValueError, match="slug.*già in uso"):
            await studio_service.create(db=mock_db, name="New Studio", slug="studio-rossi")

    @pytest.mark.asyncio
    async def test_create_studio_with_settings(self, studio_service: StudioService, mock_db: AsyncMock) -> None:
        """Edge case: studio with custom settings and max_clients."""
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

        result = await studio_service.create(
            db=mock_db,
            name="Studio Custom",
            slug="studio-custom",
            max_clients=50,
            settings={"locale": "it_IT"},
        )

        assert result.max_clients == 50
        assert result.settings == {"locale": "it_IT"}


class TestStudioServiceGetById:
    """Test StudioService.get_by_id()."""

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self,
        studio_service: StudioService,
        mock_db: AsyncMock,
        sample_studio: Studio,
    ) -> None:
        """Happy path: retrieve existing studio."""
        mock_db.get = AsyncMock(return_value=sample_studio)

        result = await studio_service.get_by_id(db=mock_db, studio_id=sample_studio.id)

        assert result is not None
        assert result.id == sample_studio.id

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, studio_service: StudioService, mock_db: AsyncMock) -> None:
        """Error: non-existent ID returns None."""
        mock_db.get = AsyncMock(return_value=None)

        result = await studio_service.get_by_id(db=mock_db, studio_id=uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_slug(
        self,
        studio_service: StudioService,
        mock_db: AsyncMock,
        sample_studio: Studio,
    ) -> None:
        """Happy path: retrieve by slug."""
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=sample_studio)))

        result = await studio_service.get_by_slug(db=mock_db, slug="studio-rossi")

        assert result is not None
        assert result.slug == "studio-rossi"


class TestStudioServiceUpdate:
    """Test StudioService.update()."""

    @pytest.mark.asyncio
    async def test_update_studio_name(
        self,
        studio_service: StudioService,
        mock_db: AsyncMock,
        sample_studio: Studio,
    ) -> None:
        """Happy path: update studio name."""
        mock_db.get = AsyncMock(return_value=sample_studio)
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

        result = await studio_service.update(db=mock_db, studio_id=sample_studio.id, name="Studio Rossi Updated")

        assert result is not None
        assert result.name == "Studio Rossi Updated"

    @pytest.mark.asyncio
    async def test_update_studio_not_found(self, studio_service: StudioService, mock_db: AsyncMock) -> None:
        """Error: update non-existent studio returns None."""
        mock_db.get = AsyncMock(return_value=None)

        result = await studio_service.update(db=mock_db, studio_id=uuid4(), name="Ghost")

        assert result is None

    @pytest.mark.asyncio
    async def test_update_slug_conflict(
        self,
        studio_service: StudioService,
        mock_db: AsyncMock,
        sample_studio: Studio,
    ) -> None:
        """Error: slug conflict raises ValueError."""
        other_studio = Studio(id=uuid4(), name="Other", slug="taken-slug")
        mock_db.get = AsyncMock(return_value=sample_studio)
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=other_studio)))

        with pytest.raises(ValueError, match="slug.*già in uso"):
            await studio_service.update(db=mock_db, studio_id=sample_studio.id, slug="taken-slug")


class TestStudioServiceDeactivate:
    """Test StudioService.deactivate()."""

    @pytest.mark.asyncio
    async def test_deactivate_success(
        self,
        studio_service: StudioService,
        mock_db: AsyncMock,
        sample_studio: Studio,
    ) -> None:
        """Happy path: deactivate studio sets updated_at."""
        mock_db.get = AsyncMock(return_value=sample_studio)

        result = await studio_service.deactivate(db=mock_db, studio_id=sample_studio.id)

        assert result is not None
        mock_db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_deactivate_not_found(self, studio_service: StudioService, mock_db: AsyncMock) -> None:
        """Error: deactivate non-existent studio returns None."""
        mock_db.get = AsyncMock(return_value=None)

        result = await studio_service.deactivate(db=mock_db, studio_id=uuid4())

        assert result is None
