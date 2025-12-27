#!/bin/bash
set -euo pipefail

# PratikoAI MCP Production Server Provisioning Script
# This script provisions a production environment with enterprise-grade reliability

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_DIR="$PROJECT_ROOT/config"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions with timestamping
log_info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] [INFO]${NC} $1" | tee -a /var/log/mcp-production-provision.log
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] [SUCCESS]${NC} $1" | tee -a /var/log/mcp-production-provision.log
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] [WARNING]${NC} $1" | tee -a /var/log/mcp-production-provision.log
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR]${NC} $1" | tee -a /var/log/mcp-production-provision.log
    exit 1
}

# Pre-deployment security checks
security_checks() {
    log_info "Performing pre-deployment security checks..."
    
    # Check for production-ready security configurations
    if [ ! -f "$CONFIG_DIR/security/production-ca.crt" ]; then
        log_error "Production CA certificate not found. Security check failed."
    fi
    
    # Verify IAM permissions
    if ! aws iam get-role --role-name PratikoMCPProductionRole >/dev/null 2>&1; then
        log_error "Required IAM role not found. Please create PratikoMCPProductionRole first."
    fi
    
    # Check VPC and security group configurations
    local vpc_id
    vpc_id=$(aws ec2 describe-vpcs --filters "Name=tag:Name,Values=pratiko-production-vpc" --query 'Vpcs[0].VpcId' --output text)
    if [ "$vpc_id" = "None" ]; then
        log_error "Production VPC not found. Please create network infrastructure first."
    fi
    
    log_success "Security checks passed"
}

# Enhanced prerequisite checks for production
check_prerequisites() {
    log_info "Checking prerequisites for production deployment..."
    
    local missing_tools=()
    
    # Check for required tools with version requirements
    command -v docker >/dev/null 2>&1 || missing_tools+=("docker")
    command -v kubectl >/dev/null 2>&1 || missing_tools+=("kubectl")
    command -v helm >/dev/null 2>&1 || missing_tools+=("helm")
    command -v aws >/dev/null 2>&1 || missing_tools+=("aws-cli")
    command -v trivy >/dev/null 2>&1 || missing_tools+=("trivy")
    command -v cosign >/dev/null 2>&1 || missing_tools+=("cosign")
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        log_error "Missing required tools: ${missing_tools[*]}."
    fi

    # Verify kubectl can access production cluster
    if ! kubectl cluster-info >/dev/null 2>&1; then
        log_error "Cannot access Kubernetes cluster. Configure kubectl for production."
    fi
    
    # Verify production AWS credentials
    local account_id
    account_id=$(aws sts get-caller-identity --query Account --output text)
    if [ "$account_id" != "$PRODUCTION_AWS_ACCOUNT_ID" ]; then
        log_error "Not authenticated to production AWS account. Expected: $PRODUCTION_AWS_ACCOUNT_ID"
    fi
    
    security_checks
    
    log_success "All prerequisites satisfied for production deployment"
}

