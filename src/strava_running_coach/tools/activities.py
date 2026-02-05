"""MCP tools for Strava activity queries."""

from datetime import datetime, timedelta
from typing import Any

from strava_running_coach.utils.dates import parse_date


def register_activity_tools(mcp, strava_client):
    """Register activity-related MCP tools."""

    @mcp.tool()
    def get_activities(limit: int = 10) -> dict[str, Any]:
        """
        Get the authenticated athlete's recent activities.

        Args:
            limit: Maximum number of activities to return (default: 10)

        Returns:
            Dictionary containing activities data
        """
        if strava_client is None:
            return {
                "error": "Strava client not initialized. Please provide refresh token, client ID, and client secret."
            }

        try:
            activities = strava_client.get_activities(limit=limit)
            return {"data": activities}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_activities_by_date_range(
        start_date: str, end_date: str, limit: int = 30
    ) -> dict[str, Any]:
        """
        Get activities within a specific date range.

        Args:
            start_date: Start date in ISO format (YYYY-MM-DD)
            end_date: End date in ISO format (YYYY-MM-DD)
            limit: Maximum number of activities to return (default: 30)

        Returns:
            Dictionary containing activities data
        """
        if strava_client is None:
            return {
                "error": "Strava client not initialized. Please provide refresh token, client ID, and client secret."
            }

        try:
            start = parse_date(start_date)
            end = parse_date(end_date)

            # Convert dates to timestamps
            after = int(datetime.combine(start, datetime.min.time()).timestamp())
            before = int(datetime.combine(end, datetime.max.time()).timestamp())

            activities = strava_client.get_activities(limit=limit, before=before, after=after)
            return {"data": activities}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_activity_by_id(activity_id: int) -> dict[str, Any]:
        """
        Get detailed information about a specific activity.

        Args:
            activity_id: ID of the activity to retrieve

        Returns:
            Dictionary containing activity details
        """
        if strava_client is None:
            return {
                "error": "Strava client not initialized. Please provide refresh token, client ID, and client secret."
            }

        try:
            activity = strava_client.get_activity(activity_id)
            return {"data": activity}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_recent_activities(days: int = 7, limit: int = 10) -> dict[str, Any]:
        """
        Get activities from the past X days.

        Args:
            days: Number of days to look back (default: 7)
            limit: Maximum number of activities to return (default: 10)

        Returns:
            Dictionary containing activities data
        """
        if strava_client is None:
            return {
                "error": "Strava client not initialized. Please provide refresh token, client ID, and client secret."
            }

        try:
            # Calculate timestamp for X days ago
            now = datetime.now()
            days_ago = now - timedelta(days=days)
            after = int(days_ago.timestamp())

            activities = strava_client.get_activities(limit=limit, after=after)
            return {"data": activities}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_activity_streams(
        activity_id: int, stream_types: str = "heartrate,pace"
    ) -> dict[str, Any]:
        """
        Get stream data for a specific activity (e.g., heartrate, pace, altitude).

        Args:
            activity_id: ID of the activity to retrieve streams for
            stream_types: Comma-separated list of stream types to retrieve.
                         Available types: heartrate, pace, altitude, cadence, distance,
                         moving, temperature, time, watts (default: "heartrate,pace")

        Returns:
            Dictionary containing stream data indexed by stream type
        """
        if strava_client is None:
            return {
                "error": "Strava client not initialized. Please provide refresh token, client ID, and client secret."
            }

        try:
            keys = [key.strip() for key in stream_types.split(",")]
            streams = strava_client.get_activity_streams(activity_id, keys)
            return {"data": streams}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_activity_description(activity_id: int) -> dict[str, Any]:
        """
        Get an activity's description to check for existing coaching feedback.

        Args:
            activity_id: ID of the activity

        Returns:
            Dictionary with activity id, name, and description
        """
        if strava_client is None:
            return {"error": "Strava client not initialized."}

        try:
            activity = strava_client.get_activity_raw(activity_id)
            return {
                "id": activity.get("id"),
                "name": activity.get("name"),
                "description": activity.get("description"),
                "has_coaching_feedback": "-------\n(" in (activity.get("description") or ""),
            }
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def add_coaching_feedback(
        activity_id: int, feedback: str, coach_name: str = "Coach David"
    ) -> dict[str, Any]:
        """
        Add coaching feedback to a Strava activity description.

        Appends feedback from the coach to the activity's description,
        preserving any existing description text.

        Args:
            activity_id: ID of the activity to add feedback to
            feedback: The coaching feedback text to append
            coach_name: Name of the coach to display (default: "Coach David")

        Returns:
            Dictionary with success status or error message
        """
        if strava_client is None:
            return {
                "error": "Strava client not initialized. Please provide refresh token, client ID, and client secret."
            }

        if not feedback or not feedback.strip():
            return {"error": "Feedback cannot be empty"}

        try:
            # Get current activity to preserve existing description
            activity = strava_client.get_activity_raw(activity_id)
            existing_description = activity.get("description") or ""

            # Format the coaching feedback
            coaching_comment = f"\n\n-------\n({coach_name} 🤖) {feedback.strip()}"

            # Append to existing description
            new_description = existing_description + coaching_comment

            # Update the activity
            updated = strava_client.update_activity(
                activity_id, description=new_description
            )

            return {
                "success": True,
                "activity_id": activity_id,
                "activity_name": updated.get("name"),
                "message": "Coaching feedback added successfully",
            }
        except Exception as e:
            error_msg = str(e)
            # Provide helpful error messages for common cases
            if "403" in error_msg:
                return {
                    "error": "Permission denied. The Strava API requires 'activity:write' scope. "
                    "Please re-authorize with Strava including the activity:write scope in your OAuth flow."
                }
            if "404" in error_msg:
                return {"error": f"Activity {activity_id} not found"}
            return {"error": error_msg}
