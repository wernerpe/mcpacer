"""MCP tools for YAML training plan management — surgical edits only."""

import json
from typing import Any

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from mcpacer.plan_context import render_plan_context
from mcpacer.storage.training_plans import TrainingPlanStorage, DAY_ORDER


def register_training_plan_tools(mcp):
    """Register training plan MCP tools."""

    plan_storage = TrainingPlanStorage()

    @mcp.tool()
    def get_plan_context() -> str:
        """
        Get the active training plan rendered as compact text.

        Returns a two-line-per-week overview with the current week highlighted.
        If no active plan exists, returns a message saying so — the coach
        works fine without a plan (off-season, casual running, etc.).

        Returns:
            Pre-formatted plan overview text.
        """
        plan_id = plan_storage.get_active_plan_id()
        if not plan_id:
            return "No active training plan."

        plan = plan_storage.load_plan(plan_id)
        if not plan:
            return "No active training plan."

        return render_plan_context(plan)

    @mcp.tool()
    def list_training_plans() -> dict[str, Any]:
        """
        List all saved training plans with summary metadata.

        Returns:
            Dict with plans list (id, name, race_date, goal_time, weeks count).
        """
        plans = plan_storage.list_plans()
        if not plans:
            return {"message": "No training plans found."}
        return {"plans": plans}

    @mcp.tool()
    def get_training_plan(plan_id: str) -> str:
        """
        Get the full YAML content of a training plan.

        Use this when you need to inspect or edit individual workouts.
        For the compact overview, use get_plan_context() instead.

        Args:
            plan_id: The plan ID.

        Returns:
            Raw YAML content as text.
        """
        raw = plan_storage.load_plan_raw(plan_id)
        if raw is None:
            return f"Plan '{plan_id}' not found."
        return raw

    @mcp.tool()
    def update_plan_run(
        plan_id: str, week_number: int, day_of_week: str, updates_json: str
    ) -> str:
        """
        Modify a single workout within a week. Surgical edit — only the
        specified fields are changed, everything else is preserved.

        Args:
            plan_id: The plan ID.
            week_number: Which week (1-indexed).
            day_of_week: Day name (e.g. "Tuesday", "Sunday").
            updates_json: JSON string of fields to update.
                Example: {"type": "easy", "distance_km": 10, "description": "Recovery run"}

        Returns:
            Confirmation message.
        """
        plan = plan_storage.load_plan(plan_id)
        if plan is None:
            return f"Plan '{plan_id}' not found."

        try:
            updates = json.loads(updates_json)
        except json.JSONDecodeError as e:
            return f"Invalid JSON: {e}"

        week = plan_storage.find_week(plan, week_number)
        if week is None:
            return f"Week {week_number} not found in plan."

        run = plan_storage.find_run(week, day_of_week)
        if run is None:
            return f"No run on {day_of_week} in week {week_number}."

        for key, value in updates.items():
            run[key] = value

        plan_storage.save_plan(plan, plan_id)
        return f"Updated {day_of_week} in week {week_number}: {updates}"

    @mcp.tool()
    def update_plan_week(
        plan_id: str, week_number: int, updates_json: str
    ) -> str:
        """
        Update week-level metadata (weekly_focus, total_planned_distance_km, etc.).

        Args:
            plan_id: The plan ID.
            week_number: Which week.
            updates_json: JSON string of week-level fields to update.
                Example: {"weekly_focus": "Deload week", "total_planned_distance_km": 50}

        Returns:
            Confirmation message.
        """
        plan = plan_storage.load_plan(plan_id)
        if plan is None:
            return f"Plan '{plan_id}' not found."

        try:
            updates = json.loads(updates_json)
        except json.JSONDecodeError as e:
            return f"Invalid JSON: {e}"

        week = plan_storage.find_week(plan, week_number)
        if week is None:
            return f"Week {week_number} not found in plan."

        for key, value in updates.items():
            if key == "runs":
                return "Use update_plan_run, add_plan_run, or remove_plan_run to modify runs."
            week[key] = value

        plan_storage.save_plan(plan, plan_id)
        return f"Updated week {week_number}: {updates}"

    @mcp.tool()
    def add_plan_run(
        plan_id: str, week_number: int, run_json: str
    ) -> str:
        """
        Add a new workout to a week.

        Args:
            plan_id: The plan ID.
            week_number: Which week.
            run_json: JSON string of the run to add.
                Example: {"day_of_week": "Friday", "type": "easy", "distance_km": 8, "description": "Recovery"}

        Returns:
            Confirmation message.
        """
        plan = plan_storage.load_plan(plan_id)
        if plan is None:
            return f"Plan '{plan_id}' not found."

        try:
            run_data = json.loads(run_json)
        except json.JSONDecodeError as e:
            return f"Invalid JSON: {e}"

        week = plan_storage.find_week(plan, week_number)
        if week is None:
            return f"Week {week_number} not found in plan."

        day = run_data.get("day_of_week", "")
        if not day:
            return "Run must have a 'day_of_week' field."

        # Check for existing run on that day
        existing = plan_storage.find_run(week, day)
        if existing is not None:
            return f"A run already exists on {day} in week {week_number}. Use update_plan_run to modify it."

        # Convert to CommentedMap for YAML compatibility
        new_run = CommentedMap(run_data)

        if "runs" not in week:
            week["runs"] = CommentedSeq()
        week["runs"].append(new_run)

        # Sort runs by day of week
        runs_list = list(week["runs"])
        runs_list.sort(key=lambda r: DAY_ORDER.get(r.get("day_of_week", ""), 7))
        week["runs"] = CommentedSeq(runs_list)

        plan_storage.save_plan(plan, plan_id)
        return f"Added {day} run to week {week_number}."

    @mcp.tool()
    def remove_plan_run(
        plan_id: str, week_number: int, day_of_week: str
    ) -> str:
        """
        Remove a workout from a week.

        Args:
            plan_id: The plan ID.
            week_number: Which week.
            day_of_week: Day name (e.g. "Thursday").

        Returns:
            Confirmation message.
        """
        plan = plan_storage.load_plan(plan_id)
        if plan is None:
            return f"Plan '{plan_id}' not found."

        week = plan_storage.find_week(plan, week_number)
        if week is None:
            return f"Week {week_number} not found in plan."

        runs = week.get("runs", [])
        for i, run in enumerate(runs):
            if run.get("day_of_week", "").lower() == day_of_week.lower():
                del runs[i]
                plan_storage.save_plan(plan, plan_id)
                return f"Removed {day_of_week} run from week {week_number}."

        return f"No run on {day_of_week} in week {week_number}."

    @mcp.tool()
    def add_plan_comment(
        plan_id: str, week_number: int, comment: str
    ) -> str:
        """
        Add a YAML comment to a week block. Documents plan adjustments
        in the plan itself (e.g. "Deload week — groin recovery, cut volume 30%").

        These comments persist through all future reads and exports.

        Args:
            plan_id: The plan ID.
            week_number: Which week.
            comment: The comment text (without # prefix).

        Returns:
            Confirmation message.
        """
        plan = plan_storage.load_plan(plan_id)
        if plan is None:
            return f"Plan '{plan_id}' not found."

        week = plan_storage.find_week(plan, week_number)
        if week is None:
            return f"Week {week_number} not found in plan."

        # Add comment before the week block using ruamel.yaml's comment API
        weeks = plan.get("weeks", [])
        for i, w in enumerate(weeks):
            if w.get("week_number") == week_number:
                weeks.yaml_set_comment_before_after_key(
                    i, before=f" {comment}", indent=2
                )
                break

        plan_storage.save_plan(plan, plan_id)
        return f"Comment added to week {week_number}: # {comment}"
