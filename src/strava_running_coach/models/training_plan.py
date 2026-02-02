"""Pydantic models for training plans."""

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class WorkoutType(str, Enum):
    """Types of workouts in a training plan."""

    EASY = "easy"
    WORKOUT = "workout"
    LONG_RUN = "long_run"
    TUNEUP_RACE = "tuneup_race"
    GYM = "gym"
    CROSS_TRAINING = "cross_training"
    REST = "rest"


class GoalRace(BaseModel):
    """Goal race information."""

    date: date
    race_type: str  # marathon, half_marathon, 10k, 5k
    distance_km: float
    goal_time: str  # HH:MM:SS format
    goal_pace_min_per_km: str  # M:SS format
    race_name: str


class PlannedRun(BaseModel):
    """A planned run or workout in the training plan."""

    day_of_week: str
    date: date
    type: WorkoutType
    description: Optional[str] = None

    # For running workouts
    distance_km: Optional[float] = None
    target_pace_min_per_km: Optional[str] = None
    structure: Optional[str] = None  # For interval workouts

    # For non-running activities
    duration_minutes: Optional[int] = None

    # For tuneup races
    race_name: Optional[str] = None


class TrainingWeek(BaseModel):
    """A week in the training plan."""

    week_number: int
    week_start_date: date
    total_planned_distance_km: Optional[float] = None
    weekly_focus: Optional[str] = None
    runs: list[PlannedRun] = Field(default_factory=list)


class TrainingPlan(BaseModel):
    """Complete training plan model."""

    id: Optional[str] = None
    plan_name: str
    goal_race: GoalRace
    created_date: Optional[date] = None
    plan_start_date: date
    plan_end_date: date
    notes: Optional[str] = None
    weeks: list[TrainingWeek] = Field(default_factory=list)
    is_active: bool = True

    # Metadata
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
