# Pharmacy Warehouse Management System

A comprehensive **FastAPI-based** warehouse management system designed for pharmaceutical supply chain optimization. This Proof-of-Concept (POC) simulates a realistic, intentionally disorganized warehouse environment to test and demonstrate optimization algorithms.

## Project Purpose

This system provides a testing ground for warehouse optimization algorithms by simulating real-world pharmaceutical inventory management challenges:

- **Realistic Data Simulation**: 50 medications across 3 pharmacy stores with 365 days of consumption history
- **Intentional Warehouse Chaos**: Fragmented storage, zone violations, and suboptimal item placement
- **Comprehensive Analytics**: Demand forecasting, inventory tracking, and supply chain metrics
- **Algorithm Testing Platform**: Baseline disorganized warehouse for optimization algorithm validation

## Key Features

### Data Management

- **50 Pharmaceutical Products** with realistic demand patterns (Chronic, Intermittent, Sporadic)
- **3 Pharmacy Stores** with individualized consumption patterns
- **365 Days** of historical consumption data with seasonality and stockout tracking
- **Supplier Management** with lead times, delivery tracking, and status monitoring
- **Price History** with temporal changes and market volatility simulation

### Warehouse Simulation

- **Intentionally Messy Storage**: 30% SKU fragmentation, 10% zone violations
- **Realistic Physical Constraints**: Volume, weight, temperature, and security requirements
- **Storage Location Management** with inconsistent capacities and distance scoring
- **Zone Management** (Ambient, Cold Chain, Controlled Substances)

### Analytics & Optimization

- **Pre-computed Forecasts** using Holt-Winters exponential smoothing
- **Monte Carlo Sampling** for demand uncertainty quantification
- **Inventory Optimization** with reorder points and safety stock calculations
- **Performance Metrics** for warehouse efficiency analysis

### Web Interface

- **Modern Dashboard** with dark mode support
- **Real-time Inventory Tracking** with pagination and filtering
- **Medication Detail Views** with comprehensive analytics
- **Responsive Design** for desktop and mobile access

## Quick Start

### Prerequisites

- **Python 3.12+**
- **Docker & Docker Compose** (recommended)
- **uv package manager** (for ultra-fast builds)

### Option 1: Docker Development (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd hackathon-warehouse-management

# Start development environment with live reload
make dev
# or: docker-compose -f docker-compose.dev.yml up --build

# Access the application
# Dashboard: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Option 2: Local Development

```bash
# Install dependencies with uv
uv sync

# Generate synthetic data (if not present)
uv run python src/utils/synthetic_data_generator.py --skus 50 --stores 3 --days 365

# Run the application
uv run python src/main.py

# Access at http://localhost:8000
```

## Project Structure

```bash
hackathon-warehouse-management/
├── src/
│   ├── main.py                     # FastAPI application entry point
│   ├── data_loader.py              # CSV data loading and caching
│   ├── api/
│   │   └── routes.py               # RESTful API endpoints
│   ├── utils/
│   │   └── synthetic_data_generator.py  # Comprehensive data generator (1772 lines)
│   ├── static/                     # Frontend assets (HTML/CSS/JS)
│   └── templates/                  # HTML templates
├── data/                           # Generated CSV datasets
├── docker-compose*.yml             # Docker configurations
├── Dockerfile*                     # Optimized Docker builds
├── Makefile                        # Development shortcuts
├── pyproject.toml                  # uv dependency management
└── database_documentation.md       # Detailed data schema docs
```

## Development Commands

### Docker Workflow (Recommended)

```bash
# Development with live reload
make dev

# Production deployment
make prod

# With Nginx reverse proxy
make prod-nginx

# View application logs
make logs

# Get shell access
make shell

# Run tests
make test

# Run linting
make lint

# Clean up containers
make clean
```

### Local Development

```bash
# Install/update dependencies
uv sync
uv lock

# Run application
uv run python src/main.py

# Code quality
uv run ruff check src/
uv run ruff check --fix src/

# Generate fresh data
uv run python src/utils/synthetic_data_generator.py
```

## Data Architecture

### Core Data Entities

| File | Description | Records |
|------|-------------|---------|
| `medications.csv` | Pharmaceutical product catalog | 50 items |
| `suppliers.csv` | Supplier information & lead times | 10 suppliers |
| `consumption_history.csv` | Daily dispensing records | ~54,750 records |
| `sku_meta.csv` | Physical warehouse metadata | 50 SKUs |
| `storage_loc_simple.csv` | Warehouse storage locations | 24 locations |
| `slot_assignments.csv` | SKU-to-location mappings | Variable |
| `drug_prices.csv` | Historical pricing data | Time-series |
| `forecasts.csv` | Pre-computed demand forecasts | 28-day horizon |

### Intentional Warehouse Chaos

The system simulates realistic warehouse disorganization:

- **30% SKU Fragmentation**: Same medication split across multiple locations
- **10% Zone Violations**: Items stored in inappropriate zones
- **70% Clustering**: Most items concentrated in 30% of locations
- **5% Orphaned Items**: Medications without storage assignments
- **Inconsistent Capacities**: 15% tiny locations, 25% oversized locations
- **Inverted Distance Scores**: 20% of locations have illogical distance metrics

## API Endpoints

### Core Inventory API

```bash
GET /api/inventory          # Paginated inventory with filters
GET /api/medication/{id}    # Detailed medication information
GET /api/filters           # Available filter options (categories, suppliers, etc.)
```

### Query Parameters

- `page`, `page_size`: Pagination controls
- `search`: Text search across medication names
- `category`: Filter by medication category
- `supplier`: Filter by supplier
- `stock_level`: Filter by stock status (Low, Medium, High, Out of Stock)

