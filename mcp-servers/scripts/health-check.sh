#!/bin/bash
set -euo pipefail

# PratikoAI MCP Server Health Check Script
# Comprehensive health monitoring for all environments

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_DIR="$PROJECT_ROOT/config"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
HEALTH_CHECK_TIMEOUT=30
MAX_RETRIES=3
RETRY_DELAY=5

# Health check results
HEALTH_RESULTS=()
CRITICAL_ISSUES=0
WARNING_ISSUES=0

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
    ((WARNING_ISSUES++))
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    ((CRITICAL_ISSUES++))
}

log_health_result() {
    local service=$1
    local status=$2
    local details=$3
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    HEALTH_RESULTS+=("$timestamp|$service|$status|$details")
    
    if [ "$status" = "HEALTHY" ]; then
        log_success "$service: $details"
    elif [ "$status" = "WARNING" ]; then
        log_warning "$service: $details"
    else
        log_error "$service: $details"
    fi
}

# HTTP health check with retries
http_health_check() {
    local url=$1
    local service_name=$2
    local expected_status=${3:-200}
    local timeout=${4:-$HEALTH_CHECK_TIMEOUT}
    
    log_info "Checking $service_name health at $url"
    
    for ((i=1; i<=MAX_RETRIES; i++)); do
        local response_code
        local response_time
        
        # Capture both status code and response time
        local curl_output
        curl_output=$(curl -s -w "%{http_code}|%{time_total}" \
            --connect-timeout "$timeout" \
            --max-time "$timeout" \
            "$url" 2>/dev/null || echo "000|0")
        
        response_code=$(echo "$curl_output" | cut -d'|' -f1)
        response_time=$(echo "$curl_output" | cut -d'|' -f2)
        
        if [ "$response_code" = "$expected_status" ]; then
            local response_time_ms
            response_time_ms=$(echo "$response_time * 1000" | bc -l | cut -d'.' -f1)
            
            if (( response_time_ms > 5000 )); then
                log_health_result "$service_name" "WARNING" "Slow response: ${response_time_ms}ms"
            else
                log_health_result "$service_name" "HEALTHY" "Response time: ${response_time_ms}ms"
            fi
            return 0
        fi
        
        if [ $i -lt $MAX_RETRIES ]; then
            log_info "Attempt $i failed (HTTP $response_code), retrying in ${RETRY_DELAY}s..."
            sleep $RETRY_DELAY
        fi
    done
    
    log_health_result "$service_name" "CRITICAL" "Failed after $MAX_RETRIES attempts (HTTP $response_code)"
    return 1
}

# Database connectivity check
database_health_check() {
    local env=$1
    local service_name="PostgreSQL-$env"
    
    log_info "Checking $service_name connectivity"
    
    case $env in
        "development")
            local db_host="postgres-dev"
            local db_port="5432"
            local db_name="pratiko_mcp_dev"
            ;;
        "staging")
            local db_host=$(kubectl get service postgres-staging-primary -n mcp-staging -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "postgres-staging")
            local db_port="5432"
            local db_name="pratiko_mcp_staging"
            ;;
        "production")
            local db_host=$(kubectl get service postgres-production-primary -n mcp-production -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "postgres-production")
            local db_port="5432"
            local db_name="pratiko_mcp_production"
            ;;
    esac
    
    # Test database connectivity
    local start_time=$(date +%s%3N)
    if timeout $HEALTH_CHECK_TIMEOUT pg_isready -h "$db_host" -p "$db_port" -d "$db_name" >/dev/null 2>&1; then
        local end_time=$(date +%s%3N)
        local response_time=$((end_time - start_time))
        
        # Test connection pool and query performance
        local connection_count
        connection_count=$(timeout 10 psql -h "$db_host" -p "$db_port" -d "$db_name" -t -c "SELECT count(*) FROM pg_stat_activity;" 2>/dev/null | xargs || echo "0")
        
        if [ "$connection_count" -gt 0 ] && [ "$connection_count" -lt 100 ]; then
            log_health_result "$service_name" "HEALTHY" "Active connections: $connection_count, Response: ${response_time}ms"
        elif [ "$connection_count" -ge 100 ]; then
            log_health_result "$service_name" "WARNING" "High connection count: $connection_count"
        else
            log_health_result "$service_name" "WARNING" "Could not verify connection count"
        fi
    else
        log_health_result "$service_name" "CRITICAL" "Database not accessible"
    fi
}

