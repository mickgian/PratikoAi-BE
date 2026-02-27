"""DEV-381: Tests for DeadlineService CRUD operations.

Tests cover:
- Deadline CRUD (create, get_by_id, list, update)
- Filtering by type and studio isolation
- Client-deadline assignment and completion tracking
- Duplicate assignment prevention
"""

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.deadline import ClientDeadline, Deadline, DeadlineSource, DeadlineType
from app.services.deadline_service import DeadlineService


@pytest.fixture
def deadline_service() -> DeadlineService:
    return DeadlineService()


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
def sample_deadline() -> Deadline:
    return Deadline(
        id=uuid4(),
        title="Scadenza IVA trimestrale",
        description="Versamento IVA trimestrale per regime ordinario.",
        deadline_type=DeadlineType.FISCALE,
        source=DeadlineSource.REGULATORY,
        due_date=date(2026, 3, 16),
        recurrence_rule="QUARTERLY_16",
        is_active=True,
    )


@pytest.fixture
def sample_client_deadline(studio_id, sample_deadline) -> ClientDeadline:
    return ClientDeadline(
        id=uuid4(),
        client_id=1,
        deadline_id=sample_deadline.id,
        studio_id=studio_id,
        is_completed=False,
        completed_at=None,
        notes=None,
    )


class TestDeadlineServiceCreate:
    """Test DeadlineService.create()."""

    @pytest.mark.asyncio
    async def test_create_deadline_success(self, deadline_service: DeadlineService, mock_db: AsyncMock) -> None:
        """Happy path: create a deadline with valid data."""
        result = await deadline_service.create(
            db=mock_db,
            title="Scadenza IVA trimestrale",
            description="Versamento IVA trimestrale.",
            deadline_type=DeadlineType.FISCALE,
            source=DeadlineSource.REGULATORY,
            due_date=date(2026, 3, 16),
        )

        assert result.title == "Scadenza IVA trimestrale"
        assert result.deadline_type == DeadlineType.FISCALE
        assert result.source == DeadlineSource.REGULATORY
        assert result.is_active is True
        mock_db.add.assert_called_once()
        mock_db.flush.assert_awaited_once()


class TestDeadlineServiceGetById:
    """Test DeadlineService.get_by_id()."""

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self,
        deadline_service: DeadlineService,
        mock_db: AsyncMock,
        sample_deadline: Deadline,
    ) -> None:
        """Happy path: retrieve existing deadline."""
        mock_db.get = AsyncMock(return_value=sample_deadline)

        result = await deadline_service.get_by_id(db=mock_db, deadline_id=sample_deadline.id)

        assert result is not None
        assert result.id == sample_deadline.id
        assert result.title == "Scadenza IVA trimestrale"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, deadline_service: DeadlineService, mock_db: AsyncMock) -> None:
        """Error: non-existent deadline returns None."""
        mock_db.get = AsyncMock(return_value=None)

        result = await deadline_service.get_by_id(db=mock_db, deadline_id=uuid4())

        assert result is None


class TestDeadlineServiceList:
    """Test DeadlineService listing methods."""

    @pytest.mark.asyncio
    async def test_list_by_studio(
        self,
        deadline_service: DeadlineService,
        mock_db: AsyncMock,
        studio_id,
        sample_client_deadline: ClientDeadline,
    ) -> None:
        """Happy path: list client-deadline associations with studio isolation."""
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_client_deadline])))
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await deadline_service.list_by_studio(db=mock_db, studio_id=studio_id)

        assert len(result) == 1
        assert result[0].studio_id == studio_id

    @pytest.mark.asyncio
    async def test_list_by_type_filter(
        self,
        deadline_service: DeadlineService,
        mock_db: AsyncMock,
        sample_deadline: Deadline,
    ) -> None:
        """Filter active deadlines by type."""
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_deadline])))
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await deadline_service.list_active(
            db=mock_db,
            deadline_type=DeadlineType.FISCALE,
        )

        assert len(result) == 1
        assert result[0].deadline_type == DeadlineType.FISCALE


class TestDeadlineServiceUpdate:
    """Test DeadlineService.update()."""

    @pytest.mark.asyncio
    async def test_update_deadline(
        self,
        deadline_service: DeadlineService,
        mock_db: AsyncMock,
        sample_deadline: Deadline,
    ) -> None:
        """Happy path: update deadline title and due_date."""
        mock_db.get = AsyncMock(return_value=sample_deadline)

        result = await deadline_service.update(
            db=mock_db,
            deadline_id=sample_deadline.id,
            title="Scadenza IVA aggiornata",
            due_date=date(2026, 6, 16),
        )

        assert result is not None
        assert result.title == "Scadenza IVA aggiornata"

    @pytest.mark.asyncio
    async def test_update_not_found(self, deadline_service: DeadlineService, mock_db: AsyncMock) -> None:
        """Error: update non-existent deadline returns None."""
        mock_db.get = AsyncMock(return_value=None)

        result = await deadline_service.update(
            db=mock_db,
            deadline_id=uuid4(),
            title="Fantasma",
        )

        assert result is None


class TestDeadlineServiceClientAssignment:
    """Test DeadlineService client-deadline operations."""

    @pytest.mark.asyncio
    async def test_mark_completed(
        self,
        deadline_service: DeadlineService,
        mock_db: AsyncMock,
        sample_client_deadline: ClientDeadline,
    ) -> None:
        """Happy path: mark a client deadline as completed."""
        mock_db.get = AsyncMock(return_value=sample_client_deadline)

        result = await deadline_service.mark_completed(
            db=mock_db,
            client_deadline_id=sample_client_deadline.id,
        )

        assert result is not None
        assert result.is_completed is True
        assert result.completed_at is not None

    @pytest.mark.asyncio
    async def test_assign_deadline_to_client(
        self,
        deadline_service: DeadlineService,
        mock_db: AsyncMock,
        studio_id,
        sample_deadline: Deadline,
    ) -> None:
        """Happy path: create client-deadline association."""
        # No existing assignment
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

        result = await deadline_service.assign_to_client(
            db=mock_db,
            client_id=1,
            deadline_id=sample_deadline.id,
            studio_id=studio_id,
        )

        assert result.client_id == 1
        assert result.deadline_id == sample_deadline.id
        assert result.studio_id == studio_id
        assert result.is_completed is False
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_duplicate_assignment_raises(
        self,
        deadline_service: DeadlineService,
        mock_db: AsyncMock,
        studio_id,
        sample_deadline: Deadline,
        sample_client_deadline: ClientDeadline,
    ) -> None:
        """Error: duplicate client-deadline assignment raises ValueError."""
        mock_db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=sample_client_deadline))
        )

        with pytest.raises(ValueError, match="già assegnata"):
            await deadline_service.assign_to_client(
                db=mock_db,
                client_id=1,
                deadline_id=sample_deadline.id,
                studio_id=studio_id,
            )
