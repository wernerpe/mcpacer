"""Dashboard event broadcasting via WebSocket."""

import json

from fastapi import WebSocket

_clients: set[WebSocket] = set()


async def register(ws: WebSocket):
    """Accept a dashboard event WebSocket and hold it open."""
    await ws.accept()
    _clients.add(ws)
    try:
        while True:
            await ws.receive_text()
    except Exception:
        _clients.discard(ws)


async def broadcast(event: str = "refresh"):
    """Send an event to all connected dashboard clients."""
    dead = set()
    for ws in _clients:
        try:
            await ws.send_text(event)
        except Exception:
            dead.add(ws)
    _clients.difference_update(dead)


async def broadcast_json(payload: dict):
    """Send a typed JSON payload to all dashboard clients."""
    await broadcast(json.dumps(payload))
