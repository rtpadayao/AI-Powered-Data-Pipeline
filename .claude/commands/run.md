---
name: run
description: Run local development tasks — FastAPI server, dbt models, Python scripts
paths:
  - api/**
  - dbt_project/**
  - notebooks/**
  - airflow/dags/
---

# Run Local Development Tasks

Quick commands for common local development tasks. Use these when working outside Docker or running individual components.

## Usage

```
/run <target> [options]
```

## Targets

### `api` — Start FastAPI development server

```bash
# Start with auto-reload (recommended for development)
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Start without reload (production-like)
uvicorn api.main:app --host 0.0.0.0 --port 8000

# Start on different port
uvicorn api.main:app --reload --port 8080
```

**Prerequisites:**
```bash
# Install dependencies first
pip install -r api/requirements.txt
# Or install directly
pip install fastapi uvicorn httpx pydantic sqlalchemy
```

**Access:** http://localhost:8000/docs (Swagger UI)

### `dbt` — Run dbt commands

```bash
# Run all models
docker compose run --rm dbt run

# Run specific model
docker compose run --rm dbt run --models <model_name>

# Run with model selector (supports wildcards)
docker compose run --rm dbt run --models stg_*
docker compose run --rm dbt run --models dim_customer+
docker compose run --rm dbt run --models tag:finance

# Run tests
docker compose run --rm dbt test
docker compose run --rm dbt test --models <model_name>

# Generate docs
docker compose run --rm dbt docs generate
docker compose run --rm dbt docs serve  # starts docs site at 8080

# Debug configuration
docker compose run --rm dbt debug

# List models
docker compose run --rm dbt ls

# Compile without executing (validate SQL)
docker compose run --rm dbt compile

# Run with variables
docker compose run --rm dbt run --vars '{"start_date": "2024-01-01"}'

# Full refresh (rebuild incremental models from scratch)
docker compose run --rm dbt run --full-refresh
```

### `python` — Run a Python script

```bash
# Run a script
python path/to/script.py

# Run with arguments
python path/to/script.py --arg1 value1

# Run a module
python -m module.name

# Run with IPython for interactive debugging
ipython -i path/to/script.py
```

### `notebook` — Start Jupyter

```bash
# Start JupyterLab
jupyter lab notebooks/

# Start classic notebook
jupyter notebook notebooks/

# Start with specific port
jupyter lab notebooks/ --port 8888
```

### `airflow` — Run Airflow commands

```bash
# List DAGs
docker compose exec airflow-webserver airflow dags list

# Trigger a DAG
docker compose exec airflow-webserver airflow dags trigger <dag_id>

# Test a specific task
docker compose exec airflow-webserver airflow tasks test <dag_id> <task_id> <execution_date>

# View task logs
docker compose exec airflow-webserver airflow tasks logs <dag_id> <task_id> <execution_date>

# Check DAG run status
docker compose exec airflow-webserver airflow dags list-runs <dag_id>

# Pause/unpause a DAG
docker compose exec airflow-webserver airflow dags pause <dag_id>
docker compose exec airflow-webserver airflow dags unpause <dag_id>
```

### `psql` — Connect to PostgreSQL

```bash
# Connect via Docker
docker compose exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB

# Run a query directly
docker compose exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT COUNT(*) FROM finance.gl_transactions;"

# Run a SQL file
docker compose exec -T postgres psql -U $POSTGRES_USER -d $POSTGRES_DB < query.sql
```

### `logs` — View service logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f postgres
docker compose logs -f airflow-webserver
docker compose logs -f airflow-scheduler
docker compose logs -f dbt

# Last N lines
docker compose logs --tail=100 postgres
```

### `shell` — Open a shell in a service

```bash
# PostgreSQL shell
docker compose exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB

# Airflow shell
docker compose exec airflow-webserver bash

# dbt shell
docker compose run --rm dbt bash
```

## Common Workflows

### Start developing the API
```
/run api
# In another terminal:
/run notebook
```

### Debug a dbt model
```
/run dbt --models <model_name>
# If error:
docker compose run --rm dbt debug
docker compose run --rm dbt compile
```

### Run a one-off script
```
/run python scripts/my_analysis.py
```

### Check database state
```
/run psql
# Then run SQL queries
```

### Full local test
```
/run python scripts/extract_load.py
/run dbt
/run dbt test
```
