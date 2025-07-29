#!/bin/bash
set -euo pipefail

# PratikoAI MCP Server - Startup-Friendly Provisioning Script
# Ultra-low-cost deployment for bootstrapped startups

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
    exit 1
}

log_startup() {
    echo -e "${PURPLE}[🚀]${NC} $1"
}

show_banner() {
    echo -e "${PURPLE}"
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║                  PratikoAI Startup MCP Setup                  ║"
    echo "║              Bootstrap Your Way to Success! 💰                ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

show_phase_info() {
    local phase=$1
    case $phase in
        "local")
            echo -e "${BLUE}📱 PHASE 1: Local Development${NC}"
            echo "• Cost: FREE (runs on your Mac)"
            echo "• Perfect for: Development, testing, demos"
            echo "• Capacity: You + 2-3 team members"
            ;;
        "staging")
            echo -e "${YELLOW}🏗️  PHASE 2: Staging Server${NC}"
            echo "• Cost: $24/month (DigitalOcean droplet)"
            echo "• Perfect for: Client demos, team collaboration"
            echo "• Capacity: 10-50 concurrent users"
            ;;
        "mvp")
            echo -e "${GREEN}🎯 PHASE 3: Production MVP${NC}"
            echo "• Cost: $5/month (using free tiers smartly)"
            echo "• Perfect for: First customers, validation"
            echo "• Capacity: 100+ real users"
            ;;
    esac
    echo
}

# Check system requirements
check_requirements() {
    log_info "Checking system requirements..."
    
    # Check if running on macOS
    if [[ "$OSTYPE" != "darwin"* ]]; then
        log_warning "This script is optimized for macOS development"
    fi
    
    # Check Docker
    if ! command -v docker >/dev/null 2>&1; then
        log_error "Docker is required. Install Docker Desktop: https://www.docker.com/products/docker-desktop"
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose >/dev/null 2>&1; then
        log_error "Docker Compose is required"
    fi
    
    # Check available disk space (at least 5GB)
    local available_space
    available_space=$(df -h . | awk 'NR==2{print $4}' | sed 's/Gi//')
    if [[ ${available_space%.*} -lt 5 ]]; then
        log_warning "Low disk space detected. Consider freeing up some space."
    fi
    
    log_success "System requirements check passed"
}

