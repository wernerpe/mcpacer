#!/usr/bin/env python3
"""
MCP server for Strava API integration.
This server exposes methods to query the Strava API for athlete activities.
"""

import os
from typing import Optional

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from mcpacer.strava_client import StravaClient
from mcpacer.tools import register_all_tools

load_dotenv()

# Create MCP server at module level
mcp = FastMCP("Strava API MCP Server")

# Strava client instance (initialized in main or at import time)
strava_client: Optional[StravaClient] = None

# Try to initialize from environment at import time
_refresh_token = os.environ.get("STRAVA_REFRESH_TOKEN")
_client_id = os.environ.get("STRAVA_CLIENT_ID")
_client_secret = os.environ.get("STRAVA_CLIENT_SECRET")

if _refresh_token and _client_id and _client_secret:
    strava_client = StravaClient(_refresh_token, _client_id, _client_secret)

# Register all MCP tools
register_all_tools(mcp, strava_client)


def main() -> None:
    """Main function to start the Strava MCP server."""
    print("Starting Strava MCP server!")

    # Initialize Strava client if not already done
    global strava_client
    if strava_client is None:
        refresh_token = os.environ.get("STRAVA_REFRESH_TOKEN")
        client_id = os.environ.get("STRAVA_CLIENT_ID")
        client_secret = os.environ.get("STRAVA_CLIENT_SECRET")

        if refresh_token and client_id and client_secret:
            strava_client = StravaClient(refresh_token, client_id, client_secret)
            # Re-register tools with the new client
            register_all_tools(mcp, strava_client)
        else:
            print(
                "Warning: Strava client not initialized. Please set STRAVA_REFRESH_TOKEN, "
                "STRAVA_CLIENT_ID, and STRAVA_CLIENT_SECRET environment variables."
            )

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
