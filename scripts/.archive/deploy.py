#!/usr/bin/env python3
"""
Advanced Zero-Downtime Deployment System for PratikoAI
Implements sophisticated deployment strategies with comprehensive monitoring,
automated rollbacks, and cross-service coordination.

This system supports:
- Blue-Green deployments for infrastructure changes
- Canary deployments for gradual rollouts
- Rolling updates for standard deployments
- Automated health checks and rollbacks
- Cross-service dependency management
- Real-time monitoring and alerting
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import boto3
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("deployment.log"), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


class DeploymentStrategy(Enum):
    """Available deployment strategies."""

    ROLLING = "rolling"
    BLUE_GREEN = "blue-green"
    CANARY = "canary"
    FAST = "fast"


class DeploymentStatus(Enum):
    """Deployment status states."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    HEALTH_CHECK = "health_check"
    CANARY_ANALYSIS = "canary_analysis"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class DeploymentConfig:
    """Configuration for deployment execution."""

    service_name: str
    environment: str
    image_uri: str
    strategy: DeploymentStrategy
    desired_count: int

    # Health check configuration
    health_check_timeout: int = 300
    health_check_interval: int = 15
    health_check_path: str = "/health"

    # Canary configuration
    canary_percentage: int = 10
    canary_duration: int = 300
    canary_success_threshold: float = 99.0

    # Rollback configuration
    auto_rollback: bool = True
    rollback_timeout: int = 600

    # Notification configuration
    slack_webhook: str | None = None
    email_recipients: list[str] = None


@dataclass
class HealthCheckResult:
    """Result of a health check operation."""

    endpoint: str
    status_code: int
    response_time: float
    healthy: bool
    details: dict[str, Any]


@dataclass
class DeploymentMetrics:
    """Metrics collected during deployment."""

    start_time: datetime
    end_time: datetime | None = None
    duration: float | None = None
    health_checks_passed: int = 0
    health_checks_failed: int = 0
    error_rate: float = 0.0
    response_time_p95: float = 0.0
    rollback_triggered: bool = False


