#!/bin/bash

# Warehouse Management System - Deployment Script
# Usage: ./deploy.sh

set -e

echo "========================================="
echo "Warehouse Management System Deployment"
echo "========================================="

# Configuration
IMAGE_NAME="sidhez/warehouse-management"
IMAGE_TAG="${1:-latest}"
CONTAINER_NAME="warehouse-management-prod"
APP_DIR="${HOME}/warehouse-app"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create application directory
echo "Creating application directory..."
mkdir -p "${APP_DIR}"
cd "${APP_DIR}"
print_success "Application directory created: ${APP_DIR}"

# Check if docker-compose.prod.yml exists
if [ ! -f "docker-compose.prod.yml" ]; then
    echo "Creating docker-compose.prod.yml..."
    cat > docker-compose.prod.yml << 'EOF'
version: '3.8'

services:
  warehouse-app:
    image: sidhez/warehouse-management:latest
    container_name: warehouse-management-prod
    ports:
      - "${PORT:-27893}:8000"
    environment:
      - PORT=${PORT:-8000}
      - HOST=0.0.0.0
      - WORKERS=${WORKERS:-2}
      - PYTHONPATH=/app/src:/app
      - APP_ENV=production
      - DEBUG=false
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DATABASE_URL=${DATABASE_URL:-sqlite:///app/poc_supplychain.db}
      - SMTP_USER=${SMTP_USER}
      - SMTP_PASSWORD=${SMTP_PASSWORD}
      - EMAIL_FROM_NAME=${EMAIL_FROM_NAME:-Warehouse Team}
      - EMAIL_BCC=${EMAIL_BCC}
      - SMTP_HOST=${SMTP_HOST}
      - SMTP_PORT=${SMTP_PORT}
      - VITE_ENABLE_MOCK_FALLBACKS=${VITE_ENABLE_MOCK_FALLBACKS:-false}
      - VITE_API_URL=${VITE_API_URL:-/api}
      - VITE_ENABLE_AI_GENERATION=${VITE_ENABLE_AI_GENERATION:-true}
    volumes:
      - warehouse-logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8000/api/filters', timeout=5)"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 120s
    networks:
      - warehouse-network

networks:
  warehouse-network:
    driver: bridge

volumes:
  warehouse-logs:
    driver: local
EOF
    print_success "docker-compose.prod.yml created"
else
    print_warning "docker-compose.prod.yml already exists"
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Creating .env template..."
    cat > .env << 'EOF'
# AI Configuration (REQUIRED)
OPENAI_API_KEY=your_openai_api_key_here

# Database Configuration
DATABASE_URL=sqlite:///app/poc_supplychain.db

# Application Settings
APP_ENV=production
DEBUG=false
PORT=27893
WORKERS=2

# Email Configuration (Optional)
SMTP_USER=
SMTP_PASSWORD=
EMAIL_FROM_NAME=Warehouse Team
EMAIL_BCC=
SMTP_HOST=
SMTP_PORT=

# Frontend Settings
VITE_ENABLE_MOCK_FALLBACKS=false
VITE_API_URL=/api
VITE_ENABLE_AI_GENERATION=true
EOF
    print_warning ".env file created - PLEASE EDIT IT WITH YOUR ACTUAL VALUES"
    echo ""
    echo "Please edit .env file and add your OPENAI_API_KEY"
    echo "Run this script again after updating .env"
    exit 0
else
    print_success ".env file found"
fi

# Check if OPENAI_API_KEY is set
if grep -q "your_openai_api_key_here" .env; then
    print_error "Please update OPENAI_API_KEY in .env file"
    exit 1
fi

# Stop existing container if running
echo "Checking for existing containers..."
if docker ps -a | grep -q ${CONTAINER_NAME}; then
    print_warning "Stopping existing container..."
    docker compose -f docker-compose.prod.yml down
    print_success "Existing container stopped"
fi

# Pull latest image
echo "Pulling latest image..."
docker pull ${IMAGE_NAME}:${IMAGE_TAG}
print_success "Image pulled: ${IMAGE_NAME}:${IMAGE_TAG}"

# Start the application
echo "Starting application..."
docker compose -f docker-compose.prod.yml up -d
print_success "Application started"

# Wait for health check
echo "Waiting for application to be ready..."
MAX_ATTEMPTS=30
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if curl -f http://localhost:27893/api/filters &> /dev/null; then
        print_success "Application is ready!"
        break
    fi
    ATTEMPT=$((ATTEMPT + 1))
    echo -n "."
    sleep 2
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    print_error "Application failed to start. Check logs with:"
    echo "docker compose -f docker-compose.prod.yml logs"
    exit 1
fi

# Display status
echo ""
echo "========================================="
echo "Deployment Complete!"
echo "========================================="
docker compose -f docker-compose.prod.yml ps

echo ""
echo "Access the application at:"
echo "  - Frontend: http://localhost:27893"
echo "  - API Docs: http://localhost:27893/docs"
echo ""
echo "Useful commands:"
echo "  - View logs: docker compose -f docker-compose.prod.yml logs -f"
echo "  - Stop app: docker compose -f docker-compose.prod.yml down"
echo "  - Restart: docker compose -f docker-compose.prod.yml restart"
echo ""
print_success "Deployment successful!"