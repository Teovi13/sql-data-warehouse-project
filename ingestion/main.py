"""Entry point of the ingestion."""

import logging
import sys

import pandas as pd
from sqlalchemy.exc import SQLAlchemyError

from ingestion.db import check_connection, get_engine
from ingestion.loaders import STATUS_SUCCESS
from ingestion.pipeline import ingest_all

logger = logging.getLogger(__name__)


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


def main() -> int:
    """Run the whole ingestion and return the exit code of the process.

    The log goes to stderr and the summary of the run to stdout. The
    returned code is ``0`` if every table was loaded, ``1`` if any table
    failed (see ``exit_code``) and ``2`` if the run could not start: a
    missing environment variable or no connection to the database. In that
    last case nothing is loaded and nothing is written to ``bronze.load_log``.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        engine = get_engine()
        database = check_connection(engine)
    except KeyError as error:
        logger.error("Missing environment variable: %s", error)
        return 2
    except SQLAlchemyError as error:
        logger.error("Cannot connect to the database: %s", error)
        return 2
    logger.info("Connected to the database %s", database)
    summary = ingest_all(engine)
    print(summary.to_string(index=False))
    return exit_code(summary)


if __name__ == "__main__":
    sys.exit(main())
