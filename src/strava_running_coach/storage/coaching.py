"""Coaching data storage for persisting coaching memory."""

from datetime import datetime
from pathlib import Path
from typing import Any

from strava_running_coach.storage.base import BaseStorage


class CoachingStorage(BaseStorage):
    """Storage for coaching data including persona, athlete profile, and session notes."""

    MAX_SESSION_NOTES = 50  # Keep the last N session notes

    def __init__(self) -> None:
        """Initialize coaching storage in the coaching_data directory."""
        super().__init__("coaching_data")

    def get_persona_path(self) -> Path:
        """Get the path to the coaching persona file."""
        return self.data_dir / "coaching_persona.md"

    def get_persona(self) -> str | None:
        """
        Get the coaching persona markdown content.

        Returns:
            The persona markdown content or None if not found
        """
        return self._load_text(self.get_persona_path())

    def save_persona(self, content: str) -> None:
        """
        Save the coaching persona markdown content.

        Args:
            content: The markdown content defining the coaching persona
        """
        self._save_text(self.get_persona_path(), content)

    def get_athlete_profile(self, athlete_id: str = "default") -> dict[str, Any] | None:
        """
        Get the athlete profile.

        Args:
            athlete_id: Athlete identifier (default for single-user mode)

        Returns:
            The athlete profile or None if not found
        """
        file_path = self.data_dir / f"athlete_profile_{athlete_id}.json"
        return self._load_json(file_path)  # type: ignore

    def save_athlete_profile(self, profile: dict[str, Any], athlete_id: str = "default") -> None:
        """
        Save or update the athlete profile.

        Args:
            profile: The athlete profile data
            athlete_id: Athlete identifier
        """
        # Ensure athlete_id is set
        profile["athlete_id"] = athlete_id
        if "updated_at" not in profile:
            profile["created_at"] = datetime.now().isoformat()
        profile["updated_at"] = datetime.now().isoformat()

        file_path = self.data_dir / f"athlete_profile_{athlete_id}.json"
        self._save_json(file_path, profile)

    def update_athlete_profile(
        self, updates: dict[str, Any], athlete_id: str = "default"
    ) -> dict[str, Any]:
        """
        Merge updates into the existing athlete profile.

        Args:
            updates: Fields to update
            athlete_id: Athlete identifier

        Returns:
            The updated profile
        """
        profile = self.get_athlete_profile(athlete_id) or {
            "athlete_id": athlete_id,
            "training_preferences": {},
            "goals": [],
            "injury_history": [],
            "notes": "",
        }

        # Merge updates
        for key, value in updates.items():
            if key in profile and isinstance(profile[key], dict) and isinstance(value, dict):
                profile[key].update(value)
            elif key in profile and isinstance(profile[key], list) and isinstance(value, list):
                # For lists, extend rather than replace
                profile[key].extend(value)
            else:
                profile[key] = value

        self.save_athlete_profile(profile, athlete_id)
        return profile

    def get_session_notes(self, athlete_id: str = "default") -> list[dict[str, Any]]:
        """
        Get session notes for an athlete.

        Args:
            athlete_id: Athlete identifier

        Returns:
            List of session notes, most recent first
        """
        file_path = self.data_dir / f"session_notes_{athlete_id}.json"
        notes = self._load_json(file_path)
        if notes is None or not isinstance(notes, list):
            return []
        return notes

    def add_session_note(
        self,
        note_type: str,
        content: dict[str, Any],
        athlete_id: str = "default",
    ) -> dict[str, Any]:
        """
        Add a session note.

        Args:
            note_type: Type of note (session_summary, insight, adjustment)
            content: Note content (summary, key_points, etc.)
            athlete_id: Athlete identifier

        Returns:
            The created note
        """
        notes = self.get_session_notes(athlete_id)

        note = {
            "timestamp": datetime.now().isoformat(),
            "athlete_id": athlete_id,
            "note_type": note_type,
            **content,
        }

        # Add new note at the beginning
        notes.insert(0, note)

        # Prune old notes
        if len(notes) > self.MAX_SESSION_NOTES:
            notes = notes[: self.MAX_SESSION_NOTES]

        file_path = self.data_dir / f"session_notes_{athlete_id}.json"
        self._save_json(file_path, notes)
        return note

    def get_plan_adjustments(self, athlete_id: str = "default") -> list[dict[str, Any]]:
        """
        Get plan adjustments for an athlete.

        Args:
            athlete_id: Athlete identifier

        Returns:
            List of plan adjustments, most recent first
        """
        file_path = self.data_dir / f"plan_adjustments_{athlete_id}.json"
        adjustments = self._load_json(file_path)
        if adjustments is None or not isinstance(adjustments, list):
            return []
        return adjustments

    def add_plan_adjustment(
        self,
        plan_id: str,
        change_description: str,
        reason: str,
        athlete_id: str = "default",
    ) -> dict[str, Any]:
        """
        Record a plan adjustment.

        Args:
            plan_id: ID of the plan that was adjusted
            change_description: What was changed
            reason: Why the change was made
            athlete_id: Athlete identifier

        Returns:
            The created adjustment record
        """
        adjustments = self.get_plan_adjustments(athlete_id)

        adjustment = {
            "timestamp": datetime.now().isoformat(),
            "athlete_id": athlete_id,
            "plan_id": plan_id,
            "change_description": change_description,
            "reason": reason,
        }

        adjustments.insert(0, adjustment)

        file_path = self.data_dir / f"plan_adjustments_{athlete_id}.json"
        self._save_json(file_path, adjustments)
        return adjustment
