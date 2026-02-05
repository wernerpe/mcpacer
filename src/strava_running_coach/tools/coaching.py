"""MCP tools for coaching memory and context."""

import json
from typing import Any

from strava_running_coach.storage.coaching import CoachingStorage
from strava_running_coach.storage.training_plans import TrainingPlanStorage


def register_coaching_tools(mcp):
    """Register coaching MCP tools."""

    coaching_storage = CoachingStorage()
    plan_storage = TrainingPlanStorage()

    @mcp.tool()
    def get_coaching_context(
        coach_name: str = "david", athlete_id: str = "default"
    ) -> dict[str, Any]:
        """
        Get the coaching context for starting a coaching conversation.

        This should be called at the start of coaching conversations to load:
        - The coaching persona (how Claude should behave as a coach)
        - The athlete's profile (preferences, goals, injury history)
        - Recent session notes
        - Active training plan summary

        Claude should adopt the persona defined in the coaching_persona.md file.

        Args:
            coach_name: Name of the coach persona to use (e.g., "david", "roland")
            athlete_id: Athlete identifier (default for single-user mode)

        Returns:
            Dictionary containing coaching persona, athlete profile, recent notes,
            and active plan summary
        """
        try:
            # Load coaching persona
            persona = coaching_storage.get_persona(coach_name)

            # Load athlete profile
            profile = coaching_storage.get_athlete_profile(athlete_id)

            # Load recent session notes (last 10)
            all_notes = coaching_storage.get_session_notes(athlete_id)
            recent_notes = all_notes[:10]

            # Load recent plan adjustments
            adjustments = coaching_storage.get_plan_adjustments(athlete_id)[:5]

            # Get active training plan summary
            plans = plan_storage.list_plans()
            active_plans = [p for p in plans if p.get("is_active", True)]
            active_plan_summary = None
            if active_plans:
                active_plan = active_plans[0]  # Get the first active plan
                active_plan_summary = {
                    "plan_id": active_plan.get("id"),
                    "plan_name": active_plan.get("plan_name"),
                    "race_name": active_plan.get("race_name"),
                    "race_date": active_plan.get("race_date"),
                }

            return {
                "data": {
                    "coaching_persona": persona,
                    "athlete_profile": profile,
                    "recent_notes": recent_notes,
                    "recent_adjustments": adjustments,
                    "active_plan": active_plan_summary,
                }
            }
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def save_coaching_note(
        note_type: str, content_json: str, athlete_id: str = "default"
    ) -> dict[str, Any]:
        """
        Save a coaching note to persist insights across conversations.

        Types of notes:
        - "session_summary": Summary of a coaching conversation
        - "insight": An observation about the athlete's training
        - "adjustment": Record of a plan adjustment made

        Args:
            note_type: Type of note (session_summary, insight, adjustment)
            content_json: JSON string with note content (summary, key_points, etc.)
            athlete_id: Athlete identifier

        Returns:
            Dictionary with the saved note
        """
        valid_types = ["session_summary", "insight", "adjustment"]
        if note_type not in valid_types:
            return {"error": f"Invalid note_type. Must be one of: {valid_types}"}

        try:
            content = json.loads(content_json)
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON: {e}"}

        try:
            note = coaching_storage.add_session_note(note_type, content, athlete_id)
            return {"data": {"saved": True, "note": note}}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def update_athlete_profile(
        updates_json: str, athlete_id: str = "default"
    ) -> dict[str, Any]:
        """
        Update the athlete's profile with new information.

        The profile can include:
        - name: Athlete's name
        - training_preferences: Dict of preferences (preferred days, paces, etc.)
        - goals: List of goal objects
        - injury_history: List of injury records
        - notes: Free-form notes

        Args:
            updates_json: JSON string with fields to update
            athlete_id: Athlete identifier

        Returns:
            Dictionary with the updated profile
        """
        try:
            updates = json.loads(updates_json)
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON: {e}"}

        try:
            profile = coaching_storage.update_athlete_profile(updates, athlete_id)
            return {"data": {"updated": True, "profile": profile}}
        except Exception as e:
            return {"error": str(e)}
