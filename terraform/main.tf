# =============================================================================
# PratikoAI Infrastructure - Main Configuration
# Comprehensive AWS infrastructure for coordinated backend and frontend deployment
# =============================================================================

terraform {
  required_version = ">= 1.5"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
  
  backend "s3" {
    # Configure remote state - replace with your actual bucket
    bucket         = "praktiko-terraform-state"
    key            = "infrastructure/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "praktiko-terraform-locks"
  }
}

# =============================================================================
# Provider Configuration
# =============================================================================

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "PratikoAI"
      Environment = var.environment
      ManagedBy   = "Terraform"
      CreatedAt   = timestamp()
    }
  }
}

# =============================================================================
# Local Values
# =============================================================================

locals {
  name_prefix = "praktiko-${var.environment}"
  
  # Common tags for all resources
  common_tags = {
    Project     = "PratikoAI"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
  
  # Database configuration
  db_name     = "praktiko_${var.environment}"
  db_username = "praktiko_admin"
  
  # Domain configuration
  domain_name = var.environment == "production" ? "praktiko.ai" : "${var.environment}.praktiko.ai"
  
  # Availability zones
  availability_zones = data.aws_availability_zones.available.names
}

# =============================================================================
# Data Sources
# =============================================================================

data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

# =============================================================================
# Networking Module
# =============================================================================

module "networking" {
  source = "./modules/networking"
  
  name_prefix        = local.name_prefix
  environment        = var.environment
  vpc_cidr           = var.vpc_cidr
  availability_zones = local.availability_zones
  
  # Public subnets for ALB and NAT gateways
  public_subnet_cidrs = [
    cidrsubnet(var.vpc_cidr, 8, 1),  # 10.0.1.0/24
    cidrsubnet(var.vpc_cidr, 8, 2),  # 10.0.2.0/24
    cidrsubnet(var.vpc_cidr, 8, 3),  # 10.0.3.0/24
  ]
  
  # Private subnets for ECS tasks and RDS
  private_subnet_cidrs = [
    cidrsubnet(var.vpc_cidr, 8, 11), # 10.0.11.0/24
    cidrsubnet(var.vpc_cidr, 8, 12), # 10.0.12.0/24
    cidrsubnet(var.vpc_cidr, 8, 13), # 10.0.13.0/24
  ]
  
  # Database subnets (isolated)
  database_subnet_cidrs = [
    cidrsubnet(var.vpc_cidr, 8, 21), # 10.0.21.0/24
    cidrsubnet(var.vpc_cidr, 8, 22), # 10.0.22.0/24
    cidrsubnet(var.vpc_cidr, 8, 23), # 10.0.23.0/24
  ]
  
  enable_nat_gateway = var.enable_nat_gateway
  enable_vpn_gateway = var.enable_vpn_gateway
  
  tags = local.common_tags
}

# =============================================================================
# Security Module
# =============================================================================

module "security" {
  source = "./modules/security"
  
  name_prefix = local.name_prefix
  environment = var.environment
  vpc_id      = module.networking.vpc_id
  
  # Allow HTTP/HTTPS from anywhere to ALB
  alb_ingress_cidrs = ["0.0.0.0/0"]
  
  # Allow backend traffic only from ALB security group
  backend_allowed_security_groups = [module.security.alb_security_group_id]
  
  # Database access only from backend security group
  database_allowed_security_groups = [module.security.backend_security_group_id]
  
  tags = local.common_tags
  
  depends_on = [module.networking]
}

# =============================================================================
# Database Module
# =============================================================================

module "database" {
  source = "./modules/database"
  
  name_prefix = local.name_prefix
  environment = var.environment
  
  # Database configuration
  db_name     = local.db_name
  db_username = local.db_username
  db_password = var.db_password != "" ? var.db_password : random_password.db_password.result
  
  # Network configuration
  vpc_id               = module.networking.vpc_id
  database_subnet_ids  = module.networking.database_subnet_ids
  security_group_ids   = [module.security.database_security_group_id]
  
  # Instance configuration
  instance_class       = var.db_instance_class
  allocated_storage    = var.db_allocated_storage
  max_allocated_storage = var.db_max_allocated_storage
  
  # Backup and maintenance
  backup_retention_period = var.db_backup_retention_period
  backup_window          = var.db_backup_window
  maintenance_window     = var.db_maintenance_window
  
  # Multi-AZ for production
  multi_az               = var.environment == "production"
  deletion_protection    = var.environment == "production"
  
  # Performance monitoring
  performance_insights_enabled = var.environment != "development"
  monitoring_interval         = var.environment == "production" ? 60 : 0
  
  tags = local.common_tags
  
  depends_on = [module.networking, module.security]
}

# =============================================================================
# Cache Module (Redis/ElastiCache)
# =============================================================================

module "cache" {
  source = "./modules/cache"
  
  name_prefix = local.name_prefix
  environment = var.environment
  
  # Network configuration
  vpc_id              = module.networking.vpc_id
  private_subnet_ids  = module.networking.private_subnet_ids
  security_group_ids  = [module.security.cache_security_group_id]
  
  # Redis configuration
  node_type           = var.redis_node_type
  num_cache_nodes     = var.redis_num_nodes
  parameter_group_name = var.redis_parameter_group
  
  # Backup configuration
  snapshot_retention_limit = var.redis_snapshot_retention
  snapshot_window         = var.redis_snapshot_window
  
  # Multi-AZ for production
  automatic_failover_enabled = var.environment == "production"
  multi_az_enabled          = var.environment == "production"
  
  tags = local.common_tags
  
  depends_on = [module.networking, module.security]
}

# =============================================================================
# Container Registry (ECR)
# =============================================================================

module "container_registry" {
  source = "./modules/ecr"
  
  name_prefix = local.name_prefix
  environment = var.environment
  
  # Repository configuration
  repositories = [
    "praktiko-backend",
    "praktiko-worker",
    "praktiko-mcp-server"
  ]
  
  # Lifecycle policy
  image_count_limit = var.ecr_image_count_limit
  
  # Cross-account access
  cross_account_ids = var.ecr_cross_account_ids
  
  tags = local.common_tags
}

# =============================================================================
# ECS Cluster and Services
# =============================================================================

module "ecs" {
  source = "./modules/ecs"
  
  name_prefix = local.name_prefix
  environment = var.environment
  
  # Network configuration
  vpc_id              = module.networking.vpc_id
  private_subnet_ids  = module.networking.private_subnet_ids
  public_subnet_ids   = module.networking.public_subnet_ids
  
  # Security groups
  alb_security_group_id     = module.security.alb_security_group_id
  backend_security_group_id = module.security.backend_security_group_id
  
  # Database connection
  database_endpoint = module.database.endpoint
  database_name     = local.db_name
  database_username = local.db_username
  database_password = var.db_password != "" ? var.db_password : random_password.db_password.result
  
  # Cache connection
  cache_endpoint = module.cache.endpoint
  
  # Container images
  backend_image_uri = "${module.container_registry.repository_urls["praktiko-backend"]}:latest"
  
  # Service configuration
  backend_desired_count = var.backend_desired_count
  backend_cpu          = var.backend_cpu
  backend_memory       = var.backend_memory
  
  # Auto scaling
  backend_min_capacity = var.backend_min_capacity
  backend_max_capacity = var.backend_max_capacity
  
  # Health check
  health_check_path = "/health"
  
  # Environment variables
  environment_variables = {
    ENVIRONMENT         = var.environment
    DATABASE_URL        = "postgresql://${local.db_username}:${var.db_password != "" ? var.db_password : random_password.db_password.result}@${module.database.endpoint}/${local.db_name}"
    REDIS_URL          = "redis://${module.cache.endpoint}:6379"
    JWT_SECRET_KEY     = var.jwt_secret_key != "" ? var.jwt_secret_key : random_password.jwt_secret.result
    LLM_API_KEY        = var.llm_api_key
    LANGFUSE_PUBLIC_KEY = var.langfuse_public_key
    LANGFUSE_SECRET_KEY = var.langfuse_secret_key
  }
  
  # Secrets (stored in AWS Secrets Manager)
  secrets = {
    DATABASE_PASSWORD = module.database.password_secret_arn
    JWT_SECRET_KEY   = aws_secretsmanager_secret.jwt_secret.arn
    LLM_API_KEY      = aws_secretsmanager_secret.llm_api_key.arn
  }
  
  tags = local.common_tags
  
  depends_on = [
    module.networking,
    module.security,
    module.database,
    module.cache,
    module.container_registry
  ]
}

# =============================================================================
# Frontend Distribution (CloudFront + S3)
# =============================================================================

module "frontend" {
  source = "./modules/frontend"
  
  name_prefix = local.name_prefix
  environment = var.environment
  
  # Domain configuration
  domain_name = local.domain_name
  
  # SSL certificate
  certificate_arn = var.ssl_certificate_arn
  
  # Backend integration
  api_domain_name = module.ecs.alb_dns_name
  
  # Cache configuration
  cache_behavior_settings = {
    default_ttl = var.cloudfront_default_ttl
    max_ttl     = var.cloudfront_max_ttl
    min_ttl     = var.cloudfront_min_ttl
  }
  
  # Security headers
  security_headers_enabled = var.environment == "production"
  
  tags = local.common_tags
  
  depends_on = [module.ecs]
}

# =============================================================================
# Monitoring and Observability
# =============================================================================

module "monitoring" {
  source = "./modules/monitoring"
  
  name_prefix = local.name_prefix
  environment = var.environment
  
  # Resources to monitor
  ecs_cluster_name = module.ecs.cluster_name
  ecs_service_names = [
    module.ecs.backend_service_name
  ]
  
  alb_arn_suffix       = module.ecs.alb_arn_suffix
  target_group_arn_suffix = module.ecs.target_group_arn_suffix
  
  # Database monitoring
  db_instance_identifier = module.database.identifier
  
  # Cache monitoring
  cache_cluster_id = module.cache.cluster_id
  
  # CloudFront monitoring
  cloudfront_distribution_id = module.frontend.distribution_id
  
  # Alerting configuration
  alert_email = var.alert_email
  slack_webhook_url = var.slack_webhook_url
  
  # Alert thresholds
  cpu_threshold_high    = var.cpu_threshold_high
  memory_threshold_high = var.memory_threshold_high
  error_rate_threshold  = var.error_rate_threshold
  response_time_threshold = var.response_time_threshold
  
  tags = local.common_tags
  
  depends_on = [
    module.ecs,
    module.database,
    module.cache,
    module.frontend
  ]
}

# =============================================================================
# MCP Server Configuration
# =============================================================================

module "mcp_server" {
  source = "./modules/mcp"
  
  name_prefix = local.name_prefix
  environment = var.environment
  
  # Network configuration
  vpc_id              = module.networking.vpc_id
  private_subnet_ids  = module.networking.private_subnet_ids
  security_group_ids  = [module.security.mcp_security_group_id]
  
  # ECS cluster
  ecs_cluster_id = module.ecs.cluster_id
  
  # Container configuration
  mcp_image_uri = "${module.container_registry.repository_urls["praktiko-mcp-server"]}:latest"
  
  # Service configuration
  desired_count = var.mcp_desired_count
  cpu          = var.mcp_cpu
  memory       = var.mcp_memory
  
  # Environment-specific configuration
  mcp_config = {
    development = {
      log_level = "DEBUG"
      workers   = 2
    }
    staging = {
      log_level = "INFO"
      workers   = 4
    }
    production = {
      log_level = "INFO"
      workers   = 8
    }
  }
  
  tags = local.common_tags
  
  depends_on = [
    module.networking,
    module.security,
    module.ecs,
    module.container_registry
  ]
}

# =============================================================================
# Secrets Management
# =============================================================================

# Generate random passwords for security
resource "random_password" "db_password" {
  length  = 32
  special = true
}

resource "random_password" "jwt_secret" {
  length  = 64
  special = false
}

# Store secrets in AWS Secrets Manager
resource "aws_secretsmanager_secret" "db_password" {
  name        = "${local.name_prefix}-db-password"
  description = "Database password for ${var.environment} environment"
  
  tags = local.common_tags
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id     = aws_secretsmanager_secret.db_password.id
  secret_string = var.db_password != "" ? var.db_password : random_password.db_password.result
}

resource "aws_secretsmanager_secret" "jwt_secret" {
  name        = "${local.name_prefix}-jwt-secret"
  description = "JWT secret key for ${var.environment} environment"
  
  tags = local.common_tags
}

resource "aws_secretsmanager_secret_version" "jwt_secret" {
  secret_id     = aws_secretsmanager_secret.jwt_secret.id
  secret_string = var.jwt_secret_key != "" ? var.jwt_secret_key : random_password.jwt_secret.result
}

resource "aws_secretsmanager_secret" "llm_api_key" {
  name        = "${local.name_prefix}-llm-api-key"
  description = "LLM API key for ${var.environment} environment"
  
  tags = local.common_tags
}

resource "aws_secretsmanager_secret_version" "llm_api_key" {
  secret_id     = aws_secretsmanager_secret.llm_api_key.id
  secret_string = var.llm_api_key
}

# =============================================================================
# Outputs
# =============================================================================

output "vpc_id" {
  description = "ID of the VPC"
  value       = module.networking.vpc_id
}

output "database_endpoint" {
  description = "RDS instance endpoint"
  value       = module.database.endpoint
  sensitive   = true
}

output "cache_endpoint" {
  description = "ElastiCache endpoint"
  value       = module.cache.endpoint
}

output "backend_url" {
  description = "Backend API URL"
  value       = "https://${module.ecs.alb_dns_name}"
}

output "frontend_url" {
  description = "Frontend URL"
  value       = "https://${local.domain_name}"
}

output "mcp_server_endpoint" {
  description = "MCP Server endpoint"
  value       = module.mcp_server.endpoint
}

output "ecr_repositories" {
  description = "ECR repository URLs"
  value       = module.container_registry.repository_urls
}

output "monitoring_dashboard_url" {
  description = "CloudWatch dashboard URL"
  value       = module.monitoring.dashboard_url
}