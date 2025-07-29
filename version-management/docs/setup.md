# 🔧 Setup Guide

This guide walks you through setting up the PratikoAI Version Management System from scratch.

## Prerequisites

- Python 3.11 or higher
- PostgreSQL 13+ (or SQLite for development)
- Redis (optional, for caching)
- Git
- Docker (optional, for containerized deployment)

## 1. Environment Setup

### Local Development

```bash
# Clone the repository
git clone https://github.com/your-org/PratikoAi-BE.git
cd PratikoAi-BE/version-management

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Production Environment

```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install python3.11 python3.11-venv postgresql-client redis-tools

# Create application user
sudo useradd -m -s /bin/bash pratiko-version
sudo su - pratiko-version

# Setup application directory
mkdir -p /opt/pratiko-version
cd /opt/pratiko-version
python3.11 -m venv venv
source venv/bin/activate
```

## 2. Database Setup

### PostgreSQL (Recommended for Production)

```sql
-- Create database and user (as postgres superuser)
CREATE DATABASE version_registry;
CREATE USER version_manager WITH PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE version_registry TO version_manager;

-- Connect to the database
\c version_registry

-- Grant schema permissions
GRANT ALL ON SCHEMA public TO version_manager;
GRANT ALL ON ALL TABLES IN SCHEMA public TO version_manager;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO version_manager;
```

### SQLite (Development Only)

```bash
# SQLite database will be created automatically
export VERSION_REGISTRY_DB_URL="sqlite:///version_registry.db"
```

### Initialize Database Schema

```bash
# Set database URL
export VERSION_REGISTRY_DB_URL="postgresql://version_manager:secure_password_here@localhost/version_registry"

# Initialize the database
python -c "
from registry.database import init_database
db = init_database()
print('Database initialized successfully!')
"
```

## 3. Configuration

### Environment Variables

Create a `.env` file in the `version-management` directory:

```bash
# Database Configuration
VERSION_REGISTRY_DB_URL=postgresql://version_manager:password@localhost/version_registry

# API Configuration
VERSION_REGISTRY_URL=http://localhost:8001
VERSION_REGISTRY_TOKEN=your-secure-api-token-here
API_HOST=0.0.0.0
API_PORT=8001

# Redis Configuration (optional)
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-for-jwt-signing
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/pratiko-version/app.log

# GitHub Integration
GITHUB_TOKEN=your-github-token
GITHUB_WEBHOOK_SECRET=your-webhook-secret
```

### Configuration File

Create `config/settings.yaml`:

```yaml
version_management:
  database:
    url: ${VERSION_REGISTRY_DB_URL}
    pool_size: 10
    max_overflow: 20
    pool_timeout: 30
    
  api:
    host: ${API_HOST:0.0.0.0}
    port: ${API_PORT:8001}
    workers: 4
    reload: false
    
  compatibility:
    strict_mode: false
    warning_as_error: false
    max_dependency_depth: 5
    
  notifications:
    webhook_url: ${WEBHOOK_URL}
    email_enabled: false
    
  security:
    require_authentication: true
    allowed_origins:
      - "http://localhost:3000"
      - "https://your-frontend-domain.com"
```

## 4. Service Registration

### Registry API Service

Create a systemd service file `/etc/systemd/system/pratiko-version-api.service`:

```ini
[Unit]
Description=PratikoAI Version Registry API
After=network.target postgresql.service

