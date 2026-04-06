"""Tests for web API helpers and auth utilities — no LLM or API calls."""

import tempfile
from pathlib import Path

from mcpacer.web.api import _run_to_json, _speed_to_pace
from mcpacer.web.auth import _read_env, _write_env


class TestSpeedToPace:
    def test_normal_pace(self):
        # ~5:00/km
        assert _speed_to_pace(3.333) == "5:00"

    def test_zero(self):
        assert _speed_to_pace(0) == "0:00"

    def test_negative(self):
        assert _speed_to_pace(-1) == "0:00"


class TestRunToJson:
    def test_basic_run(self):
        run = {
            "id": 123,
            "name": "Morning Run",
            "start_date": "2026-03-16T08:00:00Z",
            "distance_metres": 10000,
            "moving_time_seconds": 3000,
            "average_speed_mps": 3.33,
            "total_elevation_gain_metres": 50,
            "laps": [{"average_heartrate": 150, "max_heartrate": 175}],
            "description": "Felt good",
        }
        result = _run_to_json(run)
        assert result["id"] == 123
        assert result["distance_km"] == 10.0
        assert result["elevation_gain"] == 50
        assert result["description"] == "Felt good"
        assert result["pace"] is not None

    def test_missing_fields(self):
        result = _run_to_json({})
        assert result["id"] is None
        assert result["distance_km"] == 0
        assert result["name"] == ""


class TestEnvReadWrite:
    def test_roundtrip(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("KEY1=value1\nKEY2=value2\n")
            tmp_path = Path(f.name)

        import mcpacer.web.auth as auth_mod
        original_env_file = auth_mod.ENV_FILE
        try:
            auth_mod.ENV_FILE = tmp_path
            env = _read_env()
            assert env == {"KEY1": "value1", "KEY2": "value2"}

            env["KEY3"] = "value3"
            _write_env(env)

            env2 = _read_env()
            assert env2["KEY3"] == "value3"
            assert len(env2) == 3
        finally:
            auth_mod.ENV_FILE = original_env_file
            tmp_path.unlink()

    def test_read_missing_file(self):
        import mcpacer.web.auth as auth_mod
        original_env_file = auth_mod.ENV_FILE
        try:
            auth_mod.ENV_FILE = Path("/tmp/nonexistent_env_file_test")
            assert _read_env() == {}
        finally:
            auth_mod.ENV_FILE = original_env_file

    def test_comments_and_blanks(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("# comment\n\nKEY=val\n")
            tmp_path = Path(f.name)

        import mcpacer.web.auth as auth_mod
        original_env_file = auth_mod.ENV_FILE
        try:
            auth_mod.ENV_FILE = tmp_path
            env = _read_env()
            assert env == {"KEY": "val"}
        finally:
            auth_mod.ENV_FILE = original_env_file
            tmp_path.unlink()
