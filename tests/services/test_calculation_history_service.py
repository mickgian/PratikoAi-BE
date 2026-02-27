"""DEV-352: Tests for CalculationHistory Service."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.calculation_history import CalculationHistory
from app.services.calculation_history_service import CalculationHistoryService


@pytest.fixture
def svc():
    return CalculationHistoryService()


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_record_calculation(svc, mock_db):
    studio_id = uuid.uuid4()
    result = await svc.record(
        mock_db,
        studio_id=studio_id,
        calculation_type="irpef",
        input_data={"reddito": 50000},
        result_data={"imposta": 11600},
        client_id=1,
        performed_by=10,
    )
    assert isinstance(result, CalculationHistory)
    assert result.calculation_type == "irpef"
    assert result.client_id == 1
    mock_db.add.assert_called_once()
    mock_db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_record_without_client(svc, mock_db):
    result = await svc.record(
        mock_db,
        studio_id=uuid.uuid4(),
        calculation_type="iva",
        input_data={"importo": 1000},
        result_data={"iva": 220},
    )
    assert result.client_id is None


@pytest.mark.asyncio
async def test_list_by_client(svc, mock_db):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)

    results = await svc.list_by_client(mock_db, studio_id=uuid.uuid4(), client_id=1)
    assert results == []
    mock_db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_by_studio(svc, mock_db):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)

    results = await svc.list_by_studio(mock_db, studio_id=uuid.uuid4())
    assert results == []
