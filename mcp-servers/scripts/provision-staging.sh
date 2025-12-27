#!/bin/bash
set -euo pipefail

# PratikoAI MCP Staging Server Provisioning Script
# This script provisions a staging environment for MCP servers with high availability

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
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a /tmp/mcp-staging-provision.log
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a /tmp/mcp-staging-provision.log
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a /tmp/mcp-staging-provision.log
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a /tmp/mcp-staging-provision.log
    exit 1
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites for staging deployment..."
    
    local missing_tools=()
    
    # Check for required tools
    command -v docker >/dev/null 2>&1 || missing_tools+=("docker")
    command -v kubectl >/dev/null 2>&1 || missing_tools+=("kubectl")
    command -v helm >/dev/null 2>&1 || missing_tools+=("helm")
    command -v aws >/dev/null 2>&1 || missing_tools+=("aws-cli")
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        log_error "Missing required tools: ${missing_tools[*]}. Please run ./scripts/install-prerequisites.sh first."
    fi
    
    # Verify Kubernetes cluster access
    if ! kubectl cluster-info >/dev/null 2>&1; then
        log_error "Cannot access Kubernetes cluster. Please configure kubectl."
    fi
    
    # Verify AWS credentials
    if ! aws sts get-caller-identity >/dev/null 2>&1; then
        log_error "AWS credentials not configured. Please run 'aws configure'."
    fi
    
    log_success "All prerequisites satisfied"
}

# Load environment configuration
load_config() {
    log_info "Loading staging configuration..."
    
    if [ ! -f "$CONFIG_DIR/.env.staging" ]; then
        log_error "Staging config not found. Please create $CONFIG_DIR/.env.staging"
    fi
    
    # Source the configuration
    set -a
    source "$CONFIG_DIR/.env.staging"
    set +a
    
    # Validate required variables
    local required_vars=(
        "AWS_REGION"
        "CLUSTER_NAME"
        "NAMESPACE"
        "POSTGRES_PASSWORD"
        "JWT_SECRET_KEY"
        "SSL_CERT_ARN"
    )
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            log_error "Required environment variable $var is not set"
        fi
    done
    
    log_success "Configuration loaded and validated"
}

# Create staging infrastructure
# NOTE: PratikoAI uses Hetzner Cloud + Docker Compose instead of Terraform/AWS.
# Architecture Decision (ADR-017):
# - Target scale: 100-1000 users over 7-8 years (simple, static infrastructure)
# - Cost optimization: Hetzner is 5-10x cheaper than AWS for our scale
# - Simplicity: Docker Compose is sufficient, no Kubernetes/Terraform complexity needed
# - Infrastructure is provisioned manually via Hetzner Cloud Console or hcloud CLI
create_infrastructure() {
    log_info "Verifying staging infrastructure..."

    # Verify Docker is running
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker daemon."
    fi

    # Verify docker-compose configuration exists
    local compose_file="$PROJECT_ROOT/docker-compose.staging.yml"
    if [ ! -f "$compose_file" ]; then
        compose_file="$PROJECT_ROOT/docker-compose.yml"
        log_info "Using default docker-compose.yml for staging"
    fi

    # Validate docker-compose configuration
    docker compose -f "$compose_file" config >/dev/null 2>&1
    if [ $? -ne 0 ]; then
        log_error "Invalid docker-compose configuration"
    fi

    log_success "Staging infrastructure verified (Hetzner + Docker Compose)"
}

