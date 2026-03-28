"""MCP tools for coach memory and session logs."""

from strava_running_coach.storage.memory import MEMORY_SECTIONS, MemoryStorage


def register_memory_tools(mcp):
    """Register memory MCP tools."""

    memory_storage = MemoryStorage()

    @mcp.tool()
    def read_coach_memory() -> str:
        """
        Read the full COACH_MEMORY.md — the coach's long-term knowledge about the athlete.

        Contains sections: Athlete, PRs, Goals, Active Flags, Training Context, Patterns & Insights.
        This is loaded at session start and can be re-read on demand.

        Returns:
            The full coach memory as markdown text.
        """
        return memory_storage.read_memory()

    @mcp.tool()
    def update_coach_memory(section: str, content: str) -> str:
        """
        Update a specific section of the coach's memory (COACH_MEMORY.md).

        Rewrites the section in-place. Call this immediately when significant
        new information emerges — don't wait until session end.

        Sections:
            athlete — name, location, weight
            prs — self-reported PRs with date assessed
            goals — target race, current phase
            active_flags — injuries, niggles, concerns
            training_context — weekly volume, training days, constraints
            patterns — observations about the athlete's training

        Args:
            section: Section key (athlete, prs, goals, active_flags, training_context, patterns)
            content: New content for the section (replaces everything under the ## header)

        Returns:
            Confirmation message.
        """
        return memory_storage.update_section(section, content)

    @mcp.tool()
    def get_session_logs(limit: int = 3) -> str:
        """
        Read recent daily session logs — summaries of previous coaching conversations.

        Each log records what was discussed, flags raised, decisions made, and
        plan adjustments from a past session. Provides conversation continuity.

        Args:
            limit: Number of recent logs to return (default 3, max 5).

        Returns:
            Concatenated session logs as text, most recent first.
        """
        limit = min(limit, 5)
        return memory_storage.get_session_logs(limit)

    @mcp.tool()
    def save_session_log(summary: str, coach_name: str = "Coach") -> str:
        """
        Save a session summary log for today.

        Called at the end of a coaching session to persist what was discussed.
        The summary should be 3-5 lines covering: what was discussed, flags
        raised, decisions made, and any plan adjustments.

        Args:
            summary: The session summary text (3-5 lines).
            coach_name: Name of the coach persona used in this session.

        Returns:
            Confirmation message.
        """
        return memory_storage.save_session_log(summary, coach_name)
