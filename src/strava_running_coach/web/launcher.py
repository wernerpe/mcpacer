"""Launcher for the running coach web app.

Starts FastAPI backend + SvelteKit dev server, opens browser.
"""

import os
import signal
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

import httpx


def _find_project_root() -> Path:
    """Walk up from this file to find the directory containing pyproject.toml."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


def _wait_for_server(url: str, timeout: float = 15.0) -> bool:
    """Poll a URL until it responds or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = httpx.get(url, timeout=2.0)
            if resp.status_code == 200:
                return True
        except (httpx.ConnectError, httpx.TimeoutException):
            pass
        time.sleep(0.3)
    return False


def main() -> None:
    project_root = _find_project_root()
    web_dir = project_root / "web"

    if not web_dir.exists():
        print(f"Error: web/ directory not found at {web_dir}", file=sys.stderr)
        sys.exit(1)

    # Check for node/npm
    try:
        subprocess.run(
            ["node", "--version"],
            capture_output=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("Error: Node.js is required. Install from https://nodejs.org/", file=sys.stderr)
        sys.exit(1)

    # Install npm deps if needed
    if not (web_dir / "node_modules").exists():
        print("Installing frontend dependencies...")
        subprocess.run(
            ["npm", "install"],
            cwd=str(web_dir),
            check=True,
        )

    processes: list[subprocess.Popen] = []

    def shutdown(sig=None, frame=None):
        for proc in processes:
            try:
                proc.terminate()
            except ProcessLookupError:
                pass
        for proc in processes:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        # Start FastAPI backend
        print("Starting backend...")
        backend = subprocess.Popen(
            [
                sys.executable, "-m", "uvicorn",
                "strava_running_coach.web.app:app",
                "--host", "127.0.0.1",
                "--port", "8000",
                "--log-level", "warning",
            ],
            cwd=str(project_root),
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
        processes.append(backend)

        # Start SvelteKit dev server
        print("Starting frontend...")
        frontend = subprocess.Popen(
            ["npm", "run", "dev", "--", "--port", "5173"],
            cwd=str(web_dir),
            env={**os.environ, "BROWSER": "none"},
        )
        processes.append(frontend)

        # Wait for both servers
        if not _wait_for_server("http://127.0.0.1:8000/health"):
            print("Error: Backend failed to start", file=sys.stderr)
            shutdown()

        if not _wait_for_server("http://127.0.0.1:5173"):
            print("Error: Frontend failed to start", file=sys.stderr)
            shutdown()

        print("Opening browser at http://localhost:5173")
        webbrowser.open("http://localhost:5173")

        # Wait for either process to exit
        while True:
            for proc in processes:
                ret = proc.poll()
                if ret is not None:
                    print(f"Process exited with code {ret}, shutting down...")
                    shutdown()
            time.sleep(0.5)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        shutdown()


if __name__ == "__main__":
    main()
