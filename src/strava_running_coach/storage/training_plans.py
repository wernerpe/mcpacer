"""Training plan storage for persisting training plans."""

import uuid
from datetime import datetime
from typing import Any

from strava_running_coach.storage.base import BaseStorage


class TrainingPlanStorage(BaseStorage):
    """Storage for training plans."""

    def __init__(self) -> None:
        """Initialize training plan storage in the training_plans directory."""
        super().__init__("training_plans")

    def _generate_plan_id(self) -> str:
        """Generate a unique plan ID."""
        return str(uuid.uuid4())[:8]

    def save_plan(self, plan: dict[str, Any], plan_id: str | None = None) -> str:
        """
        Save a training plan.

        Args:
            plan: Training plan data (should conform to TrainingPlan model)
            plan_id: Optional plan ID. If not provided, one will be generated.

        Returns:
            The plan ID
        """
        if plan_id is None:
            plan_id = self._generate_plan_id()

        # Add metadata if not present
        if "id" not in plan:
            plan["id"] = plan_id
        if "created_at" not in plan:
            plan["created_at"] = datetime.now().isoformat()
        plan["updated_at"] = datetime.now().isoformat()

        file_path = self.data_dir / f"plan_{plan_id}.json"
        self._save_json(file_path, plan)
        return plan_id

    def get_plan(self, plan_id: str) -> dict[str, Any] | None:
        """
        Get a training plan by ID.

        Args:
            plan_id: The plan ID

        Returns:
            The training plan data or None if not found
        """
        file_path = self.data_dir / f"plan_{plan_id}.json"
        return self._load_json(file_path)  # type: ignore

    def list_plans(self) -> list[dict[str, Any]]:
        """
        List all training plans with summary information.

        Returns:
            List of plan summaries (id, name, race date, is_active)
        """
        summaries: list[dict[str, Any]] = []
        for file_path in self.data_dir.glob("plan_*.json"):
            plan = self._load_json(file_path)
            if plan and isinstance(plan, dict):
                goal_race = plan.get("goal_race", {})
                summaries.append({
                    "id": plan.get("id", file_path.stem.replace("plan_", "")),
                    "plan_name": plan.get("plan_name", "Unnamed Plan"),
                    "race_date": goal_race.get("date"),
                    "race_name": goal_race.get("race_name"),
                    "is_active": plan.get("is_active", True),
                    "created_at": plan.get("created_at"),
                    "updated_at": plan.get("updated_at"),
                })
        # Sort by race date (upcoming first)
        summaries.sort(key=lambda p: p.get("race_date") or "", reverse=False)
        return summaries

    def update_plan(self, plan_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        """
        Update an existing training plan by merging updates.

        Args:
            plan_id: The plan ID
            updates: Dictionary of fields to update

        Returns:
            The updated plan or None if not found
        """
        plan = self.get_plan(plan_id)
        if plan is None:
            return None

        # Deep merge updates into plan
        self._merge_dict(plan, updates)
        plan["updated_at"] = datetime.now().isoformat()

        file_path = self.data_dir / f"plan_{plan_id}.json"
        self._save_json(file_path, plan)
        return plan

    def delete_plan(self, plan_id: str) -> bool:
        """
        Delete a training plan.

        Args:
            plan_id: The plan ID

        Returns:
            True if deleted, False if not found
        """
        file_path = self.data_dir / f"plan_{plan_id}.json"
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def _merge_dict(self, base: dict[str, Any], updates: dict[str, Any]) -> None:
        """Recursively merge updates into base dictionary."""
        for key, value in updates.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_dict(base[key], value)
            else:
                base[key] = value
