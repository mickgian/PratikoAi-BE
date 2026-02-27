"""DEV-375: Tests for BreachNotificationService — Breach lifecycle management.

Tests cover:
- Breach report creation
- Status transitions (DETECTED -> INVESTIGATING -> CONTAINED -> AUTHORITY_NOTIFIED -> RESOLVED)
- Authority notification within GDPR 72h deadline
- Invalid status transitions
- Overdue notification detection
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.breach_notification import BreachNotification, BreachSeverity, BreachStatus
from app.services.breach_notification_service import BreachNotificationService


@pytest.fixture
def breach_service() -> BreachNotificationService:
    return BreachNotificationService()


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
def sample_breach(studio_id) -> BreachNotification:
    return BreachNotification(
        id=uuid4(),
        studio_id=studio_id,
        title="Accesso non autorizzato ai dati clienti",
        description="Rilevato accesso non autorizzato al database clienti.",
        severity=BreachSeverity.HIGH,
        status=BreachStatus.DETECTED,
        reported_by=1,
        detected_at=datetime.now(UTC),
        affected_records_count=150,
        data_categories=["dati_personali", "codice_fiscale"],
    )


class TestBreachNotificationServiceCreate:
    """Test BreachNotificationService.create()."""

    @pytest.mark.asyncio
    async def test_create_breach_report(
        self,
        breach_service: BreachNotificationService,
        mock_db: AsyncMock,
        studio_id,
    ) -> None:
        """Happy path: report a new data breach."""
        result = await breach_service.create(
            db=mock_db,
            studio_id=studio_id,
            title="Accesso non autorizzato",
            description="Rilevato accesso non autorizzato al sistema.",
            severity=BreachSeverity.HIGH,
            reported_by=1,
            affected_records_count=150,
            data_categories=["dati_personali"],
        )

        assert result.title == "Accesso non autorizzato"
        assert result.severity == BreachSeverity.HIGH
        assert result.status == BreachStatus.DETECTED
        assert result.studio_id == studio_id
        mock_db.add.assert_called_once()
        mock_db.flush.assert_awaited_once()


class TestBreachNotificationServiceStatusTransitions:
    """Test BreachNotificationService status transitions."""

    @pytest.mark.asyncio
    async def test_update_status_investigating(
        self,
        breach_service: BreachNotificationService,
        mock_db: AsyncMock,
        sample_breach: BreachNotification,
        studio_id,
    ) -> None:
        """Happy path: DETECTED -> INVESTIGATING."""
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=sample_breach)))

        result = await breach_service.update_status(
            db=mock_db,
            breach_id=sample_breach.id,
            studio_id=studio_id,
            new_status=BreachStatus.INVESTIGATING,
        )

        assert result is not None
        assert result.status == BreachStatus.INVESTIGATING

    @pytest.mark.asyncio
    async def test_update_status_contained(
        self,
        breach_service: BreachNotificationService,
        mock_db: AsyncMock,
        sample_breach: BreachNotification,
        studio_id,
    ) -> None:
        """Happy path: INVESTIGATING -> CONTAINED."""
        sample_breach.status = BreachStatus.INVESTIGATING
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=sample_breach)))

        result = await breach_service.update_status(
            db=mock_db,
            breach_id=sample_breach.id,
            studio_id=studio_id,
            new_status=BreachStatus.CONTAINED,
        )

        assert result is not None
        assert result.status == BreachStatus.CONTAINED

    @pytest.mark.asyncio
    async def test_notify_authority(
        self,
        breach_service: BreachNotificationService,
        mock_db: AsyncMock,
        sample_breach: BreachNotification,
        studio_id,
    ) -> None:
        """Happy path: mark authority notified within 72h GDPR deadline."""
        sample_breach.status = BreachStatus.CONTAINED
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=sample_breach)))

        result = await breach_service.update_status(
            db=mock_db,
            breach_id=sample_breach.id,
            studio_id=studio_id,
            new_status=BreachStatus.AUTHORITY_NOTIFIED,
        )

        assert result is not None
        assert result.status == BreachStatus.AUTHORITY_NOTIFIED
        assert result.authority_notified_at is not None

    @pytest.mark.asyncio
    async def test_resolve_breach(
        self,
        breach_service: BreachNotificationService,
        mock_db: AsyncMock,
        sample_breach: BreachNotification,
        studio_id,
    ) -> None:
        """Happy path: mark breach as resolved."""
        sample_breach.status = BreachStatus.AUTHORITY_NOTIFIED
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=sample_breach)))

        result = await breach_service.update_status(
            db=mock_db,
            breach_id=sample_breach.id,
            studio_id=studio_id,
            new_status=BreachStatus.RESOLVED,
        )

        assert result is not None
        assert result.status == BreachStatus.RESOLVED
        assert result.resolved_at is not None

    @pytest.mark.asyncio
    async def test_invalid_transition(
        self,
        breach_service: BreachNotificationService,
        mock_db: AsyncMock,
        sample_breach: BreachNotification,
        studio_id,
    ) -> None:
        """Error: invalid status transition raises ValueError."""
        # DETECTED -> RESOLVED is not a valid direct transition
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=sample_breach)))

        with pytest.raises(ValueError, match="non.*valida"):
            await breach_service.update_status(
                db=mock_db,
                breach_id=sample_breach.id,
                studio_id=studio_id,
                new_status=BreachStatus.RESOLVED,
            )


class TestBreachNotificationServiceOverdue:
    """Test BreachNotificationService overdue detection."""

    @pytest.mark.asyncio
    async def test_check_overdue_notifications(
        self,
        breach_service: BreachNotificationService,
        mock_db: AsyncMock,
        studio_id,
    ) -> None:
        """Find breaches past the 72h GDPR notification deadline."""
        overdue_breach = BreachNotification(
            id=uuid4(),
            studio_id=studio_id,
            title="Breach vecchio non notificato",
            description="Breach rilevato 4 giorni fa senza notifica.",
            severity=BreachSeverity.CRITICAL,
            status=BreachStatus.INVESTIGATING,
            reported_by=1,
            detected_at=datetime.now(UTC) - timedelta(hours=96),
            authority_notified_at=None,
        )

        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[overdue_breach])))
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await breach_service.check_overdue_notifications(db=mock_db)

        assert len(result) == 1
        assert result[0].authority_notified_at is None
        # Verify the breach is past the 72h deadline
        assert result[0].notification_deadline < datetime.now(UTC)
