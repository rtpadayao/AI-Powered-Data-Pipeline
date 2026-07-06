---
name: dbt
description: dbt transformation modeling skills and shortcuts
paths:
  - dbt_project/
---

# dbt Skills

Quick reference for common dbt operations and best practices.

## Model Operations

### Running Models
```
# Run all models
dbt run

# Run specific models
dbt run --models stg_transactions
dbt run --models stg_* finance_*

# Run models with specific target
dbt run --target prod

# Run models with variables
dbt run --vars '{'start_date': '2023-01-01'}'
```

### Testing
```
# Run all tests
dbt test

# Test specific models
dbt test --models stg_transactions

# Run specific test types
dbt test --data  # Run data tests
dbt test --schema  # Run schema tests
```

### Documentation
```
# Generate documentation
dbt docs generate

# Serve documentation
dbt docs serve

# Check for documentation issues
dbt docs check
```

### Development Workflow
```
# Compile without running
dbt compile

# Debug configuration
dbt debug

# List available models
dbt ls

# List resources (models, tests, sources)
dbt ls --resource-type model
dbt ls --resource-type test
dbt ls --resource-type source

# Show compiled SQL
dbt compile --models stg_transactions --show
```

## Model Configuration Best Practices

### Materialization
```sql
{{ config(materialized='table') }}          -- Default, full refresh
{{ config(materialized='view') }}           -- Virtual view
{{ config(materialized='incremental') }}    -- Append new/changed records
{{ config(materialized='ephemeral') }}      -- No physical object, used in other models
```

### Incremental Models
```sql
{{ config(
    materialized='incremental',
    unique_key='id',
    incremental_strategy='merge'
) }}

{% if is_incremental() %}
  where updated_at > (select max(updated_at) from {{ this }})
{% endif %}
```

### Tags and Metadata
```sql
{{ config(
    tags=['finance', 'daily'],
    meta={
        'owner': 'data-team',
        'domain': 'transactions',
        'contains_pii': false
    }
) }}
```

### Testing Configuration
```yaml
# In schema.yml
version: 2

models:
  - name: stg_transactions
    description: "Staging layer for raw transactions"
    columns:
      - name: id
        tests:
          - not_null
          - unique
      - name: amount
        tests:
          - not_null
          - accepted_range:
              min: 0
              max: 1000000
      - name: status
        tests:
          - accepted_values:
              values: ['completed', 'pending', 'failed', 'refunded']
```

## Common Macros and Utilities

### Date Handling
```sql
-- Current timestamp
{{ dbt_utils.current_timestamp() }}

-- Date manipulation
{{ dbt_utils.date_add(datecolumn, interval=1, datepart='day') }}

-- Date spine for time series
{{ dbt_utils.date_spine(
    datepart="day",
    start_date="cast('2023-01-01' as date)",
    end_date="cast('2023-12-31' as date)"
) }}
```

### Surrogate Keys
```sql
-- Generate surrogate key
{{ dbt_utils.surrogate_key(['id', 'source_system']) }}

-- Surrogate key for slowly changing dimensions
{{ dbt_utils.surrogate_key([
    'natural_key',
    'effective_date'
]) }}
```

### String Manipulation
```sql
-- Concatenate with null handling
{{ dbt_utils.concat(['first_name', "' '", 'last_name']) }}

-- Replace characters
{{ dbt_utils.replace(field, "old", "new") }}

-- Length
{{ dbt_utils.length(field) }}
```

## Project Organization

### Recommended Structure
```
dbt_project/
├── dbt_project.yml
├── models/
│   ├── staging/
│   │   ├── stg_transactions.sql
│   │   └── schema.yml
│   ├── refined/
│   │   ├── dim_account.sql
│   │   └── schema.yml
│   └── marts/
│       ├── fact_transactions.sql
│       └── schema.yml
├── macros/
├── seeds/
├── tests/
├── snapshots/
└── analyses/
```

### Naming Conventions
- **Models**: `stg_` (staging), `dim_` (dimensions), `fact_` (facts), `int_` (intermediate)
- **Seeds**: `seed_` prefix
- **Snapshots**: `snapshot_` prefix
- **Tests**: Descriptive names like `not_null_stg_transactions_id`
- **Macros**: Verb-noun format like `get_date_range`

## Troubleshooting

### Compilation Errors
```
Compilation Error in model stg_transactions (models/staging/stg_transactions.sql)
  Undefined variable: 'var'
```
- Check that variables are defined in dbt_project.yml or passed via --vars
- Verify variable names match exactly (case-sensitive)
- Ensure variables are referenced correctly: {{ var.variable_name }}

### Dependency Errors
```
Found multiple matching nodes for dependency stg_transactions
```
- Ensure unique model names across project
- Use package names if needed: ref('my_package.stg_transactions')
- Check for circular dependencies in model dependencies

### Resource Errors
```
Database Error in model fact_transactions
  relation "stg_transactions" does not exist
```
- Check that source models exist and are spelled correctly
- Verify schema.yml sources match actual table names
- Run upstream models first: dbt run --models stg_*

### Performance Issues
```
Query took too long and was cancelled
```
- Add appropriate indexes in post-hook
- Consider incremental materialization for large fact tables
- Break complex transformations into multiple models
- Review JOIN conditions for Cartesian products

## Best Practices

### Modeling Principles
1. Follow the staging → refined → marts layering principle
2. Keep models focused on single business concepts
3. Document all models and columns in schema.yml
4. Use source freshness to monitor data latency
5. Implement data tests for critical business rules

### SQL Style
1. Use CTEs (WITH clauses) for readability
2. Alias all tables and columns
3. Use consistent formatting (2-space indentation)
4. Prefer ANSI JOIN syntax over WHERE joins
5. Use UPPER for SQL keywords, lowercase for identifiers

### Testing Strategy
1. Test at least 80% of model columns
2. Implement not_null and unique tests for primary keys
3. Use accepted_values for categorical data
4. Create custom tests for complex business validations
5. Test edge cases (nulls, empty strings, boundary values)

### Documentation
1. Write clear descriptions for all models and columns
2. Include business context and data source information
3. Note any transformations or cleaning applied
4. Document known limitations or data quality issues
5. Keep documentation updated with model changes

### Performance Optimization
1. Use incremental materialization for frequently updated fact tables
2. Partition large tables by date when appropriate
3. Create indexes on frequently filtered/joined columns
4. Optimize JOIN order (largest tables first)
5. Consider using materialized views for expensive aggregations

### Collaboration
1. Use descriptive commit messages
2. Review schema changes with team
3. Use version control for all dbt project files
4. Run tests in CI/CD pipeline before merging
5. Share macros and utilities across projects