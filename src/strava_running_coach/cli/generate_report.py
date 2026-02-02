#!/usr/bin/env python3
"""
Generate a hierarchical training report from local run data.

Structure:
1. Overall summary (last 4 weeks)
2. Week-by-week summaries
3. Individual runs with splits and detailed data
"""

import argparse
from typing import Any

from strava_running_coach.storage.runs import RunStorage
from strava_running_coach.utils.dates import group_runs_by_week
from strava_running_coach.utils.formatting import format_duration, format_pace


def calculate_summary_stats(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate summary statistics for a list of runs."""
    if not runs:
        return {}

    total_distance = sum(r.get("distance_metres", 0) for r in runs)
    total_time = sum(r.get("moving_time_seconds", 0) for r in runs)
    total_elevation = sum(r.get("total_elevation_gain_metres", 0) for r in runs)

    # Calculate average pace
    avg_pace = None
    if total_distance > 0 and total_time > 0:
        avg_speed = total_distance / total_time
        avg_pace = format_pace(avg_speed)

    # Get average heartrate from runs that have it
    hr_values: list[float] = []
    for run in runs:
        laps = run.get("laps", [])
        for lap in laps:
            if lap.get("average_heartrate", 0) > 0:
                hr_values.append(lap["average_heartrate"])

    avg_hr = sum(hr_values) / len(hr_values) if hr_values else None

    return {
        "total_runs": len(runs),
        "total_distance_km": total_distance / 1000,
        "total_time_seconds": total_time,
        "total_elevation_m": total_elevation,
        "avg_pace": avg_pace,
        "avg_hr": avg_hr,
        "avg_distance_km": total_distance / 1000 / len(runs) if runs else 0,
    }


def print_overall_summary(runs: list[dict[str, Any]], weeks: int = 4) -> None:
    """Print overall summary for the last N weeks."""
    print("=" * 100)
    print(f"TRAINING REPORT - LAST {weeks} WEEKS")
    print("=" * 100)
    print()

    stats = calculate_summary_stats(runs)

    print(f"Total Runs:           {stats['total_runs']}")
    print(f"Total Distance:       {stats['total_distance_km']:.2f} km")
    print(f"Total Time:           {format_duration(stats['total_time_seconds'])}")
    print(f"Total Elevation Gain: {stats['total_elevation_m']:.0f} m")
    print(f"Average Pace:         {stats['avg_pace']} /km")
    print(f"Average Distance:     {stats['avg_distance_km']:.2f} km")
    if stats["avg_hr"]:
        print(f"Average Heart Rate:   {stats['avg_hr']:.0f} bpm")
    print()


def print_weekly_summaries(
    runs_by_week: dict[tuple[int, int], list[dict[str, Any]]]
) -> None:
    """Print summary for each week."""
    print("=" * 100)
    print("WEEKLY SUMMARIES")
    print("=" * 100)
    print()

    # Sort weeks by date (most recent first)
    sorted_weeks = sorted(
        runs_by_week.items(), key=lambda x: (x[0][0], x[0][1]), reverse=True
    )

    for (year, week_num), week_runs in sorted_weeks:
        # Get date range for the week
        first_run_date = min(r.get("start_date", "") for r in week_runs)[:10]
        last_run_date = max(r.get("start_date", "") for r in week_runs)[:10]

        print(f"Week {week_num}, {year} ({first_run_date} to {last_run_date})")
        print("-" * 100)

        stats = calculate_summary_stats(week_runs)

        print(f"  Runs:          {stats['total_runs']}")
        print(f"  Distance:      {stats['total_distance_km']:.2f} km")
        print(f"  Time:          {format_duration(stats['total_time_seconds'])}")
        print(f"  Elevation:     {stats['total_elevation_m']:.0f} m")
        print(f"  Avg Pace:      {stats['avg_pace']} /km")
        print(f"  Avg Distance:  {stats['avg_distance_km']:.2f} km")
        if stats["avg_hr"]:
            print(f"  Avg HR:        {stats['avg_hr']:.0f} bpm")
        print()


def print_run_details(run: dict[str, Any]) -> None:
    """Print detailed information for a single run."""
    name = run.get("name", "Unnamed Run")
    date_str = run.get("start_date", "")[:10]
    distance_km = run.get("distance_metres", 0) / 1000
    time_sec = run.get("moving_time_seconds", 0)
    elevation = run.get("total_elevation_gain_metres", 0)

    # Calculate overall pace
    avg_speed = run.get("average_speed_mps", 0)
    pace = format_pace(avg_speed)

    print(f"{name} - {date_str}")
    print(
        f"  Distance: {distance_km:.2f} km | Time: {format_duration(time_sec)} | "
        f"Pace: {pace} /km | Elevation: {elevation:.0f} m"
    )

    # Print laps if available
    laps = run.get("laps", [])
    if laps:
        print(f"  Splits ({len(laps)} laps):")
        for i, lap in enumerate(laps, 1):
            lap_distance_km = lap.get("distance", 0) / 1000
            lap_time = lap.get("moving_time", 0)
            lap_speed = lap.get("average_speed", 0)
            lap_pace = format_pace(lap_speed)
            lap_hr = lap.get("average_heartrate", 0)
            lap_max_hr = lap.get("max_heartrate", 0)

            lap_info = (
                f"    Lap {i}: {lap_distance_km:.2f} km in "
                f"{format_duration(lap_time)} @ {lap_pace} /km"
            )

            if lap_hr > 0:
                lap_info += f" | HR: {int(lap_hr)} bpm (max: {int(lap_max_hr)})"

            print(lap_info)

    # Print stream data summary if available
    streams = run.get("streams")
    if streams:
        stream_types = [k for k in streams.keys() if streams[k]]
        if stream_types:
            print(f"  Available data streams: {', '.join(stream_types)}")

    print()


def print_individual_runs(
    runs_by_week: dict[tuple[int, int], list[dict[str, Any]]]
) -> None:
    """Print detailed information for all runs, grouped by week."""
    print("=" * 100)
    print("INDIVIDUAL RUNS")
    print("=" * 100)
    print()

    # Sort weeks by date (most recent first)
    sorted_weeks = sorted(
        runs_by_week.items(), key=lambda x: (x[0][0], x[0][1]), reverse=True
    )

    for (year, week_num), week_runs in sorted_weeks:
        print(f"--- Week {week_num}, {year} ---")
        print()

        # Sort runs within week by date (most recent first)
        week_runs.sort(key=lambda r: r.get("start_date", ""), reverse=True)

        for run in week_runs:
            print_run_details(run)

        print()


def main() -> int:
    """Generate and print the training report."""
    parser = argparse.ArgumentParser(
        description="Generate a hierarchical training report from local run data"
    )
    parser.add_argument(
        "--weeks",
        type=int,
        default=4,
        help="Number of weeks to include in the report (default: 4)",
    )

    args = parser.parse_args()

    # Load all runs
    print("Loading run data...")
    run_storage = RunStorage()
    runs = run_storage.load_all_runs()

    if not runs:
        print("No run data found. Run 'strava-update-data' first.")
        return 1

    print(f"Loaded {len(runs)} runs\n")

    # Group runs by week
    runs_by_week = group_runs_by_week(runs)

    # Print overall summary
    print_overall_summary(runs, weeks=args.weeks)

    # Print weekly summaries
    print_weekly_summaries(runs_by_week)

    # Print individual runs
    print_individual_runs(runs_by_week)

    print("=" * 100)
    print("END OF REPORT")
    print("=" * 100)

    return 0


if __name__ == "__main__":
    exit(main())