# Redis connectivity check
redis_health_check() {
    local env=$1
    local service_name="Redis-$env"
    
    log_info "Checking $service_name connectivity"
    
    case $env in
        "development")
            local redis_host="redis-dev"
            local redis_port="6379"
            ;;
        "staging")
            local redis_host=$(kubectl get service redis-staging-master -n mcp-staging -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "redis-staging")
            local redis_port="6379"
            ;;
        "production")
            local redis_host=$(kubectl get service redis-production-master -n mcp-production -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "redis-production")
            local redis_port="6379"
            ;;
    esac
    
    # Test Redis connectivity and performance
    local start_time=$(date +%s%3N)
    if timeout $HEALTH_CHECK_TIMEOUT redis-cli -h "$redis_host" -p "$redis_port" ping >/dev/null 2>&1; then
        local end_time=$(date +%s%3N)
        local response_time=$((end_time - start_time))
        
        # Check memory usage
        local memory_usage
        memory_usage=$(timeout 10 redis-cli -h "$redis_host" -p "$redis_port" info memory | grep "used_memory_human" | cut -d: -f2 | tr -d '\r' 2>/dev/null || echo "unknown")
        
        # Check connected clients
        local connected_clients
        connected_clients=$(timeout 10 redis-cli -h "$redis_host" -p "$redis_port" info clients | grep "connected_clients" | cut -d: -f2 | tr -d '\r' 2>/dev/null || echo "0")
        
        if [ "$connected_clients" -lt 100 ]; then
            log_health_result "$service_name" "HEALTHY" "Memory: $memory_usage, Clients: $connected_clients, Response: ${response_time}ms"
        else
            log_health_result "$service_name" "WARNING" "High client count: $connected_clients"
        fi
    else
        log_health_result "$service_name" "CRITICAL" "Redis not accessible"
    fi
}

# Kubernetes cluster health check
kubernetes_health_check() {
    local env=$1
    local namespace
    
    case $env in
        "staging")
            namespace="mcp-staging"
            ;;
        "production")
            namespace="mcp-production"
            ;;
        *)
            log_info "Skipping Kubernetes check for $env environment"
            return 0
            ;;
    esac
    
    log_info "Checking Kubernetes cluster health for $env"
    
    # Check if kubectl is available and configured
    if ! command -v kubectl >/dev/null 2>&1; then
        log_health_result "Kubernetes-$env" "WARNING" "kubectl not available"
        return 1
    fi
    
    # Check cluster connectivity
    if ! kubectl cluster-info >/dev/null 2>&1; then
        log_health_result "Kubernetes-$env" "CRITICAL" "Cannot connect to cluster"
        return 1
    fi
    
    # Check namespace exists
    if ! kubectl get namespace "$namespace" >/dev/null 2>&1; then
        log_health_result "Kubernetes-$env" "CRITICAL" "Namespace $namespace not found"
        return 1
    fi
    
    # Check pod status
    local pods_status
    pods_status=$(kubectl get pods -n "$namespace" --no-headers 2>/dev/null | wc -l || echo "0")
    local ready_pods
    ready_pods=$(kubectl get pods -n "$namespace" --no-headers 2>/dev/null | grep -c "Running\|Completed" || echo "0")
    
    if [ "$pods_status" -eq 0 ]; then
        log_health_result "Kubernetes-$env" "CRITICAL" "No pods found in namespace"
    elif [ "$ready_pods" -eq "$pods_status" ]; then
        log_health_result "Kubernetes-$env" "HEALTHY" "$ready_pods/$pods_status pods ready"
    else
        log_health_result "Kubernetes-$env" "WARNING" "$ready_pods/$pods_status pods ready"
    fi
    
    # Check services
    local services_count
    services_count=$(kubectl get services -n "$namespace" --no-headers 2>/dev/null | wc -l || echo "0")
    log_health_result "Kubernetes-Services-$env" "HEALTHY" "$services_count services found"
    
    # Check deployments
    local deployments
    deployments=$(kubectl get deployments -n "$namespace" --no-headers 2>/dev/null | awk '$2 != $4 {print $1}' | tr '\n' ',' | sed 's/,$//' || echo "")
    
    if [ -z "$deployments" ]; then
        log_health_result "Kubernetes-Deployments-$env" "HEALTHY" "All deployments ready"
    else
        log_health_result "Kubernetes-Deployments-$env" "WARNING" "Unready deployments: $deployments"
    fi
}

