# =============================================================================
# Networking Module Outputs
# =============================================================================

output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC"
  value       = aws_vpc.main.cidr_block
}

output "internet_gateway_id" {
  description = "ID of the Internet Gateway"
  value       = aws_internet_gateway.main.id
}

# =============================================================================
# Subnet Outputs
# =============================================================================

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = aws_subnet.private[*].id
}

output "database_subnet_ids" {
  description = "IDs of the database subnets"
  value       = aws_subnet.database[*].id
}

output "public_subnet_cidrs" {
  description = "CIDR blocks of the public subnets"
  value       = aws_subnet.public[*].cidr_block
}

output "private_subnet_cidrs" {
  description = "CIDR blocks of the private subnets"
  value       = aws_subnet.private[*].cidr_block
}

output "database_subnet_cidrs" {
  description = "CIDR blocks of the database subnets"
  value       = aws_subnet.database[*].cidr_block
}

# =============================================================================
# Subnet Group Outputs
# =============================================================================

output "db_subnet_group_name" {
  description = "Name of the database subnet group"
  value       = aws_db_subnet_group.main.name
}

output "cache_subnet_group_name" {
  description = "Name of the cache subnet group"
  value       = aws_elasticache_subnet_group.main.name
}

# =============================================================================
# NAT Gateway Outputs
# =============================================================================

output "nat_gateway_ids" {
  description = "IDs of the NAT Gateways"
  value       = aws_nat_gateway.main[*].id
}

output "nat_gateway_public_ips" {
  description = "Public IPs of the NAT Gateways"
  value       = aws_eip.nat[*].public_ip
}

# =============================================================================
# Route Table Outputs
# =============================================================================

output "public_route_table_id" {
  description = "ID of the public route table"
  value       = aws_route_table.public.id
}

output "private_route_table_ids" {
  description = "IDs of the private route tables"
  value       = aws_route_table.private[*].id
}

output "database_route_table_id" {
  description = "ID of the database route table"
  value       = aws_route_table.database.id
}

# =============================================================================
# Availability Zone Mappings
# =============================================================================

output "availability_zones" {
  description = "List of availability zones used"
  value       = var.availability_zones
}

output "public_subnet_az_mapping" {
  description = "Mapping of public subnet IDs to availability zones"
  value = zipmap(
    aws_subnet.public[*].id,
    aws_subnet.public[*].availability_zone
  )
}

output "private_subnet_az_mapping" {
  description = "Mapping of private subnet IDs to availability zones"
  value = zipmap(
    aws_subnet.private[*].id,
    aws_subnet.private[*].availability_zone
  )
}

output "database_subnet_az_mapping" {
  description = "Mapping of database subnet IDs to availability zones"
  value = zipmap(
    aws_subnet.database[*].id,
    aws_subnet.database[*].availability_zone
  )
}

# =============================================================================
# VPC Endpoint Outputs
# =============================================================================

output "vpc_endpoint_s3_id" {
  description = "ID of the S3 VPC Endpoint"
  value       = var.enable_vpc_endpoints ? aws_vpc_endpoint.s3[0].id : null
}

output "vpc_endpoint_ecr_dkr_id" {
  description = "ID of the ECR DKR VPC Endpoint"
  value       = var.enable_vpc_endpoints ? aws_vpc_endpoint.ecr_dkr[0].id : null
}

output "vpc_endpoint_ecr_api_id" {
  description = "ID of the ECR API VPC Endpoint"
  value       = var.enable_vpc_endpoints ? aws_vpc_endpoint.ecr_api[0].id : null
}

output "vpc_endpoint_logs_id" {
  description = "ID of the CloudWatch Logs VPC Endpoint"
  value       = var.enable_vpc_endpoints ? aws_vpc_endpoint.logs[0].id : null
}

# =============================================================================
# Network ACL Outputs
# =============================================================================

output "public_network_acl_id" {
  description = "ID of the public network ACL"
  value       = aws_network_acl.public.id
}

output "private_network_acl_id" {
  description = "ID of the private network ACL"
  value       = aws_network_acl.private.id
}

output "database_network_acl_id" {
  description = "ID of the database network ACL"
  value       = aws_network_acl.database.id
}

# =============================================================================
# Summary Outputs for Reference
# =============================================================================

output "networking_summary" {
  description = "Summary of networking configuration"
  value = {
    vpc_id                = aws_vpc.main.id
    vpc_cidr             = aws_vpc.main.cidr_block
    public_subnets       = length(aws_subnet.public)
    private_subnets      = length(aws_subnet.private)
    database_subnets     = length(aws_subnet.database)
    availability_zones   = length(var.availability_zones)
    nat_gateways_enabled = var.enable_nat_gateway
    vpc_endpoints_enabled = var.enable_vpc_endpoints
    flow_logs_enabled    = var.enable_vpc_flow_logs
  }
}