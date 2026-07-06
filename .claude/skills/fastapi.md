---
name: fastapi
description: FastAPI development skills and shortcuts
paths:
  - api/
---

# FastAPI Skills

Quick reference for common FastAPI operations and best practices.

## Application Structure

### Basic App Setup
```python
# main.py
from fastapi import FastAPI

app = FastAPI(
    title="Data Pipeline API",
    description="API for financial data pipeline",
    version="1.0.0"
)

@app.get("/")
async def root():
    return {"message": "Hello World"}
```

### With Routers
```python
# main.py
from fastapi import FastAPI
from api.routers import transactions, health

app = FastAPI(
    title="Data Pipeline API",
    description="API for financial data pipeline",
    version="1.0.0"
)

app.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
app.include_router(health.router, prefix="/health", tags=["health"])
```

## Path Operations

### HTTP Methods
```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

# GET - Retrieve data
@app.get("/items/{item_id}")
async def read_item(item_id: int):
    return {"item_id": item_id}

# POST - Create data
@app.post("/items/")
async def create_item(item: Item):
    return item

# PUT - Replace entire resource
@app.put("/items/{item_id}")
async def update_item(item_id: int, item: Item):
    return {"item_id": item_id, **item.dict()}

# PATCH - Partial update
@app.patch("/items/{item_id}")
async def partial_update(item_id: int, item: ItemUpdate):
    return {"item_id": item_id, **item.dict(exclude_unset=True)}

# DELETE - Remove resource
@app.delete("/items/{item_id}")
async def delete_item(item_id: int):
    return {"message": f"Item {item_id} deleted"}
```

### Query Parameters
```python
@app.get("/transactions/")
async def read_transactions(
    skip: int = 0,
    limit: int = 100,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None
):
    # Filter logic here
    return transactions

@app.get("/search/")
async def search_transactions(q: str = None, category: str = None):
    # Search logic
    return results
```

### Path Parameters
```python
@app.get("/transactions/{transaction_id}")
async def read_transaction(transaction_id: str):
    # Get specific transaction
    return transaction

@app.get("/users/{user_id}/transactions/{transaction_id}")
async def read_user_transaction(
    user_id: int, 
    transaction_id: str
):
    # Nested resources
    return transaction
```

### Request Body
```python
from pydantic import BaseModel, Field
from typing import Optional, List

class TransactionBase(BaseModel):
    id: str = Field(..., description="Entry number from CSV")
    date: str = Field(..., description="Transaction date")
    amount: float = Field(..., description="Transaction amount")

class TransactionCreate(TransactionBase):
    pass

class TransactionUpdate(BaseModel):
    date: Optional[str] = None
    amount: Optional[float] = None

@app.post("/transactions/")
async def create_transaction(transaction: TransactionCreate):
    # Create logic
    return transaction

@app.put("/transactions/{transaction_id}")
async def update_transaction(
    transaction_id: str, 
    transaction: TransactionUpdate
):
    # Update logic
    return transaction
```

## Dependencies

### Database Session
```python
# database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "postgresql://user:password@postgres/finance"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### Usage in Path Operations
```python
from fastapi import Depends
from sqlalchemy.orm import Session

@app.get("/transactions/")
async def read_transactions(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    transactions = db.query(TransactionModel).offset(skip).limit(limit).all()
    return transactions
```

### Authentication
```python
# security.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"

security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return username
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
```

### Usage
```python
@app.post("/transactions/")
async def create_transaction(
    transaction: TransactionCreate,
    username: str = Depends(verify_token)
):
    # Only authenticated users can create
    return transaction
```

### Common Query Parameters
```python
def pagination_params(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    return {"skip": skip, "limit": limit}

@app.get("/transactions/")
async def read_transactions(
    pagination: dict = Depends(pagination_params),
    db: Session = Depends(get_db)
):
    transactions = db.query(TransactionModel).offset(pagination["skip"]).limit(pagination["limit"]).all()
    return transactions
```

## Response Models

### Basic Response Model
```python
from pydantic import BaseModel
from typing import List, Optional

class TransactionBase(BaseModel):
    id: str
    date: str
    amount: float

class TransactionResponse(TransactionBase):
    pass

class TransactionListResponse(BaseModel):
    success: bool = True
    data: List[TransactionResponse]
    count: int
    message: Optional[str] = None

@app.get("/transactions/", response_model=TransactionListResponse)
async def read_transactions():
    return {
        "success": True,
        "data": transactions,
        "count": len(transactions),
        "message": "Retrieved transactions successfully"
    }
```

### Error Responses
```python
from fastapi import HTTPException
from pydantic import BaseModel

class ErrorResponse(BaseModel):
    success: bool = False
    error: dict
    message: Optional[str] = None

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail
            },
            "message": "An error occurred"
        }
    )