# Setup local development environment
setup_local_development() {
    log_startup "Setting up FREE local development environment..."
    show_phase_info "local"
    
    # Create local data directories
    mkdir -p "$PROJECT_ROOT/data/local"/{postgres,redis,mcp}
    mkdir -p "$PROJECT_ROOT/logs/local"
    
    # Create minimal docker-compose for local development
    cat > "$PROJECT_ROOT/docker-compose.local.yml" << 'EOF'
version: '3.8'

services:
  mcp-server:
    build:
      context: ./docker/mcp-server
      dockerfile: Dockerfile.local
    container_name: pratiko-mcp-local
    ports:
      - "8080:8080"
      - "9090:9090"  # Metrics
    environment:
      - ENVIRONMENT=local
      - LOG_LEVEL=debug
      - POSTGRES_URL=postgresql://pratiko:pratiko123@postgres:5432/pratiko_mcp
      - REDIS_URL=redis://redis:6379
      - JWT_SECRET_KEY=local-dev-secret-key-not-for-production
    volumes:
      - ./data/local/mcp:/app/data
      - ./logs/local:/app/logs
      - .:/app/src  # Hot reload for development
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.2'
          memory: 512M

  postgres:
    image: postgres:15-alpine
    container_name: pratiko-postgres-local
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_DB=pratiko_mcp
      - POSTGRES_USER=pratiko
      - POSTGRES_PASSWORD=pratiko123
    volumes:
      - ./data/local/postgres:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U pratiko"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M

  redis:
    image: redis:7-alpine
    container_name: pratiko-redis-local
    ports:
      - "6379:6379"
    volumes:
      - ./data/local/redis:/data
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5
    deploy:
      resources:
        limits:
          cpus: '0.2'
          memory: 256M

  # Lightweight monitoring for development
  prometheus:
    image: prom/prometheus:latest
    container_name: pratiko-prometheus-local
    ports:
      - "9091:9090"
    volumes:
      - ./monitoring/prometheus/local.yml:/etc/prometheus/prometheus.yml:ro
      - ./data/local/prometheus:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=7d'  # Keep only 7 days locally
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
    deploy:
      resources:
        limits:
          cpus: '0.3'
          memory: 512M

networks:
  default:
    name: pratiko-local
EOF

    # Create Prometheus config for local
    mkdir -p "$PROJECT_ROOT/monitoring/prometheus"
    cat > "$PROJECT_ROOT/monitoring/prometheus/local.yml" << 'EOF'
global:
  scrape_interval: 30s
  evaluation_interval: 30s

scrape_configs:
  - job_name: 'mcp-server-local'
    static_configs:
      - targets: ['mcp-server:9090']
    scrape_interval: 15s

  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
EOF

    # Start local environment
    log_info "Starting local development environment..."
    cd "$PROJECT_ROOT"
    docker-compose -f docker-compose.local.yml up -d
    
    # Wait for services to be ready
    log_info "Waiting for services to start..."
    sleep 30
    
    # Verify services are running
    if curl -sf http://localhost:8080/health >/dev/null 2>&1; then
        log_success "MCP Server is running at http://localhost:8080"
    else
        log_warning "MCP Server might still be starting up..."
    fi
    
    log_success "Local development environment is ready!"
    echo
    echo "🔗 Local Services:"
    echo "   • MCP Server:    http://localhost:8080"
    echo "   • Health Check:  http://localhost:8080/health"
    echo "   • Database:      localhost:5432 (pratiko/pratiko123)"
    echo "   • Redis:         localhost:6379"
    echo "   • Prometheus:    http://localhost:9091"
    echo
    echo "📝 Development Commands:"
    echo "   • View logs:     docker-compose -f docker-compose.local.yml logs -f"
    echo "   • Stop:          docker-compose -f docker-compose.local.yml down"
    echo "   • Restart:       docker-compose -f docker-compose.local.yml restart"
    echo "   • Clean up:      docker-compose -f docker-compose.local.yml down -v"
    echo
}

