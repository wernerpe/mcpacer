"""REST API endpoints for the web dashboard."""

from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from mcpacer.context import (
    _group_runs_by_week,
    _parse_run_date,
    _run_avg_hr,
    _week_monday,
)
from mcpacer.storage.runs import RunStorage
from mcpacer.storage.training_plans import TrainingPlanStorage
from mcpacer.web import body_state
from mcpacer.web.events import broadcast_json

router = APIRouter(prefix="/api")

plan_storage = TrainingPlanStorage()
run_storage = RunStorage()


DAY_ORDER = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}


def _speed_to_pace(speed_mps: float) -> str:
    """Convert m/s to min:sec/km string."""
    if speed_mps <= 0:
        return "0:00"
    pace_seconds = 1000.0 / speed_mps
    mins = int(pace_seconds // 60)
    secs = int(pace_seconds % 60)
    return f"{mins}:{secs:02d}"


def _run_to_json(run: dict[str, Any]) -> dict[str, Any]:
    """Convert a cached run to a JSON-friendly dict for the frontend."""
    dist_m = run.get("distance_metres", 0)
    speed = run.get("average_speed_mps", 0)
    return {
        "id": run.get("id"),
        "name": run.get("name", ""),
        "date": run.get("start_date", ""),
        "distance_km": round(dist_m / 1000, 1) if dist_m else 0,
        "duration_seconds": run.get("moving_time_seconds", 0),
        "pace": _speed_to_pace(speed) if speed else None,
        "avg_hr": round(_run_avg_hr(run), 0) if _run_avg_hr(run) else None,
        "max_hr": max((lap.get("max_heartrate", 0) for lap in run.get("laps", [])), default=None),
        "elevation_gain": round(run.get("total_elevation_gain_metres", 0)),
        "description": run.get("description", ""),
        "digest": run.get("run_digest"),
        "coach_notes": run.get("coach_notes", []),
    }


@router.get("/plan")
async def get_plan() -> dict[str, Any]:
    """Get the active training plan overview."""
    plan_id = plan_storage.get_active_plan_id()
    if not plan_id:
        return {"active": False}

    plan = plan_storage.load_plan(plan_id)
    if not plan:
        return {"active": False}

    goal_race = plan.get("goal_race", {})
    current_week = plan_storage.get_current_week_number(plan)

    weeks = []
    for week in plan.get("weeks", []):
        runs = []
        for run in week.get("runs", []):
            runs.append({
                "day": run.get("day_of_week", ""),
                "type": run.get("type", ""),
                "distance_km": run.get("distance_km"),
                "description": run.get("description", ""),
                "structure": run.get("structure"),
                "target_pace": run.get("target_pace_min_per_km"),
            })
        # Sort runs by day of week
        runs.sort(key=lambda r: DAY_ORDER.get(r["day"].lower(), 7))

        weeks.append({
            "week_number": week.get("week_number"),
            "start_date": str(week.get("week_start_date", "")),
            "planned_km": week.get("total_planned_distance_km", 0),
            "focus": week.get("weekly_focus", ""),
            "is_current": week.get("week_number") == current_week,
            "runs": runs,
        })

    return {
        "active": True,
        "plan_id": plan_id,
        "plan_name": plan.get("plan_name", ""),
        "race_name": goal_race.get("race_name", ""),
        "race_date": str(goal_race.get("date", "")),
        "goal_time": goal_race.get("goal_time", ""),
        "goal_pace": goal_race.get("goal_pace_min_per_km", ""),
        "current_week": current_week,
        "weeks": weeks,
    }


@router.get("/weeks")
async def get_weeks() -> list[dict[str, Any]]:
    """Get weekly volume summaries (planned vs actual)."""
    # Load plan for planned volumes
    plan_id = plan_storage.get_active_plan_id()
    plan = plan_storage.load_plan(plan_id) if plan_id else None
    plan_weeks: dict[str, dict] = {}
    current_week_num = None

    if plan:
        current_week_num = plan_storage.get_current_week_number(plan)
        for week in plan.get("weeks", []):
            start = str(week.get("week_start_date", ""))
            plan_weeks[start] = {
                "week_number": week.get("week_number"),
                "planned_km": week.get("total_planned_distance_km", 0),
                "focus": week.get("weekly_focus", ""),
                "is_current": week.get("week_number") == current_week_num,
            }

    # Load actual runs
    runs = run_storage.load_all_runs()
    runs_by_week = _group_runs_by_week(runs)

    # Build combined weeks
    all_mondays: set[date] = set()
    for start_str in plan_weeks:
        try:
            all_mondays.add(date.fromisoformat(start_str))
        except ValueError:
            pass
    all_mondays.update(runs_by_week.keys())

    cutoff = _week_monday(date.today()) - timedelta(weeks=12)
    result = []

    for monday in sorted(all_mondays):
        if monday < cutoff:
            continue

        monday_str = monday.isoformat()
        plan_info = plan_weeks.get(monday_str, {})
        week_runs = runs_by_week.get(monday, [])

        actual_km = sum(
            r.get("distance_metres", 0) / 1000 for r in week_runs
        )

        result.append({
            "start_date": monday_str,
            "week_number": plan_info.get("week_number"),
            "planned_km": plan_info.get("planned_km", 0),
            "actual_km": round(actual_km, 1),
            "focus": plan_info.get("focus", ""),
            "is_current": plan_info.get("is_current", False),
            "run_count": len(week_runs),
        })

    return result


@router.get("/weeks/{start_date}")
async def get_week_detail(start_date: str) -> dict[str, Any]:
    """Get detailed run data for a specific week."""
    try:
        monday = date.fromisoformat(start_date)
    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD."}

    # Get plan prescriptions for this week
    plan_id = plan_storage.get_active_plan_id()
    plan = plan_storage.load_plan(plan_id) if plan_id else None
    prescribed_runs: list[dict] = []

    if plan:
        for week in plan.get("weeks", []):
            if str(week.get("week_start_date", "")) == start_date:
                for run in week.get("runs", []):
                    prescribed_runs.append({
                        "day": run.get("day_of_week", ""),
                        "type": run.get("type", ""),
                        "distance_km": run.get("distance_km"),
                        "description": run.get("description", ""),
                        "structure": run.get("structure"),
                        "target_pace": run.get("target_pace_min_per_km"),
                    })
                prescribed_runs.sort(key=lambda r: DAY_ORDER.get(r["day"].lower(), 7))
                break

    # Get actual runs for this week
    runs = run_storage.load_all_runs()
    week_runs = []
    for run in runs:
        run_date = _parse_run_date(run)
        if run_date and _week_monday(run_date) == monday:
            week_runs.append(run)

    # Sort by date
    week_runs.sort(key=lambda r: r.get("start_date", ""))

    # Match actual runs to prescribed days
    actual_by_day: dict[str, list[dict]] = {}
    for run in week_runs:
        run_date = _parse_run_date(run)
        if run_date:
            day_name = run_date.strftime("%A")
            actual_by_day.setdefault(day_name, []).append(_run_to_json(run))

    return {
        "start_date": start_date,
        "prescribed": prescribed_runs,
        "actual_by_day": actual_by_day,
        "actual_runs": [_run_to_json(r) for r in week_runs],
    }


def _lap_to_json(lap: dict[str, Any], index: int) -> dict[str, Any]:
    """Convert a raw Strava lap to a JSON-friendly dict."""
    dist = lap.get("distance", 0)
    speed = lap.get("average_speed", 0)
    pace = _speed_to_pace(speed) if speed else None
    return {
        "index": index + 1,
        "name": lap.get("name", f"Lap {index + 1}"),
        "distance_km": round(dist / 1000, 2) if dist else 0,
        "moving_time_seconds": lap.get("moving_time", 0),
        "pace": pace,
        "avg_hr": round(lap.get("average_heartrate", 0)) if lap.get("average_heartrate") else None,
        "max_hr": round(lap.get("max_heartrate", 0)) if lap.get("max_heartrate") else None,
        "elevation_gain": round(lap.get("total_elevation_gain", 0), 1),
        "avg_cadence": round(lap.get("average_cadence", 0)) if lap.get("average_cadence") else None,
    }


@router.get("/runs/{activity_id}")
async def get_run_detail(activity_id: int) -> dict[str, Any]:
    """Get detailed data for a single run including laps."""
    runs = run_storage.load_all_runs()
    run = next((r for r in runs if r.get("id") == activity_id), None)
    if not run:
        return {"error": "Run not found"}

    base = _run_to_json(run)
    raw_laps = run.get("laps", [])
    base["laps"] = [_lap_to_json(lap, i) for i, lap in enumerate(raw_laps)]
    base["elapsed_time_seconds"] = run.get("elapsed_time_seconds", 0)
    base["elevation_gain"] = round(run.get("total_elevation_gain_metres", 0))
    base["start_latlng"] = run.get("start_latlng")
    base["summary_polyline"] = run.get("summary_polyline")
    return base


# ====================================================================
# Body state — shared between the web UI and the MCP body tools.
# UI POSTs painted regions; MCP server POSTs highlighted regions.
# All mutations broadcast on /ws/events as {"type": "body_state", ...}.
# ====================================================================


class BodyPaintRequest(BaseModel):
    regions: list[str]


class BodyHighlightRequest(BaseModel):
    regions: list[str]
    reason: str = ""


@router.get("/body/state")
async def get_body_state():
    return body_state.get_state()


@router.post("/body/painted")
async def post_body_painted(req: BodyPaintRequest):
    body_state.set_painted(req.regions)
    state = body_state.get_state()
    await broadcast_json({"type": "body_state", "state": state})
    return state


@router.post("/body/highlighted")
async def post_body_highlighted(req: BodyHighlightRequest):
    body_state.set_highlighted(req.regions, req.reason)
    state = body_state.get_state()
    await broadcast_json({"type": "body_state", "state": state})
    return state