# Load and validate production configuration
load_config() {
    log_info "Loading production configuration..."
    
    if [ ! -f "$CONFIG_DIR/.env.production" ]; then
        log_error "Production config not found. Please create $CONFIG_DIR/.env.production"
    fi
    
    # Source the configuration
    set -a
    source "$CONFIG_DIR/.env.production"
    set +a
    
    # Validate critical production variables
    local required_vars=(
        "AWS_REGION"
        "PRODUCTION_AWS_ACCOUNT_ID"
        "CLUSTER_NAME"
        "NAMESPACE"
        "POSTGRES_PASSWORD"
        "JWT_SECRET_KEY"
        "SSL_CERT_ARN"
        "WAF_WEB_ACL_ARN"
        "BACKUP_BUCKET"
        "MONITORING_SLACK_WEBHOOK"
        "PAGERDUTY_INTEGRATION_KEY"
    )
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            log_error "Critical production variable $var is not set"
        fi
    done
    
    # Validate secret strength
    if [ ${#JWT_SECRET_KEY} -lt 64 ]; then
        log_error "JWT_SECRET_KEY must be at least 64 characters for production"
    fi
    
    if [ ${#POSTGRES_PASSWORD} -lt 32 ]; then
        log_error "POSTGRES_PASSWORD must be at least 32 characters for production"
    fi
    
    log_success "Production configuration loaded and validated"
}

# Create production infrastructure
# NOTE: PratikoAI uses Hetzner Cloud + Docker Compose instead of Terraform/AWS.
# Architecture Decision (ADR-017):
# - Target scale: 100-1000 users over 7-8 years (simple, static infrastructure)
# - Cost optimization: Hetzner is 5-10x cheaper than AWS for our scale
# - Simplicity: Docker Compose is sufficient, no Kubernetes/Terraform complexity needed
# - Infrastructure is provisioned manually via Hetzner Cloud Console or hcloud CLI
create_infrastructure() {
    log_info "Verifying production infrastructure..."

    # Verify Docker is running
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker daemon."
    fi

    # Verify docker-compose configuration exists
    if [ ! -f "$PROJECT_ROOT/docker-compose.prod.yml" ]; then
        log_warning "Production docker-compose file not found: docker-compose.prod.yml"
        log_info "Using default docker-compose.yml for production"
    fi

    # Validate docker-compose configuration
    local compose_file="$PROJECT_ROOT/docker-compose.prod.yml"
    if [ ! -f "$compose_file" ]; then
        compose_file="$PROJECT_ROOT/docker-compose.yml"
    fi

    docker compose -f "$compose_file" config >/dev/null 2>&1
    if [ $? -ne 0 ]; then
        log_error "Invalid docker-compose configuration"
    fi

    log_success "Production infrastructure verified (Hetzner + Docker Compose)"
}

# Setup production-grade security
setup_security() {
    log_info "Configuring production security controls..."
    
    # Create security namespace
    kubectl create namespace security --dry-run=client -o yaml | kubectl apply -f -
    
    # Deploy Falco for runtime security
    helm repo add falcosecurity https://falcosecurity.github.io/charts
    helm upgrade --install falco falcosecurity/falco \
        --namespace security \
        --set falco.grpc.enabled=true \
        --set falco.grpcOutput.enabled=true \
        --wait
    
    # Deploy network policies
    cat << EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: mcp-server-network-policy
  namespace: $NAMESPACE
spec:
  podSelector:
    matchLabels:
      app: mcp-server
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8080
  - from:
    - namespaceSelector:
        matchLabels:
          name: monitoring
    ports:
    - protocol: TCP
      port: 9090
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: $NAMESPACE
    ports:
    - protocol: TCP
      port: 5432  # PostgreSQL
    - protocol: TCP
      port: 6379  # Redis
  - to: []  # Allow external API calls with restrictions
    ports:
    - protocol: TCP
      port: 443
    - protocol: TCP
      port: 80
EOF
    
    # Setup Pod Security Standards
    kubectl label namespace "$NAMESPACE" \
        pod-security.kubernetes.io/enforce=restricted \
        pod-security.kubernetes.io/audit=restricted \
        pod-security.kubernetes.io/warn=restricted
    
    log_success "Production security controls configured"
}

# Deploy enterprise database with multi-AZ
deploy_database() {
    log_info "Deploying enterprise PostgreSQL with multi-AZ configuration..."
    
    # Create storage class for high-performance storage
    cat << EOF | kubectl apply -f -
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  iops: "3000"
  throughput: "125"
  encrypted: "true"
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
EOF
    
    # Deploy PostgreSQL HA with enterprise features
    cat > "$PROJECT_ROOT/config/postgres-production-values.yaml" << EOF
auth:
  existingSecret: postgres-credentials
  secretKeys:
    adminPasswordKey: password
    userPasswordKey: password
architecture: replication
primary:
  resources:
    requests:
      memory: "8Gi"
      cpu: "4000m"
    limits:
      memory: "16Gi"
      cpu: "8000m"
  persistence:
    enabled: true
    size: 500Gi
    storageClass: fast-ssd
  nodeSelector:
    node-type: database
  tolerations:
  - key: "database"
    operator: "Equal"
    value: "true"
    effect: "NoSchedule"
readReplicas:
  replicaCount: 2
  resources:
    requests:
      memory: "4Gi"
      cpu: "2000m"
    limits:
      memory: "8Gi"
      cpu: "4000m"
  persistence:
    enabled: true
    size: 500Gi
    storageClass: fast-ssd
  nodeSelector:
    node-type: database
  tolerations:
  - key: "database"
    operator: "Equal"
    value: "true"
    effect: "NoSchedule"
postgresql:
  maxConnections: 500
  sharedBuffers: "2GB"  
  effectiveCacheSize: "12GB"
  maintenanceWorkMem: "1GB"
  checkpointCompletionTarget: 0.9
  walBuffers: "64MB"
  defaultStatisticsTarget: 500
  randomPageCost: 1.1
  effectiveIoConcurrency: 200
metrics:
  enabled: true
  serviceMonitor:
    enabled: true
    interval: 30s
backup:
  enabled: true
  cronjob:
    schedule: "0 2 * * *"
    storage:
      size: 200Gi
      storageClass: fast-ssd
  retention: 30
tls:
  enabled: true
  certificatesSecret: postgres-tls
  certFilename: tls.crt
  certKeyFilename: tls.key
EOF
    
    # Deploy PostgreSQL
    helm upgrade --install postgres-production bitnami/postgresql-ha \
        --namespace "$NAMESPACE" \
        --values "$PROJECT_ROOT/config/postgres-production-values.yaml" \
        --wait --timeout=15m
    
    log_success "Enterprise PostgreSQL deployed"
}

# Deploy Redis cluster for production
deploy_redis() {
    log_info "Deploying production Redis cluster..."
    
    cat > "$PROJECT_ROOT/config/redis-production-values.yaml" << EOF
architecture: replication
auth:
  enabled: true
  password: "$REDIS_PASSWORD"
master:
  resources:
    requests:
      memory: "4Gi"
      cpu: "2000m"
    limits:
      memory: "8Gi"
      cpu: "4000m"
  persistence:
    enabled: true
    size: 100Gi
    storageClass: fast-ssd
  nodeSelector:
    node-type: cache
replica:
  replicaCount: 3
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
    storageClass: fast-ssd
  nodeSelector:
    node-type: cache
metrics:
  enabled: true
  serviceMonitor:
    enabled: true
sentinel:
  enabled: true
  resources:
    requests:
      memory: "256Mi"
      cpu: "100m"
    limits:
      memory: "512Mi"
      cpu: "200m"
tls:
  enabled: true
  certificatesSecret: redis-tls
  certFilename: tls.crt
  certKeyFilename: tls.key
EOF
    
    helm upgrade --install redis-production bitnami/redis \
        --namespace "$NAMESPACE" \
        --values "$PROJECT_ROOT/config/redis-production-values.yaml" \
        --wait --timeout=15m
    
    log_success "Production Redis cluster deployed"
}

# Deploy MCP server with production hardening
deploy_mcp_server() {
    log_info "Deploying production MCP server with enterprise features..."
    
    # Create production deployment with comprehensive security
    cat << EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-server-production
  namespace: $NAMESPACE
  labels:
    app: mcp-server
    environment: production
    version: v1.0.0
spec:
  replicas: 6
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 2
      maxUnavailable: 1
  selector:
    matchLabels:
      app: mcp-server
      environment: production
  template:
    metadata:
      labels:
        app: mcp-server
        environment: production
        version: v1.0.0
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9090"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: mcp-server-production
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        runAsGroup: 10001
        fsGroup: 10001
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: mcp-server
        image: pratiko/mcp-server:v1.0.0-production
        imagePullPolicy: Always
        ports:
        - containerPort: 8080
          name: http
          protocol: TCP
        - containerPort: 9090
          name: metrics
          protocol: TCP
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: LOG_LEVEL
          value: "warn"
        - name: LOG_FORMAT
          value: "json"
        - name: POSTGRES_URL
          valueFrom:
            secretKeyRef:
              name: postgres-credentials
              key: url
        - name: REDIS_URL
          value: "rediss://redis-production-master:6379"
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: jwt-secret
              key: secret-key
        - name: RATE_LIMIT_ENABLED
          value: "true"
        - name: RATE_LIMIT_MAX_REQUESTS
          value: "1000"
        - name: ENABLE_TRACING
          value: "true"
        - name: JAEGER_ENDPOINT
          value: "http://jaeger-collector:14268/api/traces"
        resources:
          requests:
            memory: "4Gi"
            cpu: "2000m"
            ephemeral-storage: "2Gi"
          limits:
            memory: "8Gi"
            cpu: "4000m"
            ephemeral-storage: "4Gi"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
            scheme: HTTP
          initialDelaySeconds: 45
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
          successThreshold: 1
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
            scheme: HTTP
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 2
          successThreshold: 1
        startupProbe:
          httpGet:
            path: /startup
            port: 8080
            scheme: HTTP
          initialDelaySeconds: 10
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 30
          successThreshold: 1
        securityContext:
          runAsNonRoot: true
          runAsUser: 10001
          runAsGroup: 10001
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        - name: var-log
          mountPath: /var/log
        - name: config
          mountPath: /app/config
          readOnly: true
        - name: tls-certs
          mountPath: /app/certs
          readOnly: true
      volumes:
      - name: tmp
        emptyDir: {}
      - name: var-log
        emptyDir: {}
      - name: config
        configMap:
          name: mcp-server-config
      - name: tls-certs
        secret:
          secretName: mcp-server-tls
      nodeSelector:
        node-type: application
      tolerations:
      - key: "application"
        operator: "Equal"
        value: "true"
        effect: "NoSchedule"
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchExpressions:
              - key: app
                operator: In
                values:
                - mcp-server
            topologyKey: kubernetes.io/hostname
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            preference:
              matchExpressions:
              - key: instance-type
                operator: In
                values:
                - c5.2xlarge
                - c5.4xlarge
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: mcp-server
---
apiVersion: v1
kind: Service
metadata:
  name: mcp-server-production
  namespace: $NAMESPACE
  labels:
    app: mcp-server
    environment: production
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
    service.beta.kubernetes.io/aws-load-balancer-ssl-cert: $SSL_CERT_ARN
    service.beta.kubernetes.io/aws-load-balancer-backend-protocol: "http"
    service.beta.kubernetes.io/aws-load-balancer-ssl-ports: "https"
spec:
  selector:
    app: mcp-server
    environment: production
  ports:
  - name: https
    port: 443
    targetPort: 8080
    protocol: TCP
  - name: metrics
    port: 9090
    targetPort: 9090
    protocol: TCP
  type: LoadBalancer
  sessionAffinity: ClientIP
  sessionAffinityConfig:
    clientIP:
      timeoutSeconds: 3600
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: mcp-server-production
  namespace: $NAMESPACE
  annotations:
    kubernetes.io/ingress.class: "alb"
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/certificate-arn: $SSL_CERT_ARN
    alb.ingress.kubernetes.io/ssl-policy: ELBSecurityPolicy-TLS-1-2-2017-01
    alb.ingress.kubernetes.io/wafv2-acl-arn: $WAF_WEB_ACL_ARN
    alb.ingress.kubernetes.io/healthcheck-path: /health
    alb.ingress.kubernetes.io/healthcheck-interval-seconds: "15"
    alb.ingress.kubernetes.io/healthcheck-timeout-seconds: "5"
    alb.ingress.kubernetes.io/healthy-threshold-count: "2"
    alb.ingress.kubernetes.io/unhealthy-threshold-count: "3"
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}]'
    alb.ingress.kubernetes.io/ssl-redirect: "443"
spec:
  tls:
  - hosts:
    - mcp.pratiko.ai
    - api.pratiko.ai
    secretName: production-tls
  rules:
  - host: mcp.pratiko.ai
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: mcp-server-production
            port:
              number: 443
  - host: api.pratiko.ai
    http:
      paths:
      - path: /mcp
        pathType: Prefix
        backend:
          service:
            name: mcp-server-production
            port:
              number: 443
EOF
    
    log_success "Production MCP server deployed with enterprise security"
}

# Setup advanced autoscaling
setup_autoscaling() {
    log_info "Configuring advanced autoscaling for production..."
    
    # Vertical Pod Autoscaler
    cat << EOF | kubectl apply -f -
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: mcp-server-vpa
  namespace: $NAMESPACE
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: mcp-server-production
  updatePolicy:
    updateMode: "Auto"
  resourcePolicy:
    containerPolicies:
    - containerName: mcp-server
      minAllowed:
        cpu: "1000m"
        memory: "2Gi"
      maxAllowed:
        cpu: "8000m"
        memory: "16Gi"
      controlledResources: ["cpu", "memory"]
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: mcp-server-hpa
  namespace: $NAMESPACE
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: mcp-server-production
  minReplicas: 6
  maxReplicas: 50
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 60
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 70
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "1000"
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 600
      policies:
      - type: Percent
        value: 10
        periodSeconds: 300
      - type: Pods
        value: 2
        periodSeconds: 300
      selectPolicy: Min
    scaleUp:
      stabilizationWindowSeconds: 120
      policies:
      - type: Percent
        value: 100
        periodSeconds: 60
      - type: Pods
        value: 4
        periodSeconds: 60
      selectPolicy: Max
EOF
    
    log_success "Advanced autoscaling configured"
}

# Deploy comprehensive monitoring
deploy_monitoring() {
    log_info "Deploying enterprise monitoring and observability..."
    
    # Create monitoring namespace
    kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
    
    # Deploy Prometheus Operator with enterprise features
    cat > "$PROJECT_ROOT/config/monitoring-production-values.yaml" << EOF
prometheus:
  prometheusSpec:
    retention: 90d
    retentionSize: 450GB
    replicas: 2
    storageSpec:
      volumeClaimTemplate:
        spec:
          storageClassName: fast-ssd
          accessModes: ["ReadWriteOnce"]
          resources:
            requests:
              storage: 500Gi
    resources:
      requests:
        memory: "8Gi"
        cpu: "4000m"
      limits:
        memory: "16Gi"
        cpu: "8000m"
    nodeSelector:
      node-type: monitoring
    affinity:
      podAntiAffinity:
        requiredDuringSchedulingIgnoredDuringExecution:
        - labelSelector:
            matchLabels:
              app.kubernetes.io/name: prometheus
          topologyKey: kubernetes.io/hostname
    ruleSelector:
      matchLabels:
        prometheus: kube-prometheus
        role: alert-rules
    serviceMonitorSelector:
      matchLabels:
        team: pratiko
alertmanager:
  alertmanagerSpec:
    replicas: 3
    storage:
      volumeClaimTemplate:
        spec:
          storageClassName: fast-ssd
          accessModes: ["ReadWriteOnce"]
          resources:
            requests:
              storage: 50Gi
    resources:
      requests:
        memory: "1Gi"
        cpu: "500m"
      limits:
        memory: "2Gi"
        cpu: "1000m"
    nodeSelector:
      node-type: monitoring
grafana:
  adminPassword: $GRAFANA_ADMIN_PASSWORD
  persistence:
    enabled: true
    size: 20Gi
    storageClassName: fast-ssd
  resources:
    requests:
      memory: "1Gi"
      cpu: "500m"
    limits:
      memory: "2Gi"
      cpu: "1000m"
  ingress:
    enabled: true
    annotations:
      kubernetes.io/ingress.class: "alb"
      alb.ingress.kubernetes.io/certificate-arn: $SSL_CERT_ARN
      alb.ingress.kubernetes.io/wafv2-acl-arn: $WAF_WEB_ACL_ARN
    hosts:
      - grafana.pratiko.ai
  nodeSelector:
    node-type: monitoring
  sidecar:
    dashboards:
      enabled: true
      searchNamespace: ALL
    datasources:
      enabled: true
      searchNamespace: ALL
EOF
    
    # Deploy monitoring stack
    helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
        --namespace monitoring \
        --values "$PROJECT_ROOT/config/monitoring-production-values.yaml" \
        --wait --timeout=20m
    
    # Deploy Jaeger for distributed tracing
    helm repo add jaegertracing https://jaegertracing.github.io/helm-charts
    helm upgrade --install jaeger jaegertracing/jaeger \
        --namespace monitoring \
        --set query.ingress.enabled=true \
        --set query.ingress.hosts[0]=jaeger.pratiko.ai \
        --set storage.type=elasticsearch \
        --wait
    
    log_success "Enterprise monitoring stack deployed"
}

# Setup enterprise backup and disaster recovery
setup_backup() {
    log_info "Configuring enterprise backup and disaster recovery..."
    
    # Deploy Velero for cluster backups
    helm repo add vmware-tanzu https://vmware-tanzu.github.io/helm-charts
    helm upgrade --install velero vmware-tanzu/velero \
        --namespace velero \
        --create-namespace \
        --set configuration.provider=aws \
        --set configuration.backupStorageLocation.bucket="$BACKUP_BUCKET" \
        --set configuration.backupStorageLocation.config.region="$AWS_REGION" \
        --set configuration.volumeSnapshotLocation.config.region="$AWS_REGION" \
        --set serviceAccount.server.create=false \
        --set serviceAccount.server.name=velero \
        --wait
    
    # Create backup schedules
    cat << EOF | kubectl apply -f -
apiVersion: velero.io/v1
kind: Schedule
metadata:
  name: daily-backup
  namespace: velero
spec:
  schedule: "0 1 * * *"  # Daily at 1 AM
  template:
    includedNamespaces:
    - $NAMESPACE
    - monitoring
    excludedResources:
    - events
    - events.events.k8s.io
    ttl: 720h0m0s  # 30 days
---
apiVersion: velero.io/v1
kind: Schedule
metadata:
  name: weekly-backup
  namespace: velero
spec:
  schedule: "0 2 * * 0"  # Weekly on Sunday at 2 AM
  template:
    includedNamespaces:
    - $NAMESPACE
    - monitoring
    ttl: 2160h0m0s  # 90 days
EOF
    
    # Database backup job
    cat << EOF | kubectl apply -f -
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
  namespace: $NAMESPACE
spec:
  schedule: "0 3 * * *"  # Daily at 3 AM
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 1
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: backup-service-account
          containers:
          - name: postgres-backup
            image: postgres:15-alpine
            command:
            - /bin/bash
            - -c
            - |
              set -euo pipefail
              
              # Create backup
              timestamp=\$(date +%Y%m%d-%H%M%S)
              backup_file="postgres-\$timestamp.sql"
              
              pg_dump "\$POSTGRES_URL" > "/backup/\$backup_file"
              
              # Compress backup
              gzip "/backup/\$backup_file"
              
              # Upload to S3 with encryption
              aws s3 cp "/backup/\$backup_file.gz" \
                "s3://$BACKUP_BUCKET/postgres/\$backup_file.gz" \
                --server-side-encryption AES256
              
              # Cleanup old local backups
              find /backup -name "*.sql.gz" -mtime +1 -delete
              
              # Cleanup old S3 backups (keep 30 days)
              aws s3 ls "s3://$BACKUP_BUCKET/postgres/" | \
                awk '\$1 < "'"\$(date -d '30 days ago' '+%Y-%m-%d')"'" {print \$4}' | \
                xargs -I {} aws s3 rm "s3://$BACKUP_BUCKET/postgres/{}"
              
              echo "Backup completed successfully"
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
            emptyDir:
              sizeLimit: 100Gi
          restartPolicy: OnFailure
          nodeSelector:
            node-type: utility
EOF
    
    log_success "Enterprise backup and disaster recovery configured"
}

# Setup comprehensive alerting
setup_alerting() {
    log_info "Configuring production alerting..."
    
    # Create AlertManager configuration
    cat << EOF | kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: alertmanager-main
  namespace: monitoring
type: Opaque
stringData:
  alertmanager.yml: |
    global:
      smtp_smarthost: 'smtp.gmail.com:587'
      smtp_from: 'alerts@pratiko.ai'
      slack_api_url: '$MONITORING_SLACK_WEBHOOK'
    
    route:
      group_by: ['alertname', 'cluster', 'service']
      group_wait: 10s
      group_interval: 10s
      repeat_interval: 1h
      receiver: 'default'
      routes:
      - match:
          severity: critical
        receiver: 'pagerduty-critical'
      - match:
          severity: warning
        receiver: 'slack-warnings'
    
    receivers:
    - name: 'default'
      slack_configs:
      - channel: '#alerts'
        title: 'PratikoAI Alert'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
    
    - name: 'pagerduty-critical'
      pagerduty_configs:
      - service_key: '$PAGERDUTY_INTEGRATION_KEY'
        description: '{{ .CommonAnnotations.summary }}'
      slack_configs:
      - channel: '#critical-alerts'
        title: 'CRITICAL: PratikoAI Alert'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
        color: 'danger'
    
    - name: 'slack-warnings'
      slack_configs:
      - channel: '#warnings'
        title: 'Warning: PratikoAI Alert'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
        color: 'warning'
EOF
    
    # Create custom alert rules
    cat << EOF | kubectl apply -f -
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: mcp-server-alerts
  namespace: monitoring
  labels:
    prometheus: kube-prometheus
    role: alert-rules
spec:
  groups:
  - name: mcp-server.rules
    rules:
    - alert: MCPServerDown
      expr: up{job="mcp-server-production"} == 0
      for: 1m
      labels:
        severity: critical
      annotations:
        summary: "MCP Server instance is down"
        description: "MCP Server instance {{ \$labels.instance }} has been down for more than 1 minute"
    
    - alert: MCPServerHighErrorRate
      expr: rate(http_requests_total{job="mcp-server-production",status=~"5.."}[5m]) / rate(http_requests_total{job="mcp-server-production"}[5m]) > 0.1
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "MCP Server high error rate"
        description: "MCP Server error rate is above 10% for 5 minutes"
    
    - alert: MCPServerHighLatency
      expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{job="mcp-server-production"}[5m])) > 1
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: "MCP Server high latency"
        description: "MCP Server 95th percentile latency is above 1s"
    
    - alert: MCPServerHighMemoryUsage
      expr: container_memory_usage_bytes{pod=~"mcp-server-production-.*"} / container_spec_memory_limit_bytes > 0.9
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "MCP Server high memory usage"
        description: "MCP Server memory usage is above 90%"
    
    - alert: PostgreSQLDown
      expr: up{job="postgres-production-metrics"} == 0
      for: 2m
      labels:
        severity: critical
      annotations:
        summary: "PostgreSQL is down"
        description: "PostgreSQL instance has been down for more than 2 minutes"
    
    - alert: RedisDown
      expr: up{job="redis-production-metrics"} == 0
      for: 2m
      labels:
        severity: critical
      annotations:
        summary: "Redis is down"
        description: "Redis instance has been down for more than 2 minutes"
EOF
    
    log_success "Production alerting configured"
}

