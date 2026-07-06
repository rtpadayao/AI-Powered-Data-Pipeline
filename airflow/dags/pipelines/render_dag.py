#!/usr/bin/env python3
"""
DAG renderer — reads a pipeline YAML config and emits the corresponding Airflow DAG file.

This is the config-driven alternative to hand-editing DAG Python. The YAML config is the
source of truth; the generated DAG file is a build artifact.

Usage:
    python render_dag.py                    # emit airflow/dags/finance_etl_daily.py
    python render_dag.py --diff            # show diff vs current DAG (no write)
    python render_dag.py --check           # exit 1 if current DAG != rendered output

The renderer is idempotent: if the rendered output matches the existing file, no write
is performed (so re-rendering doesn't churn the artifact).

Schema (stages-based, per the Phase 3 blueprint):

    dag_id: <id>
    schedule: "<cron|preset>"
    start_date: "YYYY-MM-DD"
    default_args:
      owner: <str>
      retries: <int>
      retry_delay_minutes: <int>           # → timedelta(minutes=…)
      retry_exponential_backoff: <bool>
      max_retry_delay_minutes: <int>        # → timedelta(minutes=…)
      execution_timeout_minutes: <int>      # → timedelta(minutes=…)
    stages:
      - id: <stage_id>
        type: python_callable | dbt_run | dbt_test | dbt_model
        sla_minutes: <int>                  # optional, per-stage SLA
        doc: "<doc string>"                 # optional
        models: [<model>, ...]              # required for dbt_model
        doc_template: "Rebuild the {model} mart (generated artifact)."  # optional

Stages run in listed order; within a dbt_model stage, models chain in listed order.
For python_callable, the task variable defaults to ``{id}_task`` (avoids colliding
with the extract_load callable defined at module top); set ``var:`` to override.

Runtime deps: pyyaml (standard in Airflow's venv; pip install pyyaml bare-metal).
No Jinja2 — the DAG structure is rigid enough for plain string building.
"""

import argparse
import difflib
import sys
from datetime import timedelta
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("pyyaml is required. Install with: pip install pyyaml")


# ---------------------------------------------------------------------------
# Config paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = SCRIPT_DIR / "finance_etl_daily.yml"
DAG_DIR = SCRIPT_DIR.parent
DEFAULT_OUTPUT = DAG_DIR / "finance_etl_daily.py"


# ---------------------------------------------------------------------------
# Schema constants
# ---------------------------------------------------------------------------
VALID_TYPES = {"python_callable", "dbt_run", "dbt_test", "dbt_model"}

# default_args keys that carry a per-minute integer and must render as timedelta.
# Maps config key → the Python kwarg name in the default_args dict.
_TD_MINUTE_KEYS = {
    "retry_delay_minutes": "retry_delay",
    "max_retry_delay_minutes": "max_retry_delay",
    "execution_timeout_minutes": "execution_timeout",
}

# Report-style model-name suffixes stripped when deriving a short task/var name
# (e.g. trial_balance_by_month → trial_balance_run).
_MODEL_SUFFIXES = ("_by_month", "_by_quarter", "_by_year")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def _parse_config(config_path: Path) -> dict:
    """Load and validate the pipeline YAML config (stages schema)."""
    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    required_top = ["dag_id", "schedule", "default_args", "stages"]
    for key in required_top:
        if key not in cfg:
            raise ValueError(f"Config missing required key: {key}")
    for stage in cfg["stages"]:
        if "id" not in stage or "type" not in stage:
            raise ValueError(f"Each stage must have 'id' and 'type': {stage}")
        if stage["type"] not in VALID_TYPES:
            raise ValueError(
                f"Stage '{stage['id']}' has unsupported type {stage['type']!r}; "
                f"valid: {sorted(VALID_TYPES)}"
            )
        if stage["type"] == "dbt_model" and "models" not in stage:
            raise ValueError(f"dbt_model stage '{stage['id']}' missing 'models' list")
    return cfg


