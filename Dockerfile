# Base image: lightweight Python 3.11
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Install system dependencies (for psycopg2, dbt, Airflow)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files (DAGs, dbt models, scripts)
COPY . .

# Expose Airflow webserver port
EXPOSE 8080

# Default command: start Airflow webserver
CMD ["airflow", "webserver", "--port", "8080"]