[Service]
Type=simple
User=pratiko-version
Group=pratiko-version
WorkingDirectory=/opt/pratiko-version
Environment=PATH=/opt/pratiko-version/venv/bin
EnvironmentFile=/opt/pratiko-version/.env
ExecStart=/opt/pratiko-version/venv/bin/python -m registry.api
Restart=always
RestartSec=5

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/pratiko-version /var/log/pratiko-version

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable pratiko-version-api
sudo systemctl start pratiko-version-api
sudo systemctl status pratiko-version-api
```

### Nginx Reverse Proxy (Optional)

Create `/etc/nginx/sites-available/pratiko-version`:

```nginx
server {
    listen 80;
    server_name version-registry.your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Health check endpoint
    location /health {
        proxy_pass http://127.0.0.1:8001/health;
        access_log off;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/pratiko-version /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 5. GitHub Integration

### Repository Secrets

Add these secrets to both your backend and frontend repositories:

1. Go to your GitHub repository
2. Navigate to Settings → Secrets and variables → Actions
3. Add these repository secrets:

```
VERSION_REGISTRY_URL=https://version-registry.your-domain.com
VERSION_REGISTRY_TOKEN=your-secure-api-token
VERSION_REGISTRY_DB_URL=postgresql://user:pass@host/db
```

### Workflow Files

The workflow files are already created in:
- Backend: `.github/workflows/version-management.yml`
- Frontend: `../PratikoAi-KMP/.github/workflows/version-management.yml`

## 6. Testing the Setup

### API Health Check

```bash
# Test API connectivity
curl http://localhost:8001/health

# Expected response:
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "1.0.0",
  "database": "connected"
}
```

### Database Connectivity

```bash
# Test database operations
python -c "
from registry.database import init_database
db = init_database()
print('Database connection successful!')

# Test a simple query
from core.version_schema import ServiceType
versions = db.get_versions_by_service(ServiceType.BACKEND, limit=1)
print(f'Database query successful: {len(versions)} versions found')
"
```

### CLI Tools

```bash
# Test CLI functionality
python cli/version_cli.py list
python cli/version_cli.py --help
```

### Version Registration

```bash
# Register a test version
python cli/version_cli.py register
# Follow the interactive prompts

# Or via API
curl -X POST http://localhost:8001/api/v1/versions/register \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-token" \
  -d '{
    "service_type": "backend",
    "version": "1.0.0-test",
    "git_commit": "test123",
    "git_branch": "main",
    "change_type": "patch",
    "created_by": "setup-test"
  }'
```

## 7. Security Configuration

### API Authentication

Generate a secure API token:

```bash
# Generate a secure random token
python -c "
import secrets
token = secrets.token_urlsafe(32)
print(f'Generated API token: {token}')
"
```

### Database Security

```sql
-- Create read-only user for monitoring
CREATE USER version_monitor WITH PASSWORD 'monitor_password';
GRANT CONNECT ON DATABASE version_registry TO version_monitor;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO version_monitor;

-- Revoke unnecessary permissions
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
```

### Network Security

```bash
# Configure firewall (ufw example)
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw allow from 10.0.0.0/8 to any port 8001  # Internal API access
sudo ufw enable
```

## 8. Monitoring and Logging

### Log Configuration

Create log directory and configure rotation:

```bash
sudo mkdir -p /var/log/pratiko-version
sudo chown pratiko-version:pratiko-version /var/log/pratiko-version

# Configure logrotate
sudo tee /etc/logrotate.d/pratiko-version << EOF
/var/log/pratiko-version/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 pratiko-version pratiko-version
    postrotate
        systemctl reload pratiko-version-api
    endscript
}
EOF
```

### Monitoring Endpoints

The API provides these monitoring endpoints:

- `GET /health` - Basic health check
- `GET /metrics` - Prometheus metrics
- `GET /stats` - System statistics

### Integration with Monitoring Systems

Example Prometheus configuration:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'pratiko-version-registry'
    static_configs:
      - targets: ['localhost:8001']
    metrics_path: '/metrics'
    scrape_interval: 30s
```

## 9. Backup and Recovery

### Database Backup

```bash
# Create backup script
cat > /opt/pratiko-version/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/pratiko-version/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/version_registry_$TIMESTAMP.sql"

mkdir -p $BACKUP_DIR
pg_dump -h localhost -U version_manager version_registry > $BACKUP_FILE
gzip $BACKUP_FILE

# Keep only last 30 backups
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
EOF

chmod +x /opt/pratiko-version/backup.sh

# Add to crontab
echo "0 2 * * * /opt/pratiko-version/backup.sh" | crontab -u pratiko-version -
```

### Recovery Process

```bash
# Restore from backup
gunzip version_registry_20240115_020000.sql.gz
psql -h localhost -U version_manager -d version_registry < version_registry_20240115_020000.sql
```

## 10. Performance Tuning

### Database Optimization

```sql
-- Optimize PostgreSQL for version management workload
ALTER TABLE service_versions SET (autovacuum_vacuum_scale_factor = 0.05);
ALTER TABLE version_dependencies SET (autovacuum_vacuum_scale_factor = 0.05);

-- Create additional indexes for common queries
CREATE INDEX CONCURRENTLY idx_versions_service_created_at 
ON service_versions(service_type, created_at DESC);

CREATE INDEX CONCURRENTLY idx_deployments_env_service 
ON deployments(environment, service_type, deployed_at DESC);
```

### API Performance

```bash
# Configure connection pooling
export DB_POOL_SIZE=20
export DB_MAX_OVERFLOW=30
export DB_POOL_TIMEOUT=30

# Enable caching
export REDIS_URL=redis://localhost:6379/0
export CACHE_TTL=300
```

## Troubleshooting

Common setup issues and solutions:

### Database Connection Issues

```bash
# Test database connectivity
pg_isready -h localhost -p 5432 -U version_manager

# Check database permissions
psql -h localhost -U version_manager -d version_registry -c "\dt"
```

### API Service Issues

```bash
# Check service status
sudo systemctl status pratiko-version-api

# View logs
sudo journalctl -u pratiko-version-api -f

# Test API directly
python -m uvicorn registry.api:app --host 0.0.0.0 --port 8001 --reload
```

### GitHub Actions Issues

Check the workflow logs and ensure:
- Secrets are properly configured
- API endpoint is accessible from GitHub Actions
- Authentication tokens are valid

---

Your version management system should now be fully operational! Continue to the [Developer Guide](developer-guide.md) for day-to-day usage patterns.