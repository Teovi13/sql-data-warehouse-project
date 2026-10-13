"""Entry point of the ingestion."""

import pandas as pd

from ingestion.loaders import STATUS_SUCCESS


def exit_code(summary: pd.DataFrame) -> int:
    """Return the exit code of an ingestion run.

    The run succeeds (``0``) only when ``summary`` has at least one table and
    every table has the status ``STATUS_SUCCESS``. Anything else is a failure
    (``1``): a failed table, an unknown or missing status, or an empty
    summary, because a run that processed nothing is not a success.

    Raises:
        KeyError: If ``summary`` has rows but no ``status`` column.
    """
    if summary.empty:
        return 1
    all_ok = (summary["status"] == STATUS_SUCCESS).all()
    if all_ok:
        return 0
    return 1