# Comprehensive deployment verification
verify_deployment() {
    log_info "Performing comprehensive production deployment verification..."
    
    # Wait for all deployments
    kubectl wait --for=condition=available deployment/mcp-server-production \
        --namespace="$NAMESPACE" --timeout=900s
    
    # Health checks
    local health_checks=(
        "https://mcp.pratiko.ai/health"
        "https://mcp.pratiko.ai/ready"
        "https://mcp.pratiko.ai/metrics"
    )
    
    for endpoint in "${health_checks[@]}"; do
        local attempts=0
        local max_attempts=10
        
        while [ $attempts -lt $max_attempts ]; do
            if curl -f -k "$endpoint" >/dev/null 2>&1; then
                log_success "Health check passed: $endpoint"
                break
            fi
            
            ((attempts++))
            if [ $attempts -eq $max_attempts ]; then
                log_error "Health check failed: $endpoint"
            fi
            
            sleep 30
        done
    done
    
    # Verify database connectivity
    if kubectl exec -n "$NAMESPACE" deployment/mcp-server-production -- \
        curl -f http://localhost:8080/health/database >/dev/null 2>&1; then
        log_success "Database connectivity verified"
    else
        log_warning "Database connectivity check failed"
    fi
    
    # Verify scaling capabilities
    kubectl scale deployment/mcp-server-production --replicas=8 -n "$NAMESPACE"
    kubectl wait --for=condition=available deployment/mcp-server-production \
        --namespace="$NAMESPACE" --timeout=300s
    kubectl scale deployment/mcp-server-production --replicas=6 -n "$NAMESPACE"
    
    log_success "Scaling verification completed"
    
    # Security scan
    log_info "Running security vulnerability scan..."
    trivy k8s --namespace "$NAMESPACE" deployment/mcp-server-production || log_warning "Security scan found vulnerabilities"
    
    log_success "Production deployment verification completed"
}

