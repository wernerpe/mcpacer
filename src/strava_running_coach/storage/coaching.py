"""Coaching data storage for persisting coaching memory."""

from datetime import datetime
from pathlib import Path
from typing import Any

from strava_running_coach.storage.base import BaseStorage


class CoachingStorage(BaseStorage):
    """Storage for coaching data including persona, athlete profile, and session notes."""

    MAX_SESSION_NOTES = 50  # Keep the last N session notes
    DEFAULT_COACH = "david"

    def __init__(self) -> None:
        """Initialize coaching storage in the coaching_data directory."""
        super().__init__("coaching_data")

    def get_guidelines_path(self) -> Path:
        """Get the path to the shared coaching guidelines file."""
        return self.data_dir / "coaching_guidelines.md"

    def get_guidelines(self) -> str | None:
        """
        Get the shared coaching guidelines markdown content.

        Returns:
            The guidelines markdown content or None if not found
        """
        return self._load_text(self.get_guidelines_path())

    def get_persona_path(self, coach_name: str | None = None) -> Path:
        """
        Get the path to a coach's persona file.

        Args:
            coach_name: Name of the coach (e.g., "david", "roland").
                       If None, uses the default coach.

        Returns:
            Path to the persona file in coaching_data/personas/
        """
        if coach_name is None:
            coach_name = self.DEFAULT_COACH
        return self.data_dir / "personas" / f"{coach_name}.md"

    def get_persona(self, coach_name: str | None = None) -> str | None:
        """
        Get the combined coaching persona and guidelines content.

        Loads the coach-specific persona and combines it with the shared
        coaching guidelines.

        Args:
            coach_name: Name of the coach (e.g., "david", "roland").
                       If None, uses the default coach.

        Returns:
            The combined persona + guidelines markdown content, or None if not found
        """
        if coach_name is None:
            coach_name = self.DEFAULT_COACH

        persona_content = self._load_text(self.get_persona_path(coach_name))
        guidelines_content = self.get_guidelines()

        if persona_content is None:
            return None

        # Combine persona and guidelines
        combined = f"{persona_content}\n\n# Coaching Guidelines\n\n"
        if guidelines_content:
            # Strip the "# Coaching Guidelines" header from guidelines since we add it
            lines = guidelines_content.split("\n")
            if lines and lines[0].strip() == "# Coaching Guidelines":
                guidelines_content = "\n".join(lines[1:]).lstrip()
            combined += guidelines_content

        return combined

    def list_personas(self) -> list[str]:
        """
        List available coach personas.

        Returns:
            List of coach names (without .md extension)
        """
        personas_dir = self.data_dir / "personas"
        if not personas_dir.exists():
            return []
        return [p.stem for p in personas_dir.glob("*.md")]

    def save_persona(self, content: str, coach_name: str | None = None) -> None:
        """
        Save a coaching persona markdown content.

        Args:
            content: The markdown content defining the coaching persona
            coach_name: Name of the coach. If None, uses the default coach.
        """
        if coach_name is None:
            coach_name = self.DEFAULT_COACH
        persona_path = self.get_persona_path(coach_name)
        persona_path.parent.mkdir(parents=True, exist_ok=True)
        self._save_text(persona_path, content)

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
