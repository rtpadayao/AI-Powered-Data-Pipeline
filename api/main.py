# api/main.py
import csv
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Query, Request, Depends
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from schemas import (
    TransactionResponse,
    DimAccountResponse,
    DimDateResponse,
    FactGLTransactionsResponse,
    NormalizeResponse,
    FinancialStatementsResponse,
    AccountBalancesResponse,
    TrialBalanceResponse,
    IncomeStatementResponse
)
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from database import get_refined_data, get_marts_data, execute_read_only_query, is_read_only_sql

# CSV file path for backward compatibility
CSV_PATH = os.getenv(
    "CSV_PATH",
    "/home/roy/repos/cc_AI-Powered_Airflow/infrastructure/raw_storage/raw_gl_dr_cr_noAmount.csv"
)

app = FastAPI(title="GL Transactions API - Serving dbt-transformed data")

# ----------------------------------------------------------------------
# Rate limiting
# ----------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ----------------------------------------------------------------------
# Middleware
# ----------------------------------------------------------------------
# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# Gzip middleware for compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Trusted host middleware (adjust as needed)
# app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

# ----------------------------------------------------------------------
# CSV Caching
# ----------------------------------------------------------------------
_cached_data: List[Dict[str, Any]] = None
_cached_mtime: float = None

def _read_csv_as_dicts(path: str) -> List[Dict[str, Any]]:
    """
    Reads the CSV file and returns a list of dictionaries, each representing a row
    with the original column names as keys and values as strings (empty string for missing).
    Skips completely empty rows (where all fields are empty).
    Raises HTTPException with appropriate status codes on failure.
    """
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"CSV file not found: {path}")

    rows: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8-sig") as f:  # utf-8-sig to handle BOM
        reader = csv.DictReader(f)
        for line_no, raw_row in enumerate(reader, start=2):  # start=2 accounts for header
            # Skip empty rows (where all values are empty strings)
            if all(v.strip() == "" for v in raw_row.values()):
                continue
            # Store values as strings (preserving original format)
            rows.append({k: v for k, v in raw_row.items()})
    return rows

def get_csv_data(path: str) -> List[Dict[str, Any]]:
    """
    Returns the CSV data, using a cache that invalidates when the file modification time changes.
    """
    global _cached_data, _cached_mtime
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        raise HTTPException(status_code=404, detail=f"CSV file not found: {path}")

    if _cached_data is not None and _cached_mtime == mtime:
        return _cached_data

    # Read and cache
    data = _read_csv_as_dicts(path)
    _cached_data = data
    _cached_mtime = mtime
    return data




# ----------------------------------------------------------------------
# Endpoints
# ----------------------------------------------------------------------
@app.get("/transactions", response_model=List[TransactionResponse], summary="Return GL transactions as JSON array (from dbt marts.normalize)")
@limiter.limit("100/minute")  # 100 requests per minute per IP
def get_transactions(
    request: Request,
    limit: int = Query(
        None, gt=0, description="Maximum number of rows to return (for pagination)"
    ),
    offset: int = Query(
        0, ge=0, description="Number of rows to skip before starting to collect"
    ),
):
    """
    Returns GL transaction data from the dbt marts.normalize table.
    Provides transaction data with normalized amounts (already transformed by dbt).
    Optional `limit` and `offset` query parameters allow simple pagination.
    """
    try:
        # Get data from marts.normalize table
        raw_data = get_marts_data("normalize", limit, offset)

        # Transform to match the expected TransactionResponse format
        # marts.normalize has: entry_no, date, territory_key, account_id, details, debit, credit, amount
        # We need to return: id, date, amount
        transformed_data = []
        for row in raw_data:
            transformed_data.append({
                "id": row["entry_no"],
                "date": row["date"],
                "amount": row["amount"]
            })

        return JSONResponse(content=transformed_data)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error querying marts.normalize table: {str(e)}"
        )


@app.get("/transactions/raw", summary="Return raw CSV data as JSON array")
@limiter.limit("100/minute")  # 100 requests per minute per IP
def get_transactions_raw(
    request: Request,
    limit: int = Query(
        None, gt=0, description="Maximum number of rows to return (for pagination)"
    ),
    offset: int = Query(
        0, ge=0, description="Number of rows to skip before starting to collect"
    ),
):
    """
    Reads the CSV and returns the raw data as a list of dictionaries (with original column names).
    Optional `limit` and `offset` query parameters allow simple pagination.
    """
    raw_data = get_csv_data(CSV_PATH)

    # Apply pagination
    if offset:
        raw_data = raw_data[offset:]
    if limit is not None:
        raw_data = raw_data[:limit]

    return JSONResponse(content=raw_data)


