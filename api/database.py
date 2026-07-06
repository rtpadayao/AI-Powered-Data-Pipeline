"""
Database utility functions for the FastAPI application.
Handles PostgreSQL connections and queries for dbt-transformed data.
"""
import os
import re
import datetime
import decimal
import psycopg2
import psycopg2.extras
from typing import List, Dict, Any, Optional
from contextlib import contextmanager

# Database connection parameters (can be overridden by environment)
DB_HOST = os.getenv("DB_HOST", "postgres")  # Changed to postgres service name for Docker
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "finance_demo")
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "123learn")


@contextmanager
def get_db_connection():
    """
    Context manager for PostgreSQL database connections.
    Automatically handles connection closing and transaction rollback on error.
    """
    conn = None
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        # Set search path to finance schema where dbt models are located
        with conn.cursor() as cur:
            cur.execute("SET search_path TO finance;")
        yield conn
    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()


def execute_query(query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
    """
    Execute a SELECT query and return results as a list of dictionaries.

    Args:
        query: SQL query string
        params: Optional tuple of query parameters

    Returns:
        List of dictionaries representing the query results
    """
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
            # Convert to list of regular dictionaries, with date/decimal
            # values coerced to JSON-safe types (psycopg2 returns datetime.date
            # and Decimal, which JSONResponse cannot serialize).
            return [_json_safe(dict(row)) for row in rows]


# ---------------------------------------------------------------------------
# Read-only guard — used by /ask and any caller that takes
# untrusted input (natural language → SQL). Mirrors the pipeline-mcp
# server's guard (server.py) so the rule lives in one place per surface.
# ---------------------------------------------------------------------------
_READ_ONLY_RE = re.compile(r"^\s*(SELECT|WITH|EXPLAIN)\b", re.IGNORECASE)
_WRITE_VERBS_RE = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|COPY)\b",
    re.IGNORECASE,
)


def is_read_only_sql(query: str) -> bool:
    """True only if the statement starts with SELECT/WITH/EXPLAIN and contains
    no write verbs. Comment-obfuscated writes are caught because the regex
    matches the verb regardless of surrounding comment syntax."""
    if not _READ_ONLY_RE.match(query):
        return False
    if _WRITE_VERBS_RE.search(query):
        return False
    return True


def execute_read_only_query(query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
    """
    Execute a query only if it passes the read-only guard. Use this for any
    SQL derived from untrusted input (e.g. natural-language questions in /ask).
    Raises HTTPException-equivalent error dict on guard failure so callers can
    return a clean 400.
    """
    if not is_read_only_sql(query):
        raise ValueError(
            "Rejected: only SELECT / WITH / EXPLAIN statements are permitted."
        )
    return execute_query(query, params)


def _json_safe(row: Dict[str, Any]) -> Dict[str, Any]:
    """Coerce psycopg2's non-JSON types (date, datetime, Decimal) to safe ones."""
    clean: Dict[str, Any] = {}
    for k, v in row.items():
        if isinstance(v, (datetime.date, datetime.datetime, datetime.time)):
            clean[k] = v.isoformat()
        elif isinstance(v, decimal.Decimal):
            # Whole decimals render as int, otherwise float
            clean[k] = int(v) if v == v.to_integral() else float(v)
        else:
            clean[k] = v
    return clean


def get_refined_data(table_name: str, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Get data from a refined schema table.

    Args:
        table_name: Name of the table in the refined schema
        limit: Maximum number of rows to return
        offset: Number of rows to skip before starting to collect

    Returns:
        List of dictionaries representing the table data
    """
    query = f"SELECT * FROM public_refined.{table_name}"
    params = []

    if offset is not None:
        query += " OFFSET %s"
        params.append(offset)

    if limit is not None:
        query += " LIMIT %s"
        params.append(limit)

    return execute_query(query, tuple(params) if params else None)


def get_marts_data(table_name: str, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Get data from a marts schema table.

    Args:
        table_name: Name of the table in the marts schema
        limit: Maximum number of rows to return
        offset: Number of rows to skip before starting to collect

    Returns:
        List of dictionaries representing the table data
    """
    query = f"SELECT * FROM public_marts.{table_name}"
    params = []

    if offset is not None:
        query += " OFFSET %s"
        params.append(offset)

    if limit is not None:
        query += " LIMIT %s"
        params.append(limit)

    return execute_query(query, tuple(params) if params else None)