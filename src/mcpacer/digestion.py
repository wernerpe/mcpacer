"""Run digestion — compact structured summaries via LLM.

All recent runs get digested by a small LLM (Haiku via subagent). The LLM
determines from the lap data whether it's an easy run, workout, long run, etc.
No pre-classification needed on our end.

Digestion strategy (no extra API keys required):
1. get_pending_digests() returns recent undigested runs with pre-built prompts.
2. The host digests them — ideally via Haiku subagents (cheap, parallel),
   or the host LLM itself as fallback.
3. Host saves results via save_run_digest(activity_id, digest).
4. Digests are one-time — once saved, they persist across sessions.
"""

import re
from datetime import datetime, timedelta
from typing import Any

from mcpacer.utils.formatting import format_pace


# How far back to look for undigested runs
DIGEST_WINDOW_DAYS = 10

# Allowed run type tags — Haiku must pick exactly one
RUN_TYPE_TAGS = ["easy", "recovery", "long", "long-workout", "workout", "progression", "race", "shakeout"]


def needs_digest(run: dict[str, Any]) -> bool:
    """Check if a run needs digestion.

    Returns True if the run is recent (within DIGEST_WINDOW_DAYS) and
    doesn't have a digest yet. All recent runs get digested — the LLM
    figures out the structure from the lap data.
    """
    if run.get("run_digest"):
        return False

    date_str = run.get("start_date", "")
    if not date_str:
        return False

    try:
        run_date = datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()
    except ValueError:
        return False

    cutoff = datetime.now().date() - timedelta(days=DIGEST_WINDOW_DAYS)
    return run_date >= cutoff


def build_lap_table(run: dict[str, Any]) -> str:
    """Build a compact lap table from run laps for the digestion prompt."""
    laps = run.get("laps", [])
    if not laps:
        return "No lap data available."

    lines = ["Laps (dist, pace, HR, elev gain):"]
    for i, lap in enumerate(laps, 1):
        dist_km = lap.get("distance", 0) / 1000
        avg_speed = lap.get("average_speed", 0)
        pace = format_pace(avg_speed) if avg_speed > 0 else "N/A"
        hr = lap.get("average_heartrate")
        hr_str = f"HR {hr:.0f}" if hr else "HR N/A"
        elev = lap.get("total_elevation_gain", 0)
        lines.append(f"{i}: {dist_km:.2f}km  {pace}/km  {hr_str}  +{elev:.0f}m")

    return "\n".join(lines)


def _extract_athlete_description(description: str | None) -> str:
    """Extract the athlete's own text from a Strava description.

    Strips any coaching feedback (everything after the ------- separator)
    since that was written by the coach, not the athlete.
    """
    if not description:
        return ""
    # Coach feedback is appended after a ------- line
    parts = description.split("-------")
    athlete_text = parts[0].strip()
    return athlete_text


def build_digestion_prompt(run: dict[str, Any]) -> str:
    """Build the prompt for the digestion LLM.

    Includes the compact lap table and the athlete's Strava description
    (treated as authoritative, especially for treadmill runs).
    Coach feedback is stripped — only the athlete's own words are included.
    """
    name = run.get("name", "Unknown")
    description = _extract_athlete_description(run.get("description"))
    distance_km = run.get("distance_metres", 0) / 1000
    total_elev = run.get("total_elevation_gain_metres", 0)
    lap_table = build_lap_table(run)

    tags_str = ", ".join(RUN_TYPE_TAGS)

    prompt = f"""Summarize this run from the lap data below into a single compact line.

IMPORTANT: The athlete's description is authoritative. If they mention treadmill,
treat GPS pace data as approximate and prefer any paces they state. If the
description contradicts lap data, prefer the description.

Use this format — segments separated by |, elevation at end, then a [tag]:
- WU 2km @5:00/km HR 140 | 10×1km @3:45/km HR 165→185 rec 90s | CD 2km @5:00/km HR 138 | +110m [workout]
- WU 2km @5:30/km HR 132 | Tempo 20min @4:08/km HR 162→171 | CD 2km @5:30/km HR 138 | +45m [workout]
- Progression 16km @5:20→4:35/km HR 138→162 | +85m [progression]
- WU 10km @5:10/km HR 140 | 16km MP @4:15/km HR 160→170 | CD 8km @5:10/km HR 145 | +80m [long-workout]
- 0–28km @4:53/km HR 142→155 | 28–35km @5:20/km HR 155→162 (fade) | +180m [long]
- Easy 10km @5:15/km HR 135 | +50m [easy]
- Recovery 5km @6:00/km HR 120 | +10m [recovery]
- Shakeout 3km @5:30/km | +0m [shakeout]
- 10km race @3:55/km HR 172→180 | +25m [race]

Rules:
- One line only, no newlines
- Use × for repeats (e.g. 10×1km)
- HR as start→end for segments with drift, or single value if stable
- Include recovery duration/type between intervals if detectable from lap pattern
- Total elevation gain at the end as +Xm
- End the line with exactly one tag in brackets: [{tags_str}]

Activity name: "{name}"
Total distance: {distance_km:.1f}km
Total elevation: +{total_elev:.0f}m"""

    if description:
        prompt += f'\nAthlete description: "{description}"'

    prompt += f"\n\n{lap_table}"

    return prompt


def parse_digest_tag(digest: str) -> str:
    """Extract the run type tag from a digest string.

    Looks for a [tag] at the end of the digest. Returns the tag if valid,
    or "unknown" if missing/unrecognized.
    """
    match = re.search(r"\[([\w-]+)\]\s*$", digest)
    if match and match.group(1) in RUN_TYPE_TAGS:
        return match.group(1)
    return "unknown"


def strip_digest_tag(digest: str) -> str:
    """Return the digest text with the trailing [tag] removed."""
    return re.sub(r"\s*\[[\w-]+\]\s*$", "", digest)


def add_coach_note(run: dict[str, Any], note: str) -> dict[str, Any]:
    """Append a coach note to a run's coach_notes list.

    Args:
        run: The run data dict (modified in-place).
        note: The note text to append.

    Returns:
        The modified run dict.
    """
    if "coach_notes" not in run:
        run["coach_notes"] = []
    run["coach_notes"].append(note)
    return run
