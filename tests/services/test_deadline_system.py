"""DEV-387: Deadline System Test Suite.

Tests DeadlineService CRUD, assignment, completion, and listing.
Patches model constructors to avoid EncryptedUser mapper errors.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.deadline import DeadlineSource, DeadlineType

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_db() -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.get = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def service():
    from app.services.deadline_service import DeadlineService

    return DeadlineService()


@pytest.fixture
def sample_deadline():
    d = MagicMock()
    d.id = uuid4()
    d.title = "Versamento IVA mensile"
    d.description = "Scadenza mensile IVA"
    d.deadline_type = DeadlineType.FISCALE
    d.source = DeadlineSource.TAX
    d.is_active = True
    d.created_at = datetime.now(UTC)
    return d


@pytest.fixture
def sample_client_deadline():
    cd = MagicMock()
    cd.id = uuid4()
    cd.client_id = 1
    cd.deadline_id = uuid4()
    cd.studio_id = uuid4()
    cd.is_completed = False
    cd.completed_at = None
    cd.notes = None
    return cd


# ---------------------------------------------------------------------------
# Enum tests
# ---------------------------------------------------------------------------


class TestDeadlineEnums:
    def test_deadline_type_values(self) -> None:
        assert DeadlineType.FISCALE == "fiscale"
        assert DeadlineType.ADEMPIMENTO == "adempimento"
        assert DeadlineType.CONTRIBUTIVO == "contributivo"
        assert DeadlineType.SOCIETARIO == "societario"
        assert len(DeadlineType) == 4

    def test_deadline_source_values(self) -> None:
        assert DeadlineSource.REGULATORY == "regulatory"
        assert DeadlineSource.TAX == "tax"
        assert DeadlineSource.CLIENT_SPECIFIC == "client_specific"
        assert len(DeadlineSource) == 3


# ---------------------------------------------------------------------------
# DeadlineService.create
# ---------------------------------------------------------------------------


class TestCreateDeadline:
    @pytest.mark.asyncio(loop_scope="function")
    async def test_create_deadline_success(self, service, mock_db) -> None:
        with patch("app.services.deadline_service.Deadline") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.id = uuid4()
            mock_instance.title = "Versamento IVA"
            mock_instance.deadline_type = DeadlineType.FISCALE
            mock_instance.source = DeadlineSource.TAX
            mock_cls.return_value = mock_instance

            from datetime import date

            result = await service.create(
                mock_db,
                title="Versamento IVA",
                deadline_type=DeadlineType.FISCALE,
                source=DeadlineSource.TAX,
                due_date=date(2026, 3, 16),
            )

        assert result.title == "Versamento IVA"
        mock_db.add.assert_called_once()
        mock_db.flush.assert_awaited_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_create_deadline_with_optional_fields(self, service, mock_db) -> None:
        with patch("app.services.deadline_service.Deadline") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.description = "Scadenza mensile"
            mock_instance.recurrence_rule = "MONTHLY_16"
            mock_cls.return_value = mock_instance

            from datetime import date

            result = await service.create(
                mock_db,
                title="IVA",
                deadline_type=DeadlineType.FISCALE,
                source=DeadlineSource.TAX,
                due_date=date(2026, 3, 16),
                description="Scadenza mensile",
                recurrence_rule="MONTHLY_16",
            )

        assert result.description == "Scadenza mensile"
        assert result.recurrence_rule == "MONTHLY_16"


# ---------------------------------------------------------------------------
# DeadlineService.get_by_id
# ---------------------------------------------------------------------------


class TestGetDeadlineById:
    @pytest.mark.asyncio(loop_scope="function")
    async def test_get_by_id_found(self, service, mock_db, sample_deadline) -> None:
        mock_db.get = AsyncMock(return_value=sample_deadline)
        result = await service.get_by_id(mock_db, deadline_id=sample_deadline.id)
        assert result is sample_deadline

    @pytest.mark.asyncio(loop_scope="function")
    async def test_get_by_id_not_found(self, service, mock_db) -> None:
        mock_db.get = AsyncMock(return_value=None)
        result = await service.get_by_id(mock_db, deadline_id=uuid4())
        assert result is None


# ---------------------------------------------------------------------------
# DeadlineService.list_active / list_upcoming
# ---------------------------------------------------------------------------


class TestListDeadlines:
    @pytest.mark.asyncio(loop_scope="function")
    async def test_list_active_no_filters(self, service, mock_db) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.deadline_service.select"):
            result = await service.list_active(mock_db)

        assert len(result) == 2

    @pytest.mark.asyncio(loop_scope="function")
    async def test_list_active_with_type_filter(self, service, mock_db) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.deadline_service.select"):
            result = await service.list_active(mock_db, deadline_type=DeadlineType.FISCALE)

        assert len(result) == 1

    @pytest.mark.asyncio(loop_scope="function")
    async def test_list_upcoming(self, service, mock_db) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [MagicMock(), MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.deadline_service.select"), patch("app.services.deadline_service.and_"):
            result = await service.list_upcoming(mock_db, days_ahead=7)

        assert len(result) == 3


# ---------------------------------------------------------------------------
# DeadlineService.update / deactivate
# ---------------------------------------------------------------------------


class TestUpdateDeadline:
    @pytest.mark.asyncio(loop_scope="function")
    async def test_update_deadline_fields(self, service, mock_db, sample_deadline) -> None:
        mock_db.get = AsyncMock(return_value=sample_deadline)

        result = await service.update(mock_db, deadline_id=sample_deadline.id, title="Updated Title")

        assert result is sample_deadline
        assert sample_deadline.title == "Updated Title"
        mock_db.flush.assert_awaited_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_update_not_found(self, service, mock_db) -> None:
        mock_db.get = AsyncMock(return_value=None)
        result = await service.update(mock_db, deadline_id=uuid4(), title="New")
        assert result is None

    @pytest.mark.asyncio(loop_scope="function")
    async def test_deactivate_success(self, service, mock_db, sample_deadline) -> None:
        mock_db.get = AsyncMock(return_value=sample_deadline)
        result = await service.deactivate(mock_db, deadline_id=sample_deadline.id)
        assert result is sample_deadline
        assert sample_deadline.is_active is False

    @pytest.mark.asyncio(loop_scope="function")
    async def test_deactivate_not_found(self, service, mock_db) -> None:
        mock_db.get = AsyncMock(return_value=None)
        result = await service.deactivate(mock_db, deadline_id=uuid4())
        assert result is None


# ---------------------------------------------------------------------------
# DeadlineService.assign_to_client
# ---------------------------------------------------------------------------


class TestAssignToClient:
    @pytest.mark.asyncio(loop_scope="function")
    async def test_assign_success(self, service, mock_db) -> None:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        deadline_id = uuid4()
        studio_id = uuid4()

        with (
            patch("app.services.deadline_service.ClientDeadline") as mock_cls,
            patch("app.services.deadline_service.select"),
            patch("app.services.deadline_service.and_"),
        ):
            mock_instance = MagicMock()
            mock_instance.client_id = 1
            mock_instance.deadline_id = deadline_id
            mock_instance.studio_id = studio_id
            mock_cls.return_value = mock_instance

            result = await service.assign_to_client(mock_db, client_id=1, deadline_id=deadline_id, studio_id=studio_id)

        assert result.client_id == 1
        mock_db.add.assert_called_once()
        mock_db.flush.assert_awaited_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_assign_duplicate_raises(self, service, mock_db) -> None:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        with (
            patch("app.services.deadline_service.select"),
            patch("app.services.deadline_service.and_"),
            pytest.raises(ValueError, match="già assegnata"),
        ):
            await service.assign_to_client(mock_db, client_id=1, deadline_id=uuid4(), studio_id=uuid4())


# ---------------------------------------------------------------------------
# DeadlineService.mark_completed
# ---------------------------------------------------------------------------


class TestMarkCompleted:
    @pytest.mark.asyncio(loop_scope="function")
    async def test_mark_completed(self, service, mock_db, sample_client_deadline) -> None:
        mock_db.get = AsyncMock(return_value=sample_client_deadline)
        result = await service.mark_completed(mock_db, client_deadline_id=sample_client_deadline.id)
        assert result is sample_client_deadline
        assert sample_client_deadline.is_completed is True
        assert sample_client_deadline.completed_at is not None

    @pytest.mark.asyncio(loop_scope="function")
    async def test_mark_completed_not_found(self, service, mock_db) -> None:
        mock_db.get = AsyncMock(return_value=None)
        result = await service.mark_completed(mock_db, client_deadline_id=uuid4())
        assert result is None


# ---------------------------------------------------------------------------
# DeadlineService.list_by_studio / list_by_client
# ---------------------------------------------------------------------------


class TestListByStudioAndClient:
    @pytest.mark.asyncio(loop_scope="function")
    async def test_list_by_studio(self, service, mock_db) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.deadline_service.select"):
            result = await service.list_by_studio(mock_db, studio_id=uuid4())

        assert len(result) == 2

    @pytest.mark.asyncio(loop_scope="function")
    async def test_list_by_studio_completed_filter(self, service, mock_db) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.deadline_service.select"):
            result = await service.list_by_studio(mock_db, studio_id=uuid4(), completed=True)

        assert len(result) == 1

    @pytest.mark.asyncio(loop_scope="function")
    async def test_list_by_client(self, service, mock_db) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [MagicMock(), MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.deadline_service.select"), patch("app.services.deadline_service.and_"):
            result = await service.list_by_client(mock_db, client_id=1, studio_id=uuid4())

        assert len(result) == 3

    @pytest.mark.asyncio(loop_scope="function")
    async def test_list_by_client_empty(self, service, mock_db) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.deadline_service.select"), patch("app.services.deadline_service.and_"):
            result = await service.list_by_client(mock_db, client_id=999, studio_id=uuid4())

        assert result == []
