"""Run data storage for locally caching Strava activities."""

from typing import Any

from mcpacer.storage.base import BaseStorage


class RunStorage(BaseStorage):
    """Storage for run data fetched from Strava."""

    def __init__(self) -> None:
        """Initialize run storage in the run_data directory."""
        super().__init__("run_data")

    def get_existing_run_ids(self) -> set[int]:
        """Get the set of activity IDs that are already stored locally."""
        existing_ids: set[int] = set()
        for file_path in self.data_dir.glob("run_*.json"):
            try:
                activity_id = int(file_path.stem.split("_")[1])
                existing_ids.add(activity_id)
            except (IndexError, ValueError):
                pass
        return existing_ids

    def save_run(self, run: dict[str, Any], activity_id: int) -> None:
        """Save a single run to a JSON file."""
        file_path = self.data_dir / f"run_{activity_id}.json"
        self._save_json(file_path, run)

    def load_run(self, activity_id: int) -> dict[str, Any] | None:
        """Load a single run by activity ID."""
        file_path = self.data_dir / f"run_{activity_id}.json"
        return self._load_json(file_path)  # type: ignore

    def load_all_runs(self) -> list[dict[str, Any]]:
        """Load all run data from the run_data directory."""
        runs: list[dict[str, Any]] = []
        for file_path in self.data_dir.glob("run_*.json"):
            run = self._load_json(file_path)
            if run and isinstance(run, dict):
                runs.append(run)
        # Sort by date (most recent first)
        runs.sort(key=lambda r: r.get("start_date", ""), reverse=True)
        return runs

    def delete_run(self, activity_id: int) -> bool:
        """Delete a run by activity ID. Returns True if deleted."""
        file_path = self.data_dir / f"run_{activity_id}.json"
        if file_path.exists():
            file_path.unlink()
            return True
        return False