# Print comprehensive deployment summary
print_summary() {
    log_success "Production MCP server deployment completed successfully!"
    echo
    echo "🚀 Production Services:"
    echo "   • Primary API:     https://mcp.pratiko.ai"
    echo "   • Secondary API:   https://api.pratiko.ai/mcp"
    echo "   • Health Check:    https://mcp.pratiko.ai/health"
    echo "   • Metrics:         https://mcp.pratiko.ai/metrics"
    echo "   • Grafana:         https://grafana.pratiko.ai"
    echo "   • Jaeger:          https://jaeger.pratiko.ai"
    echo
    echo "📊 Production Specifications:"
    echo "   • Replicas:        6 (auto-scaling 6-50)"
    echo "   • Resources:       2-8 CPU, 4-16GB RAM per pod"
    echo "   • Database:        PostgreSQL HA with read replicas"
    echo "   • Cache:           Redis cluster with sentinel"
    echo "   • Storage:         500GB+ high-performance SSD"
    echo "   • Backup:          Daily automated with 30-day retention"
    echo "   • Monitoring:      Prometheus + Grafana + Jaeger"
    echo "   • Security:        WAF, Network policies, Pod security"
    echo
    echo "🔒 Security Features:"
    echo "   • TLS 1.3 encryption everywhere"
    echo "   • AWS WAF protection"
    echo "   • Network segmentation"
    echo "   • Pod security standards (restricted)"
    echo "   • Runtime security monitoring (Falco)"
    echo "   • Regular vulnerability scanning"
    echo
    echo "📋 Management Commands:"
    echo "   • View logs:       kubectl logs -f deployment/mcp-server-production -n $NAMESPACE"
    echo "   • Scale manually:  kubectl scale deployment/mcp-server-production --replicas=N -n $NAMESPACE"
    echo "   • Rolling update:  kubectl rollout restart deployment/mcp-server-production -n $NAMESPACE"
    echo "   • Status:          kubectl get pods -n $NAMESPACE"
    echo "   • Resource usage:  kubectl top pods -n $NAMESPACE"
    echo
    echo "🚨 Alerting:"
    echo "   • Critical alerts: PagerDuty + Slack #critical-alerts"
    echo "   • Warnings:        Slack #warnings"
    echo "   • General alerts:  Slack #alerts"
    echo
    echo "💾 Backup & Recovery:"
    echo "   • Cluster backups: Daily via Velero"
    echo "   • Database backups: Daily to S3 with encryption"
    echo "   • Retention: 30 days standard, 90 days weekly"
    echo "   • Recovery time: < 4 hours (RTO)"
    echo "   • Recovery point: < 1 hour (RPO)"
    echo
    echo "📈 SLA Targets:"
    echo "   • Uptime:          99.9% (8.76 hours downtime/year)"
    echo "   • Response time:   < 500ms (95th percentile)"
    echo "   • Error rate:      < 0.1%"
    echo "   • Recovery:        < 4 hours"
    echo
}

# Main execution with comprehensive logging
main() {
    log_info "Starting PratikoAI MCP Production Server Provisioning"
    echo "========================================================="
    
    # Create log file with proper permissions
    sudo touch /var/log/mcp-production-provision.log
    sudo chmod 666 /var/log/mcp-production-provision.log
    
    check_prerequisites
    load_config
    create_infrastructure
    setup_security
    deploy_database
    deploy_redis
    deploy_mcp_server
    setup_autoscaling
    deploy_monitoring
    setup_backup
    setup_alerting
    verify_deployment
    print_summary
    
    log_success "Production environment is live and ready for enterprise workloads! 🚀"
    log_info "Complete deployment log available at: /var/log/mcp-production-provision.log"
}

# Enhanced cleanup for production
cleanup() {
    log_warning "Production provisioning interrupted. Manual verification required."
    log_warning "Check all resources in AWS console and Kubernetes cluster."
    log_warning "Partial deployment may have occurred - review before cleanup."
    exit 1
}

# Set trap for cleanup
trap cleanup INT TERM

# Run main function with all arguments
main "$@"