---
name: docker
description: Docker and Docker Compose skills and shortcuts
paths:
  - /
---

# Docker Skills

Quick reference for common Docker and Docker Compose operations.

## This Project's Stack

Services defined in `docker-compose.yml`: `postgres`, `airflow-init`, `airflow-webserver`, `airflow-scheduler`, `fastapi`, `pgadmin`, `dbt`.

First bring-up:
```bash
docker compose up -d          # start stack
docker compose ps             # verify health
docker compose logs -f <svc>  # debug any unhealthy service
```

Then open in browser: Airflow (`:8081` — remapped from :8080 due to Windows port conflict), FastAPI docs (`:8000/docs`), pgAdmin (`:5050`).

Airflow runs as uid 50000 inside the container but bind-mounts host dirs (`./airflow/logs`, `./airflow/dags`, `./airflow/plugins`). If you see `PermissionError: [Errno 13]` on those paths, fix ownership:
```bash
sudo chown -R 50000:0 airflow/logs airflow/dags airflow/plugins
```

For the full list of day-one failure modes and their signatures, see `rules/docker_compose_rules.md`.

## Docker Commands

### Container Management
```
# List running containers
docker ps

# List all containers (including stopped)
docker ps -a

# Start container
docker start <container_name_or_id>

# Stop container
docker stop <container_name_or_id>

# Restart container
docker restart <container_name_or_id>

# Remove container
docker rm <container_name_or_id>

# Remove stopped containers
docker container prune

# View container logs
docker logs <container_name_or_id>

# Follow logs in real-time
docker logs -f <container_name_or_id>

# View container stats (CPU, memory, etc.)
docker stats <container_name_or_id>

# Execute command in running container
docker exec -it <container_name_or_id> /bin/bash

# Copy files to/from container
docker cp <local_file> <container_name>:<path>
docker cp <container_name>:<path> <local_file>
```

### Image Management
```
# List images
docker images

# Build image
docker build -t <image_name>:<tag> .

# Build with no cache
docker build --no-cache -t <image_name>:<tag> .

# Remove image
docker rmi <image_name>:<tag>

# Remove dangling images
docker image prune

# Pull image from registry
docker pull <image_name>:<tag>

# Push image to registry
docker push <image_name>:<tag>

# Tag image
docker tag <source_image>:<tag> <target_image>:<tag>

# Show image history
docker history <image_name>:<tag>

# Inspect image/container
docker inspect <image_name_or_container>
```

### Network Management
```
# List networks
docker network list

# Inspect network
docker network inspect <network_name>

# Create network
docker network create <network_name>

# Connect container to network
docker network connect <network_name> <container_name>

# Disconnect container from network
docker network disconnect <network_name> <container_name>

# Remove network
docker network rm <network_name>

# Remove unused networks
docker network prune
```

### Volume Management
```
# List volumes
docker volume list

# Inspect volume
docker volume inspect <volume_name>

# Create volume
docker volume create <volume_name>

# Remove volume
docker volume rm <volume_name>

# Remove unused volumes
docker volume prune

# Backup volume
docker run --rm \
  -v <volume_name>:/volume \
  -v $(pwd):/backup \
  ubuntu tar cvf /backup/backup.tar /volume

# Restore volume
docker run --rm \
  -v <volume_name>:/volume \
  -v $(pwd):/backup \
  ubuntu tar xvf /backup/backup.tar -C /volume
```

## Docker Compose Commands

### Service Management
```
# List services
docker compose ps

# Start services
docker compose up -d

# Start specific services
docker compose up -d <service_name> <service_name2>

# Start services with build
docker compose up --build -d

# Stop services
docker compose down

# Stop services without removing volumes
docker compose down -v

# Restart services
docker compose restart <service_name>

# View service logs
docker compose logs <service_name>

# Follow service logs
docker compose logs -f <service_name>

# Show service configuration
docker compose config

# Validate compose file
docker compose config --validate

# Execute command in service container
docker compose exec <service_name> /bin/bash

# Run one-off command
docker compose run --rm <service_name> <command>

# Scale service
docker compose up --scale <service_name>=<replicas> -d

# Pause/unpause services
docker compose pause <service_name>
docker compose unpause <service_name>
```

### Build and Images
```
# Build images
docker compose build

# Build specific service
docker compose build <service_name>

# Build with no cache
docker compose build --no-cache

# Pull images
docker compose pull

# Push images
docker compose push

# Remove images
docker compose down --rmi all

# Remove images and volumes
docker compose down --rmi all -v
```

### Logs and Monitoring
```
# View logs for all services
docker compose logs

# View logs with timestamps
docker compose logs -t

# Tail logs for specific service
docker compose logs -f <service_name>

# Show service resource usage
docker compose top

# Check service ports
docker compose port <service_name> <port>
```

## Development Workflow

### Local Development
```
# Start stack for development
docker compose up -d

# Rebuild after code changes
docker compose up --build -d <service_name>

# View logs for debugging
docker compose logs -f <service_name>

# Execute commands in service
docker compose exec <service_name> <command>

# Run tests in service
docker compose exec <service_name> pytest

# Enter service shell for debugging
docker compose exec <service_name> /bin/bash
```

