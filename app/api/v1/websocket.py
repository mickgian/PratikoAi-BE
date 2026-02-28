"""DEV-369: WebSocket Events for Real-time Updates.

WebSocket endpoint for real-time events: matches, communications, progress.
"""

import asyncio
import json
from enum import StrEnum
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.logging import logger

router = APIRouter(tags=["websocket"])


class EventType(StrEnum):
    """Types of real-time events."""

    MATCH_FOUND = "match_found"
    COMMUNICATION_SENT = "communication_sent"
    COMMUNICATION_STATUS = "communication_status"
    PROCEDURA_PROGRESS = "procedura_progress"
    DASHBOARD_UPDATE = "dashboard_update"
    NOTIFICATION = "notification"


class ConnectionManager:
    """Manages WebSocket connections per studio."""

    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, studio_id: UUID) -> None:
        """Accept and register a WebSocket connection."""
        await websocket.accept()
        key = str(studio_id)
        if key not in self._connections:
            self._connections[key] = []
        self._connections[key].append(websocket)
        logger.info("websocket_connected", studio_id=key)

    def disconnect(self, websocket: WebSocket, studio_id: UUID) -> None:
        """Remove a WebSocket connection."""
        key = str(studio_id)
        if key in self._connections:
            self._connections[key] = [ws for ws in self._connections[key] if ws is not websocket]
            if not self._connections[key]:
                del self._connections[key]
        logger.info("websocket_disconnected", studio_id=key)

    async def broadcast(
        self,
        studio_id: UUID,
        event_type: EventType,
        data: dict,
    ) -> None:
        """Broadcast an event to all connections for a studio."""
        key = str(studio_id)
        connections = self._connections.get(key, [])
        message = json.dumps({"event": event_type, "data": data})
        disconnected: list[WebSocket] = []
        for ws in connections:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.disconnect(ws, studio_id)

    def get_connection_count(self, studio_id: UUID) -> int:
        """Get number of active connections for a studio."""
        key = str(studio_id)
        return len(self._connections.get(key, []))


manager = ConnectionManager()


@router.websocket("/ws/{studio_id}")
async def websocket_endpoint(websocket: WebSocket, studio_id: UUID) -> None:
    """WebSocket endpoint for real-time studio events."""
    await manager.connect(websocket, studio_id)
    try:
        while True:
            # Keep connection alive; client can send pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"event": "pong"}))
    except WebSocketDisconnect:
        manager.disconnect(websocket, studio_id)
