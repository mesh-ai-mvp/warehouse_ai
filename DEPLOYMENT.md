# Warehouse Management System - Deployment Guide

## Docker Hub Image

The application is now available on Docker Hub:
- **Repository**: `docker.io/sidhez/warehouse-management`
- **Latest**: `sidhez/warehouse-management:latest`
- **Version**: `sidhez/warehouse-management:v1.0.0`

## Server Deployment Instructions

### Prerequisites
- Docker and Docker Compose installed on your server
- At least 1GB RAM and 2GB disk space
- Port 27893 available (or configure as needed)

### Quick Deployment

1. **Create deployment directory**:
```bash
mkdir -p ~/warehouse-app
cd ~/warehouse-app
```

2. **Download configuration files**:
```bash
# Download production docker-compose
curl -O https://raw.githubusercontent.com/YOUR_REPO/docker-compose.prod.yml

# Or create it manually
cat > docker-compose.prod.yml << 'EOF'
version: '3.8'

services:
  warehouse-app:
    image: sidhez/warehouse-management:latest
    container_name: warehouse-management-prod
    ports:
      - "27893:8000"
    environment:
      - PORT=27893
      - HOST=0.0.0.0
      - WORKERS=2
      - PYTHONPATH=/app/src:/app
      - APP_ENV=production
      - DEBUG=false
      # Add your environment variables here or use env_file
    env_file:
      - .env
    volumes:
      - warehouse-logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:27893/api/filters', timeout=5)"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

volumes:
  warehouse-logs:
    driver: local
EOF
```

3. **Create environment file**:
```bash
cat > .env << 'EOF'
# AI Configuration (REQUIRED)
OPENAI_API_KEY=your_openai_api_key_here

# Database Configuration
DATABASE_URL=sqlite:///app/poc_supplychain.db

# Application Settings
APP_ENV=production
DEBUG=false

# Email Configuration (Optional)
SMTP_USER=your_email@example.com
SMTP_PASSWORD=your_smtp_password
EMAIL_FROM_NAME=Warehouse Team
EMAIL_BCC=admin@example.com
SMTP_HOST=smtp.example.com
SMTP_PORT=465

# Frontend Settings
VITE_ENABLE_MOCK_FALLBACKS=false
VITE_API_URL=/api
VITE_ENABLE_AI_GENERATION=true
EOF
```

4. **Edit the .env file with your actual values**:
```bash
nano .env
# Add your OPENAI_API_KEY and other credentials
```

5. **Start the application**:
```bash
docker compose -f docker-compose.prod.yml up -d
```

6. **Check if it's running**:
```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f
```

7. **Access the application**:
- Open browser to `http://YOUR_SERVER_IP:27893`
- API docs at `http://YOUR_SERVER_IP:27893/docs`

### Advanced Deployment

#### With Nginx Reverse Proxy

1. **Install Nginx**:
```bash
sudo apt update
sudo apt install nginx certbot python3-certbot-nginx
```

2. **Configure Nginx**:
```bash
sudo nano /etc/nginx/sites-available/warehouse
```

Add:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:27893;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_read_timeout 86400;
    }
}
```

3. **Enable site and restart Nginx**:
```bash
sudo ln -s /etc/nginx/sites-available/warehouse /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

4. **Setup SSL (optional but recommended)**:
```bash
sudo certbot --nginx -d your-domain.com
```

#### With Docker Swarm

1. **Initialize swarm**:
```bash
docker swarm init
```

2. **Deploy as service**:
```bash
docker service create \
  --name warehouse-app \
  --publish 27893:8000 \
  --env-file .env \
  --replicas 2 \
  --update-parallelism 1 \
  --update-delay 10s \
  sidhez/warehouse-management:latest
```

### Monitoring & Maintenance

#### View logs:
```bash
docker compose -f docker-compose.prod.yml logs -f warehouse-app
```

#### Update to latest version:
```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

#### Backup database:
```bash
docker compose -f docker-compose.prod.yml exec warehouse-app \
  sqlite3 /app/poc_supplychain.db ".backup /app/logs/backup.db"
docker cp warehouse-management-prod:/app/logs/backup.db ./backup-$(date +%Y%m%d).db
```

#### Monitor health:
```bash
curl http://localhost:27893/api/filters
```

### Troubleshooting

#### Container won't start:
```bash
# Check logs
docker compose -f docker-compose.prod.yml logs warehouse-app

# Check if port is in use
sudo lsof -i :27893
```

#### Application errors:
```bash
# Access container shell
docker exec -it warehouse-management-prod sh

# Check database
ls -la /app/poc_supplychain.db

# Test imports
python -c "from src.main import app; print('OK')"
```

#### Reset everything:
```bash
docker compose -f docker-compose.prod.yml down -v
docker compose -f docker-compose.prod.yml up -d
```

### Security Recommendations

1. **Always use HTTPS in production** - Setup SSL certificates
2. **Keep API keys secure** - Never commit .env files
3. **Regular updates** - Pull latest image regularly
4. **Firewall rules** - Only expose necessary ports
5. **Resource limits** - Set memory/CPU limits in production

### Environment Variables Reference

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| OPENAI_API_KEY | Yes | OpenAI API key for AI features | - |
| DATABASE_URL | No | Database connection string | sqlite:///app/poc_supplychain.db |
| APP_ENV | No | Environment (development/production) | production |
| DEBUG | No | Enable debug mode | false |
| PORT | No | Application port | 27893 |
| WORKERS | No | Number of Uvicorn workers | 2 |
| SMTP_* | No | Email configuration | - |
| VITE_* | No | Frontend configuration | - |

### Support

For issues or questions:
- Check application logs first
- Ensure all environment variables are set correctly
- Verify Docker and system requirements
- Check that the database was properly initialized

## Notes

⚠️ **Known Issue**: The application may take 30-60 seconds to fully initialize on first startup as it loads AI models and builds knowledge graphs. The health check will pass once initialization is complete.

✅ **Success Indicators**:
- Health check endpoint returns 200: `curl http://localhost:27893/api/filters`
- Logs show "Uvicorn running on http://0.0.0.0:8000"
- Frontend loads at http://localhost:27893