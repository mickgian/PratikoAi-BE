"""DEV-412: Tests for Email Open Tracking Service.

Tests: track open, track click, respect consent flags, no tracking without consent.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.email_tracking_service import EmailTrackingService


@pytest.fixture
def svc():
    return EmailTrackingService()


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    return db


class TestGenerateTrackingUrl:
    def test_generate_click_url(self, svc):
        url = svc.generate_tracking_url(
            communication_id=uuid.uuid4(),
            target_url="https://example.com/article",
            tracking_type="click",
        )
        assert "/t/" in url
        assert url.startswith("https://")

    def test_generate_unique_urls(self, svc):
        comm_id = uuid.uuid4()
        url1 = svc.generate_tracking_url(comm_id, "https://a.com", "click")
        url2 = svc.generate_tracking_url(comm_id, "https://b.com", "click")
        assert url1 != url2


class TestRecordEvent:
    @pytest.mark.asyncio
    async def test_record_click_event(self, svc, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(
            consenso_marketing=True,
            consenso_profilazione=True,
        )
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await svc.record_event(
            mock_db,
            tracking_token="abc123",
            event_type="click",
            client_id=1,
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_no_tracking_without_consent(self, svc, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(
            consenso_marketing=False,
            consenso_profilazione=False,
        )
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await svc.record_event(
            mock_db,
            tracking_token="abc123",
            event_type="click",
            client_id=1,
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_client_not_found(self, svc, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await svc.record_event(
            mock_db,
            tracking_token="abc123",
            event_type="click",
            client_id=999,
        )
        assert result is False


class TestGetStats:
    @pytest.mark.asyncio
    async def test_get_communication_stats(self, svc, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 5
        mock_db.execute = AsyncMock(return_value=mock_result)

        stats = await svc.get_communication_stats(mock_db, communication_id=uuid.uuid4())
        assert isinstance(stats, dict)
        assert "click_count" in stats
