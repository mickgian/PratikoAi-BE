"""DEV-374: Tests for Data Breach Notification Model."""

from datetime import UTC, datetime, timezone
from uuid import uuid4

import pytest

from app.models.breach_notification import BreachNotification, BreachSeverity, BreachStatus


class TestBreachNotificationCreation:
    """Test BreachNotification model creation and field defaults."""

    def test_breach_creation_valid(self) -> None:
        """Valid breach notification with required fields."""
        breach = BreachNotification(
            studio_id=uuid4(),
            title="Accesso non autorizzato",
            description="Rilevato accesso non autorizzato ai dati dei clienti.",
            severity=BreachSeverity.HIGH,
            reported_by=1,
        )

        assert breach.title == "Accesso non autorizzato"
        assert breach.severity == BreachSeverity.HIGH
        assert breach.status == BreachStatus.DETECTED
        assert breach.id is not None

    def test_breach_status_default(self) -> None:
        """Status defaults to DETECTED."""
        breach = BreachNotification(
            studio_id=uuid4(),
            title="Test",
            description="Test description.",
            severity=BreachSeverity.LOW,
            reported_by=1,
        )
        assert breach.status == BreachStatus.DETECTED

    def test_breach_with_affected_count(self) -> None:
        """Breach with affected records count."""
        breach = BreachNotification(
            studio_id=uuid4(),
            title="Data leak",
            description="Perdita dati.",
            severity=BreachSeverity.CRITICAL,
            reported_by=1,
            affected_records_count=150,
            data_categories=["personal_data", "tax_id"],
        )

        assert breach.affected_records_count == 150
        assert "tax_id" in breach.data_categories

    def test_breach_notification_timestamps(self) -> None:
        """Breach with notification timestamps."""
        now = datetime.now(UTC)
        breach = BreachNotification(
            studio_id=uuid4(),
            title="Test breach",
            description="Test.",
            severity=BreachSeverity.MEDIUM,
            reported_by=1,
            authority_notified_at=now,
        )

        assert breach.authority_notified_at == now

    def test_breach_uuid_uniqueness(self) -> None:
        """Two breaches get different UUIDs."""
        b1 = BreachNotification(
            studio_id=uuid4(), title="A", description="a", severity=BreachSeverity.LOW, reported_by=1
        )
        b2 = BreachNotification(
            studio_id=uuid4(), title="B", description="b", severity=BreachSeverity.LOW, reported_by=1
        )
        assert b1.id != b2.id

    def test_breach_repr(self) -> None:
        """__repr__ includes title and severity."""
        breach = BreachNotification(
            studio_id=uuid4(),
            title="Security incident",
            description="desc",
            severity=BreachSeverity.HIGH,
            reported_by=1,
        )
        assert "Security incident" in repr(breach)

    def test_breach_72h_deadline_property(self) -> None:
        """Breach has is_within_72h property."""
        breach = BreachNotification(
            studio_id=uuid4(),
            title="Test",
            description="Test.",
            severity=BreachSeverity.HIGH,
            reported_by=1,
            detected_at=datetime.now(UTC),
        )

        assert breach.notification_deadline is not None
