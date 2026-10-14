"""Tests for the entry point of the ingestion."""

import logging

import pandas as pd
import pytest
from sqlalchemy.exc import OperationalError

from ingestion import main
from ingestion.loaders import STATUS_FAILED, STATUS_SUCCESS
from ingestion.main import exit_code

ENGINE = object()
TABLES = ["t.a", "t.b"]


@pytest.mark.parametrize(
    "statuses, expected",
    [
        ([STATUS_SUCCESS] * 6, 0),
        ([STATUS_SUCCESS] * 5 + [STATUS_FAILED], 1),
        ([STATUS_FAILED] * 6, 1),
        ([], 1),
        ([STATUS_SUCCESS, "OTHER"], 1),
        ([STATUS_SUCCESS, None], 1),
    ],
    ids=[
        "all_succeeded",
        "one_failed",
        "all_failed",
        "empty_summary",
        "unknown_status",
        "missing_status",
    ],
)
def test_exit_code(statuses, expected):
    """Check that only a run where every table succeeded exits with 0."""
    summary = pd.DataFrame({"status": statuses})

    assert exit_code(summary) == expected


def make_summary(statuses):
    """Build a run summary with one table per status."""
    return pd.DataFrame({"table": TABLES, "status": statuses})


def use_pipeline(monkeypatch, summary):
    """Fake the database and ``ingest_all``; return the engines it got.

    ``ingest_all`` returns ``summary`` and records the engine it receives,
    so a test can tell whether the ingestion ran at all.
    """
    received = []

    def fake_ingest_all(engine):
        received.append(engine)
        return summary

    monkeypatch.setattr(main, "get_engine", lambda: ENGINE)
    monkeypatch.setattr(main, "check_connection", lambda _engine: "TestDW")
    monkeypatch.setattr(main, "ingest_all", fake_ingest_all)
    return received


def test_clean_run_returns_0_and_prints_the_summary(monkeypatch, capsys):
    """A run where every table loads exits with 0 and shows the summary."""
    summary = make_summary([STATUS_SUCCESS, STATUS_SUCCESS])
    received = use_pipeline(monkeypatch, summary)
    code = main.main()
    output = capsys.readouterr().out
    assert code == 0
    assert received == [ENGINE]
    assert "t.a" in output
    assert "t.b" in output


def test_a_failed_table_returns_1(monkeypatch):
    """The exit code of the process comes from the summary."""
    summary = make_summary([STATUS_SUCCESS, STATUS_FAILED])
    use_pipeline(monkeypatch, summary)
    assert main.main() == 1


@pytest.mark.parametrize(
    "step, error",
    [
        ("get_engine", KeyError("DW_SERVER")),
        (
            "check_connection",
            OperationalError("SELECT 1", {}, Exception("login failed")),
        ),
    ],
    ids=["missing_variable", "no_connection"],
)
def test_startup_error_returns_2_and_loads_nothing(
    monkeypatch, capsys, caplog, step, error
):
    """If the run cannot start, say why, load nothing and exit with 2."""
    received = use_pipeline(monkeypatch, make_summary([STATUS_SUCCESS] * 2))

    def broken_step(*_args):
        raise error

    monkeypatch.setattr(main, step, broken_step)
    with caplog.at_level(logging.ERROR, logger="ingestion.main"):
        code = main.main()
    assert code == 2
    assert not received
    assert capsys.readouterr().out == ""
    assert [record.levelname for record in caplog.records] == ["ERROR"]
    assert str(error) in caplog.messages[0]
