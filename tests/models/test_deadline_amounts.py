"""DEV-437: Tests for Deadline importo & sanzioni fields.

Covers:
- Nullable importo (default None)
- Valid decimal importo values
- Negative importo rejected at schema level
- JSONB sanzioni structure
- Nullable sanzioni (default None)
- Schema validation for DeadlineCreateRequest and DeadlineResponse
"""

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.deadline import Deadline, DeadlineSource, DeadlineType
from app.schemas.deadline import DeadlineCreateRequest, DeadlineResponse, SanzioniInfo


class TestDeadlineImporto:
    """Test importo (amount) field on the Deadline model."""

    def test_importo_nullable_by_default(self) -> None:
        """importo defaults to None when not provided."""
        dl = Deadline(
            title="Scadenza IVA",
            deadline_type=DeadlineType.FISCALE,
            source=DeadlineSource.REGULATORY,
            due_date=date(2026, 3, 16),
        )
        assert dl.importo is None

    def test_importo_valid_decimal(self) -> None:
        """importo accepts a valid Decimal value."""
        dl = Deadline(
            title="F24 mensile",
            deadline_type=DeadlineType.FISCALE,
            source=DeadlineSource.TAX,
            due_date=date(2026, 4, 16),
            importo=Decimal("1500.50"),
        )
        assert dl.importo == Decimal("1500.50")

    def test_importo_zero(self) -> None:
        """importo accepts zero."""
        dl = Deadline(
            title="Scadenza zero",
            deadline_type=DeadlineType.ADEMPIMENTO,
            source=DeadlineSource.REGULATORY,
            due_date=date(2026, 6, 30),
            importo=Decimal("0.00"),
        )
        assert dl.importo == Decimal("0.00")

    def test_importo_large_value(self) -> None:
        """importo accepts large values within Numeric(12,2) range."""
        dl = Deadline(
            title="Grande importo",
            deadline_type=DeadlineType.FISCALE,
            source=DeadlineSource.TAX,
            due_date=date(2026, 12, 31),
            importo=Decimal("9999999999.99"),
        )
        assert dl.importo == Decimal("9999999999.99")


class TestDeadlineSanzioni:
    """Test sanzioni (penalties) JSONB field on the Deadline model."""

    def test_sanzioni_nullable_by_default(self) -> None:
        """sanzioni defaults to None when not provided."""
        dl = Deadline(
            title="Scadenza senza sanzioni",
            deadline_type=DeadlineType.CONTRIBUTIVO,
            source=DeadlineSource.REGULATORY,
            due_date=date(2026, 5, 15),
        )
        assert dl.sanzioni is None

    def test_sanzioni_with_full_structure(self) -> None:
        """sanzioni accepts full JSONB structure with all fields."""
        penalties = {
            "percentuale": 30.0,
            "importo_fisso": 250.00,
            "descrizione": "Sanzione per ritardato pagamento IVA",
        }
        dl = Deadline(
            title="IVA trimestrale",
            deadline_type=DeadlineType.FISCALE,
            source=DeadlineSource.TAX,
            due_date=date(2026, 3, 16),
            sanzioni=penalties,
        )
        assert dl.sanzioni is not None
        assert dl.sanzioni["percentuale"] == 30.0
        assert dl.sanzioni["importo_fisso"] == 250.00
        assert dl.sanzioni["descrizione"] == "Sanzione per ritardato pagamento IVA"

    def test_sanzioni_partial_structure(self) -> None:
        """sanzioni accepts partial JSONB structure (only some fields)."""
        penalties = {
            "percentuale": 15.0,
            "descrizione": "Sanzione ridotta per ravvedimento operoso",
        }
        dl = Deadline(
            title="Ravvedimento",
            deadline_type=DeadlineType.FISCALE,
            source=DeadlineSource.TAX,
            due_date=date(2026, 7, 1),
            sanzioni=penalties,
        )
        assert dl.sanzioni is not None
        assert dl.sanzioni["percentuale"] == 15.0
        assert "importo_fisso" not in dl.sanzioni

    def test_sanzioni_empty_dict(self) -> None:
        """sanzioni accepts empty dict."""
        dl = Deadline(
            title="Senza sanzione",
            deadline_type=DeadlineType.ADEMPIMENTO,
            source=DeadlineSource.CLIENT_SPECIFIC,
            due_date=date(2026, 9, 30),
            sanzioni={},
        )
        assert dl.sanzioni == {}


class TestDeadlineImportoAndSanzioniTogether:
    """Test importo and sanzioni used together."""

    def test_both_fields_set(self) -> None:
        """Deadline with both importo and sanzioni populated."""
        dl = Deadline(
            title="IMU Seconda Casa",
            deadline_type=DeadlineType.FISCALE,
            source=DeadlineSource.TAX,
            due_date=date(2026, 6, 16),
            importo=Decimal("2400.00"),
            sanzioni={
                "percentuale": 30.0,
                "importo_fisso": 100.00,
                "descrizione": "Sanzione IMU",
            },
        )
        assert dl.importo == Decimal("2400.00")
        assert dl.sanzioni["percentuale"] == 30.0