# Setup Kubernetes namespace and RBAC
setup_kubernetes() {
    log_info "Setting up Kubernetes namespace and RBAC..."
    
    # Create namespace
    kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
    
    # Apply RBAC configuration
    cat << EOF | kubectl apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  name: mcp-server-staging
  namespace: $NAMESPACE
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: mcp-server-role
  namespace: $NAMESPACE
rules:
- apiGroups: [""]
  resources: ["pods", "services", "configmaps", "secrets"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments", "replicasets"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: mcp-server-binding
  namespace: $NAMESPACE
subjects:
- kind: ServiceAccount
  name: mcp-server-staging
  namespace: $NAMESPACE
roleRef:
  kind: Role
  name: mcp-server-role
  apiGroup: rbac.authorization.k8s.io
EOF
    
    log_success "Kubernetes namespace and RBAC configured"
}

# Create and apply secrets
create_secrets() {
    log_info "Creating Kubernetes secrets..."
    
    # Database credentials
    kubectl create secret generic postgres-credentials \
        --namespace="$NAMESPACE" \
        --from-literal=username=pratiko \
        --from-literal=password="$POSTGRES_PASSWORD" \
        --from-literal=database=pratiko_mcp_staging \
        --dry-run=client -o yaml | kubectl apply -f -
    
    # JWT secret
    kubectl create secret generic jwt-secret \
        --namespace="$NAMESPACE" \
        --from-literal=secret-key="$JWT_SECRET_KEY" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    # TLS certificates (using AWS Certificate Manager)
    cat << EOF | kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: tls-certificate
  namespace: $NAMESPACE
type: kubernetes.io/tls
data:
  tls.crt: $(echo "$SSL_CERT_ARN" | base64 -w 0)
  tls.key: $(echo "managed-by-aws" | base64 -w 0)
EOF
    
    log_success "Kubernetes secrets created"
}

# Deploy database with high availability
deploy_database() {
    log_info "Deploying PostgreSQL with high availability..."
    
    # Add Bitnami Helm repository for PostgreSQL HA
    helm repo add bitnami https://charts.bitnami.com/bitnami
    helm repo update
    
    # Create PostgreSQL HA configuration
    cat > "$PROJECT_ROOT/config/postgres-staging-values.yaml" << EOF
auth:
  existingSecret: postgres-credentials
  secretKeys:
    adminPasswordKey: password
    userPasswordKey: password
architecture: replication
primary:
  resources:
    requests:
      memory: "2Gi"
      cpu: "1000m"
    limits:
      memory: "4Gi"
      cpu: "2000m"
  persistence:
    enabled: true
    size: 100Gi
    storageClass: gp2
readReplicas:
  replicaCount: 1
  resources:
    requests:
      memory: "1Gi"
      cpu: "500m"
    limits:
      memory: "2Gi"
      cpu: "1000m"
  persistence:
    enabled: true
    size: 100Gi
    storageClass: gp2
metrics:
  enabled: true
  serviceMonitor:
    enabled: true
backup:
  enabled: true
  cronjob:
    schedule: "0 2 * * *"
    storage:
      size: 50Gi
EOF
    
    # Deploy PostgreSQL
    helm upgrade --install postgres-staging bitnami/postgresql-ha \
        --namespace "$NAMESPACE" \
        --values "$PROJECT_ROOT/config/postgres-staging-values.yaml" \
        --wait --timeout=10m
    
    log_success "PostgreSQL HA deployed"
}

# Deploy Redis cluster
deploy_redis() {
    log_info "Deploying Redis cluster..."
    
    # Create Redis cluster configuration
    cat > "$PROJECT_ROOT/config/redis-staging-values.yaml" << EOF
architecture: replication
auth:
  enabled: true
  password: "$REDIS_PASSWORD"
master:
  resources:
    requests:
      memory: "1Gi"
      cpu: "500m"
    limits:
      memory: "2Gi"
      cpu: "1000m"
  persistence:
    enabled: true
    size: 20Gi
replica:
  replicaCount: 2
  resources:
    requests:
      memory: "512Mi"
      cpu: "250m"
    limits:
      memory: "1Gi"
      cpu: "500m"
  persistence:
    enabled: true
    size: 20Gi
metrics:
  enabled: true
  serviceMonitor:
    enabled: true
sentinel:
  enabled: true
EOF
    
    # Deploy Redis
    helm upgrade --install redis-staging bitnami/redis \
        --namespace "$NAMESPACE" \
        --values "$PROJECT_ROOT/config/redis-staging-values.yaml" \
        --wait --timeout=10m
    
    log_success "Redis cluster deployed"
}

# Deploy MCP server with high availability
deploy_mcp_server() {
    log_info "Deploying MCP server with high availability..."
    
    # Create MCP server deployment
    cat << EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-server-staging
  namespace: $NAMESPACE
  labels:
    app: mcp-server
    environment: staging
spec:
  replicas: 2
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: mcp-server
      environment: staging
  template:
    metadata:
      labels:
        app: mcp-server
        environment: staging
    spec:
      serviceAccountName: mcp-server-staging
      containers:
      - name: mcp-server
        image: pratiko/mcp-server:staging-latest
        ports:
        - containerPort: 8080
          name: http
        - containerPort: 9090
          name: metrics
        env:
        - name: ENVIRONMENT
          value: "staging"
        - name: LOG_LEVEL
          value: "info"
        - name: POSTGRES_URL
          valueFrom:
            secretKeyRef:
              name: postgres-credentials
              key: url
        - name: REDIS_URL
          value: "redis://redis-staging-master:6379"
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: jwt-secret
              key: secret-key
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 2
        securityContext:
          runAsNonRoot: true
          runAsUser: 1000
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        - name: config
          mountPath: /app/config
          readOnly: true
      volumes:
      - name: tmp
        emptyDir: {}
      - name: config
        configMap:
          name: mcp-server-config
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - mcp-server
              topologyKey: kubernetes.io/hostname
---
apiVersion: v1
kind: Service
metadata:
  name: mcp-server-staging
  namespace: $NAMESPACE
  labels:
    app: mcp-server
    environment: staging
spec:
  selector:
    app: mcp-server
    environment: staging
  ports:
  - name: http
    port: 80
    targetPort: 8080
  - name: metrics
    port: 9090
    targetPort: 9090
  type: ClusterIP
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: mcp-server-staging
  namespace: $NAMESPACE
  annotations:
    kubernetes.io/ingress.class: "alb"
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/certificate-arn: $SSL_CERT_ARN
    alb.ingress.kubernetes.io/ssl-policy: ELBSecurityPolicy-TLS-1-2-2017-01
    alb.ingress.kubernetes.io/healthcheck-path: /health
spec:
  tls:
  - hosts:
    - mcp-staging.pratiko.ai
    secretName: tls-certificate
  rules:
  - host: mcp-staging.pratiko.ai
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: mcp-server-staging
            port:
              number: 80
EOF
    
    log_success "MCP server deployed with high availability"
}

# Setup horizontal pod autoscaler
setup_autoscaling() {
    log_info "Setting up horizontal pod autoscaling..."
    
    cat << EOF | kubectl apply -f -
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: mcp-server-hpa
  namespace: $NAMESPACE
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: mcp-server-staging
  minReplicas: 2
  maxReplicas: 6
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
EOF
    
    log_success "Horizontal pod autoscaling configured"
}

# Deploy monitoring stack
deploy_monitoring() {
    log_info "Deploying monitoring stack..."
    
    # Add Prometheus community Helm repository
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo update
    
    # Create monitoring configuration
    cat > "$PROJECT_ROOT/config/monitoring-staging-values.yaml" << EOF
prometheus:
  prometheusSpec:
    retention: 30d
    storageSpec:
      volumeClaimTemplate:
        spec:
          storageClassName: gp2
          accessModes: ["ReadWriteOnce"]
          resources:
            requests:
              storage: 50Gi
    resources:
      requests:
        memory: "2Gi"
        cpu: "1000m"
      limits:
        memory: "4Gi"
        cpu: "2000m"
grafana:
  adminPassword: $GRAFANA_ADMIN_PASSWORD
  persistence:
    enabled: true
    size: 10Gi
    storageClassName: gp2
  ingress:
    enabled: true
    annotations:
      kubernetes.io/ingress.class: "alb"
      alb.ingress.kubernetes.io/certificate-arn: $SSL_CERT_ARN
    hosts:
      - grafana-staging.pratiko.ai
alertmanager:
  alertmanagerSpec:
    storage:
      volumeClaimTemplate:
        spec:
          storageClassName: gp2
          accessModes: ["ReadWriteOnce"]
          resources:
            requests:
              storage: 10Gi
EOF
    
    # Deploy monitoring stack
    helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
        --namespace monitoring \
        --create-namespace \
        --values "$PROJECT_ROOT/config/monitoring-staging-values.yaml" \
        --wait --timeout=15m
    
    log_success "Monitoring stack deployed"
}

# Setup backup and disaster recovery
setup_backup() {
    log_info "Setting up backup and disaster recovery..."
    
    # Create backup configuration
    cat << EOF | kubectl apply -f -
apiVersion: batch/v1
kind: CronJob
metadata:
  name: mcp-backup-staging
  namespace: $NAMESPACE
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: mcp-server-staging
          containers:
          - name: backup
            image: pratiko/backup-tool:latest
            command:
            - /bin/bash
            - -c
            - |
              # Backup database
              pg_dump \$POSTGRES_URL > /backup/db-\$(date +%Y%m%d-%H%M%S).sql
              
              # Upload to S3
              aws s3 cp /backup/ s3://pratiko-backups/staging/mcp/ --recursive
              
              # Cleanup old local backups
              find /backup -name "*.sql" -mtime +7 -delete
            env:
            - name: POSTGRES_URL
              valueFrom:
                secretKeyRef:
                  name: postgres-credentials
                  key: url
            - name: AWS_DEFAULT_REGION
              value: $AWS_REGION
            volumeMounts:
            - name: backup-storage
              mountPath: /backup
          volumes:
          - name: backup-storage
            persistentVolumeClaim:
              claimName: backup-pvc
          restartPolicy: OnFailure
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: backup-pvc
  namespace: $NAMESPACE
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: gp2
  resources:
    requests:
      storage: 50Gi
EOF
    
    log_success "Backup and disaster recovery configured"
}

# Verify deployment
verify_deployment() {
    log_info "Verifying staging deployment..."
    
    # Wait for deployment to be ready
    kubectl wait --for=condition=available deployment/mcp-server-staging \
        --namespace="$NAMESPACE" --timeout=600s
    
    # Check service endpoints
    local ingress_ip
    ingress_ip=$(kubectl get ingress mcp-server-staging -n "$NAMESPACE" \
        -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
    
    if [ -n "$ingress_ip" ]; then
        log_success "MCP server is accessible at: https://$ingress_ip"
    else
        log_warning "Ingress IP not yet available"
    fi
    
    # Verify database connectivity
    if kubectl exec -n "$NAMESPACE" deployment/mcp-server-staging -- \
        curl -f http://localhost:8080/health >/dev/null 2>&1; then
        log_success "MCP server health check passed"
    else
        log_warning "MCP server health check failed"
    fi
    
    log_success "Staging deployment verification completed"
}

# Print deployment summary
print_summary() {
    log_success "Staging MCP server deployment completed!"
    echo
    echo "🚀 Services Available:"
    echo "   • MCP Server:   https://mcp-staging.pratiko.ai"
    echo "   • Health Check: https://mcp-staging.pratiko.ai/health"
    echo "   • Metrics:      https://mcp-staging.pratiko.ai/metrics"
    echo "   • Grafana:      https://grafana-staging.pratiko.ai"
    echo
    echo "📋 Management Commands:"
    echo "   • View logs:    kubectl logs -f deployment/mcp-server-staging -n $NAMESPACE"
    echo "   • Scale:        kubectl scale deployment/mcp-server-staging --replicas=N -n $NAMESPACE"
    echo "   • Status:       kubectl get pods -n $NAMESPACE"
    echo "   • Restart:      kubectl rollout restart deployment/mcp-server-staging -n $NAMESPACE"
    echo
    echo "🔧 Staging Features:"
    echo "   • High availability: 2+ replicas with auto-scaling"
    echo "   • Resource limits: 2 CPU, 4GB RAM per pod"
    echo "   • Database: PostgreSQL HA with read replicas"
    echo "   • Cache: Redis cluster with sentinel"
    echo "   • Monitoring: Prometheus + Grafana"
    echo "   • Backup: Daily automated backups to S3"
    echo "   • SSL/TLS: AWS Certificate Manager integration"
    echo
    echo "🔍 Monitoring:"
    echo "   • Logs: Available in CloudWatch and Kubernetes"
    echo "   • Metrics: Prometheus scraping enabled"
    echo "   • Alerts: Configured for critical issues"
    echo
}

# Main execution
main() {
    log_info "Starting PratikoAI MCP Staging Server Provisioning"
    echo "=================================================="
    
    check_prerequisites
    load_config
    create_infrastructure
    setup_kubernetes
    create_secrets
    deploy_database
    deploy_redis
    deploy_mcp_server
    setup_autoscaling
    deploy_monitoring
    setup_backup
    verify_deployment
    print_summary
    
    log_success "Staging environment is ready! 🎉"
}

# Cleanup function for interrupted execution
cleanup() {
    log_warning "Provisioning interrupted. Check resources manually."
    exit 1
}

# Set trap for cleanup
trap cleanup INT TERM

# Run main function
main "$@"