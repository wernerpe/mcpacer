#!/usr/bin/env python3
"""
Analyze training plan adherence and show upcoming workouts.

This script compares your actual runs against your training plan and shows:
- Overall plan progress
- Completed vs missed workouts
- Upcoming workouts
- Plan adherence statistics
"""

import argparse
from datetime import datetime
from typing import Any

from strava_running_coach.storage.runs import RunStorage
from strava_running_coach.storage.training_plans import TrainingPlanStorage
from strava_running_coach.utils.formatting import format_pace


def parse_date(date_str: str) -> datetime:
    """Parse date string to datetime."""
    if "T" in date_str or "Z" in date_str:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    return datetime.strptime(date_str, "%Y-%m-%d")


def find_run_for_planned_workout(
    planned_run: dict[str, Any], actual_runs: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """Find actual run that matches a planned workout (within 1 day)."""
    if "date" not in planned_run:
        return None

    planned_date = parse_date(planned_run["date"]).date()

    for run in actual_runs:
        run_date = parse_date(run.get("start_date", "")).date()

        # Check if run is within 1 day of planned date
        if abs((run_date - planned_date).days) <= 1:
            # For non-running activities, we can't match them
            if planned_run["type"] in ["gym", "cross_training", "rest"]:
                continue
            return run

    return None


def calculate_pace_from_run(run: dict[str, Any]) -> str:
    """Calculate pace from actual run data."""
    distance = run.get("distance_metres", 0)
    time = run.get("moving_time_seconds", 0)

    if distance > 0 and time > 0:
        speed_mps = distance / time
        return format_pace(speed_mps)

    return "N/A"


def print_plan_overview(plan: dict[str, Any]) -> None:
    """Print overview of the training plan."""
    print("=" * 100)
    print("TRAINING PLAN OVERVIEW")
    print("=" * 100)
    print()

    goal_race = plan.get("goal_race", {})
    print(f"Plan Name:       {plan.get('plan_name', 'Unnamed Plan')}")
    print(
        f"Goal Race:       {goal_race.get('race_name', 'N/A')} - {goal_race.get('race_type', 'N/A')}"
    )
    print(f"Race Date:       {goal_race.get('date', 'N/A')}")
    print(f"Goal Time:       {goal_race.get('goal_time', 'N/A')}")
    print(f"Goal Pace:       {goal_race.get('goal_pace_min_per_km', 'N/A')} /km")
    print(
        f"Plan Duration:   {plan.get('plan_start_date', 'N/A')} to {plan.get('plan_end_date', 'N/A')}"
    )
    print()

    # Calculate days until race
    race_date_str = goal_race.get("date", "")
    if race_date_str:
        race_date = parse_date(race_date_str)
        today = datetime.now()
        days_until_race = (race_date - today).days

        if days_until_race > 0:
            weeks_until_race = days_until_race / 7
            print(f"Days until race: {days_until_race} ({weeks_until_race:.1f} weeks)")
        elif days_until_race == 0:
            print("Race day is TODAY!")
        else:
            print(f"Race was {abs(days_until_race)} days ago")

    print()


def print_upcoming_workouts(plan: dict[str, Any], days_ahead: int = 7) -> None:
    """Print upcoming workouts for the next N days."""
    print("=" * 100)
    print(f"UPCOMING WORKOUTS (Next {days_ahead} days)")
    print("=" * 100)
    print()

    today = datetime.now().date()
    upcoming: list[tuple[int, Any, dict[str, Any]]] = []

    for week in plan.get("weeks", []):
        for run in week.get("runs", []):
            if "date" not in run:
                continue

            run_date = parse_date(run["date"]).date()
            days_away = (run_date - today).days

            if 0 <= days_away <= days_ahead:
                upcoming.append((days_away, run_date, run))

    # Sort by date
    upcoming.sort(key=lambda x: x[0])

    if not upcoming:
        print("No workouts scheduled in the next week.")
        return

    for days_away, run_date, run in upcoming:
        day_label = (
            "TODAY"
            if days_away == 0
            else "TOMORROW" if days_away == 1 else f"in {days_away} days"
        )

        print(f"{run_date.strftime('%A, %B %d')} ({day_label})")
        print(f"  Type: {run['type'].replace('_', ' ').title()}")

        if run["type"] in ["gym", "cross_training"]:
            duration = run.get("duration_minutes", "N/A")
            print(f"  Duration: {duration} minutes")
        elif run["type"] == "rest":
            print("  Activity: Rest day")
        else:
            distance = run.get("distance_km", "N/A")
            pace = run.get("target_pace_min_per_km", "N/A")
            print(f"  Distance: {distance}km")
            print(f"  Target Pace: {pace} /km")

            if "structure" in run:
                print(f"  Structure: {run['structure']}")

        if "description" in run:
            print(f"  Notes: {run['description']}")

        print()


def analyze_plan_adherence(plan: dict[str, Any], actual_runs: list[dict[str, Any]]) -> None:
    """Analyze how well actual training matches the plan."""
    print("=" * 100)
    print("PLAN ADHERENCE ANALYSIS")
    print("=" * 100)
    print()

    today = datetime.now().date()
    completed_workouts: list[dict[str, Any]] = []
    missed_workouts: list[dict[str, Any]] = []
    upcoming_workouts: list[dict[str, Any]] = []

    for week in plan.get("weeks", []):
        week_num = week.get("week_number")

        for planned_run in week.get("runs", []):
            if "date" not in planned_run:
                continue

            run_date = parse_date(planned_run["date"]).date()

            # Skip future workouts
            if run_date > today:
                upcoming_workouts.append(planned_run)
                continue

            # Try to find matching actual run
            actual_run = find_run_for_planned_workout(planned_run, actual_runs)

            if actual_run:
                completed_workouts.append(
                    {"planned": planned_run, "actual": actual_run, "week": week_num}
                )
            else:
                # Only count as missed if it's a running workout
                if planned_run["type"] not in ["gym", "cross_training", "rest"]:
                    missed_workouts.append({"planned": planned_run, "week": week_num})

    # Calculate statistics
    total_planned = len(completed_workouts) + len(missed_workouts)
    completion_rate = (
        (len(completed_workouts) / total_planned * 100) if total_planned > 0 else 0
    )

    print(
        f"Workouts Completed: {len(completed_workouts)}/{total_planned} ({completion_rate:.1f}%)"
    )
    print(f"Workouts Missed:    {len(missed_workouts)}")
    print()

    # Show missed workouts
    if missed_workouts:
        print("-" * 100)
        print("MISSED WORKOUTS")
        print("-" * 100)
        print()

        for item in missed_workouts[-10:]:  # Show last 10 missed
            planned = item["planned"]
            date_str = planned.get("date", "N/A")
            print(f"{date_str} - Week {item['week']}")
            print(f"  Type: {planned['type'].replace('_', ' ').title()}")

            if "distance_km" in planned:
                print(
                    f"  Planned: {planned['distance_km']}km @ {planned.get('target_pace_min_per_km', 'N/A')} /km"
                )

            if "description" in planned:
                print(f"  Description: {planned['description']}")

            print()

    # Show recent completed workouts with comparison
    if completed_workouts:
        print("-" * 100)
        print("RECENT COMPLETED WORKOUTS (Last 5)")
        print("-" * 100)
        print()

        for item in completed_workouts[-5:]:
            planned = item["planned"]
            actual = item["actual"]
            date_str = planned.get("date", "N/A")

            print(f"{date_str} - Week {item['week']}: {actual.get('name', 'Unnamed Run')}")

            planned_dist = planned.get("distance_km", 0)
            actual_dist = actual.get("distance_metres", 0) / 1000
            planned_pace = planned.get("target_pace_min_per_km", "N/A")
            actual_pace = calculate_pace_from_run(actual)

            print(f"  Distance: {actual_dist:.1f}km (planned: {planned_dist}km)")
            print(f"  Pace:     {actual_pace} /km (target: {planned_pace} /km)")

            if "structure" in planned:
                print(f"  Workout:  {planned['structure']}")

            print()


def main() -> int:
    """Main function to analyze training plan."""
    parser = argparse.ArgumentParser(
        description="Analyze training plan adherence and show upcoming workouts"
    )
    parser.add_argument(
        "plan_id",
        nargs="?",
        help="Plan ID to analyze (if not provided, uses the most recent active plan)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days ahead to show upcoming workouts (default: 7)",
    )

    args = parser.parse_args()

    # Load training plan
    plan_storage = TrainingPlanStorage()

    if args.plan_id:
        plan = plan_storage.get_plan(args.plan_id)
        if not plan:
            print(f"Error: Plan not found: {args.plan_id}")
            return 1
    else:
        # Get the most recent active plan
        plans = plan_storage.list_plans()
        active_plans = [p for p in plans if p.get("is_active", True)]
        if not active_plans:
            print("No active training plans found.")
            print("Use save_training_plan() to create a plan first.")
            return 1
        plan = plan_storage.get_plan(active_plans[0]["id"])
        if not plan:
            print("Error loading plan")
            return 1

    # Load actual runs
    run_storage = RunStorage()
    actual_runs = run_storage.load_all_runs()

    # Print analyses
    print_plan_overview(plan)
    print_upcoming_workouts(plan, days_ahead=args.days)
    analyze_plan_adherence(plan, actual_runs)

    print("=" * 100)
    print("END OF ANALYSIS")
    print("=" * 100)

    return 0


if __name__ == "__main__":
    exit(main())
