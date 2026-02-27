"""Tests for Deadlines API endpoints (DEV-385).

TDD: Tests written FIRST before implementation.
Tests the deadline management endpoints.

Endpoints tested:
- GET  /deadlines/upcoming                           (list upcoming deadlines)
- GET  /deadlines/upcoming?days_ahead=7              (filter by days)
- GET  /deadlines/{deadline_id}                      (get single deadline)
- POST /deadlines                                    (create deadline)
- GET  /deadlines/studio/{studio_id}/client-deadlines (list client deadlines)
- PUT  /deadlines/client-deadlines/{id}/complete     (mark complete)
- 404  on non-existent deadline
"""

from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from app.models.deadline import DeadlineSource, DeadlineType

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def studio_id() -> UUID:
    """Fixed studio UUID for tenant isolation."""
    return uuid4()


@pytest.fixture
def mock_db() -> AsyncMock:
    """Mock async database session."""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.rollback = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.fixture
def deadline_id() -> UUID:
    """Fixed deadline UUID."""
    return uuid4()


@pytest.fixture
def sample_deadline(deadline_id: UUID) -> MagicMock:
    """Return a mock Deadline."""
    dl = MagicMock()
    dl.id = deadline_id
    dl.title = "Versamento IVA trimestrale"
    dl.description = "Scadenza versamento IVA Q1"
    dl.deadline_type = DeadlineType.FISCALE
    dl.source = DeadlineSource.TAX
    dl.due_date = date.today() + timedelta(days=7)
    dl.recurrence_rule = None
    dl.is_active = True
    dl.created_at = datetime.now(UTC)
    dl.updated_at = None
    return dl


@pytest.fixture
def sample_deadline_30(deadline_id: UUID) -> MagicMock:
    """Return a mock Deadline due in 30 days."""
    dl = MagicMock()
    dl.id = uuid4()
    dl.title = "Dichiarazione annuale redditi"
    dl.description = "Dichiarazione dei redditi persone fisiche"
    dl.deadline_type = DeadlineType.ADEMPIMENTO
    dl.source = DeadlineSource.REGULATORY
    dl.due_date = date.today() + timedelta(days=30)
    dl.recurrence_rule = None
    dl.is_active = True
    dl.created_at = datetime.now(UTC)
    dl.updated_at = None
    return dl


@pytest.fixture
def sample_client_deadline(studio_id: UUID, deadline_id: UUID) -> MagicMock:
    """Return a mock ClientDeadline."""
    cd = MagicMock()
    cd.id = uuid4()
    cd.client_id = 1
    cd.deadline_id = deadline_id
    cd.studio_id = studio_id
    cd.is_completed = False
    cd.completed_at = None
    cd.notes = "In attesa di documentazione"
    cd.created_at = datetime.now(UTC)
    return cd


@pytest.fixture
def completed_client_deadline(studio_id: UUID, deadline_id: UUID) -> MagicMock:
    """Return a mock completed ClientDeadline."""
    cd = MagicMock()
    cd.id = uuid4()
    cd.client_id = 2
    cd.deadline_id = deadline_id
    cd.studio_id = studio_id
    cd.is_completed = True
    cd.completed_at = datetime.now(UTC)
    cd.notes = None
    cd.created_at = datetime.now(UTC)
    return cd


# ---------------------------------------------------------------------------
# GET /deadlines/upcoming — List upcoming deadlines
# ---------------------------------------------------------------------------


