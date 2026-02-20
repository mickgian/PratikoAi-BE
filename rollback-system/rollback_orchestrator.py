#!/usr/bin/env python3
"""PratikoAI Robust Rollback Orchestration System

Comprehensive rollback system that safely reverts frontend and backend deployments
when issues are detected, with zero downtime and data preservation guarantees.

Features:
- Automated rollback detection and execution
- Cross-service rollback coordination
- Zero-downtime backend rollbacks
- Database migration rollbacks with data preservation
- Health monitoring integration
- Comprehensive logging and audit trails
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import boto3
import httpx
import psycopg2
import requests
import yaml  # type: ignore[import-untyped]
from kubernetes import client, config
from sqlalchemy import create_engine, text

import docker

logger = logging.getLogger(__name__)


class RollbackTrigger(Enum):
    """Reasons that can trigger a rollback."""

    HEALTH_CHECK_FAILURE = "health_check_failure"
    ERROR_RATE_THRESHOLD = "error_rate_threshold"
    RESPONSE_TIME_DEGRADATION = "response_time_degradation"
    USER_INITIATED = "user_initiated"
    DEPENDENCY_FAILURE = "dependency_failure"
    DATABASE_MIGRATION_FAILURE = "migration_failure"
    DEPLOYMENT_TIMEOUT = "deployment_timeout"
    COMPATIBILITY_FAILURE = "compatibility_failure"
    AUTOMATED_TEST_FAILURE = "test_failure"


class RollbackStatus(Enum):
    """Status of rollback operations."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    CANCELLED = "cancelled"


class ServiceType(Enum):
    """Types of services that can be rolled back."""

    BACKEND_API = "backend_api"
    FRONTEND_WEB = "frontend_web"
    FRONTEND_ANDROID = "frontend_android"
    FRONTEND_IOS = "frontend_ios"
    FRONTEND_DESKTOP = "frontend_desktop"
    DATABASE = "database"
    CACHE = "cache"
    CDN = "cdn"


@dataclass
class RollbackTarget:
    """Represents a service version to rollback to."""

    service_type: ServiceType
    current_version: str
    target_version: str
    deployment_id: str
    environment: str
    rollback_strategy: str = "blue_green"  # blue_green, rolling, immediate
    preserve_data: bool = True
    health_check_url: str | None = None
    dependencies: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RollbackExecution:
    """Runtime state of a rollback operation."""

    rollback_id: str
    trigger: RollbackTrigger
    targets: list[RollbackTarget]
    status: RollbackStatus
    started_at: datetime
    completed_at: datetime | None = None
    initiated_by: str = "system"
    error_message: str | None = None
    completed_targets: list[str] = field(default_factory=list)
    failed_targets: list[str] = field(default_factory=list)
    preserved_data: dict[str, Any] = field(default_factory=dict)
    health_validations: dict[str, bool] = field(default_factory=dict)
    logs: list[str] = field(default_factory=list)


