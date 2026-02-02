"""MCP tools for training plan management."""

import json
from datetime import datetime
from typing import Any

from strava_running_coach.storage.runs import RunStorage
from strava_running_coach.storage.training_plans import TrainingPlanStorage
from strava_running_coach.utils.formatting import format_pace


def register_training_plan_tools(mcp):
    """Register training plan MCP tools."""

    plan_storage = TrainingPlanStorage()
    run_storage = RunStorage()

    @mcp.tool()
    def save_training_plan(plan_json: str, plan_id: str | None = None) -> dict[str, Any]:
        """
        Save a training plan.

        Claude should translate the user's text description into the JSON format
        defined in TRAINING_PLAN_FORMAT.md before calling this tool.

        Args:
            plan_json: JSON string containing the training plan data
            plan_id: Optional plan ID. If not provided, one will be generated.

        Returns:
            Dictionary with plan_id and saved status
        """
        try:
            plan = json.loads(plan_json)
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON: {e}"}

        try:
            saved_id = plan_storage.save_plan(plan, plan_id)
            return {
                "data": {
                    "plan_id": saved_id,
                    "saved": True,
                    "plan_name": plan.get("plan_name", "Unnamed Plan"),
                }
            }
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def list_training_plans() -> dict[str, Any]:
        """
        List all saved training plans.

        Returns:
            Dictionary containing list of plan summaries with id, name, race date, is_active
        """
        try:
            plans = plan_storage.list_plans()
            return {"data": {"plans": plans, "count": len(plans)}}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_training_plan(plan_id: str) -> dict[str, Any]:
        """
        Get a training plan by ID.

        Args:
            plan_id: The plan ID to retrieve

        Returns:
            Dictionary containing the full training plan data
        """
        try:
            plan = plan_storage.get_plan(plan_id)
            if plan is None:
                return {"error": f"Plan not found: {plan_id}"}
            return {"data": plan}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def update_training_plan(plan_id: str, updates_json: str) -> dict[str, Any]:
        """
        Update an existing training plan.

        Args:
            plan_id: The plan ID to update
            updates_json: JSON string containing the fields to update

        Returns:
            Dictionary with the updated plan data
        """
        try:
            updates = json.loads(updates_json)
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON: {e}"}

        try:
            updated_plan = plan_storage.update_plan(plan_id, updates)
            if updated_plan is None:
                return {"error": f"Plan not found: {plan_id}"}
            return {
                "data": {
                    "plan_id": plan_id,
                    "updated": True,
                    "plan": updated_plan,
                }
            }
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def delete_training_plan(plan_id: str) -> dict[str, Any]:
        """
        Delete a training plan.

        Args:
            plan_id: The plan ID to delete

        Returns:
            Dictionary with deletion status
        """
        try:
            deleted = plan_storage.delete_plan(plan_id)
            if not deleted:
                return {"error": f"Plan not found: {plan_id}"}
            return {"data": {"plan_id": plan_id, "deleted": True}}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def analyze_plan_adherence(plan_id: str) -> dict[str, Any]:
        """
        Analyze how well actual training matches the plan.

        Compares planned workouts against actual runs from Strava to show
        completion rate, missed workouts, and upcoming workouts.

        Args:
            plan_id: The plan ID to analyze

        Returns:
            Dictionary containing:
            - completion_rate: Percentage of planned workouts completed
            - completed_workouts: List of completed workouts with planned vs actual
            - missed_workouts: List of missed workouts
            - upcoming_workouts: List of upcoming workouts (next 7 days)
        """
        try:
            plan = plan_storage.get_plan(plan_id)
            if plan is None:
                return {"error": f"Plan not found: {plan_id}"}

            # Load actual runs
            actual_runs = run_storage.load_all_runs()

            today = datetime.now().date()
            completed_workouts: list[dict[str, Any]] = []
            missed_workouts: list[dict[str, Any]] = []
            upcoming_workouts: list[dict[str, Any]] = []

            for week in plan.get("weeks", []):
                week_num = week.get("week_number")

                for planned_run in week.get("runs", []):
                    if "date" not in planned_run:
                        continue

                    run_date_str = planned_run["date"]
                    # Parse date
                    if isinstance(run_date_str, str):
                        run_date = datetime.fromisoformat(run_date_str).date()
                    else:
                        run_date = run_date_str

                    # Skip non-running workouts for matching
                    workout_type = planned_run.get("type", "")
                    is_running = workout_type not in ["gym", "cross_training", "rest"]

                    # Future workouts
                    if run_date > today:
                        days_away = (run_date - today).days
                        if days_away <= 7:
                            upcoming_workouts.append(
                                {
                                    "date": str(run_date),
                                    "days_away": days_away,
                                    "week": week_num,
                                    **planned_run,
                                }
                            )
                        continue

                    # Past workouts - try to find matching actual run
                    if not is_running:
                        continue

                    actual_run = _find_matching_run(run_date, actual_runs)

                    if actual_run:
                        completed_workouts.append(
                            {
                                "date": str(run_date),
                                "week": week_num,
                                "planned": planned_run,
                                "actual": {
                                    "name": actual_run.get("name", "Unnamed"),
                                    "distance_km": round(
                                        actual_run.get("distance_metres", 0) / 1000, 2
                                    ),
                                    "pace": _calculate_pace(actual_run),
                                },
                            }
                        )
                    else:
                        missed_workouts.append(
                            {
                                "date": str(run_date),
                                "week": week_num,
                                **planned_run,
                            }
                        )

            # Calculate completion rate
            total_planned = len(completed_workouts) + len(missed_workouts)
            completion_rate = (
                round(len(completed_workouts) / total_planned * 100, 1)
                if total_planned > 0
                else 0
            )

            return {
                "data": {
                    "plan_id": plan_id,
                    "plan_name": plan.get("plan_name", "Unnamed Plan"),
                    "completion_rate": completion_rate,
                    "workouts_completed": len(completed_workouts),
                    "workouts_missed": len(missed_workouts),
                    "completed_workouts": completed_workouts[-5:],  # Last 5
                    "missed_workouts": missed_workouts[-10:],  # Last 10
                    "upcoming_workouts": upcoming_workouts,
                }
            }
        except Exception as e:
            return {"error": str(e)}


def _find_matching_run(
    planned_date: Any, actual_runs: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """Find an actual run that matches a planned date (within 1 day)."""
    for run in actual_runs:
        run_date_str = run.get("start_date", "")
        if not run_date_str:
            continue

        try:
            run_date = datetime.fromisoformat(run_date_str.replace("Z", "+00:00")).date()
            if abs((run_date - planned_date).days) <= 1:
                return run
        except (ValueError, TypeError):
            continue

    return None


def _calculate_pace(run: dict[str, Any]) -> str:
    """Calculate pace from run data."""
    distance = run.get("distance_metres", 0)
    time = run.get("moving_time_seconds", 0)

    if distance > 0 and time > 0:
        speed_mps = distance / time
        return format_pace(speed_mps)

    return "N/A"
