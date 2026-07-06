# Pipeline Config Contract

This directory (`airflow/dags/pipelines/`) is the **source of truth** for the
`finance_etl_daily` Airflow DAG. The generated DAG file (`../finance_etl_daily.py`) is a
**build artifact** — do not hand-edit it.

## The rule

| Artifact | Role | Editable by |
|----------|------|-------------|
| `pipelines/finance_etl_daily.yml` | Source of truth (stages, models, schedule) | Humans, `pipeline-generator` agent |
| `pipelines/render_dag.py` | Renderer (YAML → DAG Python) | Humans only |
| `pipelines/CONTRACT.md` (this file) | Governance contract | Humans only |
| `airflow/dags/finance_etl_daily.py` | Generated DAG artifact | `render_dag.py` only |

## The stages schema

The config is a top-level `stages:` list. Each stage has a `type:`:

| `type` | What it emits | Notes |
|--------|---------------|-------|
| `python_callable` | `PythonOperator(task_id={id}, python_callable=extract_load)` | The extract/load callable is rendered inline at module top by the renderer when any `python_callable` stage is present. |
| `dbt_run` | `BashOperator(bash_command="dbt run")` | Full dbt run. |
| `dbt_test` | `BashOperator(bash_command="dbt test")` | Full dbt test. |
| `dbt_model` | one `BashOperator` per listed model | Requires a `models:` list; one task per model, chained in listed order. |

Per-stage SLA is `sla_minutes:` (integer). `default_args` uses `*_minutes` keys
(`retry_delay_minutes`, `max_retry_delay_minutes`, `execution_timeout_minutes`) which
the renderer converts to `timedelta(...)` — preferring the largest whole unit (so 60
minutes renders as `timedelta(hours=1)`).

## To add a new mart

1. Append the model name to the `models:` list under the `marts` stage
   (`type: dbt_model`) in `finance_etl_daily.yml`.
2. Run `python render_dag.py` to regenerate the DAG file.
3. Verify the diff: exactly one new `BashOperator` and one new link in the `>>` chain.
4. Commit both the YAML change and the regenerated DAG file.

## To add a new stage type

1. Add a new entry under `stages:` in the YAML with a unique `id` and a `type` from
   the table above plus its fields (`sla_minutes:`, `doc:`, and `models:` for
   `dbt_model`).
2. If the renderer doesn't yet support the new type, extend `render_dag.py`'s
   `_build_stages` function — but prefer reusing an existing type.
3. Re-render and verify the diff.

## Who does what

- **`pipeline-generator` agent**: edits the YAML + re-runs `render_dag.py`. MUST NOT
  hand-edit `finance_etl_daily.py`. The handoff-1 report should list the YAML edit
  and the rendered DAG diff as artifacts.
- **`data-engineer` agent**: validates the rendered DAG (compiles, balances, wires).
- **`airflow-expert` agent**: confirms scheduling and triggers runs.
- **Humans**: edit the YAML for manual changes (e.g., adjusting schedule, adding a
  new stage type, changing SLAs).

## Why

The previous approach — hand-editing the DAG Python for every new mart — created
near-duplicate BashOperators and a hard-coded chain that grew with each mart. Config-driven
generation means:

- Adding a mart is a one-line YAML change, not a Python edit.
- The dependency chain is derived, not hand-wired — no risk of mis-ordering.
- The renderer is testable: `render_dag.py --check` exits non-zero if the artifact
  drifts from the config.
- Governance tools (lineage, blast radius) can read the YAML to know what depends on
  what, without parsing Python.

## Verification

After any change to the YAML or the renderer:

```bash
# 1. Render and show diff
python render_dag.py --diff

# 2. Confirm the generated DAG parses (in the Airflow container)
docker compose exec airflow-webserver airflow dags list-import-errors

# 3. Idempotency: re-rendering unchanged config should skip the write
python render_dag.py    # prints "unchanged — skipping write"
```
