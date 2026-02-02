"""CLI tools for the Strava Running Coach."""

from strava_running_coach.cli.analyze_plan import main as analyze_plan_main
from strava_running_coach.cli.generate_report import main as generate_report_main
from strava_running_coach.cli.generate_calendar import main as generate_calendar_main
from strava_running_coach.cli.update_data import main as update_data_main

__all__ = [
    "analyze_plan_main",
    "generate_report_main",
    "generate_calendar_main",
    "update_data_main",
]
