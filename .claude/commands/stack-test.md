---
name: stack-test
description: Verify the Docker Compose stack is healthy end-to-end after bring-up
paths:
  - /
---

# Stack Bring-Up Test

Run this after `docker compose up -d` to verify the whole stack is actually working — not just "containers running", but serving traffic. This is the day-one verification that catches the non-obvious failure modes documented in `rules/docker_compose_rules.md`.

## Usage

```
/stack-test
```

## What It Checks

### 1. Container health

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

### 2. Service endpoints

```bash
# FastAPI health
curl -s -o /dev/null -w 'FastAPI /health: HTTP %{http_code}\n' http://localhost:8000/health

# Airflow health (container-internal)
docker compose exec airflow-webserver curl -s -o /dev/null -w 'Airflow /health: HTTP %{http_code}\n' http://localhost:8080/health

# Postgres
docker compose exec postgres pg_isready -U ${POSTGRES_USER:-postgres}
```

### 3. Browser UIs

Open in a browser (use the remapped ports if you changed them):
- Airflow UI: `http://localhost:8080` (or current remap, e.g. `:8081`)
- FastAPI docs: `http://localhost:8000/docs`
- pgAdmin: `http://localhost:5050`

### 4. Common failure signatures

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `airflow_init` `Restarting (127)` | YAML `command:` folding broke the bash command | Write command as single line; rebuild `--no-cache` |
| `airflow_init` `PermissionError` on `./airflow/logs` | Volume not owned by uid 50000 | `sudo chown -R 50000:0 airflow/logs airflow/dags airflow/plugins` |
| `fastapi_app` `unhealthy` but `:8000/health` returns 200 from host | `curl` missing from image | Install curl in Dockerfile |
| `fastapi_app` `Restarting (1)` with `ImportError: attempted relative import` | Relative imports in `main.py` | Change to absolute imports |
| `airflow_webserver` fails to start, port conflict | Host port occupied (e.g. Windows AgentService on :8080) | Remap to `"8081:8080"` in compose |
| Build fails: `target stage "development" could not be found` | Dockerfile missing the named stage | Add `FROM base AS development` stage |

## See Also

- `/run-pipeline` — run the full data pipeline (requires a healthy stack)
- `/dbt-run` — run dbt transformations
- `/api-test` — test FastAPI endpoints
- `/airflow-test` — test Airflow DAGs
- `/run` — local dev tasks
