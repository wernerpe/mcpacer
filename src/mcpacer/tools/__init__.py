"""MCP tools for the Strava MCP Server."""

from mcpacer.tools.activities import register_activity_tools
from mcpacer.tools.coaching import register_coaching_tools
from mcpacer.tools.context import register_context_tools
from mcpacer.tools.memory import register_memory_tools
from mcpacer.tools.training_plans import register_training_plan_tools

__all__ = [
    "register_activity_tools",
    "register_training_plan_tools",
    "register_coaching_tools",
    "register_memory_tools",
    "register_context_tools",
]


def register_all_tools(mcp, strava_client):
    """Register all MCP tools with the server."""
    register_activity_tools(mcp, strava_client)
    register_training_plan_tools(mcp)
    register_coaching_tools(mcp)
    register_memory_tools(mcp)
    register_context_tools(mcp, strava_client)
