"""Tests for date utilities — no LLM or API calls."""

from datetime import date

import pytest

from mcpacer.utils.dates import (
    get_week_date_range,
    get_week_key,
    group_runs_by_week,
    parse_date,
    timestamp_to_date,
)


class TestParseDate:
    def test_valid_date(self):
        assert parse_date("2026-03-15") == date(2026, 3, 15)

    def test_invalid_format(self):
        with pytest.raises(ValueError, match="Invalid date format"):
            parse_date("15-03-2026")

    def test_empty_string(self):
        with pytest.raises(ValueError):
            parse_date("")


class TestTimestampToDate:
    def test_known_timestamp(self):
        # 2026-01-01 12:00:00 UTC = 1767268800 (use midday to avoid TZ edge)
        result = timestamp_to_date(1767268800)
        assert result == date(2026, 1, 1)


class TestGetWeekKey:
    def test_known_date(self):
        # 2026-03-16 is a Monday, ISO week 12
        year, week = get_week_key("2026-03-16T10:00:00Z")
        assert year == 2026
        assert week == 12

    def test_sunday_same_week(self):
        # Sunday of the same week
        _, week_mon = get_week_key("2026-03-16T10:00:00Z")
        _, week_sun = get_week_key("2026-03-22T10:00:00Z")
        assert week_mon == week_sun


class TestGetWeekDateRange:
    def test_known_week(self):
        result = get_week_date_range(2026, 12)
        assert "2026-03-16" in result
        assert "2026-03-22" in result


class TestGroupRunsByWeek:
    def test_groups_correctly(self):
        runs = [
            {"start_date": "2026-03-16T08:00:00Z", "name": "Monday run"},
            {"start_date": "2026-03-18T08:00:00Z", "name": "Wednesday run"},
            {"start_date": "2026-03-23T08:00:00Z", "name": "Next Monday"},
        ]
        grouped = group_runs_by_week(runs)
        assert len(grouped) == 2
        week12 = grouped[(2026, 12)]
        assert len(week12) == 2

    def test_empty_runs(self):
        assert group_runs_by_week([]) == {}

    def test_missing_date(self):
        runs = [{"name": "no date"}]
        assert group_runs_by_week(runs) == {}
