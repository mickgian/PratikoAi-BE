"""Query Pattern Analyzer for Automated FAQ Generation.

This service analyzes user query patterns to identify frequently asked questions
that could benefit from automated FAQ generation, optimizing costs and response times.
"""

import asyncio
import hashlib
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.models.faq_automation import FAQ_AUTOMATION_CONFIG, FAQCandidate, QueryCluster, calculate_faq_priority
from app.services.cache import CacheService
from app.services.embedding_service import EmbeddingService
from app.services.query_normalizer import QueryNormalizer

# Custom Exceptions


class InsufficientDataError(Exception):
    """Raised when insufficient data for pattern analysis"""

    pass


class ClusteringFailedError(Exception):
    """Raised when query clustering fails"""

    pass


class PatternAnalysisError(Exception):
    """Base exception for pattern analysis errors"""

    pass


class QueryPatternAnalyzer:
    """Analyzes user query patterns to identify FAQ generation opportunities.

    Uses semantic clustering, cost analysis, and ROI calculations to identify
    queries that would benefit from automated FAQ generation.
    """

    def __init__(
        self,
        db: AsyncSession,
        embedding_service: EmbeddingService,
        normalizer: QueryNormalizer,
        cache_service: CacheService | None = None,
    ):
        self.db = db
        self.embeddings = embedding_service
        self.normalizer = normalizer
        self.cache = cache_service

        # Configuration from FAQ_AUTOMATION_CONFIG
        config = FAQ_AUTOMATION_CONFIG["pattern_analysis"]
        self.min_frequency = config["min_frequency"]
        self.time_window_days = config["time_window_days"]
        self.similarity_threshold = config["similarity_threshold"]
        self.min_quality_score = config["min_quality_score"]

        # Business rules
        business_config = FAQ_AUTOMATION_CONFIG["business_rules"]
        self.min_roi_score = business_config["min_roi_score"]
        self.max_candidates_per_run = business_config["max_candidates_per_run"]
        self.min_monthly_savings = business_config["min_monthly_savings"]

    async def find_faq_candidates(self) -> list[FAQCandidate]:
        """Identify queries that should become FAQs based on pattern analysis.

        Returns:
            List of FAQ candidates sorted by priority score

        Raises:
            InsufficientDataError: If not enough data for analysis
            ClusteringFailedError: If clustering process fails
        """
        logger.info("Starting FAQ candidate analysis...")

        try:
            # Get recent high-quality queries not covered by existing FAQs
            recent_queries = await self._get_uncovered_queries()

            if len(recent_queries) < self.min_frequency:
                raise InsufficientDataError(
                    f"Insufficient queries for analysis: {len(recent_queries)} < {self.min_frequency}"
                )

            logger.info(f"Analyzing {len(recent_queries)} uncovered queries")

            # Cluster similar queries
            clusters = await self._cluster_queries(recent_queries)

            if not clusters:
                logger.warning("No valid clusters found")
                return []

            logger.info(f"Found {len(clusters)} query clusters")

            # Analyze each cluster for FAQ potential
            candidates = []
            for cluster_id, queries in clusters.items():
                if len(queries) >= self.min_frequency:
                    try:
                        candidate = await self._analyze_cluster(cluster_id, queries)
                        if candidate and candidate.roi_score >= self.min_roi_score:
                            candidates.append(candidate)
                    except Exception as e:
                        logger.error(f"Error analyzing cluster {cluster_id}: {e}")
                        continue

            # Sort by priority score
            candidates.sort(key=lambda x: x.priority_score, reverse=True)

            # Limit results
            final_candidates = candidates[: self.max_candidates_per_run]

            logger.info(f"Generated {len(final_candidates)} FAQ candidates")

            return final_candidates

        except Exception as e:
            logger.error(f"FAQ candidate analysis failed: {e}")
            if isinstance(e, InsufficientDataError | ClusteringFailedError):
                raise
            raise PatternAnalysisError(f"Pattern analysis failed: {e}")

    async def _get_uncovered_queries(self) -> list[dict[str, Any]]:
        """Get recent queries not covered by existing FAQs"""
        try:
            # SQL query to get uncovered, high-quality queries
            query = text("""
                SELECT
                    q.id,
                    q.query,
                    q.normalized_query,
                    q.response,
                    q.cost_cents,
                    q.response_time_ms,
                    q.quality_score,
                    q.timestamp,
                    q.user_id,
                    q.category
                FROM query_logs q
                LEFT JOIN faq_coverage fc ON q.normalized_query = fc.normalized_query
                WHERE q.timestamp > NOW() - INTERVAL ':days days'
                AND q.response_cached = FALSE
                AND fc.faq_id IS NULL
                AND q.quality_score >= :min_quality
                AND q.cost_cents > 0
                ORDER BY q.timestamp DESC
                LIMIT 5000
            """)

            result = await self.db.execute(
                query, {"days": self.time_window_days, "min_quality": self.min_quality_score}
            )

            queries = []
            for row in result:
                queries.append(
                    {
                        "id": row.id,
                        "query": row.query,
                        "normalized_query": row.normalized_query,
                        "response": row.response,
                        "cost_cents": row.cost_cents,
                        "response_time_ms": row.response_time_ms,
                        "quality_score": float(row.quality_score),
                        "timestamp": row.timestamp,
                        "user_id": row.user_id,
                        "category": row.category,
                    }
                )

            return queries

        except Exception as e:
            logger.error(f"Error fetching uncovered queries: {e}")
            raise

    async def _cluster_queries(self, queries: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
        """Cluster queries using semantic embeddings.

        Args:
            queries: List of query dictionaries

        Returns:
            Dictionary mapping cluster_id to list of queries

        Raises:
            ClusteringFailedError: If clustering fails
        """
        try:
            if len(queries) < 3:
                return {}

            # Extract normalized queries for embedding
            normalized_texts = [q["normalized_query"] for q in queries]

            # Get embeddings
            logger.info("Generating embeddings for query clustering...")
            embeddings = await self.embeddings.embed_batch(normalized_texts)

            if not embeddings:
                raise ClusteringFailedError("Failed to generate embeddings")

            # Convert to numpy array
            embeddings_array = np.array(embeddings)

            # DBSCAN clustering for variable cluster sizes
            # eps = 1 - similarity_threshold (cosine distance)
            eps = 1 - self.similarity_threshold
            min_samples = max(2, self.min_frequency // 2)

            logger.info(f"Clustering with eps={eps}, min_samples={min_samples}")

            clustering = DBSCAN(eps=eps, min_samples=min_samples, metric="cosine")

            cluster_labels = clustering.fit_predict(embeddings_array)

            # Group queries by cluster
            clusters = {}
            noise_count = 0

            for idx, label in enumerate(cluster_labels):
                if label == -1:  # Noise points
                    noise_count += 1
                    continue

                if label not in clusters:
                    clusters[label] = []
                clusters[label].append(queries[idx])

            logger.info(f"Clustering results: {len(clusters)} clusters, {noise_count} noise points")

            # Filter clusters by minimum size
            valid_clusters = {
                cluster_id: cluster_queries
                for cluster_id, cluster_queries in clusters.items()
                if len(cluster_queries) >= self.min_frequency
            }

            logger.info(f"Valid clusters after filtering: {len(valid_clusters)}")

            return valid_clusters

        except Exception as e:
            logger.error(f"Query clustering failed: {e}")
            raise ClusteringFailedError(f"Clustering failed: {e}")

    async def _analyze_cluster(self, cluster_id: int, queries: list[dict[str, Any]]) -> FAQCandidate | None:
        """Analyze a cluster of similar queries to create an FAQ candidate.

        Args:
            cluster_id: Unique cluster identifier
            queries: List of queries in the cluster

        Returns:
            FAQ candidate or None if not viable
        """
        try:
            if len(queries) < self.min_frequency:
                return None

            # Calculate cluster statistics
            total_cost = sum(q["cost_cents"] for q in queries) / 100.0
            avg_cost = total_cost / len(queries)
            avg_response_time = np.mean([q["response_time_ms"] for q in queries])
            avg_quality = np.mean([q["quality_score"] for q in queries])

            # Find best response (highest quality score)
            best_response = max(queries, key=lambda q: q["quality_score"])

            # Extract query variations (up to 10 examples)
            query_variations = list({q["query"] for q in queries})[:10]

            # Get canonical form (most common normalized query)
            normalized_forms = [q["normalized_query"] for q in queries]
            canonical_query = max(set(normalized_forms), key=normalized_forms.count)

            # Calculate potential savings
            monthly_projections = await self._calculate_monthly_projections(queries)

            if monthly_projections["estimated_savings"] < self.min_monthly_savings:
                logger.debug(f"Cluster {cluster_id} savings too low: {monthly_projections['estimated_savings']}")
                return None

            # Extract tags and categorization
            tags = await self._extract_cluster_tags(queries)
            suggested_category = await self._suggest_category(queries, tags)

            # Generate suggested question
            suggested_question = await self._generate_suggested_question(query_variations, canonical_query)

            # Calculate ROI and priority scores
            roi_score = await self._calculate_roi_score(monthly_projections, avg_quality)
            priority_score = calculate_faq_priority(
                frequency=len(queries), avg_cost_cents=int(avg_cost * 100), quality_score=avg_quality, time_factor=1.0
            )

            # Create FAQ candidate
            candidate = FAQCandidate(
                id=uuid4(),
                cluster_id=None,  # Will be set when cluster is persisted
                suggested_question=suggested_question,
                best_response_content=best_response["response"],
                best_response_id=best_response["id"],
                suggested_category=suggested_category,
                suggested_tags=tags,
                frequency=len(queries),
                estimated_monthly_savings=Decimal(str(monthly_projections["estimated_savings"])),
                roi_score=roi_score,
                priority_score=priority_score,
                status="pending",
                analysis_metadata={
                    "cluster_id": cluster_id,
                    "avg_cost_cents": int(avg_cost * 100),
                    "avg_response_time_ms": int(avg_response_time),
                    "avg_quality_score": avg_quality,
                    "query_variations_count": len(query_variations),
                    "time_window_days": self.time_window_days,
                    "analysis_date": datetime.utcnow().isoformat(),
                },
            )

            # Set expiry (candidates expire after 7 days)
            candidate.expires_at = datetime.utcnow() + timedelta(days=7)

            return candidate

        except Exception as e:
            logger.error(f"Error analyzing cluster {cluster_id}: {e}")
            return None

    async def _calculate_monthly_projections(self, queries: list[dict[str, Any]]) -> dict[str, float]:
        """Calculate monthly cost projections and savings"""
        try:
            # Current costs
            total_cost = sum(q["cost_cents"] for q in queries) / 100.0
            avg_cost = total_cost / len(queries)

            # Project to monthly based on time window
            scaling_factor = 30 / self.time_window_days
            monthly_queries = len(queries) * scaling_factor
            current_monthly_cost = monthly_queries * avg_cost

            # FAQ costs (using GPT-3.5 for variations)
            faq_monthly_cost = monthly_queries * 0.0003  # €0.0003 per variation

            # Calculate savings
            estimated_savings = max(current_monthly_cost - faq_monthly_cost, 0)

            return {
                "monthly_queries": monthly_queries,
                "current_monthly_cost": current_monthly_cost,
                "faq_monthly_cost": faq_monthly_cost,
                "estimated_savings": estimated_savings,
                "savings_percentage": (estimated_savings / current_monthly_cost * 100)
                if current_monthly_cost > 0
                else 0,
            }

        except Exception as e:
            logger.error(f"Error calculating monthly projections: {e}")
            return {
                "monthly_queries": 0,
                "current_monthly_cost": 0,
                "faq_monthly_cost": 0,
                "estimated_savings": 0,
                "savings_percentage": 0,
            }

    async def _extract_cluster_tags(self, queries: list[dict[str, Any]]) -> list[str]:
        """Extract relevant tags from query cluster"""
        try:
            # Common Italian tax and accounting terms
            tax_terms = {
                "iva": ["iva", "imposta", "valore", "aggiunto"],
                "irpef": ["irpef", "reddito", "personale", "fisica"],
                "detrazioni": ["detrazioni", "detraib", "scaricare", "deduc"],
                "fatturazione": ["fattura", "fatturazione", "emissione", "sdi"],
                "contributi": ["contributi", "inps", "previdenza", "gestione"],
                "dichiarazione": ["dichiarazione", "730", "redditi", "presentare"],
                "partita_iva": ["partita", "iva", "piva", "apertura"],
                "regime_forfettario": ["forfettario", "regime", "semplificato"],
                "contabilita": ["contabilità", "registrazioni", "libri", "contabili"],
                "bilancio": ["bilancio", "chiusura", "esercizio", "stato", "patrimoniale"],
            }

            # Analyze query text for matching terms
            all_text = " ".join([q["query"].lower() + " " + q["normalized_query"].lower() for q in queries])

            found_tags = []
            for tag, keywords in tax_terms.items():
                if any(keyword in all_text for keyword in keywords):
                    found_tags.append(tag)

            # Add category-based tags if available
            categories = {q.get("category") for q in queries if q.get("category")}
            for category in categories:
                if category and category.lower() not in found_tags:
                    found_tags.append(category.lower())

            # Limit to most relevant tags
            return found_tags[:8]

        except Exception as e:
            logger.error(f"Error extracting cluster tags: {e}")
            return []

    async def _suggest_category(self, queries: list[dict[str, Any]], tags: list[str]) -> str | None:
        """Suggest FAQ category based on queries and tags"""
        try:
            # Category mapping based on tags
            category_mapping = {
                "IVA": ["iva", "imposta", "aliquota"],
                "IRPEF": ["irpef", "reddito", "addizionale"],
                "Detrazioni": ["detrazioni", "spese", "scaricare"],
                "Fatturazione": ["fattura", "fatturazione", "sdi", "elettronica"],
                "Contributi": ["contributi", "inps", "previdenza"],
                "Dichiarazioni": ["dichiarazione", "730", "redditi"],
                "Partita IVA": ["partita", "iva", "apertura", "chiusura"],
                "Regime Forfettario": ["forfettario", "regime", "semplificato"],
                "Contabilità": ["contabilità", "registrazioni", "libri"],
                "Bilancio": ["bilancio", "chiusura", "esercizio"],
            }

            # Score each category based on tag matches
            category_scores = {}
            for category, keywords in category_mapping.items():
                score = sum(1 for tag in tags if any(keyword in tag for keyword in keywords))
                if score > 0:
                    category_scores[category] = score

            # Return highest scoring category
            if category_scores:
                return max(category_scores.items(), key=lambda x: x[1])[0]

            # Fallback to most common category in queries
            query_categories = [q.get("category") for q in queries if q.get("category")]
            if query_categories:
                return max(set(query_categories), key=query_categories.count)

            return "Generale"

        except Exception as e:
            logger.error(f"Error suggesting category: {e}")
            return "Generale"

    async def _generate_suggested_question(self, query_variations: list[str], canonical_query: str) -> str:
        """Generate a suggested FAQ question from query variations"""
        try:
            # Find the most complete and professional question
            # Prefer questions that:
            # 1. Are properly formed (end with ?)
            # 2. Are not too short or too long
            # 3. Use professional language

            scored_questions = []

            for query in query_variations:
                score = 0
                query_lower = query.lower()

                # Bonus for proper question format
                if query.strip().endswith("?"):
                    score += 3

                # Bonus for professional terms
                professional_terms = [
                    "calcola",
                    "calcolo",
                    "come si",
                    "qual è",
                    "quali sono",
                    "quando",
                    "dove",
                    "perché",
                    "come fare",
                    "come funziona",
                ]
                for term in professional_terms:
                    if term in query_lower:
                        score += 2
                        break

                # Penalty for too short or too long
                word_count = len(query.split())
                if 4 <= word_count <= 15:
                    score += 2
                elif word_count < 4 or word_count > 20:
                    score -= 1

                # Bonus for complete sentences
                if any(starter in query_lower for starter in ["come ", "qual ", "quando ", "dove ", "perché "]):
                    score += 1

                scored_questions.append((query, score))

            # Sort by score and return best question
            scored_questions.sort(key=lambda x: x[1], reverse=True)

            if scored_questions:
                best_question = scored_questions[0][0]

                # Ensure it ends with a question mark
                if not best_question.strip().endswith("?"):
                    best_question += "?"

                return best_question

            # Fallback: create question from canonical query
            canonical_words = canonical_query.replace("_", " ").strip()
            return f"Come {canonical_words}?"

        except Exception as e:
            logger.error(f"Error generating suggested question: {e}")
            return f"Domanda su {canonical_query}"

    async def _calculate_roi_score(self, monthly_projections: dict[str, float], avg_quality: float) -> Decimal:
        """Calculate ROI score for FAQ candidate"""
        try:
            # Base ROI: monthly savings / generation cost
            generation_cost = 0.001  # €0.001 estimated generation cost
            base_roi = monthly_projections["estimated_savings"] / generation_cost

            # Quality multiplier (0.8 to 1.2)
            quality_multiplier = min(max(avg_quality / 0.85, 0.8), 1.2)

            # Volume multiplier (higher volume = higher ROI)
            volume_multiplier = min(monthly_projections["monthly_queries"] / 10, 2.0)

            roi_score = base_roi * quality_multiplier * volume_multiplier

            return Decimal(str(max(roi_score, 0)))

        except Exception as e:
            logger.error(f"Error calculating ROI score: {e}")
            return Decimal("0")

    async def update_cluster_statistics(
        self, cluster: QueryCluster, new_queries: list[dict[str, Any]]
    ) -> QueryCluster:
        """Update existing cluster with new query data"""
        try:
            cluster.update_statistics(new_queries)

            # Recalculate scores
            cluster.roi_score = await self._calculate_roi_score(
                {
                    "estimated_savings": float(cluster.potential_savings_cents / 100),
                    "monthly_queries": cluster.query_count * (30 / self.time_window_days),
                },
                float(cluster.avg_quality_score),
            )

            cluster.priority_score = calculate_faq_priority(
                frequency=cluster.query_count,
                avg_cost_cents=cluster.avg_cost_cents,
                quality_score=float(cluster.avg_quality_score),
            )

            cluster.last_analyzed = datetime.utcnow()

            return cluster

        except Exception as e:
            logger.error(f"Error updating cluster statistics: {e}")
            raise

    async def get_cluster_analysis_summary(self) -> dict[str, Any]:
        """Get summary of cluster analysis results"""
        try:
            # Get cluster statistics from database
            cluster_stats = await self.db.execute(
                select(
                    func.count(QueryCluster.id).label("total_clusters"),
                    func.sum(QueryCluster.query_count).label("total_queries"),
                    func.sum(QueryCluster.potential_savings_cents).label("total_savings_cents"),
                    func.avg(QueryCluster.roi_score).label("avg_roi_score"),
                ).where(QueryCluster.last_analyzed >= datetime.utcnow() - timedelta(days=7))
            )

            stats = cluster_stats.first()

            # Get candidate statistics
            candidate_stats = await self.db.execute(
                select(
                    func.count(FAQCandidate.id).label("total_candidates"),
                    func.count(FAQCandidate.id).filter(FAQCandidate.status == "pending").label("pending_candidates"),
                    func.sum(FAQCandidate.estimated_monthly_savings).label("total_potential_savings"),
                ).where(FAQCandidate.created_at >= datetime.utcnow() - timedelta(days=7))
            )

            candidate_data = candidate_stats.first()

            return {
                "analysis_period": f"Last {self.time_window_days} days",
                "clusters": {
                    "total_clusters": stats.total_clusters or 0,
                    "total_queries": stats.total_queries or 0,
                    "avg_roi_score": float(stats.avg_roi_score or 0),
                    "total_potential_savings": float(stats.total_savings_cents or 0) / 100,
                },
                "candidates": {
                    "total_candidates": candidate_data.total_candidates or 0,
                    "pending_candidates": candidate_data.pending_candidates or 0,
                    "total_potential_savings": float(candidate_data.total_potential_savings or 0),
                },
                "configuration": {
                    "min_frequency": self.min_frequency,
                    "similarity_threshold": self.similarity_threshold,
                    "min_roi_score": self.min_roi_score,
                    "time_window_days": self.time_window_days,
                },
                "last_updated": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error generating analysis summary: {e}")
            return {"error": str(e), "last_updated": datetime.utcnow().isoformat()}