# Resource utilization check
resource_utilization_check() {
    local env=$1
    
    log_info "Checking resource utilization for $env"
    
    case $env in
        "development")
            # Check Docker container resources
            if command -v docker >/dev/null 2>&1; then
                local container_stats
                container_stats=$(docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null | grep -E "(mcp|postgres|redis)" || echo "")
                
                if [ -n "$container_stats" ]; then
                    log_health_result "Resources-$env" "HEALTHY" "Container stats available"
                else
                    log_health_result "Resources-$env" "WARNING" "No container stats available"
                fi
            fi
            ;;
        "staging"|"production")
            local namespace
            case $env in
                "staging") namespace="mcp-staging" ;;
                "production") namespace="mcp-production" ;;
            esac
            
            if command -v kubectl >/dev/null 2>&1; then
                # Check node resources
                local node_usage
                node_usage=$(kubectl top nodes 2>/dev/null | tail -n +2 | awk '{print $1 ": CPU " $2 ", Memory " $3}' | head -3 | tr '\n' '; ' || echo "")
                
                if [ -n "$node_usage" ]; then
                    log_health_result "Node-Resources-$env" "HEALTHY" "$node_usage"
                else
                    log_health_result "Node-Resources-$env" "WARNING" "Node metrics not available"
                fi
                
                # Check pod resources
                local pod_usage
                pod_usage=$(kubectl top pods -n "$namespace" 2>/dev/null | tail -n +2 | awk '{cpu+=$2; mem+=$3} END {print "CPU: " cpu ", Memory: " mem}' || echo "")
                
                if [ -n "$pod_usage" ]; then
                    log_health_result "Pod-Resources-$env" "HEALTHY" "$pod_usage"
                else
                    log_health_result "Pod-Resources-$env" "WARNING" "Pod metrics not available"
                fi
            fi
            ;;
    esac
}

# SSL certificate check
ssl_certificate_check() {
    local url=$1
    local service_name=$2
    
    log_info "Checking SSL certificate for $service_name"
    
    local cert_info
    cert_info=$(timeout $HEALTH_CHECK_TIMEOUT openssl s_client -connect "${url}:443" -servername "$url" </dev/null 2>/dev/null | openssl x509 -noout -dates 2>/dev/null || echo "")
    
    if [ -n "$cert_info" ]; then
        local expiry_date
        expiry_date=$(echo "$cert_info" | grep "notAfter" | cut -d= -f2)
        
        local expiry_timestamp
        expiry_timestamp=$(date -d "$expiry_date" +%s 2>/dev/null || echo "0")
        local current_timestamp
        current_timestamp=$(date +%s)
        local days_until_expiry
        days_until_expiry=$(( (expiry_timestamp - current_timestamp) / 86400 ))
        
        if [ "$days_until_expiry" -gt 30 ]; then
            log_health_result "SSL-$service_name" "HEALTHY" "Certificate expires in $days_until_expiry days"
        elif [ "$days_until_expiry" -gt 7 ]; then
            log_health_result "SSL-$service_name" "WARNING" "Certificate expires in $days_until_expiry days"
        else
            log_health_result "SSL-$service_name" "CRITICAL" "Certificate expires in $days_until_expiry days"
        fi
    else
        log_health_result "SSL-$service_name" "WARNING" "Could not retrieve certificate information"
    fi
}

# Backup verification check
backup_verification_check() {
    local env=$1
    
    log_info "Checking backup status for $env"
    
    case $env in
        "production"|"staging")
            # Check Velero backups
            if command -v kubectl >/dev/null 2>&1; then
                local recent_backups
                recent_backups=$(kubectl get backups -n velero --no-headers 2>/dev/null | grep -E "(Completed|InProgress)" | head -3 | awk '{print $1 " (" $3 ")"}' | tr '\n' ', ' | sed 's/, $//' || echo "")
                
                if [ -n "$recent_backups" ]; then
                    log_health_result "Backups-$env" "HEALTHY" "Recent backups: $recent_backups"
                else
                    log_health_result "Backups-$env" "WARNING" "No recent backups found"
                fi
            fi
            
            # Check database backups (if S3 CLI is available)
            if command -v aws >/dev/null 2>&1; then
                local db_backups
                db_backups=$(aws s3 ls "s3://pratiko-backups/$env/postgres/" 2>/dev/null | tail -3 | awk '{print $4}' | tr '\n' ', ' | sed 's/, $//' || echo "")
                
                if [ -n "$db_backups" ]; then
                    log_health_result "DB-Backups-$env" "HEALTHY" "Recent DB backups: $db_backups"
                else
                    log_health_result "DB-Backups-$env" "WARNING" "No recent DB backups found"
                fi
            fi
            ;;
        *)
            log_info "Skipping backup check for $env environment"
            ;;
    esac
}

