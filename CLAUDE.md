# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Start

### Prerequisites
- Docker Engine 29.x running in WSL2 (Ubuntu 24.04) — **not** Docker Desktop; `docker` is on PATH directly
- Ports: 8000 (FastAPI), 5050 (pgAdmin), 5432 (Postgres internal), and 8080 or 8081 for Airflow (see note below)
  - **Common gotcha:** Windows `AgentService.exe` (PID varies) often occupies :8080. Before assuming a compose error, check with `cmd.exe /c "netstat -ano | findstr :8080"`. If occupied, compose currently maps Airflow to **8081**; adjust if you change this.

### Environment Setup
1. `.env` is already populated (committed for this demo project). For other setups, copy `.env.example` to `.env` and fill in real values — especially `AIRFLOW_FERNET_KEY` (44-char base64) and `AIRFLOW_SECRET_KEY` (64-char hex). Placeholders like `your_fernet_key_here...` will cause `airflow db migrate` to fail or webserver logins to reject.

2. Start the full stack:
   ```bash
   docker compose up -d
   ```

3. Verify health (important — see "Bring-Up Verification" below):
   ```bash
   docker compose ps
   ```

4. Stop the stack:
   ```bash
   docker compose down
   ```

### Service-Specific Commands
- **Initialize Airflow database and admin user** (runs automatically on first `up -d` via `airflow-init` service; one-shot, exits 0 on success):
  ```bash
  docker compose up airflow-init
  ```

- **Run dbt transformations** (as a one-off):
  ```bash
  docker compose run --rm dbt run
  docker compose run --rm dbt test
  docker compose run --rm dbt docs generate
  ```

- **Access services**:
  - Airflow UI: http://localhost:8081 (remapped from default 8080 due to Windows port conflict)
  - pgAdmin: http://localhost:5050 (credentials from `.env`)
  - FastAPI docs: http://localhost:8000/docs
  - Postgres: localhost:5432 (internal only; use pgAdmin or add port mapping in compose for direct access)

### Bring-Up Verification

After `docker compose up -d`, confirm the stack is actually healthy — not just "containers running". The day-one bring-up has several non-obvious failure modes; see `.claude/rules/docker_compose_rules.md` for the full list.

Quick health check:
```bash
docker compose ps
```

Expected healthy state:
- `postgres_db` → `healthy`
- `airflow_scheduler` → `healthy`
- `airflow_webserver` → `healthy`
- `fastapi_app` → `healthy`
- `pgadmin_gui` → `Up`
- `airflow_init` → `Exited (0)` (one-shot, success)
- `dbt_core` → `Exited (0)` or `Started` (one-shot)

Any `unhealthy`, `restarting`, or `Exited (1)` → investigate with `docker compose logs --tail=30 <service>`.

Then hit the UIs in a browser to confirm traffic flows: Airflow (`:8081`), FastAPI docs (`:8000/docs`), pgAdmin (`:5050`).

Common failure signatures (see `rules/docker_compose_rules.md` for fixes):

| Symptom | Likely cause |
|---------|-------------|
| `airflow_init` `Restarting (127)` | YAML `command:` folding broke the bash command — rebuild `--no-cache` |
| `airflow_init` `PermissionError` on `./airflow/logs` | Volume not owned by uid 50000 — `sudo chown -R 50000:0 airflow/logs airflow/dags airflow/plugins` |
| `fastapi_app` `unhealthy` but `:8000/health` returns 200 from host | `curl` missing from image — install in Dockerfile |
| `fastapi_app` `Restarting (1)` with `ImportError: attempted relative import` | Relative imports in `main.py` — use absolute imports |
| `airflow_webserver` fails to start, port conflict | Host port occupied — remap in compose or free the port |
| Build fails: `target stage "development" could not be found` | Dockerfile missing the named stage |

## Development Workflow

### Airflow
- DAGs are located in `airflow/dags/`
- Mounted into the container; changes appear immediately in the webserver (if containers are restarted or touch the file to trigger reload)
- To develop a new DAG:
  1. Add Python file to `airflow/dags/`
  2. Restart the webserver/scheduler or touch the file to trigger a reload:
     ```bash
     docker compose restart airflow-webserver airflow-scheduler
     ```
  3. View logs:
     ```bash
     docker compose logs -f airflow-webserver
     docker compose logs -f airflow-scheduler
     ```

### dbt (Data Transformation)
- dbt project lives in `dbt_project/` (mounted into the dbt service)
- Profiles are in `dbt_project/profiles.yml` (mounted read-only)
- Commands are run via `docker compose run --rm dbt <command>`
- Common dbt workflow:
  - Build models: `docker compose run --rm dbt run`
  - Test models: `docker compose run --rm dbt test`
  - Generate docs: `docker compose run --rm dbt docs generate`
  - Seed data: `docker compose run --rm dbt seed`
  - Run specific models: `docker compose run --rm dbt run --models <model_name>`
- dbt models are organized in layers:
  - `staging/`: source-centric, cleaned data
  - `refined/`: business rules, master data
  - `marts/`: domain-centric, ready for consumption

