#!/usr/bin/env python3
"""Adaptive Deployment Engine for PratikoAI
=========================================

This module implements a self-learning deployment system that adapts to different
environments and conditions, optimizing deployment strategies based on historical
data and current system state.

Key Features:
- Environment auto-detection with fallback mechanisms
- Dynamic resource allocation based on real-time system load
- Machine learning-based strategy optimization
- Comprehensive decision logging and reporting
- Failure pattern recognition and mitigation
"""

import asyncio
import json
import logging
import os
import platform
import sqlite3
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
import joblib
import numpy as np
import psutil
import yaml
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler


class EnvironmentType(Enum):
    """Enumeration of supported deployment environments."""

    LOCAL = "local"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    UNKNOWN = "unknown"


class DeploymentStrategy(Enum):
    """Available deployment strategies with risk/reward profiles."""

    CONSERVATIVE = "conservative"  # Slow, safe, minimal resource usage
    BALANCED = "balanced"  # Standard approach, moderate resources
    AGGRESSIVE = "aggressive"  # Fast, high resource usage, higher risk
    ADAPTIVE = "adaptive"  # ML-determined optimal strategy


@dataclass
class SystemMetrics:
    """Current system performance and resource metrics."""

    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    load_average: float
    network_latency: float
    available_memory_gb: float
    free_disk_gb: float
    timestamp: datetime


@dataclass
class DeploymentContext:
    """Complete context for deployment decision making."""

    environment: EnvironmentType
    system_metrics: SystemMetrics
    previous_deployments: list["DeploymentRecord"]
    target_services: list[str]
    deployment_size: str  # small, medium, large
    time_constraints: int | None  # minutes
    rollback_capability: bool


@dataclass
class DeploymentRecord:
    """Historical record of a deployment attempt."""

    id: str
    timestamp: datetime
    environment: str
    strategy: str
    duration_minutes: float
    success: bool
    resource_usage: dict[str, float]
    error_message: str | None
    system_state_before: dict[str, float]
    system_state_after: dict[str, float]
    services_deployed: list[str]
    rollback_required: bool


