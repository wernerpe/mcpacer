"""Strava API client for interacting with the Strava API."""

import time
from typing import Any, Optional

import httpx


class StravaClient:
    """Client for interacting with the Strava API."""

    BASE_URL = "https://www.strava.com/api/v3"

    def __init__(self, refresh_token: str, client_id: str, client_secret: str):
        """
        Initialize the Strava API client.

        Args:
            refresh_token: Refresh token for Strava API
            client_id: Client ID for Strava API
            client_secret: Client secret for Strava API
        """
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token: Optional[str] = None
        self.expires_at = 0
        self.client = httpx.Client(timeout=30.0)

    def _ensure_valid_token(self) -> None:
        """Ensure we have a valid access token, refreshing if necessary."""
        current_time = int(time.time())

        # If token is missing or expired, refresh it
        if not self.access_token or current_time >= self.expires_at:
            self._refresh_token()

    def _refresh_token(self) -> None:
        """Refresh the access token using the refresh token."""
        refresh_url = "https://www.strava.com/oauth/token"
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
        }

        response = self.client.post(refresh_url, data=payload)
        if response.status_code != 200:
            error_msg = f"Error {response.status_code}: {response.text}"
            raise Exception(error_msg)

        token_data = response.json()
        self.access_token = token_data["access_token"]
        self.expires_at = token_data["expires_at"]
        print("Token refreshed successfully")

    def _make_request(self, endpoint: str, params: Optional[dict] = None) -> Any:
        """Make an authenticated request to the Strava API."""
        self._ensure_valid_token()

        url = f"{self.BASE_URL}/{endpoint}"
        headers = {"Authorization": f"Bearer {self.access_token}"}

        response = self.client.get(url, headers=headers, params=params)
        if response.status_code != 200:
            error_msg = f"Error {response.status_code}: {response.text}"
            raise Exception(error_msg)

        return response.json()

    def get_activities(
        self, limit: int = 10, before: Optional[int] = None, after: Optional[int] = None
    ) -> list[dict[str, Any]]:
        """
        Get the authenticated athlete's activities.

        Args:
            limit: Maximum number of activities to return
            before: Unix timestamp to filter activities before this time
            after: Unix timestamp to filter activities after this time

        Returns:
            List of activities
        """
        params: dict[str, Any] = {"per_page": limit}

        if before:
            params["before"] = before

        if after:
            params["after"] = after

        activities = self._make_request("athlete/activities", params)
        return self._filter_activities(activities)

    def get_activity(self, activity_id: int) -> dict[str, Any]:
        """
        Get detailed information about a specific activity.

        Args:
            activity_id: ID of the activity to retrieve

        Returns:
            Activity details
        """
        activity = self._make_request(f"activities/{activity_id}")
        return self._filter_activity(activity)

    def get_activity_streams(self, activity_id: int, keys: list[str]) -> list[dict[str, Any]]:
        """
        Get stream data for a specific activity.

        Args:
            activity_id: ID of the activity to retrieve streams for
            keys: List of stream types to retrieve (e.g., ['heartrate', 'pace'])

        Returns:
            List of stream objects containing time-series data
        """
        keys_param = ",".join(keys)
        params = {"keys": keys_param, "key_by_type": "true"}
        streams = self._make_request(f"activities/{activity_id}/streams", params)
        return streams

    def get_activity_laps(self, activity_id: int) -> list[dict[str, Any]]:
        """
        Get laps data for a specific activity.

        Args:
            activity_id: ID of the activity to retrieve laps for

        Returns:
            List of lap objects containing lap details
        """
        laps = self._make_request(f"activities/{activity_id}/laps")
        return laps

    def _filter_activity(self, activity: dict[str, Any]) -> dict[str, Any]:
        """Filter activity to only include specific keys and rename with units."""
        # Define field mappings with units
        field_mappings = {
            "id": "id",  # Activity ID for fetching streams
            "calories": "calories",
            "distance": "distance_metres",
            "elapsed_time": "elapsed_time_seconds",
            "elev_high": "elev_high_metres",
            "elev_low": "elev_low_metres",
            "end_latlng": "end_latlng",
            "average_speed": "average_speed_mps",  # metres per second
            "max_speed": "max_speed_mps",  # metres per second
            "moving_time": "moving_time_seconds",
            "sport_type": "sport_type",
            "start_date": "start_date",
            "start_latlng": "start_latlng",
            "total_elevation_gain": "total_elevation_gain_metres",
            "name": "name",  # Keep name for display purposes
        }

        # Create a new dictionary with renamed fields
        filtered_activity: dict[str, Any] = {}
        for old_key, new_key in field_mappings.items():
            if old_key in activity:
                filtered_activity[new_key] = activity[old_key]

        return filtered_activity

    def _filter_activities(self, activities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Filter a list of activities to only include specific keys with units."""
        return [self._filter_activity(activity) for activity in activities]

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()
