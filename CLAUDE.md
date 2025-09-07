# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a FastAPI-based Pharmacy Warehouse Management System designed as a Proof-of-Concept (POC) for testing warehouse optimization algorithms. The system simulates an intentionally disorganized warehouse with realistic pharmaceutical inventory data.

## Key Development Commands

### Local Development (uv package manager)

```bash
# Install dependencies
uv sync

# Run locally with auto-reload
uv run python src/main.py

# Run linting
uv run ruff check src/

# Fix linting issues
uv run ruff check --fix src/

# Update dependencies
uv lock
```

### Docker Development (Recommended)

```bash
# Development with live reload
make dev
# or: docker-compose -f docker-compose.dev.yml up --build

# Production build
make prod
# or: docker-compose -f docker-compose.prod.yml up --build -d

# View logs
make logs
# or: docker-compose logs -f warehouse-app

# Get shell access
make shell
# or: docker exec -it warehouse-management bash

# Run tests (in Docker)
make test
# or: docker-compose -f docker-compose.dev.yml exec warehouse-app-dev uv run pytest

# Run linting (in Docker)
make lint
# or: docker-compose -f docker-compose.dev.yml exec warehouse-app-dev uv run ruff check src/
```

### Health Checks

```bash
# Test application health
curl http://localhost:8000/api/filters
```

## Architecture Overview

### Backend Architecture

- **FastAPI Application** (`src/main.py`): Main application entry point with lifespan management and static file serving
- **API Routes** (`src/api/routes.py`): RESTful endpoints for inventory data with pagination and filtering
- **Data Layer** (`src/data_loader.py`): CSV data loading and in-memory caching with NaN value cleaning
- **Data Generation** (`src/utils/synthetic_data_generator.py`): Comprehensive synthetic pharmaceutical data generator (1772 lines)

### Frontend

- **Static Web App**: HTML/CSS/JavaScript files in `src/static/`
- **Features**: Dark mode, responsive tables, inventory management UI
- **API Integration**: Consumes FastAPI endpoints for data visualization

### Data Architecture

The system uses CSV files for data storage with an intentionally messy warehouse simulation:

**Core Data Entities:**

- `medications.csv`: 50 pharmaceutical products with categories (Chronic, Intermittent, Sporadic)
- `suppliers.csv`: Pharmaceutical suppliers with lead times and status
- `consumption_history.csv`: 365 days of realistic demand patterns across 3 stores
- `sku_meta.csv`: Physical warehouse metadata (volume, weight, storage requirements)
- `storage_loc_simple.csv`: Fragmented storage locations with inconsistent capacities
- `slot_assignments.csv`: Intentionally disorganized SKU-to-location mappings

**Enhanced Data (Optional):**

- `current_inventory.csv`: Real-time stock levels with reorder points
- `batch_info.csv`: Lot tracking and expiration data
- `warehouse_zones.csv`: Zone definitions with capacity utilization
- `purchase_orders.csv`: PO history and status tracking

### Messy Warehouse Simulation

The data generator creates realistic warehouse chaos:

- 30% SKU fragmentation (same item in multiple locations)
- 10% zone violations (items in wrong storage zones)
- 70% clustering (most items in 30% of locations)
- 5% orphaned items (no assigned location)
- Inconsistent storage capacities and inverted distance scores

## Development Patterns

### Data Loading

- All CSV data loaded into memory at startup via `DataLoader` class
- Graceful fallback for missing enhanced data files
- NaN values cleaned for JSON serialization
- Pagination and filtering implemented in-memory

### API Design

- RESTful endpoints with `/api` prefix
- Query parameter validation using FastAPI Query types
- Comprehensive error handling with HTTPException
- JSON responses with cleaned NaN values

### Docker Optimization

- Multi-stage builds with uv package manager (10x faster than pip)
- Non-root execution with security hardening
- Health checks for container orchestration
- Separate dev/prod configurations with live reload support

## File Structure

```bash
src/
├── main.py              # FastAPI application entry point
├── data_loader.py       # CSV data loading and caching
├── api/
│   ├── __init__.py
│   └── routes.py        # API endpoints
├── utils/
│   └── synthetic_data_generator.py  # Large data generation script
├── static/              # Frontend assets (HTML/CSS/JS)
└── templates/           # HTML templates

data/                    # Generated CSV files
docker-compose*.yml      # Docker configurations  
Makefile                # Development shortcuts
pyproject.toml          # uv dependencies
```

## Testing and Quality

### Code Quality

- **Ruff** for linting with automatic fixes
- **uv** for fast dependency management
- Health checks via `/api/filters` endpoint

### Expected Data Validation Issues

The intentionally messy warehouse will trigger validation warnings:

- "Extreme slot over-concentration"
- "SKU fragmentation detected"
- "Zone violations" for storage placement
- 25-35% fragmentation rate expected

## Environment Configuration

### Docker Environment Variables

- `PORT`: Application port (default: 8000)
- `HOST`: Bind address (default: 0.0.0.0)
- `WORKERS`: Uvicorn workers (default: 1)
- `PYTHONOPTIMIZE`: Python optimization level

### Production Considerations

- Resource limits: 1GB memory, 1.0 CPU cores
- Read-only filesystem with tmpfs for temporary files
- JSON logging with rotation (10MB, 3 files)
- Nginx reverse proxy support with caching

## Data Generation

To regenerate synthetic data:

```bash
# Generate fresh dataset (run from project root)
uv run python src/utils/synthetic_data_generator.py --skus 50 --stores 3 --days 365

# This creates poc_supplychain.db and exports all CSV files to data/
```

## Working with Purchase Orders

The system includes purchase order functionality via the `feat/po-creation` branch:

- PO data linked to medications and suppliers
- Status tracking (pending, approved, completed)
- Integration with inventory levels and reorder points