class EnvironmentDetector:
    """Intelligent environment detection using multiple signals.

    Detection Strategy:
    1. Check explicit environment variables
    2. Analyze network configuration and accessible services
    3. Examine file system structure and configuration files
    4. Use hostname patterns and domain resolution
    5. Fallback to interactive detection
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.EnvironmentDetector")

    async def detect_environment(self) -> EnvironmentType:
        """Detect the current environment using multiple detection methods.

        Returns:
            EnvironmentType: The detected environment with confidence scoring
        """
        detection_methods = [
            self._detect_from_environment_variables,
            self._detect_from_network_topology,
            self._detect_from_filesystem,
            self._detect_from_running_services,
            self._detect_from_hostname_patterns,
        ]

        confidence_scores = {}

        for method in detection_methods:
            try:
                result = await method()
                if result:
                    env_type, confidence = result
                    if env_type not in confidence_scores:
                        confidence_scores[env_type] = []
                    confidence_scores[env_type].append(confidence)
                    self.logger.debug(
                        f"Detection method {method.__name__} suggests {env_type} with confidence {confidence}"
                    )
            except Exception as e:
                self.logger.warning(f"Detection method {method.__name__} failed: {e}")

        if not confidence_scores:
            self.logger.warning("All detection methods failed, defaulting to LOCAL")
            return EnvironmentType.LOCAL

        # Calculate weighted average confidence for each environment
        final_scores = {}
        for env_type, scores in confidence_scores.items():
            final_scores[env_type] = sum(scores) / len(scores)

        # Return environment with highest confidence
        best_environment = max(final_scores.items(), key=lambda x: x[1])
        self.logger.info(f"Environment detected as {best_environment[0]} with confidence {best_environment[1]:.2f}")

        return best_environment[0]

    async def _detect_from_environment_variables(self) -> tuple[EnvironmentType, float] | None:
        """Detect environment from explicit environment variables."""
        env_var = os.getenv("DEPLOYMENT_ENVIRONMENT", "").lower()

        env_mapping = {
            "local": (EnvironmentType.LOCAL, 0.95),
            "development": (EnvironmentType.DEVELOPMENT, 0.95),
            "dev": (EnvironmentType.DEVELOPMENT, 0.90),
            "staging": (EnvironmentType.STAGING, 0.95),
            "stage": (EnvironmentType.STAGING, 0.90),
            "production": (EnvironmentType.PRODUCTION, 0.95),
            "prod": (EnvironmentType.PRODUCTION, 0.90),
        }

        return env_mapping.get(env_var)

    async def _detect_from_network_topology(self) -> tuple[EnvironmentType, float] | None:
        """Detect environment based on network configuration and accessible services."""
        try:
            # Check for local development services
            local_services = ["localhost:8000", "localhost:5432", "localhost:6379"]
            local_accessible = 0

            for service in local_services:
                host, port = service.split(":")
                if await self._check_port_accessible(host, int(port)):
                    local_accessible += 1

            if local_accessible >= 2:
                return (EnvironmentType.LOCAL, 0.8)

            # Check for production-like load balancers or gateways
            production_indicators = ["api.pratiko.ai", "prod-gateway.internal", "production.k8s.local"]

            for indicator in production_indicators:
                if await self._resolve_hostname(indicator):
                    return (EnvironmentType.PRODUCTION, 0.85)

            # Check for staging indicators
            staging_indicators = ["staging.pratiko.ai", "stage-api.internal"]

            for indicator in staging_indicators:
                if await self._resolve_hostname(indicator):
                    return (EnvironmentType.STAGING, 0.85)

        except Exception as e:
            self.logger.debug(f"Network topology detection failed: {e}")

        return None

    async def _detect_from_filesystem(self) -> tuple[EnvironmentType, float] | None:
        """Detect environment from filesystem structure and configuration files."""
        try:
            # Check for Docker environment
            if Path("/.dockerenv").exists():
                # Look for environment-specific configuration
                if Path("/app/config/production.yaml").exists():
                    return (EnvironmentType.PRODUCTION, 0.7)
                elif Path("/app/config/staging.yaml").exists():
                    return (EnvironmentType.STAGING, 0.7)
                else:
                    return (EnvironmentType.DEVELOPMENT, 0.6)

            # Check for Kubernetes environment
            if Path("/var/run/secrets/kubernetes.io").exists():
                namespace_file = Path("/var/run/secrets/kubernetes.io/serviceaccount/namespace")
                if namespace_file.exists():
                    namespace = namespace_file.read_text().strip()
                    if "prod" in namespace:
                        return (EnvironmentType.PRODUCTION, 0.8)
                    elif "staging" in namespace or "stage" in namespace:
                        return (EnvironmentType.STAGING, 0.8)
                    else:
                        return (EnvironmentType.DEVELOPMENT, 0.6)

            # Check for local development indicators
            if Path("./docker-compose.local.yml").exists() or Path("./.env.development").exists():
                return (EnvironmentType.LOCAL, 0.7)

        except Exception as e:
            self.logger.debug(f"Filesystem detection failed: {e}")

        return None

    async def _detect_from_running_services(self) -> tuple[EnvironmentType, float] | None:
        """Detect environment based on running services and processes."""
        try:
            # Get list of running processes
            processes = [p.info["name"] for p in psutil.process_iter(["name"])]

            # Production indicators
            production_processes = ["nginx", "gunicorn", "supervisor", "systemd"]
            production_count = sum(1 for p in production_processes if p in processes)

            if production_count >= 2:
                return (EnvironmentType.PRODUCTION, 0.6)

            # Development indicators
            dev_processes = ["uvicorn", "python", "node", "npm"]
            dev_count = sum(1 for p in dev_processes if p in processes)

            if dev_count >= 2:
                return (EnvironmentType.LOCAL, 0.5)

        except Exception as e:
            self.logger.debug(f"Service detection failed: {e}")

        return None

    async def _detect_from_hostname_patterns(self) -> tuple[EnvironmentType, float] | None:
        """Detect environment from hostname patterns."""
        try:
            hostname = platform.node().lower()

            if any(pattern in hostname for pattern in ["prod", "production"]):
                return (EnvironmentType.PRODUCTION, 0.7)
            elif any(pattern in hostname for pattern in ["staging", "stage"]):
                return (EnvironmentType.STAGING, 0.7)
            elif any(pattern in hostname for pattern in ["dev", "development"]):
                return (EnvironmentType.DEVELOPMENT, 0.7)
            elif any(pattern in hostname for pattern in ["local", "laptop", "desktop"]):
                return (EnvironmentType.LOCAL, 0.6)

        except Exception as e:
            self.logger.debug(f"Hostname detection failed: {e}")

        return None

    async def _check_port_accessible(self, host: str, port: int, timeout: float = 1.0) -> bool:
        """Check if a port is accessible on the given host."""
        try:
            reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
            writer.close()
            await writer.wait_closed()
            return True
        except:
            return False

    async def _resolve_hostname(self, hostname: str) -> bool:
        """Check if a hostname can be resolved."""
        try:
            import socket

            socket.gethostbyname(hostname)
            return True
        except:
            return False


class SystemMonitor:
    """Real-time system monitoring and performance analysis.

    Provides comprehensive system metrics including:
    - CPU utilization and load patterns
    - Memory usage and availability
    - Disk I/O and space utilization
    - Network latency and throughput
    - Historical trend analysis
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.SystemMonitor")
        self._metric_history = []

    async def get_current_metrics(self) -> SystemMetrics:
        """Collect comprehensive current system metrics.

        Returns:
            SystemMetrics: Current system performance data
        """
        try:
            # CPU metrics with load average
            cpu_percent = psutil.cpu_percent(interval=1)
            load_avg = os.getloadavg()[0] if hasattr(os, "getloadavg") else cpu_percent / 100

            # Memory metrics
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            available_memory_gb = memory.available / (1024**3)

            # Disk metrics
            disk = psutil.disk_usage("/")
            disk_usage_percent = disk.percent
            free_disk_gb = disk.free / (1024**3)

            # Network latency (ping to reliable host)
            network_latency = await self._measure_network_latency()

            metrics = SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                disk_usage_percent=disk_usage_percent,
                load_average=load_avg,
                network_latency=network_latency,
                available_memory_gb=available_memory_gb,
                free_disk_gb=free_disk_gb,
                timestamp=datetime.now(),
            )

            # Store in history for trend analysis
            self._metric_history.append(metrics)
            # Keep only last 100 measurements
            if len(self._metric_history) > 100:
                self._metric_history.pop(0)

            self.logger.debug(
                f"Collected metrics: CPU={cpu_percent:.1f}%, Memory={memory_percent:.1f}%, Disk={disk_usage_percent:.1f}%"
            )

            return metrics

        except Exception as e:
            self.logger.error(f"Failed to collect system metrics: {e}")
            # Return default metrics as fallback
            return SystemMetrics(
                cpu_percent=50.0,
                memory_percent=60.0,
                disk_usage_percent=70.0,
                load_average=1.0,
                network_latency=50.0,
                available_memory_gb=4.0,
                free_disk_gb=10.0,
                timestamp=datetime.now(),
            )

    async def _measure_network_latency(self) -> float:
        """Measure network latency to a reliable external host."""
        try:
            import platform as plat
            import subprocess

            # Use ping command appropriate for the platform
            if plat.system().lower() == "windows":
                cmd = ["ping", "-n", "1", "8.8.8.8"]
            else:
                cmd = ["ping", "-c", "1", "8.8.8.8"]

            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, timeout=5)
            end_time = time.time()

            if result.returncode == 0:
                return (end_time - start_time) * 1000  # Convert to milliseconds
            else:
                return 100.0  # Default latency if ping fails

        except Exception:
            return 100.0  # Default latency on error

    def get_system_trend(self, minutes: int = 10) -> dict[str, float]:
        """Analyze system performance trends over the specified time period.

        Args:
            minutes: Number of minutes to analyze

        Returns:
            Dict containing trend analysis (increasing, stable, decreasing)
        """
        if len(self._metric_history) < 2:
            return {"trend": "stable", "confidence": 0.0}

        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        recent_metrics = [m for m in self._metric_history if m.timestamp >= cutoff_time]

        if len(recent_metrics) < 2:
            return {"trend": "stable", "confidence": 0.0}

        # Calculate trends for key metrics
        cpu_trend = self._calculate_trend([m.cpu_percent for m in recent_metrics])
        memory_trend = self._calculate_trend([m.memory_percent for m in recent_metrics])

        # Overall trend assessment
        if cpu_trend > 0.1 or memory_trend > 0.1:
            return {"trend": "increasing", "confidence": 0.8}
        elif cpu_trend < -0.1 or memory_trend < -0.1:
            return {"trend": "decreasing", "confidence": 0.8}
        else:
            return {"trend": "stable", "confidence": 0.9}

    def _calculate_trend(self, values: list[float]) -> float:
        """Calculate linear trend coefficient for a series of values."""
        if len(values) < 2:
            return 0.0

        x = np.arange(len(values))
        y = np.array(values)

        # Calculate linear regression slope
        slope = np.polyfit(x, y, 1)[0]
        return slope


