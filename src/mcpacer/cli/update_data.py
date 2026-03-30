#!/usr/bin/env python3
"""
Update local run data from Strava.

This script fetches running activities from the last few weeks and stores them
locally in the run_data directory. It only adds new runs and preserves existing data.
"""

import argparse
import os
from datetime import datetime, timedelta
from typing import Any

from dotenv import load_dotenv

from mcpacer.strava_client import StravaClient
from mcpacer.storage.runs import RunStorage

# Configuration
LOOKBACK_WEEKS = 4


def fetch_run_details(client: StravaClient, activity_id: int) -> dict[str, Any]:
    """
    Fetch detailed information for a single run including streams and laps.

    Args:
        client: Initialized StravaClient
        activity_id: Strava activity ID

    Returns:
        Dictionary with run details, streams, and laps
    """
    run_details: dict[str, Any] = {}

    # Fetch streams (heartrate, pace, altitude, cadence)
    try:
        streams = client.get_activity_streams(
            activity_id, ["heartrate", "pace", "altitude", "cadence"]
        )
        run_details["streams"] = streams
    except Exception as e:
        print(f"    Warning: Could not fetch streams: {e}")
        run_details["streams"] = None

    # Fetch laps
    try:
        laps = client.get_activity_laps(activity_id)
        run_details["laps"] = laps
    except Exception as e:
        print(f"    Warning: Could not fetch laps: {e}")
        run_details["laps"] = []

    return run_details


def main() -> int:
    """Main function to update run data from Strava."""
    parser = argparse.ArgumentParser(
        description="Update local run data from Strava"
    )
    parser.add_argument(
        "--weeks",
        type=int,
        default=LOOKBACK_WEEKS,
        help=f"Number of weeks to look back (default: {LOOKBACK_WEEKS})",
    )
    parser.add_argument(
        "--env-file",
        help="Path to .env file with Strava credentials",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("STRAVA RUN DATA UPDATER")
    print("=" * 80)

    # Load environment variables
    if args.env_file:
        load_dotenv(dotenv_path=args.env_file, override=True)
    else:
        load_dotenv()

    # Initialize run storage
    run_storage = RunStorage()
    print(f"Run data directory: {run_storage.data_dir.absolute()}")

    # Load Strava credentials
    refresh_token = os.environ.get("STRAVA_REFRESH_TOKEN")
    client_id = os.environ.get("STRAVA_CLIENT_ID")
    client_secret = os.environ.get("STRAVA_CLIENT_SECRET")

    if not all([refresh_token, client_id, client_secret]):
        print("Error: Missing Strava credentials")
        print("Required environment variables:")
        print("  STRAVA_REFRESH_TOKEN")
        print("  STRAVA_CLIENT_ID")
        print("  STRAVA_CLIENT_SECRET")
        return 1

    # Initialize Strava client
    print("\nConnecting to Strava API...")
    client = StravaClient(refresh_token, client_id, client_secret)  # type: ignore

    # Get existing run IDs
    existing_ids = run_storage.get_existing_run_ids()
    print(f"\nFound {len(existing_ids)} existing runs in local storage")

    # Calculate date range
    after_date = datetime.now() - timedelta(weeks=args.weeks)
    after_timestamp = int(after_date.timestamp())

    print(f"Fetching runs from the last {args.weeks} weeks...")
    print(
        f"Date range: {after_date.strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}"
    )

    # Fetch activities
    try:
        all_activities = client.get_activities(limit=200, after=after_timestamp)
    except Exception as e:
        print(f"Error fetching activities: {e}")
        client.close()
        return 1

    # Filter for running activities only
    runs = [a for a in all_activities if "run" in a.get("sport_type", "").lower()]

    print(f"\nFound {len(runs)} total running activities from Strava")

    # Identify new runs
    new_runs = [r for r in runs if r.get("id") not in existing_ids]

    if not new_runs:
        print("\nNo new runs to add. Database is up to date!")
        client.close()
        return 0

    print(f"New runs to add: {len(new_runs)}")
    print("\n" + "-" * 80)
    print("Fetching detailed data for new runs...")
    print("-" * 80)

    # Fetch and save new runs
    for i, run in enumerate(new_runs, 1):
        activity_id = run.get("id")
        name = run.get("name", "Unnamed")
        date_str = run.get("start_date", "")[:10]
        distance_km = run.get("distance_metres", 0) / 1000

        print(f"\n[{i}/{len(new_runs)}] {name} ({date_str}) - {distance_km:.2f}km")

        if not activity_id:
            print("  Skipping: No activity ID")
            continue

        # Fetch additional details
        details = fetch_run_details(client, activity_id)

        # Combine basic run data with detailed information
        complete_run = {**run, **details}

        # Save to file
        run_storage.save_run(complete_run, activity_id)
        print(f"  Saved: run_{activity_id}.json")

    # Summary
    print("\n" + "=" * 80)
    print("UPDATE COMPLETE")
    print("=" * 80)
    print(f"Total runs in database: {len(existing_ids) + len(new_runs)}")
    print(f"New runs added: {len(new_runs)}")
    print(f"Storage location: {run_storage.data_dir.absolute()}")

    client.close()
    return 0


if __name__ == "__main__":
    exit(main())
