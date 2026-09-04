"""
PostgreSQL Connection & Database Bootstrap Module

Provides two helpers for working with PostgreSQL:

1. :func:`CreateDatabase`
   Connects to the server, checks if the target database exists, and
   creates it if it does not.  Prints status messages; returns an error
   string on failure.

2. :func:`CreateEngine`
   Builds and returns a SQLAlchemy ``Engine`` for the given database name.

Connection settings are read from ``.env``:

    POSTGRES_HOST
    POSTGRES_PORT
    POSTGRES_DATABASE
    POSTGRES_USER
    POSTGRES_PASSWORD

Usage:
    from Database.postgres_connect import CreateDatabase, CreateEngine

    CreateDatabase()

    engine = CreateEngine("investoriq")
    with engine.connect() as conn:
        result = conn.execute("SELECT 1")
        print(result.fetchone())
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote_plus

import psycopg2
import psycopg2.extensions
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

load_dotenv(dotenv_path=PROJECT_ROOT / ".env")


def _get_env(name: str) -> str:
    """Read a required variable from the environment."""
    value = os.getenv(key=name)
    if not value:
        raise OSError(
            f"Missing required environment variable: {name}. "
            "Add it to your .env file at the project root."
        )
    return value


# ---------------------------------------------------------------------------
# CreateDatabase
# ---------------------------------------------------------------------------
def CreateDatabase() -> str | None:
    """Create the target database if it does not exist.

    Reads connection details from ``.env``.  Connects to the default
    ``postgres`` database, checks for the target, and issues
    ``CREATE DATABASE`` when missing.

    Returns
    -------
    str | None
        ``None`` on success.  An error message string on failure.
    """
    host = _get_env(name="POSTGRES_HOST")
    port = int(_get_env(name="POSTGRES_PORT"))
    user = _get_env(name="POSTGRES_USER")
    password = _get_env(name="POSTGRES_PASSWORD")
    database = _get_env(name="POSTGRES_DATABASE")

    conn = None
    try:
        # Connect to the 'postgres' database to issue server-level DDL.
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname="postgres",
            sslmode="require",
        )
        conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (database,))

        if cursor.fetchone() is None:
            cursor.execute(f'CREATE DATABASE "{database}";')
            print(f"[OK] Database '{database}' created successfully.")
        else:
            print(f"[OK] Database '{database}' already exists.")

        cursor.close()
        return None

    except Exception as exc:
        error_msg = f"Failed to create database '{database}': {exc}"
        print(f"[ERROR] {error_msg}")
        return error_msg

    finally:
        if conn is not None:
            conn.close()


# ---------------------------------------------------------------------------
# CreateEngine
# ---------------------------------------------------------------------------
def CreateEngine(database: str) -> Engine:
    """Return a SQLAlchemy ``Engine`` for the given database.

    Parameters
    ----------
    database : str
        Name of the PostgreSQL database to connect to.

    Returns
    -------
    Engine
        A SQLAlchemy engine using the ``postgresql+psycopg2`` driver.

    Raises
    ------
    OSError
        If a required environment variable is missing.
    """
    host = _get_env(name="POSTGRES_HOST")
    port = _get_env(name="POSTGRES_PORT")
    user = _get_env(name="POSTGRES_USER")
    password = _get_env(name="POSTGRES_PASSWORD")

    url = f"postgresql+psycopg2://{quote_plus(string=user)}:{quote_plus(string=password)}@{host}:{port}/{database}"
    engine = create_engine(url)
    print(f"[OK] Engine created for database '{database}'.")
    return engine
