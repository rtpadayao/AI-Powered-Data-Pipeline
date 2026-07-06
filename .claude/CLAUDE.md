# Claude Code Configuration

This file defines the task-to-agent mapping, available commands, and rules/skills index for the AI-Powered Airflow financial data pipeline.

## Task → Agent Mapping

Use the appropriate agent for each task. Agents are specialized — picking the right one gives you deeper, more specific guidance.

This repo is the **pipeline runtime**. The agent layer (generation + orchestration)
lives in the sibling `airflow-agent-framework` repo; only the pipeline-runtime agents
are configured here.

| Task | Agent | Why |
|------|-------|-----|
| Generate pipeline artifacts from a financial request | `pipeline-generator` | NL → dbt mart + DAG + API. Lives in `airflow-agent-framework`. |
| Create/modify dbt models, macros, tests | `dbt-specialist` | Owns the entire dbt layer — staging, refined, marts |
| Build FastAPI endpoints, Pydantic schemas | `api-developer` | Owns the API layer |
| Develop Airflow DAGs, task dependencies | `airflow-expert` | Owns the orchestration layer |
| Integrate components, end-to-end pipeline flow | `data-engineer` | Cross-cutting concerns — glue between layers |

> **Removed (managing nothing real yet):** `database-admin`, `data-modeler`,
> `financial-modeling`, `fpa-accounting`, `dependency-mngr`, `housekeeper`,
> `markdown_agent`. Re-introduce only when there's real work for them to own.

## Available Commands

### Run & Develop
| Command | Purpose |
|---------|---------|
| `/run` | Local dev tasks — FastAPI server, dbt, Python scripts, Jupyter, psql, logs |
| `/run-pipeline` | Run the full data pipeline (extract → load → transform → docs) |

### Test & Validate
| Command | Purpose |
|---------|---------|
| `/dbt-run` | Run dbt models with testing and documentation |
| `/dbt-test` | Run dbt tests only (no model execution) |
| `/api-test` | Test FastAPI endpoints (functional, performance, security) |
| `/airflow-test` | Test and validate Airflow DAGs |
| `/stack-test` | Verify the Docker Compose stack is healthy end-to-end after bring-up |

## Rules (Prescriptive)

Short imperatives that define *what* must always hold. These are non-negotiable constraints.

| File | Scope |
|------|-------|
| `rules/python_rules.md` | Python data analysis patterns, pandas/polars, financial data processing |
| `rules/sql_rules.md` | SQL query writing, data modeling, database design |
| `rules/dbt_rules.md` | dbt SQL formatting, layering, model development |
| `rules/airflow_rules.md` | Airflow DAG development and orchestration |
| `rules/docker_compose_rules.md` | Docker Compose config, volume permissions, YAML pitfalls, healthchecks, port conflicts |

## Skills (Code Reference)

Executable code examples that show *how* to implement the rules. Skills complement rules — they don't duplicate them.

| File | Scope |
|------|-------|
| `skills/python.md` | Pandas, Polars, NumPy, Matplotlib, Excel integration, ML patterns |
| `skills/sql.md` | Query patterns, CTEs, window functions, schema design, ETL |
| `skills/dbt.md` | dbt operations, model configuration, testing, macros |
| `skills/airflow.md` | Airflow CLI, DAG patterns, operators, troubleshooting |
| `skills/fastapi.md` | FastAPI endpoints, Pydantic schemas, async patterns |
| `skills/postgres.md` | PostgreSQL connection, schema ops, indexing, backup, monitoring |
| `skills/docker.md` | Docker Compose commands, service management |

## Agent Directory

Pipeline-runtime agents (this repo):

| Agent | Scope | Owns |
|-------|-------|------|
| `pipeline-generator` | NL → pipeline artifacts | dbt marts, DAG tasks, API schemas/endpoints (from `airflow-agent-framework`) |
| `dbt-specialist` | dbt transformations | dbt models, macros, tests, schema.yml |
| `api-developer` | FastAPI development | endpoints, routers, Pydantic schemas |
| `airflow-expert` | Airflow orchestration | DAGs, operators, scheduling |
| `data-engineer` | Cross-cutting pipeline + infrastructure | end-to-end flow, integration, ingestion, Docker |

## Architecture

```
Extract (FastAPI) → Load (Postgres) → Transform (dbt) → Serve (API/BI)
      │                    │                   │                 │
      └────────────────────┴───────────────────┴─────────────────┘
                          Orchestrated by Airflow
```

| Layer | Component | Agent |
|-------|-----------|-------|
| Generate | NL → dbt + DAG + API | `pipeline-generator` (in `airflow-agent-framework`) |
| Extract | FastAPI endpoints | `api-developer` |
| Transform | dbt staging → refined → marts | `dbt-specialist` |
| Orchestrate | Airflow DAGs | `airflow-expert` |
| Infrastructure | Docker Compose, networking, volumes | `data-engineer` |
| Cross-cutting | Integration, data flow | `data-engineer` |

## Path Reference

Rules and skills are loaded automatically based on the file you're editing:

| Path | Rules Loaded | Skills Loaded |
|------|--------------|---------------|
| `api/**` | python_rules, sql_rules | python, sql, fastapi, postgres |
| `dbt_project/**` | python_rules, sql_rules, dbt_rules | python, sql, dbt, postgres |
| `airflow/dags/**` | python_rules, sql_rules, airflow_rules | python, sql, airflow |
| `infrastructure/**` | sql_rules | sql, postgres, docker |
| `notebooks/**` | python_rules | python |
| `docker-compose.yml` | docker_compose_rules | docker, postgres |
| `Dockerfile` | docker_compose_rules | docker |

## Day-One Bring-Up

When starting the stack for the first time (or after a full teardown), run `/stack-test` to verify health. The most common failures and their fixes are documented in `rules/docker_compose_rules.md`.

## Naming Conventions

| Artifact | Convention | Example |
|----------|-----------|---------|
| Rules files | `{name}_rules.md` | `python_rules.md`, `sql_rules.md` |
| Skill files | `{name}.md` | `python.md`, `sql.md` |
| Agent files | `{name}_agent.md` | `dbt-specialist_agent.md`, `data-engineer_agent.md` |
| Commands | `{name}.md` | `dbt-run.md`, `run.md` |
| dbt staging models | `stg_<source>_<table>` | `stg_erp_transactions` |
| dbt refined models | `<dim\|fact>_<entity>` | `dim_customer`, `fact_sales` |
| dbt mart models | `<domain>_<purpose>` | `finance_reporting` |
| Postgres tables | `snake_case` | `gl_transactions` |
| Airflow DAGs | `snake_case` | `finance_etl_daily` |
