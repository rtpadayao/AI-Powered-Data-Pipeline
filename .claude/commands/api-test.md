---
name: api-test
description: Test the FastAPI endpoint functionality and performance
paths:
  - api/
---

# Test FastAPI Endpoint

This command tests the FastAPI API endpoints for the data pipeline, including functionality, performance, and security checks.

## Usage

```
/api-test [options]
```

## Options

- `--endpoint <endpoint>`: Specific endpoint to test (default: all)
- `--method <method>`: HTTP method to test (GET, POST, etc.)
- `--data <data>`: JSON data to send with request
- `--header <header>`: Custom headers to include
- `--auth <token>`: Bearer token for authentication
- `--count <n>`: Number of requests to make (for load testing)
- `--concurrent <n>`: Number of concurrent requests
- `--url <url>`: Base URL for API (default: http://localhost:8000)
- `--output <format>`: Output format (json, text, table)
- `--save <file>`: Save results to file
- `--help`: Show this help message

## Examples

```bash
# Test all endpoints
/api-test

# Test specific endpoint
/api-test --endpoint /transactions

# Test with pagination parameters
/api-test --endpoint /transactions --data '{"limit": 10, "offset": 0}'

# Test health endpoint
/api-test --endpoint /health

# Load test endpoint (100 requests)
/api-test --endpoint /transactions --count 100

# Concurrent load test
/api-test --endpoint /transactions --count 100 --concurrent 10

# Test with authentication
/api-test --endpoint /transactions --auth <jwt_token>

# Test custom header
/api-test --endpoint /transactions --header "X-API-Key: secret"

# Save results to file
/api-test --endpoint /transactions --save results.json
```

## What It Does

### Functional Testing

1. Verifies endpoint availability and responsiveness
2. Validates HTTP status codes for various scenarios
3. Checks response format and structure
4. Validates data types and constraints
5. Tests error handling and edge cases

### Performance Testing

1. Measures response times (min, max, average, percentiles)
2. Tests throughput (requests per second)
3. Identifies performance bottlenecks
4. Checks for memory leaks under load

### Security Testing

1. Validates authentication requirements
2. Checks for common vulnerabilities (SQL injection, XSS, etc.)
3. Validates input sanitization
4. Checks rate limiting effectiveness

### Data Validation

1. Verifies data matches expected schema
2. Checks for data completeness and correctness
3. Validates business rules and constraints
4. Tests data type conversions

## Implementation

This command uses various testing approaches:

### Basic Functionality
```bash
curl -X GET "http://localhost:8000/transactions?limit=10"
```

### With Data Payload
```bash
curl -X POST "http://localhost:8000/transactions" \
  -H "Content-Type: application/json" \
  -d '{"id": "test1", "date": "2023-01-01", "amount": 100.0}'
```

### Load Testing (using hey or wrk if available)
```bash
hey -n 100 -c 10 "http://localhost:8000/transactions"
```

### Response Validation
- Checks JSON structure against Pydantic schemas
- Validates data types and constraints
- Ensures required fields are present
- Checks for extra unexpected fields

## Environment & Configuration

The test command uses:
- API service running via Docker Compose
- Environment variables from .env and Docker Compose
- Base URL can be overridden with --url option
- Authentication tokens can be provided via --auth option

## Common Test Scenarios

### Endpoint Availability
```bash
# Should return 200 OK
/api-test --endpoint /health

# Should return 200 OK with transaction data
/api-test --endpoint /transactions --data '{"limit": 1}'
```

### Parameter Validation
```bash
# Should return 422 Unprocessable Entity for invalid limit
/api-test --endpoint /transactions --data '{"limit": -1}'

# Should return 422 for missing required fields (POST)
/api-test --endpoint /transactions --method POST --data '{}'

# Should return 200 for valid pagination
/api-test --endpoint /transactions --data '{"limit": 5, "offset": 10}'
```

### Error Handling
```bash
# Non-existent endpoint should return 404
/api-test --endpoint /nonexistent

# Invalid HTTP method should return 405
/api-test --endpoint /transactions --method PUT
```

### Security Checks
```bash
# Missing auth should return 401 or 403 (if protected)
/api-test --endpoint /transactions --method POST

# Invalid auth should return 401
/api-test --endpoint /transactions --method POST --auth "invalid_token"
```

## Troubleshooting

### Connection Issues
```
curl: (7) Failed to connect to localhost port 8000: Connection refused
```
- Ensure API service is running: `docker compose ps fastapi`
- Check if service is healthy: `docker compose logs fastapi`
- Verify port mapping in docker-compose.yml
- Try accessing directly: `curl http://localhost:8000/health`

### Slow Response Times
- Check database query performance
- Review API middleware for bottlenecks
- Monitor system resources (CPU, memory, disk I/O)
- Consider adding caching or database indexing

### Authentication Problems
- Verify token format and expiration
- Check secret key configuration
- Validate token signature and claims
- Ensure auth middleware is properly configured

### Data Mismatch
- Compare API response with expected schema
- Check database values directly
- Verify data transformation logic
- Confirm CSV source data matches expectations

## Best Practices

### Test Organization
1. Test happy path first (valid inputs, expected outputs)
2. Test edge cases (boundary values, empty data, nulls)
3. Test error conditions (invalid inputs, missing auth)
4. Test performance characteristics under load

### Automated Testing
- Integrate with CI/CD pipeline
- Use pytest with httpx for programmatic testing
- Store test data fixtures separately
- Use mocking for external dependencies

### Performance Baselines
- Establish baseline performance metrics
- Test against performance budgets
- Monitor for regressions over time
- Load test before major releases

### Security Testing Regularly
- Schedule regular security scans
- Test authentication and authorization logic
- Validate input validation and sanitization
- Check for information disclosure in error messages

## See Also

- `/run-pipeline` - Run full data pipeline
- `/dbt-run` - Run dbt transformations
- `/airflow-test` - Test Airflow DAGs
- `/run` - Local dev tasks (API server, logs, scripts)