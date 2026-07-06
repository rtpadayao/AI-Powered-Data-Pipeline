---
name: run-pipeline
description: Run the full automated data pipeline from extraction to transformation
paths:
  - /
---

# Run Full Data Pipeline

This command executes the complete data pipeline:
1. Extracts data from CSV via FastAPI
2. Loads data into PostgreSQL `finance.gl_transactions` (source table)
3. Runs dbt transformations (staging → refined → marts)
4. Generates documentation

## Data Flow

```
CSV (raw_storage/)
  → FastAPI (/transactions/raw endpoint)
    → extract_load.py (loads into finance.gl_transactions)
      → dbt staging (stg_gl_transactions)
        → dbt refined (dim_account, dim_date, fact_gl_transactions)
          → dbt marts (account_balances, financial_statements, normalize)
```

## Usage

```
/run-pipeline [options]
```

## Options

- `--skip-extract`: Skip the extraction/load phase
- `--skip-dbt`: Skip the dbt transformation phase
- `--skip-docs`: Skip documentation generation
- `--models <model_pattern>`: Run specific dbt models (default: all)
- `--target <target>`: dbt target to use (default: dev)
- `--help`: Show this help message

## Examples

```bash
# Run full pipeline
/run-pipeline

# Run only extraction and loading
/run-pipeline --skip-dbt --skip-docs

# Run only dbt transformations
/run-pipeline --skip-extract

# Run specific dbt models (staging)
/run-pipeline --models stg_gl_transactions

# Run specific dbt models (refined dimensions/facts)
/run-pipeline --models dim_account dim_date fact_gl_transactions

# Run specific dbt models (marts)
/run-pipeline --models account_balances financial_statements

# Run pipeline with production target
/run-pipeline --target prod
```

## What It Does

### Extraction & Load Phase

1. Starts the FastAPI service if not running
2. Runs `extract_load.py` which fetches data from the FastAPI `/transactions/raw` endpoint
3. The script reads from the CSV at `infrastructure/raw_storage/raw_gl_dr_cr_noAmount.csv`
4. Loads data into PostgreSQL `finance.gl_transactions` table (defined in `infrastructure/postgres/init-db.sql`)
5. Stops the FastAPI service (if it was started by this command)

### dbt Transformation Phase

1. Runs dbt models in dependency order across three layers:
   - **staging/**: `stg_gl_transactions` (reads from `finance.gl_transactions`)
   - **refined/**: `dim_account`, `dim_date`, `fact_gl_transactions`
   - **marts/**: `account_balances`, `financial_statements`, `normalize`
2. Applies tests to validate data quality
3. Generates documentation if requested

### Documentation Phase

1. Generates dbt documentation site
2. Optionally serves it for local viewing

## Implementation

This command orchestrates the following Docker Compose operations:

```bash
# Start FastAPI (if not already running)
docker compose up -d fastapi

# Extraction/Load (unless skipped)
docker compose run --rm fastapi python /app/extract_load.py

# dbt Transformations (unless skipped)
docker compose run --rm dbt run --models <models> --target <target>
docker compose run --rm dbt test --models <models> --target <target>

# Documentation (unless skipped)
docker compose run --rm dbt docs generate
```

## Project Structure Reference

The pipeline operates on these actual project paths:

| Component | Path |
|-----------|------|
| Raw CSV | `infrastructure/raw_storage/raw_gl_dr_cr_noAmount.csv` |
| Extract/Load script | `api/extract_load.py` |
| Source table | `finance.gl_transactions` (created by `infrastructure/postgres/init-db.sql`) |
| dbt staging | `dbt_project/models/staging/stg_gl_transactions.sql` |
| dbt refined | `dbt_project/models/refined/` (dim_account, dim_date, fact_gl_transactions) |
| dbt marts | `dbt_project/models/marts/` (account_balances, financial_statements, normalize) |
| dbt profiles | `dbt_project/profiles.yml` |

## Environment Variables

The command uses environment variables from:
- `.env` file
- Docker Compose configuration
- Individual service environments

## Troubleshooting

### Common Issues

1. **Connection refused to PostgreSQL**
   - Ensure PostgreSQL service is healthy: `docker compose ps postgres`
   - Check .env file for correct POSTGRES_* variables
   - Verify network connectivity between services

2. **dbt compilation errors**
   - Check SQL syntax in models
   - Verify references to source tables
   - Ensure profiles.yml is correctly configured

3. **Extraction failures**
   - Verify CSV file exists at `infrastructure/raw_storage/raw_gl_dr_cr_noAmount.csv`
   - Check that FastAPI service is running and healthy
   - Validate CSV format and encoding

4. **Permission denied**
   - Check Docker volume permissions
   - Ensure user has access to mounted directories

## See Also

- `/dbt-run` - Run only dbt transformations
- `/api-test` - Test the FastAPI endpoint
- `/airflow-test` - Test Airflow DAGs
- `/run` - Local dev tasks (including viewing logs)
