# =============================================================================
# PratikoAI Infrastructure Variables
# Comprehensive variable definitions for multi-environment deployment
# =============================================================================

# =============================================================================
# General Configuration
# =============================================================================

variable "environment" {
  description = "Environment name (development, staging, production)"
  type        = string
  
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be one of: development, staging, production."
  }
}

variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "PratikoAI"
}

# =============================================================================
# Networking Configuration
# =============================================================================

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "enable_nat_gateway" {
  description = "Enable NAT Gateway for private subnets"
  type        = bool
  default     = true
}

variable "enable_vpn_gateway" {
  description = "Enable VPN Gateway"
  type        = bool
  default     = false
}

# =============================================================================
# Database Configuration
# =============================================================================

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
  
  validation {
    condition = can(regex("^db\\.(t[2-4]|m[3-6]|r[3-6]|x[1-2])\\.(nano|micro|small|medium|large|xlarge|[0-9]+xlarge)$", var.db_instance_class))
    error_message = "DB instance class must be a valid RDS instance type."
  }
}

variable "db_allocated_storage" {
  description = "Initial storage allocation for RDS instance (GB)"
  type        = number
  default     = 20
}

variable "db_max_allocated_storage" {
  description = "Maximum storage allocation for RDS instance (GB)"
  type        = number
  default     = 100
}

variable "db_backup_retention_period" {
  description = "Number of days to retain automated backups"
  type        = number
  default     = 7
  
  validation {
    condition     = var.db_backup_retention_period >= 0 && var.db_backup_retention_period <= 35
    error_message = "Backup retention period must be between 0 and 35 days."
  }
}

variable "db_backup_window" {
  description = "Preferred backup window (UTC)"
  type        = string
  default     = "03:00-04:00"
}

variable "db_maintenance_window" {
  description = "Preferred maintenance window (UTC)"
  type        = string
  default     = "Mon:04:00-Mon:05:00"
}

variable "db_password" {
  description = "Database password (leave empty to auto-generate)"
  type        = string
  default     = ""
  sensitive   = true
}

# =============================================================================
# Cache Configuration (Redis/ElastiCache)
# =============================================================================

variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.t3.micro"
}

variable "redis_num_nodes" {
  description = "Number of Redis nodes"
  type        = number
  default     = 1
}

variable "redis_parameter_group" {
  description = "Redis parameter group"
  type        = string
  default     = "default.redis7"
}

variable "redis_snapshot_retention" {
  description = "Number of days to retain Redis snapshots"
  type        = number
  default     = 5
}

variable "redis_snapshot_window" {
  description = "Time window for Redis snapshots (UTC)"
  type        = string
  default     = "03:00-05:00"
}

# =============================================================================
# ECS Configuration
# =============================================================================

variable "backend_desired_count" {
  description = "Desired number of backend tasks"
  type        = number
  default     = 2
}

variable "backend_cpu" {
  description = "CPU units for backend task (1024 = 1 vCPU)"
  type        = number
  default     = 512
}

variable "backend_memory" {
  description = "Memory for backend task (MB)"
  type        = number
  default     = 1024
}

variable "backend_min_capacity" {
  description = "Minimum number of backend tasks for auto scaling"
  type        = number
  default     = 1
}

variable "backend_max_capacity" {
  description = "Maximum number of backend tasks for auto scaling"
  type        = number
  default     = 10
}

# =============================================================================
# MCP Server Configuration
# =============================================================================

variable "mcp_desired_count" {
  description = "Desired number of MCP server tasks"
  type        = number
  default     = 1
}

variable "mcp_cpu" {
  description = "CPU units for MCP server task"
  type        = number
  default     = 256
}

variable "mcp_memory" {
  description = "Memory for MCP server task (MB)"
  type        = number
  default     = 512
}

# =============================================================================
# Container Registry Configuration
# =============================================================================

variable "ecr_image_count_limit" {
  description = "Maximum number of images to keep in ECR repositories"
  type        = number
  default     = 30
}

variable "ecr_cross_account_ids" {
  description = "AWS account IDs that can access ECR repositories"
  type        = list(string)
  default     = []
}

# =============================================================================
# Frontend Configuration
# =============================================================================

variable "cloudfront_default_ttl" {
  description = "Default TTL for CloudFront cache (seconds)"
  type        = number
  default     = 86400  # 24 hours
}

variable "cloudfront_max_ttl" {
  description = "Maximum TTL for CloudFront cache (seconds)"
  type        = number
  default     = 31536000  # 1 year
}

variable "cloudfront_min_ttl" {
  description = "Minimum TTL for CloudFront cache (seconds)"
  type        = number
  default     = 0
}

variable "ssl_certificate_arn" {
  description = "ARN of SSL certificate for CloudFront (must be in us-east-1)"
  type        = string
  default     = ""
}

# =============================================================================
# Security Configuration
# =============================================================================

