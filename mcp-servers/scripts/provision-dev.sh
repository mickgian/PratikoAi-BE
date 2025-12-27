#!/bin/bash
set -euo pipefail

# PratikoAI MCP Development Server Provisioning Script
# This script provisions a development environment for MCP servers

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_DIR="$PROJECT_ROOT/config"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    local missing_tools=()
    
    # Check for required tools
    command -v docker >/dev/null 2>&1 || missing_tools+=("docker")
    command -v docker-compose >/dev/null 2>&1 || missing_tools+=("docker-compose")
    command -v kubectl >/dev/null 2>&1 || missing_tools+=("kubectl")
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        log_error "Missing required tools: ${missing_tools[*]}. Please run ./scripts/install-prerequisites.sh first."
    fi
    
    log_success "All prerequisites satisfied"
}

# Load environment configuration
load_config() {
    log_info "Loading development configuration..."
    
    if [ ! -f "$CONFIG_DIR/.env.development" ]; then
        if [ -f "$CONFIG_DIR/env.example" ]; then
            log_warning "Development config not found, copying from example"
            cp "$CONFIG_DIR/env.example" "$CONFIG_DIR/.env.development"
        else
            log_error "No configuration file found. Please create $CONFIG_DIR/.env.development"
        fi
    fi
    
    # Source the configuration
    set -a
    source "$CONFIG_DIR/.env.development"
    set +a
    
    log_success "Configuration loaded"
}

# Create development infrastructure
create_infrastructure() {
    log_info "Creating development infrastructure..."
    
    # Create Docker network for MCP services
    if ! docker network inspect pratiko-mcp-dev >/dev/null 2>&1; then
        docker network create pratiko-mcp-dev
        log_success "Created Docker network: pratiko-mcp-dev"
    else
        log_info "Docker network already exists: pratiko-mcp-dev"
    fi
    
    # Create necessary directories
    mkdir -p "$PROJECT_ROOT/data/dev/mcp-server"
    mkdir -p "$PROJECT_ROOT/data/dev/redis"
    mkdir -p "$PROJECT_ROOT/data/dev/postgres"
    mkdir -p "$PROJECT_ROOT/logs/dev"
    
    log_success "Infrastructure directories created"
}