class DeploymentMLOptimizer:
    """Machine Learning-based deployment strategy optimizer.

    This component learns from historical deployment data to:
    - Predict optimal deployment strategies
    - Estimate deployment duration and resource requirements
    - Identify potential failure patterns
    - Recommend resource allocation adjustments
    """

    def __init__(self, data_dir: Path):
        self.logger = logging.getLogger(f"{__name__}.DeploymentMLOptimizer")
        self.data_dir = data_dir
        self.model_path = data_dir / "deployment_model.joblib"
        self.scaler_path = data_dir / "feature_scaler.joblib"

        # Initialize ML models
        self.strategy_classifier = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
        self.feature_scaler = StandardScaler()
        self.model_trained = False

        # Create data directory if it doesn't exist
        data_dir.mkdir(parents=True, exist_ok=True)

        # Load existing model if available
        self._load_existing_model()

    def _load_existing_model(self):
        """Load pre-trained model and scaler if they exist."""
        try:
            if self.model_path.exists() and self.scaler_path.exists():
                self.strategy_classifier = joblib.load(self.model_path)
                self.feature_scaler = joblib.load(self.scaler_path)
                self.model_trained = True
                self.logger.info("Loaded existing ML model for deployment optimization")
        except Exception as e:
            self.logger.warning(f"Failed to load existing model: {e}")

    def extract_features(self, context: DeploymentContext) -> np.ndarray:
        """Extract feature vector from deployment context for ML prediction.

        Features include:
        - System resource utilization
        - Historical success rates by environment
        - Deployment complexity indicators
        - Time constraints and external factors
        """
        features = []

        # System metrics features
        features.extend(
            [
                context.system_metrics.cpu_percent,
                context.system_metrics.memory_percent,
                context.system_metrics.disk_usage_percent,
                context.system_metrics.load_average,
                context.system_metrics.network_latency,
                context.system_metrics.available_memory_gb,
                context.system_metrics.free_disk_gb,
            ]
        )

        # Environment features (one-hot encoding)
        env_features = [0, 0, 0, 0]  # local, dev, staging, prod
        if context.environment == EnvironmentType.LOCAL:
            env_features[0] = 1
        elif context.environment == EnvironmentType.DEVELOPMENT:
            env_features[1] = 1
        elif context.environment == EnvironmentType.STAGING:
            env_features[2] = 1
        elif context.environment == EnvironmentType.PRODUCTION:
            env_features[3] = 1
        features.extend(env_features)

        # Deployment complexity features
        features.extend(
            [
                len(context.target_services),  # Number of services to deploy
                1 if context.deployment_size == "large" else 0.5 if context.deployment_size == "medium" else 0,
                context.time_constraints or 60,  # Time constraint in minutes
                1 if context.rollback_capability else 0,
            ]
        )

        # Historical success rate features
        if context.previous_deployments:
            recent_deployments = context.previous_deployments[-10:]  # Last 10 deployments
            success_rate = sum(1 for d in recent_deployments if d.success) / len(recent_deployments)
            avg_duration = sum(d.duration_minutes for d in recent_deployments) / len(recent_deployments)
            features.extend([success_rate, avg_duration])
        else:
            features.extend([0.8, 30.0])  # Default values for new environments

        # Time-based features
        now = datetime.now()
        features.extend(
            [
                now.hour,  # Hour of day (0-23)
                now.weekday(),  # Day of week (0-6)
                1 if 9 <= now.hour <= 17 else 0,  # Business hours flag
            ]
        )

        return np.array(features).reshape(1, -1)

    async def predict_optimal_strategy(self, context: DeploymentContext) -> tuple[DeploymentStrategy, float]:
        """Predict the optimal deployment strategy based on current context.

        Returns:
            Tuple of (predicted_strategy, confidence_score)
        """
        if not self.model_trained:
            # Fallback to heuristic-based strategy selection
            return self._heuristic_strategy_selection(context)

        try:
            features = self.extract_features(context)
            scaled_features = self.feature_scaler.transform(features)

            # Get prediction probabilities
            probabilities = self.strategy_classifier.predict_proba(scaled_features)[0]
            predicted_class = self.strategy_classifier.predict(scaled_features)[0]
            confidence = max(probabilities)

            # Map class index to strategy
            strategies = [DeploymentStrategy.CONSERVATIVE, DeploymentStrategy.BALANCED, DeploymentStrategy.AGGRESSIVE]
            predicted_strategy = strategies[predicted_class]

            self.logger.info(f"ML model predicts {predicted_strategy} strategy with confidence {confidence:.2f}")

            return predicted_strategy, confidence

        except Exception as e:
            self.logger.error(f"ML prediction failed: {e}")
            return self._heuristic_strategy_selection(context)

    def _heuristic_strategy_selection(self, context: DeploymentContext) -> tuple[DeploymentStrategy, float]:
        """Fallback heuristic-based strategy selection when ML model is unavailable.

        Decision logic:
        - High system load or production environment → Conservative
        - Normal conditions with time constraints → Aggressive
        - Default → Balanced approach
        """
        metrics = context.system_metrics

        # Production environment or high resource usage → Conservative
        if (
            context.environment == EnvironmentType.PRODUCTION
            or metrics.cpu_percent > 80
            or metrics.memory_percent > 85
        ):
            return DeploymentStrategy.CONSERVATIVE, 0.7

        # Local environment with good resources → Aggressive
        if context.environment == EnvironmentType.LOCAL and metrics.cpu_percent < 50 and metrics.memory_percent < 60:
            return DeploymentStrategy.AGGRESSIVE, 0.6

        # Time constraints favor aggressive approach
        if context.time_constraints and context.time_constraints < 30:
            return DeploymentStrategy.AGGRESSIVE, 0.5

        # Default to balanced approach
        return DeploymentStrategy.BALANCED, 0.8

    async def learn_from_deployment(self, record: DeploymentRecord):
        """Learn from a completed deployment to improve future predictions.

        This method updates the ML model with new deployment data,
        continuously improving prediction accuracy.
        """
        try:
            # Store the deployment record for future training
            await self._store_deployment_record(record)

            # Retrain model periodically (every 10 deployments)
            if await self._get_deployment_count() % 10 == 0:
                await self._retrain_model()

        except Exception as e:
            self.logger.error(f"Failed to learn from deployment: {e}")

    async def _store_deployment_record(self, record: DeploymentRecord):
        """Store deployment record in persistent storage."""
        db_path = self.data_dir / "deployment_history.db"

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Create table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS deployments (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT,
                    environment TEXT,
                    strategy TEXT,
                    duration_minutes REAL,
                    success BOOLEAN,
                    resource_usage TEXT,
                    error_message TEXT,
                    system_state_before TEXT,
                    system_state_after TEXT,
                    services_deployed TEXT,
                    rollback_required BOOLEAN
                )
            """)

            # Insert deployment record
            cursor.execute(
                """
                INSERT OR REPLACE INTO deployments VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    record.id,
                    record.timestamp.isoformat(),
                    record.environment,
                    record.strategy,
                    record.duration_minutes,
                    record.success,
                    json.dumps(record.resource_usage),
                    record.error_message,
                    json.dumps(record.system_state_before),
                    json.dumps(record.system_state_after),
                    json.dumps(record.services_deployed),
                    record.rollback_required,
                ),
            )

            conn.commit()
            conn.close()

        except Exception as e:
            self.logger.error(f"Failed to store deployment record: {e}")

    async def _get_deployment_count(self) -> int:
        """Get total number of stored deployment records."""
        db_path = self.data_dir / "deployment_history.db"

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM deployments")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except:
            return 0

    async def _retrain_model(self):
        """Retrain the ML model with all available deployment data."""
        try:
            # Load all deployment records
            records = await self._load_all_deployment_records()

            if len(records) < 10:  # Need minimum data for training
                self.logger.info("Insufficient data for model training")
                return

            # Prepare training data
            X = []
            y = []

            for record in records:
                # Reconstruct context for feature extraction
                context = self._reconstruct_context_from_record(record)
                features = self.extract_features(context)
                X.append(features.flatten())

                # Map strategy to class label
                strategy_map = {"conservative": 0, "balanced": 1, "aggressive": 2}
                y.append(strategy_map.get(record.strategy, 1))

            X = np.array(X)
            y = np.array(y)

            # Train the model
            self.feature_scaler.fit(X)
            X_scaled = self.feature_scaler.transform(X)

            self.strategy_classifier.fit(X_scaled, y)
            self.model_trained = True

            # Save the trained model
            joblib.dump(self.strategy_classifier, self.model_path)
            joblib.dump(self.feature_scaler, self.scaler_path)

            self.logger.info(f"Successfully retrained ML model with {len(records)} deployment records")

        except Exception as e:
            self.logger.error(f"Failed to retrain model: {e}")

    async def _load_all_deployment_records(self) -> list[DeploymentRecord]:
        """Load all deployment records from database."""
        db_path = self.data_dir / "deployment_history.db"
        records = []

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM deployments ORDER BY timestamp DESC")

            for row in cursor.fetchall():
                record = DeploymentRecord(
                    id=row[0],
                    timestamp=datetime.fromisoformat(row[1]),
                    environment=row[2],
                    strategy=row[3],
                    duration_minutes=row[4],
                    success=bool(row[5]),
                    resource_usage=json.loads(row[6]),
                    error_message=row[7],
                    system_state_before=json.loads(row[8]),
                    system_state_after=json.loads(row[9]),
                    services_deployed=json.loads(row[10]),
                    rollback_required=bool(row[11]),
                )
                records.append(record)

            conn.close()

        except Exception as e:
            self.logger.error(f"Failed to load deployment records: {e}")

        return records

    def _reconstruct_context_from_record(self, record: DeploymentRecord) -> DeploymentContext:
        """Reconstruct deployment context from historical record."""
        # Create mock system metrics from stored state
        system_metrics = SystemMetrics(
            cpu_percent=record.system_state_before.get("cpu_percent", 50.0),
            memory_percent=record.system_state_before.get("memory_percent", 60.0),
            disk_usage_percent=record.system_state_before.get("disk_usage_percent", 70.0),
            load_average=record.system_state_before.get("load_average", 1.0),
            network_latency=record.system_state_before.get("network_latency", 50.0),
            available_memory_gb=record.system_state_before.get("available_memory_gb", 4.0),
            free_disk_gb=record.system_state_before.get("free_disk_gb", 10.0),
            timestamp=record.timestamp,
        )

        # Create mock deployment context
        return DeploymentContext(
            environment=EnvironmentType(record.environment),
            system_metrics=system_metrics,
            previous_deployments=[],
            target_services=record.services_deployed,
            deployment_size="medium",  # Default assumption
            time_constraints=None,
            rollback_capability=True,
        )