variable "jwt_secret_key" {
  description = "JWT secret key (leave empty to auto-generate)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "llm_api_key" {
  description = "OpenAI/LLM API key"
  type        = string
  sensitive   = true
}

variable "langfuse_public_key" {
  description = "Langfuse public key for LLM observability"
  type        = string
  default     = ""
}

variable "langfuse_secret_key" {
  description = "Langfuse secret key for LLM observability"
  type        = string
  default     = ""
  sensitive   = true
}

# =============================================================================
# Monitoring and Alerting Configuration
# =============================================================================

variable "alert_email" {
  description = "Email address for critical alerts"
  type        = string
  default     = ""
}

variable "slack_webhook_url" {
  description = "Slack webhook URL for notifications"
  type        = string
  default     = ""
  sensitive   = true
}

variable "cpu_threshold_high" {
  description = "CPU utilization threshold for high alerts (%)"
  type        = number
  default     = 80
  
  validation {
    condition     = var.cpu_threshold_high > 0 && var.cpu_threshold_high <= 100
    error_message = "CPU threshold must be between 1 and 100."
  }
}

variable "memory_threshold_high" {
  description = "Memory utilization threshold for high alerts (%)"
  type        = number
  default     = 80
  
  validation {
    condition     = var.memory_threshold_high > 0 && var.memory_threshold_high <= 100
    error_message = "Memory threshold must be between 1 and 100."
  }
}

variable "error_rate_threshold" {
  description = "Error rate threshold for alerts (%)"
  type        = number
  default     = 5
  
  validation {
    condition     = var.error_rate_threshold >= 0 && var.error_rate_threshold <= 100
    error_message = "Error rate threshold must be between 0 and 100."
  }
}

variable "response_time_threshold" {
  description = "Response time threshold for alerts (milliseconds)"
  type        = number
  default     = 2000
}

# =============================================================================
# Environment-Specific Defaults
# =============================================================================

# Development environment defaults
variable "development_overrides" {
  description = "Development environment configuration overrides"
  type = object({
    db_instance_class           = optional(string, "db.t3.micro")
    db_backup_retention_period  = optional(number, 1)
    redis_node_type            = optional(string, "cache.t3.micro")
    backend_desired_count      = optional(number, 1)
    backend_min_capacity       = optional(number, 1)
    backend_max_capacity       = optional(number, 3)
    enable_nat_gateway         = optional(bool, false)
  })
  default = {}
}

# Staging environment defaults
variable "staging_overrides" {
  description = "Staging environment configuration overrides"
  type = object({
    db_instance_class           = optional(string, "db.t3.small")
    db_backup_retention_period  = optional(number, 7)
    redis_node_type            = optional(string, "cache.t3.small")
    backend_desired_count      = optional(number, 2)
    backend_min_capacity       = optional(number, 1)
    backend_max_capacity       = optional(number, 5)
  })
  default = {}
}

# Production environment defaults
variable "production_overrides" {
  description = "Production environment configuration overrides"
  type = object({
    db_instance_class           = optional(string, "db.r6g.large")
    db_backup_retention_period  = optional(number, 30)
    db_allocated_storage       = optional(number, 100)
    db_max_allocated_storage   = optional(number, 1000)
    redis_node_type            = optional(string, "cache.r6g.large")
    redis_num_nodes            = optional(number, 2)
    backend_desired_count      = optional(number, 3)
    backend_min_capacity       = optional(number, 2)
    backend_max_capacity       = optional(number, 20)
    backend_cpu                = optional(number, 1024)
    backend_memory             = optional(number, 2048)
  })
  default = {}
}

# =============================================================================
# Feature Flags
# =============================================================================

variable "feature_flags" {
  description = "Feature flags for optional components"
  type = object({
    enable_monitoring          = optional(bool, true)
    enable_auto_scaling       = optional(bool, true)
    enable_backup_automation  = optional(bool, true)
    enable_mcp_server         = optional(bool, false)
    enable_cdn_security_headers = optional(bool, true)
    enable_waf                = optional(bool, false)
    enable_vpc_flow_logs      = optional(bool, false)
  })
  default = {}
}

# =============================================================================
# Local Values for Environment-Specific Configuration
# =============================================================================

locals {
  # Merge environment-specific overrides
  environment_config = var.environment == "development" ? var.development_overrides : (
    var.environment == "staging" ? var.staging_overrides : var.production_overrides
  )
  
  # Apply environment-specific defaults
  final_db_instance_class = coalesce(
    local.environment_config.db_instance_class,
    var.db_instance_class
  )
  
  final_backend_desired_count = coalesce(
    local.environment_config.backend_desired_count,
    var.backend_desired_count
  )
  
  final_enable_nat_gateway = coalesce(
    local.environment_config.enable_nat_gateway,
    var.enable_nat_gateway
  )
  
  # Computed values
  is_production = var.environment == "production"
  enable_multi_az = local.is_production
  enable_deletion_protection = local.is_production
  
  # Resource naming
  name_prefix = "praktiko-${var.environment}"
}