"""Strava Running Coach MCP Server package."""

from mcpacer.server import main
from mcpacer.strava_client import StravaClient

__all__ = ["main", "StravaClient"]
