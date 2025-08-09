"""
CCNL Search Indexing Service.

This service manages search indexes and optimizations for fast CCNL queries,
including full-text indexes, caching, and pre-computed aggregations.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
import hashlib

from sqlalchemy import select, text, Index, func
from sqlalchemy.dialects.postgresql import TSVECTOR, TSQUERY
import redis

from app.models.ccnl_data import CCNLSector, WorkerCategory, GeographicArea
from app.models.ccnl_database import (
    CCNLAgreementDB, CCNLSectorDB, JobLevelDB,
    SalaryTableDB, SpecialAllowanceDB
)
from app.services.database import database_service
from app.services.cache import cache_service
from app.core.logging import logger
from app.core.config import settings


@dataclass
class IndexingStats:
    """Statistics for indexing operations."""
    total_documents: int = 0
    indexed_documents: int = 0
    failed_documents: int = 0
    index_time_seconds: float = 0.0
    last_indexed: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate indexing success rate."""
        if self.total_documents == 0:
            return 0.0
        return (self.indexed_documents / self.total_documents) * 100


@dataclass
class SearchIndex:
    """Represents a search index configuration."""
    name: str
    table_name: str
    columns: List[str]
    weights: Dict[str, str] = field(default_factory=dict)
    language: str = "italian"
    
    def get_tsvector_expression(self) -> str:
        """Generate PostgreSQL tsvector expression."""
        expressions = []
        for column in self.columns:
            weight = self.weights.get(column, 'D')
            expressions.append(
                f"setweight(to_tsvector('{self.language}', COALESCE({column}, '')), '{weight}')"
            )
        return " || ".join(expressions)


