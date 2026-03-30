"""Base storage class with data directory configuration."""

import json
import os
from pathlib import Path
from typing import Any


def get_data_dir() -> Path:
    """
    Get the data directory for storing local files.

    Uses STRAVA_DATA_DIR environment variable if set, otherwise defaults
    to the project root directory.

    Returns:
        Path to the data directory
    """
    env_dir = os.environ.get("STRAVA_DATA_DIR")
    if env_dir:
        return Path(env_dir)
    # Default to project root (parent of src/)
    return Path(__file__).parent.parent.parent.parent


class BaseStorage:
    """Base class for storage implementations."""

    def __init__(self, subdirectory: str):
        """
        Initialize storage with a subdirectory name.

        Args:
            subdirectory: Name of the subdirectory within the data directory
        """
        self.data_dir = get_data_dir() / subdirectory
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _load_json(self, file_path: Path) -> dict[str, Any] | list[Any] | None:
        """Load JSON from a file, returning None if it doesn't exist."""
        if not file_path.exists():
            return None
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def _save_json(self, file_path: Path, data: dict[str, Any] | list[Any]) -> None:
        """Save data as JSON to a file."""
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def _load_text(self, file_path: Path) -> str | None:
        """Load text from a file, returning None if it doesn't exist."""
        if not file_path.exists():
            return None
        try:
            with open(file_path, "r") as f:
                return f.read()
        except IOError:
            return None

    def _save_text(self, file_path: Path, content: str) -> None:
        """Save text to a file."""
        with open(file_path, "w") as f:
            f.write(content)
