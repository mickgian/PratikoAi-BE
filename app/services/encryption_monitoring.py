"""
Encryption Monitoring and Alerting System for PratikoAI.

This module provides comprehensive monitoring of the database encryption system,
including performance metrics, security alerts, compliance tracking, and
automated health checks for Italian data protection requirements.
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from sqlalchemy import text, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.services.database_encryption_service import DatabaseEncryptionService, ENCRYPTED_FIELDS_CONFIG
from app.services.encryption_key_rotation import EncryptionKeyRotationService
from app.core.logging import logger
from app.core.config import get_settings


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class HealthStatus(str, Enum):
    """System health status values."""
    HEALTHY = "healthy"
    WARNING = "warning"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    OFFLINE = "offline"


@dataclass
class EncryptionAlert:
    """Encryption system alert."""
    alert_id: str
    severity: AlertSeverity
    title: str
    description: str
    category: str
    affected_component: str
    metric_value: Optional[float]
    threshold_value: Optional[float]
    created_at: datetime
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None


@dataclass
class PerformanceMetrics:
    """Encryption performance metrics."""
    timestamp: datetime
    encryption_operations_per_second: float
    decryption_operations_per_second: float
    avg_encryption_time_ms: float
    avg_decryption_time_ms: float
    cache_hit_rate: float
    error_rate: float
    active_key_version: int
    total_encrypted_fields: int
    cpu_usage_percent: float
    memory_usage_mb: float


@dataclass
class ComplianceStatus:
    """GDPR and Italian data protection compliance status."""
    timestamp: datetime
    total_pii_fields: int
    encrypted_pii_fields: int
    unencrypted_pii_fields: int
    encryption_coverage_percent: float
    audit_log_retention_days: int
    key_rotation_compliance: bool
    gdpr_compliant: bool
    italian_compliance: bool
    compliance_issues: List[str]


@dataclass
class SecurityMetrics:
    """Security-related metrics."""
    timestamp: datetime
    failed_decryption_attempts: int
    unauthorized_access_attempts: int
    key_rotation_overdue_days: int
    weak_keys_detected: int
    suspicious_query_patterns: int
    data_exfiltration_indicators: int
    security_score: float  # 0-100


@dataclass
class SystemHealth:
    """Overall system health assessment."""
    timestamp: datetime
    overall_status: HealthStatus
    encryption_service_status: HealthStatus
    key_management_status: HealthStatus
    performance_status: HealthStatus
    compliance_status: HealthStatus
    security_status: HealthStatus
    active_alerts: int
    critical_alerts: int
    uptime_hours: float


class EncryptionMonitoringService:
    """
    Comprehensive monitoring service for database encryption system.
    
    Features:
    - Real-time performance monitoring
    - Security threat detection
    - Compliance tracking (GDPR, Italian data protection)
    - Automated alerting and notifications
    - Health checks and diagnostics
    - Performance optimization recommendations
    """
    
    def __init__(
        self,
        db_session: AsyncSession,
        encryption_service: DatabaseEncryptionService,
        alert_thresholds: Optional[Dict[str, float]] = None
    ):
        """
        Initialize monitoring service.
        
        Args:
            db_session: Database session for monitoring operations
            encryption_service: Encryption service to monitor
            alert_thresholds: Custom alert thresholds
        """
        self.db = db_session
        self.encryption_service = encryption_service
        self.settings = get_settings()
        
        # Default alert thresholds
        self.alert_thresholds = {
            "max_encryption_time_ms": 100.0,
            "max_decryption_time_ms": 100.0,
            "min_cache_hit_rate": 0.8,
            "max_error_rate": 0.05,
            "max_cpu_usage_percent": 80.0,
            "max_memory_usage_mb": 1024.0,
            "min_encryption_coverage_percent": 95.0,
            "max_key_age_days": 90,
            "max_audit_log_gap_hours": 1.0,
            "max_failed_decryption_rate": 0.01
        }
        
        if alert_thresholds:
            self.alert_thresholds.update(alert_thresholds)
        
        # Active alerts
        self.active_alerts: List[EncryptionAlert] = []
        
        # Monitoring state
        self.monitoring_start_time = datetime.now(timezone.utc)
        self.last_health_check = None
        self.health_check_interval = timedelta(minutes=5)
    
    async def collect_performance_metrics(self) -> PerformanceMetrics:
        """
        Collect current performance metrics.
        
        Returns:
            PerformanceMetrics with current system performance data
        """
        try:
            # Get encryption service metrics
            service_metrics = await self.encryption_service.get_performance_metrics()
            
            # Calculate rates (operations per second)
            # This is a simplified calculation - in production you'd track this over time
            encryption_ops_per_sec = service_metrics.get("encryption_operations", 0) / 60.0  # rough estimate
            decryption_ops_per_sec = service_metrics.get("decryption_operations", 0) / 60.0
            
            # Get system resource usage (simplified - would use psutil in production)
            cpu_usage = await self._get_cpu_usage()
            memory_usage = await self._get_memory_usage()
            
            # Calculate cache hit rate (placeholder)
            cache_hit_rate = 0.85  # Would be calculated from actual cache statistics
            
            # Calculate error rate from audit logs
            error_rate = await self._calculate_error_rate()
            
            # Count encrypted fields
            total_encrypted_fields = sum(
                len(config["fields"]) 
                for config in ENCRYPTED_FIELDS_CONFIG.values()
            )
            
            metrics = PerformanceMetrics(
                timestamp=datetime.now(timezone.utc),
                encryption_operations_per_second=encryption_ops_per_sec,
                decryption_operations_per_second=decryption_ops_per_sec,
                avg_encryption_time_ms=service_metrics.get("avg_encryption_time_ms", 0.0),
                avg_decryption_time_ms=service_metrics.get("avg_decryption_time_ms", 0.0),
                cache_hit_rate=cache_hit_rate,
                error_rate=error_rate,
                active_key_version=service_metrics.get("current_key_version", 0),
                total_encrypted_fields=total_encrypted_fields,
                cpu_usage_percent=cpu_usage,
                memory_usage_mb=memory_usage
            )
            
            # Check for performance alerts
            await self._check_performance_alerts(metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect performance metrics: {e}")
            raise
    
    async def collect_compliance_status(self) -> ComplianceStatus:
        """
        Collect GDPR and Italian data protection compliance status.
        
        Returns:
            ComplianceStatus with current compliance information
        """
        try:
            # Count total PII fields that should be encrypted
            total_pii_fields = 0
            encrypted_pii_fields = 0
            
            for table_name, config in ENCRYPTED_FIELDS_CONFIG.items():
                for field_name, field_type in config.get("field_types", {}).items():
                    if field_type.lower() in ["email", "phone", "tax_id", "personal_data", "financial_data"]:
                        total_pii_fields += 1
                        
                        # Check if field is actually encrypted (would query encrypted_field_registry)
                        encrypted_pii_fields += 1  # Assuming all are encrypted for now
            
            unencrypted_pii_fields = total_pii_fields - encrypted_pii_fields
            encryption_coverage = (encrypted_pii_fields / total_pii_fields * 100) if total_pii_fields > 0 else 100
            
            # Check audit log retention
            audit_retention_days = await self._get_audit_log_retention_days()
            
            # Check key rotation compliance
            key_rotation_compliant = not await self.encryption_service.check_key_rotation_needed()
            
            # Identify compliance issues
            compliance_issues = []
            
            if encryption_coverage < 100:
                compliance_issues.append(f"Only {encryption_coverage:.1f}% of PII fields are encrypted")
            
            if audit_retention_days < 730:  # 2 years required
                compliance_issues.append(f"Audit log retention is {audit_retention_days} days (minimum 730 required)")
            
            if not key_rotation_compliant:
                compliance_issues.append("Key rotation is overdue")
            
            # Overall compliance assessment
            gdpr_compliant = len(compliance_issues) == 0
            italian_compliant = gdpr_compliant  # Same requirements for Italian compliance
            
            status = ComplianceStatus(
                timestamp=datetime.now(timezone.utc),
                total_pii_fields=total_pii_fields,
                encrypted_pii_fields=encrypted_pii_fields,
                unencrypted_pii_fields=unencrypted_pii_fields,
                encryption_coverage_percent=encryption_coverage,
                audit_log_retention_days=audit_retention_days,
                key_rotation_compliance=key_rotation_compliant,
                gdpr_compliant=gdpr_compliant,
                italian_compliance=italian_compliant,
                compliance_issues=compliance_issues
            )
            
            # Check for compliance alerts
            await self._check_compliance_alerts(status)
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to collect compliance status: {e}")
            raise
    
    async def collect_security_metrics(self) -> SecurityMetrics:
        """
        Collect security-related metrics and threat indicators.
        
        Returns:
            SecurityMetrics with current security status
        """
        try:
            # Get security metrics from audit logs
            result = await self.db.execute(text("""
                SELECT 
                    COUNT(*) FILTER (WHERE success = false AND operation = 'decrypt') as failed_decryption,
                    COUNT(*) FILTER (WHERE success = false AND operation = 'encrypt') as failed_encryption,
                    COUNT(DISTINCT user_id) FILTER (WHERE success = false) as users_with_failures
                FROM encryption_audit_log
                WHERE timestamp >= NOW() - INTERVAL '1 hour'
            """))
            
            row = result.fetchone()
            failed_decryption = row[0] if row else 0
            failed_encryption = row[1] if row else 0
            users_with_failures = row[2] if row else 0
            
            # Check key rotation status
            current_key = self.encryption_service.encryption_keys.get(
                self.encryption_service.current_key_version
            )
            key_age_days = 0
            if current_key:
                key_age = datetime.now(timezone.utc) - current_key.created_at
                key_age_days = key_age.days
            
            key_rotation_overdue = max(0, key_age_days - 90)  # 90 day rotation policy
            
            # Detect suspicious patterns (simplified)
            suspicious_patterns = await self._detect_suspicious_patterns()
            
            # Calculate security score (0-100)
            security_score = self._calculate_security_score(
                failed_decryption, key_rotation_overdue, suspicious_patterns
            )
            
            metrics = SecurityMetrics(
                timestamp=datetime.now(timezone.utc),
                failed_decryption_attempts=failed_decryption,
                unauthorized_access_attempts=users_with_failures,
                key_rotation_overdue_days=key_rotation_overdue,
                weak_keys_detected=0,  # Would be implemented with key strength analysis
                suspicious_query_patterns=suspicious_patterns,
                data_exfiltration_indicators=0,  # Would be implemented with anomaly detection
                security_score=security_score
            )
            
            # Check for security alerts
            await self._check_security_alerts(metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect security metrics: {e}")
            raise
    
    async def perform_health_check(self) -> SystemHealth:
        """
        Perform comprehensive system health check.
        
        Returns:
            SystemHealth with overall system status
        """
        try:
            check_time = datetime.now(timezone.utc)
            
            # Collect all metrics
            performance_metrics = await self.collect_performance_metrics()
            compliance_status = await self.collect_compliance_status()
            security_metrics = await self.collect_security_metrics()
            
            # Assess individual component health
            encryption_status = self._assess_encryption_service_health()
            key_mgmt_status = await self._assess_key_management_health()
            performance_status = self._assess_performance_health(performance_metrics)
            compliance_health = self._assess_compliance_health(compliance_status)
            security_health = self._assess_security_health(security_metrics)
            
            # Calculate overall health
            overall_status = self._calculate_overall_health([
                encryption_status, key_mgmt_status, performance_status,
                compliance_health, security_health
            ])
            
            # Count active alerts
            active_alerts = len(self.active_alerts)
            critical_alerts = len([a for a in self.active_alerts if a.severity == AlertSeverity.CRITICAL])
            
            # Calculate uptime
            uptime = (check_time - self.monitoring_start_time).total_seconds() / 3600
            
            health = SystemHealth(
                timestamp=check_time,
                overall_status=overall_status,
                encryption_service_status=encryption_status,
                key_management_status=key_mgmt_status,
                performance_status=performance_status,
                compliance_status=compliance_health,
                security_status=security_health,
                active_alerts=active_alerts,
                critical_alerts=critical_alerts,
                uptime_hours=uptime
            )
            
            self.last_health_check = check_time
            
            # Log health status
            logger.info(
                f"Health check completed: {overall_status.value} "
                f"({active_alerts} alerts, {critical_alerts} critical)"
            )
            
            return health
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            # Return critical status if health check fails
            return SystemHealth(
                timestamp=datetime.now(timezone.utc),
                overall_status=HealthStatus.CRITICAL,
                encryption_service_status=HealthStatus.OFFLINE,
                key_management_status=HealthStatus.OFFLINE,
                performance_status=HealthStatus.OFFLINE,
                compliance_status=HealthStatus.OFFLINE,
                security_status=HealthStatus.OFFLINE,
                active_alerts=len(self.active_alerts),
                critical_alerts=len([a for a in self.active_alerts if a.severity == AlertSeverity.CRITICAL]),
                uptime_hours=0.0
            )
    
    async def create_alert(
        self,
        severity: AlertSeverity,
        title: str,
        description: str,
        category: str,
        component: str,
        metric_value: Optional[float] = None,
        threshold_value: Optional[float] = None
    ) -> EncryptionAlert:
        """
        Create and track a new alert.
        
        Args:
            severity: Alert severity level
            title: Alert title
            description: Detailed description
            category: Alert category (performance, security, compliance)
            component: Affected component
            metric_value: Current metric value
            threshold_value: Threshold that was exceeded
            
        Returns:
            Created EncryptionAlert
        """
        alert_id = f"{category}_{component}_{datetime.now(timezone.utc).timestamp()}"
        
        alert = EncryptionAlert(
            alert_id=alert_id,
            severity=severity,
            title=title,
            description=description,
            category=category,
            affected_component=component,
            metric_value=metric_value,
            threshold_value=threshold_value,
            created_at=datetime.now(timezone.utc)
        )
        
        self.active_alerts.append(alert)
        
        # Log alert
        logger.warning(
            f"ENCRYPTION ALERT [{severity.value.upper()}] {title}: {description}"
        )
        
        # Store alert in database
        await self._store_alert(alert)
        
        return alert
    
    async def resolve_alert(self, alert_id: str, resolution_notes: str) -> bool:
        """
        Resolve an active alert.
        
        Args:
            alert_id: ID of alert to resolve
            resolution_notes: Notes about resolution
            
        Returns:
            True if alert was resolved, False if not found
        """
        for alert in self.active_alerts:
            if alert.alert_id == alert_id:
                alert.resolved_at = datetime.now(timezone.utc)
                alert.resolution_notes = resolution_notes
                
                # Remove from active alerts
                self.active_alerts.remove(alert)
                
                # Update in database
                await self._update_alert_resolution(alert)
                
                logger.info(f"Resolved alert {alert_id}: {resolution_notes}")
                return True
        
        return False
    
    async def get_monitoring_dashboard_data(self) -> Dict[str, Any]:
        """
        Get comprehensive monitoring data for dashboard display.
        
        Returns:
            Dict with all monitoring information
        """
        try:
            # Collect all current data
            health = await self.perform_health_check()
            performance = await self.collect_performance_metrics()
            compliance = await self.collect_compliance_status()
            security = await self.collect_security_metrics()
            
            # Get historical trends (last 24 hours)
            trends = await self._get_historical_trends()
            
            # Get top alerts
            top_alerts = sorted(
                self.active_alerts,
                key=lambda x: (x.severity.value, x.created_at),
                reverse=True
            )[:10]
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "health": asdict(health),
                "performance": asdict(performance),
                "compliance": asdict(compliance),
                "security": asdict(security),
                "trends": trends,
                "active_alerts": [asdict(alert) for alert in top_alerts],
                "system_info": {
                    "encryption_service_version": "1.0.0",
                    "total_encrypted_tables": len(ENCRYPTED_FIELDS_CONFIG),
                    "monitoring_uptime_hours": health.uptime_hours,
                    "last_key_rotation": await self._get_last_key_rotation_date()
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get monitoring dashboard data: {e}")
            raise
    
    # Private helper methods
    
    async def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage (placeholder)."""
        # In production, would use psutil or system monitoring
        return 25.0  # Placeholder value
    
    async def _get_memory_usage(self) -> float:
        """Get current memory usage in MB (placeholder)."""
        # In production, would use psutil or system monitoring
        return 512.0  # Placeholder value
    
    async def _calculate_error_rate(self) -> float:
        """Calculate current error rate from audit logs."""
        try:
            result = await self.db.execute(text("""
                SELECT 
                    COUNT(*) as total_operations,
                    COUNT(*) FILTER (WHERE success = false) as failed_operations
                FROM encryption_audit_log
                WHERE timestamp >= NOW() - INTERVAL '1 hour'
            """))
            
            row = result.fetchone()
            if row and row[0] > 0:
                return row[1] / row[0]  # failed / total
            return 0.0
            
        except SQLAlchemyError:
            return 0.0
    
    async def _get_audit_log_retention_days(self) -> int:
        """Get current audit log retention period."""
        try:
            result = await self.db.execute(text("""
                SELECT (NOW() - MIN(timestamp))::int as retention_days
                FROM encryption_audit_log
            """))
            
            row = result.fetchone()
            return row[0] if row and row[0] else 0
            
        except SQLAlchemyError:
            return 0
    
    async def _detect_suspicious_patterns(self) -> int:
        """Detect suspicious encryption/decryption patterns."""
        try:
            # Look for unusual patterns in the last hour
            result = await self.db.execute(text("""
                SELECT COUNT(*)
                FROM encryption_audit_log
                WHERE timestamp >= NOW() - INTERVAL '1 hour'
                  AND (
                    -- High frequency from single user
                    user_id IN (
                        SELECT user_id 
                        FROM encryption_audit_log 
                        WHERE timestamp >= NOW() - INTERVAL '1 hour'
                        GROUP BY user_id 
                        HAVING COUNT(*) > 1000
                    )
                    -- Multiple failures from same IP
                    OR (success = false AND user_id IS NOT NULL)
                  )
            """))
            
            row = result.fetchone()
            return row[0] if row else 0
            
        except SQLAlchemyError:
            return 0
    
    def _calculate_security_score(
        self,
        failed_decryptions: int,
        key_overdue_days: int,
        suspicious_patterns: int
    ) -> float:
        """Calculate security score (0-100)."""
        score = 100.0
        
        # Deduct points for security issues
        score -= min(failed_decryptions * 2, 20)  # Max 20 points for failed decryptions
        score -= min(key_overdue_days * 1, 30)    # Max 30 points for overdue keys
        score -= min(suspicious_patterns * 5, 25) # Max 25 points for suspicious patterns
        
        return max(0.0, score)
    
    def _assess_encryption_service_health(self) -> HealthStatus:
        """Assess encryption service health."""
        try:
            # Check if service is initialized and has active keys
            if not self.encryption_service.current_key_version:
                return HealthStatus.CRITICAL
            
            if not self.encryption_service.encryption_keys:
                return HealthStatus.CRITICAL
            
            # Check if there are any active keys
            active_keys = [k for k in self.encryption_service.encryption_keys.values() if k.is_active]
            if not active_keys:
                return HealthStatus.CRITICAL
            
            return HealthStatus.HEALTHY
            
        except Exception:
            return HealthStatus.OFFLINE
    
    async def _assess_key_management_health(self) -> HealthStatus:
        """Assess key management health."""
        try:
            # Check if key rotation is needed
            rotation_needed = await self.encryption_service.check_key_rotation_needed()
            
            if rotation_needed:
                return HealthStatus.WARNING
            
            # Check key age
            current_key = self.encryption_service.encryption_keys.get(
                self.encryption_service.current_key_version
            )
            
            if current_key:
                key_age = datetime.now(timezone.utc) - current_key.created_at
                if key_age.days > 120:  # Beyond recommended rotation interval
                    return HealthStatus.DEGRADED
            
            return HealthStatus.HEALTHY
            
        except Exception:
            return HealthStatus.OFFLINE
    
    def _assess_performance_health(self, metrics: PerformanceMetrics) -> HealthStatus:
        """Assess performance health based on metrics."""
        if metrics.avg_encryption_time_ms > self.alert_thresholds["max_encryption_time_ms"]:
            return HealthStatus.DEGRADED
        
        if metrics.avg_decryption_time_ms > self.alert_thresholds["max_decryption_time_ms"]:
            return HealthStatus.DEGRADED
        
        if metrics.error_rate > self.alert_thresholds["max_error_rate"]:
            return HealthStatus.WARNING
        
        if metrics.cpu_usage_percent > self.alert_thresholds["max_cpu_usage_percent"]:
            return HealthStatus.WARNING
        
        return HealthStatus.HEALTHY
    
    def _assess_compliance_health(self, status: ComplianceStatus) -> HealthStatus:
        """Assess compliance health."""
        if not status.gdpr_compliant or not status.italian_compliance:
            return HealthStatus.CRITICAL
        
        if status.encryption_coverage_percent < self.alert_thresholds["min_encryption_coverage_percent"]:
            return HealthStatus.DEGRADED
        
        if not status.key_rotation_compliance:
            return HealthStatus.WARNING
        
        return HealthStatus.HEALTHY
    
    def _assess_security_health(self, metrics: SecurityMetrics) -> HealthStatus:
        """Assess security health."""
        if metrics.security_score < 50:
            return HealthStatus.CRITICAL
        
        if metrics.security_score < 70:
            return HealthStatus.DEGRADED
        
        if metrics.key_rotation_overdue_days > 30:
            return HealthStatus.WARNING
        
        return HealthStatus.HEALTHY
    
    def _calculate_overall_health(self, component_statuses: List[HealthStatus]) -> HealthStatus:
        """Calculate overall health from component statuses."""
        if HealthStatus.CRITICAL in component_statuses or HealthStatus.OFFLINE in component_statuses:
            return HealthStatus.CRITICAL
        
        if HealthStatus.DEGRADED in component_statuses:
            return HealthStatus.DEGRADED
        
        if HealthStatus.WARNING in component_statuses:
            return HealthStatus.WARNING
        
        return HealthStatus.HEALTHY
    
    async def _check_performance_alerts(self, metrics: PerformanceMetrics) -> None:
        """Check performance metrics against thresholds and create alerts."""
        if metrics.avg_encryption_time_ms > self.alert_thresholds["max_encryption_time_ms"]:
            await self.create_alert(
                AlertSeverity.MEDIUM,
                "High Encryption Latency",
                f"Average encryption time is {metrics.avg_encryption_time_ms:.1f}ms",
                "performance",
                "encryption_service",
                metrics.avg_encryption_time_ms,
                self.alert_thresholds["max_encryption_time_ms"]
            )
        
        if metrics.error_rate > self.alert_thresholds["max_error_rate"]:
            await self.create_alert(
                AlertSeverity.HIGH,
                "High Error Rate",
                f"Encryption error rate is {metrics.error_rate:.2%}",
                "performance",
                "encryption_service",
                metrics.error_rate,
                self.alert_thresholds["max_error_rate"]
            )
    
    async def _check_compliance_alerts(self, status: ComplianceStatus) -> None:
        """Check compliance status and create alerts."""
        if not status.gdpr_compliant:
            await self.create_alert(
                AlertSeverity.CRITICAL,
                "GDPR Compliance Issue",
                f"System is not GDPR compliant: {', '.join(status.compliance_issues)}",
                "compliance",
                "gdpr_compliance"
            )
    
    async def _check_security_alerts(self, metrics: SecurityMetrics) -> None:
        """Check security metrics and create alerts."""
        if metrics.security_score < 70:
            await self.create_alert(
                AlertSeverity.HIGH,
                "Low Security Score",
                f"Security score is {metrics.security_score:.1f}/100",
                "security",
                "security_assessment",
                metrics.security_score,
                70.0
            )
        
        if metrics.key_rotation_overdue_days > 30:
            await self.create_alert(
                AlertSeverity.HIGH,
                "Key Rotation Overdue",
                f"Key rotation is {metrics.key_rotation_overdue_days} days overdue",
                "security",
                "key_management",
                metrics.key_rotation_overdue_days,
                30.0
            )
    
    async def _store_alert(self, alert: EncryptionAlert) -> None:
        """Store alert in database."""
        try:
            await self.db.execute(text("""
                INSERT INTO encryption_audit_log (
                    operation, success, error_message, user_id, timestamp
                ) VALUES (
                    :operation, :success, :message, :user_id, :timestamp
                )
            """), {
                "operation": f"alert_{alert.category}",
                "success": False,
                "message": f"[{alert.severity.value.upper()}] {alert.title}: {alert.description}",
                "user_id": "system",
                "timestamp": alert.created_at
            })
            await self.db.commit()
        except SQLAlchemyError as e:
            logger.error(f"Failed to store alert in database: {e}")
    
    async def _update_alert_resolution(self, alert: EncryptionAlert) -> None:
        """Update alert resolution in database."""
        try:
            await self.db.execute(text("""
                INSERT INTO encryption_audit_log (
                    operation, success, error_message, user_id, timestamp
                ) VALUES (
                    :operation, :success, :message, :user_id, :timestamp
                )
            """), {
                "operation": f"alert_resolved_{alert.category}",
                "success": True,
                "message": f"Resolved alert {alert.alert_id}: {alert.resolution_notes}",
                "user_id": "system",
                "timestamp": alert.resolved_at
            })
            await self.db.commit()
        except SQLAlchemyError as e:
            logger.error(f"Failed to update alert resolution: {e}")
    
    async def _get_historical_trends(self) -> Dict[str, Any]:
        """Get historical performance trends."""
        # Placeholder for historical trend analysis
        return {
            "encryption_performance_24h": [],
            "error_rate_24h": [],
            "security_score_24h": [],
            "compliance_status_24h": []
        }
    
    async def _get_last_key_rotation_date(self) -> Optional[str]:
        """Get date of last key rotation."""
        try:
            result = await self.db.execute(text("""
                SELECT MAX(timestamp)
                FROM encryption_audit_log
                WHERE operation = 'key_rotation_completed'
            """))
            
            row = result.fetchone()
            if row and row[0]:
                return row[0].isoformat()
            return None
            
        except SQLAlchemyError:
            return None


# Utility functions for monitoring integration

async def run_health_check(
    db_session: AsyncSession,
    encryption_service: DatabaseEncryptionService
) -> Dict[str, Any]:
    """Run comprehensive health check and return results."""
    monitoring = EncryptionMonitoringService(db_session, encryption_service)
    health = await monitoring.perform_health_check()
    return asdict(health)


async def get_monitoring_summary(
    db_session: AsyncSession,
    encryption_service: DatabaseEncryptionService
) -> Dict[str, Any]:
    """Get monitoring summary for API endpoints."""
    monitoring = EncryptionMonitoringService(db_session, encryption_service)
    return await monitoring.get_monitoring_dashboard_data()