"""Tests for DEV-369: WebSocket Events for Real-time Updates."""

import json
from uuid import uuid4

import pytest

from app.api.v1.websocket import ConnectionManager, EventType


@pytest.fixture
def manager():
    return ConnectionManager()


@pytest.fixture
def studio_id():
    return uuid4()


class TestEventType:
    """Tests for EventType enum."""

    def test_all_event_types(self):
        assert EventType.MATCH_FOUND == "match_found"
        assert EventType.COMMUNICATION_SENT == "communication_sent"
        assert EventType.COMMUNICATION_STATUS == "communication_status"
        assert EventType.PROCEDURA_PROGRESS == "procedura_progress"
        assert EventType.DASHBOARD_UPDATE == "dashboard_update"
        assert EventType.NOTIFICATION == "notification"

    def test_event_count(self):
        assert len(EventType) == 6


class TestConnectionManager:
    """Tests for the WebSocket connection manager."""

    def test_initial_empty(self, manager, studio_id):
        assert manager.get_connection_count(studio_id) == 0

    @pytest.mark.asyncio
    async def test_connect_increments_count(self, manager, studio_id):
        ws = MockWebSocket()
        await manager.connect(ws, studio_id)
        assert manager.get_connection_count(studio_id) == 1

    @pytest.mark.asyncio
    async def test_disconnect_decrements_count(self, manager, studio_id):
        ws = MockWebSocket()
        await manager.connect(ws, studio_id)
        manager.disconnect(ws, studio_id)
        assert manager.get_connection_count(studio_id) == 0

    @pytest.mark.asyncio
    async def test_multiple_connections(self, manager, studio_id):
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        await manager.connect(ws1, studio_id)
        await manager.connect(ws2, studio_id)
        assert manager.get_connection_count(studio_id) == 2

    @pytest.mark.asyncio
    async def test_broadcast_sends_to_all(self, manager, studio_id):
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        await manager.connect(ws1, studio_id)
        await manager.connect(ws2, studio_id)

        await manager.broadcast(studio_id, EventType.MATCH_FOUND, {"id": "abc"})

        assert len(ws1.sent_messages) == 1
        assert len(ws2.sent_messages) == 1
        msg = json.loads(ws1.sent_messages[0])
        assert msg["event"] == "match_found"
        assert msg["data"]["id"] == "abc"

    @pytest.mark.asyncio
    async def test_broadcast_no_connections(self, manager, studio_id):
        # Should not raise
        await manager.broadcast(studio_id, EventType.NOTIFICATION, {"msg": "test"})

    @pytest.mark.asyncio
    async def test_broadcast_removes_failed_connection(self, manager, studio_id):
        ws_good = MockWebSocket()
        ws_bad = MockWebSocket(fail_send=True)
        await manager.connect(ws_good, studio_id)
        await manager.connect(ws_bad, studio_id)

        await manager.broadcast(studio_id, EventType.DASHBOARD_UPDATE, {})

        # Bad connection should be removed
        assert manager.get_connection_count(studio_id) == 1

    @pytest.mark.asyncio
    async def test_disconnect_nonexistent_studio(self, manager):
        ws = MockWebSocket()
        # Should not raise
        manager.disconnect(ws, uuid4())

    @pytest.mark.asyncio
    async def test_isolation_between_studios(self, manager):
        studio_a = uuid4()
        studio_b = uuid4()
        ws_a = MockWebSocket()
        ws_b = MockWebSocket()
        await manager.connect(ws_a, studio_a)
        await manager.connect(ws_b, studio_b)

        await manager.broadcast(studio_a, EventType.MATCH_FOUND, {"studio": "a"})

        assert len(ws_a.sent_messages) == 1
        assert len(ws_b.sent_messages) == 0


# ---------------------------------------------------------------------------
# Mock WebSocket helper
# ---------------------------------------------------------------------------


class MockWebSocket:
    """Lightweight mock for WebSocket testing."""

    def __init__(self, fail_send: bool = False):
        self.sent_messages: list[str] = []
        self._fail_send = fail_send
        self._accepted = False

    async def accept(self):
        self._accepted = True

    async def send_text(self, data: str):
        if self._fail_send:
            raise RuntimeError("Connection closed")
        self.sent_messages.append(data)

    async def receive_text(self) -> str:
        return "ping"
