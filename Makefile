# Makefile for Warehouse Management Docker operations

.PHONY: help dev prod build clean logs shell test lint frontend

# Default target
help:
	@echo "Available commands:"
	@echo "  dev      - Start development environment with live reload"
	@echo "  prod     - Start production environment"
	@echo "  build    - Build Docker images"
	@echo "  clean    - Clean up containers and images"
	@echo "  logs     - Show application logs"
	@echo "  shell    - Get shell access to running container"
	@echo "  test     - Run tests in container"
	@echo "  lint     - Run linting with ruff"
	@echo "  deps     - Update dependencies with uv"
	@echo ""
	@echo "Frontend commands:"
	@echo "  frontend-dev    - Start frontend development server"
	@echo "  frontend-build  - Build frontend for production"
	@echo "  frontend-test   - Run frontend tests"

# Development with live reload
dev:
	docker-compose -f docker-compose.dev.yml up --build

dev-bg:
	docker-compose -f docker-compose.dev.yml up --build -d

# Production deployment
prod:
	docker-compose -f docker-compose.prod.yml up --build -d

prod-nginx:
	docker-compose -f docker-compose.prod.yml --profile with-nginx up -d

# Build images
build:
	docker-compose build

build-prod:
	docker-compose -f docker-compose.prod.yml build

# Clean up
clean:
	docker-compose -f docker-compose.dev.yml down -v
	docker-compose down -v
	docker-compose -f docker-compose.prod.yml down -v
	docker system prune -f

clean-all:
	docker-compose -f docker-compose.dev.yml down -v
	docker-compose down -v
	docker-compose -f docker-compose.prod.yml down -v
	docker system prune -af

# Logs
logs:
	docker-compose logs -f warehouse-app

logs-dev:
	docker-compose -f docker-compose.dev.yml logs -f warehouse-app-dev

logs-prod:
	docker-compose -f docker-compose.prod.yml logs -f warehouse-app

# Shell access
shell:
	docker exec -it warehouse-management bash

shell-dev:
	docker exec -it warehouse-management-dev bash

shell-prod:
	docker exec -it warehouse-management-prod bash

# Testing and linting
test:
	docker-compose -f docker-compose.dev.yml exec warehouse-app-dev uv run pytest

lint:
	docker-compose -f docker-compose.dev.yml exec warehouse-app-dev uv run ruff check src/

lint-fix:
	docker-compose -f docker-compose.dev.yml exec warehouse-app-dev uv run ruff check --fix src/

# Dependency management
deps:
	uv lock

deps-update:
	uv sync

# Health check
health:
	curl -f http://localhost:8000/api/filters || exit 1

# Quick restart
restart:
	docker-compose restart

restart-dev:
	docker-compose -f docker-compose.dev.yml restart

restart-prod:
	docker-compose -f docker-compose.prod.yml restart

# Frontend commands
frontend-dev:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm run build

frontend-test:
	cd frontend && npm run test

frontend-lint:
	cd frontend && npm run lint

frontend-install:
	cd frontend && npm install