# Performance metrics check
performance_metrics_check() {
    local env=$1
    
    log_info "Checking performance metrics for $env"
    
    # This would typically query Prometheus for key metrics
    # For now, we'll simulate the check
    
    local metrics_available=false
    
    # Check if Prometheus is accessible
    case $env in
        "development")
            if curl -sf "http://localhost:9091/api/v1/query?query=up" >/dev/null 2>&1; then
                metrics_available=true
            fi
            ;;
        "staging"|"production")
            if command -v kubectl >/dev/null 2>&1; then
                if kubectl get service prometheus-operated -n monitoring >/dev/null 2>&1; then
                    metrics_available=true
                fi
            fi
            ;;
    esac
    
    if $metrics_available; then
        log_health_result "Metrics-$env" "HEALTHY" "Performance metrics are being collected"
    else
        log_health_result "Metrics-$env" "WARNING" "Performance metrics not available"
    fi
}

# Main health check function
run_health_checks() {
    local environment=${1:-"all"}
    
    log_info "Starting health checks for environment: $environment"
    echo "=================================================="
    
    case $environment in
        "development"|"all")
            log_info "Checking Development Environment"
            echo "----------------------------------"
            
            # MCP Server health
            http_health_check "http://localhost:8080/health" "MCP-Server-Dev"
            
            # Database health
            database_health_check "development"
            
            # Redis health
            redis_health_check "development"
            
            # Resource utilization
            resource_utilization_check "development"
            
            # Performance metrics
            performance_metrics_check "development"
            
            echo
            ;;
    esac
    
    case $environment in
        "staging"|"all")
            log_info "Checking Staging Environment"
            echo "-----------------------------"
            
            # MCP Server health
            http_health_check "https://mcp-staging.pratiko.ai/health" "MCP-Server-Staging"
            
            # Database health
            database_health_check "staging"
            
            # Redis health
            redis_health_check "staging"
            
            # Kubernetes health
            kubernetes_health_check "staging"
            
            # Resource utilization
            resource_utilization_check "staging"
            
            # SSL certificate check
            ssl_certificate_check "mcp-staging.pratiko.ai" "Staging"
            
            # Backup verification
            backup_verification_check "staging"
            
            # Performance metrics
            performance_metrics_check "staging"
            
            echo
            ;;
    esac
    
    case $environment in
        "production"|"all")
            log_info "Checking Production Environment"
            echo "-------------------------------"
            
            # MCP Server health
            http_health_check "https://mcp.pratiko.ai/health" "MCP-Server-Production"
            
            # Database health
            database_health_check "production"
            
            # Redis health
            redis_health_check "production"
            
            # Kubernetes health
            kubernetes_health_check "production"
            
            # Resource utilization
            resource_utilization_check "production"
            
            # SSL certificate check
            ssl_certificate_check "mcp.pratiko.ai" "Production"
            
            # Backup verification
            backup_verification_check "production"
            
            # Performance metrics
            performance_metrics_check "production"
            
            echo
            ;;
    esac
}

