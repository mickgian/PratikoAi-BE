"""Database query optimization and connection pool management."""

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool

from app.core.config import settings
from app.core.logging import logger
from app.services.database import database_service


@dataclass
class QueryStats:
    """Query performance statistics."""

    query_hash: str
    query_text: str
    execution_count: int
    total_time: float
    avg_time: float
    min_time: float
    max_time: float
    last_executed: datetime
    rows_affected: int
    cache_hits: int
    cache_misses: int


@dataclass
class IndexRecommendation:
    """Database index recommendation."""

    table_name: str
    columns: list[str]
    index_type: str
    reason: str
    estimated_benefit: float
    query_examples: list[str]


class DatabaseOptimizer:
    """Database performance optimization and monitoring."""

    def __init__(self):
        """Initialize database optimizer."""
        self.query_stats: dict[str, QueryStats] = {}
        self.slow_query_threshold = 1.0  # 1 second
        self.monitoring_enabled = True
        self.stats_retention_days = 30

        # Connection pool monitoring
        self.pool_stats = {
            "connections_created": 0,
            "connections_closed": 0,
            "connections_active": 0,
            "connections_idle": 0,
            "pool_overflows": 0,
            "pool_invalidations": 0,
        }

        # Query optimization settings
        self.optimization_settings = {
            "enable_query_cache": True,
            "enable_connection_pooling": True,
            "max_pool_size": settings.POSTGRES_POOL_SIZE,
            "pool_overflow": settings.POSTGRES_MAX_OVERFLOW,
            "pool_timeout": 30,
            "pool_recycle": 3600,  # 1 hour
            "statement_timeout": 30000,  # 30 seconds
            "idle_in_transaction_timeout": 60000,  # 1 minute
        }

    async def monitor_query(
        self, query: str, parameters: dict[str, Any] | None = None, execution_time: float = 0.0, rows_affected: int = 0
    ) -> str:
        """Monitor query execution and collect statistics.

        Args:
            query: SQL query text
            parameters: Query parameters
            execution_time: Query execution time in seconds
            rows_affected: Number of rows affected

        Returns:
            Query hash for tracking
        """
        try:
            if not self.monitoring_enabled:
                return ""

            # Generate query hash for tracking
            import hashlib

            query_normalized = self._normalize_query(query)
            query_hash = hashlib.md5(query_normalized.encode()).hexdigest()

            # Update query statistics
            if query_hash not in self.query_stats:
                self.query_stats[query_hash] = QueryStats(
                    query_hash=query_hash,
                    query_text=query_normalized,
                    execution_count=0,
                    total_time=0.0,
                    avg_time=0.0,
                    min_time=float("inf"),
                    max_time=0.0,
                    last_executed=datetime.utcnow(),
                    rows_affected=0,
                    cache_hits=0,
                    cache_misses=0,
                )

            stats = self.query_stats[query_hash]
            stats.execution_count += 1
            stats.total_time += execution_time
            stats.avg_time = stats.total_time / stats.execution_count
            stats.min_time = min(stats.min_time, execution_time)
            stats.max_time = max(stats.max_time, execution_time)
            stats.last_executed = datetime.utcnow()
            stats.rows_affected += rows_affected

            # Log slow queries
            if execution_time > self.slow_query_threshold:
                logger.warning(
                    "slow_query_detected",
                    query_hash=query_hash,
                    execution_time=execution_time,
                    query_text=query_normalized[:200] + "..." if len(query_normalized) > 200 else query_normalized,
                    rows_affected=rows_affected,
                )

            # Log query stats periodically
            if stats.execution_count % 100 == 0:
                logger.info(
                    "query_stats_update",
                    query_hash=query_hash,
                    execution_count=stats.execution_count,
                    avg_time=stats.avg_time,
                    total_time=stats.total_time,
                )

            return query_hash

        except Exception as e:
            logger.error(
                "query_monitoring_failed",
                query=query[:100] + "..." if len(query) > 100 else query,
                error=str(e),
                exc_info=True,
            )
            return ""

    def _normalize_query(self, query: str) -> str:
        """Normalize query for consistent tracking."""
        import re

        # Remove extra whitespace
        normalized = re.sub(r"\s+", " ", query.strip())

        # Replace parameter placeholders with generic markers
        normalized = re.sub(r"\$\d+", "?", normalized)  # PostgreSQL parameters
        normalized = re.sub(r":\w+", "?", normalized)  # Named parameters
        normalized = re.sub(r"'[^']*'", "'?'", normalized)  # String literals
        normalized = re.sub(r"\b\d+\b", "?", normalized)  # Numeric literals

        return normalized.upper()

    async def optimize_connection_pool(self) -> dict[str, Any]:
        """Optimize database connection pool settings.

        Returns:
            Pool optimization results
        """
        try:
            optimization_results = {
                "previous_settings": {},
                "new_settings": {},
                "improvements": [],
                "optimization_applied": False,
            }

            # Get current pool statistics
            current_stats = await self.get_pool_statistics()

            # Analyze pool usage patterns
            if current_stats.get("pool_overflows", 0) > 10:
                # Increase pool size if there are frequent overflows
                new_pool_size = min(self.optimization_settings["max_pool_size"] + 5, 50)
                optimization_results["improvements"].append(
                    f"Increased pool size from {self.optimization_settings['max_pool_size']} to {new_pool_size}"
                )
                optimization_results["previous_settings"]["max_pool_size"] = self.optimization_settings[
                    "max_pool_size"
                ]
                self.optimization_settings["max_pool_size"] = new_pool_size
                optimization_results["new_settings"]["max_pool_size"] = new_pool_size
                optimization_results["optimization_applied"] = True

            # Optimize pool timeout based on query patterns
            avg_query_time = self._calculate_average_query_time()
            if avg_query_time > 5.0:  # If average query time is high
                new_timeout = max(int(avg_query_time * 10), 60)
                optimization_results["improvements"].append(
                    f"Increased pool timeout from {self.optimization_settings['pool_timeout']} to {new_timeout}"
                )
                optimization_results["previous_settings"]["pool_timeout"] = self.optimization_settings["pool_timeout"]
                self.optimization_settings["pool_timeout"] = new_timeout
                optimization_results["new_settings"]["pool_timeout"] = new_timeout
                optimization_results["optimization_applied"] = True

            # Optimize connection recycling
            if current_stats.get("long_running_connections", 0) > 5:
                new_recycle_time = 1800  # 30 minutes
                optimization_results["improvements"].append(
                    f"Reduced connection recycle time from {self.optimization_settings['pool_recycle']} to {new_recycle_time}"
                )
                optimization_results["previous_settings"]["pool_recycle"] = self.optimization_settings["pool_recycle"]
                self.optimization_settings["pool_recycle"] = new_recycle_time
                optimization_results["new_settings"]["pool_recycle"] = new_recycle_time
                optimization_results["optimization_applied"] = True

            logger.info(
                "connection_pool_optimization_completed",
                improvements_count=len(optimization_results["improvements"]),
                optimization_applied=optimization_results["optimization_applied"],
            )

            return optimization_results

        except Exception as e:
            logger.error("connection_pool_optimization_failed", error=str(e), exc_info=True)
            return {"error": str(e), "optimization_applied": False}

    def _calculate_average_query_time(self) -> float:
        """Calculate average query execution time."""
        if not self.query_stats:
            return 0.0

        total_time = sum(stats.avg_time for stats in self.query_stats.values())
        return total_time / len(self.query_stats)

    async def analyze_slow_queries(self, limit: int = 10) -> list[QueryStats]:
        """Analyze slow queries and provide optimization recommendations.

        Args:
            limit: Maximum number of slow queries to return

        Returns:
            List of slow query statistics
        """
        try:
            # Sort queries by average execution time
            slow_queries = sorted(self.query_stats.values(), key=lambda x: x.avg_time, reverse=True)[:limit]

            # Filter queries that are actually slow
            slow_queries = [q for q in slow_queries if q.avg_time > self.slow_query_threshold]

            for query in slow_queries:
                logger.info(
                    "slow_query_analysis",
                    query_hash=query.query_hash,
                    avg_time=query.avg_time,
                    execution_count=query.execution_count,
                    total_time=query.total_time,
                    query_text=query.query_text[:200] + "..." if len(query.query_text) > 200 else query.query_text,
                )

            return slow_queries

        except Exception as e:
            logger.error("slow_query_analysis_failed", error=str(e), exc_info=True)
            return []

    async def generate_index_recommendations(self) -> list[IndexRecommendation]:
        """Generate database index recommendations based on query patterns.

        Returns:
            List of index recommendations
        """
        try:
            recommendations = []

            # Analyze query patterns for index opportunities
            for stats in self.query_stats.values():
                if stats.avg_time > self.slow_query_threshold and stats.execution_count > 10:
                    # Simple pattern matching for common optimization opportunities
                    query_text = stats.query_text.upper()

                    # Look for WHERE clauses without indexes
                    if "WHERE" in query_text and "=" in query_text:
                        # Extract table and column information (simplified)
                        table_match = self._extract_table_from_query(query_text)
                        column_match = self._extract_where_columns(query_text)

                        if table_match and column_match:
                            recommendations.append(
                                IndexRecommendation(
                                    table_name=table_match,
                                    columns=column_match,
                                    index_type="btree",
                                    reason=f"Frequent WHERE clause usage (executed {stats.execution_count} times)",
                                    estimated_benefit=min(stats.avg_time * 0.7, 5.0),  # Estimated time savings
                                    query_examples=[stats.query_text[:200]],
                                )
                            )

                    # Look for ORDER BY clauses
                    if "ORDER BY" in query_text:
                        table_match = self._extract_table_from_query(query_text)
                        order_columns = self._extract_order_by_columns(query_text)

                        if table_match and order_columns:
                            recommendations.append(
                                IndexRecommendation(
                                    table_name=table_match,
                                    columns=order_columns,
                                    index_type="btree",
                                    reason=f"Frequent ORDER BY usage (executed {stats.execution_count} times)",
                                    estimated_benefit=min(stats.avg_time * 0.5, 3.0),
                                    query_examples=[stats.query_text[:200]],
                                )
                            )

                    # Look for JOIN operations
                    if "JOIN" in query_text:
                        join_info = self._extract_join_info(query_text)
                        if join_info:
                            for table, columns in join_info.items():
                                recommendations.append(
                                    IndexRecommendation(
                                        table_name=table,
                                        columns=columns,
                                        index_type="btree",
                                        reason=f"Frequent JOIN usage (executed {stats.execution_count} times)",
                                        estimated_benefit=min(stats.avg_time * 0.6, 4.0),
                                        query_examples=[stats.query_text[:200]],
                                    )
                                )

            # Remove duplicate recommendations
            unique_recommendations = []
            seen_combinations = set()

            for rec in recommendations:
                key = (rec.table_name, tuple(sorted(rec.columns)))
                if key not in seen_combinations:
                    seen_combinations.add(key)
                    unique_recommendations.append(rec)

            # Sort by estimated benefit
            unique_recommendations.sort(key=lambda x: x.estimated_benefit, reverse=True)

            logger.info(
                "index_recommendations_generated",
                recommendations_count=len(unique_recommendations),
                total_potential_benefit=sum(r.estimated_benefit for r in unique_recommendations[:10]),
            )

            return unique_recommendations[:10]  # Return top 10 recommendations

        except Exception as e:
            logger.error("index_recommendation_generation_failed", error=str(e), exc_info=True)
            return []

    def _extract_table_from_query(self, query: str) -> str | None:
        """Extract primary table name from query."""
        import re

        # Look for FROM clause
        from_match = re.search(r"FROM\s+(\w+)", query)
        if from_match:
            return from_match.group(1).lower()

        # Look for UPDATE clause
        update_match = re.search(r"UPDATE\s+(\w+)", query)
        if update_match:
            return update_match.group(1).lower()

        # Look for INSERT INTO clause
        insert_match = re.search(r"INSERT\s+INTO\s+(\w+)", query)
        if insert_match:
            return insert_match.group(1).lower()

        return None

    def _extract_where_columns(self, query: str) -> list[str]:
        """Extract column names from WHERE clauses."""
        import re

        columns = []

        # Simple pattern for WHERE column = value
        where_patterns = [r"WHERE\s+(\w+)\s*=", r"AND\s+(\w+)\s*=", r"OR\s+(\w+)\s*="]

        for pattern in where_patterns:
            matches = re.findall(pattern, query)
            columns.extend([match.lower() for match in matches])

        return list(set(columns))  # Remove duplicates

    def _extract_order_by_columns(self, query: str) -> list[str]:
        """Extract column names from ORDER BY clauses."""
        import re

        order_match = re.search(r"ORDER\s+BY\s+([\w\s,]+)", query)
        if order_match:
            columns_text = order_match.group(1)
            columns = []
            for col in columns_text.split(","):
                col_name = col.strip().split()[0]  # Remove ASC/DESC
                if col_name and col_name.isalpha():
                    columns.append(col_name.lower())
            return columns

        return []

    def _extract_join_info(self, query: str) -> dict[str, list[str]]:
        """Extract JOIN information from query."""
        import re

        join_info = {}

        # Look for JOIN clauses
        join_pattern = r"JOIN\s+(\w+)\s+.*?ON\s+(\w+)\.(\w+)\s*=\s*(\w+)\.(\w+)"
        matches = re.findall(join_pattern, query)

        for match in matches:
            table1, table1_col, table2, table2_col = match[1], match[2], match[3], match[4]

            if table1 not in join_info:
                join_info[table1] = []
            if table2 not in join_info:
                join_info[table2] = []

            join_info[table1].append(table1_col.lower())
            join_info[table2].append(table2_col.lower())

        return join_info

    async def get_pool_statistics(self) -> dict[str, Any]:
        """Get database connection pool statistics.

        Returns:
            Pool statistics
        """
        try:
            # This would integrate with actual SQLAlchemy pool statistics
            # For now, return simulated statistics
            stats = {
                **self.pool_stats,
                "pool_size": self.optimization_settings["max_pool_size"],
                "pool_overflow": self.optimization_settings["pool_overflow"],
                "pool_timeout": self.optimization_settings["pool_timeout"],
                "checked_in": 15,
                "checked_out": 5,
                "overflow": 2,
                "invalidated": 0,
                "connection_efficiency": 0.85,
                "avg_connection_age": 1800,  # seconds
                "long_running_connections": 2,
            }

            logger.debug(
                "pool_statistics_retrieved",
                active_connections=stats["connections_active"],
                pool_size=stats["pool_size"],
                efficiency=stats["connection_efficiency"],
            )

            return stats

        except Exception as e:
            logger.error("pool_statistics_retrieval_failed", error=str(e), exc_info=True)
            return {}

    async def optimize_query_execution(self, query: str, parameters: dict | None = None) -> tuple[str, dict]:
        """Optimize query execution with caching and performance hints.

        Args:
            query: SQL query to optimize
            parameters: Query parameters

        Returns:
            Tuple of (optimized_query, execution_hints)
        """
        try:
            optimized_query = query
            execution_hints = {
                "use_cache": False,
                "cache_ttl": 0,
                "execution_plan": "default",
                "optimization_applied": False,
            }

            # Add query hints for common patterns
            query_upper = query.upper()

            # Add LIMIT for potentially large result sets
            if "SELECT" in query_upper and "LIMIT" not in query_upper and "COUNT(" not in query_upper:
                if "ORDER BY" in query_upper:
                    # Add reasonable limit for ordered queries
                    optimized_query += " LIMIT 1000"
                    execution_hints["optimization_applied"] = True
                    execution_hints["optimization_reason"] = "Added LIMIT to prevent large result sets"

            # Enable caching for read-only queries
            if query_upper.startswith("SELECT") and "NOW()" not in query_upper:
                execution_hints["use_cache"] = True
                execution_hints["cache_ttl"] = 300  # 5 minutes

            # Add execution plan hints for complex queries
            if query_upper.count("JOIN") > 2:
                execution_hints["execution_plan"] = "nested_loop"
            elif "GROUP BY" in query_upper and "ORDER BY" in query_upper:
                execution_hints["execution_plan"] = "hash_aggregate"

            return optimized_query, execution_hints

        except Exception as e:
            logger.error(
                "query_optimization_failed",
                query=query[:100] + "..." if len(query) > 100 else query,
                error=str(e),
                exc_info=True,
            )
            return query, {"optimization_applied": False, "error": str(e)}

    async def cleanup_old_statistics(self) -> int:
        """Clean up old query statistics.

        Returns:
            Number of statistics entries cleaned up
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=self.stats_retention_days)
            cleaned_count = 0

            # Remove old statistics
            old_hashes = [
                hash_key for hash_key, stats in self.query_stats.items() if stats.last_executed < cutoff_date
            ]

            for hash_key in old_hashes:
                del self.query_stats[hash_key]
                cleaned_count += 1

            if cleaned_count > 0:
                logger.info(
                    "query_statistics_cleaned", cleaned_count=cleaned_count, remaining_count=len(self.query_stats)
                )

            return cleaned_count

        except Exception as e:
            logger.error("statistics_cleanup_failed", error=str(e), exc_info=True)
            return 0

    def get_performance_summary(self) -> dict[str, Any]:
        """Get comprehensive performance summary.

        Returns:
            Performance summary statistics
        """
        try:
            if not self.query_stats:
                return {"status": "no_data", "message": "No query statistics available"}

            total_queries = len(self.query_stats)
            total_executions = sum(stats.execution_count for stats in self.query_stats.values())
            total_time = sum(stats.total_time for stats in self.query_stats.values())
            avg_query_time = total_time / total_executions if total_executions > 0 else 0

            slow_queries = [stats for stats in self.query_stats.values() if stats.avg_time > self.slow_query_threshold]

            summary = {
                "monitoring_status": "active" if self.monitoring_enabled else "inactive",
                "total_unique_queries": total_queries,
                "total_executions": total_executions,
                "total_execution_time": round(total_time, 2),
                "average_query_time": round(avg_query_time, 4),
                "slow_queries_count": len(slow_queries),
                "slow_query_threshold": self.slow_query_threshold,
                "top_slow_queries": [
                    {
                        "query_hash": q.query_hash,
                        "avg_time": round(q.avg_time, 4),
                        "execution_count": q.execution_count,
                        "query_preview": q.query_text[:100] + "..." if len(q.query_text) > 100 else q.query_text,
                    }
                    for q in sorted(slow_queries, key=lambda x: x.avg_time, reverse=True)[:5]
                ],
                "most_frequent_queries": [
                    {
                        "query_hash": q.query_hash,
                        "execution_count": q.execution_count,
                        "avg_time": round(q.avg_time, 4),
                        "query_preview": q.query_text[:100] + "..." if len(q.query_text) > 100 else q.query_text,
                    }
                    for q in sorted(self.query_stats.values(), key=lambda x: x.execution_count, reverse=True)[:5]
                ],
                "optimization_settings": self.optimization_settings,
                "pool_stats": self.pool_stats,
            }

            return summary

        except Exception as e:
            logger.error("performance_summary_generation_failed", error=str(e), exc_info=True)
            return {"error": str(e), "status": "error"}


# Global instance
database_optimizer = DatabaseOptimizer()
