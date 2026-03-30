"""OAuth endpoints for Strava authentication."""

import os
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

router = APIRouter(prefix="/auth")

# Project root .env location
PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = PROJECT_ROOT / ".env"

STRAVA_AUTH_URL = "https://www.strava.com/oauth/authorize"
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
STRAVA_ATHLETE_URL = "https://www.strava.com/api/v3/athlete"
SCOPES = "read,activity:read,activity:read_all,activity:write,profile:read_all"


class CredentialsPayload(BaseModel):
    client_id: str
    client_secret: str


def _read_env() -> dict[str, str]:
    """Read the .env file into a dict."""
    env_vars: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env_vars[key] = value
    return env_vars


def _write_env(env_vars: dict[str, str]) -> None:
    """Write a dict back to the .env file."""
    with open(ENV_FILE, "w") as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")


@router.get("/status")
async def auth_status() -> dict[str, Any]:
    """Check whether Strava credentials and tokens are configured."""
    env = _read_env()
    has_credentials = bool(env.get("STRAVA_CLIENT_ID") and env.get("STRAVA_CLIENT_SECRET"))
    has_tokens = bool(env.get("STRAVA_REFRESH_TOKEN") and env.get("STRAVA_ACCESS_TOKEN"))

    result: dict[str, Any] = {
        "has_credentials": has_credentials,
        "has_tokens": has_tokens,
        "connected": has_credentials and has_tokens,
    }

    # If connected, try to fetch athlete name
    if has_tokens:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    STRAVA_ATHLETE_URL,
                    headers={"Authorization": f"Bearer {env['STRAVA_ACCESS_TOKEN']}"},
                    timeout=5.0,
                )
                if resp.status_code == 200:
                    athlete = resp.json()
                    result["athlete_name"] = f"{athlete.get('firstname', '')} {athlete.get('lastname', '')}".strip()
        except Exception:
            pass  # Token might be expired, but refresh will handle it at runtime

    return result


@router.post("/credentials")
async def save_credentials(payload: CredentialsPayload) -> dict[str, Any]:
    """Save Strava client ID and secret to .env."""
    env = _read_env()
    env["STRAVA_CLIENT_ID"] = payload.client_id
    env["STRAVA_CLIENT_SECRET"] = payload.client_secret
    _write_env(env)

    # Return the OAuth URL for the frontend to redirect to
    redirect_uri = "http://localhost:8000/auth/callback"
    oauth_url = (
        f"{STRAVA_AUTH_URL}"
        f"?client_id={payload.client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope={SCOPES}"
    )

    return {"oauth_url": oauth_url}


@router.get("/callback")
async def oauth_callback(code: str = "", error: str = "") -> HTMLResponse:
    """Handle the OAuth callback from Strava."""
    if error or not code:
        return HTMLResponse(
            "<html><body style='background:#030712;color:#f87171;font-family:monospace;display:flex;align-items:center;justify-content:center;height:100vh'>"
            f"<div><h2>Authorization failed</h2><p>{error or 'No authorization code received.'}</p>"
            "<p>You can close this tab and try again.</p></div></body></html>",
            status_code=400,
        )

    env = _read_env()
    client_id = env.get("STRAVA_CLIENT_ID", "")
    client_secret = env.get("STRAVA_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        return HTMLResponse(
            "<html><body style='background:#030712;color:#f87171;font-family:monospace;display:flex;align-items:center;justify-content:center;height:100vh'>"
            "<div><h2>Missing credentials</h2><p>Client ID and secret not found. Please go back and enter them.</p></div></body></html>",
            status_code=400,
        )

    # Exchange code for tokens
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                STRAVA_TOKEN_URL,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                },
                timeout=10.0,
            )
            resp.raise_for_status()
            token_data = resp.json()
    except Exception as e:
        return HTMLResponse(
            "<html><body style='background:#030712;color:#f87171;font-family:monospace;display:flex;align-items:center;justify-content:center;height:100vh'>"
            f"<div><h2>Token exchange failed</h2><p>{e}</p>"
            "<p>You can close this tab and try again.</p></div></body></html>",
            status_code=500,
        )

    # Save tokens to .env
    env["STRAVA_ACCESS_TOKEN"] = token_data["access_token"]
    env["STRAVA_REFRESH_TOKEN"] = token_data["refresh_token"]
    env["STRAVA_EXPIRES_AT"] = str(token_data["expires_at"])
    _write_env(env)

    # Also update os.environ so the running app picks them up
    os.environ["STRAVA_CLIENT_ID"] = client_id
    os.environ["STRAVA_CLIENT_SECRET"] = client_secret
    os.environ["STRAVA_ACCESS_TOKEN"] = token_data["access_token"]
    os.environ["STRAVA_REFRESH_TOKEN"] = token_data["refresh_token"]
    os.environ["STRAVA_EXPIRES_AT"] = str(token_data["expires_at"])

    athlete_name = ""
    athlete = token_data.get("athlete", {})
    if athlete:
        athlete_name = f"{athlete.get('firstname', '')} {athlete.get('lastname', '')}".strip()

    # Return a page that auto-closes and notifies the opener
    return HTMLResponse(
        "<html><body style='background:#030712;color:#4ade80;font-family:monospace;display:flex;align-items:center;justify-content:center;height:100vh'>"
        f"<div style='text-align:center'><h2>Connected to Strava!</h2>"
        f"<p>Welcome, {athlete_name or 'athlete'}.</p>"
        "<p style='color:#94a3b8'>This tab will close automatically...</p></div>"
        "<script>setTimeout(() => { if (window.opener) window.opener.postMessage('strava-auth-success', '*'); window.close(); }, 1500);</script>"
        "</body></html>"
    )
