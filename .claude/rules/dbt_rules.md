---
  name: dbt
  description: Rules for dbt SQL formatting, layering, and model development
  paths:
    - dbt_project/**
---

# dbt Development Guidelines

## Project Structure
  - `models/staging/`: Source-centric, cleaned data (closest to raw)
  - `models/refined/`: Business rules, master data, entities
  - `models/marts/`: Domain-centric, ready for consumption (dimensional/fact models)
  - `macros/`: Reusable SQL logic (e.g., `save_history.sql`)
  - `seeds/`: Static reference data (CSV files loaded via `dbt seed`)
  - `tests/`: Custom tests (singular tests for specific business logic)

## Modeling Best Practices
  1. **Layering Principle**: Each layer should only depend on the layer directly below it
  2. **Naming Convention**: Use descriptive, lowercase names with underscores
  3. **Materialization**:
     - Staging: `view` (for latest data)
     - Refined/Marts: `incremental` (for performance with large datasets)
  4. **Documentation**: Every model, column, and test should have descriptions
  5. **Testing**:
     - Add `not_null`, `unique`, `relationships` tests where appropriate
     - Create custom tests for business-specific validations
     - Test at least 80% of model columns

## SQL Formatting
  - Use uppercase for SQL keywords (SELECT, WHERE, GROUP BY, etc.)
  - Use lowercase for column and table names
  - Indent nested queries consistently (2 spaces)
  - Place each major clause on a new line
  - Use CTEs (WITH statements) to break down complex logic

## Model Configuration
  - Always specify `materialized` in model configs
  - Use `unique_key` for incremental models
  - Add `tags` for environment-specific or team-specific organization
  - Configure `persist_docs` for relation-level documentation

## Development Workflow
  1. Create models in appropriate layer directory
  2. Test locally: `docker compose run --rm dbt run --models <model_name>`
  3. Validate tests: `docker compose run --rm dbt test --models <model_name>`
  4. Generate documentation: `docker compose run --rm dbt docs generate`
  5. Preview docs: `docker compose run --rm dbt docs serve`

## Naming Conventions
  - Staging: `stg_<source>_<table_name>` (e.g., `stg_erp_transactions`)
  - Refined: `<dimension|fact>_<business_entity>` (e.g., `dim_customer`, `fact_sales`)
  - Marts: `<domain>_<purpose>` (e.g., `finance_reporting`, `sales_performance`)
  - Macros: `snake_case_descriptive_name` (e.g., `generate_surrogate_key`)