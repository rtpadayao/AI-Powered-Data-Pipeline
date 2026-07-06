---
  name: python
  description: Rules for Python data analysis patterns, pandas/polars usage, and financial data processing
  paths:
    - api/**
    - dbt_project/**
    - notebooks/**
    - airflow/dags/**
---

# Python Data Analysis Rules

## General Python Style
  - Use Python 3.10+ with type hints for function signatures
  - Prefer f-strings over `.format()` or `%` formatting
  - Use `pathlib.Path` for filesystem operations (not `os.path`)
  - Import conventions: `import pandas as pd`, `import numpy as np`, `import matplotlib.pyplot as plt`
  - Use virtual environments or Docker containers for dependency isolation
  - Pin dependencies in `requirements.txt` with exact versions for reproducibility

## Pandas Patterns
  1. **Method Chaining**: Prefer chained operations over intermediate variables. Use `.pipe()` for custom functions in chains and `.assign()` for creating new columns.
  2. **Vectorized Operations**: Never iterate over DataFrame rows with `for` loops. Use vectorized NumPy/pandas operations. Replace `.apply()` with vectorized alternatives where possible.
  3. **Index Alignment**: Be explicit about index alignment. Use `.reset_index()` when index semantics matter.
  4. **Missing Data Handling**: Use `.isna()` / `.notna()` for detection. Choose fill strategy explicitly: `.ffill()` for time series, `.bfill()` for backfill, `.fillna(value)` for constants, `.interpolate()` for linear interpolation.
  5. **Type Optimization**: Downcast numeric types with `pd.to_numeric(downcast='integer'|'float')`. Use `pd.Categorical` for low-cardinality string columns.
  6. **GroupBy**: Use `.groupby().agg()` with named aggregations. Use `.transform()` for group-level operations that preserve index.
  7. **Time Series**: Set datetime index with `pd.to_datetime()` and `.set_index()`. Use `.resample()`, `.rolling()`, `.shift()`. Always localize timezones.
  8. **Boolean Indexing**: Combine conditions with `&` / `|` (not `and` / `or`), wrapping each in parentheses. Use `.query()` for complex filters.
  9. **Read/Write**: Specify `dtype`, `parse_dates`, `usecols` in `pd.read_csv()`. Use Parquet for large datasets. Use `pd.ExcelWriter` with `engine='openpyxl'` for Excel output.
  10. **Duplicates**: Use `.duplicated()` and `.drop_duplicates()` with explicit `subset` and `keep` parameters.

## Polars for High-Performance Analytics
  1. **When to Use Polars**: Use Polars for datasets > 1GB, when lazy evaluation is needed, or when query optimization matters. Use Pandas for small datasets (< 100MB) or prototyping.
  2. **Lazy Evaluation**: Always use `pl.scan_csv()` / `pl.scan_parquet()` for lazy loading. Chain transformations before `.collect()`.
  3. **Expressions API**: Use Polars expressions (`pl.col()`, `pl.lit()`, `pl.when().then().otherwise()`) instead of Python functions.
  4. **Type System**: Use `pl.Date`, `pl.Datetime`, `pl.Decimal` for financial data. Cast explicitly with `.cast()`.
  5. **Streaming**: For datasets exceeding memory, use `streaming=True` in `.collect()`.
  6. **GroupBy & Aggregations**: Use `df.group_by('key').agg([...])` for multi-aggregation. Use `over()` for window functions.
  7. **Joining**: Prefer `df.join(other, on='key', how='inner')`. Validate join cardinality before joining.
  8. **I/O**: Use Parquet as default. Use `sink_parquet(path, partition_by=[...])` for partitioned writes.

## NumPy for Numerical Computing
  1. **Vectorization**: Replace all Python loops with NumPy array operations. Use broadcasting rules explicitly.
  2. **Financial Calculations**: Use `np.npv()`, `np.irr()`, `np.pmt()`, `np.fv()` for time-value-of-money. Use `np.percentile()` for risk metrics (VaR, CVaR).
  3. **Random Number Generation**: Always seed with `np.random.default_rng(seed)` for reproducibility.
  4. **Broadcasting**: Leverage broadcasting for scalar-array operations. Use `np.where()` for conditional element-wise operations.

## Data Visualization
  1. **Figure Setup**: Use `fig, ax = plt.subplots(figsize=(10, 6))` for explicit axes control.
  2. **Financial Chart Types**: Line plots for time series, bar charts for comparisons, stacked area for composition, heatmaps for correlations, box plots for distributions.
  3. **Styling**: Use `seaborn.set_style('whitegrid')` for business charts. Green for positive, red for negative, blue for neutral.
  4. **Formatting**: Format y-axis with currency formatter. Rotate date labels. Add `plt.tight_layout()` before saving.
  5. **Output**: Save as SVG for reports, PNG (300 DPI) for presentations.

## Excel Integration
  1. **Reading**: Use `pd.read_excel()` with `sheet_name`, `usecols`, `dtype`. Use `openpyxl.load_workbook(read_only=True)` for large files.
  2. **Writing**: Use `pd.ExcelWriter` with `engine='openpyxl'` for multi-sheet output. Apply number formats, column widths, conditional formatting, freeze panes.
  3. **Formula Preservation**: When modifying Excel files, preserve existing formulas by only updating data cells.
  4. **xlwings**: Use `xw.Book()` for real-time Excel automation (macros, UDFs).

## Machine Learning for Data Analysis
  1. **Preprocessing**: Always use `Pipeline` and `ColumnTransformer`. Scale with `StandardScaler` for regression, `MinMaxScaler` for neural networks.
  2. **Train-Test Split**: Use `TimeSeriesSplit` for financial time series. Use `StratifiedKFold` for imbalanced classification.
  3. **Model Selection**: Start with simple baselines. Use `RandomForest` for tabular data. Use `GradientBoosting` for structured financial data.
  4. **Evaluation**: Use MAE and RMSE for regression. Use `r2_score` cautiously for non-stationary data.
  5. **Feature Engineering**: Create lag features (`.shift(1)`, `.shift(12)`), rolling window features, ratio features.
  6. **Cross-Validation**: Use `TimeSeriesSplit` for financial data. Never use random shuffle CV on time series.

## Financial Data Processing
  1. **Data Validation**: Validate on load — check for negative amounts, verify date ranges, confirm currency consistency.
  2. **Currency Handling**: Store currency as a separate column. Use `Decimal` for precision-critical calculations.
  3. **Time Series Alignment**: Align all time series to a common date range. Forward-fill market data, not fundamental data.
  4. **Aggregation Hierarchy**: Build daily → monthly → quarterly → annual. Document the aggregation method.
  5. **Anomaly Detection**: Flag values beyond 3 standard deviations from rolling mean. Investigate outliers before removing.
  6. **Reproducibility**: Set random seeds globally. Log package versions. Never hard-code file paths.

## Jupyter Notebook Best Practices
  1. **Structure**: Title → context → setup → load → profile → analysis → conclusions. Keep under 500 lines. Use markdown cells generously — a reader should understand the narrative without reading code comments.
  2. **Setup Cell**: All imports, config, magic commands, path constants, and seeds in the first code cell. Use `pathlib.Path` for repo-relative paths (not `os.path` or hard-coded strings).
  3. **Data Loading**: Validate on load — assert non-empty, check for duplicates, print shape and date range. Never silently swallow load failures.
  4. **Profiling**: Use `quick_profile()` for inline exploration. Use `ydata-profiling` (`ProfileReport`) for comprehensive EDA — but only run once per dataset (cache the output HTML).
  5. **Visualization**: Use `%matplotlib inline`. Limit charts per notebook to < 20. Save all figures to an `output/` directory with descriptive names. Use `plt.savefig(..., dpi=300, bbox_inches='tight')` before `plt.show()`.
  6. **Output Management**: Use `display()` for DataFrames. Clear large intermediate outputs before saving (Cell → All Output → Clear before sharing).
  7. **Export**: Save analysis results as Parquet (preferred) or CSV to `output/` for downstream use (Airflow tasks, dbt models). Never export to absolute paths.
  8. **Reproducibility**: Set random seeds in the setup cell. Log package versions with `pip freeze` in a markdown cell if the analysis is sensitive to versions.
  9. **Kernel Hygiene**: Restart kernel and run all cells before sharing (Kernel → Restart & Run All). Use `%autoreload 2` for development with imported modules. Never commit `.ipynb` outputs — clear them before git commit.
  10. **Naming**: Use descriptive notebook names: `01_data_profiling.ipynb`, `02_revenue_analysis.ipynb` (prefix with sequence order).
  11. **Length**: If a notebook exceeds 500 lines, split it. Extract reusable functions to a `.py` module in the same directory and import them.
  12. **Secrets**: Never hard-code credentials or API keys. Use environment variables loaded from `.env` (git-ignored).
