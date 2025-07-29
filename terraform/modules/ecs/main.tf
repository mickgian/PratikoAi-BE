# =============================================================================
# ECS Module - Cluster, Services, Tasks, and Load Balancer
# Comprehensive container orchestration with auto-scaling and monitoring
# =============================================================================

# =============================================================================
# Data Sources
# =============================================================================

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# =============================================================================
# ECS Cluster
# =============================================================================

resource "aws_ecs_cluster" "main" {
  name = "${var.name_prefix}-cluster"
  
  configuration {
    execute_command_configuration {
      kms_key_id = aws_kms_key.ecs.arn
      logging    = "OVERRIDE"
      
      log_configuration {
        cloud_watch_encryption_enabled = true
        cloud_watch_log_group_name     = aws_cloudwatch_log_group.ecs_exec.name
      }
    }
  }
  
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
  
  tags = merge(var.tags, {
    Name = "${var.name_prefix}-ecs-cluster"
  })
}

# =============================================================================
# ECS Cluster Capacity Providers
# =============================================================================

resource "aws_ecs_cluster_capacity_providers" "main" {
  cluster_name = aws_ecs_cluster.main.name
  
  capacity_providers = ["FARGATE", "FARGATE_SPOT"]
  
  default_capacity_provider_strategy {
    base              = 1
    weight            = 100
    capacity_provider = "FARGATE"
  }
  
  # Use spot instances for non-critical workloads in development
  dynamic "default_capacity_provider_strategy" {
    for_each = var.environment == "development" ? [1] : []
    
    content {
      base              = 0
      weight            = 50
      capacity_provider = "FARGATE_SPOT"
    }
  }
}

# =============================================================================
# KMS Key for ECS Exec
# =============================================================================

resource "aws_kms_key" "ecs" {
  description             = "KMS key for ECS Exec encryption"
  deletion_window_in_days = 7
  
  tags = merge(var.tags, {
    Name = "${var.name_prefix}-ecs-kms-key"
  })
}

resource "aws_kms_alias" "ecs" {
  name          = "alias/${var.name_prefix}-ecs"
  target_key_id = aws_kms_key.ecs.key_id
}

# =============================================================================
# CloudWatch Log Groups
# =============================================================================

resource "aws_cloudwatch_log_group" "ecs_exec" {
  name              = "/aws/ecs/${var.name_prefix}/exec"
  retention_in_days = var.log_retention_days
  
  tags = merge(var.tags, {
    Name = "${var.name_prefix}-ecs-exec-logs"
  })
}

resource "aws_cloudwatch_log_group" "backend" {
  name              = "/aws/ecs/${var.name_prefix}/backend"
  retention_in_days = var.log_retention_days
  
  tags = merge(var.tags, {
    Name = "${var.name_prefix}-backend-logs"
  })
}

# =============================================================================
# Application Load Balancer
# =============================================================================

resource "aws_lb" "main" {
  name               = "${var.name_prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [var.alb_security_group_id]
  subnets            = var.public_subnet_ids
  
  enable_deletion_protection = var.environment == "production"
  
  access_logs {
    bucket  = aws_s3_bucket.alb_logs.id
    prefix  = "alb-logs"
    enabled = true
  }
  
  tags = merge(var.tags, {
    Name = "${var.name_prefix}-alb"
  })
}

# =============================================================================
# S3 Bucket for ALB Access Logs
# =============================================================================

resource "aws_s3_bucket" "alb_logs" {
  bucket        = "${var.name_prefix}-alb-logs-${random_id.bucket_suffix.hex}"
  force_destroy = var.environment != "production"
  
  tags = merge(var.tags, {
    Name = "${var.name_prefix}-alb-logs"
  })
}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

