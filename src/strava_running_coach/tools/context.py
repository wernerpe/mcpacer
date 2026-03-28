"""MCP tools for run context — the training snapshot loaded at session start."""

from datetime import datetime, timedelta
from typing import Any

from strava_running_coach.context import render_run_context
from strava_running_coach.digestion import needs_digest
from strava_running_coach.storage.runs import RunStorage


# Sync window — how far back to look for new activities
SYNC_WEEKS = 12


def _sync_new_runs(strava_client, run_storage: RunStorage) -> int:
    """Fetch recent runs from Strava and save new ones locally.

    For each new run, fetches the activity detail endpoint which returns
    both description and laps in a single API call. Also backfills
    description/laps for existing runs that are missing them.

    Streams are NOT fetched (expensive, rarely needed — use get_activity_streams).

    API budget: 1 list call + 1 detail call per new/incomplete run.

    Returns:
        Number of new runs synced.
    """
    existing_ids = run_storage.get_existing_run_ids()

    after_date = datetime.now() - timedelta(weeks=SYNC_WEEKS)
    after_timestamp = int(after_date.timestamp())

    all_activities = strava_client.get_activities(limit=200, after=after_timestamp)
    runs = [a for a in all_activities if "run" in a.get("sport_type", "").lower()]

    new_count = 0

    for run in runs:
        activity_id = run.get("id")
        if not activity_id:
            continue

        if activity_id not in existing_ids:
            # New run — single detail call gets description + laps
            try:
                raw = strava_client.get_activity_raw(activity_id)
                run["description"] = raw.get("description")
                run["laps"] = raw.get("laps", [])
            except Exception:
                run["laps"] = []

            run_storage.save_run(run, activity_id)
            new_count += 1
        else:
            # Existing run — backfill description/laps if missing
            cached = run_storage.load_run(activity_id)
            if cached and (cached.get("description") is None or not cached.get("laps")):
                try:
                    raw = strava_client.get_activity_raw(activity_id)
                    cached["description"] = raw.get("description")
                    if not cached.get("laps"):
                        cached["laps"] = raw.get("laps", [])
                    run_storage.save_run(cached, activity_id)
                except Exception:
                    pass

    return new_count


def register_context_tools(mcp, strava_client):
    """Register run context MCP tools."""

    run_storage = RunStorage()

    @mcp.tool()
    def get_run_context() -> str:
        """
        Sync new activities from Strava and return a training overview.

        This is the primary tool for loading the athlete's training history
        at session start. It:
        1. Syncs any new activities from Strava
        2. Renders an age-tiered text snapshot (one-liners for older weeks,
           per-run detail for recent weeks)

        The output is purely actual run data — no plan awareness. The plan
        context is loaded separately via get_plan_context().

        Returns:
            Pre-formatted text block with the full training overview.
        """
        # Sync new runs if Strava client is available
        sync_msg = ""
        if strava_client is not None:
            try:
                new_count = _sync_new_runs(strava_client, run_storage)
                if new_count > 0:
                    sync_msg = f"[Synced {new_count} new run(s) from Strava]\n\n"
            except Exception as e:
                sync_msg = f"[Strava sync failed: {e}. Using cached data.]\n\n"

        # Load all cached runs
        runs = run_storage.load_all_runs()

        # Render the context
        context = render_run_context(runs)

        return sync_msg + context
