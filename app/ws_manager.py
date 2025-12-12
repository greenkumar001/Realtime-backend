# backend/app/ws_manager.py
from typing import List
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        living = []
        for conn in list(self.active_connections):
            try:
                await conn.send_json(message)
                living.append(conn)
            except Exception:
                # drop bad connection
                pass
        self.active_connections = living

manager = ConnectionManager()
