"""Plan context renderer — compact text snapshot of the active training plan."""

from datetime import date, timedelta
from typing import Any

from ruamel.yaml.comments import CommentedMap

# Day abbreviations for the compact format
DAY_ABBREV = {
    "Monday": "Mon", "Tuesday": "Tue", "Wednesday": "Wed",
    "Thursday": "Thu", "Friday": "Fri", "Saturday": "Sat", "Sunday": "Sun",
}


def _format_run_compact(run: dict[str, Any]) -> str:
    """Format a single planned run compactly for the week line.

    Examples:
        Mon 10km easy
        Wed 2km WU, 5×1600m @4:00 w/400m jog rec, 2km CD
        Thu 💪 Gym 60min
        Sun 28km w/10km MP
    """
    day = DAY_ABBREV.get(run.get("day_of_week", ""), run.get("day_of_week", "?"))
    run_type = run.get("type", "")

    # Non-running activities
    if run_type in ("gym", "cross_training", "rest"):
        duration = run.get("duration_minutes")
        desc = run.get("description", run_type)
        if run_type == "gym":
            return f"{day} 💪 {desc}" + (f" {duration}min" if duration else "")
        if run_type == "rest":
            return f"{day} Rest"
        return f"{day} {desc}" + (f" {duration}min" if duration else "")

    # Running activities
    dist = run.get("distance_km")
    structure = run.get("structure")
    description = run.get("description", "")

    if structure:
        # Structured workout — show the full structure
        return f"{day} {structure}"

    if dist:
        # Simple run — show distance + type/description
        label = description or run_type or "run"
        return f"{day} {dist:.0f}km {label}"

    return f"{day} {description or run_type or '?'}"


def _get_week_comments(week: CommentedMap) -> list[str]:
    """Extract YAML comments from a week block."""
    comments = []
    # ruamel.yaml stores comments in .ca attribute
    if hasattr(week, "ca") and week.ca:
        # Check for end-of-line comment on the week mapping itself
        for key in ["week_number", "weekly_focus"]:
            if key in week:
                try:
                    comment = week.ca.items.get(key)
                    if comment and comment[2]:
                        text = comment[2].value.strip().lstrip("#").strip()
                        if text:
                            comments.append(text)
                except (AttributeError, IndexError, TypeError):
                    pass
    return comments


def render_plan_context(plan: CommentedMap) -> str:
    """Render an active training plan as compact text.

    Two lines per week: header with volume + focus, then day-by-day prescription.
    Current week marked with → and ← CURRENT.

    Args:
        plan: The loaded YAML plan (CommentedMap).

    Returns:
        Pre-formatted text block.
    """
    plan_name = plan.get("plan_name", "Training Plan")
    goal_race = plan.get("goal_race", {}) or {}
    race_type = goal_race.get("race_type", "")
    race_date = goal_race.get("date", "")
    goal_time = goal_race.get("goal_time", "")
    goal_pace = goal_race.get("goal_pace_min_per_km", "")
    race_name = goal_race.get("race_name", "")

    # Header
    lines = [f"=== ACTIVE PLAN: {plan_name} ==="]

    race_info = race_type.title() if race_type else "Race"
    if race_name:
        race_info = race_name
    if race_date:
        try:
            d = date.fromisoformat(str(race_date))
            race_info += f" — {d.strftime('%b %-d, %Y')}"
        except ValueError:
            race_info += f" — {race_date}"
    if goal_time:
        race_info += f" — Goal {goal_time}"
    if goal_pace:
        race_info += f" ({goal_pace}/km)"
    lines.append(f"Race: {race_info}")

    # Determine current week
    today = date.today()
    current_week_num = None
    total_weeks = len(plan.get("weeks", []))

    for week in plan.get("weeks", []):
        start_str = str(week.get("week_start_date", ""))
        if not start_str:
            continue
        try:
            start = date.fromisoformat(start_str)
            if start <= today <= start + timedelta(days=6):
                current_week_num = week.get("week_number")
                break
        except ValueError:
            continue

    if current_week_num:
        lines.append(f"Status: Week {current_week_num} of {total_weeks}")
    lines.append("")

    # Weeks
    for week in plan.get("weeks", []):
        week_num = week.get("week_number", "?")
        start_str = str(week.get("week_start_date", ""))
        total_km = week.get("total_planned_distance_km", "")
        focus = week.get("weekly_focus", "")

        # Format the start date
        date_str = ""
        if start_str:
            try:
                d = date.fromisoformat(start_str)
                date_str = d.strftime("%b %-d")
            except ValueError:
                date_str = start_str

        # Week comments from YAML
        comments = _get_week_comments(week)
        comment_str = f"  # {'; '.join(comments)}" if comments else ""

        # Header line
        is_current = week_num == current_week_num
        prefix = "→ " if is_current else "  "
        suffix = "  ← CURRENT" if is_current else ""

        km_str = f"{total_km:.0f}km" if isinstance(total_km, (int, float)) else str(total_km)
        header = f"{prefix}W{week_num:<3d} {date_str:<8s} {km_str:<6s} {focus}{comment_str}{suffix}"
        lines.append(header)

        # Day-by-day line
        runs = week.get("runs", [])
        if runs:
            run_strs = [_format_run_compact(r) for r in runs]
            lines.append(f"    {' | '.join(run_strs)}")

    lines.append("")
    # Find plan ID from the plan data or just hint at the tool
    lines.append("For full plan YAML: get_training_plan(plan_id)")

    return "\n".join(lines)