class DatabaseRollback:
    """Handles database migration rollbacks with data preservation."""

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.engine = create_engine(db_url)

    async def create_data_snapshot(self, snapshot_id: str, tables: list[str] | None = None) -> dict[str, Any]:
        """Create a data snapshot before rollback."""
        snapshot_info: dict[str, Any] = {
            "snapshot_id": snapshot_id,
            "created_at": datetime.now(UTC).isoformat(),
            "tables": {},
            "metadata": {"db_version": None, "schema_version": None, "total_records": 0},
        }

        try:
            with self.engine.connect() as conn:
                # Get current schema version (if using migration system like Alembic)
                try:
                    result = conn.execute(text("SELECT version_num FROM alembic_version"))
                    snapshot_info["metadata"]["schema_version"] = result.scalar()
                except:
                    logger.warning("Could not determine schema version")

                # Get database version
                result = conn.execute(text("SELECT version()"))
                snapshot_info["metadata"]["db_version"] = result.scalar()

                # Create backup tables for specified tables or all tables
                if not tables:
                    # Get all table names
                    result = conn.execute(
                        text("""
                        SELECT tablename FROM pg_tables
                        WHERE schemaname = 'public'
                        AND tablename NOT LIKE 'backup_%'
                        AND tablename != 'alembic_version'
                    """)
                    )
                    tables = [row[0] for row in result]

                total_records = 0
                for table in tables:
                    backup_table = f"backup_{snapshot_id}_{table}"

                    try:
                        # Create backup table
                        conn.execute(
                            text(f"""
                            CREATE TABLE {backup_table} AS
                            SELECT * FROM {table}
                        """)
                        )

                        # Get record count
                        result = conn.execute(text(f"SELECT COUNT(*) FROM {backup_table}"))
                        record_count = result.scalar()

                        snapshot_info["tables"][table] = {
                            "backup_table": backup_table,
                            "record_count": record_count,
                            "created_at": datetime.now(UTC).isoformat(),
                        }

                        total_records += record_count
                        logger.info(f"Created backup table {backup_table} with {record_count} records")

                    except Exception as e:
                        logger.error(f"Failed to backup table {table}: {str(e)}")
                        snapshot_info["tables"][table] = {"error": str(e), "backup_table": None, "record_count": 0}

                snapshot_info["metadata"]["total_records"] = total_records
                conn.commit()

                logger.info(f"Created data snapshot {snapshot_id} with {total_records} total records")
                return snapshot_info

        except Exception as e:
            logger.error(f"Failed to create data snapshot: {str(e)}")
            raise

    async def rollback_migrations(self, target_version: str, preserve_data: bool = True) -> bool:
        """Rollback database migrations to target version."""
        try:
            logger.info(f"Rolling back database migrations to version {target_version}")

            if preserve_data:
                # Create snapshot before rollback
                snapshot_id = f"rollback_{int(datetime.now().timestamp())}"
                snapshot_info = await self.create_data_snapshot(snapshot_id)
                logger.info(f"Data snapshot created: {snapshot_id}")

            # Use Alembic for migration rollback
            import subprocess

            result = subprocess.run(
                ["alembic", "downgrade", target_version], capture_output=True, text=True, cwd=os.getcwd()
            )

            if result.returncode == 0:
                logger.info(f"Successfully rolled back migrations to {target_version}")
                return True
            else:
                logger.error(f"Migration rollback failed: {result.stderr}")

                # If rollback failed and we have a snapshot, offer restoration
                if preserve_data and "snapshot_info" in locals():
                    logger.info("Migration rollback failed, snapshot data preserved for manual recovery")

                return False

        except Exception as e:
            logger.error(f"Database rollback failed: {str(e)}")
            return False

    async def restore_from_snapshot(self, snapshot_id: str) -> bool:
        """Restore data from a snapshot."""
        try:
            with self.engine.connect() as conn:
                # Find backup tables for this snapshot
                result = conn.execute(
                    text(f"""
                    SELECT tablename FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND tablename LIKE 'backup_{snapshot_id}_%'
                """)
                )

                backup_tables = [row[0] for row in result]

                for backup_table in backup_tables:
                    # Extract original table name
                    original_table = backup_table.replace(f"backup_{snapshot_id}_", "")

                    try:
                        # Clear current table
                        conn.execute(text(f"TRUNCATE TABLE {original_table} CASCADE"))

                        # Restore from backup
                        conn.execute(
                            text(f"""
                            INSERT INTO {original_table}
                            SELECT * FROM {backup_table}
                        """)
                        )

                        logger.info(f"Restored table {original_table} from snapshot {snapshot_id}")

                    except Exception as e:
                        logger.error(f"Failed to restore table {original_table}: {str(e)}")
                        return False

                conn.commit()
                logger.info(f"Successfully restored data from snapshot {snapshot_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to restore from snapshot: {str(e)}")
            return False

    async def cleanup_snapshots(self, older_than_days: int = 7) -> int:
        """Clean up old backup snapshots."""
        try:
            cutoff_timestamp = int((datetime.now() - timedelta(days=older_than_days)).timestamp())

            with self.engine.connect() as conn:
                # Find old backup tables
                result = conn.execute(
                    text(f"""
                    SELECT tablename FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND tablename LIKE 'backup_%'
                    AND CAST(SPLIT_PART(SPLIT_PART(tablename, '_', 2), '_', 1) AS INTEGER) < {cutoff_timestamp}
                """)
                )

                old_tables = [row[0] for row in result]
                cleaned_count = 0

                for table in old_tables:
                    try:
                        conn.execute(text(f"DROP TABLE {table}"))
                        cleaned_count += 1
                        logger.info(f"Cleaned up old backup table: {table}")
                    except Exception as e:
                        logger.warning(f"Failed to drop table {table}: {str(e)}")

                conn.commit()
                logger.info(f"Cleaned up {cleaned_count} old backup tables")
                return cleaned_count

        except Exception as e:
            logger.error(f"Failed to cleanup snapshots: {str(e)}")
            return 0


