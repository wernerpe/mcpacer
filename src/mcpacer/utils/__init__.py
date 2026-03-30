"""Utility functions for the Strava Running Coach."""

from mcpacer.utils.formatting import format_duration, format_pace
from mcpacer.utils.dates import (
    date_to_timestamp,
    get_week_date_range,
    get_week_key,
    group_runs_by_week,
    parse_date,
    timestamp_to_date,
)

__all__ = [
    "format_pace",
    "format_duration",
    "timestamp_to_date",
    "date_to_timestamp",
    "parse_date",
    "get_week_key",
    "get_week_date_range",
    "group_runs_by_week",
]