@app.get("/transactions/refined/{table_name}", summary="Get data from refined schema tables")
@limiter.limit("100/minute")  # 100 requests per minute per IP
def get_transactions_refined(
    request: Request,
    table_name: str,
    limit: int = Query(
        None, gt=0, description="Maximum number of rows to return (for pagination)"
    ),
    offset: int = Query(
        0, ge=0, description="Number of rows to skip before starting to collect"
    ),
):
    """
    Query data from the refined schema tables:
    - dim_account
    - dim_date
    - fact_gl_transactions

    Optional `limit` and `offset` query parameters allow simple pagination.
    """
    # Validate table name to prevent SQL injection
    allowed_tables = ["dim_account", "dim_date", "fact_gl_transactions"]
    if table_name not in allowed_tables:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid table name. Allowed tables: {', '.join(allowed_tables)}"
        )

    try:
        data = get_refined_data(table_name, limit, offset)
        return JSONResponse(content=data)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error querying refined table {table_name}: {str(e)}"
        )


@app.get("/transactions/marts/{table_name}", summary="Get data from marts schema tables")
@limiter.limit("100/minute")  # 100 requests per minute per IP
def get_transactions_marts(
    request: Request,
    table_name: str,
    limit: int = Query(
        None, gt=0, description="Maximum number of rows to return (for pagination)"
    ),
    offset: int = Query(
        0, ge=0, description="Number of rows to skip before starting to collect"
    ),
):
    """
    Query data from the marts schema tables:
    - normalize
    - financial_statements
    - account_balances

    Optional `limit` and `offset` query parameters allow simple pagination.
    """
    # Validate table name to prevent SQL injection
    allowed_tables = ["normalize", "financial_statements", "account_balances", "trial_balance_by_month", "income_statement_by_month", "balance_sheet_by_month", "gross_profit_mom_variance", "account_aging"]
    if table_name not in allowed_tables:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid table name. Allowed tables: {', '.join(allowed_tables)}"
        )

    try:
        data = get_marts_data(table_name, limit, offset)
        return JSONResponse(content=data)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error querying marts table {table_name}: {str(e)}"
        )


@app.get("/health", summary="Simple liveness probe")
@limiter.limit("100/minute")  # 100 requests per minute per IP
def health(request: Request):
    return {"status": "ok"}


# ----------------------------------------------------------------------
# /ask — natural-language Q&A over the warehouse
# ----------------------------------------------------------------------
class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, description="Natural-language question about the GL data.")
    limit: int = Field(100, gt=0, le=1000, description="Max rows to return (default 100, max 1000).")


class AskResponse(BaseModel):
    question: str
    sql: str
    rows: List[Dict[str, Any]]
    row_count: int
    answer: str
    guard: str = "read-only"


# Schema primer handed to the LLM for SQL generation. Kept tight so the
# model only learns the tables/columns it may query — no DDL, no write
# verbs, no raw-source schema. dim_account case-sensitivity is documented
# here so generated SQL quotes correctly.
_SCHEMA_PRIMER = """
You are a read-only SQL assistant over a financial data warehouse (PostgreSQL).
Generate ONLY a single SELECT/WITH/EXPLAIN statement. Never emit INSERT/UPDATE/
DELETE/DROP/ALTER/CREATE/TRUNCATE/COPY/GRANT/REVOKE.

Available tables (query with public_marts.*, public_refined.*):
- public_marts.normalize: entry_no (int), date (date), territory_key (int),
    account_id (int), details (text), debit (numeric), credit (numeric),
    amount (numeric, SIGNED: debit-normal accounts id<=100 have amount=debit-credit;
    credit-normal id>100 have amount=credit-debit). This is the base fact.
- public_marts.gross_profit_mom_variance: month (date), revenue, cogs, gross_profit,
    gross_profit_mom_pct (numeric).
- public_marts.trial_balance_by_month: month, account_id, total_debit, total_credit, net_amount.
- public_marts.income_statement_by_month: month, account_id, account_name, account_class,
    "SubClass", amount.
- public_marts.balance_sheet_by_month: month, account_class, net_amount, cumulative_amount.
- public_refined.dim_account: account_id (int), "Report" (text, 'Balance Sheet' or
    'Profit and Loss'), "Class" (text), "SubClass" (text), "SubClass2" (text),
    account_name (text), sub_account_name (text).
  CRITICAL: dim_account columns "Report", "Class", "SubClass", "SubClass2" are
  CASE-SENSITIVE and MUST be double-quoted in SQL. account_id and account_name are
  not case-sensitive and must NOT be quoted.
- public_refined.dim_date: date_key, year, month, quarter, day_of_week, is_weekend.
- public_refined.fact_gl_transactions: entry_no, date, territory_key, account_key,
    details, debit, credit, amount.

Layering: prefer public_marts.* over public_refined.* for analysis. Never query
finance.* (raw source) or public_staging.*.

Always add a LIMIT (default 100, max 1000). Always ORDER BY when using LIMIT.
Always use explicit JOIN syntax. Qualify every column with a table alias.
"""


