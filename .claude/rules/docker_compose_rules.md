---
  name: docker_compose
  description: Rules for Docker Compose configuration and day-one bring-up
  paths:
    - docker-compose.yml
    - Dockerfile
    - .env
---

# Docker Compose Rules

Non-negotiable constraints for this project's container stack. These are the failure modes that actually bite on day one — each one was hit during bring-up and is documented here so future sessions don't rediscover them.

## Build & Image

- **Multi-stage Dockerfile targets must match `build.target` in compose.** If compose says `target: development`, the Dockerfile must declare `FROM base AS development`. A missing target fails the build with `target stage "development" could not be found`.
- **Healthcheck tools must exist in the image.** This project's FastAPI healthcheck uses `curl`, but `python:3.11-slim` ships without it. Install with `apt-get install -y --no-install-recommends curl` in the Dockerfile, or switch the healthcheck to a tool that exists. A container that is `Up` and serving traffic from the host but reports `unhealthy` almost always has this mismatch.
- **CMD must match the actual entrypoint.** The FastAPI app is `main.py` with `app = FastAPI()`, so CMD is `["uvicorn", "main:app", ...]` — not `app.py` or a module path that doesn't exist.

## Python Module Imports

- **Use absolute imports in files launched directly by uvicorn.** This project runs `uvicorn main:app` (module mode, not package mode), so relative imports like `from .schemas import ...` fail with `ImportError: attempted relative import with no known parent package`. Always write `from schemas import ...`, `from database import ...`. This applies to `api/main.py` and any file uvicorn targets directly.
- Relative imports are only safe in modules that are themselves imported by an entrypoint, never in the entrypoint itself.

## Volumes & Permissions

- **Airflow runs as uid 50000** (`user: "${AIRFLOW_UID:-50000}:0"` in compose). Any host directory it writes to (`./airflow/logs`, `./airflow/dags`, `./airflow/plugins`) must be owned by uid 50000, or you get `PermissionError: [Errno 13] Permission denied`. Fix:
  ```bash
  sudo chown -R 50000:0 airflow/logs airflow/dags airflow/plugins
  ```
- **Bind-mounting a host path that doesn't exist** creates an empty directory owned by root — which the container can't write to. Ensure host dirs exist before `up -d`, or let compose create them and then `chown`.

## Environment & Secrets

- **`.env` secrets must be real, not placeholders.** `AIRFLOW_FERNET_KEY` must be a 32-byte base64 string (44 chars, ends with `=`); `AIRFLOW_SECRET_KEY` must be a random string. Placeholders like `your_fernet_key_here...` cause `airflow db migrate` to fail or the webserver to reject logins. Generate with:
  ```bash
  python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  python3 -c "import secrets; print(secrets.token_hex(32))"
  ```
- **An `.env.example` must exist** documenting every required variable, so new developers don't start from a broken `.env`.

## Compose `command:` Pitfalls

- **YAML folded blocks (`>`) collapse newlines to spaces — and a blank line becomes a paragraph break.** A multi-line `bash -c` command using `>` will split at any blank line, turning a flag like `--username` into a fresh command (`/bin/bash: line N: --username: command not found`). The fix is to write the whole bash command as a single physical line, or use the list form:
  ```yaml
  command:
    - bash
    - -c
    - airflow db migrate && airflow users create --username admin ... && echo done
  ```
- **After editing `docker-compose.yml`, rebuild with `--no-cache`** for the affected service, or compose may reuse a cached container with the old command.

## Ports & Networking

- **Host port conflicts fail `up -d`.** This project maps Airflow webserver to host port 8080 — but Windows `AgentService.exe` (and others) commonly occupy 8080. Before assuming a compose error, check the host: in PowerShell run `netstat -ano | findstr :8080` then `Get-Process -Id <PID>`. If the port is held by a system service, remap in compose (`"8081:8080"`) rather than killing the service. (Current state: remapped to 8081 because of AgentService.)
- **Container-internal ports stay the same when you remap the host port.** If compose is `"8081:8080"`, the healthcheck still uses `http://localhost:8080/health` (container-internal) — only the host URL changes.
- **This project runs in WSL2 (Ubuntu 24.04), not Docker Desktop.** `docker` is on PATH inside the WSL distro. To check host-side port usage from WSL: `cmd.exe /c "netstat -ano | findstr :8080"`.

## Bring-Up Verification

After `docker compose up -d`, verify before declaring success. Use the `/stack-test` command, or run the checks manually:
1. `docker compose ps` — all services `healthy` or `running` (one-shot services like `airflow-init` and `dbt` show `Exited (0)`, which is correct).
2. `docker compose logs --tail=20 <service>` for any service that's `unhealthy` or `restarting`.
3. Hit the UIs in a browser: Airflow (`:8080` or remapped port), FastAPI docs (`:8000/docs`), pgAdmin (`:5050`).
4. A container that's `Up` but `unhealthy` while its endpoint returns 200 from the host usually means the **healthcheck command is missing from the image** (see Build & Image above).
