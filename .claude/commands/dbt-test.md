---
name: dbt-test
description: Run dbt tests only (no model execution)
paths:
  - dbt_project/
---

# Run dbt Tests

Run dbt tests without executing models. Use this to validate data quality after a model run.

## Usage

```
/dbt-test [options]
```

## Options

- `--models <model_pattern>`: Test specific models (default: all)
- `--test <test_name>`: Run a specific test by name
- `--select <selector>`: Use predefined selectors from selectors.yml
- `--store-failures`: Save failed test rows to a table for inspection
- `--warn-error`: Treat warnings as errors

## Examples

```bash
# Run all tests
/dbt-test

# Test specific model
/dbt-test --models dim_customer

# Test staging models only
/dbt-test --models stg_*

# Run a specific test
/dbt-test --test unique_dim_customer_customer_key

# Save failures for inspection
/dbt-test --models fact_sales --store-failures
```

## Implementation

```bash
# Run all tests
docker compose run --rm dbt test

# Test specific models
docker compose run --rm dbt test --models <model_name>

# Test with failure storage
docker compose run --rm dbt test --store-failures

# Test specific test name
docker compose run --rm dbt test --name <test_name>
```

## See Also

- `/dbt-run` — Run dbt models (with optional testing)
- `/run` — Run local development tasks
