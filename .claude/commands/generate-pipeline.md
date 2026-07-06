---
name: generate-pipeline
description: >
  Drive the 3-agent handoff to turn a natural-language financial request into a
  running, queryable report. Use when an analyst asks for a report, mart, or metric
  (e.g. 'trial balance by month', 'aging analysis', 'P&L by cost center'). Invokes
  pipeline-generator → data-engineer → airflow-expert in sequence, passing a
  structured handoff report between each. The user can stop at any handoff to review
  before the next phase runs.
paths:
  - dbt_project/models/marts/**
  - airflow/dags/**
  - api/**
---

# Generate Pipeline (3-Agent Handoff)

Turn a **natural-language financial request** into a running, queryable report by
driving the three-agent orchestration defined in
`airflow-agent-framework/orchestration/handoff_protocol.md`.

This command is the **executable Phase 1 handoff**: one invocation runs all three
phases (generate → validate → operate), with a structured handoff report between
each and a review gate the user can stop at.

## Usage

```
/generate-pipeline "<natural-language request>"
```

Examples:
```
/generate-pipeline "Build me a trial balance by month"
/generate-pipeline "I need an aging analysis of receivables by account"
/generate-pipeline "Show me a P&L broken down by cost center"
```

The argument is the analyst's request verbatim. If the user ran `/generate-pipeline`
without an argument, ask them for the request before proceeding.

## The 3-Agent Chain

```
pipeline-generator  ──handoff 1──▶  data-engineer  ──handoff 2──▶  airflow-expert
   (writes artifacts)               (validates vs real DB)          (schedules + runs)
```

Each agent is a **subagent** invoked via the Agent tool. The key design: **the
handoff report is the contract**. Each agent receives the *previous* agent's report
as input, so it validates without re-deriving intent.

### Review gates (important)

After **handoff 1** (generate) and **handoff 2** (validate), PAUSE and present the
report to the user before invoking the next agent. This is the "reviewable before
run" property — generation and execution are deliberately separated. Say something
like: "Handoff 1 complete — artifacts written. Proceed to validation?" and wait.

You may run all three in one go only if the user explicitly says "run it all" or
"don't stop for review." Otherwise, stop at each gate.

---

## Phase 1 — Generate (pipeline-generator agent)

**Goal:** write the three artifacts (dbt mart, DAG task, API access) and produce the
handoff-1 report.

Invoke the `pipeline-generator_agent` subagent with a prompt containing:
- The analyst's exact request.
- The instruction to emit the three artifacts per the pipeline contract:
  - **dbt mart** at `dbt_project/models/marts/<name>.sql` — must `ref('normalize')`,
    never read staging/raw; case-quote `dim_account` columns (`"Class"`, `"Report"`,
    `"SubClass"`); header comment with purpose/grain/accounting rule.
  - **DAG task** in `airflow/dags/finance_etl_daily.py` — BashOperator running
    `dbt run --models <name>`, wired last in the dependency chain.
  - **API access** — add `<name>` to the `allowed_tables` list in
    `api/main.py`'s `/transactions/marts/{table_name}` endpoint.
- The instruction to output the **handoff-1 report** (artifacts_written,
  accounting_logic, base_model, correctness_check) as a fenced YAML block.
- The instruction to NOT run dbt, NOT trigger anything, NOT query the DB.

**After the subagent returns:** present the handoff-1 report to the user. Confirm
before moving to validation.

### Handoff 1 report shape (what you should see)

```yaml
artifacts_written:
  - type: dbt_mart
    path: dbt_project/models/marts/<name>.sql
    refs: [normalize, dim_account]
  - type: dag_task
    task_id: <name>_run
    bash_command: dbt run --models <name>
    dependency_chain: ... >> <name>_run
  - type: api_allowlist
    change: added "<name>" to allowed_tables
accounting_logic: ...
base_model: normalize
correctness_check:
  description: ...
  query: |
    SELECT ...
  success_criteria: ...
```

---

## Phase 2 — Validate (data-engineer agent)

**Goal:** validate the artifacts against the real database and produce the
handoff-2 report.

**Prereq:** the stack must be up. Before invoking, ensure postgres is healthy:
`docker compose ps postgres_db`. If it's not healthy, tell the user — validation
needs the DB.

Invoke the `data-engineer_agent` subagent with:
- The full handoff-1 report (copy it verbatim into the prompt).
- Instructions to run, IN ORDER:
  1. `cd /home/roy/repos/cc_AI-Powered_Airflow && docker compose run --rm dbt run`
     — confirm the new model builds (expect one more model than before).
  2. `docker compose run --rm dbt test` — confirm no regressions.
  3. The correctness_check query via
     `docker exec -i postgres_db psql -U postgres -d finance_demo -c "<query>"`
     (use literal `postgres`/`finance_demo` — `$POSTGRES_USER` is not set in this
     shell). **Report the actual numbers**, especially whether the accounting rule
     holds.
  4. Read `airflow/dags/finance_etl_daily.py` and confirm the new task + dependency
     chain.
  5. Read `api/main.py` and confirm the allow-list entry; optionally test with
     `curl http://localhost:8000/transactions/marts/<name>?limit=3`.
- Instructions to output the **handoff-2 report** (validation_results with
  dbt_compile/dbt_run/balance_check/dag_wiring/api_endpoint; failures list;
  artifacts_confirmed) as a fenced YAML block.
- Instruction to REPORT HONESTLY — if the accounting rule doesn't hold, give the
  actual discrepancy and analyze whether it's a model bug or unbalanced source data.

**After the subagent returns:** present the handoff-2 report. If `failures` is empty
and the user confirms, proceed to operate. If there are failures, STOP and discuss
with the user — do not trigger a broken pipeline.

### Handoff 2 report shape (what you should see)

```yaml
validation_results:
  dbt_compile: pass
  dbt_run: pass (N/N models)
  dbt_test: pass (M/M)
  balance_check: pass | fail_with_finding
    root_cause: ...          # model bug vs unbalanced source data
    discrepancy: ...         # actual numbers
  dag_wiring: pass
  api_endpoint: pass | fail_preexisting
failures: [...]
artifacts_confirmed:
  - dbt_mart: public_marts.<name>
  - dag_task: <name>_run
  - api_allowlist: <name>
```

---

## Phase 3 — Operate (airflow-expert agent)

**Goal:** confirm scheduling, verify the DAG parses, and (if the user approves)
trigger the first run.

**Prereq:** Airflow services. Before invoking, ensure they're up:
`docker compose ps | grep airflow`. If `airflow-webserver`/`airflow-scheduler` are
not running, start them:
`docker compose up -d airflow-webserver airflow-scheduler` and wait for healthy.

Invoke the `airflow-expert_agent` subagent with:
- The full handoff-2 report.
- Instructions to:
  1. Read `airflow/dags/finance_etl_daily.py` and confirm the final dependency
     chain and the new task's position.
  2. Verify the DAG parses: `docker compose exec airflow-webserver airflow dags
     list-import-errors` (expect "No data found" / no errors). If there are import
     errors, FIX them in the DAG file (common: legacy import paths, removed
     operator params) and re-check — report what was fixed.
  3. Confirm the DAG-level schedule and default_args (schedule, retries, SLA).
  4. Output the **handoff-3 report** (dependency_chain, dag_parse status + any
     fixes, scheduling, final status) as a fenced YAML block.
- Instruction: do NOT trigger a DAG run unless the user explicitly says "trigger
  it" or "run it now." Default to confirming scheduling only.

**After the subagent returns:** present the handoff-3 report. If the user wants to
trigger the first run, use
`docker compose exec airflow-webserver airflow dags trigger finance_etl_daily`.

### Handoff 3 report shape (what you should see)

```yaml
dependency_chain: extract_load_task >> dbt_run >> dbt_test >> ... >> <name>_run
dag_parse: pass
  validation_method: Airflow live parse
  bugs_found_and_fixed: N
  fixes: [...]
  import_errors: 0
scheduling:
  schedule: @daily
  default_args: { retries: 3, retry_delay: 2 minutes, ... }
  <name>_run_sla: 15 minutes
status: scheduled | triggered
```

---

## Failure handling

- **Handoff 1 fails** (agent can't write artifacts): report the error; do not
  proceed to validation.
- **Handoff 2 fails** (model doesn't compile, or balance check fails): STOP. Show
  the failures. If it's a model bug, loop back to the pipeline-generator to fix it.
  If it's unbalanced source data, tell the user and let them decide whether to
  proceed.
- **Handoff 3 fails** (DAG import error): the subagent should fix common issues and
  re-check. If it can't, stop and report.

No broken artifact reaches a triggered run — each handoff boundary is a gate.

## Notes

- The `pipeline-generator` agent definition lives at
  `airflow-agent-framework/agents/pipeline-generator_agent.md` (symlinked into
  `.claude/agents/`). The `dbt-generator` skill at
  `.claude/skills/dbt-generator/` encodes the pipeline contract the generator
  follows — it's the "how to build dbt models" knowledge.
- The handoff protocol contract is at
  `airflow-agent-framework/orchestration/handoff_protocol.md`.
- All three agents are subagents — they run in isolation and return a final text
  report. That report is the handoff; pass it verbatim to the next agent.
