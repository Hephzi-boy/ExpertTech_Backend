import json

from fastapi import WebSocket


class FeedEventManager:
    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self._connections:
            self._connections.remove(websocket)

    async def broadcast(self, event_type: str, payload: dict) -> None:
        message = json.dumps({"type": event_type, "payload": payload}, default=str)
        stale_connections: list[WebSocket] = []
        for connection in self._connections:
            try:
                await connection.send_text(message)
            except Exception:
                stale_connections.append(connection)

        for connection in stale_connections:
            self.disconnect(connection)


feed_events = FeedEventManager()
