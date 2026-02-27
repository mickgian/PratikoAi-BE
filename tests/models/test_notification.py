"""DEV-422: Tests for Notification SQLModel."""

from uuid import uuid4

import pytest

from app.models.notification import Notification, NotificationPriority, NotificationType


class TestNotificationModel:
    """Test Notification model creation and defaults."""

    def test_create_valid_notification(self) -> None:
        """Happy path: create notification with all required fields."""
        studio_id = uuid4()
        n = Notification(
            user_id=1,
            studio_id=studio_id,
            notification_type=NotificationType.SCADENZA,
            priority=NotificationPriority.HIGH,
            title="Scadenza IVA in arrivo",
        )
        assert n.user_id == 1
        assert n.studio_id == studio_id
        assert n.notification_type == NotificationType.SCADENZA
        assert n.priority == NotificationPriority.HIGH
        assert n.title == "Scadenza IVA in arrivo"

    def test_default_unread(self) -> None:
        """Default: is_read=False, dismissed=False."""
        n = Notification(
            user_id=1,
            studio_id=uuid4(),
            notification_type=NotificationType.MATCH,
            priority=NotificationPriority.MEDIUM,
            title="Nuovo match trovato",
        )
        assert n.is_read is False
        assert n.dismissed is False
        assert n.read_at is None

    def test_nullable_description(self) -> None:
        """Description is optional."""
        n = Notification(
            user_id=1,
            studio_id=uuid4(),
            notification_type=NotificationType.COMUNICAZIONE,
            priority=NotificationPriority.LOW,
            title="Comunicazione approvata",
            description="La comunicazione per il cliente è stata approvata.",
        )
        assert n.description == "La comunicazione per il cliente è stata approvata."

    def test_polymorphic_reference(self) -> None:
        """Polymorphic reference to source entity."""
        ref_id = uuid4()
        n = Notification(
            user_id=1,
            studio_id=uuid4(),
            notification_type=NotificationType.NORMATIVA,
            priority=NotificationPriority.MEDIUM,
            title="Nuova normativa pubblicata",
            reference_id=ref_id,
            reference_type="deadline",
        )
        assert n.reference_id == ref_id
        assert n.reference_type == "deadline"

    def test_all_notification_types(self) -> None:
        """All 4 notification types are valid."""
        types = [
            NotificationType.SCADENZA,
            NotificationType.MATCH,
            NotificationType.COMUNICAZIONE,
            NotificationType.NORMATIVA,
        ]
        assert len(types) == 4
        for t in types:
            n = Notification(
                user_id=1,
                studio_id=uuid4(),
                notification_type=t,
                priority=NotificationPriority.LOW,
                title=f"Test {t.value}",
            )
            assert n.notification_type == t

    def test_all_priority_levels(self) -> None:
        """All 4 priority levels are valid."""
        priorities = [
            NotificationPriority.LOW,
            NotificationPriority.MEDIUM,
            NotificationPriority.HIGH,
            NotificationPriority.URGENT,
        ]
        assert len(priorities) == 4
        for p in priorities:
            n = Notification(
                user_id=1,
                studio_id=uuid4(),
                notification_type=NotificationType.SCADENZA,
                priority=p,
                title=f"Test {p.value}",
            )
            assert n.priority == p

    def test_uuid_auto_generated(self) -> None:
        """ID is auto-generated UUID."""
        n = Notification(
            user_id=1,
            studio_id=uuid4(),
            notification_type=NotificationType.MATCH,
            priority=NotificationPriority.LOW,
            title="Test",
        )
        assert n.id is not None
