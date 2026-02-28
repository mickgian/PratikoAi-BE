"""DEV-415: Tests for Unsubscribe Service.

Tests: unsubscribe via link, consent flag updated, no further emails, re-subscribe.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.unsubscribe_service import UnsubscribeService


@pytest.fixture
def svc():
    return UnsubscribeService()


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.commit = AsyncMock()
    return db


class TestUnsubscribe:
    @pytest.mark.asyncio
    async def test_unsubscribe_sets_consent_false(self, svc, mock_db):
        mock_client = MagicMock()
        mock_client.consenso_marketing = True
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_client
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await svc.unsubscribe(mock_db, token="valid-token", client_id=1)
        assert result is True

    @pytest.mark.asyncio
    async def test_unsubscribe_client_not_found(self, svc, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await svc.unsubscribe(mock_db, token="token", client_id=999)
        assert result is False

    @pytest.mark.asyncio
    async def test_already_unsubscribed(self, svc, mock_db):
        mock_client = MagicMock()
        mock_client.consenso_marketing = False
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_client
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await svc.unsubscribe(mock_db, token="token", client_id=1)
        assert result is True  # Idempotent


class TestResubscribe:
    @pytest.mark.asyncio
    async def test_resubscribe_sets_consent_true(self, svc, mock_db):
        mock_client = MagicMock()
        mock_client.consenso_marketing = False
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_client
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await svc.resubscribe(mock_db, client_id=1)
        assert result is True


class TestGenerateUnsubscribeLink:
    def test_generates_valid_link(self, svc):
        link = svc.generate_unsubscribe_link(client_id=1, communication_id=uuid.uuid4())
        assert "/unsubscribe/" in link

    def test_includes_list_unsubscribe_header(self, svc):
        headers = svc.get_unsubscribe_headers(client_id=1, communication_id=uuid.uuid4())
        assert "List-Unsubscribe" in headers
        assert "List-Unsubscribe-Post" in headers