def _generate_sql(question: str, limit: int) -> str:
    """Turn a natural-language question into a read-only SQL query via LLM.

    In this lightweight implementation we use a rule-based mapper for the most
    common analytical questions so the endpoint works without an external LLM
    call. For anything not matched, we raise so the caller can escalate to the
    finance-analyst agent (which has full LLM reasoning + psql_query access).
    """
    q = question.lower().strip()

    # --- MoM / variance / gross profit ---
    if any(k in q for k in ["gross profit", "revenue", "cogs", "cost of sales", "month over month", "mom"]):
        return (
            "SELECT month, revenue, cogs, gross_profit, gross_profit_mom_pct "
            "FROM public_marts.gross_profit_mom_variance "
            "ORDER BY month LIMIT %s"
        ) % limit

    # --- P&L / income statement ---
    if any(k in q for k in ["income statement", "p&l", "p and l", "profit and loss", "net income", "revenue", "expense"]):
        return (
            "SELECT month, account_class, SUM(amount) AS net_amount "
            "FROM public_marts.income_statement_by_month "
            "GROUP BY month, account_class ORDER BY month, account_class LIMIT %s"
        ) % limit

    # --- balance sheet ---
    if any(k in q for k in ["balance sheet", "assets", "liabilities", "equity"]):
        return (
            "SELECT month, account_class, cumulative_amount "
            "FROM public_marts.balance_sheet_by_month "
            "ORDER BY month, account_class LIMIT %s"
        ) % limit

    # --- trial balance / debits vs credits ---
    if any(k in q for k in ["trial balance", "debit", "credit"]):
        return (
            "SELECT month, SUM(total_debit) AS total_debit, SUM(total_credit) AS total_credit, "
            "SUM(total_debit) - SUM(total_credit) AS imbalance "
            "FROM public_marts.trial_balance_by_month "
            "GROUP BY month ORDER BY month LIMIT %s"
        ) % limit

    # --- largest / top postings ---
    if any(k in q for k in ["largest", "top", "biggest", "unusual"]):
        return (
            "SELECT n.entry_no, n.date, n.account_id, acc.account_name, n.details, n.amount "
            "FROM public_marts.normalize n "
            "JOIN public_refined.dim_account acc ON n.account_id = acc.account_id "
            "ORDER BY ABS(n.amount) DESC LIMIT %s"
        ) % limit

    # --- account detail ---
    if any(k in q for k in ["account", "dim_account", "chart of accounts"]):
        return (
            'SELECT account_id, "Report", "Class", "SubClass", account_name '
            "FROM public_refined.dim_account ORDER BY account_id LIMIT %s"
        ) % limit

    # --- raw GL rows ---
    if any(k in q for k in ["gl transactions", "raw", "posting"]):
        return (
            "SELECT entry_no, date, account_id, details, debit, credit, amount "
            "FROM public_marts.normalize ORDER BY date, entry_no LIMIT %s"
        ) % limit

    # --- date range / specific month ---
    # Try to extract a year-month like "2018-02" or "february 2018" or "mar 2018"
    import re as _re
    m = _re.search(r"(20\d{2})[/-](\d{1,2})", q)
    if m:
        y, mo = m.group(1), m.group(2).zfill(2)
        return (
            f"SELECT month, revenue, cogs, gross_profit, gross_profit_mom_pct "
            f"FROM public_marts.gross_profit_mom_variance "
            f"WHERE month >= '{y}-{mo}-01' AND month < '{y}-{mo}-01'::date + interval '1 month' "
            f"ORDER BY month LIMIT %s"
        ) % limit
    m = _re.search(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+(20\d{2})", q)
    if m:
        mon, y = m.group(1), m.group(2)
        months = {"jan":"01","feb":"02","mar":"03","apr":"04","may":"05","jun":"06",
                  "jul":"07","aug":"08","sep":"09","oct":"10","nov":"11","dec":"12"}
        mo = months[mon[:3]]
        return (
            f"SELECT month, revenue, cogs, gross_profit, gross_profit_mom_pct "
            f"FROM public_marts.gross_profit_mom_variance "
            f"WHERE month >= '{y}-{mo}-01' AND month < '{y}-{mo}-01'::date + interval '1 month' "
            f"ORDER BY month LIMIT %s"
        ) % limit

    # Unmatched — the question needs full LLM reasoning. Signal clearly.
    raise NotImplementedError(
        f"Question not covered by the built-in /ask mapper: {question!r}. "
        "Escalate to the finance-analyst_agent for LLM-generated SQL."
    )


def _narrate(question: str, rows: List[Dict[str, Any]], sql: str) -> str:
    """Produce a sourced natural-language answer from query rows.

    For the lightweight implementation we template the most common shapes.
    The finance-analyst agent produces richer narratives; /ask is the
    fast-path for straightforward questions."""
    if not rows:
        return f"No rows returned for: {question}"

    # Detect shape from keys and narrate accordingly.
    keys = set(rows[0].keys())

    if "gross_profit_mom_pct" in keys:
        # gross_profit_mom_variance shape
        parts = []
        for r in rows:
            month = r.get("month")
            gp = r.get("gross_profit")
            mom = r.get("gross_profit_mom_pct")
            rev = r.get("revenue")
            cogs = r.get("cogs")
            mom_s = f"{mom:+.2f}%" if isinstance(mom, (int, float)) and mom is not None else "n/a"
            parts.append(f"{month}: revenue={rev}, cogs={cogs}, GP={gp} ({mom_s} MoM)")
        return f"Answer for '{question}': " + "; ".join(parts) + "."

    if "account_class" in keys and "cumulative_amount" in keys:
        parts = [f"{r['month']} {r['account_class']}: {r['cumulative_amount']}" for r in rows]
        return f"Answer for '{question}': " + "; ".join(parts) + "."

    if "account_class" in keys and "net_amount" in keys and "total_debit" not in keys:
        parts = [f"{r['month']} {r['account_class']}: {r['net_amount']}" for r in rows]
        return f"Answer for '{question}': " + "; ".join(parts) + "."

    if "total_debit" in keys:
        parts = []
        for r in rows:
            imb = r.get("imbalance", 0)
            mark = " ⚠ IMBALANCED" if imb and abs(imb) > 0.01 else ""
            parts.append(f"{r['month']}: debit={r['total_debit']}, credit={r['total_credit']} (Δ={imb}){mark}")
        return f"Answer for '{question}': " + "; ".join(parts) + "."

    if "account_name" in keys and "ABS" in sql:
        parts = [f"{r.get('date')} {r.get('account_name')}: {r.get('amount')} ({r.get('details','')[:40]})" for r in rows[:5]]
        return f"Answer for '{question}' (top 5): " + "; ".join(parts) + "."

    # Generic fallback: echo the first few rows.
    preview = ", ".join(f"{k}={rows[0][k]}" for k in list(rows[0].keys())[:4])
    return f"Answer for '{question}': {len(rows)} rows. First: {preview}."


@app.post("/ask", summary="Natural-language Q&A over the warehouse (read-only SQL)")
@limiter.limit("30/minute")
def ask(request: Request, body: AskRequest):
    """
    Turn a natural-language question into a read-only SQL query, execute it,
    and return a sourced answer. The generated SQL is always echoed in the
    response so the answer is auditable.

    Safety: only SELECT/WITH/EXPLAIN are permitted. Write verbs are rejected
    with HTTP 400 before execution. This mirrors the pipeline-mcp read-only
    guard (server.py).
    """
    # 1. Generate SQL.
    try:
        sql = _generate_sql(body.question, body.limit)
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))

    # 2. Read-only guard (defense in depth — the mapper should only emit
    #    SELECT, but the guard is the real enforcement).
    if not is_read_only_sql(sql):
        raise HTTPException(
            status_code=400,
            detail="Generated SQL did not pass the read-only guard. "
                   "Only SELECT/WITH/EXPLAIN are permitted.",
        )

    # 3. Execute.
    try:
        rows = execute_read_only_query(sql)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query execution failed: {str(e)}")

    # 4. Narrate.
    answer = _narrate(body.question, rows, sql)

    return AskResponse(
        question=body.question,
        sql=sql,
        rows=rows,
        row_count=len(rows),
        answer=answer,
    )