#!/usr/bin/env python3
"""
Extract GL transaction data from the API and load into PostgreSQL database.

This module can be used in two ways:
1. As a standalone CLI script — reads DB credentials from environment variables.
2. As a library callable from Airflow — accepts a pre-built psycopg2 connection
   (e.g., from PostgresHook), bypassing environment-variable defaults entirely.
"""
import os
import sys
import json
from datetime import datetime
import psycopg2
import requests
from psycopg2.extras import execute_batch

# Configuration — used only in standalone CLI mode.
# Defaults target the Docker Compose service names so that
# `docker compose run --rm fastapi python /app/extract_load.py` works
# without extra -e flags. Override via env vars for local/Airflow use.
API_BASE_URL = os.getenv("API_BASE_URL", "http://fastapi_app:8000")
CSV_ENDPOINT = f"{API_BASE_URL}/transactions/raw"

# Database connection parameters — fallbacks for standalone CLI use only.
# When called from Airflow, connection is provided via PostgresHook.
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "finance_demo")
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "123learn")

# Batch size for inserts
BATCH_SIZE = 1000


def parse_date(date_str: str) -> datetime.date:
    """
    Parse date from format like "Monday, 22 January 2018" to a date object.
    """
    try:
        # Remove the day name prefix (e.g., "Monday, ")
        date_part = date_str.split(", ", 1)[1] if ", " in date_str else date_str
        return datetime.strptime(date_part, "%d %B %Y").date()
    except (ValueError, IndexError) as e:
        raise ValueError(f"Unable to parse date '{date_str}': {str(e)}") from e


def fetch_raw_data() -> list:
    """
    Fetch all raw data from the API endpoint with pagination.
    Returns a list of dictionaries (each dict is a row with original column names as strings).

    Raises RuntimeError on API failures instead of sys.exit() so that
    Airflow can catch and retry the task.
    """
    all_rows = []
    offset = 0
    limit = 1000  # Fetch in batches of 1000

    while True:
        params = {"limit": limit, "offset": offset}
        try:
            response = requests.get(CSV_ENDPOINT, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            if not data:
                break
            all_rows.extend(data)
            if len(data) < limit:
                break
            offset += limit
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Error fetching data from API: {e}") from e
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Error decoding JSON response: {e}") from e

    return all_rows


def transform_row(raw_row: dict) -> tuple:
    """
    Transform a raw row (dict with string values) into a tuple of values suitable for insertion.
    Returns a tuple in the order: (entry_no, date, territory_key, account_key, details, debit, credit)
    """
    try:
        entry_no = raw_row.get("EntryNo", "").strip()
        date_str = raw_row.get("Date", "").strip()
        details = raw_row.get("Details", "").strip()
        territory_key_str = raw_row.get("Territory_key", "0").strip()
        account_key_str = raw_row.get("Account_key", "0").strip()
        debit_str = raw_row.get("Debit", "0").strip()
        credit_str = raw_row.get("Credit", "0").strip()

        if not entry_no:
            raise ValueError("EntryNo is required")
        if not date_str:
            raise ValueError("Date is required")

        # Parse date
        date_obj = parse_date(date_str)

        # Convert numeric fields
        try:
            territory_key = int(territory_key_str) if territory_key_str else 0
        except ValueError:
            territory_key = 0

        try:
            account_key = int(account_key_str) if account_key_str else 0
        except ValueError:
            account_key = 0

        try:
            debit = float(debit_str) if debit_str else 0.0
        except ValueError:
            debit = 0.0

        try:
            credit = float(credit_str) if credit_str else 0.0
        except ValueError:
            credit = 0.0

        return (entry_no, date_obj, territory_key, account_key, details, debit, credit)

    except Exception as e:
        # Re-raise with context
        raise ValueError(f"Error transforming row {raw_row}: {e}") from e


def load_data_to_db(rows: list, conn=None):
    """
    Load the list of transformed rows into the PostgreSQL database.
    Uses batch inserts for efficiency.

    Args:
        rows: List of raw row dicts to transform and load.
        conn: Optional psycopg2 connection. When provided (e.g., from Airflow
              PostgresHook), it is used directly and NOT closed here — the caller
              owns the lifecycle. When None, a connection is created from env-var
              defaults and closed in the finally block.

    Raises:
        RuntimeError: On database errors (instead of sys.exit).
    """
    conn_owned = conn is None  # Track whether we created this connection
    if conn is None:
        # Standalone CLI mode — build connection from environment variables
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
        )

    try:
        cur = conn.cursor()

        # Ensure we are in the finance schema
        cur.execute("SET search_path TO finance;")

        # Prepare the insert statement
        insert_sql = """
            INSERT INTO finance.gl_transactions
                (entry_no, date, territory_key, account_key, details, debit, credit)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (entry_no) DO UPDATE SET
                date = EXCLUDED.date,
                territory_key = EXCLUDED.territory_key,
                account_key = EXCLUDED.account_key,
                details = EXCLUDED.details,
                debit = EXCLUDED.debit,
                credit = EXCLUDED.credit;
        """

        # Transform all rows
        transformed_rows = []
        for i, raw_row in enumerate(rows):
            try:
                transformed_row = transform_row(raw_row)
                transformed_rows.append(transformed_row)
            except ValueError as e:
                print(f"Skipping row {i+1} due to transformation error: {e}", file=sys.stderr)
                continue

        # Insert in batches
        for i in range(0, len(transformed_rows), BATCH_SIZE):
            batch = transformed_rows[i:i+BATCH_SIZE]
            execute_batch(cur, insert_sql, batch)
            conn.commit()
            print(f"Inserted batch {i//BATCH_SIZE + 1} ({len(batch)} rows)")

        cur.close()
        print(f"Successfully loaded {len(transformed_rows)} rows into the database.")

    except psycopg2.Error as e:
        print(f"Database error: {e}", file=sys.stderr)
        if conn:
            conn.rollback()
        raise RuntimeError(f"Database error: {e}") from e
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        if conn:
            conn.rollback()
        raise RuntimeError(f"Unexpected error: {e}") from e
    finally:
        # Only close connections we created — caller-owned connections are their responsibility
        if conn_owned and conn:
            conn.close()


def main():
    """Entry point for standalone CLI execution."""
    print("Fetching raw data from API...")
    raw_data = fetch_raw_data()
    print(f"Fetched {len(raw_data)} raw rows.")

    print("Loading data into database...")
    load_data_to_db(raw_data)

    print("Done.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)