# Deploy MCP server
deploy_mcp_server() {
    log_info "Deploying MCP development server..."
    
    # Generate docker-compose configuration for development
    cat > "$PROJECT_ROOT/docker-compose.dev.yml" << EOF
version: '3.8'

services:
  mcp-server-dev:
    build:
      context: ./docker/mcp-server
      dockerfile: Dockerfile.dev
    container_name: pratiko-mcp-dev
    environment:
      - ENVIRONMENT=development
      - LOG_LEVEL=debug
      - REDIS_URL=redis://redis-dev:6379
      - POSTGRES_URL=postgresql://\${POSTGRES_USER}:\${POSTGRES_PASSWORD}@postgres-dev:5432/\${POSTGRES_DB}
      - JWT_SECRET_KEY=\${JWT_SECRET_KEY}
      - MCP_SERVER_PORT=8080
      - ENABLE_DEBUG=true
    ports:
      - "8080:8080"
      - "9090:9090"  # Metrics port
    volumes:
      - ./data/dev/mcp-server:/app/data
      - ./logs/dev:/app/logs
      - ./config:/app/config:ro
    networks:
      - pratiko-mcp-dev
    depends_on:
      - redis-dev
      - postgres-dev
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    resource_limits:
      cpus: '2.0'
      memory: 4G
    resource_reservations:
      cpus: '0.5'
      memory: 1G

  redis-dev:
    image: redis:7-alpine
    container_name: pratiko-redis-dev
    ports:
      - "6379:6379"
    volumes:
      - ./data/dev/redis:/data
    networks:
      - pratiko-mcp-dev
    restart: unless-stopped
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru

  postgres-dev:
    image: postgres:15-alpine
    container_name: pratiko-postgres-dev
    environment:
      - POSTGRES_DB=\${POSTGRES_DB:-pratiko_mcp_dev}
      - POSTGRES_USER=\${POSTGRES_USER:-pratiko}
      - POSTGRES_PASSWORD=\${POSTGRES_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - ./data/dev/postgres:/var/lib/postgresql/data
      - ./scripts/sql/init-dev.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - pratiko-mcp-dev
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U \${POSTGRES_USER:-pratiko}"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Development monitoring stack
  prometheus-dev:
    image: prom/prometheus:latest
    container_name: pratiko-prometheus-dev
    ports:
      - "9091:9090"
    volumes:
      - ./monitoring/prometheus/dev.yml:/etc/prometheus/prometheus.yml:ro
      - ./data/dev/prometheus:/prometheus
    networks:
      - pratiko-mcp-dev
    restart: unless-stopped
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'

  grafana-dev:
    image: grafana/grafana:latest
    container_name: pratiko-grafana-dev
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=\${GRAFANA_ADMIN_PASSWORD:-admin123}
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - ./data/dev/grafana:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards:ro
      - ./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources:ro
    networks:
      - pratiko-mcp-dev
    restart: unless-stopped

networks:
  pratiko-mcp-dev:
    external: true

volumes:
  postgres-dev-data:
  redis-dev-data:
  grafana-dev-data:
  prometheus-dev-data:
EOF

    # Start the development stack
    docker-compose -f "$PROJECT_ROOT/docker-compose.dev.yml" up -d
    
    log_success "MCP development server deployed"
}

# Setup monitoring
setup_monitoring() {
    log_info "Setting up development monitoring..."
    
    # Create Prometheus configuration
    mkdir -p "$PROJECT_ROOT/monitoring/prometheus"
    cat > "$PROJECT_ROOT/monitoring/prometheus/dev.yml" << EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'mcp-server-dev'
    static_configs:
      - targets: ['mcp-server-dev:9090']
    scrape_interval: 10s
    metrics_path: /metrics

  - job_name: 'redis-dev'
    static_configs:
      - targets: ['redis-dev:6379']
    scrape_interval: 30s

  - job_name: 'postgres-dev'
    static_configs:
      - targets: ['postgres-dev:5432']
    scrape_interval: 30s

  - job_name: 'prometheus-dev'
    static_configs:
      - targets: ['localhost:9090']
EOF

    # Create Grafana datasource configuration
    mkdir -p "$PROJECT_ROOT/monitoring/grafana/datasources"
    cat > "$PROJECT_ROOT/monitoring/grafana/datasources/prometheus.yml" << EOF
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus-dev:9090
    isDefault: true
    editable: true
EOF

    log_success "Development monitoring configured"
}

# Create development certificates
setup_certificates() {
    log_info "Setting up development certificates..."
    
    CERT_DIR="$PROJECT_ROOT/config/security/certs/dev"
    mkdir -p "$CERT_DIR"
    
    if [ ! -f "$CERT_DIR/server.crt" ]; then
        # Generate self-signed certificate for development
        openssl req -x509 -newkey rsa:4096 -keyout "$CERT_DIR/server.key" -out "$CERT_DIR/server.crt" \
            -days 365 -nodes -subj "/C=US/ST=CA/L=San Francisco/O=PratikoAI/CN=localhost"
        
        log_success "Development certificates generated"
    else
        log_info "Development certificates already exist"
    fi
}

# Verify deployment
verify_deployment() {
    log_info "Verifying development deployment..."
    
    # Wait for services to be ready
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        log_info "Attempt $attempt/$max_attempts: Checking service health..."
        
        if curl -f http://localhost:8080/health >/dev/null 2>&1; then
            log_success "MCP server is healthy!"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            log_error "MCP server failed to start within timeout"
        fi
        
        sleep 10
        ((attempt++))
    done
    
    # Check other services
    if curl -f http://localhost:3000 >/dev/null 2>&1; then
        log_success "Grafana is accessible at http://localhost:3000"
    else
        log_warning "Grafana may not be ready yet"
    fi
    
    if curl -f http://localhost:9091 >/dev/null 2>&1; then
        log_success "Prometheus is accessible at http://localhost:9091"
    else
        log_warning "Prometheus may not be ready yet"
    fi
}

# Print deployment summary
print_summary() {
    log_success "Development MCP server deployment completed!"
    echo
    echo "🚀 Services Available:"
    echo "   • MCP Server:   http://localhost:8080"
    echo "   • Health Check: http://localhost:8080/health"
    echo "   • Metrics:      http://localhost:8080/metrics"
    echo "   • Grafana:      http://localhost:3000 (admin/admin123)"
    echo "   • Prometheus:   http://localhost:9091"
    echo "   • Redis:        localhost:6379"
    echo "   • PostgreSQL:   localhost:5432"
    echo
    echo "📋 Management Commands:"
    echo "   • View logs:    docker-compose -f docker-compose.dev.yml logs -f"
    echo "   • Stop:         docker-compose -f docker-compose.dev.yml down"
    echo "   • Restart:      docker-compose -f docker-compose.dev.yml restart"
    echo "   • Status:       docker-compose -f docker-compose.dev.yml ps"
    echo
    echo "🔧 Development Features:"
    echo "   • Hot reload enabled"
    echo "   • Debug logging active"
    echo "   • Resource limits: 2 CPU, 4GB RAM"
    echo "   • Data persistence in ./data/dev/"
    echo
}

# Main execution
main() {
    log_info "Starting PratikoAI MCP Development Server Provisioning"
    echo "=================================================="
    
    check_prerequisites
    load_config
    create_infrastructure
    setup_certificates
    deploy_mcp_server
    setup_monitoring
    verify_deployment
    print_summary
    
    log_success "Development environment is ready! 🎉"
}

# Cleanup function for interrupted execution
cleanup() {
    log_warning "Provisioning interrupted. Cleaning up..."
    docker-compose -f "$PROJECT_ROOT/docker-compose.dev.yml" down --remove-orphans 2>/dev/null || true
    exit 1
}

# Set trap for cleanup
trap cleanup INT TERM

# Run main function
main "$@"