---
name: python
description: Python data analysis patterns, pandas/polars usage, and financial data processing skills
paths:
  - api/**
  - notebooks/**
  - airflow/dags/**
---

# Python Data Analysis Skills

Quick reference for common Python data analysis operations and patterns.

## Pandas Core Operations

### Data Loading
```python
import pandas as pd

# CSV with explicit types and dates
df = pd.read_csv(
    'data/transactions.csv',
    dtype={'id': str, 'category': 'category'},
    parse_dates=['date', 'created_at'],
    usecols=['id', 'date', 'amount', 'category', 'status']
)

# Excel with sheet selection
df = pd.read_excel(
    'data/report.xlsx',
    sheet_name='Transactions',
    engine='openpyxl',
    dtype={'id': str}
)

# Parquet (preferred for large datasets)
df = pd.read_parquet('data/transactions.parquet', columns=['id', 'date', 'amount'])

# SQL database
from sqlalchemy import create_engine
engine = create_engine('postgresql://user:pass@localhost/db')
df = pd.read_sql('SELECT * FROM transactions WHERE date >= %(start)s', engine, params={'start': '2024-01-01'})
```

### Data Export
```python
# CSV
df.to_csv('output.csv', index=False, float_format='%.2f')

# Excel with formatting
with pd.ExcelWriter('output.xlsx', engine='openpyxl') as writer:
    df.to_excel(writer, sheet_name='Data', index=False)
    # Auto-adjust column widths
    worksheet = writer.sheets['Data']
    for i, col in enumerate(df.columns):
        worksheet.column_dimensions[chr(65 + i)].width = max(len(col) + 2, 12)

# Parquet (preserves types, 10x faster than CSV)
df.to_parquet('output.parquet', index=False, compression='snappy')

# SQL
df.to_sql('table_name', engine, if_exists='append', index=False, method='multi', chunksize=10000)
```

### Method Chaining Pattern
```python
# Preferred: chain operations for readability
result = (
    df
    .assign(
        month=lambda x: x['date'].dt.to_period('M'),
        margin=lambda x: x['revenue'] - x['cost']
    )
    .query('status == "completed" and amount > 0')
    .groupby('month')
    .agg(
        total_revenue=('revenue', 'sum'),
        total_cost=('cost', 'sum'),
        transaction_count=('id', 'count'),
        avg_amount=('amount', 'mean')
    )
    .assign(
        margin_pct=lambda x: (x['total_revenue'] - x['total_cost']) / x['total_revenue'] * 100
    )
    .sort_index()
    .reset_index()
)
```

### Column Operations
```python
# Create/update columns with .assign()
df = df.assign(
    year=lambda x: x['date'].dt.year,
    quarter=lambda x: x['date'].dt.quarter,
    yoy_growth=lambda x: x.groupby('category')['amount'].pct_change(12),
    rolling_avg=lambda x: x.groupby('category')['amount'].transform(lambda s: s.rolling(3).mean())
)

# Conditional logic with np.where / np.select
import numpy as np
df['tier'] = np.where(df['amount'] > 10000, 'enterprise',
                     np.where(df['amount'] > 1000, 'business', 'standard'))

conditions = [
    df['margin'] > 0.3,
    df['margin'] > 0.15,
    df['margin'] > 0
]
choices = ['high', 'medium', 'low']
df['margin_tier'] = np.select(conditions, choices, default='negative')
```

### Filtering
```python
# Boolean indexing (preferred for simple filters)
filtered = df[(df['date'] >= '2024-01-01') & (df['status'] == 'active')]

# .query() for complex multi-column filters
filtered = df.query('status == "active" and amount > @min_amount and category in @categories')

# .loc for label-based selection
subset = df.loc[df['date'] >= '2024-01-01', ['id', 'date', 'amount']]

# .isin() for membership
filtered = df[df['category'].isin(['sales', 'marketing', 'operations'])]

# Date range filtering
filtered = df[df['date'].between('2024-01-01', '2024-12-31')]
# Or with explicit bounds (avoids BETWEEN inclusivity issues)
filtered = df[(df['date'] >= '2024-01-01') & (df['date'] < '2025-01-01')]
```

### GroupBy & Aggregation
```python
# Named aggregation (clean output columns)
summary = (
    df
    .groupby(['region', 'product'])
    .agg(
        total_revenue=('revenue', 'sum'),
        avg_margin=('margin', 'mean'),
        unique_customers=('customer_id', 'nunique'),
        first_sale=('date', 'min'),
        last_sale=('date', 'max')
    )
    .reset_index()
)

# Transform (preserves original index)
df['pct_of_group'] = df.groupby('region')['revenue'].transform(lambda x: x / x.sum())

# Filter groups
large_regions = df.groupby('region').filter(lambda x: x['revenue'].sum() > 1000000)

# Multiple group levels with ROLLUP-like behavior
from itertools import combinations
results = []
for n in range(1, len(group_cols) + 1):
    for combo in combinations(group_cols, n):
        agg = df.groupby(list(combo)).agg(total=('amount', 'sum')).reset_index()
        results.append(agg)
```

### Missing Data Handling
```python
# Detection
df.isna().sum()  # Count per column
df[df['amount'].isna()]  # Rows with missing amounts

# Fill strategies
df['amount'] = df['amount'].fillna(0)  # Constant fill
df['amount'] = df['amount'].ffill()  # Forward fill (time series)
df['amount'] = df['amount'].bfill()  # Back fill
df['amount'] = df['amount'].interpolate()  # Linear interpolation
df['amount'] = df.groupby('category')['amount'].transform(lambda x: x.fillna(x.mean()))  # Group fill

# Drop
df = df.dropna(subset=['id', 'amount'])  # Drop rows with critical nulls
df = df.dropna(axis=1, thresh=len(df) * 0.5)  # Drop columns with >50% nulls
```

### Time Series Operations
```python
# Set datetime index
df['date'] = pd.to_datetime(df['date'])
df = df.set_index('date').sort_index()

# Resampling
monthly = df.resample('M').agg({'revenue': 'sum', 'cost': 'sum'})
weekly = df.resample('W').mean()
quarterly = df.resample('Q').sum()

# Rolling windows
df['ma_7d'] = df['amount'].rolling(7).mean()
df['rolling_std_30d'] = df['amount'].rolling(30).std()
df['rolling_sum_12m'] = df['revenue'].rolling(12).sum()

# Lag features
df['prev_month'] = df['amount'].shift(1)
df['yoy_change'] = df['amount'].shift(12)
df['pct_change'] = df['amount'].pct_change()

# Date range generation
full_range = pd.date_range('2024-01-01', '2024-12-31', freq='D')
df = df.reindex(full_range)  # Fill gaps in time series
```

### Pivot & Reshape
```python
# Pivot table
pivot = df.pivot_table(
    values='amount',
    index='region',
    columns='quarter',
    aggfunc='sum',
    margins=True,  # Add row/column totals
    fill_value=0
)

# Melt (wide to long)
melted = pd.melt(
    df,
    id_vars=['id', 'date'],
    value_vars=['q1', 'q2', 'q3', 'q4'],
    var_name='quarter',
    value_name='revenue'
)

# Cross-tabulation
ct = pd.crosstab(df['region'], df['product'], values=df['amount'], aggfunc='sum', margins=True)
```

## Polars for High Performance

### When to Use Polars
- Datasets > 1GB where pandas is slow
- Need lazy evaluation for query optimization
- Streaming large files that don't fit in memory
- ETL pipelines with complex transformations

### Lazy Evaluation Pattern
```python
import polars as pl

# Scan (lazy) - doesn't load data yet
lf = pl.scan_parquet('data/transactions.parquet')

# Build query plan
result = (
    lf
    .filter(pl.col('date') >= pl.lit('2024-01-01'))
    .with_columns([
        (pl.col('revenue') - pl.col('cost')).alias('margin'),
        pl.col('date').dt.month().alias('month')
    ])
    .group_by(['region', 'month'])
    .agg([
        pl.col('revenue').sum().alias('total_revenue'),
        pl.col('margin').mean().alias('avg_margin'),
        pl.col('id').count().alias('transaction_count')
    ])
    .sort(['region', 'month'])
)

# Execute and collect
df = result.collect()

# Stream large dataset (out-of-core)
df = result.collect(streaming=True)
```

### Polars Expressions
```python
# Column operations with expressions
df = df.with_columns([
    (pl.col('revenue') * pl.col('tax_rate')).alias('tax_amount'),
    pl.when(pl.col('amount') > 10000)
      .then(pl.lit('enterprise'))
      .when(pl.col('amount') > 1000)
      .then(pl.lit('business'))
      .otherwise(pl.lit('standard'))
      .alias('tier'),
    pl.col('date').dt.to_period('M').alias('month')
])

# Filtering
filtered = df.filter(
    (pl.col('status') == 'active') &
    (pl.col('amount') > 0) &
    pl.col('category').is_in(['sales', 'marketing'])
)

# Window functions
df = df.with_columns([
    pl.col('amount').mean().over('region').alias('region_avg'),
    pl.col('amount').rank().over('region').alias('region_rank'),
    pl.col('amount').shift(1).over('customer_id').alias('prev_amount')
])
```

### Polars I/O
```python
# Read
df = pl.read_csv('data.csv', dtypes={'id': pl.Utf8}, try_parse_dates=True)
df = pl.read_parquet('data.parquet', columns=['id', 'date', 'amount'])
df = pl.read_excel('data.xlsx', sheet_name='Sheet1')

# Write
df.write_parquet('output.parquet', compression='snappy')
df.write_csv('output.csv')

# Multiple files
df = pl.scan_parquet('data/*.parquet').collect()
```

## NumPy for Financial Calculations

### Time Value of Money
```python
import numpy as np
import numpy_financial as npf

# Present Value
pv = npf.pv(rate=0.05, nper=10, pmt=0, fv=10000)  # → -6139.13

# Future Value
fv = npf.fv(rate=0.05, nper=10, pmt=-1000, pv=0)  # → 15528.23

# Net Present Value
cashflows = [-10000, 3000, 4000, 5000, 6000]
npv = npf.npv(rate=0.1, values=cashflows)  # → 3238.67

# Internal Rate of Return
irr = npf.irr(cashflows)  # → 0.1986 (19.86%)

# Loan payment
pmt = npf.pmt(rate=0.06/12, nper=360, pv=300000)  # → -1798.65
```

### Monte Carlo Simulation
```python
rng = np.random.default_rng(42)  # Always seed for reproducibility

# Simulate stock returns
n_simulations = 10000
n_days = 252
mean_daily_return = 0.0005
daily_volatility = 0.02

daily_returns = rng.normal(mean_daily_return, daily_volatility, (n_simulations, n_days))
price_paths = 100 * np.exp(np.cumsum(daily_returns, axis=1))

# Value at Risk (VaR)
final_returns = price_paths[:, -1] - 100
var_95 = np.percentile(final_returns, 5)  # 5% worst case
var_99 = np.percentile(final_returns, 1)  # 1% worst case

# Conditional VaR (Expected Shortfall)
cvar_95 = final_returns[final_returns <= var_95].mean()
```

### Vectorized Operations
```python
# Broadcasting for scalar-array operations
revenue = np.array([100000, 150000, 200000])
tax_rate = 0.25
tax_amount = revenue * tax_rate  # Broadcasting

# Element-wise conditional
margin = np.where(revenue > 150000, 0.35, 0.25)

# Percentile calculations
p5 = np.percentile(data, 5)
p25 = np.percentile(data, 25)
p50 = np.percentile(data, 50)  # Median
p75 = np.percentile(data, 75)
p95 = np.percentile(data, 95)
```

## Data Visualization

### Matplotlib Financial Charts
```python
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# Time series line plot
ax = axes[0, 0]
ax.plot(df['date'], df['revenue'], color='#2196F3', linewidth=1.5, label='Revenue')
ax.plot(df['date'], df['cost'], color='#F44336', linewidth=1.5, label='Cost')
ax.fill_between(df['date'], df['revenue'], df['cost'], alpha=0.1, color='#4CAF50')
ax.set_title('Revenue vs Cost Over Time')
ax.legend()
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f'${x:,.0f}'))
ax.tick_params(axis='x', rotation=45)

# Bar chart
ax = axes[0, 1]
colors = ['#4CAF50' if v > 0 else '#F44336' for v in df['margin']]
ax.bar(df['category'], df['margin'], color=colors)
ax.axhline(y=0, color='black', linewidth=0.5)
ax.set_title('Margin by Category')
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f'${x:,.0f}'))

# Histogram
ax = axes[1, 0]
ax.hist(df['amount'], bins=50, color='#2196F3', alpha=0.7, edgecolor='white')
ax.axvline(df['amount'].mean(), color='red', linestyle='--', label=f'Mean: ${df["amount"].mean():,.0f}')
ax.set_title('Transaction Amount Distribution')
ax.legend()

# Correlation heatmap
ax = axes[1, 1]
corr = df[['revenue', 'cost', 'margin', 'volume']].corr()
im = ax.imshow(corr, cmap='RdBu_r', vmin=-1, vmax=1)
ax.set_xticks(range(len(corr.columns)))
ax.set_yticks(range(len(corr.columns)))
ax.set_xticklabels(corr.columns, rotation=45)
ax.set_yticklabels(corr.columns)
for i in range(len(corr)):
    for j in range(len(corr)):
        ax.text(j, i, f'{corr.iloc[i, j]:.2f}', ha='center', va='center')
plt.colorbar(im, ax=ax)
ax.set_title('Correlation Matrix')

plt.tight_layout()
plt.savefig('financial_dashboard.png', dpi=300, bbox_inches='tight')
plt.show()
```

### Seaborn Statistical Plots
```python
import seaborn as sns

sns.set_style('whitegrid')
sns.set_palette('husl')

fig, axes = plt.subplots(1, 3, figsize=(18, 5))

# Box plot
sns.boxplot(data=df, x='region', y='margin', ax=axes[0])
axes[0].set_title('Margin Distribution by Region')

# Violin plot
sns.violinplot(data=df, x='category', y='amount', ax=axes[1])
axes[1].set_title('Amount Distribution by Category')

# Scatter with regression
sns.regplot(data=df, x='revenue', y='cost', ax=axes[2], scatter_kws={'alpha': 0.3})
axes[2].set_title('Revenue vs Cost (with regression)')

plt.tight_layout()
```

## Excel Integration

### Reading Excel
```python
# Simple read
df = pd.read_excel('data.xlsx', sheet_name='Sheet1')

# Multiple sheets
all_sheets = pd.read_excel('data.xlsx', sheet_name=None)  # Returns dict of DataFrames

# Memory-efficient streaming read
from openpyxl import load_workbook
wb = load_workbook('large_file.xlsx', read_only=True)
ws = wb['Sheet1']
data = ws.values
headers = next(data)
df = pd.DataFrame(data, columns=headers)
wb.close()
```

### Writing Excel with Formatting
```python
from openpyxl.styles import Font, PatternFill, Alignment, numbers
from openpyxl.utils.dataframe import dataframe_to_rows

with pd.ExcelWriter('output.xlsx', engine='openpyxl') as writer:
    # Write data
    df.to_excel(writer, sheet_name='Summary', index=False, startrow=2)

    # Get workbook and worksheet
    wb = writer.book
    ws = writer.sheets['Summary']

    # Title
    ws['A1'] = 'Financial Summary Report'
    ws['A1'].font = Font(size=16, bold=True)

    # Header formatting
    header_fill = PatternFill(start_color='1F4E79', fill_color='1F4E79', fill_type='solid')
    header_font = Font(color='FFFFFF', bold=True)
    for cell in ws[3]:  # Row 3 is header (after title)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center')

    # Number formatting
    for row in ws.iter_rows(min_row=4, max_row=ws.max_row, min_col=2, max_col=4):
        for cell in row:
            cell.number_format = '#,##0.00'

    # Auto-adjust column widths
    for column in ws.columns:
        max_length = max(len(str(cell.value or '')) for cell in column)
        ws.column_dimensions[column[0].column_letter].width = max_length + 4

    # Freeze panes
    ws.freeze_panes = 'A4'

    # Add conditional formatting
    from openpyxl.formatting.rule import CellIsRule
    red_fill = PatternFill(start_color='FFC7CE', fill_color='FFC7CE', fill_type='solid')
    green_fill = PatternFill(start_color='C6EFCE', fill_color='C6EFCE', fill_type='solid')
    ws.conditional_formatting.add('D4:D100', CellIsRule(operator='lessThan', formula=['0'], fill=red_fill))
    ws.conditional_formatting.add('D4:D100', CellIsRule(operator='greaterThan', formula=['0'], fill=green_fill))
```

## Machine Learning Patterns

### Preprocessing Pipeline
```python
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer

# Define column types
numeric_features = ['amount', 'volume', 'duration']
categorical_features = ['region', 'category', 'channel']

# Build preprocessing pipeline
preprocessor = ColumnTransformer(
    transformers=[
        ('num', Pipeline([
            ('imputer', SimpleImputer(strategy='median')),
            ('scaler', StandardScaler())
        ]), numeric_features),
        ('cat', Pipeline([
            ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
            ('encoder', OneHotEncoder(handle_unknown='ignore'))
        ]), categorical_features)
    ]
)

# Full pipeline with model
from sklearn.ensemble import RandomForestRegressor
pipeline = Pipeline([
    ('preprocessor', preprocessor),
    ('model', RandomForestRegressor(n_estimators=100, random_state=42))
])
```

### Time Series Cross-Validation
```python
from sklearn.model_selection import TimeSeriesSplit

tscv = TimeSeriesSplit(n_splits=5, test_size=30)  # 30-day test windows

for train_idx, test_idx in tscv.split(X):
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
    # Train and evaluate
```

### Feature Engineering for Financial Data
```python
# Lag features
for lag in [1, 7, 14, 30]:
    df[f'amount_lag_{lag}'] = df.groupby('customer_id')['amount'].shift(lag)

# Rolling features
for window in [7, 30, 90]:
    df[f'amount_rolling_mean_{window}'] = df.groupby('customer_id')['amount'].transform(
        lambda x: x.rolling(window, min_periods=1).mean()
    )
    df[f'amount_rolling_std_{window}'] = df.groupby('customer_id')['amount'].transform(
        lambda x: x.rolling(window, min_periods=1).std()
    )

# Date features
df['day_of_week'] = df['date'].dt.dayofweek
df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
df['month_end'] = df['date'].dt.is_month_end.astype(int)
df['quarter'] = df['date'].dt.quarter
```

## Data Validation

### Schema Validation with Pandera
```python
import pandera as pa

schema = pa.DataFrameSchema({
    "id": pa.Column(str, unique=True, nullable=False),
    "date": pa.Column(pa.DateTime, nullable=False),
    "amount": pa.Column(float, pa.Check.greater_than_or_equal_to(0)),
    "category": pa.Column(str, pa.Check.isin(["sales", "marketing", "ops"])),
    "region": pa.Column(str, nullable=True)
})

validated_df = schema.validate(df)
```

### Quick Profiling
```python
def profile_dataframe(df):
    """Quick data profiling for financial datasets."""
    print(f"Shape: {df.shape}")
    print(f"\nTypes:\n{df.dtypes}")
    print(f"\nNulls:\n{df.isna().sum()}")
    print(f"\nNumeric Summary:\n{df.describe()}")
    print(f"\nDuplicates: {df.duplicated().sum()}")
    if 'amount' in df.columns:
        print(f"\nAmount: min={df['amount'].min():.2f}, max={df['amount'].max():.2f}, "
              f"mean={df['amount'].mean():.2f}, sum={df['amount'].sum():.2f}")

profile_dataframe(df)
```

## Jupyter Notebook Patterns

### Notebook Structure Template
```
Cell 1 [Markdown]: # Title — One-line summary of the analysis
Cell 2 [Markdown]: ## Context — What question this answers, data sources
Cell 3 [Code]:     # Setup — imports, config, magic commands
Cell 4 [Code]:     # Data Load — with validation
Cell 5 [Code]:     # Quick Profile — shape, types, nulls
...
Cell N-2 [Code]:   # Analysis / Visualization
Cell N-1 [Code]:   # Export (if needed)
Cell N [Markdown]: ## Conclusions — Key findings, next steps
```

### Notebook Setup Cell
```python
# Cell 1: Setup
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from pathlib import Path

# Display config
pd.set_option('display.max_columns', 50)
pd.set_option('display.max_rows', 100)
pd.set_option('display.float_format', '{:,.2f}'.format)
pd.set_option('display.width', 200)

# Plot config
plt.style.use('seaborn-v0_8-whitegrid')
%matplotlib inline
%load_ext autoreload
%autoreload 2

# Path constants (repo-relative)
NOTEBOOKS_DIR = Path.cwd()
DATA_DIR = NOTEBOOKS_DIR.parent / 'infrastructure' / 'raw_storage'
OUTPUT_DIR = NOTEBOOKS_DIR.parent / 'output'
OUTPUT_DIR.mkdir(exist_ok=True)

# Reproducibility
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)
```

### Data Loading Cell Pattern
```python
# Cell 2: Data Load with validation
raw_path = DATA_DIR / 'transactions.csv'

df = pd.read_csv(
    raw_path,
    dtype={'id': str, 'category': 'category'},
    parse_dates=['date', 'created_at'],
    usecols=['id', 'date', 'amount', 'category', 'status', 'region']
)

# Quick validation
assert not df.empty, "DataFrame is empty — check source file"
assert df['id'].is_duplicate == 0, "Duplicate IDs found"
print(f"Loaded: {df.shape[0]:,} rows, {df.shape[1]} columns")
print(f"Date range: {df['date'].min()} to {df['date'].max()}")
df.head()
```

### Profiling Cell Pattern
```python
# Cell 3: Quick profile (use ydata-profiling for deep dives)
def quick_profile(df: pd.DataFrame) -> None:
    """Inline profiling for notebook exploration."""
    print(f"Shape: {df.shape[0]:,} rows x {df.shape[1]} columns\n")
    print(f"Memory: {df.memory_usage(deep=True).sum() / 1e6:.1f} MB\n")
    print("Types:")
    print(df.dtypes.to_string())
    print(f"\nNulls ({df.isna().any().sum()} columns with nulls):")
    null_counts = df.isna().sum()
    print(null_counts[null_counts > 0].to_string())
    print(f"\nDuplicates: {df.duplicated().sum():,}\n")
    print(df.describe().to_string())

quick_profile(df)

# For comprehensive profiling (run once, takes time):
# from ydata_profiling import ProfileReport
# profile = ProfileReport(df, title="Data Profile", explorative=True)
# profile.to_notebook_iframe()
```

### Visualization Cell Patterns
```python
# Single chart pattern
fig, ax = plt.subplots(figsize=(12, 6))
monthly = df.resample('M', on='date')['amount'].sum()
ax.plot(monthly.index, monthly.values, color='#2196F3', linewidth=2)
ax.fill_between(monthly.index, monthly.values, alpha=0.1, color='#2196F3')
ax.set_title('Monthly Transaction Volume', fontsize=14, fontweight='bold')
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f'${x:,.0f}'))
ax.set_xlabel('')
plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'monthly_volume.png', dpi=300, bbox_inches='tight')
plt.show()
```

```python
# Multi-panel dashboard pattern
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# Panel 1: Time series
ax = axes[0, 0]
ax.plot(df['date'], df['amount'], alpha=0.3, linewidth=0.5)
ax.plot(df['date'], df['amount'].rolling(7).mean(), color='#F44336', linewidth=2)
ax.set_title('Daily Amount (7-day MA)')

# Panel 2: Distribution
ax = axes[0, 1]
ax.hist(df['amount'], bins=50, color='#2196F3', alpha=0.7, edgecolor='white')
ax.axvline(df['amount'].mean(), color='red', linestyle='--')
ax.set_title('Amount Distribution')

# Panel 3: Breakdown
ax = axes[1, 0]
by_region = df.groupby('region')['amount'].sum().sort_values()
by_region.plot.barh(ax=ax, color='#4CAF50')
ax.set_title('Total by Region')

# Panel 4: Table
ax = axes[1, 1]
ax.axis('off')
summary = df.describe().round(2)
table = ax.table(cellText=summary.values, colLabels=summary.columns,
                 rowLabels=summary.index, loc='center', cellLoc='center')
table.auto_set_font_size(False)
table.set_fontsize(8)
ax.set_title('Summary Statistics', pad=20)

plt.suptitle('Transaction Dashboard', fontsize=16, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'dashboard.png', dpi=300, bbox_inches='tight')
plt.show()
```

### Interactive Widgets
```python
from ipywidgets import interact, widgets

@interact(
    region=widgets.Dropdown(options=['All'] + df['region'].unique().tolist()),
    date_range=widgets.DateRangePicker(description='Date Range'),
    log_scale=widgets.Checkbox(value=False, description='Log scale')
)
def explore(region, date_range, log_scale):
    mask = pd.Series(True, index=df.index)
    if region != 'All':
        mask &= df['region'] == region
    if date_range:
        mask &= df['date'].between(*date_range)
    subset = df[mask]

    fig, ax = plt.subplots(figsize=(10, 5))
    daily = subset.resample('D', on='date')['amount'].sum()
    ax.plot(daily.index, daily.values)
    if log_scale:
        ax.set_yscale('log')
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f'${x:,.0f}'))
    ax.set_title(f'{region} — {len(subset):,} records')
    plt.tight_layout()
    plt.show()
```

### Export Cell Pattern
```python
# Export results for downstream use (Airflow, dbt, etc.)
result = (
    df
    .groupby([pd.Grouper(key='date', freq='M'), 'region'])
    .agg(total_amount=('amount', 'sum'), txn_count=('id', 'count'))
    .reset_index()
)

# Save to parquet (preferred — preserves types)
result.to_parquet(OUTPUT_DIR / 'monthly_by_region.parquet', index=False)

# Or CSV for inspection
result.to_csv(OUTPUT_DIR / 'monthly_by_region.csv', index=False)

print(f"Exported {len(result):,} rows to {OUTPUT_DIR}")
result.head()
```

### Debugging Cell Helpers
```python
# Use %debug after an exception, or embed breakpoints:
%pdb on          # auto-debug on exception

# Quick shape/type checks during development:
print(f"{df.shape=} {df.dtypes.value_counts().to_dict()=}")
print(f"Memory: {df.memory_usage(deep=True).sum() / 1e6:.1f} MB")

# Check for common issues:
assert df['date'].is_monotonic_increasing or not df['date'].is_monotonic_decreasing, \
    "Dates not sorted — use df = df.sort_values('date')"
```

## Notebook Development Workflow

When developing notebooks in this project:
1. Start from the structure template (above) — fill in markdown context before writing code
2. Use repo-relative `pathlib.Path` constants (never hard-coded absolute paths)
3. Profile before analyzing — run `quick_profile()` before any transformations
4. Save all figures to `output/` with descriptive names
5. Export derived datasets as Parquet for downstream tasks (Airflow, dbt)
6. Clear outputs before sharing: Cell → All Output → Clear
7. Restart & Run All before committing to verify reproducibility

## Best Practices

See `python_rules.md` for the full set of Python rules and conventions. The rules file is the authoritative source for:
- Pandas/Polars/NumPy patterns
- Data visualization standards
- Excel integration practices
- ML preprocessing patterns
- Financial data processing rules
- Jupyter notebook structure, hygiene, and naming conventions

This skill file focuses on executable code examples that demonstrate the rules in practice.
