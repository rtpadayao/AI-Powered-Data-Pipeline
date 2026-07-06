# API Module

This module provides a FastAPI-based REST API for serving GL transaction data from CSV files.

## Overview

The API reads transaction data from a CSV file and exposes it as a JSON endpoint compatible with the existing `extract_load.py` script.

## Endpoints

### GET `/transactions`

Returns GL transactions as a JSON array.

**Query Parameters:**

- `limit` (optional): Maximum number of rows to return
- `offset` (optional): Number of rows to skip before starting to collect

**Response Format:**
```json
[
  {
    "id": "29.1",
    "date": "2018-01-22",
    "amount": -2394.0
  },
  {
    "id": "42.1",
    "date": "2018-01-30",
    "amount": -2828.0
  }
]
```

### GET `/health`

Simple health check endpoint.

**Response:**
```json
{
  "status": "ok"
}
```

## Usage

### Development (Recommended for API development)

```bash
# Install dependencies
pip install -r requirements.txt

# Run the API server
uvicorn api.main:app --reload
```

The API will be available at http://localhost:8000
API documentation at http://localhost:8000/docs

### Production / Docker

The API can also be run using Docker Compose as part of the full stack:
```bash
docker compose up -d fastapi
```

## Data Transformation

The API transforms the raw CSV data as follows:

- `id` → Maps to `EntryNo` column
- `date` → Parses `Date` column from format like "Monday, 22 January 2018" to "YYYY-MM-DD"
- `amount` → Calculated as `Debit - Credit` (following accounting convention where debits are positive, credits negative)

## Testing

Run the included test script:
```bash
python test_api.py
```

Or run pytest tests (if added):
```bash
pytest
```