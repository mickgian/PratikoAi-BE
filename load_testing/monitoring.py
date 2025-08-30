"""
Performance Monitoring Framework for Load Testing.

This module monitors system resources, database performance, and application
metrics during load testing to identify bottlenecks and ensure SLA compliance.
"""

import asyncio
import asyncpg
import redis.asyncio as aioredis
import psutil
import time
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict, field
from pathlib import Path
import aiohttp
import aiofiles

logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    """System resource metrics at a point in time"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_available_gb: float
    disk_read_mb: float
    disk_write_mb: float
    disk_io_percent: float
    network_sent_mb: float
    network_recv_mb: float
    load_avg_1m: float
    load_avg_5m: float
    load_avg_15m: float
    process_count: int


@dataclass
class DatabaseMetrics:
    """Database performance metrics"""
    timestamp: datetime
    active_connections: int
    idle_connections: int
    total_connections: int
    queries_per_second: float
    slow_queries: int
    deadlocks: int
    lock_waits: int
    cache_hit_ratio: float
    avg_query_time_ms: float
    longest_query_time_ms: float
    database_size_mb: float
    temp_files: int
    temp_bytes: int


@dataclass
class RedisMetrics:
    """Redis performance metrics"""
    timestamp: datetime
    used_memory_mb: float
    peak_memory_mb: float
    connected_clients: int
    blocked_clients: int
    total_commands_processed: int
    instantaneous_ops_per_sec: int
    keyspace_hits: int
    keyspace_misses: int
    evicted_keys: int
    expired_keys: int
    pub_sub_channels: int
    pub_sub_patterns: int


@dataclass
class ApplicationMetrics:
    """Application-specific metrics"""
    timestamp: datetime
    active_requests: int
    request_rate: float
    response_time_p50: float
    response_time_p95: float
    response_time_p99: float
    error_rate: float
    llm_requests: int
    llm_errors: int
    llm_retries: int
    cache_hit_rate: float
    circuit_breaker_state: Dict[str, str]
    queue_sizes: Dict[str, int]


@dataclass
class PerformanceSnapshot:
    """Complete performance snapshot"""
    system: SystemMetrics
    database: DatabaseMetrics
    redis: RedisMetrics
    application: ApplicationMetrics


@dataclass
class LoadTestSession:
    """Load testing session metadata"""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    config: Dict[str, Any] = field(default_factory=dict)
    results_dir: Path = field(default_factory=lambda: Path("load_test_results"))
    
    def __post_init__(self):
        self.results_dir = Path(self.results_dir)
        self.results_dir.mkdir(exist_ok=True)


class LoadTestMonitor:
    """Monitor system resources and performance during load tests"""
    
    def __init__(
        self,
        db_url: str,
        redis_url: str,
        prometheus_url: Optional[str] = None,
        grafana_url: Optional[str] = None
    ):
        self.db_url = db_url
        self.redis_url = redis_url
        self.prometheus_url = prometheus_url
        self.grafana_url = grafana_url
        
        self.monitoring = False
        self.session: Optional[LoadTestSession] = None
        self.snapshots: List[PerformanceSnapshot] = []
        
        # Monitoring configuration
        self.monitor_interval = 5  # seconds
        self.alert_thresholds = {
            "cpu_percent": 80.0,
            "memory_percent": 90.0,
            "db_connections": 80,
            "response_time_p95": 5000,  # ms
            "error_rate": 0.05  # 5%
        }
        
    async def start_monitoring(
        self,
        session_id: str,
        config: Dict[str, Any],
        interval: int = 5
    ) -> LoadTestSession:
        """Start monitoring for a load test session"""
        if self.monitoring:
            raise RuntimeError("Monitoring already active")
        
        self.session = LoadTestSession(
            session_id=session_id,
            start_time=datetime.now(timezone.utc),
            config=config
        )
        
        self.monitor_interval = interval
        self.monitoring = True
        self.snapshots = []
        
        logger.info(f"Started monitoring session {session_id}")
        
        # Start monitoring task
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        
        return self.session
    
    async def stop_monitoring(self) -> LoadTestSession:
        """Stop monitoring and save results"""
        if not self.monitoring:
            raise RuntimeError("Monitoring not active")
        
        self.monitoring = False
        
        if hasattr(self, 'monitor_task'):
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        self.session.end_time = datetime.now(timezone.utc)
        
        # Save results
        await self._save_session_results()
        
        logger.info(f"Stopped monitoring session {self.session.session_id}")
        return self.session
    
    async def _monitor_loop(self):
        """Main monitoring loop"""
        try:
            while self.monitoring:
                snapshot = await self.collect_snapshot()
                self.snapshots.append(snapshot)
                
                # Check for alerts
                await self._check_alerts(snapshot)
                
                # Save periodic checkpoint
                if len(self.snapshots) % 12 == 0:  # Every minute with 5s interval
                    await self._save_checkpoint()
                
                await asyncio.sleep(self.monitor_interval)
                
        except asyncio.CancelledError:
            logger.info("Monitoring loop cancelled")
            raise
        except Exception as e:
            logger.error(f"Monitoring loop error: {e}")
            raise
    
    async def collect_snapshot(self) -> PerformanceSnapshot:
        """Collect a complete performance snapshot"""
        timestamp = datetime.now(timezone.utc)
        
        # Collect metrics concurrently
        system_task = asyncio.create_task(self._collect_system_metrics(timestamp))
        db_task = asyncio.create_task(self._collect_database_metrics(timestamp))
        redis_task = asyncio.create_task(self._collect_redis_metrics(timestamp))
        app_task = asyncio.create_task(self._collect_application_metrics(timestamp))
        
        system_metrics = await system_task
        db_metrics = await db_task
        redis_metrics = await redis_task
        app_metrics = await app_task
        
        return PerformanceSnapshot(
            system=system_metrics,
            database=db_metrics,
            redis=redis_metrics,
            application=app_metrics
        )
    
    async def _collect_system_metrics(self, timestamp: datetime) -> SystemMetrics:
        """Collect system resource metrics"""
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        
        # Disk I/O
        disk_io = psutil.disk_io_counters()
        disk_usage = psutil.disk_usage('/')
        
        # Network I/O
        network_io = psutil.net_io_counters()
        
        # Load average (Unix/Linux only)
        try:
            load_avg = psutil.getloadavg()
        except AttributeError:
            load_avg = (0, 0, 0)  # Windows fallback
        
        # Process count
        process_count = len(psutil.pids())
        
        return SystemMetrics(
            timestamp=timestamp,
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_used_gb=memory.used / (1024**3),
            memory_available_gb=memory.available / (1024**3),
            disk_read_mb=disk_io.read_bytes / (1024**2) if disk_io else 0,
            disk_write_mb=disk_io.write_bytes / (1024**2) if disk_io else 0,
            disk_io_percent=disk_usage.percent,
            network_sent_mb=network_io.bytes_sent / (1024**2) if network_io else 0,
            network_recv_mb=network_io.bytes_recv / (1024**2) if network_io else 0,
            load_avg_1m=load_avg[0],
            load_avg_5m=load_avg[1],
            load_avg_15m=load_avg[2],
            process_count=process_count
        )
    
    async def _collect_database_metrics(self, timestamp: datetime) -> DatabaseMetrics:
        """Collect PostgreSQL database metrics"""
        try:
            db_conn = await asyncpg.connect(self.db_url)
            
            # Connection stats
            conn_stats = await db_conn.fetchrow("""
                SELECT 
                    count(*) FILTER (WHERE state = 'active') as active_connections,
                    count(*) FILTER (WHERE state = 'idle') as idle_connections,
                    count(*) as total_connections
                FROM pg_stat_activity
                WHERE datname = current_database()
            """)
            
            # Query performance
            query_stats = await db_conn.fetchrow("""
                SELECT 
                    COALESCE(sum(calls), 0) as total_queries,
                    COALESCE(avg(mean_exec_time), 0) as avg_query_time,
                    COALESCE(max(max_exec_time), 0) as max_query_time,
                    COALESCE(count(*) FILTER (WHERE mean_exec_time > 1000), 0) as slow_queries
                FROM pg_stat_statements
                WHERE dbid = (SELECT oid FROM pg_database WHERE datname = current_database())
            """)
            
            # Database size
            db_size = await db_conn.fetchval("""
                SELECT pg_database_size(current_database()) / (1024*1024)
            """)
            
            # Cache hit ratio
            cache_hit = await db_conn.fetchrow("""
                SELECT 
                    sum(heap_blks_hit) / NULLIF(sum(heap_blks_hit + heap_blks_read), 0) as cache_hit_ratio
                FROM pg_statio_user_tables
            """)
            
            # Lock and deadlock info
            locks = await db_conn.fetchrow("""
                SELECT 
                    COALESCE(count(*) FILTER (WHERE NOT granted), 0) as lock_waits,
                    0 as deadlocks  -- Would need pg_stat_database for deadlocks
                FROM pg_locks
                WHERE database = (SELECT oid FROM pg_database WHERE datname = current_database())
            """)
            
            await db_conn.close()
            
            return DatabaseMetrics(
                timestamp=timestamp,
                active_connections=conn_stats['active_connections'] or 0,
                idle_connections=conn_stats['idle_connections'] or 0,
                total_connections=conn_stats['total_connections'] or 0,
                queries_per_second=0,  # Would need time-based calculation
                slow_queries=query_stats['slow_queries'] or 0,
                deadlocks=0,  # locks['deadlocks'] or 0,
                lock_waits=locks['lock_waits'] or 0,
                cache_hit_ratio=cache_hit['cache_hit_ratio'] or 0,
                avg_query_time_ms=query_stats['avg_query_time'] or 0,
                longest_query_time_ms=query_stats['max_query_time'] or 0,
                database_size_mb=db_size or 0,
                temp_files=0,  # Would need additional queries
                temp_bytes=0
            )
            
        except Exception as e:
            logger.error(f"Failed to collect database metrics: {e}")
            return DatabaseMetrics(
                timestamp=timestamp,
                active_connections=0,
                idle_connections=0,
                total_connections=0,
                queries_per_second=0,
                slow_queries=0,
                deadlocks=0,
                lock_waits=0,
                cache_hit_ratio=0,
                avg_query_time_ms=0,
                longest_query_time_ms=0,
                database_size_mb=0,
                temp_files=0,
                temp_bytes=0
            )
    
    async def _collect_redis_metrics(self, timestamp: datetime) -> RedisMetrics:
        """Collect Redis performance metrics"""
        try:
            redis = aioredis.from_url(self.redis_url)
            info = await redis.info()
            await redis.aclose()
            
            return RedisMetrics(
                timestamp=timestamp,
                used_memory_mb=info.get('used_memory', 0) / (1024**2),
                peak_memory_mb=info.get('used_memory_peak', 0) / (1024**2),
                connected_clients=info.get('connected_clients', 0),
                blocked_clients=info.get('blocked_clients', 0),
                total_commands_processed=info.get('total_commands_processed', 0),
                instantaneous_ops_per_sec=info.get('instantaneous_ops_per_sec', 0),
                keyspace_hits=info.get('keyspace_hits', 0),
                keyspace_misses=info.get('keyspace_misses', 0),
                evicted_keys=info.get('evicted_keys', 0),
                expired_keys=info.get('expired_keys', 0),
                pub_sub_channels=info.get('pubsub_channels', 0),
                pub_sub_patterns=info.get('pubsub_patterns', 0)
            )
            
        except Exception as e:
            logger.error(f"Failed to collect Redis metrics: {e}")
            return RedisMetrics(
                timestamp=timestamp,
                used_memory_mb=0,
                peak_memory_mb=0,
                connected_clients=0,
                blocked_clients=0,
                total_commands_processed=0,
                instantaneous_ops_per_sec=0,
                keyspace_hits=0,
                keyspace_misses=0,
                evicted_keys=0,
                expired_keys=0,
                pub_sub_channels=0,
                pub_sub_patterns=0
            )
    
    async def _collect_application_metrics(self, timestamp: datetime) -> ApplicationMetrics:
        """Collect application-specific metrics"""
        try:
            # Try to get metrics from Prometheus if available
            if self.prometheus_url:
                metrics = await self._get_prometheus_metrics()
                if metrics:
                    return metrics
            
            # Fallback to basic metrics
            return ApplicationMetrics(
                timestamp=timestamp,
                active_requests=0,
                request_rate=0,
                response_time_p50=0,
                response_time_p95=0,
                response_time_p99=0,
                error_rate=0,
                llm_requests=0,
                llm_errors=0,
                llm_retries=0,
                cache_hit_rate=0,
                circuit_breaker_state={},
                queue_sizes={}
            )
            
        except Exception as e:
            logger.error(f"Failed to collect application metrics: {e}")
            return ApplicationMetrics(
                timestamp=timestamp,
                active_requests=0,
                request_rate=0,
                response_time_p50=0,
                response_time_p95=0,
                response_time_p99=0,
                error_rate=0,
                llm_requests=0,
                llm_errors=0,
                llm_retries=0,
                cache_hit_rate=0,
                circuit_breaker_state={},
                queue_sizes={}
            )
    
    async def _get_prometheus_metrics(self) -> Optional[ApplicationMetrics]:
        """Get metrics from Prometheus"""
        if not self.prometheus_url:
            return None
        
        try:
            async with aiohttp.ClientSession() as session:
                # Query multiple metrics
                queries = {
                    'request_rate': 'rate(http_requests_total[1m])',
                    'response_time_p95': 'histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))',
                    'error_rate': 'rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])',
                    'cache_hit_rate': 'rate(cache_hits_total[5m]) / (rate(cache_hits_total[5m]) + rate(cache_misses_total[5m]))'
                }
                
                metrics_data = {}
                for name, query in queries.items():
                    url = f"{self.prometheus_url}/api/v1/query"
                    params = {'query': query}
                    
                    async with session.get(url, params=params) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data['status'] == 'success' and data['data']['result']:
                                value = float(data['data']['result'][0]['value'][1])
                                metrics_data[name] = value
                
                return ApplicationMetrics(
                    timestamp=datetime.now(timezone.utc),
                    active_requests=0,  # Would need specific metric
                    request_rate=metrics_data.get('request_rate', 0),
                    response_time_p50=0,  # Would need specific query
                    response_time_p95=metrics_data.get('response_time_p95', 0) * 1000,  # Convert to ms
                    response_time_p99=0,  # Would need specific query
                    error_rate=metrics_data.get('error_rate', 0),
                    llm_requests=0,  # Would need specific metric
                    llm_errors=0,
                    llm_retries=0,
                    cache_hit_rate=metrics_data.get('cache_hit_rate', 0),
                    circuit_breaker_state={},
                    queue_sizes={}
                )
                
        except Exception as e:
            logger.error(f"Failed to get Prometheus metrics: {e}")
            return None
    
    async def _check_alerts(self, snapshot: PerformanceSnapshot):
        """Check metrics against alert thresholds"""
        alerts = []
        
        # CPU alert
        if snapshot.system.cpu_percent > self.alert_thresholds["cpu_percent"]:
            alerts.append(f"High CPU: {snapshot.system.cpu_percent:.1f}%")
        
        # Memory alert
        if snapshot.system.memory_percent > self.alert_thresholds["memory_percent"]:
            alerts.append(f"High Memory: {snapshot.system.memory_percent:.1f}%")
        
        # Database connections alert
        if snapshot.database.total_connections > self.alert_thresholds["db_connections"]:
            alerts.append(f"High DB connections: {snapshot.database.total_connections}")
        
        # Response time alert
        if snapshot.application.response_time_p95 > self.alert_thresholds["response_time_p95"]:
            alerts.append(f"High response time P95: {snapshot.application.response_time_p95:.0f}ms")
        
        # Error rate alert
        if snapshot.application.error_rate > self.alert_thresholds["error_rate"]:
            alerts.append(f"High error rate: {snapshot.application.error_rate*100:.1f}%")
        
        if alerts:
            alert_message = f"⚠️ ALERTS at {snapshot.system.timestamp}: {', '.join(alerts)}"
            logger.warning(alert_message)
            print(alert_message)  # Also print to console for immediate visibility
    
    async def _save_checkpoint(self):
        """Save periodic checkpoint of metrics"""
        if not self.session or not self.snapshots:
            return
        
        checkpoint_file = self.session.results_dir / f"{self.session.session_id}_checkpoint.json"
        
        try:
            checkpoint_data = {
                "session": asdict(self.session),
                "snapshots_count": len(self.snapshots),
                "latest_snapshot": asdict(self.snapshots[-1]) if self.snapshots else None,
                "checkpoint_time": datetime.now(timezone.utc).isoformat()
            }
            
            async with aiofiles.open(checkpoint_file, 'w') as f:
                await f.write(json.dumps(checkpoint_data, indent=2, default=str))
                
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
    
    async def _save_session_results(self):
        """Save complete session results"""
        if not self.session:
            return
        
        results_file = self.session.results_dir / f"{self.session.session_id}_results.json"
        
        try:
            session_data = {
                "session": asdict(self.session),
                "summary": self._generate_summary(),
                "snapshots": [asdict(snapshot) for snapshot in self.snapshots]
            }
            
            async with aiofiles.open(results_file, 'w') as f:
                await f.write(json.dumps(session_data, indent=2, default=str))
            
            logger.info(f"Saved session results to {results_file}")
            
        except Exception as e:
            logger.error(f"Failed to save session results: {e}")
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate summary statistics from collected snapshots"""
        if not self.snapshots:
            return {}
        
        # Calculate aggregated metrics
        cpu_values = [s.system.cpu_percent for s in self.snapshots]
        memory_values = [s.system.memory_percent for s in self.snapshots]
        db_conn_values = [s.database.total_connections for s in self.snapshots]
        response_time_values = [s.application.response_time_p95 for s in self.snapshots if s.application.response_time_p95 > 0]
        
        return {
            "duration_minutes": len(self.snapshots) * self.monitor_interval / 60,
            "total_snapshots": len(self.snapshots),
            "cpu_stats": {
                "min": min(cpu_values) if cpu_values else 0,
                "max": max(cpu_values) if cpu_values else 0,
                "avg": sum(cpu_values) / len(cpu_values) if cpu_values else 0
            },
            "memory_stats": {
                "min": min(memory_values) if memory_values else 0,
                "max": max(memory_values) if memory_values else 0,
                "avg": sum(memory_values) / len(memory_values) if memory_values else 0
            },
            "db_connections_stats": {
                "min": min(db_conn_values) if db_conn_values else 0,
                "max": max(db_conn_values) if db_conn_values else 0,
                "avg": sum(db_conn_values) / len(db_conn_values) if db_conn_values else 0
            },
            "response_time_stats": {
                "min": min(response_time_values) if response_time_values else 0,
                "max": max(response_time_values) if response_time_values else 0,
                "avg": sum(response_time_values) / len(response_time_values) if response_time_values else 0
            },
            "sla_violations": self._count_sla_violations(),
            "bottlenecks_detected": self._detect_bottlenecks()
        }
    
    def _count_sla_violations(self) -> Dict[str, int]:
        """Count SLA violations during the test"""
        violations = {
            "cpu_high": 0,
            "memory_high": 0,
            "db_connections_high": 0,
            "response_time_high": 0,
            "error_rate_high": 0
        }
        
        for snapshot in self.snapshots:
            if snapshot.system.cpu_percent > self.alert_thresholds["cpu_percent"]:
                violations["cpu_high"] += 1
            if snapshot.system.memory_percent > self.alert_thresholds["memory_percent"]:
                violations["memory_high"] += 1
            if snapshot.database.total_connections > self.alert_thresholds["db_connections"]:
                violations["db_connections_high"] += 1
            if snapshot.application.response_time_p95 > self.alert_thresholds["response_time_p95"]:
                violations["response_time_high"] += 1
            if snapshot.application.error_rate > self.alert_thresholds["error_rate"]:
                violations["error_rate_high"] += 1
        
        return violations
    
    def _detect_bottlenecks(self) -> List[str]:
        """Detect potential bottlenecks based on metrics patterns"""
        bottlenecks = []
        
        if not self.snapshots:
            return bottlenecks
        
        # Calculate averages
        avg_cpu = sum(s.system.cpu_percent for s in self.snapshots) / len(self.snapshots)
        avg_memory = sum(s.system.memory_percent for s in self.snapshots) / len(self.snapshots)
        avg_db_conn = sum(s.database.total_connections for s in self.snapshots) / len(self.snapshots)
        
        # Detect bottlenecks
        if avg_cpu > 70:
            bottlenecks.append("CPU_BOTTLENECK")
        if avg_memory > 80:
            bottlenecks.append("MEMORY_BOTTLENECK")
        if avg_db_conn > 70:
            bottlenecks.append("DATABASE_CONNECTION_BOTTLENECK")
        
        # Check for I/O bottlenecks
        high_disk_io = any(s.system.disk_io_percent > 80 for s in self.snapshots)
        if high_disk_io:
            bottlenecks.append("DISK_IO_BOTTLENECK")
        
        return bottlenecks
    
    def get_current_metrics(self) -> Optional[PerformanceSnapshot]:
        """Get the most recent performance snapshot"""
        return self.snapshots[-1] if self.snapshots else None
    
    def export_grafana_dashboard(self) -> Dict[str, Any]:
        """Export Grafana dashboard configuration for load test metrics"""
        # This would return a Grafana dashboard JSON configuration
        # for visualizing the load test metrics
        return {
            "dashboard": {
                "title": f"Load Test - {self.session.session_id}",
                "panels": [
                    # CPU panel
                    {
                        "title": "CPU Usage",
                        "type": "graph",
                        "targets": [{"expr": "cpu_percent"}]
                    },
                    # Memory panel
                    {
                        "title": "Memory Usage", 
                        "type": "graph",
                        "targets": [{"expr": "memory_percent"}]
                    },
                    # Database connections panel
                    {
                        "title": "Database Connections",
                        "type": "graph", 
                        "targets": [{"expr": "db_total_connections"}]
                    },
                    # Response time panel
                    {
                        "title": "Response Times",
                        "type": "graph",
                        "targets": [
                            {"expr": "response_time_p50"},
                            {"expr": "response_time_p95"},
                            {"expr": "response_time_p99"}
                        ]
                    }
                ]
            }
        }