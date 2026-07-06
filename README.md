# AI-Powered Airflow Data Pipeline

A robust, automated data pipeline that leverages Airflow for orchestration, dbt for transformation, and FastAPI for both data ingestion (as a validation gateway) and data serving, with AI-powered enhancements for data quality, monitoring, and optimization.

## 📋 Overview

This project implements a modern data platform using industry-standard tools:
- **Apache Airflow**: Workflow orchestration and scheduling
- **dbt (data build tool)**: Data transformation and testing
- **FastAPI**: High-performance API for data serving
- **PostgreSQL**: Reliable data storage
- **Claude Code**: AI-powered development assistance with custom agents and skills

The pipeline follows a layered architecture where data flows: Sources → FastAPI (Ingestion Gateway for validation/authentication) → PostgreSQL → dbt (staging → refined → marts transformation layers) → FastAPI (Serving Layer for consuming transformed data) → Power BI/Other Consumers, ensuring data quality, traceability, and scalability.

## 🏗️ Project Structure

```
ai-powered-airflow/
├── .claude/                 # Claude Code customizations (agents, commands, rules, skills)
├── airflow/                 # Orchestration layer (DAGs, logs, plugins)
├── api/                     # FastAPI service for data delivery
├── dbt_project/             # dbt transformation project (staging/refined/marts)
├── infrastructure/          # Database initialization and raw data storage
├── notebooks/               # Exploratory data analysis and profiling
├── docker-compose.yml       # Service orchestration
├── .env                     # Environment variables
├── CLAUDE.md                # Project setup and development guidance
├── project_roadmap.md       # Planned features and milestones
├── decisions.md             # Architectural decision log
├── housekeeper.md           # Project cleanup and organization guidelines
└── dependency-manager.md    # Dependency management guidelines
```

## 🚀 Quick Start

### 1. Environment Setup
```bash
# Copy environment variables (if needed)
cp .env.example .env  # if .env.example exists
# Edit .env with your credentials
```

### 2. Start the Full Stack
```bash
docker compose up -d
```

### 3. Access Services
- **Airflow UI**: http://localhost:8080
- **pgAdmin**: http://localhost:5050 (credentials from .env)
- **FastAPI**: http://localhost:8000 (if built for development)
- **Postgres**: localhost:5432 (internal only; use pgAdmin or add port mapping in compose for direct access)

## 🔧 Development Workflow

### Airflow
- DAGs are located in `airflow/dags/`
- Mounted into the container; changes appear immediately in the webserver (if containers are restarted or touch the file to trigger reload)
- To develop a new DAG:
  1. Add Python file to `airflow/dags/`
  2. Restart the webserver/scheduler or touch the file to trigger a reload:
     ```bash
     docker compose restart airflow-webserver airflow-scheduler
     ```
  3. View logs:
     ```bash
     docker compose logs -f airflow-webserver
     docker compose logs -f airflow-scheduler
     ```

### dbt (Data Transformation)
- dbt project lives in `dbt/project/` (mounted into the dbt service)
- Profiles are in `dbt/profiles.yml` (mounted read-only)
- Commands are run via `docker compose run --rm dbt <command>`
- Common dbt workflow:
  - Build models: `docker compose run --rm dbt run`
  - Test models: `docker compose run --rm dbt test`
  - Generate docs: `docker compose run --rm dbt docs generate`
  - Seed data: `docker compose run --rm dbt seed`
  - Run specific models: `docker compose run --rm dbt run --models <model_name>`
- dbt models are organized in layers:
  - `staging/`: source-centric, cleaned data
  - `refined/`: business rules, master data
  - `marts/`: domain-centric, ready for consumption

### FastAPI
- The API service serves a dual role in the pipeline:
  1. **Ingestion Gateway**: Validates, authenticates, and preprocesses incoming data before it lands in PostgreSQL (used by `extract_load.py`)
  2. **Serving Layer**: Provides access to dbt-transformed data for consumption by tools like Power BI
- The API service is defined in `api/` (note: docker-compose references `./fastapi` which may be a symlink or misconfiguration; adjust as needed)
- Current entrypoint: `api/main.py` contains both:
  - An ingestion endpoint (`/transactions/raw`) used by `extract_load.py` to fetch and validate data
  - Serving endpoints (`/transactions/marts/*`, `/transactions/refined/*`) for accessing dbt-transformed data
- To run the API locally (outside Docker) for development:
  ```bash
  # Install dependencies
  pip install -r api/requirements.txt  # if exists, otherwise install fastapi, uvicorn, etc.
  
  # Run the server
  uvicorn api.main:app --reload  # assuming app instance named 'app' in main.py
  ```
- If using Docker development mode (as per compose):
  ```bash
  docker compose up fastapi  # builds with target: development and mounts ./fastapi:/app
  ```
- API endpoints should be defined in `api/main.py` or separate router files.
- Validate requests with Pydantic schemas (see `api/schemas.py` if populated).
- Use asynchronous HTTPX calls for external interactions.

