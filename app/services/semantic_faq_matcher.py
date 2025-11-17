"""Semantic FAQ Matcher for Advanced Vector Search.

Provides semantic matching of FAQs to boost hit rates from 40% to 70%
using vector similarity and Italian language optimization.
"""

import asyncio
import hashlib
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.models.faq_automation import GeneratedFAQ, RSSFAQImpact
from app.services.cache import CacheService
from app.services.embedding_service import EmbeddingService


@dataclass
class FAQMatch:
    """FAQ match result with confidence scoring"""

    faq_id: str
    question: str
    answer: str
    similarity_score: float
    confidence: str  # 'exact', 'high', 'medium', 'low'
    needs_update: bool = False
    matched_concepts: list[str] = None
    source_metadata: dict = None

    def __post_init__(self):
        if self.matched_concepts is None:
            self.matched_concepts = []
        if self.source_metadata is None:
            self.source_metadata = {}


class SemanticFAQMatcher:
    """Advanced semantic FAQ matching system.

    Provides intelligent FAQ matching using:
    - Vector similarity search in Pinecone
    - Confidence-based result filtering
    - Italian language semantic understanding
    - FAQ freshness validation via RSS updates
    - Multi-level similarity thresholds
    """

    def __init__(
        self,
        faq_service,
        embedding_service: EmbeddingService,
        cache_service: CacheService | None = None,
        pinecone_service=None,
        db: AsyncSession | None = None,
    ):
        self.faq = faq_service
        self.embeddings = embedding_service
        self.cache = cache_service
        self.pinecone = pinecone_service
        self.db = db

        # Tunable similarity thresholds
        self.exact_match_threshold = 0.95
        self.high_confidence_threshold = 0.85
        self.medium_confidence_threshold = 0.75
        self.low_confidence_threshold = 0.65

        # Performance and quality settings
        self.max_results_per_search = 20
        self.match_cache_ttl = 1800  # 30 minutes
        self.freshness_check_days = 7
        self.target_hit_rate = 0.70  # 70% target

        # Italian language specific settings
        self.italian_concept_boost = 0.05
        self.professional_term_boost = 0.03

        # Statistics tracking
        self.stats = {"total_queries": 0, "successful_matches": 0, "cache_hits": 0, "avg_similarity_score": 0.0}

    async def find_matching_faqs(
        self,
        query: str,
        max_results: int = 3,
        min_confidence: str = "medium",
        include_outdated: bool = False,
        boost_recent: bool = True,
    ) -> list[FAQMatch]:
        """Find semantically matching FAQs with confidence scoring.

        Args:
            query: User query in Italian
            max_results: Maximum number of FAQ matches to return
            min_confidence: Minimum confidence level ('low', 'medium', 'high', 'exact')
            include_outdated: Include FAQs that may need updates
            boost_recent: Boost recently updated FAQs

        Returns:
            List of FAQ matches ordered by relevance and confidence
        """
        start_time = time.time()
        self.stats["total_queries"] += 1

        try:
            # Check cache first
            cache_key = self._generate_cache_key(query, max_results, min_confidence)
            if self.cache:
                cached_matches = await self.cache.get(cache_key)
                if cached_matches:
                    logger.debug(f"Cache hit for FAQ matching: {query[:50]}...")
                    self.stats["cache_hits"] += 1
                    return cached_matches[:max_results]

            logger.info(f"Semantic FAQ matching for: '{query}'")

            # Generate query embedding
            query_embedding = await self.embeddings.embed(query)
            if not query_embedding:
                logger.warning("Failed to generate query embedding")
                return []

            # Search in vector space
            vector_matches = await self._vector_search_faqs(
                query_embedding,
                max_results * 3,  # Get more for filtering
            )

            if not vector_matches:
                logger.info("No vector matches found")
                return []

            # Process and enrich matches
            faq_matches = []
            for match in vector_matches:
                # Filter by minimum confidence
                confidence_level = self._calculate_confidence(match["score"])
                if not self._meets_min_confidence(confidence_level, min_confidence):
                    continue

                # Retrieve FAQ details
                faq = await self._get_faq_details(match["id"])
                if not faq:
                    continue

                # Check freshness
                needs_update = await self._check_faq_freshness(faq) if self.db else False
                if not include_outdated and needs_update:
                    continue

                # Extract matched concepts
                matched_concepts = self._extract_matched_concepts(
                    query, faq["question"], faq["answer"], match.get("metadata", {})
                )

                # Apply boosting factors
                boosted_score = self._apply_boosting_factors(match["score"], faq, matched_concepts, boost_recent)

                faq_match = FAQMatch(
                    faq_id=match["id"],
                    question=faq["question"],
                    answer=faq["answer"],
                    similarity_score=boosted_score,
                    confidence=confidence_level,
                    needs_update=needs_update,
                    matched_concepts=matched_concepts,
                    source_metadata=faq.get("metadata", {}),
                )

                faq_matches.append(faq_match)

            # Sort by final similarity score
            faq_matches.sort(key=lambda x: x.similarity_score, reverse=True)

            # Limit results
            final_matches = faq_matches[:max_results]

            # Update statistics
            if final_matches:
                self.stats["successful_matches"] += 1
                avg_score = sum(match.similarity_score for match in final_matches) / len(final_matches)
                self.stats["avg_similarity_score"] = (
                    self.stats["avg_similarity_score"] * (self.stats["successful_matches"] - 1) + avg_score
                ) / self.stats["successful_matches"]

            # Cache successful results
            if self.cache and final_matches:
                await self.cache.setex(cache_key, self.match_cache_ttl, final_matches)

            execution_time = (time.time() - start_time) * 1000
            logger.info(f"FAQ matching completed in {execution_time:.1f}ms: {len(final_matches)} matches")

            return final_matches

        except Exception as e:
            logger.error(f"FAQ matching failed for query '{query}': {e}")
            return []

    async def _vector_search_faqs(self, query_embedding: list[float], top_k: int) -> list[dict]:
        """Search FAQs in vector space using Pinecone"""
        try:
            if not self.pinecone:
                logger.warning("Pinecone service not available")
                return []

            # Search in FAQ embeddings namespace
            search_results = self.pinecone.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                filter={
                    "source_type": "faq",
                    "published": True,
                    "approval_status": {"$in": ["auto_approved", "manually_approved"]},
                },
                namespace="faq_embeddings",
            )

            matches = []
            for match in search_results.get("matches", []):
                if match["score"] >= self.low_confidence_threshold:
                    matches.append({"id": match["id"], "score": match["score"], "metadata": match.get("metadata", {})})

            logger.debug(f"Vector search found {len(matches)} FAQ matches above threshold")
            return matches

        except Exception as e:
            logger.error(f"Vector FAQ search failed: {e}")
            return []

    async def _get_faq_details(self, faq_id: str) -> dict | None:
        """Retrieve detailed FAQ information"""
        try:
            if hasattr(self.faq, "get_by_id"):
                faq = await self.faq.get_by_id(faq_id)
                if faq:
                    return {
                        "id": faq_id,
                        "question": faq.question,
                        "answer": faq.answer,
                        "category": getattr(faq, "category", None),
                        "tags": getattr(faq, "tags", []),
                        "updated_at": getattr(faq, "updated_at", None),
                        "usage_count": getattr(faq, "usage_count", 0),
                        "quality_score": getattr(faq, "quality_score", 0.0),
                        "metadata": {},
                    }

            # Fallback: try database query if available
            if self.db:
                query = select(GeneratedFAQ).where(GeneratedFAQ.id == UUID(faq_id))
                result = await self.db.execute(query)
                faq = result.scalar_one_or_none()

                if faq:
                    return {
                        "id": faq_id,
                        "question": faq.question,
                        "answer": faq.answer,
                        "category": faq.category,
                        "tags": faq.tags or [],
                        "updated_at": faq.updated_at,
                        "usage_count": faq.usage_count or 0,
                        "quality_score": float(faq.quality_score or 0.0),
                        "metadata": {},
                    }

            return None

        except Exception as e:
            logger.error(f"Failed to get FAQ details for {faq_id}: {e}")
            return None

    async def _check_faq_freshness(self, faq: dict) -> bool:
        """Check if FAQ might be outdated based on recent RSS updates"""
        if not self.db:
            return False

        try:
            # Check for recent RSS impacts on this FAQ
            recent_cutoff = datetime.utcnow() - timedelta(days=self.freshness_check_days)

            impacts_query = select(RSSFAQImpact).where(
                and_(
                    RSSFAQImpact.faq_id == UUID(faq["id"]),
                    RSSFAQImpact.rss_published_date > recent_cutoff,
                    RSSFAQImpact.impact_level.in_(["medium", "high", "critical"]),
                    RSSFAQImpact.processed is False,
                )
            )

            result = await self.db.execute(impacts_query)
            recent_impacts = result.scalars().all()

            return len(recent_impacts) > 0

        except Exception as e:
            logger.error(f"Error checking FAQ freshness: {e}")
            return False

    def _calculate_confidence(self, similarity_score: float) -> str:
        """Calculate confidence level from similarity score"""
        if similarity_score >= self.exact_match_threshold:
            return "exact"
        elif similarity_score >= self.high_confidence_threshold:
            return "high"
        elif similarity_score >= self.medium_confidence_threshold:
            return "medium"
        else:
            return "low"

    def _meets_min_confidence(self, confidence_level: str, min_confidence: str) -> bool:
        """Check if confidence level meets minimum requirement"""
        confidence_order = ["low", "medium", "high", "exact"]

        try:
            level_index = confidence_order.index(confidence_level)
            min_index = confidence_order.index(min_confidence)
            return level_index >= min_index
        except ValueError:
            return False

    def _extract_matched_concepts(self, query: str, faq_question: str, faq_answer: str, metadata: dict) -> list[str]:
        """Extract concepts that match between query and FAQ"""
        # Normalize texts
        query_lower = query.lower()
        question_lower = faq_question.lower()
        answer_lower = faq_answer.lower()

        # Italian tax concepts
        tax_concepts = [
            "iva",
            "irpef",
            "partita iva",
            "fattura",
            "dichiarazione",
            "reddito",
            "detrazione",
            "deduzione",
            "contributi",
            "regime forfettario",
            "f24",
            "modello 730",
            "codice fiscale",
            "aliquota",
            "imponibile",
            "ritenuta",
            "versamento",
        ]

        matched_concepts = []

        # Find concept matches
        for concept in tax_concepts:
            if concept in query_lower and (concept in question_lower or concept in answer_lower):
                matched_concepts.append(concept)

        # Add metadata concepts if available
        if "concepts" in metadata:
            metadata_concepts = metadata["concepts"]
            if isinstance(metadata_concepts, list):
                for concept in metadata_concepts:
                    if concept.lower() in query_lower and concept not in matched_concepts:
                        matched_concepts.append(concept)

        return matched_concepts[:5]  # Limit to top 5 concepts

    def _apply_boosting_factors(
        self, base_score: float, faq: dict, matched_concepts: list[str], boost_recent: bool
    ) -> float:
        """Apply various boosting factors to the similarity score"""
        boosted_score = base_score

        # Concept matching boost
        if matched_concepts:
            concept_boost = min(len(matched_concepts) * 0.02, 0.10)  # Max 10% boost
            boosted_score += concept_boost

        # Professional terminology boost
        professional_terms = [
            "dichiarazione",
            "versamento",
            "adempimento",
            "normativa",
            "regolamento",
            "circolare",
            "risoluzione",
        ]

        faq_text = (faq["question"] + " " + faq["answer"]).lower()
        professional_matches = sum(1 for term in professional_terms if term in faq_text)
        if professional_matches > 0:
            boosted_score += min(professional_matches * self.professional_term_boost, 0.05)

        # Usage popularity boost
        usage_count = faq.get("usage_count", 0)
        if usage_count > 10:
            usage_boost = min(usage_count / 1000, 0.05)  # Max 5% boost
            boosted_score += usage_boost

        # Quality score boost
        quality_score = faq.get("quality_score", 0.0)
        if quality_score > 0.8:
            quality_boost = (quality_score - 0.8) * 0.1  # Up to 2% boost for quality > 0.8
            boosted_score += quality_boost

        # Recent update boost
        if boost_recent and faq.get("updated_at"):
            try:
                updated_at = faq["updated_at"]
                if isinstance(updated_at, str):
                    updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))

                days_since_update = (datetime.now() - updated_at).days
                if days_since_update < 30:
                    recency_boost = 0.03 * (30 - days_since_update) / 30
                    boosted_score += recency_boost
            except (ValueError, TypeError):
                pass

        # Ensure score doesn't exceed 1.0
        return min(boosted_score, 1.0)

    def _generate_cache_key(self, query: str, max_results: int, min_confidence: str) -> str:
        """Generate cache key for FAQ matching results"""
        key_string = f"{query}|{max_results}|{min_confidence}"
        return f"faq_match:{hashlib.md5(key_string.encode()).hexdigest()}"

    async def get_matching_statistics(self) -> dict[str, Any]:
        """Get FAQ matching performance statistics"""
        try:
            current_hit_rate = (
                self.stats["successful_matches"] / self.stats["total_queries"]
                if self.stats["total_queries"] > 0
                else 0.0
            )

            cache_hit_rate = (
                self.stats["cache_hits"] / self.stats["total_queries"] if self.stats["total_queries"] > 0 else 0.0
            )

            return {
                "total_queries": self.stats["total_queries"],
                "successful_matches": self.stats["successful_matches"],
                "current_hit_rate": round(current_hit_rate, 3),
                "target_hit_rate": self.target_hit_rate,
                "hit_rate_achievement": round(current_hit_rate / self.target_hit_rate, 3)
                if self.target_hit_rate > 0
                else 0,
                "cache_hit_rate": round(cache_hit_rate, 3),
                "avg_similarity_score": round(self.stats["avg_similarity_score"], 3),
                "confidence_thresholds": {
                    "exact": self.exact_match_threshold,
                    "high": self.high_confidence_threshold,
                    "medium": self.medium_confidence_threshold,
                    "low": self.low_confidence_threshold,
                },
                "performance_metrics": {
                    "target_met": current_hit_rate >= self.target_hit_rate,
                    "quality_score": self.stats["avg_similarity_score"],
                },
            }

        except Exception as e:
            logger.error(f"Failed to get matching statistics: {e}")
            return {"error": str(e)}

    def tune_thresholds(
        self,
        exact_threshold: float | None = None,
        high_threshold: float | None = None,
        medium_threshold: float | None = None,
        low_threshold: float | None = None,
    ) -> dict[str, float]:
        """Tune similarity thresholds for optimal performance"""
        if exact_threshold is not None:
            if 0.9 <= exact_threshold <= 1.0:
                self.exact_match_threshold = exact_threshold
            else:
                raise ValueError("Exact threshold must be between 0.9 and 1.0")

        if high_threshold is not None:
            if 0.8 <= high_threshold <= 0.95:
                self.high_confidence_threshold = high_threshold
            else:
                raise ValueError("High threshold must be between 0.8 and 0.95")

        if medium_threshold is not None:
            if 0.7 <= medium_threshold <= 0.85:
                self.medium_confidence_threshold = medium_threshold
            else:
                raise ValueError("Medium threshold must be between 0.7 and 0.85")

        if low_threshold is not None:
            if 0.6 <= low_threshold <= 0.75:
                self.low_confidence_threshold = low_threshold
            else:
                raise ValueError("Low threshold must be between 0.6 and 0.75")

        # Ensure thresholds are properly ordered
        thresholds = [
            self.low_confidence_threshold,
            self.medium_confidence_threshold,
            self.high_confidence_threshold,
            self.exact_match_threshold,
        ]

        if thresholds != sorted(thresholds):
            raise ValueError("Thresholds must be in ascending order")

        logger.info(f"FAQ matching thresholds updated: {thresholds}")

        return {
            "exact": self.exact_match_threshold,
            "high": self.high_confidence_threshold,
            "medium": self.medium_confidence_threshold,
            "low": self.low_confidence_threshold,
        }

    async def batch_match_queries(
        self, queries: list[str], max_results_per_query: int = 3
    ) -> dict[str, list[FAQMatch]]:
        """Batch process multiple queries for FAQ matching"""
        results = {}

        # Process queries with limited concurrency
        semaphore = asyncio.Semaphore(5)  # Limit concurrent requests

        async def match_single_query(query: str) -> tuple[str, list[FAQMatch]]:
            async with semaphore:
                matches = await self.find_matching_faqs(query, max_results_per_query)
                return query, matches

        # Execute all queries
        tasks = [match_single_query(query) for query in queries]
        completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect results
        for task_result in completed_tasks:
            if isinstance(task_result, Exception):
                logger.error(f"Batch FAQ matching error: {task_result}")
                continue

            query, matches = task_result
            results[query] = matches

        logger.info(f"Batch FAQ matching completed: {len(results)} queries processed")

        return results

    def reset_statistics(self):
        """Reset matching statistics"""
        self.stats = {"total_queries": 0, "successful_matches": 0, "cache_hits": 0, "avg_similarity_score": 0.0}

        logger.info("FAQ matching statistics reset")