# Usage in endpoint
@app.get("/transactions/{transaction_id}")
async def read_transaction(transaction_id: str, db: Session = Depends(get_db)):
    transaction = db.query(TransactionModel).filter(TransactionModel.id == transaction_id).first()
    if not transaction:
        raise HTTPException(
            status_code=404,
            detail=f"Transaction {transaction_id} not found"
        )
    return transaction
```

## Middleware

### CORS Middleware
```python
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Custom Middleware
```python
from fastapi import Request
import time

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response
```

## Background Tasks

```python
from fastapi import BackgroundTasks

def send_notification(email: str, message: str):
    # Send email or notification
    pass

@app.post("/transactions/")
async def create_transaction(
    transaction: TransactionCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # Save transaction
    db.add(transaction_model)
    db.commit()
    
    # Send notification in background
    background_tasks.add_task(send_notification, "admin@example.com", "New transaction created")
    
    return transaction
```

## Testing

### TestClient Setup
```python
# tests/test_main.py
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}

def test_create_transaction():
    response = client.post(
        "/transactions/",
        json={"id": "txn_001", "date": "2023-01-01", "amount": 100.0}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert len(data["data"]) == 1
```

### Async Testing
```python
import pytest
from httpx import AsyncClient
from main import app

@pytest.mark.asyncio
async def test_async_transaction():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/transactions/",
            json={"id": "txn_002", "date": "2023-01-02", "amount": 200.0}
        )
        assert response.status_code == 200
```

## Performance Optimization

### Pagination
```python
# Cursor-based pagination (better for large datasets)
@app.get("/transactions/")
async def read_transactions(
    cursor: Optional[str] = None,
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db)
):
    query = db.query(TransactionModel)
    if cursor:
        # Get transactions after cursor
        query = query.filter(TransactionModel.id > cursor)
    transactions = query.limit(limit).all()
    return {
        "data": transactions,
        "next_cursor": transactions[-1].id if transactions else None
    }
```

### Caching
```python
from functools import lru_cache
import time

# Simple in-memory cache (for development)
def get_cache_key(*args, **kwargs):
    return str(args) + str(kwargs)

def cached_export_data(start_date: str, end_date: str):
    # Expensive operation
    time.sleep(2)  # Simulate delay
    return {"data": "exported_data"}

# Cache for 5 minutes
@lru_cache(maxsize=128)
def get_export_data_cached(start_date: str, end_date: str):
    return cached_export_data(start_date, end_date)

@app.get("/export/")
async def export_data(
    start_date: str,
    end_date: str,
    db: Session = Depends(get_db)
):
    # Returns cached result if same params within 5 minutes
    data = get_export_data_cached(start_date, end_date)
    return data
```

### Compression
```python
from fastapi.middleware.gzip import GZipMiddleware

app = FastAPI()
app.add_middleware(GZipMiddleware, minimum_size=1000)  # Compress responses >1000 bytes
```

## Database Optimization

### Connection Pooling
```python
# In database.py
from sqlalchemy import create_engine

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=20,           # Number of connections to maintain
    max_overflow=30,        # Additional connections when needed
    pool_timeout=30,        # Seconds to wait before giving up
    pool_recycle=1800,      # Recycle connections after 30 minutes
    pool_pre_ping=True      # Validate connections before use
)
```

### Query Optimization
```python
# Use indexes appropriately
# In SQLAlchemy model
class TransactionModel(Base):
    __tablename__ = "transactions"
    
    id = Column(String, primary_key=True, index=True)
    date = Column(Date, index=True)  # Index for date filtering
    amount = Column(Float, index=True)  # Index for amount filtering
    account_id = Column(String, ForeignKey("accounts.id"), index=True)

# Efficient querying
def get_transactions_by_date_range(db: Session, start_date: str, end_date: str):
    return db.query(TransactionModel).filter(
        TransactionModel.date >= start_date,
        TransactionModel.date <= end_date
    ).all()
```

