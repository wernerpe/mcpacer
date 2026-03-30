"""PTY management for running Claude Code in a browser terminal."""

import asyncio
import fcntl
import json
import os
import pty
import signal
import struct
import subprocess
import termios
from pathlib import Path

from fastapi import WebSocket


def _find_project_root() -> Path:
    """Walk up from this file to find the directory containing pyproject.toml."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


class PtyManager:
    """Spawns Claude Code in a PTY and bridges it to a WebSocket."""

    def __init__(self) -> None:
        self.master_fd: int | None = None
        self.process: subprocess.Popen | None = None
        self.project_root = _find_project_root()
        self.bytes_sent: int = 0

    def start(self, rows: int = 40, cols: int = 120) -> None:
        """Spawn Claude Code in a PTY."""
        master_fd, slave_fd = pty.openpty()

        # Set initial terminal size
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, winsize)

        env = os.environ.copy()
        env["TERM"] = "xterm-256color"
        env["COLORTERM"] = "truecolor"

        self.process = subprocess.Popen(
            ["claude"],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            preexec_fn=os.setsid,
            cwd=str(self.project_root),
            env=env,
        )

        os.close(slave_fd)

        # Set master fd to nonblocking
        flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
        fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

        self.master_fd = master_fd

    async def attach(self, websocket: WebSocket) -> None:
        """Bridge the PTY to a WebSocket. Blocks until disconnect."""
        if self.master_fd is None:
            return

        loop = asyncio.get_event_loop()
        master_fd = self.master_fd

        # PTY output -> WebSocket using asyncio reader
        output_queue: asyncio.Queue[bytes | None] = asyncio.Queue()

        def _on_pty_readable() -> None:
            try:
                data = os.read(master_fd, 4096)
                if data:
                    self.bytes_sent += len(data)
                    output_queue.put_nowait(data)
                else:
                    output_queue.put_nowait(None)
            except OSError as e:
                import errno
                if e.errno == errno.EIO:
                    # Child process exited
                    output_queue.put_nowait(None)
                # BlockingIOError (EAGAIN) — just no data yet, ignore

        loop.add_reader(master_fd, _on_pty_readable)

        async def read_pty() -> None:
            try:
                while True:
                    data = await output_queue.get()
                    if data is None:
                        break
                    await websocket.send_bytes(data)
            except asyncio.CancelledError:
                pass
            finally:
                loop.remove_reader(master_fd)

        # WebSocket input -> PTY
        async def write_pty() -> None:
            while True:
                try:
                    message = await websocket.receive()
                    if message["type"] == "websocket.disconnect":
                        break

                    if "text" in message:
                        text = message["text"]
                        # Check for resize messages
                        try:
                            msg = json.loads(text)
                            if isinstance(msg, dict) and msg.get("type") == "resize":
                                self.resize(msg["rows"], msg["cols"])
                                continue
                        except Exception:
                            pass
                        os.write(master_fd, text.encode())

                    elif "bytes" in message:
                        os.write(master_fd, message["bytes"])

                except Exception:
                    break

        # Run both tasks, cancel when either finishes
        read_task = asyncio.create_task(read_pty())
        write_task = asyncio.create_task(write_pty())
        try:
            done, pending = await asyncio.wait(
                [read_task, write_task],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
        except asyncio.CancelledError:
            read_task.cancel()
            write_task.cancel()

    def resize(self, rows: int, cols: int) -> None:
        """Resize the PTY."""
        if self.master_fd is not None:
            winsize = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsize)

    def inject_command(self, text: str) -> None:
        """Write a command directly to the PTY stdin."""
        if self.master_fd is not None:
            os.write(self.master_fd, text.encode())

    def stop(self) -> None:
        """Terminate the Claude Code process and clean up."""
        if self.process is not None:
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGHUP)
            except ProcessLookupError:
                pass
            self.process.wait(timeout=5)
            self.process = None

        if self.master_fd is not None:
            try:
                os.close(self.master_fd)
            except OSError:
                pass
            self.master_fd = None