# Generate health report
generate_health_report() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local report_file="/tmp/mcp-health-report-$(date +%Y%m%d-%H%M%S).txt"
    
    echo "PratikoAI MCP Server Health Check Report" > "$report_file"
    echo "Generated: $timestamp" >> "$report_file"
    echo "=========================================" >> "$report_file"
    echo >> "$report_file"
    
    echo "Summary:" >> "$report_file"
    echo "--------" >> "$report_file"
    echo "Total Checks: ${#HEALTH_RESULTS[@]}" >> "$report_file"
    echo "Critical Issues: $CRITICAL_ISSUES" >> "$report_file"
    echo "Warning Issues: $WARNING_ISSUES" >> "$report_file"
    echo "Healthy Services: $((${#HEALTH_RESULTS[@]} - CRITICAL_ISSUES - WARNING_ISSUES))" >> "$report_file"
    echo >> "$report_file"
    
    echo "Detailed Results:" >> "$report_file"
    echo "-----------------" >> "$report_file"
    
    for result in "${HEALTH_RESULTS[@]}"; do
        local timestamp=$(echo "$result" | cut -d'|' -f1)
        local service=$(echo "$result" | cut -d'|' -f2)
        local status=$(echo "$result" | cut -d'|' -f3)
        local details=$(echo "$result" | cut -d'|' -f4)
        
        printf "%-20s %-12s %-10s %s\n" "$timestamp" "$service" "$status" "$details" >> "$report_file"
    done
    
    echo >> "$report_file"
    echo "Health Check Completed: $timestamp" >> "$report_file"
    
    log_info "Health report generated: $report_file"
    
    # Display report summary
    echo
    echo "Health Check Summary:"
    echo "===================="
    echo "Total Checks: ${#HEALTH_RESULTS[@]}"
    echo "Critical Issues: $CRITICAL_ISSUES"
    echo "Warning Issues: $WARNING_ISSUES"
    echo "Healthy Services: $((${#HEALTH_RESULTS[@]} - CRITICAL_ISSUES - WARNING_ISSUES))"
    
    # Determine overall health status
    if [ $CRITICAL_ISSUES -gt 0 ]; then
        log_error "OVERALL STATUS: CRITICAL - Immediate attention required"
        return 2
    elif [ $WARNING_ISSUES -gt 0 ]; then
        log_warning "OVERALL STATUS: WARNING - Some issues detected"
        return 1
    else
        log_success "OVERALL STATUS: HEALTHY - All systems operational"
        return 0
    fi
}

# Main execution
main() {
    local environment=${1:-"all"}
    local format=${2:-"console"}  # console, json, report
    
    # Check prerequisites
    if ! command -v curl >/dev/null 2>&1; then
        log_error "curl is required for health checks"
        exit 1
    fi
    
    if ! command -v bc >/dev/null 2>&1; then
        log_warning "bc is recommended for precise calculations"
    fi
    
    # Run health checks
    run_health_checks "$environment"
    
    # Generate report
    case $format in
        "report")
            generate_health_report
            ;;
        "json")
            # Generate JSON output
            local json_output="{"
            json_output+="\"timestamp\":\"$(date -Iseconds)\","
            json_output+="\"total_checks\":${#HEALTH_RESULTS[@]},"
            json_output+="\"critical_issues\":$CRITICAL_ISSUES,"
            json_output+="\"warning_issues\":$WARNING_ISSUES,"
            json_output+="\"healthy_services\":$((${#HEALTH_RESULTS[@]} - CRITICAL_ISSUES - WARNING_ISSUES)),"
            json_output+="\"results\":["
            
            local first=true
            for result in "${HEALTH_RESULTS[@]}"; do
                if [ "$first" = true ]; then
                    first=false
                else
                    json_output+=","
                fi
                
                local timestamp=$(echo "$result" | cut -d'|' -f1)
                local service=$(echo "$result" | cut -d'|' -f2)
                local status=$(echo "$result" | cut -d'|' -f3)
                local details=$(echo "$result" | cut -d'|' -f4)
                
                json_output+="{\"timestamp\":\"$timestamp\",\"service\":\"$service\",\"status\":\"$status\",\"details\":\"$details\"}"
            done
            
            json_output+="]}"
            echo "$json_output"
            ;;
        *)
            generate_health_report
            ;;
    esac
    
    # Exit with appropriate code
    if [ $CRITICAL_ISSUES -gt 0 ]; then
        exit 2
    elif [ $WARNING_ISSUES -gt 0 ]; then
        exit 1
    else
        exit 0
    fi
}

# Help function
show_help() {
    echo "PratikoAI MCP Server Health Check Script"
    echo "========================================"
    echo
    echo "Usage: $0 [ENVIRONMENT] [FORMAT]"
    echo
    echo "ENVIRONMENT:"
    echo "  all            Check all environments (default)"
    echo "  development    Check development environment only"
    echo "  staging        Check staging environment only"
    echo "  production     Check production environment only"
    echo
    echo "FORMAT:"
    echo "  console        Display results in console (default)"
    echo "  report         Generate detailed text report"
    echo "  json           Output results in JSON format"
    echo
    echo "Examples:"
    echo "  $0                          # Check all environments"
    echo "  $0 production               # Check production only"
    echo "  $0 staging report           # Generate staging report"
    echo "  $0 all json                 # JSON output for all environments"
    echo
    echo "Exit Codes:"
    echo "  0    All systems healthy"
    echo "  1    Warning issues detected"
    echo "  2    Critical issues detected"
}

# Handle command line arguments
case "${1:-}" in
    -h|--help|help)
        show_help
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac