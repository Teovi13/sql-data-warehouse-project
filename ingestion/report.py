"""Run the validation rules and collect the results in a report."""

import pandas as pd

from ingestion.readers import read_table


def run_validations(rules: list) -> pd.DataFrame:
    """Run every rule and return one report row per rule.

    Each rule is a ``(table, check, params)`` tuple: the table name, a
    validator from ``ingestion.validators`` and its keyword arguments. Each
    table is read once and reused by all of its rules.

    A rule that raises does not stop the run: its ``rows`` is ``<NA>`` and
    the error is stored in ``error``. The report has the columns ``table``,
    ``rule``, ``params``, ``rows`` (number of flagged rows) and ``error``.
    """
    results = []
    tables = {}
    for table, check, params in rules:
        try:
            if table not in tables:
                tables[table] = read_table(table)
            found = check(tables[table], **params)
            error = None
            rows = len(found)
        except Exception as problem:  # pylint: disable=broad-exception-caught
            error = f"{type(problem).__name__}: {problem}"
            rows = None
        results.append({
            "table": table,
            "rule": check.__name__,
            "params": params,
            "rows": rows,
            "error": error,
        })

    return pd.DataFrame(results).astype({"rows": "Int64"})
