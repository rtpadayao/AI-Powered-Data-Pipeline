---
name: airflow
description: Airflow orchestration skills and shortcuts
paths:
  - airflow/
---

# Airflow Skills

Practical reference for Airflow operations: CLI commands, code patterns, and troubleshooting procedures. For architectural decisions, see the `airflow-expert_agent` agent. For mandatory rules, see `airflow_rules.md`.

## CLI Quick Reference

### DAG Management
```bash
# List and inspect
airflow dags list
airflow dags list | grep finance
airflow dags show <dag_id>
airflow dags tree <dag_id>
airflow dags list-runs <dag_id>

# Trigger and test
airflow dags trigger <dag_id>
airflow dags trigger <dag_id> --conf '{"key": "value"}'
airflow dags backfill <dag_id> --start-date 2023-06-01 --end-date 2023-06-30
airflow tasks test <dag_id> <task_id> <execution_date>
airflow dags test <dag_id> <execution_date>

# Pause/resume
airflow dags pause <dag_id>
airflow dags unpause <dag_id>

# Clear and reset
airflow tasks clear <dag_id> --start-date 2023-06-01 --end-date 2023-06-30 --task-regex 'extract_*'
airflow dags delete <dag_id>  # Removes all metadata for a DAG
```

### Connections & Variables
```bash
# Connections
airflow connections list
airflow connections add 'postgres_default' \
  --conn-type 'postgres' \
  --conn-host 'localhost' \
  --conn-schema 'airflow' \
  --conn-login 'airflow' \
  --conn-password 'airflow'
airflow connections get 'postgres_default' --json
airflow connections test 'postgres_default'

# Variables
airflow variables list
airflow variables set 'start_date' '2023-01-01'
airflow variables get 'start_date'
airflow variables delete 'start_date'
airflow variables set-json 'dbt_vars' '{"target": "prod"}'
```

### Pools
```bash
airflow pools list
airflow pools create --pool 'etl_pool' --slot-count 5 --description 'Pool for ETL tasks'
airflow pools set --pool 'etl_pool' --slot-count 10
airflow pools delete 'etl_pool'
```

### Logs & Health
```bash
airflow tasks logs <dag_id> <task_id> <execution_date>
airflow tasks logs <dag_id> <task_id> <execution_date> --follow
airflow scheduler health
airflow webserver health
airflow version
airflow check-db
```

### Database Maintenance
```bash
airflow db clean --clean-before-timestamp '2023-01-01' --table task_instance
airflow db reset  # DANGER: Deletes all metadata!
```

## Code Patterns

### BashOperator
```python
extract_task = BashOperator(
    task_id='extract_transactions',
    bash_command='python /opt/airflow/scripts/extract.py {{ ds }}',
    dag=dag,
)
```

### PythonOperator
```python
def transform_data(**context):
    # Transformation logic here
    pass

transform_task = PythonOperator(
    task_id='transform_data',
    python_callable=transform_data,
    provide_context=True,
    dag=dag,
)
```

### PostgresOperator
```python
load_task = PostgresOperator(
    task_id='load_to_postgres',
    postgres_conn_id='postgres_default',
    sql="""
        INSERT INTO finance.transactions
        SELECT * FROM staging.temp_transactions;
    """,
    dag=dag,
)
```

### HttpSensor
```python
wait_for_api = HttpSensor(
    task_id='wait_for_api',
    http_conn_id='api_default',
    endpoint='health/',
    request_params={},
    response_check=lambda response: response.status_code == 200,
    poke_interval=30,
    timeout=300,
    dag=dag,
)
```

### Dependency Patterns
```python
# Linear chain
extract >> transform >> load

# Fan-out
extract >> [transform_a, transform_b, transform_c] >> load

# Fan-in
[extract_a, extract_b, extract_c] >> combine >> load

# Conditional branching
branch_task = BranchPythonOperator(
    task_id='check_condition',
    python_callable=check_condition,
    dag=dag,
)
extract >> branch_task
branch_task >> [path_a_task, path_b_task]
[path_a_task, path_b_task] >> merge_task
```

