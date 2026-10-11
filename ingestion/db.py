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

    Reads ``DW_SERVER`` and ``DW_DATABASE`` (required), plus
    ``DW_ODBC_DRIVER`` and ``DW_TRUST_SERVER_CERT`` (optional), from the
    environment. The ``.env`` file is loaded first, but variables already
    set in the real environment win. See ``.env.example``. No username or
    password is needed: Windows authentication is used.

    The engine is lazy and every call creates its own connection pool, so
    call this once and share the result. Parameter values are hidden in
    error messages and SQL logs.

    Raises:
        KeyError: If ``DW_SERVER`` or ``DW_DATABASE`` is not set.
    """
    load_dotenv(BASE_DIR / ".env")

    # Required: a missing variable fails here, not at connection time.
    server = os.environ["DW_SERVER"]
    database = os.environ["DW_DATABASE"]

    odbc_driver = os.environ.get(
        "DW_ODBC_DRIVER",
        "ODBC Driver 18 for SQL Server",
    )
    # Secure by default: the server certificate is validated unless the
    # variable explicitly disables it (development only).
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
    # Failed inserts would otherwise echo row values (customer data) into
    # tracebacks and logs.
    engine = create_engine(url, hide_parameters=True)
    return engine


def check_connection(engine: Engine) -> str:
    """Check that the engine can reach the database and return its name.

    Raises:
        sqlalchemy.exc.DBAPIError: If the connection cannot be established
            or the query fails.
    """
    # The connection goes back to the pool when the block ends.
    with engine.connect() as connection:
        database_name = connection.execute(text("SELECT DB_NAME()")).scalar()

    return database_name