# ---------------------------------------------------------------------------
# DAG builder — plain string construction, no template engine.
# The output reproduces the exact operator surface of the hand-written DAG.
# ---------------------------------------------------------------------------
def _build_header(cfg: dict) -> str:
    """Generate the file header, imports, and extract_load function (if needed)."""
    has_python_callable = any(s["type"] == "python_callable" for s in cfg["stages"])
    # Fixed import block. When a python_callable stage is present we emit the
    # full framework import set (matching the hand-written DAG's module top);
    # otherwise just the DAG + BashOperator imports are needed.
    if has_python_callable:
        imports = [
            "from airflow import DAG",
            "from airflow.operators.bash import BashOperator",
            "from airflow.operators.python import PythonOperator",
            "from airflow.providers.postgres.hooks.postgres import PostgresHook",
            "from airflow.exceptions import AirflowSkipException",
            "from datetime import datetime, timedelta",
        ]
    else:
        imports = [
            "from airflow import DAG",
            "from airflow.operators.bash import BashOperator",
            "from datetime import datetime, timedelta",
        ]

    lines = [
        "# AUTO-GENERATED by render_dag.py — do not hand-edit.",
        f"# Edit pipelines/{cfg['dag_id']}.yml and re-run render_dag.py instead.",
        "# ============================================",
        f"# Airflow DAG: {cfg['dag_id']}",
        f"# Purpose: {cfg.get('description', '')}",
        "# ============================================",
        "",
        f'"""{cfg.get("description", "")}"""',
        "",
    ]
    lines.extend(imports)
    lines.append("")

    # Emit the extract_load callable inline (matches the hand-written DAG structure).
    # The api.extract_load import stays local to the function to avoid import-time
    # coupling; framework imports live at module top above.
    if has_python_callable:
        lines.extend([
            "",
            "def extract_load(**context):",
            '    """Fetch GL transactions from FastAPI and load into Postgres via PostgresHook.',
            "",
            "    Uses Airflow's ``postgres_default`` connection (configured via",
            "    ``AIRFLOW_CONN_POSTGRES_DEFAULT`` in docker-compose) so that no",
            "    credentials are stored in code.  Raises AirflowSkipException when the",
            "    API returns zero rows, preventing downstream dbt runs on empty data.",
            '    """',
            "    from api.extract_load import fetch_raw_data, load_data_to_db",
            "",
            "    raw_data = fetch_raw_data()",
            "    row_count = len(raw_data)",
            "",
            "    if row_count == 0:",
            '        raise AirflowSkipException("No rows returned from API — skipping dbt run/test.")',
            "",
            '    hook = PostgresHook(conn_id="postgres_default")',
            "    conn = hook.get_conn()  # psycopg2 connection — lifecycle owned by hook",
            "",
            "    try:",
            "        load_data_to_db(raw_data, conn=conn)",
            "    finally:",
            "        conn.close()",
            "",
            '    print(f"Extract/load complete — {row_count} rows processed.")',
        ])

    return "\n".join(lines)


def _build_default_args(args: dict) -> str:
    """Generate the default_args dict, converting *_minutes keys to timedelta."""
    lines = [
        "",
        "",
        "# Default arguments for the DAG",
        "default_args = {",
    ]
    for key, value in args.items():
        if key in _TD_MINUTE_KEYS:
            out_key = _TD_MINUTE_KEYS[key]
            lines.append(f'    "{out_key}": {_minutes_to_td(value)},')
        elif isinstance(value, bool):
            # Python source uses capitalized True/False (not YAML's true/false).
            lines.append(f'    "{key}": {str(value)},')
        elif isinstance(value, str):
            lines.append(f'    "{key}": "{value}",')
        else:
            lines.append(f'    "{key}": {value},')
    lines.append("}")
    return "\n".join(lines)


def _build_dag_context(cfg: dict) -> str:
    """Generate the `with DAG(...) as dag:` block header."""
    start_date = cfg["start_date"]
    y, m, d = start_date.split("-")
    catchup = str(cfg.get("catchup", False))
    tags = cfg.get("tags", [])
    # Render tags as ["a", "b"] (double-quoted) to match the hand-written DAG style.
    tags_str = "[" + ", ".join(f'"{t}"' for t in tags) + "]"
    lines = [
        "",
        "with DAG(",
        f'    dag_id="{cfg["dag_id"]}",',
        f'    description="{cfg.get("description", "")}",',
        f'    schedule="{cfg["schedule"]}",',
        f"    start_date=datetime({y}, {int(m)}, {int(d)}),",
        f"    catchup={catchup},",
        f"    tags={tags_str},",
        f"    max_active_runs={cfg.get('max_active_runs', 1)},",
        "    doc_md=__doc__,",
        ") as dag:",
    ]
    return "\n".join(lines)


def _short_model_name(model: str) -> str:
    """Strip report-style suffixes to derive a short task/var name for a dbt model."""
    short = model
    for suffix in _MODEL_SUFFIXES:
        if short.endswith(suffix):
            short = short[: -len(suffix)]
            break
    return short


def _minutes_to_td(minutes: int) -> str:
    """Render an integer minute count as a timedelta(...) literal, preferring the
    largest whole unit (hours > minutes) — so 60 → timedelta(hours=1), 30 → timedelta(minutes=30)."""
    total = int(minutes) * 60
    if total >= 3600 and total % 3600 == 0:
        return f"timedelta(hours={total // 3600})"
    return f"timedelta(minutes={int(minutes)})"