### Error Handling & Retries
```python
default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'start_date': datetime(2023, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'retry_exponential_backoff': True,
    'max_retry_delay': timedelta(minutes=60),
}

task = PythonOperator(
    task_id='flaky_task',
    python_callable=flaky_function,
    retries=5,  # Override default
    retry_delay=timedelta(minutes=10),
    dag=dag,
)
```

### SLA Monitoring
```python
with DAG('finance_etl', default_args=default_args, schedule_interval='@daily') as dag:
    task = PythonOperator(
        task_id='critical_task',
        python_callable=critical_function,
        sla=timedelta(hours=2),
        dag=dag,
    )
```

### Pool Usage
```python
load_task = PostgresOperator(
    task_id='load_to_postgres',
    postgres_conn_id='postgres_default',
    sql="""INSERT INTO ...""",
    pool='postgres_write_pool',
    pool_slots=2,
    dag=dag,
)
```

### Resource Prioritization
```python
critical_task = PythonOperator(
    task_id='critical_reconciliation',
    python_callable=reconcile_accounts,
    weight_rule='upstream',
    weight=10,
    dag=dag,
)

latest_only = LatestOnlyOperator(task_id='latest_only', dag=dag)
latest_only >> extract_task
```

## Templating & Macros

### Built-in Variables
- `{{ ds }}`: YYYY-MM-DD (execution date)
- `{{ ds_nodash }}`: YYYYMMDD
- `{{ ts }}`: YYYY-MM-DDTHH:MM:SS
- `{{ ts_nodash }}`: YYYYMMDDTHHMMSS
- `{{ yesterday_ds }}`: Previous day
- `{{ tomorrow_ds }}`: Next day
- `{{ execution_date }}`: Pendulum datetime object
- `{{ logical_date }}`: Same as execution_date (Airflow 2.2+)

### Custom Macros
```python
# In macros/
def format_filename(**context):
    return f"transactions_{context['ds']}.csv"

# In DAG template
{{ format_filename() }}
```

## Common Issues & Fixes

### DAG Not Loading
- Check for syntax errors in DAG file
- Verify file is in `DAGS_FOLDER` (usually `/opt/airflow/dags`)
- Ensure file has `.py` extension
- Check imports are available in PYTHONPATH
- Look for circular imports

### Task Stuck in queued
- Check scheduler is running: `airflow scheduler health`
- Verify pool has available slots
- Check concurrency limits (`max_active_runs_per_dag`)
- Verify executor is properly configured
- Look for zombie processes

### Task Stuck in running
- Check worker logs for infinite loops
- Verify task isn't waiting for external resource
- Check if task was killed externally (OOM killer)
- Consider setting task timeout
- Check for distributed lock issues

### Connection Issues
- Verify Connection exists in UI or CLI
- Check Connection type matches operator requirements
- Validate hostname, port, credentials
- Test connection manually outside Airflow
- Check network connectivity/firewall rules

### Permission Errors
- Verify file permissions for accessed resources
- Check user running Airflow has necessary access
- Look for SELinux/AppArmor blocking access
- Verify mounted volume permissions in Docker/K8s
- Check umask and default file permissions

### Version Compatibility
- Check provider package versions match Airflow version
- Review release notes for breaking changes
- Test upgrades in staging environment first
- Use constraints files for reproducible installations
- Check compatibility matrix in documentation

## Docker Compose Commands

```bash
# Service status
docker compose ps airflow-webserver airflow-scheduler airflow-worker

# Validation
docker compose exec airflow-webserver airflow dags list
docker compose exec airflow-webserver airflow dags show <dag_id>
docker compose exec airflow-webserver airflow dags list-runs <dag_id>
docker compose exec airflow-webserver airflow tasks test <dag_id> <task_id> <execution_date>

# Logs
docker compose logs -f airflow-webserver
docker compose logs -f airflow-scheduler
docker compose logs -f airflow-worker

# Resource monitoring
docker compose stats

# Database check
docker compose exec postgres psql -U airflow -d airflow -c "\l"

# Redis check (if using CeleryExecutor)
docker compose exec redis redis-cli ping
```