## Security Best Practices

### Input Validation
```python
from pydantic import validator

class TransactionBase(BaseModel):
    amount: float
    
    @validator('amount')
    def amount_must_be_positive(cls, v):
        if v < 0:
            raise ValueError('Amount must be positive')
        return v
    
    @validator('id')
    def id_must_be_alphanumeric(cls, v):
        if not v.replace('_', '').isalnum():
            raise ValueError('ID must be alphanumeric with underscores only')
        return v
```

### Rate Limiting
```python
# Using slowapi (would need to be installed)
# from slowapi import Limiter, _rate_limit_exceeded_handler
# from slowapi.util import get_remote_address

# limiter = Limiter(key_func=get_remote_address)
# app.state.limiter = limiter
# app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# @app.limit("10/minute")
# @app.post("/transactions/")
# async def create_transaction(...):
#     pass
```

### Security Headers
```python
from fastapi.middleware.trustedhost import TrustedHostMiddleware

app = FastAPI()
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["example.com", "*.example.com", "localhost"]
)
```

## Development Workflow

### Running Development Server
```bash
# Install dependencies
pip install -r requirements.txt

# Run with auto-reload
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Or using main directly
python -m uvicorn main:app --reload
```

### Docker Development
```bash
# Build and run
docker compose up --build -d fastapi

# View logs
docker compose logs -f fastapi

# Rebuild after changes
docker compose up --build -d fastapi

# Enter container for debugging
docker compose exec fastapi /bin/bash
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_transactions.py

# Run with coverage
pytest --cov=api --cov-report=html

# Run tests in watch mode (development)
ptw  # pytest-watch
```

## Common Endpoints

### Health Check
```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

@app.get("/health/detailed")
async def detailed_health_check(db: Session = Depends(get_db)):
    # Check database connection
    try:
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "healthy" else "unhealthy",
        "database": db_status,
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }
```

### Metrics Endpoint
```python
from prometheus_client import Counter, Histogram, generate_latest
from fastapi.responses import Response

REQUEST_COUNT = Counter(
    'http_requests_total', 
    'Total HTTP Requests', 
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds', 
    'HTTP Request Latency'
)

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    method = request.method
    endpoint = request.url.path
    
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    status_code = response.status_code
    
    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status_code).inc()
    REQUEST_LATENCY.observe(process_time)
    
    return response

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

## Best Practices

### Code Organization
1. Keep route handlers thin; move business logic to service layer
2. Use dependency injection for database connections and external services
3. Group related endpoints in routers with appropriate prefixes and tags
4. Separate concerns: routes → dependencies → services → models
5. Use Pydantic models for request/response validation and serialization
6. Follow REST conventions for endpoint design

### Error Handling
1. Use HTTPException for known error conditions with appropriate status codes
2. Implement global exception handlers for unhandled exceptions
3. Log errors appropriately for debugging without exposing internals
4. Return consistent error response format
5. Handle validation errors gracefully (422 status code)

### Security
1. Never hardcode secrets; use environment variables
2. Implement proper authentication and authorization
3. Validate and sanitize all inputs
4. Use HTTPS in production
5. Implement rate limiting for public endpoints
6. Add security headers (HSTS, CSP, etc.)
7. Regularly update dependencies and check for vulnerabilities

### Performance
1. Implement pagination for list endpoints
2. Use database indexing appropriately
3. Implement caching for expensive operations
4. Use connection pooling for database connections
5. Consider async endpoints for I/O-bound operations
6. Enable gzip compression for large responses
7. Monitor and optimize slow endpoints

### Documentation
1. Use docstrings for all endpoints (appears in automatic docs)
2. Provide clear examples in Pydantic schemas
3. Keep API documentation up to date
4. Document authentication requirements
5. Include error response examples
6. Tag endpoints logically in Swagger UI

### Testing
1. Write unit tests for business logic and utilities
2. Write integration tests for API endpoints
3. Test both valid and invalid inputs
4. Test authentication and authorization flows
5. Mock external dependencies in tests
6. Test performance characteristics under load
7. Use factories or fixtures for test data

### Versioning
1. Consider API versioning in URL path (/api/v1/transactions)
2. Use semantic versioning for releases
3. Deprecate old versions gracefully with warnings
4. Maintain backward compatibility when possible
5. Document breaking changes in release notes