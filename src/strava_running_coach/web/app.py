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

    # Auto-run the coaching skill once Claude Code is ready.
    # Wait for output to settle (prompt is showing when output stops).
    async def inject_skill():
        await asyncio.sleep(3.0)  # initial wait for startup
        # Wait for output to go quiet (no data for 1.5s = prompt is ready)
        last_size = 0
        quiet_count = 0
        for _ in range(20):  # up to 10 more seconds
            await asyncio.sleep(0.5)
            if pty_manager.process and pty_manager.process.poll() is not None:
                return
            current_size = pty_manager.bytes_sent
            if current_size == last_size:
                quiet_count += 1
                if quiet_count >= 3:  # 1.5s of quiet
                    break
            else:
                quiet_count = 0
                last_size = current_size
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