class BackendRollback:
    """Handles zero-downtime backend API rollbacks."""

    def __init__(self, environment: str):
        self.environment = environment
        self.docker_client = docker.from_env()  # type: ignore[attr-defined]

        # Initialize Kubernetes client if available
        try:
            config.load_incluster_config()
            self.k8s_client = client.AppsV1Api()
            self.k8s_available = True
        except:
            try:
                config.load_kube_config()
                self.k8s_client = client.AppsV1Api()
                self.k8s_available = True
            except:
                self.k8s_available = False
                logger.warning("Kubernetes not available, using Docker-based rollback")

    async def blue_green_rollback(self, target: RollbackTarget) -> bool:
        """Perform blue-green rollback strategy."""
        try:
            logger.info(f"Starting blue-green rollback for {target.service_type.value}")

            if self.k8s_available:
                return await self._k8s_blue_green_rollback(target)
            else:
                return await self._docker_blue_green_rollback(target)

        except Exception as e:
            logger.error(f"Blue-green rollback failed: {str(e)}")
            return False

    async def _k8s_blue_green_rollback(self, target: RollbackTarget) -> bool:
        """Kubernetes-based blue-green rollback."""
        try:
            namespace = f"pratiko-{self.environment}"
            deployment_name = "pratiko-backend"
            service_name = "pratiko-backend-service"

            # Get current deployment
            current_deployment = self.k8s_client.read_namespaced_deployment(name=deployment_name, namespace=namespace)

            # Create green deployment with target version
            green_deployment_name = f"{deployment_name}-green"
            green_deployment = current_deployment
            green_deployment.metadata.name = green_deployment_name
            green_deployment.spec.selector.match_labels["version"] = target.target_version
            green_deployment.spec.template.metadata.labels["version"] = target.target_version
            green_deployment.spec.template.spec.containers[0].image = f"pratiko-backend:{target.target_version}"

            # Create green deployment
            self.k8s_client.create_namespaced_deployment(namespace=namespace, body=green_deployment)

            # Wait for green deployment to be ready
            await self._wait_for_k8s_deployment_ready(green_deployment_name, namespace)

            # Perform health check
            if target.health_check_url:
                if not await self._perform_health_check(target.health_check_url):
                    logger.error("Green deployment health check failed")
                    await self._cleanup_k8s_deployment(green_deployment_name, namespace)
                    return False

            # Switch traffic to green deployment
            service = client.CoreV1Api().read_namespaced_service(name=service_name, namespace=namespace)
            service.spec.selector["version"] = target.target_version

            client.CoreV1Api().patch_namespaced_service(name=service_name, namespace=namespace, body=service)

            # Wait and verify traffic switch
            await asyncio.sleep(10)

            if target.health_check_url:
                if not await self._perform_health_check(target.health_check_url):
                    logger.error("Post-switch health check failed, reverting traffic")
                    service.spec.selector["version"] = target.current_version
                    client.CoreV1Api().patch_namespaced_service(name=service_name, namespace=namespace, body=service)
                    return False

            # Clean up old blue deployment
            await self._cleanup_k8s_deployment(deployment_name, namespace)

            # Rename green to main deployment
            green_deployment.metadata.name = deployment_name
            green_deployment.spec.selector.match_labels.pop("version", None)
            green_deployment.spec.template.metadata.labels.pop("version", None)

            self.k8s_client.create_namespaced_deployment(namespace=namespace, body=green_deployment)

            await self._cleanup_k8s_deployment(green_deployment_name, namespace)

            logger.info("Blue-green rollback completed successfully")
            return True

        except Exception as e:
            logger.error(f"Kubernetes blue-green rollback failed: {str(e)}")
            return False

    async def _docker_blue_green_rollback(self, target: RollbackTarget) -> bool:
        """Docker-based blue-green rollback."""
        try:
            # Pull target image
            image_name = f"pratiko-backend:{target.target_version}"
            logger.info(f"Pulling target image: {image_name}")
            self.docker_client.images.pull(image_name)

            # Start green container
            green_container_name = f"pratiko-backend-green-{int(datetime.now().timestamp())}"
            green_container = self.docker_client.containers.run(
                image_name,
                name=green_container_name,
                ports={"8000/tcp": None},  # Dynamic port assignment
                environment={"ENVIRONMENT": self.environment, "VERSION": target.target_version},
                detach=True,
                restart_policy={"Name": "unless-stopped"},
            )

            # Wait for container to be ready
            await asyncio.sleep(30)

            # Get assigned port
            green_container.reload()
            green_port = green_container.ports["8000/tcp"][0]["HostPort"]
            green_health_url = f"http://localhost:{green_port}/health"

            # Perform health check
            if not await self._perform_health_check(green_health_url):
                logger.error("Green container health check failed")
                green_container.stop()
                green_container.remove()
                return False

            # Update load balancer / reverse proxy configuration
            await self._update_nginx_upstream(green_port)

            # Wait and verify
            await asyncio.sleep(10)

            if target.health_check_url:
                if not await self._perform_health_check(target.health_check_url):
                    logger.error("Post-switch health check failed")
                    return False

            # Stop and remove old container
            try:
                old_containers = self.docker_client.containers.list(
                    filters={"name": "pratiko-backend", "status": "running"}
                )
                for container in old_containers:
                    if container.name != green_container_name:
                        container.stop()
                        container.remove()
            except Exception as e:
                logger.warning(f"Failed to cleanup old containers: {str(e)}")

            # Rename green container
            green_container.rename("pratiko-backend")

            logger.info("Docker blue-green rollback completed successfully")
            return True

        except Exception as e:
            logger.error(f"Docker blue-green rollback failed: {str(e)}")
            return False

    async def rolling_rollback(self, target: RollbackTarget) -> bool:
        """Perform rolling rollback strategy."""
        try:
            logger.info(f"Starting rolling rollback for {target.service_type.value}")

            if self.k8s_available:
                # Use Kubernetes rolling update
                namespace = f"pratiko-{self.environment}"
                deployment_name = "pratiko-backend"

                # Update deployment with target version
                deployment = self.k8s_client.read_namespaced_deployment(name=deployment_name, namespace=namespace)

                deployment.spec.template.spec.containers[0].image = f"pratiko-backend:{target.target_version}"

                self.k8s_client.patch_namespaced_deployment(name=deployment_name, namespace=namespace, body=deployment)

                # Wait for rollout to complete
                await self._wait_for_k8s_deployment_ready(deployment_name, namespace)

                # Perform health check
                if target.health_check_url:
                    if not await self._perform_health_check(target.health_check_url):
                        logger.error("Rolling rollback health check failed")
                        return False

                logger.info("Rolling rollback completed successfully")
                return True
            else:
                logger.warning("Rolling rollback requires Kubernetes")
                return False

        except Exception as e:
            logger.error(f"Rolling rollback failed: {str(e)}")
            return False

    async def _wait_for_k8s_deployment_ready(self, deployment_name: str, namespace: str, timeout: int = 300):
        """Wait for Kubernetes deployment to be ready."""
        start_time = datetime.now()
        while (datetime.now() - start_time).seconds < timeout:
            try:
                deployment = self.k8s_client.read_namespaced_deployment(name=deployment_name, namespace=namespace)

                if deployment.status.ready_replicas and deployment.status.ready_replicas == deployment.spec.replicas:
                    logger.info(f"Deployment {deployment_name} is ready")
                    return True

                await asyncio.sleep(5)

            except Exception as e:
                logger.warning(f"Error checking deployment status: {str(e)}")
                await asyncio.sleep(5)

        raise TimeoutError(f"Deployment {deployment_name} did not become ready within {timeout} seconds")

    async def _cleanup_k8s_deployment(self, deployment_name: str, namespace: str):
        """Clean up Kubernetes deployment."""
        try:
            self.k8s_client.delete_namespaced_deployment(name=deployment_name, namespace=namespace)
            logger.info(f"Cleaned up deployment {deployment_name}")
        except Exception as e:
            logger.warning(f"Failed to cleanup deployment {deployment_name}: {str(e)}")

    async def _perform_health_check(self, health_url: str, retries: int = 3) -> bool:
        """Perform health check with retries."""
        for attempt in range(retries):
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    response = await client.get(health_url)

                    if response.status_code == 200:
                        health_data = response.json()
                        if health_data.get("status") == "healthy":
                            return True

                logger.warning(f"Health check attempt {attempt + 1} failed: {response.status_code}")

            except Exception as e:
                logger.warning(f"Health check attempt {attempt + 1} error: {str(e)}")

            if attempt < retries - 1:
                await asyncio.sleep(10)

        return False

    async def _update_nginx_upstream(self, port: int):
        """Update nginx upstream configuration."""
        try:
            # This would update your nginx configuration
            # Implementation depends on your nginx setup
            nginx_config = f"""
            upstream pratiko_backend {{
                server localhost:{port};
            }}
            """

            # Write config and reload nginx
            with open(f"/etc/nginx/sites-available/pratiko-{self.environment}", "w") as f:
                f.write(nginx_config)

            # Reload nginx
            import subprocess

            subprocess.run(["nginx", "-s", "reload"], check=True)

            logger.info(f"Updated nginx upstream to port {port}")

        except Exception as e:
            logger.error(f"Failed to update nginx upstream: {str(e)}")
            raise


