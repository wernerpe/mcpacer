"""Strava Running Coach MCP Server package."""

from strava_running_coach.server import main
from strava_running_coach.strava_client import StravaClient

__all__ = ["main", "StravaClient"]