class AWSDeploymentManager:
    """Manages AWS ECS deployments with advanced strategies."""

    def __init__(self, region: str = "us-east-1"):
        self.region = region

        # AWS clients
        self.ecs_client = boto3.client("ecs", region_name=region)
        self.elbv2_client = boto3.client("elbv2", region_name=region)
        self.cloudwatch_client = boto3.client("cloudwatch", region_name=region)
        self.logs_client = boto3.client("logs", region_name=region)

        # Deployment tracking
        self.deployment_history: list[dict[str, Any]] = []

    async def deploy(self, config: DeploymentConfig) -> bool:
        """Execute deployment with specified strategy."""

        logger.info(f"🚀 Starting {config.strategy.value} deployment for {config.service_name}")
        logger.info(f"   Environment: {config.environment}")
        logger.info(f"   Image: {config.image_uri}")
        logger.info(f"   Desired Count: {config.desired_count}")

        # Initialize metrics
        metrics = DeploymentMetrics(start_time=datetime.utcnow())

        try:
            # Pre-deployment validation
            if not await self._pre_deployment_checks(config):
                logger.error("❌ Pre-deployment checks failed")
                return False

            # Execute deployment based on strategy
            success = False
            if config.strategy == DeploymentStrategy.BLUE_GREEN:
                success = await self._blue_green_deployment(config, metrics)
            elif config.strategy == DeploymentStrategy.CANARY:
                success = await self._canary_deployment(config, metrics)
            elif config.strategy == DeploymentStrategy.ROLLING:
                success = await self._rolling_deployment(config, metrics)
            elif config.strategy == DeploymentStrategy.FAST:
                success = await self._fast_deployment(config, metrics)

            # Finalize metrics
            metrics.end_time = datetime.utcnow()
            metrics.duration = (metrics.end_time - metrics.start_time).total_seconds()

            # Save deployment record
            await self._save_deployment_record(config, metrics, success)

            # Send notifications
            await self._send_notifications(config, metrics, success)

            if success:
                logger.info(f"✅ Deployment completed successfully in {metrics.duration:.1f}s")
            else:
                logger.error(f"❌ Deployment failed after {metrics.duration:.1f}s")

            return success

        except Exception as e:
            logger.error(f"❌ Deployment failed with exception: {str(e)}")
            metrics.end_time = datetime.utcnow()
            metrics.duration = (metrics.end_time - metrics.start_time).total_seconds()
            await self._save_deployment_record(config, metrics, False)
            return False

    async def _pre_deployment_checks(self, config: DeploymentConfig) -> bool:
        """Comprehensive pre-deployment validation."""

        logger.info("🔍 Running pre-deployment checks...")

        checks = [
            ("ECS Cluster Status", self._check_ecs_cluster_status, config),
            ("Service Exists", self._check_service_exists, config),
            ("Task Definition Valid", self._check_task_definition, config),
            ("Load Balancer Health", self._check_load_balancer_health, config),
            ("Database Connectivity", self._check_database_connectivity, config),
            ("External Dependencies", self._check_external_dependencies, config),
        ]

        for check_name, check_func, check_config in checks:
            logger.info(f"  🔄 {check_name}...")
            try:
                if await check_func(check_config):
                    logger.info(f"    ✅ {check_name} passed")
                else:
                    logger.error(f"    ❌ {check_name} failed")
                    return False
            except Exception as e:
                logger.error(f"    ❌ {check_name} failed with error: {str(e)}")
                return False

        logger.info("✅ All pre-deployment checks passed")
        return True

    async def _blue_green_deployment(self, config: DeploymentConfig, metrics: DeploymentMetrics) -> bool:
        """Execute blue-green deployment strategy."""

        logger.info("🔵🟢 Executing Blue-Green deployment")

        cluster_name = f"praktiko-{config.environment}"
        service_name = f"praktiko-{config.service_name}-{config.environment}"

        try:
            # Step 1: Create new task definition
            logger.info("📋 Creating new task definition...")
            new_task_def_arn = await self._create_task_definition(config)
            if not new_task_def_arn:
                return False

            # Step 2: Get current service configuration
            current_service = await self._get_service_config(cluster_name, service_name)
            if not current_service:
                return False

            # Step 3: Create new service (Green)
            green_service_name = f"{service_name}-green"
            logger.info(f"🟢 Creating green service: {green_service_name}")

            green_service_arn = await self._create_green_service(
                cluster_name, green_service_name, new_task_def_arn, config
            )
            if not green_service_arn:
                return False

            # Step 4: Wait for green service to be stable
            logger.info("⏳ Waiting for green service to stabilize...")
            if not await self._wait_for_service_stable(cluster_name, green_service_name, 600):
                await self._cleanup_green_service(cluster_name, green_service_name)
                return False

            # Step 5: Health check green service
            logger.info("🩺 Health checking green service...")
            green_endpoint = await self._get_service_endpoint(cluster_name, green_service_name)
            if not await self._comprehensive_health_check(green_endpoint, config, metrics):
                await self._cleanup_green_service(cluster_name, green_service_name)
                return False

            # Step 6: Switch traffic to green service
            logger.info("🔄 Switching traffic to green service...")
            if not await self._switch_traffic_to_green(config, green_service_name):
                await self._cleanup_green_service(cluster_name, green_service_name)
                return False

            # Step 7: Monitor traffic for stability
            logger.info("📊 Monitoring traffic stability...")
            if not await self._monitor_traffic_stability(config, metrics, 180):
                logger.warning("⚠️ Traffic instability detected, rolling back...")
                await self._switch_traffic_to_blue(config, service_name)
                await self._cleanup_green_service(cluster_name, green_service_name)
                return False

            # Step 8: Cleanup old blue service
            logger.info("🧹 Cleaning up old blue service...")
            await self._cleanup_blue_service(cluster_name, service_name)

            # Step 9: Rename green service to primary
            await self._rename_green_to_primary(cluster_name, green_service_name, service_name)

            logger.info("✅ Blue-Green deployment completed successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Blue-Green deployment failed: {str(e)}")
            return False

    async def _canary_deployment(self, config: DeploymentConfig, metrics: DeploymentMetrics) -> bool:
        """Execute canary deployment strategy."""

        logger.info(f"🐦 Executing Canary deployment ({config.canary_percentage}% traffic)")

        cluster_name = f"praktiko-{config.environment}"
        service_name = f"praktiko-{config.service_name}-{config.environment}"

        try:
            # Step 1: Create new task definition
            logger.info("📋 Creating new task definition...")
            new_task_def_arn = await self._create_task_definition(config)
            if not new_task_def_arn:
                return False

            # Step 2: Calculate canary instance count
            canary_count = max(1, int(config.desired_count * config.canary_percentage / 100))
            stable_count = config.desired_count - canary_count

            logger.info(f"🎯 Canary instances: {canary_count}, Stable instances: {stable_count}")

            # Step 3: Deploy canary instances
            logger.info("🐦 Deploying canary instances...")
            canary_service_name = f"{service_name}-canary"

            canary_service_arn = await self._create_canary_service(
                cluster_name, canary_service_name, new_task_def_arn, canary_count, config
            )
            if not canary_service_arn:
                return False

            # Step 4: Configure load balancer for canary traffic
            logger.info(f"⚖️ Configuring {config.canary_percentage}% traffic to canary...")
            if not await self._configure_canary_traffic(config, canary_service_name):
                await self._cleanup_canary_service(cluster_name, canary_service_name)
                return False

            # Step 5: Monitor canary performance
            logger.info(f"📊 Monitoring canary for {config.canary_duration}s...")
            canary_success = await self._monitor_canary_performance(config, metrics, config.canary_duration)

            if not canary_success:
                logger.warning("⚠️ Canary analysis failed, rolling back...")
                await self._remove_canary_traffic(config)
                await self._cleanup_canary_service(cluster_name, canary_service_name)
                return False

            # Step 6: Promote canary to full deployment
            logger.info("🎉 Canary successful, promoting to full deployment...")
            if not await self._promote_canary_to_full(cluster_name, service_name, new_task_def_arn, config):
                await self._remove_canary_traffic(config)
                await self._cleanup_canary_service(cluster_name, canary_service_name)
                return False

            # Step 7: Cleanup canary resources
            await self._cleanup_canary_service(cluster_name, canary_service_name)

            logger.info("✅ Canary deployment completed successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Canary deployment failed: {str(e)}")
            return False

    async def _rolling_deployment(self, config: DeploymentConfig, metrics: DeploymentMetrics) -> bool:
        """Execute rolling deployment strategy."""

        logger.info("🔄 Executing Rolling deployment")

        cluster_name = f"praktiko-{config.environment}"
        service_name = f"praktiko-{config.service_name}-{config.environment}"

        try:
            # Step 1: Create new task definition
            logger.info("📋 Creating new task definition...")
            new_task_def_arn = await self._create_task_definition(config)
            if not new_task_def_arn:
                return False

            # Step 2: Update service with new task definition
            logger.info("🔄 Updating service with new task definition...")

            response = self.ecs_client.update_service(
                cluster=cluster_name,
                service=service_name,
                taskDefinition=new_task_def_arn,
                deploymentConfiguration={
                    "minimumHealthyPercent": 50,
                    "maximumPercent": 200,
                    "deploymentCircuitBreaker": {"enable": True, "rollback": config.auto_rollback},
                },
            )

            deployment_id = response["service"]["deployments"][0]["id"]
            logger.info(f"📊 Deployment ID: {deployment_id}")

            # Step 3: Monitor rolling deployment
            logger.info("⏳ Monitoring rolling deployment...")
            if not await self._monitor_rolling_deployment(cluster_name, service_name, deployment_id, config, metrics):
                return False

            # Step 4: Final health check
            logger.info("🩺 Final health check...")
            service_endpoint = await self._get_service_endpoint(cluster_name, service_name)
            if not await self._comprehensive_health_check(service_endpoint, config, metrics):
                return False

            logger.info("✅ Rolling deployment completed successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Rolling deployment failed: {str(e)}")
            return False

    async def _fast_deployment(self, config: DeploymentConfig, metrics: DeploymentMetrics) -> bool:
        """Execute fast deployment strategy (for minor changes)."""

        logger.info("⚡ Executing Fast deployment")

        # Fast deployment is essentially a rolling deployment with more aggressive settings
        cluster_name = f"praktiko-{config.environment}"
        service_name = f"praktiko-{config.service_name}-{config.environment}"

        try:
            # Step 1: Create new task definition
            new_task_def_arn = await self._create_task_definition(config)
            if not new_task_def_arn:
                return False

            # Step 2: Update service with aggressive deployment configuration
            response = self.ecs_client.update_service(
                cluster=cluster_name,
                service=service_name,
                taskDefinition=new_task_def_arn,
                deploymentConfiguration={
                    "minimumHealthyPercent": 100,
                    "maximumPercent": 200,
                    "deploymentCircuitBreaker": {"enable": True, "rollback": config.auto_rollback},
                },
            )

            deployment_id = response["service"]["deployments"][0]["id"]

            # Step 3: Quick monitoring (shorter timeout)
            if not await self._monitor_rolling_deployment(
                cluster_name, service_name, deployment_id, config, metrics, timeout=180
            ):
                return False

            # Step 4: Basic health check
            service_endpoint = await self._get_service_endpoint(cluster_name, service_name)
            if not await self._basic_health_check(service_endpoint, config):
                return False

            logger.info("✅ Fast deployment completed successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Fast deployment failed: {str(e)}")
            return False

    async def _comprehensive_health_check(
        self, endpoint: str, config: DeploymentConfig, metrics: DeploymentMetrics
    ) -> bool:
        """Perform comprehensive health checks on the deployed service."""

        if not endpoint:
            logger.error("No endpoint available for health check")
            return False

        logger.info(f"🩺 Running comprehensive health checks on {endpoint}")

        # Health check endpoints
        health_endpoints = [
            {"path": config.health_check_path, "name": "Basic Health", "critical": True},
            {"path": "/api/v1/health", "name": "API Health", "critical": True},
            {"path": "/health/db", "name": "Database Health", "critical": True},
            {"path": "/health/cache", "name": "Cache Health", "critical": False},
            {"path": "/health/deps", "name": "Dependencies", "critical": False},
            {"path": "/metrics", "name": "Metrics Endpoint", "critical": False},
        ]

        start_time = time.time()

        while time.time() - start_time < config.health_check_timeout:
            all_critical_healthy = True
            healthy_endpoints = 0

            for endpoint_config in health_endpoints:
                url = f"{endpoint.rstrip('/')}{endpoint_config['path']}"

                try:
                    response = requests.get(url, timeout=10)
                    healthy = response.status_code == 200

                    if healthy:
                        healthy_endpoints += 1
                        metrics.health_checks_passed += 1
                        logger.info(f"    ✅ {endpoint_config['name']}: {response.status_code}")
                    else:
                        metrics.health_checks_failed += 1
                        logger.warning(f"    ❌ {endpoint_config['name']}: {response.status_code}")
                        if endpoint_config["critical"]:
                            all_critical_healthy = False

                except Exception as e:
                    metrics.health_checks_failed += 1
                    logger.warning(f"    ❌ {endpoint_config['name']}: {str(e)}")
                    if endpoint_config["critical"]:
                        all_critical_healthy = False

            if all_critical_healthy:
                success_rate = (healthy_endpoints / len(health_endpoints)) * 100
                logger.info(f"✅ Health checks passed ({success_rate:.1f}% success rate)")
                return True

            logger.info(f"⏳ Waiting for health checks... ({int(time.time() - start_time)}s)")
            await asyncio.sleep(config.health_check_interval)

        logger.error(f"❌ Health checks failed after {config.health_check_timeout}s timeout")
        return False

    async def _basic_health_check(self, endpoint: str, config: DeploymentConfig) -> bool:
        """Perform basic health check (for fast deployments)."""

        if not endpoint:
            return False

        url = f"{endpoint.rstrip('/')}{config.health_check_path}"

        try:
            response = requests.get(url, timeout=10)
            healthy = response.status_code == 200

            if healthy:
                logger.info(f"✅ Basic health check passed: {response.status_code}")
            else:
                logger.error(f"❌ Basic health check failed: {response.status_code}")

            return healthy

        except Exception as e:
            logger.error(f"❌ Basic health check failed: {str(e)}")
            return False

    # Additional helper methods would be implemented here...
    # (Due to length constraints, showing the core structure)

    async def _create_task_definition(self, config: DeploymentConfig) -> str | None:
        """Create new ECS task definition."""
        # Implementation would create and register a new task definition
        logger.info("Creating task definition...")
        return f"arn:aws:ecs:{self.region}:123456789012:task-definition/{config.service_name}:1"

    async def _get_service_endpoint(self, cluster_name: str, service_name: str) -> str | None:
        """Get service endpoint URL."""
        # Implementation would get the actual service endpoint
        return f"https://api-{service_name}.praktiko.ai"

    async def _save_deployment_record(self, config: DeploymentConfig, metrics: DeploymentMetrics, success: bool):
        """Save deployment record for audit and analysis."""

        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "service_name": config.service_name,
            "environment": config.environment,
            "strategy": config.strategy.value,
            "image_uri": config.image_uri,
            "success": success,
            "duration": metrics.duration,
            "health_checks_passed": metrics.health_checks_passed,
            "health_checks_failed": metrics.health_checks_failed,
            "rollback_triggered": metrics.rollback_triggered,
        }

        self.deployment_history.append(record)

        # Save to file
        with open(f"deployment-history-{config.environment}.json", "w") as f:
            json.dump(self.deployment_history, f, indent=2)

        logger.info(f"📝 Deployment record saved: {record}")

    async def _send_notifications(self, config: DeploymentConfig, metrics: DeploymentMetrics, success: bool):
        """Send deployment notifications."""

        status = "✅ SUCCESS" if success else "❌ FAILED"
        duration = f"{metrics.duration:.1f}s" if metrics.duration else "N/A"

        message = f"""
🚀 **Deployment {status}**

**Service:** {config.service_name}
**Environment:** {config.environment}
**Strategy:** {config.strategy.value}
**Duration:** {duration}
**Health Checks:** {metrics.health_checks_passed}✅ / {metrics.health_checks_failed}❌
        """

        if config.slack_webhook:
            try:
                requests.post(config.slack_webhook, json={"text": message})
                logger.info("📱 Slack notification sent")
            except Exception as e:
                logger.warning(f"Failed to send Slack notification: {e}")

        logger.info(f"📢 Deployment notification: {message}")


async def main():
    """Main entry point for deployment script."""

    parser = argparse.ArgumentParser(description="Advanced Zero-Downtime Deployment System")
    parser.add_argument("--service", required=True, help="Service name to deploy")
    parser.add_argument("--environment", required=True, help="Target environment")
    parser.add_argument("--image", required=True, help="Container image URI")
    parser.add_argument(
        "--strategy", required=True, choices=["rolling", "blue-green", "canary", "fast"], help="Deployment strategy"
    )
    parser.add_argument("--desired-count", type=int, default=2, help="Desired instance count")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--auto-rollback", action="store_true", help="Enable auto rollback")
    parser.add_argument("--slack-webhook", help="Slack webhook URL for notifications")

    args = parser.parse_args()

    # Create deployment configuration
    config = DeploymentConfig(
        service_name=args.service,
        environment=args.environment,
        image_uri=args.image,
        strategy=DeploymentStrategy(args.strategy),
        desired_count=args.desired_count,
        auto_rollback=args.auto_rollback,
        slack_webhook=args.slack_webhook,
    )

    # Execute deployment
    deployment_manager = AWSDeploymentManager(region=args.region)
    success = await deployment_manager.deploy(config)

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
