---
name: airflow-test
description: Test and validate Airflow DAGs for the data pipeline
paths:
  - airflow/
---

# Test Airflow DAGs

This command tests and validates Airflow DAGs for the data pipeline, including syntax validation, task testing, and workflow verification.

## Usage

```
/airflow-test [options]
```

## Options

- `--dag <dag_id>`: Specific DAG to test (default: all DAGs)
- `--task <task_id>`: Specific task to test (requires --dag)
- `--execution-date <date>`: Execution date for testing (default: yesterday)
- `--run-test`: Run actual task tests (not just syntax check)
- `--list-dags`: List all available DAGs
- `--list-tags`: List all task tags in DAG(s)
- `--tree`: Show DAG tree structure
- `--failed`: Show only failed tasks from last run
- `--success`: Show only successful tasks from last run
- `--help`: Show this help message

## Examples

```bash
# Validate all DAGs syntax
/airflow-test

# Test specific DAG
/airflow-test --dag finance_etl_daily

# Test specific task in DAG
/airflow-test --dag finance_etl_daily --task extract_transactions

# Run actual task tests
/airflow-test --dag finance_etl_daily --run-test

# List all DAGs
/airflow-test --list-dags

# Show DAG tree structure
/airflow-test --dag finance_etl_daily --tree

# Test with specific execution date
/airflow-test --dag finance_etl_daily --execution-date 2023-06-15

# Show failed tasks from last run
/airflow-test --failed

# Show successful tasks from last run
/airflow-test --success
```

## What It Does

### Syntax Validation

1. Parses all DAG files for Python syntax errors
2. Validates DAG structure and imports
3. Checks for circular dependencies
4. Verifies task IDs are unique within DAG

### Task Testing (when --run-test is used)

1. Creates task instances for testing
2. Executes tasks with specified execution date
3. Validates task outputs and side effects
4. Checks error handling and retry behavior

### Workflow Verification

1. Verifies task dependencies and trigger rules
2. Checks SLA configurations
3. Validates use of Airflow variables and connections
4. Ensures proper resource allocation (pools, weights)

## Implementation

This command uses Airflow CLI commands:

### Syntax Validation Only
```bash
airflow dags list
airflow dags show <dag_id>
airflow dags list-runs <dag_id>
```

### Task Testing
```bash
airflow tasks test <dag_id> <task_id> <execution_date>
airflow dags test <dag_id> <execution_date>
```

### Information Queries
```bash
airflow dags list-tags
airflow tasks list <dag_id>
airflow dags tree <dag_id>
airflow task-state list <dag_id> <execution_date>
```

## Environment & Configuration

The test command uses:
- Airflow services running via Docker Compose
- DAGs located in `airflow/dags/`
- Airflow configuration from Docker Compose
- Database backend for metadata (PostgreSQL)
- Execution date defaults to yesterday if not specified

## Common Test Scenarios

### DAG Validation
```bash
# Should return list of DAGs with no errors
/airflow-test

# Should show DAG structure without errors
/airflow-test --dag finance_etl_daily --tree
```

### Task Testing
```bash
# Should execute task successfully
/airflow-test --dag finance_etl_daily --task extract_transactions --run-test

# Should handle errors gracefully
/airflow-test --dag finance_etl_daily --task fail_on_purpose --run-test
```

### Dependency Verification
```bash
# Should show correct task dependencies
/airflow-test --dag finance_etl_daily --tree

# Should validate trigger rules
# (Check DAG code for TriggerRule.ALL_SUCCESS, etc.)
```

### SLA Verification
```bash
# Should show SLA settings if configured
# (Check DAG code for sla_miss_callback or sla parameters)
```

## Troubleshooting

### DAG Not Found
```
Error: DAG not found: 'nonexistent_dag'
```
- Check DAG file is in `airflow/dags/` directory
- Verify DAG file has correct `.py` extension
- Ensure DAG has unique `dag_id` parameter
- Check for syntax errors preventing DAG loading
- Run `airflow dags list` to see loaded DAGs

### Task Testing Failures
```
[2023-06-19 10:30:00,000] {taskinstance.py:1152} ERROR - Task failed with exception
```
- Check task logs for specific error details
- Verify required connections exist (Admin → Connections)
- Verify required variables exist (Admin → Variables)
- Check file paths and permissions for accessed resources
- Examine stack trace for root cause

### Import Errors
```
[2023-06-19 10:30:00,000] {model.py:487} ERROR - Failed to import: /opt/airflow/dags/finance_etl_daily.txt  No such file or directory
```
- Ensure DAG files have `.py` extension, not `.txt` or other
- Check that imported modules are available in PYTHONPATH
- Verify custom operators/plugins are installed and accessible
- Check Python version compatibility

### Database Connection Issues
```
[2023-06-19 10:30:00,000] {models.py:172} ERROR - (psycopg2.OperationalError) 
FATAL:  password authentication failed for user "airflow"
```
- Verify PostgreSQL service is running
- Check Airflow connection configuration
- Validate credentials in .env or Docker secrets
- Ensure network connectivity between services

### Permission Errors
```
[2023-06-19 10:30:00,000] {bash.py:125} ERROR - Bash command failed
```
- Check file and directory permissions
- Verify user running Airflow has necessary access
- Ensure mounted volumes have correct permissions
- Check SELinux/AppArmor restrictions if applicable

## Best Practices

### DAG Design
1. Keep DAGs focused on a single workflow or business process
2. Use clear, descriptive DAG and task IDs
3. Implement proper error handling and logging
4. Make tasks idempotent when possible
5. Use appropriate trigger rules for task dependencies
6. Limit DAG complexity (consider using SubDAGs or TaskGroups for complex workflows)

### Task Implementation
1. Use appropriate operators for task types:
   - BashOperator: For command-line operations
   - PythonOperator: For custom Python logic
   - PostgresOperator: For SQL operations
   - HttpSensor/SimpleHttpOperator: For HTTP interactions
   - File sensors: For file-based triggers
2. Avoid heavy computations in operators; delegate to external services
3. Use XComs sparingly for small data transfers
4. Implement proper resource management (close connections, etc.)
5. Handle exceptions gracefully and provide meaningful error messages

### Testing Strategy
1. Test DAG syntax regularly during development
2. Test individual tasks with realistic inputs
3. Test end-to-end workflow with production-like data
4. Test error conditions and failure scenarios
5. Test performance with expected data volumes
6. Validate SLA and alerting mechanisms

### Configuration Management
1. Store sensitive data in Airflow Connections (not in DAG code)
2. Use Variables for configurable parameters
3. Use Connections for database, API, and service credentials
4. Consider using Secrets Backend for production deployments
5. Document all connections and variables used

### Performance Optimization
1. Use pools to limit concurrent resource-intensive tasks
2. Set appropriate task weights for priority management
3. Consider using LatestOnlyOperator when appropriate
4. Use timeouts to prevent runaway tasks
5. Monitor and optimize task execution times

## See Also

- `/run-pipeline` - Run full data pipeline
- `/dbt-run` - Run dbt transformations
- `/api-test` - Test the FastAPI endpoint
- `/airflow-reset` - Reset Airflow metadata database
- `/run` - Local dev tasks (including viewing logs)