import asyncio
import json
import logging
from typing import Any, Dict, List
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketConnectionManager:
    """
    Manages active WebSocket connections per authenticated User ID.
    Supports direct peer messaging, connection tracking, and graceful disconnects.
    """
    def __init__(self):
        # Map user_id -> List of active WebSocket connections (multi-tab support)
        self.active_connections: Dict[int, List[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        """Accept WebSocket and register under user_id."""
        await websocket.accept()
        async with self._lock:
            if user_id not in self.active_connections:
                self.active_connections[user_id] = []
            self.active_connections[user_id].append(websocket)
        logger.info("WebSocket connected for User ID %d (Active sockets: %d)", user_id, len(self.active_connections[user_id]))

    async def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        """Unregister WebSocket on disconnect."""
        async with self._lock:
            if user_id in self.active_connections:
                if websocket in self.active_connections[user_id]:
                    self.active_connections[user_id].remove(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
        logger.info("WebSocket disconnected for User ID %d", user_id)

    async def send_to_user(self, user_id: int, data: Dict[str, Any]) -> bool:
        """Send JSON payload to all active sockets of a target user."""
        async with self._lock:
            sockets = list(self.active_connections.get(user_id, []))

        if not sockets:
            return False

        payload_str = json.dumps(data, default=str)
        dead_sockets: List[WebSocket] = []

        for socket in sockets:
            try:
                await socket.send_text(payload_str)
            except Exception as e:
                logger.warning("Failed sending message to socket for User %d: %s", user_id, str(e))
                dead_sockets.append(socket)

        if dead_sockets:
            async with self._lock:
                for dead in dead_sockets:
                    if user_id in self.active_connections and dead in self.active_connections[user_id]:
                        self.active_connections[user_id].remove(dead)

        return True

    def is_user_online(self, user_id: int) -> bool:
        """Check if target user has any open WebSocket connections."""
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0


# Global WebSocket connection manager instance
ws_manager = WebSocketConnectionManager()
