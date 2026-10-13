"""Tests for process_table: every failure is logged exactly once."""

import pandas as pd
import pytest

from ingestion import pipeline
from ingestion.loaders import STATUS_FAILED

ENGINE = object()
TABLE = "test.table"
REPORT = pd.DataFrame({"rows": [0]})
FRAME = pd.DataFrame({"id": [1]})


def use_fakes(monkeypatch, fail_in=None):
    """Replace the steps of ``process_table`` with fakes that record calls.

    Return ``(calls, logged)``: the steps called, in order, and what
    ``write_load_log`` received. The step named ``fail_in`` raises.
    """
    calls = []
    logged = []

    def make_step(name, result):
        def step(*_args, **_kwargs):
            calls.append(name)
            if name == fail_in:
                raise ValueError("boom")
            return result
        return step

    def write_log(engine, table_name, status, error_message=None, **_ignored):
        calls.append("log")
        logged.append((engine, table_name, status, error_message))

    fakes = {
        "validate_table": make_step("validate", REPORT),
        "prepare_table": make_step("prepare", FRAME),
        "load_and_log": make_step("load", None),
        "write_load_log": write_log,
    }
    for name, fake in fakes.items():
        monkeypatch.setattr(pipeline, name, fake)
    return calls, logged


def test_success_returns_the_validation_report(monkeypatch):
    """A clean table is validated, prepared and loaded, with no log here."""
    calls, logged = use_fakes(monkeypatch)
    result = pipeline.process_table(ENGINE, TABLE)
    assert calls == ["validate", "prepare", "load"]
    assert not logged
    assert result is REPORT


@pytest.mark.parametrize("stage", ["validate", "prepare"])
def test_failure_before_load_is_logged_and_raised(monkeypatch, stage):
    """A failure before the load leaves a FAILED row and is not swallowed."""
    calls, logged = use_fakes(monkeypatch, fail_in=stage)
    with pytest.raises(ValueError):
        pipeline.process_table(ENGINE, TABLE)
    assert "load" not in calls
    assert logged == [(ENGINE, TABLE, STATUS_FAILED, "ValueError: boom")]


def test_load_failure_is_not_logged_twice(monkeypatch):
    """``load_and_log`` logs its own failures, so this one logs nothing."""
    calls, logged = use_fakes(monkeypatch, fail_in="load")
    with pytest.raises(ValueError):
        pipeline.process_table(ENGINE, TABLE)
    assert calls == ["validate", "prepare", "load"]
    assert not logged