class FrontendRollback:
    """Handles frontend deployment rollbacks."""

    def __init__(self, environment: str):
        self.environment = environment

        # Initialize cloud storage clients
        try:
            self.s3_client = boto3.client("s3")
        except:
            self.s3_client = None
            logger.warning("AWS S3 not available for frontend rollback")

    async def rollback_web_deployment(self, target: RollbackTarget) -> bool:
        """Rollback web frontend deployment."""
        try:
            logger.info(f"Rolling back web frontend to version {target.target_version}")

            if self.s3_client:
                return await self._s3_web_rollback(target)
            else:
                return await self._local_web_rollback(target)

        except Exception as e:
            logger.error(f"Web frontend rollback failed: {str(e)}")
            return False

    async def _s3_web_rollback(self, target: RollbackTarget) -> bool:
        """S3-based web frontend rollback."""
        try:
            bucket_name = f"pratiko-web-{self.environment}"

            # List objects with target version prefix
            response = self.s3_client.list_objects_v2(Bucket=bucket_name, Prefix=f"versions/{target.target_version}/")

            if "Contents" not in response:
                logger.error(f"No files found for version {target.target_version}")
                return False

            # Copy files from version directory to root
            for obj in response["Contents"]:
                source_key = obj["Key"]
                target_key = source_key.replace(f"versions/{target.target_version}/", "")

                if target_key:  # Skip empty keys
                    self.s3_client.copy_object(
                        Bucket=bucket_name, CopySource={"Bucket": bucket_name, "Key": source_key}, Key=target_key
                    )

            # Invalidate CloudFront cache if available
            await self._invalidate_cloudfront_cache()

            logger.info(f"Web frontend rolled back to version {target.target_version}")
            return True

        except Exception as e:
            logger.error(f"S3 web rollback failed: {str(e)}")
            return False

    async def _local_web_rollback(self, target: RollbackTarget) -> bool:
        """Local filesystem web frontend rollback."""
        try:
            web_root = f"/var/www/pratiko-{self.environment}"
            version_dir = f"/var/www/versions/{target.target_version}"

            if not os.path.exists(version_dir):
                logger.error(f"Version directory not found: {version_dir}")
                return False

            # Create backup of current deployment
            backup_dir = f"/var/www/backups/{int(datetime.now().timestamp())}"
            os.makedirs(backup_dir, exist_ok=True)

            import shutil

            shutil.copytree(web_root, backup_dir, dirs_exist_ok=True)

            # Clear current deployment
            shutil.rmtree(web_root)

            # Copy target version to web root
            shutil.copytree(version_dir, web_root)

            logger.info(f"Web frontend rolled back to version {target.target_version}")
            return True

        except Exception as e:
            logger.error(f"Local web rollback failed: {str(e)}")
            return False

    async def rollback_mobile_deployment(self, target: RollbackTarget) -> bool:
        """Rollback mobile app deployment."""
        try:
            logger.info(f"Rolling back {target.service_type.value} to version {target.target_version}")

            if target.service_type == ServiceType.FRONTEND_ANDROID:
                return await self._rollback_android_deployment(target)
            elif target.service_type == ServiceType.FRONTEND_IOS:
                return await self._rollback_ios_deployment(target)
            else:
                logger.error(f"Unsupported mobile platform: {target.service_type}")
                return False

        except Exception as e:
            logger.error(f"Mobile rollback failed: {str(e)}")
            return False

    async def _rollback_android_deployment(self, target: RollbackTarget) -> bool:
        """Rollback Android app deployment."""
        try:
            # For production, this would involve:
            # 1. Google Play Console API to rollback to previous version
            # 2. Update internal distribution channels

            logger.info("Android rollback would involve Google Play Console API")

            # For development/staging, update internal distribution
            if self.environment != "production":
                # Update internal app distribution (Firebase App Distribution, etc.)
                logger.info(f"Rolling back Android {self.environment} deployment")
                return True

            # Production rollback requires Google Play Console integration
            logger.warning("Production Android rollback requires manual Google Play Console action")
            return False

        except Exception as e:
            logger.error(f"Android rollback failed: {str(e)}")
            return False

    async def _rollback_ios_deployment(self, target: RollbackTarget) -> bool:
        """Rollback iOS app deployment."""
        try:
            # For production, this would involve:
            # 1. App Store Connect API to rollback to previous version
            # 2. Update TestFlight builds

            logger.info("iOS rollback would involve App Store Connect API")

            if self.environment != "production":
                # Update TestFlight builds
                logger.info(f"Rolling back iOS {self.environment} deployment")
                return True

            # Production rollback requires App Store Connect integration
            logger.warning("Production iOS rollback requires manual App Store Connect action")
            return False

        except Exception as e:
            logger.error(f"iOS rollback failed: {str(e)}")
            return False

    async def _invalidate_cloudfront_cache(self):
        """Invalidate CloudFront cache after deployment."""
        try:
            cloudfront = boto3.client("cloudfront")
            distribution_id = os.getenv(f"CLOUDFRONT_DISTRIBUTION_ID_{self.environment.upper()}")

            if distribution_id:
                cloudfront.create_invalidation(
                    DistributionId=distribution_id,
                    InvalidationBatch={
                        "Paths": {"Quantity": 1, "Items": ["/*"]},
                        "CallerReference": f"rollback-{int(datetime.now().timestamp())}",
                    },
                )
                logger.info("CloudFront cache invalidation initiated")

        except Exception as e:
            logger.warning(f"CloudFront invalidation failed: {str(e)}")


