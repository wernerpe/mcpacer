"""Pydantic models for coaching data."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class AthleteProfile(BaseModel):
    """Athlete profile for coaching context."""

    athlete_id: str = "default"  # Extensible for multi-athlete support
    name: Optional[str] = None
    training_preferences: dict[str, Any] = Field(default_factory=dict)
    goals: list[dict[str, Any]] = Field(default_factory=list)
    injury_history: list[dict[str, Any]] = Field(default_factory=list)
    notes: str = ""

    # Metadata
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class SessionNote(BaseModel):
    """A note from a coaching session."""

    timestamp: datetime
    athlete_id: str = "default"
    note_type: str  # session_summary, insight, adjustment
    summary: str
    key_points: list[str] = Field(default_factory=list)


class PlanAdjustment(BaseModel):
    """Record of a training plan adjustment."""

    timestamp: datetime
    athlete_id: str = "default"
    plan_id: str
    change_description: str
    reason: str
