"""MCP tools for training reports."""

from datetime import datetime, timedelta
from typing import Any

from strava_running_coach.storage.runs import RunStorage
from strava_running_coach.utils.dates import get_week_date_range, group_runs_by_week
from strava_running_coach.utils.formatting import format_duration, format_pace

# Configuration
LOOKBACK_WEEKS = 4


def fetch_run_details(client, activity_id: int) -> dict[str, Any]:
    """Fetch streams and laps for a single run."""
    run_details: dict[str, Any] = {}
    try:
        streams = client.get_activity_streams(
            activity_id, ["heartrate", "pace", "altitude", "cadence"]
        )
        run_details["streams"] = streams
    except Exception:
        run_details["streams"] = None
    try:
        laps = client.get_activity_laps(activity_id)
        run_details["laps"] = laps
    except Exception:
        run_details["laps"] = []
    return run_details


def fetch_and_save_new_runs(client, run_storage: RunStorage) -> int:
    """
    Fetch recent runs from Strava and save new ones locally.

    Returns:
        Number of new runs saved
    """
    existing_ids = run_storage.get_existing_run_ids()

    # Calculate date range
    after_date = datetime.now() - timedelta(weeks=LOOKBACK_WEEKS)
    after_timestamp = int(after_date.timestamp())

    # Fetch activities
    all_activities = client.get_activities(limit=200, after=after_timestamp)

    # Filter for running activities only
    runs = [a for a in all_activities if "run" in a.get("sport_type", "").lower()]

    # Identify new runs
    new_runs = [r for r in runs if r.get("id") not in existing_ids]

    # Fetch and save new runs
    for run in new_runs:
        activity_id = run.get("id")
        if not activity_id:
            continue
        details = fetch_run_details(client, activity_id)
        complete_run = {**run, **details}
        run_storage.save_run(complete_run, activity_id)

    return len(new_runs)


def calculate_summary_stats(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate summary statistics for a list of runs."""
    if not runs:
        return {
            "total_runs": 0,
            "total_distance_km": 0,
            "total_time": "0:00",
            "total_elevation_m": 0,
            "avg_pace": "N/A",
            "avg_hr": None,
        }

    total_distance = sum(r.get("distance_metres", 0) for r in runs)
    total_time = sum(r.get("moving_time_seconds", 0) for r in runs)
    total_elevation = sum(r.get("total_elevation_gain_metres", 0) for r in runs)

    # Calculate average pace
    avg_pace = "N/A"
    if total_distance > 0 and total_time > 0:
        avg_speed = total_distance / total_time
        avg_pace = format_pace(avg_speed)

    # Get average heartrate from laps
    hr_values = []
    for run in runs:
        laps = run.get("laps", [])
        for lap in laps:
            hr = lap.get("average_heartrate", 0)
            if hr > 0:
                hr_values.append(hr)

    avg_hr = round(sum(hr_values) / len(hr_values)) if hr_values else None

    return {
        "total_runs": len(runs),
        "total_distance_km": round(total_distance / 1000, 2),
        "total_time": format_duration(total_time),
        "total_elevation_m": round(total_elevation),
        "avg_pace": avg_pace,
        "avg_hr": avg_hr,
    }


def build_individual_run(run: dict[str, Any]) -> dict[str, Any]:
    """Build the individual run object for the report."""
    activity_id = run.get("id")
    name = run.get("name", "Unnamed Run")
    date_str = run.get("start_date", "")[:10]
    distance_km = round(run.get("distance_metres", 0) / 1000, 2)
    time_sec = run.get("moving_time_seconds", 0)
    elevation = round(run.get("total_elevation_gain_metres", 0))
    avg_speed = run.get("average_speed_mps", 0)
    pace = format_pace(avg_speed)

    # Get average HR from laps
    laps_data = run.get("laps", [])
    hr_values = [
        lap.get("average_heartrate", 0)
        for lap in laps_data
        if lap.get("average_heartrate", 0) > 0
    ]
    avg_hr = round(sum(hr_values) / len(hr_values)) if hr_values else None

    # Build laps list
    laps = []
    for i, lap in enumerate(laps_data, 1):
        lap_distance_km = round(lap.get("distance", 0) / 1000, 2)
        lap_speed = lap.get("average_speed", 0)
        lap_pace = format_pace(lap_speed)
        lap_hr = lap.get("average_heartrate", 0)
        laps.append(
            {
                "km": i,
                "distance_km": lap_distance_km,
                "pace": lap_pace,
                "hr": round(lap_hr) if lap_hr > 0 else None,
            }
        )

    return {
        "id": activity_id,
        "name": name,
        "date": date_str,
        "distance_km": distance_km,
        "time": format_duration(time_sec),
        "pace": pace,
        "elevation_m": elevation,
        "avg_hr": avg_hr,
        "laps": laps,
    }


def build_training_report(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Assemble the full training report structure."""
    # Overall summary
    overall_summary = calculate_summary_stats(runs)

    # Group by week
    runs_by_week = group_runs_by_week(runs)

    # Weekly summaries (sorted most recent first)
    weekly_summaries = []
    sorted_weeks = sorted(runs_by_week.items(), key=lambda x: (x[0][0], x[0][1]), reverse=True)
    for (year, week), week_runs in sorted_weeks:
        stats = calculate_summary_stats(week_runs)
        weekly_summaries.append(
            {
                "year": year,
                "week": week,
                "date_range": get_week_date_range(year, week),
                "runs": stats["total_runs"],
                "distance_km": stats["total_distance_km"],
                "time": stats["total_time"],
                "elevation_m": stats["total_elevation_m"],
                "avg_pace": stats["avg_pace"],
                "avg_hr": stats["avg_hr"],
            }
        )

    # Individual runs (sorted by date, most recent first)
    individual_runs = [build_individual_run(run) for run in runs]

    return {
        "overall_summary": overall_summary,
        "weekly_summaries": weekly_summaries,
        "individual_runs": individual_runs,
    }


def register_report_tools(mcp, strava_client):
    """Register report-related MCP tools."""

    run_storage = RunStorage()

    @mcp.tool()
    def get_training_report(refresh: bool = True) -> dict[str, Any]:
        """
        Get a comprehensive training report with recent running data.

        This tool fetches the latest running activities from Strava (if refresh=True),
        stores them locally, and returns a structured report with overall summary,
        weekly breakdowns, and individual run details including lap splits.

        Args:
            refresh: Whether to fetch latest data from Strava first (default: True).
                     Set to False to only use locally cached data.

        Returns:
            Dictionary containing:
            - overall_summary: Total runs, distance, time, elevation, avg pace, avg HR
            - weekly_summaries: Per-week breakdown with date range and stats
            - individual_runs: List of runs with date, name, distance, pace, HR, laps
        """
        try:
            new_runs_count = 0

            # Optionally refresh data from Strava
            if refresh:
                if strava_client is None:
                    return {
                        "error": "Strava client not initialized. Please provide refresh token, client ID, and client secret."
                    }
                new_runs_count = fetch_and_save_new_runs(strava_client, run_storage)

            # Load all local runs
            runs = run_storage.load_all_runs()

            if not runs:
                return {
                    "data": {
                        "overall_summary": calculate_summary_stats([]),
                        "weekly_summaries": [],
                        "individual_runs": [],
                    },
                    "message": "No run data found. Make sure you have running activities on Strava.",
                }

            # Build the report
            report = build_training_report(runs)

            result: dict[str, Any] = {"data": report}
            if refresh:
                result["new_runs_fetched"] = new_runs_count

            return result
        except Exception as e:
            return {"error": str(e)}
