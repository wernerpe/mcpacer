"""Tests for formatting utilities — no LLM or API calls."""

from mcpacer.utils.formatting import format_duration, format_pace


class TestFormatPace:
    def test_normal_pace(self):
        # ~5:00/km = 1000m / (5*60s) = 3.333 m/s
        assert format_pace(3.333) == "5:00"

    def test_fast_pace(self):
        # ~3:45/km = 1000 / (3*60+45) = 4.444 m/s
        assert format_pace(4.444) == "3:45"

    def test_slow_pace(self):
        # ~7:00/km = 1000 / 420 ≈ 2.3809 m/s
        result = format_pace(1000 / 420)
        assert result == "7:00"

    def test_zero_speed(self):
        assert format_pace(0) == "N/A"

    def test_negative_speed(self):
        assert format_pace(-1.0) == "N/A"


class TestFormatDuration:
    def test_minutes_only(self):
        assert format_duration(300) == "5:00"

    def test_minutes_and_seconds(self):
        assert format_duration(185) == "3:05"

    def test_with_hours(self):
        assert format_duration(3661) == "1:01:01"

    def test_zero(self):
        assert format_duration(0) == "0:00"

    def test_exactly_one_hour(self):
        assert format_duration(3600) == "1:00:00"

    def test_float_input(self):
        assert format_duration(90.7) == "1:30"
