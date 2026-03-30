"""Formatting utilities for pace and duration."""


def format_pace(speed_mps: float) -> str:
    """Convert speed in m/s to pace in min:sec/km format (e.g., '5:45')."""
    if speed_mps <= 0:
        return "N/A"
    pace_min_per_km = 1000 / (speed_mps * 60)
    mins = int(pace_min_per_km)
    secs = int((pace_min_per_km % 1) * 60)
    return f"{mins}:{secs:02d}"


def format_duration(seconds: float) -> str:
    """Convert seconds to HH:MM:SS or MM:SS format."""
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
