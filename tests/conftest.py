"""Shared test configuration — isolate all storage to temp directories."""


import pytest


@pytest.fixture(autouse=True)
def isolate_data_dir(tmp_path, monkeypatch):
    """Point all storage at a temp directory so tests never touch real data."""
    monkeypatch.setenv("STRAVA_DATA_DIR", str(tmp_path))
