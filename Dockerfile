# Multi-stage build for optimized Python FastAPI application with React frontend
# Stage 1: Build React frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy frontend package files
COPY frontend/package*.json ./
RUN npm ci --no-cache && npm cache clean --force

# Copy frontend source code
COPY frontend/ ./

# Build the React frontend
RUN npm run build

# Stage 2: Build Python backend with uv package manager  
FROM python:3.12-alpine AS backend-builder

# Set build arguments for optimization
ARG UV_NO_CACHE=1

# Install uv and build dependencies in single layer
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install build dependencies for Alpine
RUN apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    cargo \
    rust \
    && rm -rf /var/cache/apk/*

# Set working directory
WORKDIR /app

# Copy uv configuration files first for better layer caching
COPY pyproject.toml uv.lock ./

# Create virtual environment and install dependencies with uv
RUN uv venv /opt/venv --python 3.12
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies using uv (much faster than pip)
RUN uv pip install --no-cache -r pyproject.toml

# Remove build dependencies to reduce image size
RUN apk del .build-deps

# Stage 3: Optimized production stage
FROM python:3.12-alpine AS production

# Install only runtime dependencies for Alpine
RUN apk add --no-cache \
    libffi \
    openssl \
    ca-certificates \
    && rm -rf /var/cache/apk/*

# Set labels for metadata
LABEL maintainer="Warehouse Management Team"
LABEL version="2.0.0"
LABEL description="Optimized FastAPI Warehouse Management System with React Frontend"

# Set environment variables for production
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app/src:/app" \
    PORT=8000 \
    HOST=0.0.0.0 \
    WORKERS=1

# Create non-root user for security
RUN addgroup -g 1000 appuser && \
    adduser -D -u 1000 -G appuser appuser

# Copy virtual environment from backend builder stage
COPY --from=backend-builder /opt/venv /opt/venv

# Set working directory
WORKDIR /app

# Copy built frontend from frontend builder stage
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist/

# Copy application code
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser data/ ./data/

# Create necessary directories and set permissions
RUN mkdir -p /app/logs /app/tmp \
    && chown -R appuser:appuser /app

# Initialize database with synthetic data (run as root, then switch)
USER root
RUN python src/utils/synthetic_data_generator.py --db /app/poc_supplychain.db --out /app/data --skus 50 --stores 3 --days 365 \
    && chown appuser:appuser /app/poc_supplychain.db \
    && chown -R appuser:appuser /app/data

# Switch to non-root user for runtime
USER appuser

# Health check for container orchestration
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:${PORT}/api/filters', timeout=5)" || exit 1

# Expose port
EXPOSE ${PORT}

# Use exec form for better signal handling  
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]