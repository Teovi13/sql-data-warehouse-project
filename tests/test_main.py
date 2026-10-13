"""Tests for the entry point of the ingestion."""

import pandas as pd
import pytest

from ingestion.loaders import STATUS_FAILED, STATUS_SUCCESS
from ingestion.main import exit_code


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
