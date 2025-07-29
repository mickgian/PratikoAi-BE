# =============================================================================
# ECS Module Variables
# =============================================================================

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "public_subnet_ids" {
  description = "Public subnet IDs for ALB"
  type        = list(string)
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for ECS tasks"
  type        = list(string)
}

variable "alb_security_group_id" {
  description = "Security group ID for ALB"
  type        = string
}

variable "backend_security_group_id" {
  description = "Security group ID for backend tasks"
  type        = string
}

# =============================================================================
# Database Configuration
# =============================================================================

variable "database_endpoint" {
  description = "Database endpoint"
  type        = string
}

variable "database_name" {
  description = "Database name"
  type        = string
}

variable "database_username" {
  description = "Database username"
  type        = string
}

variable "database_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

variable "cache_endpoint" {
  description = "Cache endpoint"
  type        = string
}

# =============================================================================
# Container Configuration
# =============================================================================

variable "backend_image_uri" {
  description = "Backend container image URI"
  type        = string
}

variable "backend_port" {
  description = "Backend container port"
  type        = number
  default     = 8000
}

variable "backend_desired_count" {
  description = "Desired number of backend tasks"
  type        = number
  default     = 2
}

variable "backend_cpu" {
  description = "CPU units for backend task"
  type        = number
  default     = 512
}

variable "backend_memory" {
  description = "Memory for backend task (MB)"
  type        = number
  default     = 1024
}

# =============================================================================
# Auto Scaling Configuration
# =============================================================================

variable "backend_min_capacity" {
  description = "Minimum number of backend tasks"
  type        = number
  default     = 1
}

variable "backend_max_capacity" {
  description = "Maximum number of backend tasks"
  type        = number
  default     = 10
}

variable "cpu_target_value" {
  description = "Target CPU utilization for auto scaling"
  type        = number
  default     = 70
}

variable "memory_target_value" {
  description = "Target memory utilization for auto scaling"
  type        = number
  default     = 70
}

variable "requests_target_value" {
  description = "Target requests per target for auto scaling"
  type        = number
  default     = 1000
}

variable "scale_in_cooldown" {
  description = "Scale in cooldown period (seconds)"
  type        = number
  default     = 300
}

variable "scale_out_cooldown" {
  description = "Scale out cooldown period (seconds)"
  type        = number
  default     = 300
}

# =============================================================================
# Load Balancer Configuration
# =============================================================================

variable "certificate_arn" {
  description = "SSL certificate ARN for HTTPS listener"
  type        = string
  default     = ""
}

variable "health_check_path" {
  description = "Health check path"
  type        = string
  default     = "/health"
}

variable "deregistration_delay" {
  description = "Deregistration delay for target group (seconds)"
  type        = number
  default     = 60
}

variable "alb_logs_retention_days" {
  description = "ALB logs retention period (days)"
  type        = number
  default     = 30
}

# =============================================================================
# Environment Variables and Secrets
# =============================================================================

variable "environment_variables" {
  description = "Environment variables for the backend container"
  type        = map(string)
  default     = {}
}

variable "secrets" {
  description = "Secret ARNs for the backend container"
  type        = map(string)
  default     = {}
}

# =============================================================================
# Logging Configuration
# =============================================================================

variable "log_retention_days" {
  description = "CloudWatch log retention period (days)"
  type        = number
  default     = 30
}

# =============================================================================
# Service Discovery
# =============================================================================

variable "enable_service_discovery" {
  description = "Enable service discovery"
  type        = bool
  default     = false
}

# =============================================================================
# Tags
# =============================================================================

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}