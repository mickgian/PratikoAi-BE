"""DEV-352: Tests for CalculationHistory model."""

import uuid

from app.models.calculation_history import CalculationHistory


class TestCalculationHistoryModel:
    def test_create_instance(self):
        studio_id = uuid.uuid4()
        record = CalculationHistory(
            studio_id=studio_id,
            calculation_type="irpef",
            input_data={"reddito": 50000},
            result_data={"imposta": 11600},
            client_id=1,
        )
        assert record.studio_id == studio_id
        assert record.calculation_type == "irpef"
        assert record.input_data == {"reddito": 50000}
        assert record.result_data == {"imposta": 11600}
        assert record.client_id == 1

    def test_nullable_fields(self):
        record = CalculationHistory(
            studio_id=uuid.uuid4(),
            calculation_type="iva",
        )
        assert record.client_id is None
        assert record.performed_by is None
        assert record.notes is None

    def test_repr(self):
        record = CalculationHistory(
            studio_id=uuid.uuid4(),
            calculation_type="inps",
            client_id=42,
        )
        assert "inps" in repr(record)
        assert "42" in repr(record)
