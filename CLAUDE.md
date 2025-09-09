# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## AI Guidance

* Ignore GEMINI.md and GEMINI-*.md files
* To save main context space, for code searches, inspections, troubleshooting or analysis, use code-searcher subagent where appropriate - giving the subagent full context background for the task(s) you assign it.
* After receiving tool results, carefully reflect on their quality and determine optimal next steps before proceeding. Use your thinking to plan and iterate based on this new information, and then take the best next action.
* For maximum efficiency, whenever you need to perform multiple independent operations, invoke all relevant tools simultaneously rather than sequentially.
* Before you finish, please verify your solution
* Do what has been asked; nothing more, nothing less.
* NEVER create files unless they're absolutely necessary for achieving your goal.
* ALWAYS prefer editing an existing file to creating a new one.
* NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
* When you update or modify core context files, also update markdown documentation and memory bank
* When asked to commit changes, exclude CLAUDE.md and CLAUDE-*.md referenced memory bank system files from any commits. Never delete these files.

## Memory Bank System

This project uses a structured memory bank system with specialized context files. Always check these files for relevant information before starting work:

### Core Context Files

* **CLAUDE-activeContext.md** - Current session state, goals, and progress (if exists)
* **CLAUDE-patterns.md** - Established code patterns and conventions (if exists)
* **CLAUDE-decisions.md** - Architecture decisions and rationale (if exists)
* **CLAUDE-troubleshooting.md** - Common issues and proven solutions (if exists)
* **CLAUDE-config-variables.md** - Configuration variables reference (if exists)
* **CLAUDE-temp.md** - Temporary scratch pad (only read when referenced)

**Important:** Always reference the active context file first to understand what's currently being worked on and maintain session continuity.

### Memory Bank System Backups

When asked to backup Memory Bank System files, you will copy the core context files above and @.claude settings directory to directory @/path/to/backup-directory. If files already exist in the backup directory, you will overwrite them.

## Project Overview

This is a **FastAPI-based pharmaceutical warehouse management system** with a multi-agent AI system for automated purchase order generation. The architecture consists of:

### Core Architecture

1. **FastAPI Application** (`src/main.py`)
   * Serves static files and API endpoints
   * Lifespan management for data loading
   * Routes for inventory, medication details, and purchase orders

2. **Multi-Agent AI System** (`src/ai_agents/`)
   * **LangGraph workflow orchestration** using state machines
   * **Three specialized agents**: ForecastAgent, AdjustmentAgent, SupplierAgent
   * **Asynchronous processing** with timeout handling and caching
   * **Integration** via AIPoHandler in api_handler.py

3. **Data Layer** (`src/data_loader.py`)
   * Centralized CSV data loading and caching
   * Inventory management with filtering and pagination
   * Consumption history and forecasting data

4. **Frontend** (Static files in `src/static/`, templates in `src/templates/`)
   * Responsive web interface with dark mode
   * Purchase order creation and management pages
   * Interactive charts using Plotly.js

### AI Agents System

The AI system uses **LangGraph** for state machine-based workflow orchestration:
* **State Management**: POGenerationState with progress tracking and reasoning
* **Sequential Flow**: forecast → adjust → optimize → finalize
* **Error Handling**: Timeout management and graceful failure handling
* **Caching**: Configurable result caching with TTL

## Development Commands

### Quick Start

```bash
# Development with live reload (recommended)
make dev

# Local development without Docker  
uv sync
uv run python src/main.py

# Generate synthetic data (if needed)
uv run python src/utils/synthetic_data_generator.py --skus 50 --stores 3 --days 365
```

### Essential Commands

```bash
# Development
make dev              # Start dev environment with live reload
make dev-bg          # Start dev environment in background
uv run python src/main.py  # Run locally on port 8000

# Code Quality
make lint            # Run ruff linting in container
make lint-fix        # Auto-fix linting issues  
uv run ruff check src/  # Run ruff locally
uv run ruff check --fix src/  # Auto-fix locally

# Testing
make test            # Run pytest in container
uv run pytest       # Run tests locally

# Production
make prod            # Production deployment
make prod-nginx      # With Nginx reverse proxy

# Data Management
uv run python src/utils/synthetic_data_generator.py  # Generate test data
```

### Docker Commands

```bash
make logs            # View application logs
make shell           # Get container shell access
make clean           # Clean up containers and images
make health          # Test API health endpoint
```

### Key Endpoints

* `http://localhost:8000` - Main dashboard
* `http://localhost:8000/docs` - FastAPI documentation
* `http://localhost:8000/api/inventory` - Inventory API
* `http://localhost:8000/create-po` - AI-powered PO creation

### Dependencies

- **Python 3.12+** with uv package manager
* **LangGraph** for AI workflow orchestration  
* **FastAPI** for REST API
* **Docker** for containerization (recommended)

### Testing Strategy

Run tests with `make test` or `uv run pytest`. Verify linting with `make lint` before committing changes.