### Environment Variables
```
# Set environment variables in .env file
POSTGRES_USER=finance_user
POSTGRES_PASSWORD=secure_password
POSTGRES_DB=finance_demo
AIRFLOW__CORE__FERNET_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
AIRFLOW__CORE__EXECUTOR=LocalExecutor

# Use in docker-compose.yml
services:
  postgres:
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
```

### Volume Mounts for Development
```
# In docker-compose.yml for live code reloading
services:
  fastapi:
    build:
      context: ./api
      target: development
    volumes:
      - ./api:/app:cached  # Mount code for live reload
      - ./logs:/app/logs   # Mount logs
    ports:
      - "8000:8000"
    environment:
      - DEBUG=true
```

### Multi-stage Dockerfiles
```dockerfile
# API/Dockerfile
FROM python:3.9-slim as builder

# Install build dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Production image
FROM python:3.9-slim

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code
WORKDIR /app
COPY . .

# Create non-root user
RUN useradd --create-home appuser
USER appuser

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Troubleshooting

### Container Issues
```
# Container exits immediately
docker ps -a  # Check STATUS column
docker logs <container_name>  # See exit reason

# Can't connect to container
docker port <container_name>  # Check port mapping
docker inspect <container_name> | grep -A 10 "NetworkSettings"  # Check networks

# High resource usage
docker stats  # Monitor real-time usage
docker top <container_name>  # See running processes

# Permission denied
docker run --user=$(id -u):$(id -g) ...  # Run as current user
# Or adjust volume permissions
sudo chown -R $(id -u):$(id -g) ./volume_directory
```

### Network Issues
```
# Containers can't communicate
docker network inspect <network_name>  # Check connected containers
docker exec <container1> ping <container2>  # Test connectivity

# Port already in use
ss -tulnp | grep <port_number>  # Find process using port
# Change port in docker-compose.yml or stop conflicting service

# DNS resolution issues
docker exec <container> cat /etc/resolv.conf  # Check DNS settings
# Add custom DNS to docker-compose.yml
dns:
  - 8.8.8.8
  - 8.8.4.4
```

### Volume Issues
```
# Permission denied in volume
docker run -v $(pwd)/data:/app/data -u root ...  # Run as root to investigate
# Check ownership: ls -la data/
# Fix: chown -R $(id -u):$(id -g) data/

# Volume not persisting data
docker volume ls  # Verify volume exists
docker inspect <volume_name>  # Check mountpoint
# Ensure you're not using bind mount when you need volume (or vice versa)

# Slow volume performance
# Use named volumes instead of bind mounts for databases
# Or use tmpfs for temporary storage
tmpfs:
  - /tmp
```

### Build Issues
```
# Build fails due to missing dependencies
docker build --no-cache .  # See full output
# Check requirements.txt or equivalent
# Ensure network connectivity for package downloads

# Image too large
docker history <image_name>  # See layer sizes
# Use multi-stage builds to exclude build tools
# Use .dockerignore to exclude unnecessary files
# Consider using slim or alpine base images

# Cache not working
# Dockerfile order matters - put frequently changing lines at the end
# COPY requirements.txt before COPY . .
# Avoid adding unnecessary files to context
```

### Compose Issues
```
# Service fails to start
docker compose ps  # Check service state
docker compose logs <service_name>  # See error logs
docker compose config  # Validate configuration

# Port conflicts between services
docker compose port <service_name> <port_number>  # Check actual port
# Change host port in docker-compose.yml
ports:
  - "8080:80"  # Host:Container

# Environment variables not expanding
# Use $$ for literal $ in docker-compose.yml
# Use ${VARIABLE:-default} for default values
# Validate with: docker compose config

# Circular dependencies
# Services should not depend on each other in a loop
# Use healthchecks and depends_on with condition
depends_on:
  postgres:
    condition: service_healthy