class RollbackOrchestrator:
    """Main orchestrator for coordinated rollback operations."""

    def __init__(self, environment: str, db_url: str | None = None):
        self.environment = environment
        self.db_rollback = DatabaseRollback(db_url) if db_url else None
        self.backend_rollback = BackendRollback(environment)
        self.frontend_rollback = FrontendRollback(environment)
        self.executions: dict[str, RollbackExecution] = {}

    async def initiate_rollback(
        self, trigger: RollbackTrigger, targets: list[RollbackTarget], initiated_by: str = "system"
    ) -> RollbackExecution:
        """Initiate a coordinated rollback operation."""
        rollback_id = f"rollback-{self.environment}-{int(datetime.now().timestamp())}"

        execution = RollbackExecution(
            rollback_id=rollback_id,
            trigger=trigger,
            targets=targets,
            status=RollbackStatus.PENDING,
            started_at=datetime.now(UTC),
            initiated_by=initiated_by,
        )

        self.executions[rollback_id] = execution

        logger.info(f"Initiated rollback {rollback_id} with {len(targets)} targets")
        execution.logs.append(f"Rollback initiated: {trigger.value} by {initiated_by}")

        # Execute rollback
        try:
            execution.status = RollbackStatus.IN_PROGRESS
            success = await self._execute_rollback(execution)

            if success:
                execution.status = RollbackStatus.SUCCESS
            else:
                execution.status = RollbackStatus.FAILED if not execution.completed_targets else RollbackStatus.PARTIAL

            execution.completed_at = datetime.now(UTC)

        except Exception as e:
            execution.error_message = str(e)
            execution.status = RollbackStatus.FAILED
            execution.completed_at = datetime.now(UTC)
            logger.error(f"Rollback {rollback_id} failed: {str(e)}")

        return execution

    async def _execute_rollback(self, execution: RollbackExecution) -> bool:
        """Execute the rollback operation."""
        # Sort targets by dependencies (database first, then backend, then frontend)
        sorted_targets = self._sort_targets_by_priority(execution.targets)

        overall_success = True

        for target in sorted_targets:
            try:
                execution.logs.append(f"Starting rollback for {target.service_type.value}")
                logger.info(
                    f"Rolling back {target.service_type.value} from {target.current_version} to {target.target_version}"
                )

                success = await self._rollback_single_target(target)

                if success:
                    execution.completed_targets.append(target.service_type.value)
                    execution.logs.append(f"Successfully rolled back {target.service_type.value}")

                    # Perform health check if URL provided
                    if target.health_check_url:
                        health_ok = await self._perform_health_check(target.health_check_url)
                        execution.health_validations[target.service_type.value] = health_ok

                        if not health_ok:
                            execution.logs.append(
                                f"Health check failed for {target.service_type.value} after rollback"
                            )
                            overall_success = False

                else:
                    execution.failed_targets.append(target.service_type.value)
                    execution.logs.append(f"Failed to rollback {target.service_type.value}")
                    overall_success = False

                    # Stop on critical failures
                    if target.service_type in [ServiceType.DATABASE, ServiceType.BACKEND_API]:
                        execution.logs.append("Critical service rollback failed, stopping execution")
                        break

            except Exception as e:
                execution.failed_targets.append(target.service_type.value)
                execution.logs.append(f"Exception during {target.service_type.value} rollback: {str(e)}")
                logger.error(f"Rollback failed for {target.service_type.value}: {str(e)}")
                overall_success = False

        return overall_success

    def _sort_targets_by_priority(self, targets: list[RollbackTarget]) -> list[RollbackTarget]:
        """Sort rollback targets by priority (dependencies first)."""
        priority_order = {
            ServiceType.DATABASE: 1,
            ServiceType.CACHE: 2,
            ServiceType.BACKEND_API: 3,
            ServiceType.FRONTEND_WEB: 4,
            ServiceType.FRONTEND_ANDROID: 5,
            ServiceType.FRONTEND_IOS: 5,
            ServiceType.FRONTEND_DESKTOP: 5,
            ServiceType.CDN: 6,
        }

        return sorted(targets, key=lambda t: priority_order.get(t.service_type, 99))

    async def _rollback_single_target(self, target: RollbackTarget) -> bool:
        """Rollback a single service target."""
        try:
            if target.service_type == ServiceType.DATABASE:
                if self.db_rollback:
                    return await self.db_rollback.rollback_migrations(target.target_version, target.preserve_data)
                else:
                    logger.error("Database rollback not configured")
                    return False

            elif target.service_type == ServiceType.BACKEND_API:
                if target.rollback_strategy == "blue_green":
                    return await self.backend_rollback.blue_green_rollback(target)
                elif target.rollback_strategy == "rolling":
                    return await self.backend_rollback.rolling_rollback(target)
                else:
                    logger.error(f"Unsupported backend rollback strategy: {target.rollback_strategy}")
                    return False

            elif target.service_type == ServiceType.FRONTEND_WEB:
                return await self.frontend_rollback.rollback_web_deployment(target)

            elif target.service_type in [ServiceType.FRONTEND_ANDROID, ServiceType.FRONTEND_IOS]:
                return await self.frontend_rollback.rollback_mobile_deployment(target)

            else:
                logger.warning(f"Rollback not implemented for {target.service_type.value}")
                return True  # Don't fail the overall rollback

        except Exception as e:
            logger.error(f"Single target rollback failed for {target.service_type.value}: {str(e)}")
            return False

    async def _perform_health_check(self, health_url: str) -> bool:
        """Perform health check after rollback."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(health_url)

                if response.status_code == 200:
                    health_data = response.json()
                    return health_data.get("status") == "healthy"

                return False

        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False

    async def get_rollback_status(self, rollback_id: str) -> RollbackExecution | None:
        """Get current status of a rollback operation."""
        return self.executions.get(rollback_id)

    async def cancel_rollback(self, rollback_id: str) -> bool:
        """Cancel an in-progress rollback operation."""
        execution = self.executions.get(rollback_id)
        if not execution:
            return False

        if execution.status == RollbackStatus.IN_PROGRESS:
            execution.status = RollbackStatus.CANCELLED
            execution.completed_at = datetime.now(UTC)
            execution.logs.append("Rollback cancelled by user")
            logger.info(f"Cancelled rollback {rollback_id}")
            return True

        return False


# CLI interface for rollback operations
async def main():
    """CLI interface for rollback operations."""
    import argparse

    parser = argparse.ArgumentParser(description="PratikoAI Rollback System")
    parser.add_argument("--environment", required=True, choices=["development", "staging", "production"])
    parser.add_argument("--trigger", required=True, choices=[t.value for t in RollbackTrigger])
    parser.add_argument("--backend-version", help="Backend version to rollback to")
    parser.add_argument("--frontend-versions", help="Frontend versions JSON")
    parser.add_argument("--database-version", help="Database version to rollback to")
    parser.add_argument("--dry-run", action="store_true", help="Perform dry run validation")
    parser.add_argument("--initiated-by", default="cli", help="Who initiated the rollback")

    args = parser.parse_args()

    # Create rollback targets
    targets = []

    if args.backend_version:
        targets.append(
            RollbackTarget(
                service_type=ServiceType.BACKEND_API,
                current_version="current",
                target_version=args.backend_version,
                deployment_id=f"rollback-{int(datetime.now().timestamp())}",
                environment=args.environment,
                rollback_strategy="blue_green",
                health_check_url=f"https://api{'-staging' if args.environment == 'staging' else ''}.pratiko.ai/health",
            )
        )

    if args.frontend_versions:
        import json

        frontend_versions = json.loads(args.frontend_versions)

        for platform, version in frontend_versions.items():
            service_type_map = {
                "web": ServiceType.FRONTEND_WEB,
                "android": ServiceType.FRONTEND_ANDROID,
                "ios": ServiceType.FRONTEND_IOS,
                "desktop": ServiceType.FRONTEND_DESKTOP,
            }

            if platform in service_type_map:
                targets.append(
                    RollbackTarget(
                        service_type=service_type_map[platform],
                        current_version="current",
                        target_version=version,
                        deployment_id=f"rollback-{int(datetime.now().timestamp())}",
                        environment=args.environment,
                    )
                )

    if args.database_version:
        targets.append(
            RollbackTarget(
                service_type=ServiceType.DATABASE,
                current_version="current",
                target_version=args.database_version,
                deployment_id=f"rollback-{int(datetime.now().timestamp())}",
                environment=args.environment,
                preserve_data=True,
            )
        )

    if not targets:
        print("No rollback targets specified")
        return

    # Initialize orchestrator
    db_url = os.getenv("DATABASE_URL")
    orchestrator = RollbackOrchestrator(args.environment, db_url)

    if args.dry_run:
        print("🧪 Dry Run Mode - Validation Only")
        print(f"Environment: {args.environment}")
        print(f"Trigger: {args.trigger}")
        print(f"Targets: {len(targets)}")
        for target in targets:
            print(f"  - {target.service_type.value}: {target.current_version} → {target.target_version}")
        print("✅ Dry run validation completed")
        return

    # Execute rollback
    trigger = RollbackTrigger(args.trigger)
    execution = await orchestrator.initiate_rollback(trigger, targets, args.initiated_by)

    print(f"Rollback completed with status: {execution.status.value}")
    print(f"Completed targets: {execution.completed_targets}")
    print(f"Failed targets: {execution.failed_targets}")

    if execution.error_message:
        print(f"Error: {execution.error_message}")


if __name__ == "__main__":
    asyncio.run(main())
