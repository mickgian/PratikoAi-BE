"""Multi-Source Context Builder for Advanced Vector Search.

Builds rich context from multiple sources (FAQs, regulations, knowledge base)
to improve answer quality and provide comprehensive responses.
"""

import asyncio
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.core.logging import logger
from app.services.hybrid_search_engine import HybridSearchEngine, SearchResult


@dataclass
class ContextPart:
    """Single piece of context from a source"""

    source_type: str
    content: str
    relevance_score: float
    metadata: dict
    token_count: int
    excerpt_start: int = 0
    excerpt_end: int = -1


@dataclass
class QueryContext:
    """Complete context assembled for a query"""

    query: str
    context_parts: list[ContextPart]
    total_tokens: int
    sources_used: int
    context_quality_score: float
    assembly_time_ms: float
    source_distribution: dict[str, int]


class MultiSourceContextBuilder:
    """Advanced context builder that assembles information from multiple sources.

    Provides intelligent context assembly with:
    - Source prioritization (FAQ > Regulation > Knowledge)
    - Token budget management
    - Relevance-based content extraction
    - Date-based content weighting
    - Italian language content optimization
    """

    def __init__(self, hybrid_search: HybridSearchEngine, max_context_tokens: int = 2000):
        self.search = hybrid_search
        self.max_context_tokens = max_context_tokens

        # Source priority weights (higher = more important)
        self.source_priorities = {
            "faq": 4,  # Highest priority - curated answers
            "regulation": 3,  # Official regulatory content
            "circular": 2,  # Official interpretations
            "knowledge": 1,  # General knowledge base
        }

        # Token allocation per source type (percentage of total)
        self.token_allocation = {
            "faq": 0.4,  # 40% for FAQs
            "regulation": 0.3,  # 30% for regulations
            "circular": 0.2,  # 20% for circulars
            "knowledge": 0.1,  # 10% for knowledge base
        }

        # Content extraction settings
        self.min_excerpt_length = 100
        self.max_excerpt_length = 500
        self.overlap_threshold = 0.7

        # Italian language specific settings
        self.italian_sentence_endings = [".", "!", "?", ":", ";"]
        self.preserve_phrases = [
            "in base all'art",
            "ai sensi dell'art",
            "secondo quanto previsto",
            "come stabilito dal",
            "in conformità a",
            "ai fini dell'applicazione",
        ]

    async def build_context(
        self,
        query: str,
        max_sources: int = 8,
        max_tokens: int | None = None,
        date_filter: datetime | None = None,
        source_types: list[str] = None,
        boost_recent: bool = True,
    ) -> QueryContext:
        """Build comprehensive context from multiple sources.

        Args:
            query: Search query for context building
            max_sources: Maximum number of sources to include
            max_tokens: Override default token limit
            date_filter: Only include content after this date
            source_types: Types of sources to search
            boost_recent: Boost recently updated content

        Returns:
            QueryContext with assembled information
        """
        if source_types is None:
            source_types = ["faq", "regulation", "circular", "knowledge"]
        start_time = time.time()

        try:
            # Use provided token limit or default
            token_limit = max_tokens or self.max_context_tokens

            logger.info(f"Building context for query: '{query}' (limit: {token_limit} tokens)")

            # Search across all specified sources
            search_results = await self.search.search(
                query=query,
                search_types=source_types,
                date_filter=date_filter,
                limit=max_sources * 2,  # Get more results for better selection
            )

            if not search_results:
                logger.warning(f"No search results found for query: {query}")
                return self._create_empty_context(query, start_time)

            logger.debug(f"Found {len(search_results)} search results")

            # Group results by source type
            grouped_results = self._group_results_by_source(search_results)

            # Build context parts with token budget management
            context_parts = await self._build_context_parts(grouped_results, query, token_limit, boost_recent)

            # Calculate context quality metrics
            context_quality = self._calculate_context_quality(context_parts, query)

            # Calculate source distribution
            source_distribution = self._calculate_source_distribution(context_parts)

            # Create final context
            total_tokens = sum(part.token_count for part in context_parts)
            assembly_time = (time.time() - start_time) * 1000

            context = QueryContext(
                query=query,
                context_parts=context_parts,
                total_tokens=total_tokens,
                sources_used=len(context_parts),
                context_quality_score=context_quality,
                assembly_time_ms=assembly_time,
                source_distribution=source_distribution,
            )

            logger.info(
                f"Context built: {len(context_parts)} parts, {total_tokens} tokens, "
                f"quality={context_quality:.2f}, time={assembly_time:.1f}ms"
            )

            return context

        except Exception as e:
            logger.error(f"Context building failed for query '{query}': {e}")
            return self._create_empty_context(query, start_time)

    def _group_results_by_source(self, results: list[SearchResult]) -> dict[str, list[SearchResult]]:
        """Group search results by source type"""
        grouped = {}
        for result in results:
            source_type = result.source_type
            if source_type not in grouped:
                grouped[source_type] = []
            grouped[source_type].append(result)

        # Sort each group by relevance score
        for source_type in grouped:
            grouped[source_type].sort(key=lambda x: x.relevance_score, reverse=True)

        return grouped

    async def _build_context_parts(
        self, grouped_results: dict[str, list[SearchResult]], query: str, token_limit: int, boost_recent: bool
    ) -> list[ContextPart]:
        """Build context parts with intelligent token allocation"""
        context_parts = []
        remaining_tokens = token_limit

        # Process sources in priority order
        priority_order = sorted(grouped_results.keys(), key=lambda x: self.source_priorities.get(x, 0), reverse=True)

        for source_type in priority_order:
            if remaining_tokens <= 0:
                break

            results = grouped_results[source_type]
            if not results:
                continue

            # Calculate token budget for this source type
            allocated_tokens = int(token_limit * self.token_allocation.get(source_type, 0.1))
            available_tokens = min(allocated_tokens, remaining_tokens)

            logger.debug(f"Processing {source_type}: {len(results)} results, {available_tokens} tokens available")

            # Process results for this source type
            source_parts = await self._process_source_results(
                results, query, available_tokens, source_type, boost_recent
            )

            context_parts.extend(source_parts)
            tokens_used = sum(part.token_count for part in source_parts)
            remaining_tokens -= tokens_used

            logger.debug(f"Added {len(source_parts)} parts from {source_type}, {tokens_used} tokens used")

        return context_parts

    async def _process_source_results(
        self, results: list[SearchResult], query: str, available_tokens: int, source_type: str, boost_recent: bool
    ) -> list[ContextPart]:
        """Process results from a single source type"""
        parts = []
        tokens_used = 0

        for result in results:
            if tokens_used >= available_tokens:
                break

            # Extract relevant portion of content
            relevant_content = await self._extract_relevant_portion(
                result.content, query, min(available_tokens - tokens_used, self.max_excerpt_length)
            )

            if not relevant_content or len(relevant_content.strip()) < self.min_excerpt_length:
                continue

            # Count tokens in the content
            content_tokens = self._count_tokens(relevant_content)

            if tokens_used + content_tokens > available_tokens:
                # Try to fit a smaller portion
                max_length = self._estimate_length_from_tokens(available_tokens - tokens_used)
                if max_length < self.min_excerpt_length:
                    break

                relevant_content = await self._extract_relevant_portion(result.content, query, max_length)
                content_tokens = self._count_tokens(relevant_content)

            # Apply boosting factors
            boosted_score = self._apply_context_boosting(result, relevant_content, query, boost_recent)

            # Create context part
            part = ContextPart(
                source_type=source_type,
                content=relevant_content,
                relevance_score=boosted_score,
                metadata=result.metadata,
                token_count=content_tokens,
            )

            parts.append(part)
            tokens_used += content_tokens

        return parts

    async def _extract_relevant_portion(self, content: str, query: str, max_tokens: int) -> str:
        """Extract most relevant portion of content for the query"""
        if not content:
            return ""

        # Estimate maximum character length from token budget
        max_length = self._estimate_length_from_tokens(max_tokens)

        # If content is short enough, return it as-is
        if len(content) <= max_length:
            return content.strip()

        # Find query terms in content
        query_terms = set(query.lower().split())
        content_lower = content.lower()

        # Find all positions where query terms appear
        term_positions = []
        for term in query_terms:
            if len(term) > 2:  # Skip very short terms
                start = 0
                while True:
                    pos = content_lower.find(term, start)
                    if pos == -1:
                        break
                    term_positions.append((pos, pos + len(term)))
                    start = pos + 1

        if not term_positions:
            # No query terms found, return first portion
            return self._truncate_at_sentence_boundary(content[:max_length])

        # Find the span that covers most query term matches
        term_positions.sort()
        best_start, best_end = self._find_best_span(term_positions, max_length, len(content))

        # Extract the content span
        excerpt = content[best_start:best_end]

        # Clean up and ensure proper sentence boundaries
        excerpt = self._clean_excerpt(excerpt)

        return excerpt

    def _find_best_span(
        self, positions: list[tuple[int, int]], max_length: int, content_length: int
    ) -> tuple[int, int]:
        """Find the best span of content that covers most query term positions"""
        if not positions:
            return 0, min(max_length, content_length)

        # Simple approach: center around the middle of term positions
        min_pos = min(pos[0] for pos in positions)
        max_pos = max(pos[1] for pos in positions)

        span_center = (min_pos + max_pos) // 2

        # Calculate start and end positions
        half_length = max_length // 2
        start = max(0, span_center - half_length)
        end = min(content_length, start + max_length)

        # Adjust start if end reached content boundary
        if end == content_length:
            start = max(0, end - max_length)

        return start, end

    def _clean_excerpt(self, excerpt: str) -> str:
        """Clean and improve excerpt boundaries"""
        if not excerpt:
            return ""

        # Find better start boundary (avoid cutting words)
        lines = excerpt.split("\n")
        if len(lines) > 1 and len(lines[0]) < 50:
            # If first line is very short, might be a partial sentence
            excerpt = "\n".join(lines[1:])

        # Find better end boundary
        excerpt = self._truncate_at_sentence_boundary(excerpt)

        # Remove incomplete sentences at the beginning
        sentences = self._split_sentences(excerpt)
        if len(sentences) > 1 and len(sentences[0]) < 30:
            excerpt = " ".join(sentences[1:])

        return excerpt.strip()

    def _truncate_at_sentence_boundary(self, text: str) -> str:
        """Truncate text at a sentence boundary"""
        if not text:
            return ""

        # Find the last complete sentence
        for ending in self.italian_sentence_endings:
            last_pos = text.rfind(ending)
            if last_pos > len(text) * 0.7:  # Must be in last 30% of text
                return text[: last_pos + 1].strip()

        # If no sentence boundary found, truncate at word boundary
        words = text.split()
        if len(words) > 10:
            # Remove last few words to avoid cutting mid-sentence
            return " ".join(words[:-3]) + "..."

        return text.strip()

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences (Italian-aware)"""
        # Simple sentence splitting for Italian
        pattern = r"[.!?]+\s+"
        sentences = re.split(pattern, text)

        # Clean up sentences
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

        return sentences

    def _count_tokens(self, text: str) -> int:
        """Estimate token count for text"""
        if not text:
            return 0

        # Rough estimation: ~1.3 tokens per word for Italian
        word_count = len(text.split())
        return int(word_count * 1.3)

    def _estimate_length_from_tokens(self, token_count: int) -> int:
        """Estimate character length from token count"""
        # Rough estimation: ~6 characters per token for Italian
        return int(token_count * 6)

    def _apply_context_boosting(self, result: SearchResult, content: str, query: str, boost_recent: bool) -> float:
        """Apply boosting factors to context relevance"""
        boosted_score = result.relevance_score

        # Query term density boost
        query_terms = set(query.lower().split())
        content_words = content.lower().split()

        if content_words:
            term_matches = sum(1 for word in content_words if word in query_terms)
            term_density = term_matches / len(content_words)
            boosted_score += term_density * 0.1  # Up to 10% boost

        # Content length optimization (prefer medium-length excerpts)
        content_length = len(content)
        if 200 <= content_length <= 400:
            boosted_score += 0.05  # 5% boost for optimal length
        elif content_length < 100:
            boosted_score -= 0.05  # 5% penalty for very short content

        # Professional terminology boost
        professional_terms = [
            "ai sensi",
            "in base",
            "secondo",
            "previsto",
            "stabilito",
            "decreto",
            "legge",
            "articolo",
            "comma",
            "circolare",
        ]

        professional_matches = sum(1 for term in professional_terms if term in content.lower())
        if professional_matches > 0:
            boosted_score += min(professional_matches * 0.02, 0.08)  # Max 8% boost

        # Recency boost for regulations
        if boost_recent and result.source_type in ["regulation", "circular"]:
            updated_at = result.metadata.get("updated_at")
            if updated_at:
                try:
                    if isinstance(updated_at, str):
                        update_date = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                    else:
                        update_date = updated_at

                    days_old = (datetime.now() - update_date).days
                    if days_old < 90:
                        recency_boost = 0.1 * (90 - days_old) / 90  # Up to 10% boost
                        boosted_score += recency_boost
                except (ValueError, TypeError):
                    pass

        return min(boosted_score, 1.0)  # Cap at 1.0

    def _calculate_context_quality(self, context_parts: list[ContextPart], query: str) -> float:
        """Calculate overall context quality score"""
        if not context_parts:
            return 0.0

        # Average relevance score
        avg_relevance = sum(part.relevance_score for part in context_parts) / len(context_parts)

        # Source diversity score
        source_types = {part.source_type for part in context_parts}
        diversity_score = min(len(source_types) / 4.0, 1.0)  # Max 4 source types

        # Content coverage score
        total_tokens = sum(part.token_count for part in context_parts)
        coverage_score = min(total_tokens / self.max_context_tokens, 1.0)

        # Combine scores
        quality_score = avg_relevance * 0.5 + diversity_score * 0.3 + coverage_score * 0.2

        return min(quality_score, 1.0)

    def _calculate_source_distribution(self, context_parts: list[ContextPart]) -> dict[str, int]:
        """Calculate distribution of sources in context"""
        distribution = {}
        for part in context_parts:
            source_type = part.source_type
            distribution[source_type] = distribution.get(source_type, 0) + 1

        return distribution

    def _create_empty_context(self, query: str, start_time: float) -> QueryContext:
        """Create empty context when no results found"""
        assembly_time = (time.time() - start_time) * 1000

        return QueryContext(
            query=query,
            context_parts=[],
            total_tokens=0,
            sources_used=0,
            context_quality_score=0.0,
            assembly_time_ms=assembly_time,
            source_distribution={},
        )

    async def get_context_statistics(self) -> dict[str, Any]:
        """Get context building statistics"""
        return {
            "max_context_tokens": self.max_context_tokens,
            "source_priorities": self.source_priorities,
            "token_allocation": self.token_allocation,
            "min_excerpt_length": self.min_excerpt_length,
            "max_excerpt_length": self.max_excerpt_length,
            "performance_metrics": {
                "target_assembly_time_ms": 200,  # Target: <200ms
                "context_quality_threshold": 0.7,  # Target: >70% quality
            },
        }

    def configure_token_allocation(
        self,
        faq_percentage: float | None = None,
        regulation_percentage: float | None = None,
        circular_percentage: float | None = None,
        knowledge_percentage: float | None = None,
    ) -> dict[str, float]:
        """Configure token allocation percentages across source types"""
        new_allocation = self.token_allocation.copy()

        if faq_percentage is not None:
            new_allocation["faq"] = max(0.0, min(1.0, faq_percentage))

        if regulation_percentage is not None:
            new_allocation["regulation"] = max(0.0, min(1.0, regulation_percentage))

        if circular_percentage is not None:
            new_allocation["circular"] = max(0.0, min(1.0, circular_percentage))

        if knowledge_percentage is not None:
            new_allocation["knowledge"] = max(0.0, min(1.0, knowledge_percentage))

        # Normalize to ensure sum is 1.0
        total = sum(new_allocation.values())
        if total > 0:
            for source_type in new_allocation:
                new_allocation[source_type] /= total

        self.token_allocation = new_allocation

        logger.info(f"Token allocation updated: {new_allocation}")

        return new_allocation
