"""Run context engine — server-rendered, age-tiered training snapshot.

Produces a pre-formatted text block for the LLM to read directly.
No JSON, no arrays — just a document.

Tiering rules:
- Older weeks (>2 weeks ago): one-liner per week
- Recent weeks (current + previous 1-2): one line per run
- Weeks older than 12 weeks: omitted entirely
"""

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any

from strava_running_coach.digestion import parse_digest_tag, strip_digest_tag
from strava_running_coach.storage.runs import RunStorage
from strava_running_coach.utils.formatting import format_pace, format_duration


# How far back to include in context
MAX_WEEKS_BACK = 12
# Weeks with per-run detail (current + N previous)
RECENT_DETAIL_WEEKS = 2


def _parse_run_date(run: dict[str, Any]) -> date | None:
    """Extract date from a run's start_date field."""
    date_str = run.get("start_date", "")
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _week_monday(d: date) -> date:
    """Get the Monday of the ISO week containing date d."""
    return d - timedelta(days=d.weekday())


def _group_runs_by_week(runs: list[dict[str, Any]]) -> dict[date, list[dict[str, Any]]]:
    """Group runs by their ISO week (keyed by Monday date)."""
    weeks: dict[date, list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        run_date = _parse_run_date(run)
        if run_date:
            monday = _week_monday(run_date)
            weeks[monday].append(run)
    # Sort runs within each week by date
    for monday in weeks:
        weeks[monday].sort(key=lambda r: r.get("start_date", ""))
    return dict(weeks)


def _run_avg_hr(run: dict[str, Any]) -> int | None:
    """Get average HR from laps data."""
    laps = run.get("laps", [])
    hrs = [lap.get("average_heartrate", 0) for lap in laps if lap.get("average_heartrate", 0) > 0]
    return round(sum(hrs) / len(hrs)) if hrs else None


def _run_max_hr(run: dict[str, Any]) -> int | None:
    """Get max HR from laps data."""
    laps = run.get("laps", [])
    maxes = [lap.get("max_heartrate", 0) for lap in laps if lap.get("max_heartrate", 0) > 0]
    return round(max(maxes)) if maxes else None


def _run_type_from_digest(run: dict[str, Any]) -> str:
    """Get run type from the digest tag, or fall back to distance heuristic."""
    digest = run.get("run_digest") or ""
    if digest:
        return parse_digest_tag(digest)
    # No digest — use distance as rough heuristic
    if run.get("distance_metres", 0) > 25000:
        return "long"
    return "unknown"


def _format_run_oneliner(run: dict[str, Any]) -> str:
    """Format a single run as a detailed one-liner for recent weeks.

    Format: Day Mon DD  Name 5.0km 0:27m | 5:24/km | HR 128/142 | #17750001
    """
    run_date = _parse_run_date(run)
    if not run_date:
        return "  (unknown date)"

    day_str = run_date.strftime("%a %b %d")

    # Name
    name = run.get("name", "Run")

    # Distance
    dist_km = run.get("distance_metres", 0) / 1000

    # Duration
    moving_time = run.get("moving_time_seconds", 0)
    duration = format_duration(moving_time)

    # Pace
    avg_speed = run.get("average_speed_mps", 0)
    pace = format_pace(avg_speed) if avg_speed > 0 else "N/A"

    # HR
    avg_hr = _run_avg_hr(run)
    max_hr = _run_max_hr(run)
    hr_str = ""
    if avg_hr:
        hr_str = f" | HR {avg_hr}"
        if max_hr:
            hr_str += f"/{max_hr}"

    # Activity ID for drill-down
    activity_id = run.get("id", "")

    line = f"  {day_str}  {name} {dist_km:.1f}km {duration} | {pace}/km{hr_str} | #{activity_id}"

    # Digest line (if present)
    digest = run.get("run_digest")
    coach_notes = run.get("coach_notes", [])

    parts = [line]
    if digest:
        parts.append(f"       → {strip_digest_tag(digest)}")
    for note in coach_notes:
        parts.append(f"       📝 {note}")

    return "\n".join(parts)


def _week_avg_pace(runs: list[dict[str, Any]]) -> str:
    """Calculate weighted average pace for a week's runs."""
    total_dist = sum(r.get("distance_metres", 0) for r in runs)
    total_time = sum(r.get("moving_time_seconds", 0) for r in runs)
    if total_dist > 0 and total_time > 0:
        avg_speed = total_dist / total_time
        return format_pace(avg_speed)
    return ""


def _week_avg_hr(runs: list[dict[str, Any]]) -> int | None:
    """Calculate weighted average HR for a week's runs (from lap data)."""
    total_hr_time = 0.0
    total_time = 0.0
    for run in runs:
        for lap in run.get("laps", []):
            hr = lap.get("average_heartrate", 0)
            t = lap.get("moving_time", 0)
            if hr > 0 and t > 0:
                total_hr_time += hr * t
                total_time += t
    return round(total_hr_time / total_time) if total_time > 0 else None


def _abbreviate_digest(digest: str, dist_km: float, fallback_type: str) -> str:
    """Abbreviate a digest for the week summary line.

    For workouts: extract just the main set (e.g. "5×2km @3:55→3:59/km").
    Strips WU/CD segments to keep the line compact.
    For long runs: keep as-is if short, otherwise just "Long Xkm".
    """
    if not digest:
        return f"{fallback_type} {dist_km:.0f}km"

    # Split on | segments
    segments = [s.strip() for s in digest.split("|")]

    if fallback_type == "Workout":
        # Find the main set — the segment with × or the one that's not WU/CD/elevation
        main_segments = []
        for seg in segments:
            seg_lower = seg.lower()
            if seg_lower.startswith("wu ") or seg_lower.startswith("cd "):
                continue
            if seg.startswith("+") and seg[-1] == "m":
                continue
            main_segments.append(seg)
        if main_segments:
            return " | ".join(main_segments)

    # For long runs / fallback: if digest is short enough, use it
    if len(digest) <= 40:
        return digest
    return f"{fallback_type} {dist_km:.0f}km"


def _format_week_oneliner(monday: date, runs: list[dict[str, Any]], week_num: int) -> str:
    """Format a week as a compact one-liner for older weeks.

    Format: W1  Feb 2   75km | 5 runs | 5:10/km HR 140 | Long 27km | Workout: 5×1600m @4:00
    """
    sunday = monday + timedelta(days=6)
    month_day = monday.strftime("%b %-d")

    total_dist = sum(r.get("distance_metres", 0) for r in runs) / 1000
    n_runs = len(runs)

    # Average pace and HR for the week
    avg_pace = _week_avg_pace(runs)
    avg_hr = _week_avg_hr(runs)

    # Find notable sessions — abbreviated for the week summary
    highlights = []
    for run in runs:
        run_type = _run_type_from_digest(run)
        dist_km = run.get("distance_metres", 0) / 1000
        digest = strip_digest_tag(run.get("run_digest", ""))

        if run_type in ("long", "long-workout") or (run_type == "unknown" and dist_km > 25):
            highlights.append(_abbreviate_digest(digest, dist_km, "Long"))
        elif run_type == "workout":
            highlights.append(_abbreviate_digest(digest, dist_km, "Workout"))

    highlight_str = " | ".join(highlights) if highlights else ""

    line = f"W{week_num:<3d} {month_day:<8s} {total_dist:.0f}km | {n_runs} runs"
    if avg_pace:
        pace_part = f" | {avg_pace}/km"
        if avg_hr:
            pace_part += f" HR {avg_hr}"
        line += pace_part
    if highlight_str:
        line += f" | {highlight_str}"

    return line


def render_run_context(runs: list[dict[str, Any]]) -> str:
    """Render the full run context as a pre-formatted text block.

    Args:
        runs: All cached runs (will be filtered by date).

    Returns:
        The complete training overview text.
    """
    today = date.today()
    current_monday = _week_monday(today)
    cutoff = current_monday - timedelta(weeks=MAX_WEEKS_BACK)
    recent_cutoff = current_monday - timedelta(weeks=RECENT_DETAIL_WEEKS)

    # Filter runs within the window
    filtered_runs = []
    for run in runs:
        run_date = _parse_run_date(run)
        if run_date and run_date >= cutoff:
            filtered_runs.append(run)

    if not filtered_runs:
        return "=== TRAINING OVERVIEW ===\n\nNo runs found in the last 12 weeks."

    # Group by week
    weeks = _group_runs_by_week(filtered_runs)

    # Split into older and recent
    older_weeks = {}
    recent_weeks = {}
    for monday, week_runs in weeks.items():
        if monday < recent_cutoff:
            older_weeks[monday] = week_runs
        else:
            recent_weeks[monday] = week_runs

    lines = ["=== TRAINING OVERVIEW ==="]

    # Older weeks — one-liner each
    if older_weeks:
        sorted_older = sorted(older_weeks.keys())
        first_monday = sorted_older[0]
        last_sunday = sorted_older[-1] + timedelta(days=6)
        lines.append("")
        lines.append(
            f"Weeks {first_monday.strftime('%b %-d')} – {last_sunday.strftime('%b %-d')}:"
        )

        # Number weeks sequentially
        all_mondays = sorted(weeks.keys())
        week_numbers = {m: i + 1 for i, m in enumerate(all_mondays)}

        for monday in sorted_older:
            week_num = week_numbers[monday]
            week_runs = older_weeks[monday]
            lines.append(week_num_line := _format_week_oneliner(monday, week_runs, week_num))

    # Recent weeks — per-run detail
    if recent_weeks:
        lines.append("")
        lines.append("=== RECENT DETAIL ===")

        all_mondays = sorted(weeks.keys())
        week_numbers = {m: i + 1 for i, m in enumerate(all_mondays)}

        for monday in sorted(recent_weeks.keys()):
            sunday = monday + timedelta(days=6)
            week_num = week_numbers[monday]
            is_current = monday == current_monday
            week_runs = recent_weeks[monday]

            # Summary line matching the older-week style
            summary = _format_week_oneliner(monday, week_runs, week_num)
            if is_current:
                summary += "  ← CURRENT"
            lines.append(f"\n{summary}")

            if week_runs:
                for run in week_runs:
                    lines.append(_format_run_oneliner(run))
            else:
                lines.append("  (no runs yet)")

    # Current week with no runs yet
    if current_monday not in weeks:
        lines.append(f"\nWeek — {current_monday.strftime('%b %-d')}–{(current_monday + timedelta(days=6)).strftime('%-d')} (current)")
        lines.append("  (no runs yet)")

    lines.append("")
    lines.append("For detail on any run: get_run_detail(activity_id)")

    return "\n".join(lines)