### Notebooks
- Exploratory analysis lives in `notebooks/`
- Jupyter notebooks can be run with:
  ```bash
  jupyter lab notebooks/
  ```
- Specific requirements for profiling are in `notebooks/requirements.txt`

## 🧪 Testing

### Airflow
- No specific test suite observed; validate DAGs by:
  - Running `airflow dags test <dag_id> <execution_date>` inside the webserver/scheduler container
  - Triggering DAGs via UI and checking logs

### dbt
- Tests are defined in `dbt/project/models/**/*_test.yml` or as schema tests
- Run all tests:
  ```bash
  docker compose run --rm dbt test
  ```
- Run tests for a specific model:
  ```bash
  docker compose run --rm dbt test --models <model_name>
  ```

### FastAPI
- If tests exist, they may be in `api/` or a `tests/` directory.
- Run with pytest:
  ```bash
  pytest api/
  ```
  or
  ```bash
  pytest tests/
  ```

### General
- Linting/formatting: if configured, use tools like `flake8`, `black`, `isort`. Check for config files (`.flake8`, `pyproject.toml`, etc.).
- No general test command observed; run component-specific tests as above.

## 📚 Key Configuration Files

- `docker-compose.yml`: Defines all services, networks, volumes
- `.env`: Environment variables for services (not committed; see `.env.example` if present)
- `dbt/profiles.yml`: dbt connection profiles (mounted into dbt container)
- `dbt/project/dbt_project.yml`: dbt project configuration

## 🔄 Common Commands Reference

| Purpose | Command |
|---------|---------|
| Start all services | `docker compose up -d` |
| Stop all services | `docker compose down` |
| View service logs | `docker compose logs -f <service_name>` |
| Restart a service | `docker compose restart <service_name>` |
| Run a one-off dbt command | `docker compose run --rm dbt <command>` |
| Access Postgres CLI (if port exposed) | `psql -h localhost -U $DB_USER -d $DB_NAME` |
| Access pgAdmin | Browse to http://localhost:5050 |
| Trigger Airflow DAG via CLI | `docker compose exec airflow-webserver airflow dags trigger <dag_id>` |
| List Airflow DAGs | `docker compose exec airflow-webserver airflow dags list` |
| Run FastAPI tests | `pytest api/` |
| Run dbt docs serve | `docker compose run --rm dbt docs serve` |

## 📑 Documentation

For detailed connection instructions, see:
- [Power BI Connection Guide](docs/power_bi_connection.md) - Complete guide for connecting Power BI to the pipeline via direct PostgreSQL or FastAPI endpoints
- [Pipeline Design Documentation](docs/pipeline_design.md) - Overview of standard and API-wrapper architectural patterns

## 🤖 Claude Code Specifics

This project includes custom Claude Code enhancements for improved development experience:

### Agents
Specialized subagents for domain-specific tasks:
- `airflow-expert`: Airflow orchestration assistance
- `api-developer`: FastAPI development guidance
- `data-engineer`: Data engineering task support
- `database-admin`: PostgreSQL administration and optimization
- `dbt-specialist`: dbt transformation modeling
- `housekeeper`: Project cleanup and organization recommendations
- `dependency-manager`: Dependency management guidance
- `markdown`: Markdown formatting and best practices

### Commands
Custom slash commands for common tasks:
- `/run-pipeline`: Execute the full data pipeline
- `/dbt-run`: Run dbt transformations with testing and documentation
- `/airflow-test`: Test and validate Airflow DAGs
- `/api-test`: Test FastAPI endpoint functionality and performance

### Rules
Path-specific lazy-loaded rules that provide guidance when editing files:
- `.claude/rules/dbt.md`: Rules for SQL formatting and layering
- `.claude/rules/airflow.md`: Rules for Airflow DAG development

### Skills
Specialized skills for extended functionality:
- `docker`: Docker container management
- `airflow`: Airflow-specific operations
- `fastapi`: FastAPI development assistance
- `dbt`: dbt transformation support
- `postgres`: PostgreSQL administration

## 📈 Features

- **Modular Architecture**: Separation of concerns between ingestion, orchestration, transformation, and consumption
- **Idempotency**: Pipeline tasks can be safely retried without side effects
- **AI-Powered Enhancements**: Planned features for anomaly detection, self-healing pipelines, and dynamic resource allocation
- **Comprehensive Testing**: Built-in validation at each layer of the pipeline
- **Documentation**: Auto-generated API and dbt documentation
- **Monitoring**: Hooks for integrating with observability tools
- **Security**: Best practices for credential management and data protection

## 📅 Roadmap

See [project_roadmap.md](project_roadmap.md) for planned features, improvements, and milestones.

## 📜 Decisions

See [decisions.md](decisions.md) for architectural decision records documenting significant choices made during development.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a pull request

## 📄 License

[Specify your license here]

## 🙏 Acknowledgments

- The open-source communities behind Airflow, dbt, FastAPI, and PostgreSQL
- Anthropic for Claude Code and its extensibility features
- Contributors and users of this project