# Setup staging environment (single VPS)
setup_staging_environment() {
    log_startup "Setting up $24/month staging environment..."
    show_phase_info "staging"
    
    log_info "This will guide you through setting up a DigitalOcean droplet"
    echo
    echo "🔧 Manual Steps Required:"
    echo "1. Create DigitalOcean account (if you don't have one)"
    echo "2. Create a new droplet:"
    echo "   • Image: Ubuntu 22.04 LTS"
    echo "   • Size: s-2vcpu-4gb ($24/month)"
    echo "   • Region: Choose closest to your users"
    echo "   • Authentication: SSH Key (recommended)"
    echo
    
    read -p "Have you created the droplet? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Create your droplet first, then run this script again"
        return 0
    fi
    
    read -p "Enter your droplet IP address: " DROPLET_IP
    
    if [[ ! $DROPLET_IP =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
        log_error "Invalid IP address format"
    fi
    
    # Generate deployment script for the VPS
    cat > "$PROJECT_ROOT/deploy-staging.sh" << EOF
#!/bin/bash
# Auto-generated staging deployment script

set -euo pipefail

# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker \$USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.23.0/docker-compose-\$(uname -s)-\$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Create app directory
mkdir -p /opt/pratiko-mcp
cd /opt/pratiko-mcp

# Create staging docker-compose
cat > docker-compose.staging.yml << 'COMPOSE_EOF'
version: '3.8'

services:
  mcp-server:
    image: pratiko/mcp-server:staging
    container_name: mcp-staging
    ports:
      - "80:8080"
      - "443:8443"
    environment:
      - ENVIRONMENT=staging
      - LOG_LEVEL=info
      - POSTGRES_URL=postgresql://pratiko:staging_secure_password@postgres:5432/pratiko_mcp_staging
      - REDIS_URL=redis://redis:6379
      - JWT_SECRET_KEY=staging-jwt-secret-change-in-production
      - DOMAIN_NAME=staging.yourdomain.com
    volumes:
      - ./data/mcp:/app/data
      - ./logs:/app/logs
      - ./ssl:/app/ssl
    depends_on:
      - postgres
      - redis
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '1.5'
          memory: 2G

  postgres:
    image: postgres:15-alpine
    container_name: postgres-staging
    environment:
      - POSTGRES_DB=pratiko_mcp_staging
      - POSTGRES_USER=pratiko
      - POSTGRES_PASSWORD=staging_secure_password
    volumes:
      - ./data/postgres:/var/lib/postgresql/data
      - ./backups:/backups
    deploy:
      resources:
        limits:
          cpus: '0.8'
          memory: 1G
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    container_name: redis-staging
    volumes:
      - ./data/redis:/data
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
    deploy:
      resources:
        limits:
          cpus: '0.3'
          memory: 512M
    restart: unless-stopped

  # Simple reverse proxy with SSL
  nginx:
    image: nginx:alpine
    container_name: nginx-staging
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - mcp-server
    restart: unless-stopped

  # Automated backups
  backup:
    image: postgres:15-alpine
    container_name: backup-staging
    volumes:
      - ./backups:/backups
      - ./scripts:/scripts
    environment:
      - POSTGRES_PASSWORD=staging_secure_password
    command: /scripts/backup.sh
    restart: "no"
    profiles: ["backup"]

COMPOSE_EOF

# Create nginx config
mkdir -p ssl
cat > nginx.conf << 'NGINX_EOF'
server {
    listen 80;
    server_name _;
    
    # Redirect to HTTPS
    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl;
    server_name _;
    
    # SSL configuration (you'll need to add certificates)
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    location / {
        proxy_pass http://mcp-server:8080;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    location /health {
        proxy_pass http://mcp-server:8080/health;
        access_log off;
    }
}
NGINX_EOF

# Create backup script
mkdir -p scripts backups data/{postgres,redis,mcp} logs
cat > scripts/backup.sh << 'BACKUP_EOF'
#!/bin/bash
DATE=\$(date +%Y%m%d_%H%M%S)
pg_dump -h postgres -U pratiko pratiko_mcp_staging > /backups/backup_\$DATE.sql
gzip /backups/backup_\$DATE.sql

# Keep only last 7 days of backups
find /backups -name "*.sql.gz" -mtime +7 -delete
BACKUP_EOF

chmod +x scripts/backup.sh

# Create systemd service for auto-start
sudo tee /etc/systemd/system/pratiko-mcp.service > /dev/null << 'SERVICE_EOF'
[Unit]
Description=PratikoAI MCP Server
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/pratiko-mcp
ExecStart=/usr/local/bin/docker-compose -f docker-compose.staging.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.staging.yml down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
SERVICE_EOF

# Enable auto-start
sudo systemctl enable pratiko-mcp

# Start services
docker-compose -f docker-compose.staging.yml up -d

# Set up daily backups via cron
(crontab -l 2>/dev/null; echo "0 2 * * * cd /opt/pratiko-mcp && docker-compose -f docker-compose.staging.yml run --rm backup") | crontab -

echo "🎉 Staging environment deployed!"
echo "📍 Server IP: $DROPLET_IP"
echo "🔗 Access: http://$DROPLET_IP (configure your domain to point here)"
echo "💾 Backups: Daily at 2 AM"
EOF

    chmod +x "$PROJECT_ROOT/deploy-staging.sh"
    
    log_info "Deployment script created: deploy-staging.sh"
    log_info "To deploy to your staging server, run:"
    echo
    echo "  scp deploy-staging.sh root@$DROPLET_IP:/tmp/"
    echo "  ssh root@$DROPLET_IP 'bash /tmp/deploy-staging.sh'"
    echo
    log_success "Staging deployment script ready!"
}

# Setup production MVP (using free tiers)
setup_production_mvp() {
    log_startup "Setting up $5/month production MVP..."
    show_phase_info "mvp"
    
    echo "🎯 MVP Production Strategy:"
    echo "• Railway.app for hosting ($5/month)"
    echo "• Supabase for PostgreSQL (free tier)"
    echo "• Upstash for Redis (free tier)"
    echo "• Cloudflare for CDN/DNS (free)"
    echo
    
    # Create Railway deployment config
    mkdir -p "$PROJECT_ROOT/railway"
    
    cat > "$PROJECT_ROOT/railway/railway.toml" << 'EOF'
[build]
builder = "dockerfile"
dockerfile = "Dockerfile.production"

[deploy]
healthcheckPath = "/health"
healthcheckTimeout = 300
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 3

[[deploy.environmentVariables]]
name = "ENVIRONMENT"
value = "production"

[[deploy.environmentVariables]]
name = "LOG_LEVEL"
value = "info"

[[deploy.environmentVariables]]
name = "POSTGRES_URL"
value = "${{Postgres.DATABASE_URL}}"

[[deploy.environmentVariables]]
name = "REDIS_URL"
value = "${{UPSTASH_REDIS_URL}}"

[[deploy.environmentVariables]]
name = "JWT_SECRET_KEY"
value = "${{JWT_SECRET}}"

[environments.production]
variables = [
  "RAILWAY_ENVIRONMENT=production"
]
EOF

    cat > "$PROJECT_ROOT/Dockerfile.production" << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# Start command
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
EOF

    # Create setup guide
    cat > "$PROJECT_ROOT/MVP_SETUP_GUIDE.md" << 'EOF'
# PratikoAI MVP Production Setup Guide

## 🎯 Total Cost: $5/month for 100+ users!

### Step 1: Set up Supabase (Database) - FREE
1. Go to [supabase.com](https://supabase.com)
2. Sign up and create new project
3. Note your database URL from Settings > Database
4. Free tier includes: 500MB storage, 2 concurrent connections

### Step 2: Set up Upstash (Redis) - FREE  
1. Go to [upstash.com](https://upstash.com)
2. Create account and new Redis database
3. Choose region closest to your users
4. Note your Redis URL
5. Free tier includes: 10,000 commands/day

### Step 3: Set up Railway (App Hosting) - $5/month
1. Go to [railway.app](https://railway.app)
2. Connect your GitHub repository
3. Deploy from this directory
4. Add environment variables:
   - `POSTGRES_URL`: Your Supabase database URL
   - `REDIS_URL`: Your Upstash Redis URL
   - `JWT_SECRET_KEY`: Generate with `openssl rand -hex 64`
5. Deploy and get your railway.app URL

### Step 4: Set up Cloudflare (CDN/DNS) - FREE
1. Add your domain to Cloudflare
2. Point your domain to Railway app URL
3. Enable SSL/TLS encryption
4. Free tier includes: CDN, DDoS protection, SSL

### Step 5: Monitoring (Optional) - FREE
1. [Uptime Robot](https://uptimerobot.com): Monitor uptime (free)
2. [LogRocket](https://logrocket.com): Error tracking (free tier)
3. Railway provides basic metrics built-in

## 🚀 Scaling Path

### When you hit 100 users ($500/month revenue):
- Upgrade Supabase to Pro: $25/month (8GB database)
- Upgrade Upstash: $10/month (100K commands/day)
- **Total: $40/month for 1000+ users**

### When you hit 1000 users ($2000/month revenue):
- Upgrade Railway to Pro: $20/month (more resources)
- Add monitoring: $20/month (better observability)
- **Total: $80/month for 5000+ users**

## 📊 Capacity Planning

| Tier | Users | Requests/Month | Cost | Revenue |
|------|--------|----------------|------|---------|
| MVP | 100 | 100K | $5 | $500 |
| Growth | 1000 | 1M | $40 | $2000 |
| Scale | 5000 | 5M | $150 | $10000 |

**Rule: Infrastructure should be max 5% of revenue**
EOF

    log_success "MVP production configuration created!"
    echo
    echo "📋 Next steps:"
    echo "1. Read MVP_SETUP_GUIDE.md for detailed instructions"
    echo "2. Set up accounts with Supabase, Upstash, and Railway"
    echo "3. Deploy using the Railway configuration"
    echo "4. Add your domain with Cloudflare"
    echo
    echo "💡 Pro tip: Start with free tiers, upgrade only when you have paying customers!"
}

# Show cost comparison
show_cost_comparison() {
    echo -e "${PURPLE}"
    echo "💰 COST COMPARISON"
    echo "=================" 
    echo -e "${NC}"
    
    echo "Original Enterprise Setup:"
    echo "• Development: $75/month"
    echo "• Staging: $250/month" 
    echo "• Production: $1,200/month"
    echo "• TOTAL: $1,525/month 😱"
    echo
    
    echo -e "${GREEN}Startup-Optimized Setup:${NC}"
    echo "• Development: $0/month (local Mac) ✅"
    echo "• Staging: $24/month (DigitalOcean) ✅"
    echo "• Production MVP: $5/month (smart free tiers) ✅"
    echo "• TOTAL: $29/month 🎉"
    echo
    
    echo -e "${BLUE}📈 SAVINGS: 98% cost reduction!${NC}"
    echo "That's $1,496/month saved - enough for a full-time developer!"
    echo
    
    echo "💡 Smart Scaling Strategy:"
    echo "• Month 1-3: $29/month (validate your idea)"
    echo "• Month 4-12: $75/month (when you have customers)" 
    echo "• Month 12+: $200/month (when you're profitable)"
    echo
}

# Main menu
show_menu() {
    echo -e "${BLUE}What would you like to set up?${NC}"
    echo
    echo "1) 🏠 Local Development (FREE - runs on your Mac)"
    echo "2) 🏗️  Staging Server ($24/month - DigitalOcean VPS)"
    echo "3) 🎯 Production MVP ($5/month - using free tiers)"
    echo "4) 💰 Show cost comparison"
    echo "5) ❓ Help & documentation"
    echo "6) 🚪 Exit"
    echo
}

# Help documentation
show_help() {
    echo -e "${BLUE}🆘 PratikoAI Startup MCP Help${NC}"
    echo
    echo "This script helps you set up MCP servers optimized for startups:"
    echo
    echo "🏠 Local Development:"
    echo "   • Perfect for coding, testing, demos"
    echo "   • Runs entirely on your Mac using Docker"
    echo "   • Zero cloud costs"
    echo
    echo "🏗️ Staging Server:"
    echo "   • Single DigitalOcean droplet ($24/month)"
    echo "   • Great for client demos and team collaboration"
    echo "   • Handles up to 50 concurrent users"
    echo
    echo "🎯 Production MVP:"
    echo "   • Uses free tiers from multiple providers"
    echo "   • Railway ($5) + Supabase (free) + Upstash (free)"
    echo "   • Handles 100+ real users for just $5/month"
    echo
    echo "💡 Philosophy:"
    echo "   • Start minimal, scale smartly"
    echo "   • Only spend money when making money"
    echo "   • Infrastructure costs should be <5% of revenue"
    echo
    echo "📚 Additional Resources:"
    echo "   • MVP_SETUP_GUIDE.md - Detailed production setup"
    echo "   • startup-resource-allocation.yaml - Technical specs"
    echo "   • All configs are in the mcp-servers/ directory"
    echo
}

# Main function
main() {
    show_banner
    check_requirements
    show_cost_comparison
    
    while true; do
        show_menu
        read -p "Choose an option (1-6): " -n 1 -r
        echo
        echo
        
        case $REPLY in
            1)
                setup_local_development
                ;;
            2)
                setup_staging_environment
                ;;
            3)
                setup_production_mvp
                ;;
            4)
                show_cost_comparison
                ;;
            5)
                show_help
                ;;
            6)
                log_success "Good luck with your startup! 🚀"
                exit 0
                ;;
            *)
                log_warning "Invalid option. Please choose 1-6."
                ;;
        esac
        
        echo
        read -p "Press Enter to continue..." -r
        clear
        show_banner
    done
}

# Run main function
main "$@"