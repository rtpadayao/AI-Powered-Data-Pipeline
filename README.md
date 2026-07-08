# Financial Data Platform

An end-to-end data pipeline that ingests multi-source financial data, transforms it through a layered warehouse architecture, and serves it via a secure API for business intelligence consumption.

Built for production. Designed to scale.

---

## Architecture Overview

![Architecture Overview](docs/architecture_overview.svg)

**Data flow:** Sources → Ingestion & Validation (FastAPI) → Staging (Postgres) → Transformation (dbt: staging → refined → marts) → Serving Layer (FastAPI) → BI Tools

**Orchestration:** Airflow schedules and monitors the entire pipeline with retry logic, SLAs, and failure handling.

---

## What I Built

### 1. Pluggable Ingestion Layer
- **Adapter pattern** (`api/adapters/base.py`) allows the pipeline to ingest from any source — CSV, PDF, Excel, REST API, or database — without modifying core pipeline code.
- Each adapter validates schema, transforms rows to a common financial ledger format, and reports lineage metadata.
- This means a new data source can be onboarded in hours, not days.

### 2. Dual-Role FastAPI Service
- **Ingestion Gateway:** Validates, authenticates, and preprocesses incoming data before it touches the database. Rate-limited and secured with security headers.
- **Serving Layer:** Exposes dbt-transformed marts (trial balance, P&L, balance sheet, MoM variance) to BI tools via clean REST endpoints with pagination.

### 3. dbt Data Warehouse (Medallion Architecture)
- **Staging:** Source-centric views that clean and type-cast raw data. Lightweight — always reflects the latest source data.
- **Refined:** Business rules, slowly-changing dimensions (SCD-ready `dim_account`, `dim_date`), and the core fact table (`fact_gl_transactions`). Materialized incrementally for performance.
- **Marts:** Domain-ready analytical models — `trial_balance_by_month`, `income_statement_by_month`, `balance_sheet_by_month`, `gross_profit_mom_variance`, `account_aging`.

### 4. Airflow Orchestration
- Daily DAG (`finance_etl_daily`) orchestrates extract → load → dbt run → dbt test → mart rebuild.
- Config-driven: DAG is generated from YAML, making schedule and task logic version-controlled and readable.
- Built-in resilience: retries with exponential backoff, skip-on-empty logic, and SLA monitoring.

### 5. AI-Powered Natural Language Interface
- `/ask` endpoint converts plain-English financial questions into read-only SQL queries.
- Read-only guard prevents destructive operations. Schema primer ensures the LLM understands the warehouse structure.
- Complex questions escalate to an LLM agent for deeper reasoning.

---

## Technology Stack

| Layer | Tool | Why |
|---|---|---|
| Orchestration | Apache Airflow | Industry standard for DAG scheduling, retries, and observability |
| Transformation | dbt | SQL-first transformations with testing, documentation, and lineage |
| API | FastAPI | Async, auto-documented, type-safe Python API |
| Database | PostgreSQL | Reliable, open-source, excellent analytical query performance |
| Containerization | Docker & Docker Compose | One-command local setup, consistent environments |
| AI Integration | Claude Code / LLM agents | Natural language interface, code generation, and agent orchestration |

---

## Key Design Decisions

### Why the adapter pattern for ingestion?
Businesses accumulate data from multiple systems over time. Hard-coding connectors means rewrites every time a new source appears. The adapter pattern abstracts extraction so the pipeline core remains stable while sources change.

### Why incremental materializations for refined and marts?
Financial data grows. Rebuilding the entire warehouse every run is inefficient and expensive. Incremental models only process changed data, keeping runtime and cost predictable.

### Why FastAPI for both ingestion and serving?
A single API surface reduces operational overhead. The ingestion path enforces schema and validation Tribuna at the boundary. The serving path exposes only curated marts, preventing BI tools from querying raw or intermediate tables directly.

### How are failures handled?
- Empty API responses skip the dbt run (no wasted compute).
- Airflow retries failed tasks with exponential backoff.
- dbt tests catch data quality issues before marts are rebuilt.
- Postgres transactions ensure atomic loads — no partial data.

---

## Reproduction Steps

```bash
# 1. Clone and start the stack
docker compose up -d

# 2. Verify all services are healthy
docker compose ps

# 3. Trigger the pipeline manually
docker compose exec airflow-webserver airflow dags trigger finance_etl_daily

# 4. Access services
# Airflow UI:    http://localhost:8081
# FastAPI docs:  http://localhost:8000/docs
# pgAdmin:       http://localhost:5050
```

---

## What This Demonstrates

- **System design:** Building composable, production-ready data systems
- **Software engineering:** Clean abstractions (adapters), separation of concerns, type safety
- **Data engineering:** ETL/ELT pipelines, dimensional modeling, incremental processing
- **DevOps:** Docker, container orchestration, health checks, environment management
- **AI integration:** LLM-powered interfaces with safety guards and schema awareness

---

## Contact

[[Email](padayao.roy@gmail.com)] | [[LinkedIn](www.linkedin.com/in/roytp)] | [[GitHub](https://github.com/rtpadayao)]

Open to remote data engineering, analytics engineering, and backend engineering roles.
