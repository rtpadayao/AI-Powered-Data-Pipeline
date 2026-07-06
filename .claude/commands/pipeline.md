---
name: pipeline
description: >
  Natural-language operator CLI for the cc_AI-Powered_Airflow pipeline. A thin intent
  layer over the pipeline-mcp tools — parses a plain-English operator request and calls
  the matching MCP tool(s), then formats the response as compact, readable output. Use
  for day-to-day operation: "run the finance ETL", "what's the status?", "why did
  yesterday's run fail?", "show lineage of <model>", "what does governance require for
  <model>?", "run dbt model X". NOT for generating new artifacts — that's
  /generate-pipeline. Calls MCP tools directly; does not spawn subagents.
---

# /pipeline — NL Operator CLI

This is the **executable Phase 3 Pillar 3 thin intent layer**: a natural-language
wrapper around the `pipeline-mcp` tools. The MCP surface already has everything an
operator needs; this command adds intent-parsing + pretty output. It does **not**
generate artifacts (use `/generate-pipeline`) or spawn subagents — it calls the
registered `pipeline-mcp` tools directly.

## Usage

```
/pipeline "<natural-language operator request>"
```

Examples:
```
/pipeline "run the finance ETL"
/pipeline "what's the status of finance_etl_daily?"
/pipeline "why did the last finance_etl_daily run fail?"
/pipeline "show me the lineage of account_aging"
/pipeline "what does governance require before I promote account_balances?"
/pipeline "file a signoff for account_aging — dbt_compile: pass, dbt_run: pass, balance_check: pass, dag_wiring: pass, api_endpoint: pass"
/pipeline "run the dbt model trial_balance_by_month"
/pipeline "ask: do debits equal credits in the GL?"
```

The argument is the operator's request verbatim. If the user ran `/pipeline` with no
argument, or the intent is ambiguous, ask **one** clarifying question before calling
any tool.

## Intent → MCP-tool map

Parse the request against these verbs and call the matching `pipeline-mcp` tool(s).
Tool names are the MCP tool identifiers (registered in `.claude/settings.json`), invoked
with the named arguments shown.

| Intent (NL) | MCP call(s) | Notes |
|-------------|-------------|-------|
| "run / trigger the finance ETL / the pipeline" | `airflow_trigger(dag_id="finance_etl_daily")` | The governance gate (Pillar 1) refuses unless signoffs are on file — if `ok` is false and `governance.missing_artifacts` is present, surface that list in plain English and suggest `/pipeline "file signoff for <model>"`. Do **not** auto-pass `force=True`; only set it if the user explicitly asked to bypass the gate. |
| "status of <dag>" / "is <dag> healthy" / "did it finish?" | `airflow_dag_status(dag_id=<dag>)` | If no DAG is named, call `airflow_list_dags()` first to disambiguate. Summarize the latest run's `state` and `execution_date`. |
| "why did <dag> fail" / "what happened on yesterday's run" / "diagnose the last failure" | `airflow_dag_status` → find the failed task (`state=="failed"`) and its `run_id` → `airflow_task_log(dag_id, task_id, run_id=<run_id>, execution_date=<logical_date>)` → `classify_dbt_failure(stderr=<log>)` | This is the **self-healing chain**. Report the failed task, the classifier's `class` (transient/hard/unknown), its `action` (retry/alert/investigate), and a one-line plain-English reading. Transient → "Airflow's backoff will retry; this is expected." Hard → "This is a compilation/schema bug — fix the model." Unknown → "Novel failure — needs human investigation." |
| "lineage / blast radius of <model>" / "what depends on <model>" | `dbt_manifest(action="lineage", model=<model>)` | Report `upstream` and `downstream` lists. |
| "what does governance require for <model>" / "can I promote <model>?" | `governance_check(artifact=<model>, change_type="modify")` | Report `required`, `satisfied`, `missing`, `blast_radius`, `approved`. If not approved, list the missing validations. |
| "file (a) signoff for <model>" / "approve <model>" | `governance_submit(report={artifacts:[<model>], validation:{...}, approved_by:<user>})` then `governance_check(artifact=<model>)` to confirm | Parse the validation checks from the request (the `required_validations` are `dbt_compile, dbt_run, balance_check, dag_wiring, api_endpoint`). Confirm `approved=True` afterward. |
| "run dbt model <X>" / "build <X>" | `dbt_run(models=<X>)` | Optionally `dbt_test(models=<X>)` after if the user asked to test too. |
| "test dbt model <X>" | `dbt_test(models=<X>)` | |
| "query <SQL>" / "ask <question about the data>" | `psql_query(sql=<SQL>)` | Translate an "ask" question to a read-only SELECT/WITH/EXPLAIN query yourself, then call `psql_query`. The server enforces the read-only guard. Never fabricate a write query. |

If the request matches none of these, say so and list the recognized verbs in one line.

## Output format

Keep it compact and operator-facing:
- **Status / trigger**: one line for the run state (or the gate refusal + missing list).
- **Why-failed**: failed task → class → plain-English reading. Include the matched
  `signatures` only if the user asked for detail.
- **Lineage / governance**: bulleted lists for `upstream`/`downstream` and
  `required`/`satisfied`/`missing` — these are sets the operator scans.
- **Data query**: render `rows` as a small table or JSON, truncated to ~20 rows with a
  count.

Never dump raw tool JSON when a one-line reading will do. The point of the CLI is
intent → readable answer, not a protocol dump.

## Boundaries (what /pipeline is NOT)

- It does **not** generate dbt models, DAG tasks, or API endpoints — that is
  `/generate-pipeline` (the 3-agent artifact flow). If the request is "build me a mart
  for X", tell the user to run `/generate-pipeline` instead.
- It does **not** spawn subagents. Direct MCP calls only.
- It does **not** bypass the governance gate unless the user explicitly asks to force.
- It does **not** retry Airflow tasks itself — Airflow's own backoff handles retries;
  the classifier only *explains* whether a failure is the kind Airflow will retry.
