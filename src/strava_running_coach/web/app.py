"""FastAPI app for the running coach web interface."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from strava_running_coach.web.pty_manager import PtyManager

pty_manager = PtyManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start Claude Code PTY on startup, clean up on shutdown."""
    pty_manager.start()

    # Auto-run the coaching skill after a short delay
    async def inject_skill():
        await asyncio.sleep(2.0)
        pty_manager.inject_command("/running-coach-v2\n")

    asyncio.create_task(inject_skill())

    yield

    pty_manager.stop()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_terminal(websocket: WebSocket):
    await websocket.accept()
    try:
        await pty_manager.attach(websocket)
    except WebSocketDisconnect:
        pass
