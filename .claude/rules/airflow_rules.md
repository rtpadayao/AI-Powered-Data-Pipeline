---
  name: airflow
  description: Rules for Airflow DAG development and orchestration
  paths:
    - airflow/**
---

# Airflow Development Rules

These are non-negotiable constraints when working on Airflow DAGs. The agent and skill files provide the "how" — this file defines the "what" that must always hold.

## Required Conventions

### File & Naming
- All DAGs live in `airflow/dags/`
- DAG files follow `<domain>_<process>_<frequency>.py` (e.g., `finance_etl_daily.py`)
- DAG IDs must be descriptive and match the file purpose

### DAG Design
- Each DAG must have a single, clear business purpose
- Tasks must be idempotent (safe to retry)
- Use TaskGroups for organizing related tasks in complex DAGs
- Set realistic `start_date` — avoid dates far in the past
- DAGs must have a `schedule_interval` (or `schedule` in Airflow 2.4+)

### Task Implementation
- Use `>>` and `<<` for dependency chains (no `set_upstream`/`set_downstream`)
- Every DAG must define `default_args` with at minimum: `owner`, `retries`, `retry_delay`
- Use trigger rules explicitly for any non-default branching (`one_success`, `one_failed`, etc.)
- Never store credentials or secrets in DAG code — use Connections/Variables
- Close resources (connections, file handles) in `finally` blocks or context managers

### Testing & Validation
- Every DAG must pass `airflow dags test <dag_id> <execution_date>` before commit
- Test failure scenarios for DAGs with branching or external dependencies
- Validate with realistic data volumes when tasks interact with databases

### Security
- Use Airflow Connections for all credentials (never hardcoded)
- Use Airflow Variables for non-secret configurable parameters
- Apply least-privilege to service accounts used by Airflow
- Enable Fernet encryption for sensitive Variable values

## Development Workflow

1. Create or edit DAG in `airflow/dags/`
2. Validate syntax: `docker compose exec airflow-webserver airflow dags test <dag_id> <execution_date>`
3. Restart to pick up changes: `docker compose restart airflow-webserver airflow-scheduler`
4. Monitor: `docker compose logs -f airflow-scheduler`