class TestListUpcomingDeadlines:
    """Tests for GET /deadlines/upcoming endpoint."""

    @pytest.mark.asyncio
    async def test_list_upcoming_success(
        self,
        mock_db: AsyncMock,
        sample_deadline: MagicMock,
    ) -> None:
        """Happy path: returns list of upcoming deadlines with default days_ahead=30."""
        from app.api.v1.deadlines import list_upcoming_deadlines

        with patch("app.api.v1.deadlines.deadline_service") as mock_svc:
            mock_svc.list_upcoming = AsyncMock(return_value=[sample_deadline])

            result = await list_upcoming_deadlines(
                days_ahead=30,
                deadline_type=None,
                db=mock_db,
            )

        assert len(result) == 1
        assert result[0].title == "Versamento IVA trimestrale"
        mock_svc.list_upcoming.assert_awaited_once_with(mock_db, days_ahead=30)

    @pytest.mark.asyncio
    async def test_list_upcoming_with_days_ahead_filter(
        self,
        mock_db: AsyncMock,
        sample_deadline: MagicMock,
    ) -> None:
        """Happy path: filters by days_ahead=7."""
        from app.api.v1.deadlines import list_upcoming_deadlines

        with patch("app.api.v1.deadlines.deadline_service") as mock_svc:
            mock_svc.list_upcoming = AsyncMock(return_value=[sample_deadline])

            result = await list_upcoming_deadlines(
                days_ahead=7,
                deadline_type=None,
                db=mock_db,
            )

        assert len(result) == 1
        mock_svc.list_upcoming.assert_awaited_once_with(mock_db, days_ahead=7)

    @pytest.mark.asyncio
    async def test_list_upcoming_empty(
        self,
        mock_db: AsyncMock,
    ) -> None:
        """Edge case: no upcoming deadlines returns empty list."""
        from app.api.v1.deadlines import list_upcoming_deadlines

        with patch("app.api.v1.deadlines.deadline_service") as mock_svc:
            mock_svc.list_upcoming = AsyncMock(return_value=[])

            result = await list_upcoming_deadlines(
                days_ahead=30,
                deadline_type=None,
                db=mock_db,
            )

        assert result == []

    @pytest.mark.asyncio
    async def test_list_upcoming_with_type_filter(
        self,
        mock_db: AsyncMock,
        sample_deadline: MagicMock,
    ) -> None:
        """Happy path: filter by deadline_type."""
        from app.api.v1.deadlines import list_upcoming_deadlines

        with patch("app.api.v1.deadlines.deadline_service") as mock_svc:
            mock_svc.list_upcoming = AsyncMock(return_value=[sample_deadline])

            result = await list_upcoming_deadlines(
                days_ahead=30,
                deadline_type=DeadlineType.FISCALE,
                db=mock_db,
            )

        assert len(result) == 1


# ---------------------------------------------------------------------------
# GET /deadlines/{deadline_id} — Get single deadline
# ---------------------------------------------------------------------------