def _sla_line(stage: dict) -> str:
    """Render the `sla=timedelta(...),` line for a stage, or '' if no SLA."""
    sla_minutes = stage.get("sla_minutes")
    if sla_minutes is None:
        return ""
    return f"        sla={_minutes_to_td(sla_minutes)},\n"


def _build_stages(stages: list) -> str:
    """Generate all stage operator definitions inside the DAG context."""
    parts = []
    for stage in stages:
        t = dict(stage)
        ttype = t["type"]

        if ttype == "python_callable":
            # Variable name defaults to {id}_task to avoid colliding with the
            # extract_load callable defined at module top. `var` overrides if set.
            var = t.get("var", f"{t['id']}_task")
            parts.append(
                f"\n    {var} = PythonOperator(\n"
                f'        task_id="{t["id"]}",\n'
                f"        python_callable=extract_load,\n"
                f"{_sla_line(t)}"
                f'        doc_md="{t.get("doc", "")}",\n'
                f"    )\n"
            )

        elif ttype in ("dbt_run", "dbt_test"):
            command = "dbt run" if ttype == "dbt_run" else "dbt test"
            parts.append(
                f'\n    {t["id"]} = BashOperator(\n'
                f'        task_id="{t["id"]}",\n'
                f'        bash_command="{command}",\n'
                f'        cwd="/opt/airflow/dbt",\n'
                f"{_sla_line(t)}"
                f'        doc_md="{t.get("doc", "")}",\n'
                f"    )\n"
            )

        elif ttype == "dbt_model":
            doc_template = t.get("doc_template", "Rebuild the {model} mart (generated artifact).")
            for model in t["models"]:
                doc = doc_template.replace("{model}", model)
                var = f"{_short_model_name(model)}_run"
                parts.append(
                    f"\n    {var} = BashOperator(\n"
                    f'        task_id="{var}",\n'
                    f'        bash_command="dbt run --models {model}",\n'
                    f'        cwd="/opt/airflow/dbt",\n'
                    f"{_sla_line(t)}"
                    f'        doc_md="{doc}",\n'
                    f"    )\n"
                )

    return "".join(parts)


def _build_chain(stages: list) -> str:
    """Build the `>>` dependency chain from the stages list.

    python_callable stages contribute their variable name (``var`` or ``{id}_task``);
    dbt_run/dbt_test stages contribute their ``id``; dbt_model stages contribute the
    short-name ``_run`` variable for each model."""
    ids = []
    for stage in stages:
        if stage["type"] == "dbt_model":
            for model in stage["models"]:
                ids.append(f"{_short_model_name(model)}_run")
        elif stage["type"] == "python_callable":
            ids.append(stage.get("var", f"{stage['id']}_task"))
        else:
            ids.append(stage["id"])
    chain = " >> ".join(ids)
    return f"\n    # Dependency chain — stages run in listed order; marts chain sequentially.\n    {chain}\n"


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
def render(config_path: Path) -> str:
    """Render the DAG file content from the YAML config."""
    cfg = _parse_config(config_path)
    parts = [
        _build_header(cfg),
        _build_default_args(cfg["default_args"]),
        _build_dag_context(cfg),
        _build_stages(cfg["stages"]),
        _build_chain(cfg["stages"]),
    ]
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Render Airflow DAG from YAML config.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--diff", action="store_true", help="show diff vs existing DAG (no write)")
    parser.add_argument("--check", action="store_true", help="exit 1 if rendered != existing")
    args = parser.parse_args()

    rendered = render(args.config)
    existing = args.output.read_text() if args.output.exists() else ""

    if rendered == existing:
        print(f"[render] {args.output} unchanged — skipping write.")
        return 0

    if args.diff:
        diff = difflib.unified_diff(
            existing.splitlines(keepends=True),
            rendered.splitlines(keepends=True),
            fromfile=f"a/{args.output.name}",
            tofile=f"b/{args.output.name}",
        )
        sys.stdout.writelines(diff)
        return 0

    if args.check:
        if rendered != existing:
            diff = difflib.unified_diff(
                existing.splitlines(keepends=True),
                rendered.splitlines(keepends=True),
                fromfile=f"a/{args.output.name}",
                tofile=f"b/{args.output.name}",
            )
            sys.stdout.writelines(diff)
            print(f"\n[check] {args.output} differs from rendered output.")
            return 1
        print(f"[check] {args.output} matches rendered output.")
        return 0

    # Write the artifact.
    args.output.write_text(rendered)
    print(f"[render] wrote {args.output} ({len(rendered.splitlines())} lines).")
    if existing:
        added = len(rendered.splitlines()) - len(existing.splitlines())
        print(f"[render] delta: {'+'if added>=0 else ''}{added} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
