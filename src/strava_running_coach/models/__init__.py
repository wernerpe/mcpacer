"""Pydantic models for the Strava Running Coach."""

from strava_running_coach.models.training_plan import (
    GoalRace,
    PlannedRun,
    TrainingPlan,
    TrainingWeek,
    WorkoutType,
)
from strava_running_coach.models.coaching import (
    AthleteProfile,
    PlanAdjustment,
    SessionNote,
)

__all__ = [
    # Training plan models
    "WorkoutType",
    "GoalRace",
    "PlannedRun",
    "TrainingWeek",
    "TrainingPlan",
    # Coaching models
    "AthleteProfile",
    "SessionNote",
    "PlanAdjustment",
]
