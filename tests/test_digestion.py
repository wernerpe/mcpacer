"""Tests for digestion utilities — no LLM or API calls."""

from datetime import datetime, timedelta

from mcpacer.digestion import (
    _extract_athlete_description,
    build_lap_table,
    needs_digest,
    parse_digest_tag,
    strip_digest_tag,
)


class TestNeedsDigest:
    def _make_run(self, days_ago: int = 1, has_digest: bool = False):
        dt = datetime.now() - timedelta(days=days_ago)
        run = {"start_date": dt.isoformat() + "Z"}
        if has_digest:
            run["run_digest"] = "Easy 10km @5:15/km [easy]"
        return run

    def test_recent_undigested(self):
        assert needs_digest(self._make_run(days_ago=2)) is True

    def test_recent_already_digested(self):
        assert needs_digest(self._make_run(days_ago=2, has_digest=True)) is False

    def test_old_run(self):
        assert needs_digest(self._make_run(days_ago=30)) is False

    def test_no_date(self):
        assert needs_digest({"name": "no date"}) is False


class TestBuildLapTable:
    def test_with_laps(self):
        run = {
            "laps": [
                {"distance": 1000, "average_speed": 3.33, "average_heartrate": 140, "total_elevation_gain": 5},
                {"distance": 1000, "average_speed": 4.44, "average_heartrate": 170, "total_elevation_gain": 3},
            ]
        }
        result = build_lap_table(run)
        assert "1:" in result
        assert "2:" in result
        assert "HR 140" in result

    def test_no_laps(self):
        assert build_lap_table({}) == "No lap data available."
        assert build_lap_table({"laps": []}) == "No lap data available."


class TestExtractAthleteDescription:
    def test_plain_description(self):
        assert _extract_athlete_description("Great run today") == "Great run today"

    def test_with_coaching_feedback(self):
        desc = "Felt strong\n\n-------\n(Coach) Good job!"
        assert _extract_athlete_description(desc) == "Felt strong"

    def test_none(self):
        assert _extract_athlete_description(None) == ""

    def test_empty(self):
        assert _extract_athlete_description("") == ""


class TestParseDigestTag:
    def test_valid_tag(self):
        assert parse_digest_tag("Easy 10km @5:15/km [easy]") == "easy"

    def test_workout_tag(self):
        assert parse_digest_tag("WU 2km | 10×1km @3:45 | CD 2km [workout]") == "workout"

    def test_long_workout_tag(self):
        assert parse_digest_tag("something [long-workout]") == "long-workout"

    def test_no_tag(self):
        assert parse_digest_tag("Easy 10km no tag") == "unknown"

    def test_invalid_tag(self):
        assert parse_digest_tag("something [bogus]") == "unknown"


class TestStripDigestTag:
    def test_removes_tag(self):
        assert strip_digest_tag("Easy 10km @5:15/km [easy]") == "Easy 10km @5:15/km"

    def test_no_tag(self):
        assert strip_digest_tag("Easy 10km no tag") == "Easy 10km no tag"
