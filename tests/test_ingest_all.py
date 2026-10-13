"""Tests for ingest_all: one failing table must not stop the others."""

import pandas as pd

from ingestion import pipeline
from ingestion.loaders import STATUS_FAILED, STATUS_SUCCESS

ENGINE = object()
TABLES = {"t.a": None, "t.b": None, "t.c": None}
REPORT = pd.DataFrame({"rows": [0, 2, 1]})
COLUMNS = ["table", "status", "flagged", "error"]


def use_tables(monkeypatch, tables, failing=()):
    """Fake ``SOURCES`` and ``process_table``; return the tables attempted.

    The fake returns ``REPORT`` (two rules flagged rows) and raises for the
    tables listed in ``failing``.
    """
    attempted = []

    def fake_process(_engine, table):
        attempted.append(table)
        if table in failing:
            raise ValueError("boom")
        return REPORT

    monkeypatch.setattr(pipeline, "SOURCES", tables)
    monkeypatch.setattr(pipeline, "process_table", fake_process)
    return attempted


def test_every_table_is_processed_in_order(monkeypatch):
    """A clean run has one SUCCESS row per table, in load order."""
    attempted = use_tables(monkeypatch, TABLES)
    summary = pipeline.ingest_all(ENGINE)
    assert attempted == ["t.a", "t.b", "t.c"]
    assert summary["table"].tolist() == ["t.a", "t.b", "t.c"]
    assert summary["status"].tolist() == [STATUS_SUCCESS] * 3
    assert summary["flagged"].tolist() == [2, 2, 2]
    assert summary["error"].isna().all()


def test_a_failing_table_does_not_stop_the_others(monkeypatch):
    """The failure is reported in the summary and the loop goes on."""
    attempted = use_tables(monkeypatch, TABLES, failing=["t.b"])
    summary = pipeline.ingest_all(ENGINE)
    assert attempted == ["t.a", "t.b", "t.c"]
    assert summary["status"].tolist() == [
        STATUS_SUCCESS,
        STATUS_FAILED,
        STATUS_SUCCESS,
    ]
    failed = summary[summary["status"] == STATUS_FAILED]
    assert failed["table"].tolist() == ["t.b"]
    assert failed["error"].tolist() == ["ValueError: boom"]
    assert failed["flagged"].isna().all()


def test_no_tables_gives_an_empty_summary(monkeypatch):
    """With nothing to process the summary is empty but keeps its columns."""
    use_tables(monkeypatch, {})
    summary = pipeline.ingest_all(ENGINE)
    assert summary.empty
    assert list(summary.columns) == COLUMNS
