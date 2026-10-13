"""Tests for the engine built by ``get_engine``."""

from ingestion.db import get_engine


def test_engine_uses_fast_executemany(monkeypatch):
    """Check that the engine sends insert rows in batches, not one by one."""
    monkeypatch.setenv("DW_SERVER", "any-server")
    monkeypatch.setenv("DW_DATABASE", "any-database")

    engine = get_engine()

    assert engine.dialect.fast_executemany
