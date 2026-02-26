"""DEV-380: Tests for Deadline and ClientDeadline SQLModels."""

from datetime import UTC, date, datetime, timezone
from uuid import uuid4

import pytest

from app.models.deadline import ClientDeadline, Deadline, DeadlineSource, DeadlineType


class TestDeadlineCreation:
    """Test Deadline model creation and field defaults."""

    def test_deadline_creation_valid(self) -> None:
        """Valid deadline with required fields."""
        dl = Deadline(
            title="Scadenza IVA trimestrale",
            deadline_type=DeadlineType.FISCALE,
            source=DeadlineSource.REGULATORY,
            due_date=date(2026, 3, 16),
        )

        assert dl.title == "Scadenza IVA trimestrale"
        assert dl.deadline_type == DeadlineType.FISCALE
        assert dl.source == DeadlineSource.REGULATORY
        assert dl.id is not None
        assert dl.is_active is True

    def test_deadline_defaults(self) -> None:
        """Defaults are set correctly."""
        dl = Deadline(
            title="Test",
            deadline_type=DeadlineType.ADEMPIMENTO,
            source=DeadlineSource.TAX,
            due_date=date(2026, 6, 30),
        )

        assert dl.is_active is True
        assert dl.recurrence_rule is None
        assert dl.description is None

    def test_deadline_with_recurrence(self) -> None:
        """Deadline with recurrence rule."""
        dl = Deadline(
            title="F24 mensile",
            deadline_type=DeadlineType.FISCALE,
            source=DeadlineSource.TAX,
            due_date=date(2026, 1, 16),
            recurrence_rule="MONTHLY_16",
            description="Versamento F24 entro il 16 di ogni mese.",
        )

        assert dl.recurrence_rule == "MONTHLY_16"
        assert dl.description is not None

    def test_deadline_uuid_uniqueness(self) -> None:
        """Two deadlines get different UUIDs."""
        d1 = Deadline(
            title="A",
            deadline_type=DeadlineType.FISCALE,
            source=DeadlineSource.REGULATORY,
            due_date=date(2026, 1, 1),
        )
        d2 = Deadline(
            title="B",
            deadline_type=DeadlineType.FISCALE,
            source=DeadlineSource.REGULATORY,
            due_date=date(2026, 1, 1),
        )
        assert d1.id != d2.id

    def test_deadline_repr(self) -> None:
        """__repr__ includes title and type."""
        dl = Deadline(
            title="IMU Seconda Casa",
            deadline_type=DeadlineType.FISCALE,
            source=DeadlineSource.TAX,
            due_date=date(2026, 6, 16),
        )
        assert "IMU Seconda Casa" in repr(dl)


class TestClientDeadlineCreation:
    """Test ClientDeadline many-to-many model."""

    def test_client_deadline_creation(self) -> None:
        """Valid client-deadline association."""
        cd = ClientDeadline(
            client_id=1,
            deadline_id=uuid4(),
            studio_id=uuid4(),
        )

        assert cd.client_id == 1
        assert cd.is_completed is False

    def test_client_deadline_completed(self) -> None:
        """Mark client deadline as completed."""
        cd = ClientDeadline(
            client_id=1,
            deadline_id=uuid4(),
            studio_id=uuid4(),
            is_completed=True,
            completed_at=datetime.now(UTC),
        )

        assert cd.is_completed is True
        assert cd.completed_at is not None

    def test_client_deadline_notes(self) -> None:
        """Client deadline with notes."""
        cd = ClientDeadline(
            client_id=1,
            deadline_id=uuid4(),
            studio_id=uuid4(),
            notes="Documentazione inviata.",
        )

        assert cd.notes == "Documentazione inviata."
