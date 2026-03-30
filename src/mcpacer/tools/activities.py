"""MCP tools for Strava activity queries and run annotations."""

from datetime import datetime, timedelta
from typing import Any

from mcpacer.digestion import add_coach_note, needs_digest, build_digestion_prompt
from mcpacer.storage.runs import RunStorage
from mcpacer.utils.dates import parse_date
from mcpacer.utils.formatting import format_pace, format_duration


def register_activity_tools(mcp, strava_client):
    """Register activity-related MCP tools."""

    run_storage = RunStorage()

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
        activity_id: int, feedback: str, coach_name: str = "Coach"
    ) -> dict[str, Any]:
        """
        Add coaching feedback to a Strava activity description.

        Appends feedback from the coach to the activity's description,
        preserving any existing description text.

        Args:
            activity_id: ID of the activity to add feedback to
            feedback: The coaching feedback text to append
            coach_name: Name of the coach to display (default: "Coach")

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

    @mcp.tool()
    def add_run_note(activity_id: int, note: str) -> str:
        """
        Add a coach note to a cached run. Notes persist across sessions.

        Use this when the athlete shares context that changes interpretation
        of a run (treadmill paces, watch glitch, how they felt, etc.).
        Notes appear as 📝 lines in get_run_context() output.

        Args:
            activity_id: The Strava activity ID.
            note: The note text to append.

        Returns:
            Confirmation message.
        """
        run = run_storage.load_run(activity_id)
        if run is None:
            return f"Run {activity_id} not found in cache."

        add_coach_note(run, note)
        run_storage.save_run(run, activity_id)
        return f"Note added to run {activity_id}."

    @mcp.tool()
    def get_run_detail(activity_id: int) -> str:
        """
        Get a detailed view of a single run — full lap splits, HR, elevation,
        digest, and coach notes. Use for post-race analysis, anomalies, or
        when the athlete asks about specific splits.

        Args:
            activity_id: The Strava activity ID.

        Returns:
            Formatted run detail as text.
        """
        run = run_storage.load_run(activity_id)
        if run is None:
            return f"Run {activity_id} not found in cache."

        # Header
        name = run.get("name", "Unknown")
        date = run.get("start_date", "")[:10]
        dist_km = run.get("distance_metres", 0) / 1000
        moving_time = run.get("moving_time_seconds", 0)
        avg_speed = run.get("average_speed_mps", 0)
        pace = format_pace(avg_speed) if avg_speed > 0 else "N/A"
        elev = run.get("total_elevation_gain_metres", 0)
        duration = format_duration(moving_time)

        lines = [
            f"=== {name} — {date} ===",
            f"{dist_km:.1f}km | {duration} | {pace}/km | +{elev:.0f}m",
        ]

        # Digest
        digest = run.get("run_digest")
        if digest:
            lines.append(f"Digest: {digest}")

        # Coach notes
        notes = run.get("coach_notes", [])
        for note in notes:
            lines.append(f"📝 {note}")

        # Lap splits
        laps = run.get("laps", [])
        if laps:
            lines.append("")
            lines.append("Lap splits:")
            for i, lap in enumerate(laps, 1):
                lap_dist = lap.get("distance", 0) / 1000
                lap_speed = lap.get("average_speed", 0)
                lap_pace = format_pace(lap_speed) if lap_speed > 0 else "N/A"
                lap_hr = lap.get("average_heartrate")
                lap_max_hr = lap.get("max_heartrate")
                lap_elev = lap.get("total_elevation_gain", 0)
                lap_time = format_duration(lap.get("moving_time", 0))

                hr_str = ""
                if lap_hr:
                    hr_str = f" HR {lap_hr:.0f}"
                    if lap_max_hr:
                        hr_str += f"/{lap_max_hr:.0f}"

                lines.append(
                    f"  {i:2d}. {lap_dist:.2f}km  {lap_pace}/km  {lap_time}{hr_str}  +{lap_elev:.0f}m"
                )

        return "\n".join(lines)

    @mcp.tool()
    def get_pending_digests() -> dict[str, Any]:
        """
        Get runs that need LLM digestion, with pre-built prompts.

        Returns a list of items, each with activity_id, name, date, and the
        digestion prompt. The host should process each item — ideally by
        spawning parallel Haiku subagents — and save results via
        save_run_digest(activity_id, digest).

        Returns:
            Dict with "pending" list (each item has activity_id, name, date,
            prompt) or "message" if nothing is pending.
        """
        runs = run_storage.load_all_runs()
        pending = []
        for run in runs:
            if needs_digest(run):
                pending.append({
                    "activity_id": run.get("id", 0),
                    "name": run.get("name", "Unknown"),
                    "date": run.get("start_date", "")[:10],
                    "prompt": build_digestion_prompt(run),
                })

        if not pending:
            return {"message": "All qualifying runs already have digests."}

        return {"pending": pending}

    @mcp.tool()
    def save_run_digest(activity_id: int, digest: str) -> str:
        """
        Save a digest for a run (generated by LLM or host).

        Called after processing a digestion prompt from get_pending_digests().
        The digest should be a single compact line with segments separated
        by | (e.g. "WU 2km @5:00 | 10×1km @3:45 HR 165→185 | CD 2km | +110m").

        Args:
            activity_id: The Strava activity ID.
            digest: The digest string.

        Returns:
            Confirmation message.
        """
        run = run_storage.load_run(activity_id)
        if run is None:
            return f"Run {activity_id} not found in cache."

        run["run_digest"] = digest.strip()
        run_storage.save_run(run, activity_id)
        return f"Digest saved for run {activity_id}."