resource "aws_s3_bucket_policy" "alb_logs" {
  bucket = aws_s3_bucket.alb_logs.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${local.alb_account_id}:root"
        }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.alb_logs.arn}/alb-logs/AWSLogs/${data.aws_caller_identity.current.account_id}/*"
      },
      {
        Effect = "Allow"
        Principal = {
          Service = "delivery.logs.amazonaws.com"
        }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.alb_logs.arn}/alb-logs/AWSLogs/${data.aws_caller_identity.current.account_id}/*"
        Condition = {
          StringEquals = {
            "s3:x-amz-acl" = "bucket-owner-full-control"
          }
        }
      },
      {
        Effect = "Allow"
        Principal = {
          Service = "delivery.logs.amazonaws.com"
        }
        Action   = "s3:GetBucketAcl"
        Resource = aws_s3_bucket.alb_logs.arn
      }
    ]
  })
}

resource "aws_s3_bucket_server_side_encryption_configuration" "alb_logs" {
  bucket = aws_s3_bucket.alb_logs.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "alb_logs" {
  bucket = aws_s3_bucket.alb_logs.id
  
  rule {
    id     = "delete_old_logs"
    status = "Enabled"
    
    expiration {
      days = var.alb_logs_retention_days
    }
  }
}

# =============================================================================
# ALB Target Group
# =============================================================================

resource "aws_lb_target_group" "backend" {
  name        = "${var.name_prefix}-backend-tg"
  port        = var.backend_port
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"
  
  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 10
    interval            = 30
    path                = var.health_check_path
    matcher             = "200"
    protocol            = "HTTP"
    port                = "traffic-port"
  }
  
  # Deregistration delay for graceful shutdowns
  deregistration_delay = var.deregistration_delay
  
  tags = merge(var.tags, {
    Name = "${var.name_prefix}-backend-tg"
  })
}

# =============================================================================
# ALB Listeners
# =============================================================================

# HTTP Listener (redirect to HTTPS)
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"
  
  default_action {
    type = "redirect"
    
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
  
  tags = var.tags
}

# HTTPS Listener
resource "aws_lb_listener" "https" {
  count = var.certificate_arn != "" ? 1 : 0
  
  load_balancer_arn = aws_lb.main.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS-1-2-2017-01"
  certificate_arn   = var.certificate_arn
  
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }
  
  tags = var.tags
}

# HTTP Listener for development (when no SSL certificate)
resource "aws_lb_listener" "http_dev" {
  count = var.certificate_arn == "" ? 1 : 0
  
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"
  
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }
  
  tags = var.tags
}

# =============================================================================
# ECS Task Definition
# =============================================================================

resource "aws_ecs_task_definition" "backend" {
  family                   = "${var.name_prefix}-backend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.backend_cpu
  memory                   = var.backend_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn           = aws_iam_role.ecs_task.arn
  
  container_definitions = jsonencode([
    {
      name  = "backend"
      image = var.backend_image_uri
      
      essential = true
      
      portMappings = [
        {
          containerPort = var.backend_port
          protocol      = "tcp"
        }
      ]
      
      environment = [
        for key, value in var.environment_variables : {
          name  = key
          value = tostring(value)
        }
      ]
      
      secrets = [
        for key, arn in var.secrets : {
          name      = key
          valueFrom = arn
        }
      ]
      
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.backend.name
          "awslogs-region"        = data.aws_region.current.name
          "awslogs-stream-prefix" = "ecs"
        }
      }
      
      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:${var.backend_port}${var.health_check_path} || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
      
      # Resource limits
      memory           = var.backend_memory
      memoryReservation = var.backend_memory * 0.8
      
      # Security
      readonlyRootFilesystem = false
      user                  = "1000:1000"
      
      # Graceful shutdown
      stopTimeout = 30
    }
  ])
  
  tags = merge(var.tags, {
    Name = "${var.name_prefix}-backend-task"
  })
}

# =============================================================================
# ECS Service
# =============================================================================

resource "aws_ecs_service" "backend" {
  name            = "${var.name_prefix}-backend"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = var.backend_desired_count
  
  capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight           = 100
    base             = var.backend_desired_count > 1 ? 1 : 0
  }
  
  # Use Fargate Spot for development
  dynamic "capacity_provider_strategy" {
    for_each = var.environment == "development" ? [1] : []
    
    content {
      capacity_provider = "FARGATE_SPOT"
      weight           = 50
      base             = 0
    }
  }
  
  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.backend_security_group_id]
    assign_public_ip = false
  }
  
  load_balancer {
    target_group_arn = aws_lb_target_group.backend.arn
    container_name   = "backend"
    container_port   = var.backend_port
  }
  
  # Deployment configuration
  deployment_configuration {
    maximum_percent         = 200
    minimum_healthy_percent = var.environment == "production" ? 100 : 50
    
    deployment_circuit_breaker {
      enable   = true
      rollback = true
    }
  }
  
  # Service discovery
  dynamic "service_registries" {
    for_each = var.enable_service_discovery ? [1] : []
    
    content {
      registry_arn = aws_service_discovery_service.backend[0].arn
    }
  }
  
  # Enable ECS Exec for debugging
  enable_execute_command = var.environment != "production"
  
  # Platform version
  platform_version = "LATEST"
  
  # Propagate tags from task definition
  propagate_tags = "TASK_DEFINITION"
  
  tags = merge(var.tags, {
    Name = "${var.name_prefix}-backend-service"
  })
  
  depends_on = [
    aws_lb_listener.https,
    aws_lb_listener.http_dev,
    aws_iam_role_policy_attachment.ecs_execution,
    aws_iam_role_policy_attachment.ecs_task
  ]
}

# =============================================================================
# Service Discovery (Optional)
# =============================================================================

resource "aws_service_discovery_private_dns_namespace" "main" {
  count = var.enable_service_discovery ? 1 : 0
  
  name = "${var.name_prefix}.local"
  vpc  = var.vpc_id
  
  tags = merge(var.tags, {
    Name = "${var.name_prefix}-service-discovery"
  })
}

resource "aws_service_discovery_service" "backend" {
  count = var.enable_service_discovery ? 1 : 0
  
  name = "backend"
  
  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main[0].id
    
    dns_records {
      ttl  = 10
      type = "A"
    }
    
    routing_policy = "MULTIVALUE"
  }
  
  health_check_grace_period_seconds = 300
  
  tags = merge(var.tags, {
    Name = "${var.name_prefix}-backend-discovery"
  })
}

# =============================================================================
# Auto Scaling
# =============================================================================

resource "aws_appautoscaling_target" "backend" {
  max_capacity       = var.backend_max_capacity
  min_capacity       = var.backend_min_capacity
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.backend.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
  
  tags = var.tags
}

# CPU-based scaling policy
resource "aws_appautoscaling_policy" "backend_cpu" {
  name               = "${var.name_prefix}-backend-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.backend.resource_id
  scalable_dimension = aws_appautoscaling_target.backend.scalable_dimension
  service_namespace  = aws_appautoscaling_target.backend.service_namespace
  
  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    
    target_value       = var.cpu_target_value
    scale_in_cooldown  = var.scale_in_cooldown
    scale_out_cooldown = var.scale_out_cooldown
  }
}

# Memory-based scaling policy
resource "aws_appautoscaling_policy" "backend_memory" {
  name               = "${var.name_prefix}-backend-memory-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.backend.resource_id
  scalable_dimension = aws_appautoscaling_target.backend.scalable_dimension
  service_namespace  = aws_appautoscaling_target.backend.service_namespace
  
  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }
    
    target_value       = var.memory_target_value
    scale_in_cooldown  = var.scale_in_cooldown
    scale_out_cooldown = var.scale_out_cooldown
  }
}

# Request count-based scaling policy
resource "aws_appautoscaling_policy" "backend_requests" {
  name               = "${var.name_prefix}-backend-requests-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.backend.resource_id
  scalable_dimension = aws_appautoscaling_target.backend.scalable_dimension
  service_namespace  = aws_appautoscaling_target.backend.service_namespace
  
  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ALBRequestCountPerTarget"
      resource_label = "${aws_lb.main.arn_suffix}/${aws_lb_target_group.backend.arn_suffix}"
    }
    
    target_value       = var.requests_target_value
    scale_in_cooldown  = var.scale_in_cooldown
    scale_out_cooldown = var.scale_out_cooldown
  }
}

# =============================================================================
# IAM Roles and Policies
# =============================================================================

# ECS Execution Role
resource "aws_iam_role" "ecs_execution" {
  name = "${var.name_prefix}-ecs-execution-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
  
  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Additional permissions for secrets and logging
resource "aws_iam_role_policy" "ecs_execution_additional" {
  name = "${var.name_prefix}-ecs-execution-additional"
  role = aws_iam_role.ecs_execution.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "kms:Decrypt"
        ]
        Resource = [
          for arn in values(var.secrets) : arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "${aws_cloudwatch_log_group.backend.arn}:*"
      }
    ]
  })
}

# ECS Task Role
resource "aws_iam_role" "ecs_task" {
  name = "${var.name_prefix}-ecs-task-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
  
  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "ecs_task" {
  role       = aws_iam_role.ecs_task.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Task-specific permissions
resource "aws_iam_role_policy" "ecs_task_additional" {
  name = "${var.name_prefix}-ecs-task-additional"
  role = aws_iam_role.ecs_task.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssmmessages:CreateControlChannel",
          "ssmmessages:CreateDataChannel",
          "ssmmessages:OpenControlChannel",
          "ssmmessages:OpenDataChannel"
        ]
        Resource = "*"
      }
    ]
  })
}

# =============================================================================
# Local Values
# =============================================================================

locals {
  # ALB service account IDs by region
  alb_account_ids = {
    "us-east-1"      = "127311923021"
    "us-east-2"      = "033677994240"
    "us-west-1"      = "027434742980"
    "us-west-2"      = "797873946194"
    "eu-west-1"      = "156460612806"
    "eu-central-1"   = "054676820928"
    "ap-southeast-1" = "114774131450"
    "ap-southeast-2" = "783225319266"
    "ap-northeast-1" = "582318560864"
  }
  
  alb_account_id = lookup(local.alb_account_ids, data.aws_region.current.name, "127311923021")
}