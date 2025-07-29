# =============================================================================
# ECS Module Outputs
# =============================================================================

# =============================================================================
# ECS Cluster Outputs
# =============================================================================

output "cluster_id" {
  description = "ID of the ECS cluster"
  value       = aws_ecs_cluster.main.id
}

output "cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.main.name
}

output "cluster_arn" {
  description = "ARN of the ECS cluster"
  value       = aws_ecs_cluster.main.arn
}

# =============================================================================
# ECS Service Outputs
# =============================================================================

output "backend_service_name" {
  description = "Name of the backend ECS service"
  value       = aws_ecs_service.backend.name
}

output "backend_service_arn" {
  description = "ARN of the backend ECS service"
  value       = aws_ecs_service.backend.id
}

output "backend_task_definition_arn" {
  description = "ARN of the backend task definition"
  value       = aws_ecs_task_definition.backend.arn
}

output "backend_task_definition_family" {
  description = "Family of the backend task definition"
  value       = aws_ecs_task_definition.backend.family
}

output "backend_task_definition_revision" {
  description = "Revision of the backend task definition"
  value       = aws_ecs_task_definition.backend.revision
}

# =============================================================================
# Load Balancer Outputs
# =============================================================================

output "alb_id" {
  description = "ID of the Application Load Balancer"
  value       = aws_lb.main.id
}

output "alb_arn" {
  description = "ARN of the Application Load Balancer"
  value       = aws_lb.main.arn
}

output "alb_arn_suffix" {
  description = "ARN suffix of the Application Load Balancer"
  value       = aws_lb.main.arn_suffix
}

output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = aws_lb.main.dns_name
}

output "alb_zone_id" {
  description = "Canonical hosted zone ID of the Application Load Balancer"
  value       = aws_lb.main.zone_id
}

output "alb_listener_arn" {
  description = "ARN of the ALB listener"
  value       = var.certificate_arn != "" ? aws_lb_listener.https[0].arn : aws_lb_listener.http_dev[0].arn
}

# =============================================================================
# Target Group Outputs
# =============================================================================

output "target_group_arn" {
  description = "ARN of the target group"
  value       = aws_lb_target_group.backend.arn
}

output "target_group_arn_suffix" {
  description = "ARN suffix of the target group"
  value       = aws_lb_target_group.backend.arn_suffix
}

output "target_group_name" {
  description = "Name of the target group"
  value       = aws_lb_target_group.backend.name
}

# =============================================================================
# Auto Scaling Outputs
# =============================================================================

output "autoscaling_target_arn" {
  description = "ARN of the auto scaling target"
  value       = aws_appautoscaling_target.backend.id
}

output "autoscaling_cpu_policy_arn" {
  description = "ARN of the CPU-based auto scaling policy"
  value       = aws_appautoscaling_policy.backend_cpu.arn
}

output "autoscaling_memory_policy_arn" {
  description = "ARN of the memory-based auto scaling policy"
  value       = aws_appautoscaling_policy.backend_memory.arn
}

output "autoscaling_requests_policy_arn" {
  description = "ARN of the request count-based auto scaling policy"
  value       = aws_appautoscaling_policy.backend_requests.arn
}

# =============================================================================
# IAM Role Outputs
# =============================================================================

output "ecs_execution_role_arn" {
  description = "ARN of the ECS execution role"
  value       = aws_iam_role.ecs_execution.arn
}

output "ecs_task_role_arn" {
  description = "ARN of the ECS task role"
  value       = aws_iam_role.ecs_task.arn
}

# =============================================================================
# CloudWatch Log Group Outputs
# =============================================================================

output "backend_log_group_name" {
  description = "Name of the backend CloudWatch log group"
  value       = aws_cloudwatch_log_group.backend.name
}

output "backend_log_group_arn" {
  description = "ARN of the backend CloudWatch log group"
  value       = aws_cloudwatch_log_group.backend.arn
}

output "ecs_exec_log_group_name" {
  description = "Name of the ECS Exec CloudWatch log group"
  value       = aws_cloudwatch_log_group.ecs_exec.name
}

# =============================================================================
# Service Discovery Outputs
# =============================================================================

output "service_discovery_namespace_id" {
  description = "ID of the service discovery namespace"
  value       = var.enable_service_discovery ? aws_service_discovery_private_dns_namespace.main[0].id : null
}

output "service_discovery_service_arn" {
  description = "ARN of the service discovery service"
  value       = var.enable_service_discovery ? aws_service_discovery_service.backend[0].arn : null
}

# =============================================================================
# S3 Bucket Outputs (ALB Logs)
# =============================================================================

output "alb_logs_bucket_name" {
  description = "Name of the S3 bucket for ALB logs"
  value       = aws_s3_bucket.alb_logs.id
}

output "alb_logs_bucket_arn" {
  description = "ARN of the S3 bucket for ALB logs"
  value       = aws_s3_bucket.alb_logs.arn
}

# =============================================================================
# KMS Key Outputs
# =============================================================================

output "ecs_kms_key_id" {
  description = "ID of the KMS key for ECS"
  value       = aws_kms_key.ecs.key_id
}

output "ecs_kms_key_arn" {
  description = "ARN of the KMS key for ECS"
  value       = aws_kms_key.ecs.arn
}

# =============================================================================
# Service Configuration Summary
# =============================================================================

output "service_summary" {
  description = "Summary of ECS service configuration"
  value = {
    cluster_name        = aws_ecs_cluster.main.name
    service_name        = aws_ecs_service.backend.name
    task_definition     = aws_ecs_task_definition.backend.family
    desired_count       = aws_ecs_service.backend.desired_count
    cpu                 = var.backend_cpu
    memory              = var.backend_memory
    min_capacity        = var.backend_min_capacity
    max_capacity        = var.backend_max_capacity
    alb_dns_name        = aws_lb.main.dns_name
    health_check_path   = var.health_check_path
    container_port      = var.backend_port
    service_discovery   = var.enable_service_discovery
  }
}