```

## Best Practices

### Image Creation
1. Use official base images when possible
2. Keep images small (use slim, alpine, or distroless variants)
3. Leverage browser caching by ordering Dockerfile steps
4. Use .dockerignore to exclude unnecessary files
5. Run as non-root user for security
6. Tag images clearly (version, environment, etc.)
7. Multi-stage builds to separate build and runtime environments
8. Healthchecks for containerized applications
9. Explicitly expose only necessary ports

### Docker Compose
1. Use version 3.8+ syntax for latest features
2. Separate concerns with multiple compose files (dev.yml, prod.yml)
3. Use environment variables for configuration (don't hardcode)
4. Use named volumes for persistent data
5. Set restart policies appropriately (unless-stopped for services)
6. Use depends_on for startup ordering (not for runtime dependencies)
7. Healthchecks for critical service dependencies
8. Resource limits (cpus, memory) to prevent container starvation
9. Logging drivers for centralized logging
10. Secrets management for sensitive data

### Development Workflow
1. Use bind mounts for code during development (not production)
2. Separate development and production configurations
3. Automate builds and testing with CI/CD
4. Use docker compose watch for auto-rebuild (Docker 20.10+)
5. Pre-compose scripts for setup/checks
6. Health checks in orchestration scripts
7. Clean up unused resources regularly (prune commands)
8. Document compose file purpose and usage
9. Version control compose files and Dockerfiles
10. Use docker compose profiles for environment-specific services

### Security
1. Scan images for vulnerabilities (trivy, clair, etc.)
2. Run containers with least privilege
3. Drop unnecessary Linux capabilities
4. Use read-only root filesystem when possible
5. Limit container syscalls with seccomp profiles
6. Use user namespaces for isolation
7. Encrypt volumes for sensitive data at rest
8. Use content trust for image signing (Docker Content Trust)
9. Implement admission control in production (OPA, Kyverno)
10. Regularly update base images and dependencies

### Performance Optimization
1. Optimize application startup time
2. Use appropriate storage drivers (overlay2 recommended)
3. Tune container resource limits based on profiling
4. Use tmpfs for temporary storage when appropriate
5. Enable experimental features if beneficial (buildkit)
6. Multi-arch images for different CPU architectures
7. Use containerd or cri-o for production runtimes
8. Image compression for faster pulls
9. Registry mirrors for internal networks
10. Layer caching strategies in CI/CD

## Common Dockerfile Patterns

### Python Application
```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.9-slim as builder

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Runtime stage
FROM python:3.9-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Create app user
RUN useradd --create-home appuser
WORKDIR /app
USER appuser

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Node.js Application
```dockerfile
FROM node:18-alpine as builder

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production stage
FROM node:18-alpine

WORKDIR /app
COPY --from=builder /app/package*.json ./
RUN npm ci --only=production
COPY --from=builder /app/dist ./dist

USER node
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s \
  CMD wget -qO- http://localhost:3000/health || exit 1

CMD ["node", "dist/index.js"]
```

### PostgreSQL with Custom Config
```dockerfile
FROM postgres:15

# Copy custom configuration
COPY postgresql.conf /etc/postgresql/postgresql.conf
COPY pg_hba.conf /etc/postgresql/pg_hba.txt

# Set environment variables
POSTGRES_USER=${POSTGRES_USER}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_DB=${POSTGRES_DB}
POSTGRES_INITDB_ARGS="--auth-host=scram-sha-256"

# Expose standard port
EXPOSE 5432

# Healthcheck (uses default postgres healthcheck)
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s \
  CMD pg_isready -U $POSTGRES_USER

# Default command (inherited from postgres image)
```

## Docker Compose Best Practices

### File Organization
```
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  fastapi:
    build:
      context: ./api
      target: development
    volumes:
      - ./api:/app:cached
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    env_file:
      - .env

volumes:
  postgres_data:
  redis_data:
```

### Environment Management
```
# .env.example (template)
POSTGRES_USER=finance_user
POSTGRES_PASSWORD=changeme123
POSTGRES_DB=finance_demo
AIRFLOW_FERNET_KEY=
AIRFLOW_EXECUTOR=LocalExecutor
REDIS_PASSWORD=

# .env (actual values - NOT in version control)
POSTGRES_USER=finance_prod
POSTGRES_PASSWORD=secure_random_password_here
POSTGRES_DB=finance_prod
AIRFLOW_FERNET_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
AIRFLOW_EXECUTOR=LocalExecutor
REDIS_PASSWORD=another_secure_password

# docker-compose.override.yml (for local development)
services:
  fastapi:
    command: uvicorn main:app --reload --host 0.0.0.0 --port 8000
    environment:
      - DEBUG=true
  postgres:
    ports:
      - "5433:5432"  # Avoid conflict with local postgres
```

### Service Dependencies
```
# Proper dependency ordering with healthchecks
services:
  db:
    # ... postgres config
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  api:
    build: ./api
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/db
    depends_on:
      db:
        condition: service_healthy  # Wait for healthy DB
    # App logic should still handle retry logic
```

## Maintenance Commands

### System Pruning
```
# Remove all unused containers, networks, images, build cache
docker system prune

# Include volumes in prune (use with caution!)
docker system prune --volumes

# Aggressive prune (removes all unused images, not just dangling)
docker system prune -a

# Prune with specific filters
docker system prune --filter "until=24h"  # Remove resources older than 24h
```

### Disk Usage
```
# Show Docker disk usage
docker system df

# Detailed breakdown by type
docker system df -v

# Image disk usage
docker images --format "{{.Repository}}:{{.Tag}}\t{{.Size}}"

# Container disk usage (approximate)
docker ps -s --format "{{.Names}}\t{{.Size}}"
```

### Backup and Restore
```
# Backup all volumes
#!/bin/bash
BACKUP_DIR=/backups/docker_$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

for volume in $(docker volume ls -q); do
    echo "Backing up volume: $volume"
    docker run --rm \
        -v $volume:/volume \
        -v $BACKUP_DIR:/backup \
        alpine tar czf /backup/$volume.tar.gz /volume
done

# Backup compose applications
# For each service with persistent data:
docker compose exec <service> <backup_command>
# Or backup volume directly as shown above

# Restore volumes
# Stop services using the volume
docker compose down
# Restore backup as shown in volume management section
# Restart services
docker compose up -d
```