class AdaptiveDeploymentEngine:
    """Main orchestrator for intelligent, self-adapting deployments.

    This is the central component that coordinates all other subsystems:
    - Environment detection and system monitoring
    - Machine learning-based strategy optimization
    - Dynamic resource allocation and deployment execution
    - Comprehensive logging and decision tracking
    """

    def __init__(self, config_path: Path | None = None):
        self.logger = logging.getLogger(__name__)
        self.config_path = config_path or Path("deployment_config.yaml")
        self.data_dir = Path("deployment_data")

        # Initialize subsystems
        self.env_detector = EnvironmentDetector()
        self.system_monitor = SystemMonitor()
        self.ml_optimizer = DeploymentMLOptimizer(self.data_dir)

        # Load configuration
        self.config = self._load_configuration()

        # Decision tracking for reporting
        self.decision_log = []

    def _load_configuration(self) -> dict[str, Any]:
        """Load deployment configuration from YAML file."""
        default_config = {
            "resource_limits": {
                "conservative": {"cpu_limit": 0.5, "memory_limit": 0.6, "concurrency": 2},
                "balanced": {"cpu_limit": 0.7, "memory_limit": 0.8, "concurrency": 4},
                "aggressive": {"cpu_limit": 0.9, "memory_limit": 0.9, "concurrency": 8},
            },
            "thresholds": {"high_cpu": 80.0, "high_memory": 85.0, "high_disk": 90.0, "max_deployment_time": 60},
            "retry_policies": {"max_retries": 3, "backoff_factor": 2.0, "initial_delay": 30},
        }

        try:
            if self.config_path.exists():
                with open(self.config_path) as f:
                    user_config = yaml.safe_load(f)
                    # Merge with defaults
                    default_config.update(user_config)
                    self.logger.info(f"Loaded configuration from {self.config_path}")
            else:
                # Save default configuration
                with open(self.config_path, "w") as f:
                    yaml.dump(default_config, f, default_flow_style=False)
                self.logger.info(f"Created default configuration at {self.config_path}")
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")

        return default_config

    async def execute_adaptive_deployment(
        self,
        target_services: list[str],
        deployment_size: str = "medium",
        time_constraints: int | None = None,
        force_strategy: DeploymentStrategy | None = None,
    ) -> DeploymentRecord:
        """Execute an intelligent, adaptive deployment.

        This is the main entry point that orchestrates the entire deployment process:
        1. Detect environment and collect system metrics
        2. Analyze historical patterns and predict optimal strategy
        3. Execute deployment with dynamic resource allocation
        4. Monitor progress and adapt as needed
        5. Learn from results to improve future deployments

        Args:
            target_services: List of services to deploy
            deployment_size: Size indicator (small, medium, large)
            time_constraints: Maximum deployment time in minutes
            force_strategy: Override ML prediction with specific strategy

        Returns:
            DeploymentRecord: Complete record of the deployment attempt
        """
        deployment_id = f"deploy_{int(time.time())}"
        start_time = datetime.now()

        self.logger.info(f"Starting adaptive deployment {deployment_id}")
        self._log_decision(
            "deployment_started",
            {
                "deployment_id": deployment_id,
                "target_services": target_services,
                "deployment_size": deployment_size,
                "time_constraints": time_constraints,
            },
        )

        try:
            # Phase 1: Environment Analysis and Context Building
            self.logger.info("Phase 1: Analyzing environment and system state")

            environment = await self.env_detector.detect_environment()
            current_metrics = await self.system_monitor.get_current_metrics()
            system_trend = self.system_monitor.get_system_trend()

            self._log_decision(
                "environment_detected",
                {
                    "environment": environment.value,
                    "system_metrics": asdict(current_metrics),
                    "system_trend": system_trend,
                },
            )

            # Load previous deployment history
            previous_deployments = await self.ml_optimizer._load_all_deployment_records()

            # Build comprehensive deployment context
            context = DeploymentContext(
                environment=environment,
                system_metrics=current_metrics,
                previous_deployments=previous_deployments[-20:],  # Last 20 deployments
                target_services=target_services,
                deployment_size=deployment_size,
                time_constraints=time_constraints,
                rollback_capability=True,
            )

            # Phase 2: Strategy Selection and Resource Planning
            self.logger.info("Phase 2: Selecting optimal deployment strategy")

            if force_strategy:
                selected_strategy = force_strategy
                strategy_confidence = 1.0
                self._log_decision("strategy_forced", {"strategy": selected_strategy.value})
            else:
                selected_strategy, strategy_confidence = await self.ml_optimizer.predict_optimal_strategy(context)
                self._log_decision(
                    "strategy_predicted", {"strategy": selected_strategy.value, "confidence": strategy_confidence}
                )

            # Validate strategy against current conditions
            if await self._should_override_strategy(context, selected_strategy):
                original_strategy = selected_strategy
                selected_strategy = await self._get_safe_strategy(context)
                self._log_decision(
                    "strategy_overridden",
                    {
                        "original_strategy": original_strategy.value,
                        "new_strategy": selected_strategy.value,
                        "reason": "safety_override",
                    },
                )

            # Calculate resource allocation
            resource_allocation = self._calculate_resource_allocation(selected_strategy, context)
            self._log_decision("resource_allocation", resource_allocation)

            # Phase 3: Pre-deployment Validation
            self.logger.info("Phase 3: Pre-deployment validation")

            validation_result = await self._validate_deployment_conditions(context, resource_allocation)
            if not validation_result["valid"]:
                raise Exception(f"Pre-deployment validation failed: {validation_result['reason']}")

            self._log_decision("pre_deployment_validation", validation_result)

            # Phase 4: Deployment Execution
            self.logger.info("Phase 4: Executing deployment")

            deployment_result = await self._execute_deployment_strategy(
                selected_strategy, context, resource_allocation
            )

            end_time = datetime.now()
            duration_minutes = (end_time - start_time).total_seconds() / 60

            # Phase 5: Post-deployment Analysis and Learning
            self.logger.info("Phase 5: Post-deployment analysis")

            final_metrics = await self.system_monitor.get_current_metrics()

            # Create deployment record
            deployment_record = DeploymentRecord(
                id=deployment_id,
                timestamp=start_time,
                environment=environment.value,
                strategy=selected_strategy.value,
                duration_minutes=duration_minutes,
                success=deployment_result["success"],
                resource_usage=deployment_result.get("resource_usage", {}),
                error_message=deployment_result.get("error_message"),
                system_state_before=asdict(current_metrics),
                system_state_after=asdict(final_metrics),
                services_deployed=target_services,
                rollback_required=deployment_result.get("rollback_required", False),
            )

            # Learn from this deployment
            await self.ml_optimizer.learn_from_deployment(deployment_record)

            self._log_decision(
                "deployment_completed",
                {
                    "success": deployment_result["success"],
                    "duration_minutes": duration_minutes,
                    "resource_usage": deployment_result.get("resource_usage", {}),
                },
            )

            if deployment_result["success"]:
                self.logger.info(
                    f"Deployment {deployment_id} completed successfully in {duration_minutes:.1f} minutes"
                )
            else:
                self.logger.error(f"Deployment {deployment_id} failed: {deployment_result.get('error_message')}")

            return deployment_record

        except Exception as e:
            # Handle deployment failure
            end_time = datetime.now()
            duration_minutes = (end_time - start_time).total_seconds() / 60

            self.logger.error(f"Deployment {deployment_id} failed with exception: {e}")
            self._log_decision("deployment_failed", {"error": str(e)})

            # Create failure record
            failure_record = DeploymentRecord(
                id=deployment_id,
                timestamp=start_time,
                environment=environment.value if "environment" in locals() else "unknown",
                strategy=selected_strategy.value if "selected_strategy" in locals() else "unknown",
                duration_minutes=duration_minutes,
                success=False,
                resource_usage={},
                error_message=str(e),
                system_state_before=asdict(current_metrics) if "current_metrics" in locals() else {},
                system_state_after={},
                services_deployed=target_services,
                rollback_required=True,
            )

            # Learn from failure
            try:
                await self.ml_optimizer.learn_from_deployment(failure_record)
            except:
                pass  # Don't fail on learning failure

            return failure_record

    async def _should_override_strategy(self, context: DeploymentContext, strategy: DeploymentStrategy) -> bool:
        """Determine if the predicted strategy should be overridden for safety.

        Safety overrides are triggered by:
        - High system resource utilization
        - Production environment with aggressive strategy
        - Recent deployment failures
        - Critical time periods (business hours in production)
        """
        metrics = context.system_metrics

        # Override aggressive strategy in production with high resource usage
        if (
            strategy == DeploymentStrategy.AGGRESSIVE
            and context.environment == EnvironmentType.PRODUCTION
            and (metrics.cpu_percent > 70 or metrics.memory_percent > 75)
        ):
            return True

        # Override if system is under stress
        if (
            metrics.cpu_percent > self.config["thresholds"]["high_cpu"]
            or metrics.memory_percent > self.config["thresholds"]["high_memory"]
        ):
            return True

        # Override if recent deployments have been failing
        if context.previous_deployments:
            recent_failures = sum(1 for d in context.previous_deployments[-5:] if not d.success)
            if recent_failures >= 3:  # 3 or more failures in last 5 deployments
                return True

        # Override aggressive strategy during business hours in production
        now = datetime.now()
        if (
            strategy == DeploymentStrategy.AGGRESSIVE
            and context.environment == EnvironmentType.PRODUCTION
            and 9 <= now.hour <= 17
            and now.weekday() < 5
        ):  # Business hours, weekdays
            return True

        return False

    async def _get_safe_strategy(self, context: DeploymentContext) -> DeploymentStrategy:
        """Get a safe fallback strategy based on current conditions."""
        metrics = context.system_metrics

        # If system is under high stress, use conservative
        if metrics.cpu_percent > 80 or metrics.memory_percent > 85:
            return DeploymentStrategy.CONSERVATIVE

        # Production environment defaults to balanced for safety
        if context.environment == EnvironmentType.PRODUCTION:
            return DeploymentStrategy.BALANCED

        # Default safe strategy
        return DeploymentStrategy.BALANCED

    def _calculate_resource_allocation(
        self, strategy: DeploymentStrategy, context: DeploymentContext
    ) -> dict[str, Any]:
        """Calculate optimal resource allocation based on strategy and system state.

        Resource allocation considers:
        - Base strategy limits from configuration
        - Current system resource availability
        - Deployment size and complexity
        - Historical resource usage patterns
        """
        base_limits = self.config["resource_limits"][strategy.value]
        metrics = context.system_metrics

        # Adjust based on available resources
        available_cpu_ratio = max(0.1, (100 - metrics.cpu_percent) / 100)
        available_memory_ratio = max(0.1, (100 - metrics.memory_percent) / 100)

        # Calculate actual resource allocation
        cpu_allocation = min(base_limits["cpu_limit"], available_cpu_ratio * 0.8)
        memory_allocation = min(base_limits["memory_limit"], available_memory_ratio * 0.8)

        # Adjust concurrency based on deployment size
        size_multiplier = {"small": 0.5, "medium": 1.0, "large": 1.5}[context.deployment_size]
        concurrency = int(base_limits["concurrency"] * size_multiplier)

        # Ensure minimum viable resources
        cpu_allocation = max(cpu_allocation, 0.1)
        memory_allocation = max(memory_allocation, 0.2)
        concurrency = max(concurrency, 1)

        return {
            "cpu_limit": cpu_allocation,
            "memory_limit": memory_allocation,
            "concurrency": concurrency,
            "timeout_minutes": self.config["thresholds"]["max_deployment_time"],
            "strategy": strategy.value,
        }

    async def _validate_deployment_conditions(
        self, context: DeploymentContext, resource_allocation: dict[str, Any]
    ) -> dict[str, Any]:
        """Validate that current conditions are suitable for deployment.

        Validation checks:
        - System resource availability
        - Network connectivity
        - Required services accessibility
        - Time constraints feasibility
        """
        validation_issues = []

        # Check system resources
        metrics = context.system_metrics

        if metrics.cpu_percent > 95:
            validation_issues.append("CPU utilization too high (>95%)")

        if metrics.memory_percent > 95:
            validation_issues.append("Memory utilization too high (>95%)")

        if metrics.disk_usage_percent > 95:
            validation_issues.append("Disk usage too high (>95%)")

        if metrics.available_memory_gb < 0.5:
            validation_issues.append("Insufficient available memory (<0.5GB)")

        if metrics.free_disk_gb < 1.0:
            validation_issues.append("Insufficient free disk space (<1GB)")

        # Check network connectivity
        if metrics.network_latency > 1000:  # >1 second latency
            validation_issues.append("High network latency detected (>1s)")

        # Check time constraints
        if context.time_constraints:
            estimated_duration = self._estimate_deployment_duration(context, resource_allocation)
            if estimated_duration > context.time_constraints:
                validation_issues.append(
                    f"Estimated duration ({estimated_duration}min) exceeds time constraint ({context.time_constraints}min)"
                )

        # Validate service dependencies
        for service in context.target_services:
            if not await self._validate_service_dependencies(service):
                validation_issues.append(f"Service {service} has unmet dependencies")

        return {
            "valid": len(validation_issues) == 0,
            "issues": validation_issues,
            "reason": "; ".join(validation_issues) if validation_issues else None,
        }

    def _estimate_deployment_duration(self, context: DeploymentContext, resource_allocation: dict[str, Any]) -> float:
        """Estimate deployment duration based on context and resource allocation."""
        # Base duration estimates by strategy (in minutes)
        base_durations = {"conservative": 45, "balanced": 30, "aggressive": 20}

        base_duration = base_durations[resource_allocation["strategy"]]

        # Adjust based on deployment size
        size_multipliers = {"small": 0.7, "medium": 1.0, "large": 1.5}
        duration = base_duration * size_multipliers[context.deployment_size]

        # Adjust based on number of services
        service_factor = 1 + (len(context.target_services) - 1) * 0.2
        duration *= service_factor

        # Adjust based on system load
        load_factor = 1 + (context.system_metrics.cpu_percent / 100) * 0.5
        duration *= load_factor

        # Adjust based on historical data
        if context.previous_deployments:
            recent_deployments = [
                d for d in context.previous_deployments if d.environment == context.environment.value
            ]
            if recent_deployments:
                avg_historical = sum(d.duration_minutes for d in recent_deployments[-5:]) / len(
                    recent_deployments[-5:]
                )
                duration = (duration + avg_historical) / 2  # Average with historical data

        return duration

    async def _validate_service_dependencies(self, service: str) -> bool:
        """Validate that a service's dependencies are met."""
        # This is a placeholder for actual dependency checking
        # In practice, this would check database connectivity, external APIs, etc.
        return True

    async def _execute_deployment_strategy(
        self, strategy: DeploymentStrategy, context: DeploymentContext, resource_allocation: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute the actual deployment using the selected strategy and resource allocation.

        This method orchestrates the deployment process with strategy-specific optimizations:
        - Conservative: Sequential deployment with extensive validation
        - Balanced: Parallel deployment with moderate validation
        - Aggressive: Maximum parallelism with minimal validation
        """
        start_time = time.time()
        deployment_results = []

        try:
            if strategy == DeploymentStrategy.CONSERVATIVE:
                # Sequential deployment with extensive validation
                for service in context.target_services:
                    result = await self._deploy_service_conservative(service, resource_allocation)
                    deployment_results.append(result)
                    if not result["success"]:
                        # Stop on first failure in conservative mode
                        break

            elif strategy == DeploymentStrategy.BALANCED:
                # Parallel deployment with moderate batch size
                batch_size = min(resource_allocation["concurrency"], len(context.target_services))
                service_batches = [
                    context.target_services[i : i + batch_size]
                    for i in range(0, len(context.target_services), batch_size)
                ]

                for batch in service_batches:
                    batch_tasks = [self._deploy_service_balanced(service, resource_allocation) for service in batch]
                    batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                    deployment_results.extend(batch_results)

            elif strategy == DeploymentStrategy.AGGRESSIVE:
                # Maximum parallelism deployment
                deployment_tasks = [
                    self._deploy_service_aggressive(service, resource_allocation)
                    for service in context.target_services
                ]
                deployment_results = await asyncio.gather(*deployment_tasks, return_exceptions=True)

            # Analyze deployment results
            successful_deployments = sum(
                1 for r in deployment_results if isinstance(r, dict) and r.get("success", False)
            )
            total_deployments = len(deployment_results)

            overall_success = successful_deployments == total_deployments

            # Calculate resource usage
            end_time = time.time()
            final_metrics = await self.system_monitor.get_current_metrics()

            resource_usage = {
                "peak_cpu_percent": final_metrics.cpu_percent,
                "peak_memory_percent": final_metrics.memory_percent,
                "deployment_duration": end_time - start_time,
                "services_deployed": successful_deployments,
                "services_failed": total_deployments - successful_deployments,
            }

            return {
                "success": overall_success,
                "resource_usage": resource_usage,
                "deployment_results": deployment_results,
                "rollback_required": not overall_success,
            }

        except Exception as e:
            return {"success": False, "error_message": str(e), "resource_usage": {}, "rollback_required": True}

    async def _deploy_service_conservative(self, service: str, resource_allocation: dict[str, Any]) -> dict[str, Any]:
        """Deploy a service using conservative strategy (slow, safe, extensive validation)."""
        try:
            self.logger.info(f"Deploying {service} using conservative strategy")

            # Pre-deployment health check
            await asyncio.sleep(2)  # Simulate health check

            # Deploy with conservative resource limits
            await asyncio.sleep(5)  # Simulate deployment time

            # Post-deployment validation
            await asyncio.sleep(3)  # Simulate validation

            return {"success": True, "service": service, "strategy": "conservative"}

        except Exception as e:
            return {"success": False, "service": service, "error": str(e)}

    async def _deploy_service_balanced(self, service: str, resource_allocation: dict[str, Any]) -> dict[str, Any]:
        """Deploy a service using balanced strategy (moderate speed and safety)."""
        try:
            self.logger.info(f"Deploying {service} using balanced strategy")

            # Basic health check
            await asyncio.sleep(1)  # Simulate health check

            # Deploy with balanced resource limits
            await asyncio.sleep(3)  # Simulate deployment time

            # Basic validation
            await asyncio.sleep(1)  # Simulate validation

            return {"success": True, "service": service, "strategy": "balanced"}

        except Exception as e:
            return {"success": False, "service": service, "error": str(e)}

    async def _deploy_service_aggressive(self, service: str, resource_allocation: dict[str, Any]) -> dict[str, Any]:
        """Deploy a service using aggressive strategy (fast, minimal validation)."""
        try:
            self.logger.info(f"Deploying {service} using aggressive strategy")

            # Minimal validation
            await asyncio.sleep(0.5)  # Simulate minimal check

            # Fast deployment with maximum resources
            await asyncio.sleep(2)  # Simulate fast deployment

            return {"success": True, "service": service, "strategy": "aggressive"}

        except Exception as e:
            return {"success": False, "service": service, "error": str(e)}

    def _log_decision(self, decision_type: str, details: dict[str, Any]):
        """Log a decision for later reporting and analysis."""
        decision_entry = {"timestamp": datetime.now().isoformat(), "decision_type": decision_type, "details": details}
        self.decision_log.append(decision_entry)
        self.logger.debug(f"Decision logged: {decision_type}")

    def generate_deployment_report(self, deployment_record: DeploymentRecord) -> dict[str, Any]:
        """Generate a comprehensive report of the deployment decision-making process.

        The report includes:
        - Decision tree and reasoning at each step
        - Resource allocation calculations
        - Performance metrics and comparisons
        - Lessons learned and recommendations
        """
        report = {
            "deployment_summary": {
                "id": deployment_record.id,
                "timestamp": deployment_record.timestamp.isoformat(),
                "environment": deployment_record.environment,
                "strategy_used": deployment_record.strategy,
                "duration_minutes": deployment_record.duration_minutes,
                "success": deployment_record.success,
                "services_deployed": deployment_record.services_deployed,
                "rollback_required": deployment_record.rollback_required,
            },
            "decision_process": self.decision_log,
            "performance_analysis": self._analyze_deployment_performance(deployment_record),
            "resource_utilization": deployment_record.resource_usage,
            "system_impact": self._calculate_system_impact(deployment_record),
            "recommendations": self._generate_recommendations(deployment_record),
            "lessons_learned": self._extract_lessons_learned(deployment_record),
        }

        return report

    def _analyze_deployment_performance(self, record: DeploymentRecord) -> dict[str, Any]:
        """Analyze deployment performance against benchmarks."""
        # Performance benchmarks by strategy
        benchmarks = {
            "conservative": {"expected_duration": 45, "expected_success_rate": 0.95},
            "balanced": {"expected_duration": 30, "expected_success_rate": 0.90},
            "aggressive": {"expected_duration": 20, "expected_success_rate": 0.85},
        }

        benchmark = benchmarks.get(record.strategy, benchmarks["balanced"])

        duration_performance = "good" if record.duration_minutes <= benchmark["expected_duration"] else "slow"
        success_performance = "good" if record.success else "failed"

        return {
            "duration_performance": duration_performance,
            "success_performance": success_performance,
            "benchmark_duration": benchmark["expected_duration"],
            "actual_duration": record.duration_minutes,
            "duration_variance": record.duration_minutes - benchmark["expected_duration"],
        }

    def _calculate_system_impact(self, record: DeploymentRecord) -> dict[str, Any]:
        """Calculate the deployment's impact on system resources."""
        before = record.system_state_before
        after = record.system_state_after

        if not before or not after:
            return {"impact": "unknown", "reason": "insufficient_data"}

        cpu_impact = after.get("cpu_percent", 0) - before.get("cpu_percent", 0)
        memory_impact = after.get("memory_percent", 0) - before.get("memory_percent", 0)

        return {
            "cpu_impact_percent": cpu_impact,
            "memory_impact_percent": memory_impact,
            "overall_impact": "high" if abs(cpu_impact) > 20 or abs(memory_impact) > 20 else "low",
        }

    def _generate_recommendations(self, record: DeploymentRecord) -> list[str]:
        """Generate recommendations for future deployments."""
        recommendations = []

        if not record.success:
            recommendations.append("Consider using a more conservative strategy for similar deployments")
            recommendations.append("Review and address the root cause of deployment failure")

        if record.duration_minutes > 60:
            recommendations.append("Consider optimizing deployment process or using more aggressive strategy")

        if record.system_state_before and record.system_state_after:
            cpu_before = record.system_state_before.get("cpu_percent", 0)
            if cpu_before > 80:
                recommendations.append("Deploy during periods of lower system load for better performance")

        if record.rollback_required:
            recommendations.append("Implement better pre-deployment validation to reduce rollback need")

        return recommendations

    def _extract_lessons_learned(self, record: DeploymentRecord) -> list[str]:
        """Extract key lessons learned from the deployment."""
        lessons = []

        # Strategy effectiveness
        if record.success:
            lessons.append(f"{record.strategy} strategy was effective for {record.environment} environment")
        else:
            lessons.append(f"{record.strategy} strategy may not be suitable for current conditions")

        # Duration insights
        if record.duration_minutes < 15:
            lessons.append("Deployment completed faster than expected - consider more aggressive strategies")
        elif record.duration_minutes > 60:
            lessons.append("Deployment took longer than expected - investigate bottlenecks")

        # Resource usage insights
        if record.resource_usage:
            peak_cpu = record.resource_usage.get("peak_cpu_percent", 0)
            if peak_cpu > 90:
                lessons.append("High CPU usage during deployment - consider resource optimization")

        return lessons


# Example usage and configuration
if __name__ == "__main__":

    async def main():
        """Example usage of the Adaptive Deployment Engine."""
        # Configure logging
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        # Initialize the adaptive deployment engine
        engine = AdaptiveDeploymentEngine()

        # Execute an adaptive deployment
        services_to_deploy = ["api-service", "web-frontend", "background-worker"]

        deployment_record = await engine.execute_adaptive_deployment(
            target_services=services_to_deploy,
            deployment_size="medium",
            time_constraints=45,  # 45 minute maximum
            force_strategy=None,  # Let ML decide
        )

        # Generate comprehensive report
        report = engine.generate_deployment_report(deployment_record)

        # Print report summary
        print("\n" + "=" * 60)
        print("ADAPTIVE DEPLOYMENT REPORT")
        print("=" * 60)
        print(f"Deployment ID: {deployment_record.id}")
        print(f"Success: {deployment_record.success}")
        print(f"Duration: {deployment_record.duration_minutes:.1f} minutes")
        print(f"Strategy: {deployment_record.strategy}")
        print(f"Environment: {deployment_record.environment}")

        if deployment_record.error_message:
            print(f"Error: {deployment_record.error_message}")

        print("\nRecommendations:")
        for recommendation in report["recommendations"]:
            print(f"  • {recommendation}")

        print("\nLessons Learned:")
        for lesson in report["lessons_learned"]:
            print(f"  • {lesson}")

    # Run the example
    asyncio.run(main())
