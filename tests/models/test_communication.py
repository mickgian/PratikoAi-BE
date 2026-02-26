"""DEV-304: Tests for Communication SQLModel."""

import sys
from datetime import UTC, datetime
from types import ModuleType
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

if "app.services.database" not in sys.modules:
    _db_stub = ModuleType("app.services.database")
    _db_stub.database_service = MagicMock()  # type: ignore[attr-defined]
    sys.modules["app.services.database"] = _db_stub

from app.models.communication import (
    CanaleInvio,
    Communication,
    StatoComunicazione,
)


class TestCommunicationCreation:
    """Test Communication model creation and field defaults."""

    def test_communication_creation_valid(self) -> None:
        """Valid communication with all required fields."""
        studio_id = uuid4()
        comm = Communication(
            studio_id=studio_id,
            subject="Nuova normativa IVA",
            content="Si informa che dal 1 gennaio...",
            channel=CanaleInvio.EMAIL,
            created_by=1,
        )

        assert comm.studio_id == studio_id
        assert comm.subject == "Nuova normativa IVA"
        assert comm.channel == CanaleInvio.EMAIL
        assert comm.created_by == 1
        assert comm.id is not None  # uuid4 auto-generated

    def test_communication_status_default_draft(self) -> None:
        """Status defaults to DRAFT."""
        comm = Communication(
            studio_id=uuid4(),
            subject="Test",
            content="Content",
            channel=CanaleInvio.EMAIL,
            created_by=1,
        )
        assert comm.status == StatoComunicazione.DRAFT

    def test_communication_client_nullable(self) -> None:
        """client_id is nullable for bulk communications."""
        comm = Communication(
            studio_id=uuid4(),
            subject="Bulk",
            content="Content",
            channel=CanaleInvio.EMAIL,
            created_by=1,
        )
        assert comm.client_id is None

    def test_communication_with_client(self) -> None:
        """Communication can target a specific client."""
        comm = Communication(
            studio_id=uuid4(),
            client_id=42,
            subject="Test",
            content="Content",
            channel=CanaleInvio.EMAIL,
            created_by=1,
        )
        assert comm.client_id == 42


class TestCommunicationEnums:
    """Test enum values."""

    def test_status_enum_values(self) -> None:
        """All StatoComunicazione enum values are valid."""
        assert StatoComunicazione.DRAFT == "draft"
        assert StatoComunicazione.PENDING_REVIEW == "pending_review"
        assert StatoComunicazione.APPROVED == "approved"
        assert StatoComunicazione.REJECTED == "rejected"
        assert StatoComunicazione.SENT == "sent"
        assert StatoComunicazione.FAILED == "failed"

    def test_channel_enum_values(self) -> None:
        """All CanaleInvio enum values are valid."""
        assert CanaleInvio.EMAIL == "email"
        assert CanaleInvio.WHATSAPP == "whatsapp"


class TestCommunicationSelfApproval:
    """Test self-approval constraint logic."""

    def test_self_approval_detected(self) -> None:
        """is_self_approval returns True when creator == approver."""
        comm = Communication(
            studio_id=uuid4(),
            subject="Test",
            content="Content",
            channel=CanaleInvio.EMAIL,
            created_by=5,
            approved_by=5,
        )
        assert comm.is_self_approval is True

    def test_different_approver_allowed(self) -> None:
        """is_self_approval returns False when approver differs."""
        comm = Communication(
            studio_id=uuid4(),
            subject="Test",
            content="Content",
            channel=CanaleInvio.EMAIL,
            created_by=5,
            approved_by=10,
        )
        assert comm.is_self_approval is False

    def test_no_approver_not_self_approval(self) -> None:
        """is_self_approval returns False when no approver set."""
        comm = Communication(
            studio_id=uuid4(),
            subject="Test",
            content="Content",
            channel=CanaleInvio.EMAIL,
            created_by=5,
        )
        assert comm.is_self_approval is False


class TestCommunicationAuditFields:
    """Test audit trail fields."""

    def test_approved_at_default_none(self) -> None:
        """approved_at defaults to None."""
        comm = Communication(
            studio_id=uuid4(),
            subject="Test",
            content="Content",
            channel=CanaleInvio.EMAIL,
            created_by=1,
        )
        assert comm.approved_at is None
        assert comm.approved_by is None

    def test_sent_at_default_none(self) -> None:
        """sent_at defaults to None."""
        comm = Communication(
            studio_id=uuid4(),
            subject="Test",
            content="Content",
            channel=CanaleInvio.EMAIL,
            created_by=1,
        )
        assert comm.sent_at is None

    def test_approval_fields_set(self) -> None:
        """Approval fields can be set."""
        now = datetime.now(tz=UTC)
        comm = Communication(
            studio_id=uuid4(),
            subject="Test",
            content="Content",
            channel=CanaleInvio.EMAIL,
            created_by=1,
            approved_by=2,
            approved_at=now,
            status=StatoComunicazione.APPROVED,
        )
        assert comm.approved_by == 2
        assert comm.approved_at == now

    def test_normativa_riferimento(self) -> None:
        """normativa_riferimento is optional."""
        comm = Communication(
            studio_id=uuid4(),
            subject="Test",
            content="Content",
            channel=CanaleInvio.EMAIL,
            created_by=1,
            normativa_riferimento="DL 104/2023",
        )
        assert comm.normativa_riferimento == "DL 104/2023"

    def test_matching_rule_id_optional(self) -> None:
        """matching_rule_id is optional."""
        rule_id = uuid4()
        comm = Communication(
            studio_id=uuid4(),
            subject="Test",
            content="Content",
            channel=CanaleInvio.EMAIL,
            created_by=1,
            matching_rule_id=rule_id,
        )
        assert comm.matching_rule_id == rule_id


class TestCommunicationRepr:
    """Test __repr__ output."""

    def test_repr(self) -> None:
        """__repr__ includes subject and status."""
        comm = Communication(
            studio_id=uuid4(),
            subject="IVA Update",
            content="Content",
            channel=CanaleInvio.EMAIL,
            created_by=1,
        )
        r = repr(comm)
        assert "IVA Update" in r
        assert "draft" in r
