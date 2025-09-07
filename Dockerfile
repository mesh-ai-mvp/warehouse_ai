# Multi-stage build for optimized Python FastAPI application using uv
# Stage 1: Build stage with uv package manager
FROM python:3.12-slim as builder

# Set build arguments for optimization
ARG DEBIAN_FRONTEND=noninteractive
ARG UV_NO_CACHE=1

# Install uv - the fast Python package installer
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install build dependencies in a single layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

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

# Stage 2: Production stage
FROM python:3.12-slim as production

# Set labels for metadata
LABEL maintainer="Warehouse Management Team"
LABEL version="1.0.0"
LABEL description="Optimized FastAPI Warehouse Management System with uv"

# Set environment variables for production
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8000 \
    HOST=0.0.0.0 \
    WORKERS=1

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser data/ ./data/

# Create necessary directories and set permissions
RUN mkdir -p /app/logs /app/tmp \
    && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Health check for container orchestration
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:${PORT}/api/health', timeout=5)" || exit 1

# Expose port
EXPOSE ${PORT}

# Use exec form for better signal handling
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]