class TestSanzioniInfoSchema:
    """Test the SanzioniInfo Pydantic schema."""

    def test_valid_full_sanzioni(self) -> None:
        """SanzioniInfo with all fields populated."""
        info = SanzioniInfo(
            percentuale=30.0,
            importo_fisso=Decimal("250.00"),
            descrizione="Sanzione per omesso versamento",
        )
        assert info.percentuale == 30.0
        assert info.importo_fisso == Decimal("250.00")
        assert info.descrizione == "Sanzione per omesso versamento"

    def test_valid_partial_sanzioni(self) -> None:
        """SanzioniInfo with only percentuale."""
        info = SanzioniInfo(percentuale=15.0)
        assert info.percentuale == 15.0
        assert info.importo_fisso is None
        assert info.descrizione is None

    def test_all_fields_none(self) -> None:
        """SanzioniInfo with all optional fields as None."""
        info = SanzioniInfo()
        assert info.percentuale is None
        assert info.importo_fisso is None
        assert info.descrizione is None

    def test_negative_percentuale_rejected(self) -> None:
        """Negative percentuale is rejected."""
        with pytest.raises(ValidationError):
            SanzioniInfo(percentuale=-5.0)

    def test_negative_importo_fisso_rejected(self) -> None:
        """Negative importo_fisso is rejected."""
        with pytest.raises(ValidationError):
            SanzioniInfo(importo_fisso=Decimal("-100.00"))


class TestDeadlineCreateRequestAmounts:
    """Test DeadlineCreateRequest schema with importo and sanzioni."""

    def _base_request(self, **overrides: object) -> dict:
        """Build a base request dict with required fields."""
        data: dict = {
            "title": "Test Scadenza",
            "deadline_type": "fiscale",
            "source": "regulatory",
            "due_date": "2026-06-16",
        }
        data.update(overrides)
        return data

    def test_create_request_without_amounts(self) -> None:
        """Request without importo/sanzioni is valid."""
        req = DeadlineCreateRequest(**self._base_request())
        assert req.importo is None
        assert req.sanzioni is None

    def test_create_request_with_importo(self) -> None:
        """Request with valid importo."""
        req = DeadlineCreateRequest(**self._base_request(importo=Decimal("500.00")))
        assert req.importo == Decimal("500.00")

    def test_create_request_negative_importo_rejected(self) -> None:
        """Request with negative importo is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            DeadlineCreateRequest(**self._base_request(importo=Decimal("-100.00")))
        assert "importo" in str(exc_info.value).lower()

    def test_create_request_with_sanzioni(self) -> None:
        """Request with valid sanzioni object."""
        req = DeadlineCreateRequest(
            **self._base_request(
                sanzioni={"percentuale": 30.0, "descrizione": "Multa"},
            )
        )
        assert req.sanzioni is not None
        assert req.sanzioni.percentuale == 30.0

    def test_create_request_with_both(self) -> None:
        """Request with both importo and sanzioni."""
        req = DeadlineCreateRequest(
            **self._base_request(
                importo=Decimal("1000.00"),
                sanzioni={
                    "percentuale": 15.0,
                    "importo_fisso": Decimal("50.00"),
                    "descrizione": "Ravvedimento operoso",
                },
            )
        )
        assert req.importo == Decimal("1000.00")
        assert req.sanzioni is not None
        assert req.sanzioni.percentuale == 15.0


class TestDeadlineResponseAmounts:
    """Test DeadlineResponse schema with importo and sanzioni."""

    def test_response_with_importo(self) -> None:
        """Response includes importo field."""
        from datetime import datetime
        from uuid import uuid4

        resp = DeadlineResponse(
            id=uuid4(),
            title="Test",
            deadline_type="fiscale",
            source="regulatory",
            due_date=date(2026, 6, 16),
            is_active=True,
            created_at=datetime.now(),
            importo=Decimal("750.00"),
        )
        assert resp.importo == Decimal("750.00")

    def test_response_without_importo(self) -> None:
        """Response with None importo."""
        from datetime import datetime
        from uuid import uuid4

        resp = DeadlineResponse(
            id=uuid4(),
            title="Test",
            deadline_type="fiscale",
            source="regulatory",
            due_date=date(2026, 6, 16),
            is_active=True,
            created_at=datetime.now(),
        )
        assert resp.importo is None

    def test_response_with_sanzioni(self) -> None:
        """Response includes sanzioni field."""
        from datetime import datetime
        from uuid import uuid4

        resp = DeadlineResponse(
            id=uuid4(),
            title="Test",
            deadline_type="fiscale",
            source="regulatory",
            due_date=date(2026, 6, 16),
            is_active=True,
            created_at=datetime.now(),
            sanzioni={"percentuale": 30.0, "descrizione": "Test sanzione"},
        )
        assert resp.sanzioni is not None
        assert resp.sanzioni["percentuale"] == 30.0
