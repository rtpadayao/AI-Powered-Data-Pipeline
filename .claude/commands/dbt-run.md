---
name: dbt-run
description: Run dbt transformations with testing and documentation generation
paths:
  - dbt_project/
---

# Run dbt Transformations

This command executes dbt transformations, tests, and documentation generation for the data pipeline.

## Usage

```
/dbt-run [options]
```

## Options

- `--models <model_pattern>`: Run specific dbt models (default: all)
- `--exclude <model_pattern>`: Exclude specific dbt models
- `--target <target>`: dbt target to use (default: dev)
- `--vars '<vars>'`: Pass variables to dbt (JSON format)
- `--skip-tests`: Skip running tests after models
- `--skip-docs`: Skip documentation generation
- `--watch`: Watch for changes and re-run (development mode)
- `--help`: Show this help message

## Examples

```bash
# Run all models and tests
/dbt-run

# Run only staging models
/dbt-run --models stg_*

# Run specific model
/dbt-run --models dim_customer

# Exclude certain models
/dbt-run --exclude marts_archive_*

# Run with custom variables
/dbt-run --vars '{'start_date': '2023-01-01'}'

# Run in development mode with watch
/dbt-run --watch

# Run tests only
/dbt-run --skip-models --only-tests

# Generate documentation only
/dbt-run --skip-models --skip-tests --docs-only
```

## What It Does

### Model Execution
1. Compiles dbt project (validates SQL and Jinja2)
2. Executes specified models in correct dependency order
3. Creates/updates database objects according to materialization

### Testing
1. Runs schema tests (not_null, unique, relationships, etc.)
2. Runs data tests (custom tests in tests/ directory)
3. Reports test results and failures

### Documentation
1. Generates documentation artifacts (manifest.json, catalog.json)
2. Creates searchable documentation site

## Implementation

This command orchestrates the following Docker Compose operations:

```bash
# Run models
docker compose run --rm dbt run <options>

# Run tests (unless skipped)
docker compose run --rm dbt test <options>

# Generate docs (unless skipped)
docker compose run --rm dbt docs generate
```

## dbt Command Options Explained

### Model Selection
- `--models`: Specify which models to run (supports wildcards)
- `--exclude`: Exclude specific models from execution
- `--select`: Alternative syntax for model selection
- `--selector`: Use predefined selectors from selectors.yml

### Target Configuration
- `--target`: Specifies which target in profiles.yml to use
- Common targets: dev, prod, qa

### Variables
- `--vars`: Pass variables to templates (must be valid JSON)
- Alternative: `-v` for single key=value pairs
- Variables accessible in models as {{ var.variable_name }}

### Testing Options
- `--skip-tests`: Skip test execution after model runs
- `--data`: Run data tests in addition to schema tests
- `--store-failures`: Save failed test rows for inspection
- `--warn-error`: Treat warnings as errors

### Documentation Options
- `--docs-only`: Only generate documentation (skip models and tests)
- `--serve`: Start documentation server after generation

## Environment & Configuration

The command uses:
- dbt_project/project/ for models
- dbt_project/profiles.yml for database connections
- Environment variables from .env and Docker Compose
- dbt_project/dbt_project.yml for project configuration

## Troubleshooting

### Compilation Errors
```
Error: Database Error in model <model_name> (models/staging/stg_model.sql)
  Failed to execute query
  Database error in model <model_name> (models/staging/stg_model.sql)
  relation "source_name.table_name" does not exist
```
- Check that source is defined in sources.yml
- Verify source table exists in database
- Check schema spelling and case sensitivity

### Dependency Errors
```
Error: Ambiguous dependency in model <model_name>
  Found multiple matching nodes for dependency <dependency_name>
```
- Ensure unique model names
- Use @ in ref() to specify package if needed
- Check for circular dependencies

### Resource Constraints
```
Error: Database Error
  ERROR:  out of memory
  Detail: Failed on request of size XXXX
```
- Increase work_mem in post-hook for the model
- Consider breaking complex transformations into multiple models
- Check for Cartesian products in JOINs

### Test Failures
```
FAILED test_name [not_null]
  - with values: ["NULL", "NULL", ...]
```
- Check source data for null values
- Consider if column should allow nulls
- Update test definition if business logic changed

## Best Practices

### Incremental Development
1. Start with `--models <specific_model>` to iterate quickly
2. Use `dbt compile` to check SQL without executing
3. Use `dbt debug` to check configuration
4. Use `dbt ls` to list available models

### Performance Optimization
- Use incremental materialization for large fact tables
- Partition large tables by date when appropriate
- Create indexes on frequently filtered columns
- Use appropriate join order in complex queries

### Testing Strategy
- Test at least 80% of model columns
- Use data tests for business logic validation
- Test edge cases (empty data, boundary values)
- Consider implementing custom tests for complex validations

### Documentation
- Always describe models and columns in schema.yml
- Include business context in descriptions
- Keep documentation up to date with model changes

## See Also

- `/run-pipeline` - Run full data pipeline
- `/api-test` - Test the FastAPI endpoint
- `/airflow-test` - Test Airflow DAGs
- `/dbt-test` - Run only dbt tests
- `/dbt-docs` - Generate only dbt documentation