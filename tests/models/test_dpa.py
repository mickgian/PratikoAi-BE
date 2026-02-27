"""DEV-372: Tests for Data Processing Agreement (DPA) Model."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.models.dpa import DPA, DPAAcceptance, DPAStatus


class TestDPACreation:
    """Test DPA model creation and field defaults."""

    def test_dpa_creation_valid(self) -> None:
        """Valid DPA with required fields."""
        dpa = DPA(
            title="Accordo Trattamento Dati v1",
            version="1.0",
            content="Contenuto completo dell'accordo DPA...",
        )

        assert dpa.title == "Accordo Trattamento Dati v1"
        assert dpa.version == "1.0"
        assert dpa.status == DPAStatus.DRAFT
        assert dpa.id is not None

    def test_dpa_status_default(self) -> None:
        """Status defaults to DRAFT."""
        dpa = DPA(
            title="Test DPA",
            version="1.0",
            content="Test content.",
        )
        assert dpa.status == DPAStatus.DRAFT

    def test_dpa_active_status(self) -> None:
        """DPA can be set to ACTIVE."""
        dpa = DPA(
            title="Active DPA",
            version="2.0",
            content="Active content.",
            status=DPAStatus.ACTIVE,
        )
        assert dpa.status == DPAStatus.ACTIVE

    def test_dpa_uuid_uniqueness(self) -> None:
        """Two DPAs get different UUIDs."""
        d1 = DPA(title="A", version="1.0", content="a")
        d2 = DPA(title="B", version="1.0", content="b")
        assert d1.id != d2.id

    def test_dpa_repr(self) -> None:
        """__repr__ includes title and version."""
        dpa = DPA(title="Test DPA", version="1.0", content="content")
        assert "Test DPA" in repr(dpa)
        assert "1.0" in repr(dpa)


class TestDPAAcceptanceCreation:
    """Test DPAAcceptance model."""

    def test_acceptance_creation(self) -> None:
        """Valid acceptance record."""
        acceptance = DPAAcceptance(
            dpa_id=uuid4(),
            studio_id=uuid4(),
            accepted_by=1,
            ip_address="192.168.1.1",
        )

        assert acceptance.accepted_by == 1
        assert acceptance.ip_address == "192.168.1.1"
        assert acceptance.id is not None

    def test_acceptance_with_user_agent(self) -> None:
        """Acceptance with user agent info."""
        acceptance = DPAAcceptance(
            dpa_id=uuid4(),
            studio_id=uuid4(),
            accepted_by=1,
            ip_address="10.0.0.1",
            user_agent="Mozilla/5.0",
        )

        assert acceptance.user_agent == "Mozilla/5.0"

    def test_acceptance_uuid_uniqueness(self) -> None:
        """Two acceptances get different UUIDs."""
        a1 = DPAAcceptance(dpa_id=uuid4(), studio_id=uuid4(), accepted_by=1, ip_address="1.1.1.1")
        a2 = DPAAcceptance(dpa_id=uuid4(), studio_id=uuid4(), accepted_by=2, ip_address="2.2.2.2")
        assert a1.id != a2.id
