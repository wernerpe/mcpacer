"""Smoke tests for FastAPI endpoints — no LLM, no Strava API calls.

Tests the auth and API routers in isolation (no PTY, no real Strava OAuth).
"""

from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from mcpacer.web.auth import router as auth_router

# Standalone test app with just the auth router — no PTY, no lifespan.
test_app = FastAPI()
test_app.include_router(auth_router)
client = TestClient(test_app)


class TestHealthAndRoutes:
    """Verify the auth router mounts and responds."""

    def test_auth_status_no_env(self, tmp_path):
        """Auth status returns disconnected when no .env exists."""
        import mcpacer.web.auth as auth_mod
        orig = auth_mod.ENV_FILE
        try:
            auth_mod.ENV_FILE = tmp_path / ".env"
            resp = client.get("/auth/status")
            assert resp.status_code == 200
            data = resp.json()
            assert data["connected"] is False
            assert data["has_credentials"] is False
            assert data["has_tokens"] is False
        finally:
            auth_mod.ENV_FILE = orig

    def test_auth_status_with_credentials_only(self, tmp_path):
        """Auth status shows has_credentials but not connected without tokens."""
        env_file = tmp_path / ".env"
        env_file.write_text("STRAVA_CLIENT_ID=12345\nSTRAVA_CLIENT_SECRET=secret\n")

        import mcpacer.web.auth as auth_mod
        orig = auth_mod.ENV_FILE
        try:
            auth_mod.ENV_FILE = env_file
            resp = client.get("/auth/status")
            assert resp.status_code == 200
            data = resp.json()
            assert data["has_credentials"] is True
            assert data["has_tokens"] is False
            assert data["connected"] is False
        finally:
            auth_mod.ENV_FILE = orig

    def test_auth_status_fully_connected(self, tmp_path):
        """Auth status shows connected when all tokens are present."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            "STRAVA_CLIENT_ID=12345\n"
            "STRAVA_CLIENT_SECRET=secret\n"
            "STRAVA_ACCESS_TOKEN=abc\n"
            "STRAVA_REFRESH_TOKEN=def\n"
        )

        import mcpacer.web.auth as auth_mod
        orig = auth_mod.ENV_FILE
        try:
            auth_mod.ENV_FILE = env_file
            # Patch the httpx call that fetches athlete name
            with patch("mcpacer.web.auth.httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
                mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
                mock_client.return_value.get = AsyncMock(
                    return_value=type("R", (), {"status_code": 200, "json": lambda self: {"firstname": "Test", "lastname": "User"}})()
                )
                resp = client.get("/auth/status")
            assert resp.status_code == 200
            data = resp.json()
            assert data["connected"] is True
            assert data["athlete_name"] == "Test User"
        finally:
            auth_mod.ENV_FILE = orig


class TestCredentialsEndpoint:
    """Test POST /auth/credentials — saves creds, returns OAuth URL."""

    def test_save_credentials(self, tmp_path):
        env_file = tmp_path / ".env"

        import mcpacer.web.auth as auth_mod
        orig = auth_mod.ENV_FILE
        try:
            auth_mod.ENV_FILE = env_file
            resp = client.post(
                "/auth/credentials",
                json={"client_id": "99999", "client_secret": "supersecret"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "oauth_url" in data
            assert "99999" in data["oauth_url"]
            assert "localhost" in data["oauth_url"]

            # Verify .env was written
            contents = env_file.read_text()
            assert "STRAVA_CLIENT_ID=99999" in contents
            assert "STRAVA_CLIENT_SECRET=supersecret" in contents
        finally:
            auth_mod.ENV_FILE = orig

    def test_save_credentials_preserves_existing(self, tmp_path):
        """Saving credentials doesn't blow away existing env vars."""
        env_file = tmp_path / ".env"
        env_file.write_text("OTHER_VAR=keep_me\n")

        import mcpacer.web.auth as auth_mod
        orig = auth_mod.ENV_FILE
        try:
            auth_mod.ENV_FILE = env_file
            client.post(
                "/auth/credentials",
                json={"client_id": "123", "client_secret": "abc"},
            )
            contents = env_file.read_text()
            assert "OTHER_VAR=keep_me" in contents
            assert "STRAVA_CLIENT_ID=123" in contents
        finally:
            auth_mod.ENV_FILE = orig


class TestCallbackEndpoint:
    """Test GET /auth/callback — the OAuth return leg."""

    def test_callback_no_code(self):
        """Missing code returns 400."""
        resp = client.get("/auth/callback")
        assert resp.status_code == 400

    def test_callback_with_error(self):
        """Strava error param returns 400."""
        resp = client.get("/auth/callback?error=access_denied")
        assert resp.status_code == 400
        assert "Authorization failed" in resp.text

    def test_callback_missing_credentials(self, tmp_path):
        """Code present but no saved credentials returns 400."""
        import mcpacer.web.auth as auth_mod
        orig = auth_mod.ENV_FILE
        try:
            auth_mod.ENV_FILE = tmp_path / ".env"
            resp = client.get("/auth/callback?code=fake_code")
            assert resp.status_code == 400
            assert "Missing credentials" in resp.text
        finally:
            auth_mod.ENV_FILE = orig

    def test_callback_token_exchange_failure(self, tmp_path):
        """Token exchange fails gracefully when Strava returns error."""
        env_file = tmp_path / ".env"
        env_file.write_text("STRAVA_CLIENT_ID=123\nSTRAVA_CLIENT_SECRET=secret\n")

        import mcpacer.web.auth as auth_mod
        orig = auth_mod.ENV_FILE
        try:
            auth_mod.ENV_FILE = env_file
            # Mock httpx to simulate a Strava error
            with patch("mcpacer.web.auth.httpx.AsyncClient") as mock_client:
                mock_instance = mock_client.return_value
                mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
                mock_instance.__aexit__ = AsyncMock(return_value=False)
                mock_instance.post = AsyncMock(side_effect=Exception("Connection refused"))

                resp = client.get("/auth/callback?code=fake_code")
            assert resp.status_code == 500
            assert "Token exchange failed" in resp.text
        finally:
            auth_mod.ENV_FILE = orig

    def test_callback_success(self, tmp_path):
        """Successful token exchange saves tokens and returns success page."""
        env_file = tmp_path / ".env"
        env_file.write_text("STRAVA_CLIENT_ID=123\nSTRAVA_CLIENT_SECRET=secret\n")

        import mcpacer.web.auth as auth_mod
        orig = auth_mod.ENV_FILE
        try:
            auth_mod.ENV_FILE = env_file
            mock_token_response = type("R", (), {
                "status_code": 200,
                "json": lambda self: {
                    "access_token": "new_access",
                    "refresh_token": "new_refresh",
                    "expires_at": 9999999999,
                    "athlete": {"firstname": "Jane", "lastname": "Runner"},
                },
                "raise_for_status": lambda self: None,
            })()

            with patch("mcpacer.web.auth.httpx.AsyncClient") as mock_client:
                mock_instance = mock_client.return_value
                mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
                mock_instance.__aexit__ = AsyncMock(return_value=False)
                mock_instance.post = AsyncMock(return_value=mock_token_response)

                resp = client.get("/auth/callback?code=real_code")

            assert resp.status_code == 200
            assert "Connected to Strava" in resp.text
            assert "Jane Runner" in resp.text

            # Verify tokens saved
            contents = env_file.read_text()
            assert "STRAVA_ACCESS_TOKEN=new_access" in contents
            assert "STRAVA_REFRESH_TOKEN=new_refresh" in contents
        finally:
            auth_mod.ENV_FILE = orig
