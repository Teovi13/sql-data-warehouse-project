"""Database connection helpers for the ingestion layer.

Connection settings are read from environment variables, optionally loaded
from the ``.env`` file at the project root, so no server name or credential
is hardcoded.
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, URL

from ingestion.config import BASE_DIR


def get_engine() -> Engine:
    """Build a SQLAlchemy engine for the data warehouse.

    Settings come from environment variables. The ``.env`` file at the
    project root is loaded first; variables already set in the real
    environment take precedence over it. Windows authentication is used,
    so no username or password is needed.

    Required variables:
        DW_SERVER: SQL Server host and instance name.
        DW_DATABASE: Database to connect to.

    Optional variables:
        DW_ODBC_DRIVER: ODBC driver name. Defaults to
            ``ODBC Driver 18 for SQL Server``.
        DW_TRUST_SERVER_CERT: ``yes`` or ``no``. Defaults to ``no``, so
            the server certificate is validated unless validation is
            explicitly disabled (development only).

    Returns:
        A lazy engine: no connection is opened until it is first used.
        Each call creates a new engine with its own connection pool, so
        call it once and share the result.

    Raises:
        KeyError: If ``DW_SERVER`` or ``DW_DATABASE`` is not set.
    """
    # Load the project's .env file. Variables already present in the real
    # environment are not overwritten.
    load_dotenv(BASE_DIR / ".env")

    # Required settings: a missing one raises KeyError right away.
    server = os.environ["DW_SERVER"]
    database = os.environ["DW_DATABASE"]

    # Optional settings, with safe defaults.
    odbc_driver = os.environ.get(
        "DW_ODBC_DRIVER",
        "ODBC Driver 18 for SQL Server",
    )
    trust_server_cert = os.environ.get("DW_TRUST_SERVER_CERT", "no")

    # No username or password: SQLAlchemy adds Trusted_Connection=Yes
    # by itself, which selects Windows authentication.
    url = URL.create(
        drivername="mssql+pyodbc",
        host=server,
        database=database,
        query={
            "driver": odbc_driver,
            "TrustServerCertificate": trust_server_cert,
        },
    )
    engine = create_engine(url)
    return engine


def check_connection(engine: Engine) -> str:
    """Check that the engine can reach the database.

    Opens a connection, asks the server for the name of the database it
    is connected to, and releases the connection.

    Args:
        engine: Engine returned by ``get_engine``.

    Returns:
        The name of the connected database, e.g. ``DataWarehouse``.

    Raises:
        sqlalchemy.exc.DBAPIError: If the connection cannot be established
            or the query fails (driver, certificate, login or database
            errors).
    """
    # The connection goes back to the pool when the block ends.
    with engine.connect() as connection:
        database_name = connection.execute(text("SELECT DB_NAME()")).scalar()

    return database_name
