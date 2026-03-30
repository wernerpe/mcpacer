"""CLI tools for the Strava Running Coach."""

from mcpacer.cli.analyze_plan import main as analyze_plan_main
from mcpacer.cli.generate_calendar import main as generate_calendar_main
from mcpacer.cli.update_data import main as update_data_main

__all__ = [
    "analyze_plan_main",
    "generate_calendar_main",
    "update_data_main",
]