class CCNLIndexingService:
    """Service for managing CCNL search indexes."""
    
    def __init__(self):
        """Initialize indexing service."""
        self.logger = logger
        self.cache_prefix = "ccnl_index:"
        self.aggregation_cache_ttl = 3600  # 1 hour
        
        # Define search indexes
        self.indexes = [
            SearchIndex(
                name="ccnl_agreements_search",
                table_name="ccnl_agreements",
                columns=["name", "sector_code"],
                weights={"name": "A", "sector_code": "B"}
            ),
            SearchIndex(
                name="job_levels_search",
                table_name="ccnl_job_levels",
                columns=["level_name", "description", "typical_tasks"],
                weights={"level_name": "A", "description": "B", "typical_tasks": "C"}
            ),
            SearchIndex(
                name="allowances_search",
                table_name="ccnl_special_allowances",
                columns=["allowance_type", "conditions"],
                weights={"allowance_type": "A", "conditions": "C"}
            )
        ]
    
    async def create_indexes(self) -> IndexingStats:
        """Create or update all search indexes."""
        stats = IndexingStats()
        start_time = datetime.utcnow()
        
        try:
            with database_service.get_session_maker() as session:
                for index_config in self.indexes:
                    try:
                        # Create GIN index for full-text search
                        index_name = f"idx_{index_config.name}"
                        tsvector_expr = index_config.get_tsvector_expression()
                        
                        # Drop existing index if exists
                        session.execute(text(f"DROP INDEX IF EXISTS {index_name}"))
                        
                        # Create new index
                        create_index_sql = f"""
                        CREATE INDEX {index_name} ON {index_config.table_name}
                        USING gin(({tsvector_expr}))
                        """
                        session.execute(text(create_index_sql))
                        
                        stats.indexed_documents += 1
                        self.logger.info(f"Created index: {index_name}")
                        
                    except Exception as e:
                        stats.failed_documents += 1
                        self.logger.error(f"Failed to create index {index_config.name}: {e}")
                
                # Create additional performance indexes
                await self._create_performance_indexes(session)
                
                session.commit()
                
        except Exception as e:
            self.logger.error(f"Indexing error: {e}")
            stats.failed_documents += 1
        
        stats.index_time_seconds = (datetime.utcnow() - start_time).total_seconds()
        stats.last_indexed = datetime.utcnow()
        stats.total_documents = len(self.indexes)
        
        # Cache indexing stats
        await self._cache_indexing_stats(stats)
        
        return stats
    
    async def _create_performance_indexes(self, session):
        """Create additional indexes for query performance."""
        performance_indexes = [
            # Composite indexes for common queries
            "CREATE INDEX IF NOT EXISTS idx_agreements_sector_dates ON ccnl_agreements(sector_code, valid_from, valid_to)",
            "CREATE INDEX IF NOT EXISTS idx_salary_agreement_level_area ON ccnl_salary_tables(agreement_id, level_code, geographic_area)",
            "CREATE INDEX IF NOT EXISTS idx_job_levels_agreement_category ON ccnl_job_levels(agreement_id, worker_category)",
            
            # Partial indexes for active agreements
            "CREATE INDEX IF NOT EXISTS idx_agreements_active ON ccnl_agreements(sector_code) WHERE valid_to IS NULL OR valid_to >= CURRENT_DATE",
            
            # Indexes for salary range queries
            "CREATE INDEX IF NOT EXISTS idx_salary_amount ON ccnl_salary_tables(base_monthly_salary)",
            
            # Geographic coverage
            "CREATE INDEX IF NOT EXISTS idx_salary_geographic ON ccnl_salary_tables(geographic_area)",
            
            # Worker category coverage
            "CREATE INDEX IF NOT EXISTS idx_job_levels_category ON ccnl_job_levels(worker_category)"
        ]
        
        for index_sql in performance_indexes:
            try:
                session.execute(text(index_sql))
                self.logger.info(f"Created performance index: {index_sql.split(' ')[5]}")
            except Exception as e:
                self.logger.warning(f"Could not create index: {e}")
    
    async def update_search_vectors(self) -> int:
        """Update pre-computed search vectors for better performance."""
        updated_count = 0
        
        try:
            with database_service.get_session_maker() as session:
                # Add search vector columns if they don't exist
                alter_statements = [
                    """
                    ALTER TABLE ccnl_agreements 
                    ADD COLUMN IF NOT EXISTS search_vector tsvector
                    """,
                    """
                    ALTER TABLE ccnl_job_levels 
                    ADD COLUMN IF NOT EXISTS search_vector tsvector
                    """,
                    """
                    ALTER TABLE ccnl_special_allowances 
                    ADD COLUMN IF NOT EXISTS search_vector tsvector
                    """
                ]
                
                for stmt in alter_statements:
                    session.execute(text(stmt))
                
                # Update search vectors
                update_statements = [
                    """
                    UPDATE ccnl_agreements 
                    SET search_vector = to_tsvector('italian', 
                        COALESCE(name, '') || ' ' || 
                        COALESCE(sector_code, '')
                    )
                    """,
                    """
                    UPDATE ccnl_job_levels 
                    SET search_vector = to_tsvector('italian',
                        COALESCE(level_name, '') || ' ' ||
                        COALESCE(description, '') || ' ' ||
                        COALESCE(typical_tasks::text, '')
                    )
                    """,
                    """
                    UPDATE ccnl_special_allowances
                    SET search_vector = to_tsvector('italian',
                        COALESCE(allowance_type, '') || ' ' ||
                        COALESCE(conditions::text, '')
                    )
                    """
                ]
                
                for stmt in update_statements:
                    result = session.execute(text(stmt))
                    updated_count += result.rowcount
                
                session.commit()
                
                self.logger.info(f"Updated {updated_count} search vectors")
                
        except Exception as e:
            self.logger.error(f"Error updating search vectors: {e}")
        
        return updated_count
    
    async def pre_compute_aggregations(self) -> Dict[str, Any]:
        """Pre-compute common aggregations for fast retrieval."""
        aggregations = {}
        
        try:
            with database_service.get_session_maker() as session:
                # Sector statistics
                sector_stats = session.exec(
                    select(
                        CCNLAgreementDB.sector_code,
                        func.count(CCNLAgreementDB.id).label("agreement_count"),
                        func.min(SalaryTableDB.base_monthly_salary).label("min_salary"),
                        func.max(SalaryTableDB.base_monthly_salary).label("max_salary"),
                        func.avg(SalaryTableDB.base_monthly_salary).label("avg_salary")
                    ).join(
                        SalaryTableDB, CCNLAgreementDB.id == SalaryTableDB.agreement_id
                    ).group_by(CCNLAgreementDB.sector_code)
                ).all()
                
                aggregations["sector_stats"] = {
                    stat[0]: {
                        "agreement_count": stat[1],
                        "min_salary": float(stat[2]) if stat[2] else 0,
                        "max_salary": float(stat[3]) if stat[3] else 0,
                        "avg_salary": float(stat[4]) if stat[4] else 0
                    }
                    for stat in sector_stats
                }
                
                # Geographic distribution
                geo_stats = session.exec(
                    select(
                        SalaryTableDB.geographic_area,
                        func.count(func.distinct(SalaryTableDB.agreement_id)).label("agreement_count"),
                        func.avg(SalaryTableDB.base_monthly_salary).label("avg_salary")
                    ).group_by(SalaryTableDB.geographic_area)
                ).all()
                
                aggregations["geographic_stats"] = {
                    stat[0]: {
                        "agreement_count": stat[1],
                        "avg_salary": float(stat[2]) if stat[2] else 0
                    }
                    for stat in geo_stats
                }
                
                # Worker category distribution
                category_stats = session.exec(
                    select(
                        JobLevelDB.worker_category,
                        func.count(func.distinct(JobLevelDB.agreement_id)).label("agreement_count"),
                        func.count(JobLevelDB.id).label("level_count")
                    ).group_by(JobLevelDB.worker_category)
                ).all()
                
                aggregations["category_stats"] = {
                    stat[0]: {
                        "agreement_count": stat[1],
                        "level_count": stat[2]
                    }
                    for stat in category_stats
                }
                
                # Cache aggregations
                for key, value in aggregations.items():
                    cache_key = f"{self.cache_prefix}aggregation:{key}"
                    await cache_service.set(
                        cache_key,
                        json.dumps(value),
                        ttl=self.aggregation_cache_ttl
                    )
                
                self.logger.info("Pre-computed aggregations cached successfully")
                
        except Exception as e:
            self.logger.error(f"Error computing aggregations: {e}")
        
        return aggregations
    
    async def get_cached_aggregation(self, aggregation_type: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached aggregation data."""
        cache_key = f"{self.cache_prefix}aggregation:{aggregation_type}"
        
        cached_data = await cache_service.get(cache_key)
        if cached_data:
            return json.loads(cached_data)
        
        # Recompute if not cached
        aggregations = await self.pre_compute_aggregations()
        return aggregations.get(aggregation_type)
    
    async def warm_search_cache(self, popular_queries: List[str]) -> int:
        """Warm cache with popular search queries."""
        warmed_count = 0
        
        for query in popular_queries:
            try:
                # Generate cache key
                query_hash = hashlib.md5(query.encode()).hexdigest()
                cache_key = f"{self.cache_prefix}query:{query_hash}"
                
                # Check if already cached
                if await cache_service.exists(cache_key):
                    continue
                
                # Execute search to populate cache
                # This would call the actual search service
                # For now, we'll simulate with a placeholder
                result = {"query": query, "cached_at": datetime.utcnow().isoformat()}
                
                await cache_service.set(
                    cache_key,
                    json.dumps(result),
                    ttl=3600  # 1 hour cache
                )
                
                warmed_count += 1
                
            except Exception as e:
                self.logger.error(f"Error warming cache for query '{query}': {e}")
        
        self.logger.info(f"Warmed cache with {warmed_count} queries")
        return warmed_count
    
    async def analyze_search_patterns(self) -> Dict[str, Any]:
        """Analyze search patterns to optimize indexes."""
        analysis = {
            "most_searched_sectors": [],
            "common_salary_ranges": [],
            "frequent_geographic_areas": [],
            "popular_keywords": [],
            "average_query_complexity": 0
        }
        
        # In a real implementation, this would analyze search logs
        # For now, return sample analysis
        analysis["most_searched_sectors"] = [
            {"sector": "metalmeccanici_industria", "count": 1250},
            {"sector": "commercio_terziario", "count": 980},
            {"sector": "edilizia_industria", "count": 756}
        ]
        
        analysis["common_salary_ranges"] = [
            {"range": "1500-2000", "count": 450},
            {"range": "2000-3000", "count": 380},
            {"range": "3000-5000", "count": 210}
        ]
        
        return analysis
    
    async def optimize_slow_queries(self, threshold_ms: int = 500) -> List[Dict[str, Any]]:
        """Identify and optimize slow queries."""
        slow_queries = []
        
        try:
            with database_service.get_session_maker() as session:
                # Get PostgreSQL slow query log (if available)
                # This is a simplified version
                result = session.execute(
                    text("""
                    SELECT query, mean_exec_time, calls
                    FROM pg_stat_statements
                    WHERE mean_exec_time > :threshold
                    AND query LIKE '%ccnl%'
                    ORDER BY mean_exec_time DESC
                    LIMIT 10
                    """),
                    {"threshold": threshold_ms}
                )
                
                for row in result:
                    slow_queries.append({
                        "query": row[0][:100] + "...",  # Truncate long queries
                        "avg_time_ms": row[1],
                        "execution_count": row[2],
                        "optimization_hint": self._get_optimization_hint(row[0])
                    })
                    
        except Exception as e:
            self.logger.warning(f"Could not analyze slow queries: {e}")
        
        return slow_queries
    
    def _get_optimization_hint(self, query: str) -> str:
        """Get optimization hints for slow queries."""
        query_lower = query.lower()
        
        if "join" in query_lower and "salary" in query_lower:
            return "Consider adding composite index on salary table joins"
        elif "like" in query_lower:
            return "Consider using full-text search instead of LIKE patterns"
        elif "order by" in query_lower and "limit" not in query_lower:
            return "Consider adding LIMIT to sorted queries"
        else:
            return "Analyze query execution plan for optimization opportunities"
    
    async def _cache_indexing_stats(self, stats: IndexingStats):
        """Cache indexing statistics."""
        cache_key = f"{self.cache_prefix}stats:indexing"
        stats_data = {
            "total_documents": stats.total_documents,
            "indexed_documents": stats.indexed_documents,
            "failed_documents": stats.failed_documents,
            "index_time_seconds": stats.index_time_seconds,
            "last_indexed": stats.last_indexed.isoformat() if stats.last_indexed else None,
            "success_rate": stats.success_rate
        }
        
        await cache_service.set(
            cache_key,
            json.dumps(stats_data),
            ttl=86400  # 24 hours
        )
    
    async def get_index_health(self) -> Dict[str, Any]:
        """Check health of search indexes."""
        health = {
            "status": "healthy",
            "indexes": {},
            "issues": []
        }
        
        try:
            with database_service.get_session_maker() as session:
                # Check each index
                for index_config in self.indexes:
                    index_name = f"idx_{index_config.name}"
                    
                    # Check if index exists
                    result = session.execute(
                        text("""
                        SELECT 1 FROM pg_indexes 
                        WHERE indexname = :index_name
                        """),
                        {"index_name": index_name}
                    ).first()
                    
                    if result:
                        health["indexes"][index_name] = "active"
                    else:
                        health["indexes"][index_name] = "missing"
                        health["issues"].append(f"Index {index_name} is missing")
                        health["status"] = "degraded"
                
                # Check index bloat
                bloat_result = session.execute(
                    text("""
                    SELECT schemaname, tablename, indexname, 
                           pg_size_pretty(pg_relation_size(indexrelid)) as index_size
                    FROM pg_stat_user_indexes
                    WHERE schemaname = 'public'
                    AND indexname LIKE 'idx_ccnl%'
                    """)
                ).all()
                
                for row in bloat_result:
                    size_info = f"{row[2]}: {row[3]}"
                    health["indexes"][row[2]] = {"status": "active", "size": row[3]}
                
        except Exception as e:
            health["status"] = "error"
            health["issues"].append(f"Error checking indexes: {str(e)}")
        
        return health
    
    async def rebuild_index(self, index_name: str) -> bool:
        """Rebuild a specific index."""
        try:
            with database_service.get_session_maker() as session:
                # Use REINDEX for PostgreSQL
                session.execute(text(f"REINDEX INDEX {index_name}"))
                session.commit()
                
                self.logger.info(f"Successfully rebuilt index: {index_name}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error rebuilding index {index_name}: {e}")
            return False


# Service instance
ccnl_indexing_service = CCNLIndexingService()