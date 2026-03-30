"""Date utility functions for the Strava Running Coach."""

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any


def timestamp_to_date(timestamp: int) -> date:
    """
    Convert a Unix timestamp to a date object.

    Args:
        timestamp: Unix timestamp

    Returns:
        Date object
    """
    return datetime.fromtimestamp(timestamp).date()


def date_to_timestamp(date_obj: date) -> int:
    """
    Convert a date object to a Unix timestamp (end of day).

    Args:
        date_obj: Date object

    Returns:
        Unix timestamp
    """
    dt = datetime.combine(date_obj, datetime.max.time())
    return int(dt.timestamp())


def parse_date(date_str: str) -> date:
    """
    Parse a date string in ISO format (YYYY-MM-DD).

    Args:
        date_str: Date string in ISO format

    Returns:
        Date object
    """
    try:
        return date.fromisoformat(date_str)
    except ValueError as err:
        raise ValueError(f"Invalid date format: {date_str}. Expected format: YYYY-MM-DD") from err


def get_week_key(date_str: str) -> tuple[int, int]:
    """Get (year, ISO week number) from date string."""
    dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    iso_cal = dt.isocalendar()
    return iso_cal[0], iso_cal[1]


def get_week_date_range(year: int, week: int) -> str:
    """Get the date range string for a given ISO week."""
    # ISO week 1 starts on the Monday of the week containing Jan 4
    jan4 = datetime(year, 1, 4)
    week1_monday = jan4 - timedelta(days=jan4.weekday())
    week_monday = week1_monday + timedelta(weeks=week - 1)
    week_sunday = week_monday + timedelta(days=6)
    return f"{week_monday.strftime('%Y-%m-%d')} to {week_sunday.strftime('%Y-%m-%d')}"


def group_runs_by_week(runs: list[dict[str, Any]]) -> dict[tuple[int, int], list[dict[str, Any]]]:
    """Group runs by ISO week number."""
    weeks: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        date_str = run.get("start_date", "")
        if date_str:
            week_key = get_week_key(date_str)
            weeks[week_key].append(run)
    return dict(weeks)