class TestGetDeadline:
    """Tests for GET /deadlines/{deadline_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_deadline_success(
        self,
        mock_db: AsyncMock,
        deadline_id: UUID,
        sample_deadline: MagicMock,
    ) -> None:
        """Happy path: returns single deadline."""
        from app.api.v1.deadlines import get_deadline

        with patch("app.api.v1.deadlines.deadline_service") as mock_svc:
            mock_svc.get_by_id = AsyncMock(return_value=sample_deadline)

            result = await get_deadline(
                deadline_id=deadline_id,
                db=mock_db,
            )

        assert result.title == "Versamento IVA trimestrale"
        mock_svc.get_by_id.assert_awaited_once_with(mock_db, deadline_id=deadline_id)

    @pytest.mark.asyncio
    async def test_get_deadline_not_found_returns_404(
        self,
        mock_db: AsyncMock,
    ) -> None:
        """Error case: nonexistent deadline raises 404."""
        from app.api.v1.deadlines import get_deadline

        fake_id = uuid4()

        with patch("app.api.v1.deadlines.deadline_service") as mock_svc:
            mock_svc.get_by_id = AsyncMock(return_value=None)

            with pytest.raises(HTTPException) as exc_info:
                await get_deadline(
                    deadline_id=fake_id,
                    db=mock_db,
                )

        assert exc_info.value.status_code == 404
        assert "non trovat" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# POST /deadlines — Create deadline
# ---------------------------------------------------------------------------


class TestCreateDeadline:
    """Tests for POST /deadlines endpoint."""

    @pytest.mark.asyncio
    async def test_create_deadline_success(
        self,
        mock_db: AsyncMock,
        sample_deadline: MagicMock,
    ) -> None:
        """Happy path: creates a new deadline."""
        from app.api.v1.deadlines import create_deadline
        from app.schemas.deadline import DeadlineCreateRequest

        body = DeadlineCreateRequest(
            title="Nuovo adempimento fiscale",
            description="Test description",
            deadline_type="fiscale",
            source="tax",
            due_date=date.today() + timedelta(days=14),
        )

        with patch("app.api.v1.deadlines.deadline_service") as mock_svc:
            mock_svc.create = AsyncMock(return_value=sample_deadline)

            result = await create_deadline(
                body=body,
                db=mock_db,
            )

        assert result.title == "Versamento IVA trimestrale"
        mock_svc.create.assert_awaited_once()
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_deadline_with_recurrence(
        self,
        mock_db: AsyncMock,
        sample_deadline: MagicMock,
    ) -> None:
        """Happy path: creates deadline with recurrence rule."""
        from app.api.v1.deadlines import create_deadline
        from app.schemas.deadline import DeadlineCreateRequest

        body = DeadlineCreateRequest(
            title="IVA mensile",
            deadline_type="fiscale",
            source="tax",
            due_date=date.today() + timedelta(days=30),
            recurrence_rule="MONTHLY_16",
        )

        with patch("app.api.v1.deadlines.deadline_service") as mock_svc:
            sample_deadline.recurrence_rule = "MONTHLY_16"
            mock_svc.create = AsyncMock(return_value=sample_deadline)

            result = await create_deadline(
                body=body,
                db=mock_db,
            )

        mock_svc.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_deadline_service_error(
        self,
        mock_db: AsyncMock,
    ) -> None:
        """Error case: service raises ValueError returns 400."""
        from app.api.v1.deadlines import create_deadline
        from app.schemas.deadline import DeadlineCreateRequest

        body = DeadlineCreateRequest(
            title="Test",
            deadline_type="fiscale",
            source="tax",
            due_date=date.today(),
        )

        with patch("app.api.v1.deadlines.deadline_service") as mock_svc:
            mock_svc.create = AsyncMock(side_effect=ValueError("Tipo scadenza non valido."))

            with pytest.raises(HTTPException) as exc_info:
                await create_deadline(
                    body=body,
                    db=mock_db,
                )

        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# GET /deadlines/studio/{studio_id}/client-deadlines — List client deadlines
# ---------------------------------------------------------------------------


class TestListClientDeadlines:
    """Tests for GET /deadlines/studio/{studio_id}/client-deadlines endpoint."""

    @pytest.mark.asyncio
    async def test_list_client_deadlines_success(
        self,
        mock_db: AsyncMock,
        studio_id: UUID,
        sample_client_deadline: MagicMock,
    ) -> None:
        """Happy path: returns client deadlines for studio."""
        from app.api.v1.deadlines import list_client_deadlines

        with patch("app.api.v1.deadlines.deadline_service") as mock_svc:
            mock_svc.list_by_studio = AsyncMock(return_value=[sample_client_deadline])

            result = await list_client_deadlines(
                studio_id=studio_id,
                completed=None,
                db=mock_db,
            )

        assert len(result) == 1
        mock_svc.list_by_studio.assert_awaited_once_with(mock_db, studio_id=studio_id, completed=None)

    @pytest.mark.asyncio
    async def test_list_client_deadlines_filter_completed(
        self,
        mock_db: AsyncMock,
        studio_id: UUID,
        completed_client_deadline: MagicMock,
    ) -> None:
        """Happy path: filter by completed=True."""
        from app.api.v1.deadlines import list_client_deadlines

        with patch("app.api.v1.deadlines.deadline_service") as mock_svc:
            mock_svc.list_by_studio = AsyncMock(return_value=[completed_client_deadline])

            result = await list_client_deadlines(
                studio_id=studio_id,
                completed=True,
                db=mock_db,
            )

        assert len(result) == 1
        mock_svc.list_by_studio.assert_awaited_once_with(mock_db, studio_id=studio_id, completed=True)

    @pytest.mark.asyncio
    async def test_list_client_deadlines_empty(
        self,
        mock_db: AsyncMock,
        studio_id: UUID,
    ) -> None:
        """Edge case: no client deadlines returns empty list."""
        from app.api.v1.deadlines import list_client_deadlines

        with patch("app.api.v1.deadlines.deadline_service") as mock_svc:
            mock_svc.list_by_studio = AsyncMock(return_value=[])

            result = await list_client_deadlines(
                studio_id=studio_id,
                completed=None,
                db=mock_db,
            )

        assert result == []


# ---------------------------------------------------------------------------
# PUT /deadlines/client-deadlines/{id}/complete — Mark as complete
# ---------------------------------------------------------------------------


class TestMarkClientDeadlineComplete:
    """Tests for PUT /deadlines/client-deadlines/{id}/complete endpoint."""

    @pytest.mark.asyncio
    async def test_mark_complete_success(
        self,
        mock_db: AsyncMock,
        studio_id: UUID,
        sample_client_deadline: MagicMock,
    ) -> None:
        """Happy path: marks client deadline as complete."""
        from app.api.v1.deadlines import mark_client_deadline_complete

        sample_client_deadline.is_completed = True
        sample_client_deadline.completed_at = datetime.now(UTC)

        with patch("app.api.v1.deadlines.deadline_service") as mock_svc:
            mock_svc.mark_completed = AsyncMock(return_value=sample_client_deadline)

            result = await mark_client_deadline_complete(
                client_deadline_id=sample_client_deadline.id,
                x_studio_id=studio_id,
                db=mock_db,
            )

        assert result.is_completed is True
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_mark_complete_not_found_returns_404(
        self,
        mock_db: AsyncMock,
        studio_id: UUID,
    ) -> None:
        """Error case: nonexistent client deadline raises 404."""
        from app.api.v1.deadlines import mark_client_deadline_complete

        fake_id = uuid4()

        with patch("app.api.v1.deadlines.deadline_service") as mock_svc:
            mock_svc.mark_completed = AsyncMock(return_value=None)

            with pytest.raises(HTTPException) as exc_info:
                await mark_client_deadline_complete(
                    client_deadline_id=fake_id,
                    x_studio_id=studio_id,
                    db=mock_db,
                )

        assert exc_info.value.status_code == 404
        assert "non trovat" in exc_info.value.detail.lower()
