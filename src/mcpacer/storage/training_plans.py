"""Training plan storage — YAML with ruamel.yaml for comment-preserving round-trips."""

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from mcpacer.storage.base import get_data_dir


# Day-of-week ordering for sorting runs within a week
DAY_ORDER = {
    "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
    "Friday": 4, "Saturday": 5, "Sunday": 6,
}


class TrainingPlanStorage:
    """Storage for YAML training plans with comment-preserving edits."""

    def __init__(self) -> None:
        self.data_dir = get_data_dir() / "training_plans"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._yaml = YAML()
        self._yaml.preserve_quotes = True
        self._yaml.default_flow_style = False

    def _plan_path(self, plan_id: str) -> Path:
        return self.data_dir / f"plan_{plan_id}.yaml"

    def load_plan(self, plan_id: str) -> CommentedMap | None:
        """Load a plan as a ruamel CommentedMap (preserves comments)."""
        path = self._plan_path(plan_id)
        if not path.exists():
            return None
        with open(path) as f:
            return self._yaml.load(f)

    def save_plan(self, plan: CommentedMap, plan_id: str) -> None:
        """Save a plan, preserving comments and formatting."""
        path = self._plan_path(plan_id)
        with open(path, "w") as f:
            self._yaml.dump(plan, f)

    def load_plan_raw(self, plan_id: str) -> str | None:
        """Load plan YAML as raw text."""
        path = self._plan_path(plan_id)
        if not path.exists():
            return None
        return path.read_text()

    def list_plans(self) -> list[dict[str, Any]]:
        """List all plans with summary metadata."""
        summaries = []
        for path in self.data_dir.glob("plan_*.yaml"):
            plan_id = path.stem.replace("plan_", "")
            try:
                with open(path) as f:
                    plan = self._yaml.load(f)
                if not plan:
                    continue
                goal = plan.get("goal_race", {}) or {}
                summaries.append({
                    "id": plan_id,
                    "plan_name": plan.get("plan_name", "Unnamed Plan"),
                    "race_date": str(goal.get("date", "")),
                    "race_name": goal.get("race_name", ""),
                    "goal_time": str(goal.get("goal_time", "")),
                    "weeks": len(plan.get("weeks", [])),
                })
            except Exception:
                continue
        summaries.sort(key=lambda p: p.get("race_date") or "")
        return summaries

    def find_week(self, plan: CommentedMap, week_number: int) -> CommentedMap | None:
        """Find a week by its week_number."""
        for week in plan.get("weeks", []):
            if week.get("week_number") == week_number:
                return week
        return None

    def find_run(
        self, week: CommentedMap, day_of_week: str
    ) -> CommentedMap | None:
        """Find a run within a week by day_of_week."""
        for run in week.get("runs", []):
            if run.get("day_of_week", "").lower() == day_of_week.lower():
                return run
        return None

    def get_current_week_number(self, plan: CommentedMap) -> int | None:
        """Determine which week is current based on today's date."""
        today = date.today()
        for week in plan.get("weeks", []):
            start_str = str(week.get("week_start_date", ""))
            if not start_str:
                continue
            try:
                start = date.fromisoformat(start_str)
            except ValueError:
                continue
            end = start + timedelta(days=6)
            if start <= today <= end:
                return week.get("week_number")
        return None

    def get_active_plan_id(self) -> str | None:
        """Find the plan whose race date is in the future and closest to today."""
        plans = self.list_plans()
        today = date.today()
        active = None
        for p in plans:
            try:
                race_date = date.fromisoformat(p["race_date"])
            except (ValueError, KeyError):
                continue
            if race_date >= today:
                if active is None or race_date < date.fromisoformat(active["race_date"]):
                    active = p
        return active["id"] if active else None