### Example Response

```json
{
  "items": [
    {
      "med_id": 1,
      "name": "Metformin 500mg",
      "category": "Chronic",
      "current_stock": 1250,
      "stock_category": "High",
      "supplier_name": "MedCo Pharma",
      "reorder_point": 300,
      "days_until_stockout": 45
    }
  ],
  "total_items": 50,
  "total_pages": 3,
  "current_page": 1
}
```

## Frontend Features

### Dashboard Features

- **Responsive Design**: Works on desktop, tablet, and mobile
- **Dark Mode**: Toggle between light and dark themes
- **Advanced Filtering**: Multi-criteria search and filtering
- **Pagination**: Efficient handling of large datasets
- **Real-time Updates**: Live inventory status and metrics

### User Interface Components

- **Inventory Table**: Sortable columns with stock level indicators
- **Medication Details**: Comprehensive view with consumption history
- **Supplier Dashboard**: Lead times and delivery performance
- **Zone Management**: Storage location optimization view

## Docker Optimization

### Performance Benefits

- **uv Package Manager**: 10-100x faster than pip for dependency resolution
- **Multi-Stage Builds**: Optimized image size (~120MB vs ~150MB with pip)
- **Build Speed**: Cold builds in ~1 minute vs ~3 minutes with pip
- **Layer Caching**: Efficient Docker layer optimization with uv.lock

### Security Features

- **Non-root Execution**: Enhanced container security
- **Read-only Filesystem**: Immutable production containers
- **Security Options**: Comprehensive container hardening
- **Health Checks**: Automatic health monitoring and restarts

### Environment Configurations

| Configuration | Purpose | Features |
|--------------|---------|----------|
| `docker-compose.dev.yml` | Development | Live reload, debug mode |
| `docker-compose.yml` | Standard | Basic production-like setup |
| `docker-compose.prod.yml` | Production | Optimized, resource-limited |

## Data Generation & Validation

### Synthetic Data Features

- **Configurable Scale**: Adjust SKUs, stores, time periods
- **Realistic Patterns**: Seasonal demand, supplier variability
- **Validation Metrics**: Built-in data quality checks
- **Export Formats**: SQLite database + CSV files

### Expected Validation Results

| Metric | Expected Range | Purpose |
|--------|---------------|---------|
| SKU Fragmentation Rate | 25-35% | Items split across locations |
| Location Utilization | 70-85% | Warehouse space efficiency |
| Zone Violations | 5-10% | Incorrect storage placements |
| Orphaned Items | 2-3 | Unassigned inventory |

### Data Generation Commands

```bash
# Standard dataset generation
uv run python src/utils/synthetic_data_generator.py --skus 50 --stores 3 --days 365

# Custom configuration
uv run python src/utils/synthetic_data_generator.py --skus 100 --stores 5 --days 730 --suppliers 15

# Output: poc_supplychain.db + CSV files in data/ directory
```

## Testing & Optimization Use Cases

### Algorithm Testing Scenarios

1. **Slotting Optimization**: Test velocity-based placement algorithms
2. **Zone Consolidation**: Evaluate storage zone reorganization strategies
3. **SKU Defragmentation**: Benchmark item consolidation approaches
4. **Capacity Balancing**: Optimize warehouse space utilization

### Performance Benchmarks

- **Picking Distance Reduction**: Measure improvement in average picking routes
- **Storage Efficiency**: Track capacity utilization improvements
- **Stockout Prevention**: Analyze reorder point optimization
- **Lead Time Optimization**: Evaluate supplier performance improvements

## Deployment Options

### Development Deployment

```bash
# Local development with auto-reload
make dev

# Background development
make dev-bg
```

### Production Deployment

```bash
# Standard production
make prod

# With Nginx reverse proxy and load balancing
make prod-nginx

# Resource-optimized production
docker-compose -f docker-compose.prod.yml up -d
```

### Health Monitoring

```bash
# Check application health
curl http://localhost:8000/api/filters

# Monitor container stats
docker stats warehouse-management

# View detailed logs
make logs
```

## Documentation

- **[Database Documentation](database_documentation.md)**: Comprehensive schema and data relationships
- **[Docker Documentation](DOCKER_README.md)**: Detailed Docker setup and optimization guide
- **[API Documentation](http://localhost:8000/docs)**: Interactive FastAPI documentation (when running)

## Contributing

This POC is designed for hackathon and optimization algorithm testing. Key areas for enhancement:

1. **Algorithm Integration**: Add optimization algorithm plugins
2. **Advanced Analytics**: Implement additional forecasting models
3. **Real-time Updates**: Add WebSocket support for live data
4. **Mobile App**: Develop native mobile companion app
5. **ML Integration**: Add machine learning for demand prediction

## License

This project is designed for educational and research purposes as part of warehouse optimization algorithm development and testing.

## Troubleshooting

### Common Issues

#### Port Already in Use

```bash
# Change port in docker-compose.yml
ports:
  - "8001:8000"  # Use different host port
```

#### Permission Issues

```bash
# Fix data directory permissions
chmod 644 data/*.csv
```

#### Health Check Failures

```bash
# Check application logs
docker-compose logs warehouse-app

# Test health endpoint manually
curl http://localhost:8000/api/filters
```

### Performance Optimization

#### Slow Data Loading

- Ensure data/ directory contains all CSV files
- Check for large consumption_history.csv files
- Consider reducing dataset size for development

#### Container Resource Issues

- Monitor with `docker stats`
- Adjust resource limits in docker-compose.prod.yml
- Use development configuration for resource-constrained environments

---

**Ready to optimize your warehouse? Start with `make dev` and explore the intentionally chaotic inventory system!**
