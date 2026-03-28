"""MCP tools for coaching personas."""

from typing import Any

from strava_running_coach.storage.coaching import CoachingStorage


def register_coaching_tools(mcp):
    """Register coaching MCP tools."""

    coaching_storage = CoachingStorage()

    @mcp.tool()
    def get_coaching_personas() -> dict[str, Any]:
        """
        Get the list of available coaching personas.

        Returns:
            Dictionary containing a list of available coach names.
        """
        try:
            personas = coaching_storage.list_personas()
            return {"data": {"personas": personas}}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_coaching_persona(coach_name: str) -> dict[str, Any]:
        """
        Load a coaching persona's full definition and guidelines.

        Returns the persona's personality, tone, and communication style
        combined with shared coaching guidelines. This content should be
        adopted fully for the duration of the session.

        Args:
            coach_name: Name of the coach persona to load (e.g. "david", "coach").

        Returns:
            The full persona text as markdown.
        """
        try:
            content = coaching_storage.get_persona(coach_name)
            if content is None:
                return {"error": f"Persona '{coach_name}' not found."}
            return {"data": {"persona": coach_name, "content": content}}
        except Exception as e:
            return {"error": str(e)}