### FastAPI
- The API service is defined in `api/` (compose `build.context: ./api`, volume `./api:/app`)
- Entrypoint: `api/main.py` with `app = FastAPI()`; run via `uvicorn main:app`
- Imports in `main.py` are **absolute** (`from schemas import ...`, not `from .schemas`) because uvicorn launches the module directly, not as a package
- To run the API locally (outside Docker) for development:
  ```bash
  # Install dependencies
  pip install -r api/requirements.txt
  
  # Run the server
  uvicorn main:app --reload --host 0.0.0.0 --port 8000
  ```
- API endpoints are defined in `api/main.py` (Pydantic schemas in `api/schemas.py`, DB helpers in `api/database.py`).
- Use asynchronous HTTPX calls for external interactions.

### Notebooks
- Exploratory analysis lives in `notebooks/`
- Jupyter notebooks can be run with:
  ```bash
  jupyter lab notebooks/
  ```
- Specific requirements for profiling are in `notebooks/requirements.txt`

## Testing

### Airflow
- No specific test suite observed; validate DAGs by:
  - Running `airflow dags test <dag_id> <execution_date>` inside the webserver/scheduler container
  - Triggering DAGs via UI and checking logs

### dbt
- Tests are defined in `dbt_project/models/**/*_test.yml` or as schema tests
- Run all tests:
  ```bash
  docker compose run --rm dbt test
  ```
- Run tests for a specific model:
  ```bash
  docker compose run --rm dbt test --models <model_name>
  ```

### FastAPI
- Tests are in `api/test_api.py`
- Run with pytest:
  ```bash
  pytest api/
  ```

### General
- Linting/formatting: if configured, use tools like `flake8`, `black`, `isort`. Check for config files (`.flake8`, `pyproject.toml`, etc.).
- No general test command observed; run component-specific tests as above.

## Project Architecture

### High-Level Data Flow
1. **Ingestion**: Raw data landed in `infrastructure/raw_storage/` (CSV files, etc.)
2. **Extract/Load**: A script (`api/extract_load.py`) pulls data from the FastAPI endpoint (or other sources) and loads into PostgreSQL.
3. **Orchestration**: Airflow DAGs schedule and monitor tasks, including triggering dbt runs.
4. **Transformation**: dbt models transform raw data through staging → refined → marts layers.
5. **Consumption**: Transformed data is available in Postgres for querying or served via the FastAPI API.

### Directory Purposes
- `airflow/`: Contains DAGs, logs, and custom plugins. Manages workflow orchestration.
- `dbt_project/`: dbt transformation project. SQL models, macros, seeds, and tests.
- `api/`: FastAPI application for serving data and providing an extract/load interface.
- `infrastructure/`:
  - `postgres/init-db.sql`: Scripts to initialize schemas/database objects.
  - `raw_storage/`: Immutable source data for reproducibility.
- `notebooks/`: Exploratory data analysis and profiling.
- `.claude/`: Claude Code customizations (agents, commands, rules, skills).

### Key Configuration Files
- `docker-compose.yml`: Defines all services, networks, volumes.
- `.env`: Environment variables for services (not committed; see `.env.example` if present).
- `dbt_project/profiles.yml`: dbt connection profiles (mounted into dbt container).
- `dbt_project/dbt_project.yml`: dbt project configuration.

## Common Commands Reference

| Purpose | Command |
|---------|---------|
| Start all services | `docker compose up -d` |
| Stop all services | `docker compose down` |
| View service logs | `docker compose logs -f <service_name>` |
| Restart a service | `docker compose restart <service_name>` |
| Run a one-off dbt command | `docker compose run --rm dbt <command>` |
| Access Postgres CLI (if port exposed) | `psql -h localhost -U $DB_USER -d $DB_NAME` |
| Access pgAdmin | Browse to http://localhost:5050 |
| Trigger Airflow DAG via CLI | `docker compose exec airflow-webserver airflow dags trigger <dag_id>` |
| List Airflow DAGs | `docker compose exec airflow-webserver airflow dags list` |
| Run FastAPI tests | `pytest api/` |
| Run dbt docs serve | `docker compose run --rm dbt docs serve` |

## Claude Code Specifics

### Agent Commands
Check `.claude/commands/` for custom slash commands.

### Rules
- Path-specific lazy-loaded rules exist in `.claude/rules/` (e.g., `dbt_rules.md`, `python_rules.md`, `sql_rules.md`, `airflow_rules.md`, `docker_compose_rules.md`).
- These provide guidance when editing files in those directories.

### Skills
- Specialized skills are installed in `.claude/skills/` (e.g., `dbt.md`, `airflow.md`, `docker.md`, `fastapi.md`, `postgres.md`, `python.md`, `sql.md`).

### Subagents
- For complex tasks, invoke subagents via the Agent tool (e.g., `dbt-specialist`, `airflow-expert`, `data-engineer`).

### Agent Framework

This repo is the **pipeline runtime** (Airflow, dbt, FastAPI, Postgres). The
**agent layer** — agents that generate pipeline artifacts, MCP servers, and the
orchestration protocol — lives in the sibling repo:
- Path: `/home/roy/repos/airflow-agent-framework/`
- The `pipeline-generator` agent is symlinked into `.claude/agents/` from there.
- The `pipeline-mcp` server can be registered in Claude Code's `settings.json`
  to give agents (and Claude) direct access to dbt/Airflow/psql operations.

See the agent framework's README for the full 3-agent handoff protocol.

---
*This guide is intended to accelerate onboarding and reduce context-switching. Keep it updated as the project evolves.*
