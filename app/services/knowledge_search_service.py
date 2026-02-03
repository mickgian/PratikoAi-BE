"""Knowledge Search Service - RAG STEP 39 Implementation.

Implements RAG STEP 39 — KBPreFetch

This service implements hybrid search combining BM25 text search, vector semantic search,
and recency boost to retrieve the most relevant knowledge items for user queries.

Based on Mermaid diagram: KBPreFetch (KnowledgeSearch.retrieve_topk BM25 and vectors and recency boost)
"""

import math
import re
import time
from dataclasses import (
    dataclass,
    field,
)
from datetime import (
    UTC,
    date,
    datetime,
    timedelta,
    timezone,
)
from enum import Enum
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Union,
)

from sqlalchemy import (
    func,
    select,
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.core.logging import logger
from app.models.knowledge import KnowledgeItem
from app.observability.rag_logging import (
    rag_step_log,
    rag_step_timer,
)
from app.services.query_normalizer import QueryNormalizer
from app.services.ranking_utils import get_tier_multiplier
from app.services.search_service import SearchResult as BaseSearchResult
from app.services.search_service import SearchService

STEP_NUM = 39
STEP_ID = "RAG.preflight.knowledgesearch.retrieve.topk.bm25.and.vectors.and.recency.boost"
NODE_LABEL = "KBPreFetch"

# Document type mapping for normalization (used by both LLM and regex paths)
DOCUMENT_TYPE_MAPPING = {
    "risoluzione": "risoluzion",
    "circolare": "circolar",
    "decreto": "decret",
    "interpello": "interpell",
    "risposta": "rispost",
    "provvedimento": "provvediment",
    # Court documents (Cassazione)
    "ordinanza": "ordinanza",
    "sentenza": "sentenza",
    # INPS documents
    "messaggio": "messaggio",
}

# DEV-242 ADR-023: Topic keywords for automatic topic extraction from queries
# These map keywords in user queries to topics in the knowledge_items.topics field
# Topics are used to filter search results via GIN index for faster, more accurate retrieval
#
# DEV-XXX: Simplified to broad categories for scalability (no version-specific topics)
TOPIC_KEYWORDS = {
    # Broad category for fiscal amnesty procedures (rottamazione, sanatoria, etc.)
    "fiscal_amnesty": [
        "rottamazione",
        "rottamazione quinquies",
        "rottamazione quater",
        "quinquies",
        "quater",
        "definizione agevolata",
        "stralcio",
        "pace fiscale",
        "sanatoria",
    ],
    "irpef": [
        "irpef",
        "imposta sul reddito",
        "aliquote",
        "scaglioni",
        "detrazioni lavoro",
        "no tax area",
    ],
    "iva": [
        "iva",
        "imposta sul valore aggiunto",
        "aliquota iva",
        "reverse charge",
        "split payment",
    ],
    "contributi": [
        "contributi",
        "inps",
        "previdenza",
        "pensione",
        "gestione separata",
    ],
    "bonus": [
        "bonus",
        "credito d'imposta",
        "agevolazione",
        "incentivo",
        "superbonus",
        "ecobonus",
    ],
    "fatturazione": [
        "fattura elettronica",
        "e-fattura",
        "sdi",
        "fatturazione",
        "corrispettivi",
    ],
    "forfettario": [
        "forfettario",
        "regime forfetario",
        "flat tax",
    ],
}


class SearchMode(str, Enum):
    """Search mode for knowledge retrieval."""

    HYBRID = "hybrid"  # BM25 + vector + recency (default)
    BM25_ONLY = "bm25_only"  # BM25 text search only
    VECTOR_ONLY = "vector_only"  # Vector semantic search only


@dataclass
class KnowledgeSearchConfig:
    """Configuration for knowledge search service.

    DEV-BE-78: Updated to include quality and source authority weights.
    Uses global config values from app/core/config.py for consistency.
    """

    bm25_weight: float | None = None  # Weight for BM25 text search scores
    vector_weight: float | None = None  # Weight for vector similarity scores
    recency_weight: float | None = None  # Weight for recency boost
    quality_weight: float | None = None  # Weight for text quality score
    source_weight: float | None = None  # Weight for source authority boost
    max_results: int = 10  # Maximum number of results to return
    min_score_threshold: float = 0.1  # Minimum combined score threshold
    recency_decay_days: int = 90  # Days for recency decay calculation
    vector_top_k: int = 50  # Top-k results from vector search
    bm25_top_k: int = 50  # Top-k results from BM25 search

    def __post_init__(self):
        """Initialize weights from global config and validate they sum to 1.0."""
        # Import here to avoid circular imports
        from app.core.config import (
            HYBRID_WEIGHT_FTS,
            HYBRID_WEIGHT_QUALITY,
            HYBRID_WEIGHT_RECENCY,
            HYBRID_WEIGHT_SOURCE,
            HYBRID_WEIGHT_VEC,
        )

        # Use global config values if not explicitly provided
        if self.bm25_weight is None:
            self.bm25_weight = HYBRID_WEIGHT_FTS
        if self.vector_weight is None:
            self.vector_weight = HYBRID_WEIGHT_VEC
        if self.recency_weight is None:
            self.recency_weight = HYBRID_WEIGHT_RECENCY
        if self.quality_weight is None:
            self.quality_weight = HYBRID_WEIGHT_QUALITY
        if self.source_weight is None:
            self.source_weight = HYBRID_WEIGHT_SOURCE

        # Validate weights sum to 1.0
        total_weight = (
            self.bm25_weight + self.vector_weight + self.recency_weight + self.quality_weight + self.source_weight
        )
        if not math.isclose(total_weight, 1.0, rel_tol=1e-5):
            raise ValueError(f"Search weights must sum to 1.0, got {total_weight}")


@dataclass
class SearchResult:
    """Enhanced search result with hybrid scoring."""

    id: str
    title: str
    content: str
    category: str
    score: float  # Final combined score
    source: str
    source_url: str | None = None
    updated_at: datetime | None = None
    publication_date: date | None = None

    # Individual scoring components
    bm25_score: float | None = None
    vector_score: float | None = None
    recency_score: float | None = None

    # Search metadata
    search_method: str = field(default="hybrid")
    rank_position: int | None = None
    highlight: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for structured logging."""
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "score": self.score,
            "source": self.source,
            "source_url": self.source_url,
            "bm25_score": self.bm25_score,
            "vector_score": self.vector_score,
            "recency_score": self.recency_score,
            "search_method": self.search_method,
            "rank_position": self.rank_position,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class KnowledgeSearchService:
    """Service for hybrid knowledge search with BM25, vector search and recency boost."""

    def __init__(
        self, db_session: AsyncSession, vector_service: Any = None, config: KnowledgeSearchConfig | None = None
    ):
        """Initialize knowledge search service."""
        self.db = db_session
        self.vector_service = vector_service
        self.config = config or KnowledgeSearchConfig()

        # Initialize BM25 search service
        self.search_service = SearchService(db_session)

        # Cache for performance optimization
        self._embedding_cache: dict[str, list[float]] = {}
        self._query_cache: dict[str, list[SearchResult]] = {}

    def _format_recent_conversation(self, messages: list | None, max_turns: int = 3) -> str | None:
        """Format recent conversation for query normalization context.

        DEV-251: Extract last N turns for typo correction context.

        Args:
            messages: Conversation history (list of message dicts)
            max_turns: Max turns to include (default: 3)

        Returns:
            Formatted string or None if no messages
        """
        if not messages:
            return None

        recent = []
        # Take last N turns (each turn is user + assistant = 2 messages)
        for msg in messages[-max_turns * 2 :]:
            if not isinstance(msg, dict):
                continue
            role = msg.get("role", "")
            content = msg.get("content", "")
            if not content:
                continue
            # Truncate content for efficiency (200 chars max per message)
            content_truncated = content[:200]
            if role in ("user", "assistant") and content_truncated:
                recent.append(f"{role}: {content_truncated}")

        return "\n".join(recent) if recent else None

    @staticmethod
    def _extract_topics_from_query(query: str) -> list[str] | None:
        """Extract topic tags from user query for GIN-indexed filtering.

        DEV-242 ADR-023: Implements topic-based search filtering.
        Matches keywords in the user query against TOPIC_KEYWORDS mapping
        to identify relevant topics. This enables faster, more accurate
        retrieval by filtering on the indexed topics field.

        DEV-245: When USE_DYNAMIC_TOPIC_DETECTION is enabled, returns None
        to let LLM-generated semantic_expansions handle topic detection.
        This enables unlimited scalability without manual keyword maintenance.

        Args:
            query: User's search query

        Returns:
            List of topic tags (e.g., ["fiscal_amnesty", "irpef"]) or None if no topics detected
        """
        from app.core.config import USE_DYNAMIC_TOPIC_DETECTION

        # DEV-245: When dynamic detection is enabled, skip hardcoded topics
        # and rely on LLM-generated semantic_expansions instead
        if USE_DYNAMIC_TOPIC_DETECTION:
            logger.debug(
                "dynamic_topic_detection_enabled",
                query=query[:100] if query else "",
                reason="dev_245_scalable_topic_detection",
            )
            return None

        if not query:
            return None

        query_lower = query.lower()
        detected_topics = []

        # Simple iteration through all topic categories (legacy fallback)
        for topic, keywords in TOPIC_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in query_lower:
                    detected_topics.append(topic)
                    break  # Only add topic once even if multiple keywords match

        if detected_topics:
            logger.info(
                "topics_extracted_from_query",
                query=query[:100],
                detected_topics=detected_topics,
                reason="adr_023_topic_based_search_legacy_fallback",
            )
            return detected_topics

        return None

    async def retrieve_topk(self, query_data: dict[str, Any]) -> list[SearchResult]:
        """Retrieve top-k knowledge items using hybrid search.

        Args:
            query_data: Dictionary containing:
                - query: The user's query text
                - canonical_facts: List of extracted canonical facts (optional)
                - user_id: User identifier
                - session_id: Session identifier
                - trace_id: Trace identifier for logging
                - search_mode: SearchMode enum (optional, defaults to HYBRID)
                - filters: Dictionary of filters (category, source, etc.)
                - max_results: Maximum results to return (optional)
                - messages: Conversation history for context (optional, DEV-251)

        Returns:
            List of SearchResult objects ordered by combined relevance score
        """
        start_time = time.perf_counter()

        try:
            # Extract and validate query parameters
            query = query_data.get("query", "").strip()
            if not query:
                return []

            canonical_facts = query_data.get("canonical_facts", [])
            search_mode = SearchMode(query_data.get("search_mode", SearchMode.HYBRID))
            filters = query_data.get("filters", {})
            max_results = query_data.get("max_results", self.config.max_results)
            trace_id = query_data.get("trace_id")
            # DEV-251: Extract conversation context for typo correction
            messages = query_data.get("messages", [])
            conversation_context = self._format_recent_conversation(messages)

            # Use timer context manager for performance logging
            with rag_step_timer(
                STEP_NUM, STEP_ID, NODE_LABEL, query=query, search_mode=search_mode.value, trace_id=trace_id
            ):
                # Perform search based on mode
                if search_mode == SearchMode.BM25_ONLY:
                    bm25_raw_results = await self._perform_bm25_search(
                        query,
                        canonical_facts,
                        max_results,
                        filters,
                        conversation_context=conversation_context,
                    )
                    # Convert BM25 dict results to SearchResult objects
                    results = []
                    for bm25_result in bm25_raw_results:
                        search_result = SearchResult(
                            id=str(bm25_result["id"]),
                            title=bm25_result["title"],
                            content=bm25_result["content"],
                            category=bm25_result["category"],
                            score=bm25_result["rank_score"],
                            source=bm25_result["source"],
                            source_url=bm25_result.get("source_url"),
                            updated_at=bm25_result["updated_at"],
                            publication_date=bm25_result.get("publication_date"),
                            bm25_score=bm25_result["rank_score"],
                            search_method="bm25",
                        )
                        results.append(search_result)

                elif search_mode == SearchMode.VECTOR_ONLY:
                    results = await self._perform_vector_search(query, canonical_facts, filters)
                    for result in results:
                        result.search_method = "vector"
                    results = results[:max_results]

                else:  # HYBRID mode
                    results = await self._perform_hybrid_search(
                        query,
                        canonical_facts,
                        filters,
                        max_results,
                        conversation_context=conversation_context,
                    )

                # Apply final ranking and filtering
                results = self._apply_final_ranking(results, max_results)

                # Log successful search
                rag_step_log(
                    step=STEP_NUM,
                    step_id=STEP_ID,
                    node_label=NODE_LABEL,
                    query=query,
                    results_count=len(results),
                    search_mode=search_mode.value,
                    trace_id=trace_id,
                    avg_score=sum(r.score for r in results) / len(results) if results else 0.0,
                    top_categories=[r.category for r in results[:3]],
                )

                return results

        except Exception as exc:
            # Calculate latency even on error
            end_time = time.perf_counter()
            latency_ms = round((end_time - start_time) * 1000.0, 2)

            # Log error
            rag_step_log(
                step=STEP_NUM,
                step_id=STEP_ID,
                node_label=NODE_LABEL,
                level="ERROR",
                query=query_data.get("query", ""),
                error=str(exc),
                latency_ms=latency_ms,
                trace_id=query_data.get("trace_id"),
            )

            # Return empty results on error (graceful degradation)
            logger.error("knowledge_search_error", error=str(exc), trace_id=query_data.get("trace_id"))
            return []

    async def _perform_hybrid_search(
        self,
        query: str,
        canonical_facts: list[str],
        filters: dict[str, Any],
        max_results: int,
        conversation_context: str | None = None,
    ) -> list[SearchResult]:
        """Perform hybrid search combining BM25, vector search and recency boost.

        Args:
            query: User query text
            canonical_facts: Extracted facts from query
            filters: Search filters
            max_results: Maximum results to return
            conversation_context: Optional conversation context for typo correction (DEV-251)
        """
        # Perform both searches concurrently for better performance
        import asyncio

        bm25_task = asyncio.create_task(
            self._perform_bm25_search(
                query,
                canonical_facts,
                self.config.bm25_top_k,
                filters,
                conversation_context=conversation_context,
            )
        )

        vector_task = asyncio.create_task(self._perform_vector_search(query, canonical_facts, filters))

        # Wait for both searches to complete
        bm25_results, vector_results = await asyncio.gather(bm25_task, vector_task)

        # Convert BM25 results to SearchResult format
        bm25_search_results = []
        for bm25_result in bm25_results:
            # FIX: Ensure datetime fields are proper objects, not strings
            # BM25 search may return datetime as strings from serialization/cache
            updated_at_value = bm25_result.get("updated_at")
            if isinstance(updated_at_value, str):
                try:
                    updated_at_value = datetime.fromisoformat(updated_at_value.replace("Z", "+00:00"))
                except Exception:
                    updated_at_value = None

            publication_date_value = bm25_result.get("publication_date")
            if isinstance(publication_date_value, str):
                try:
                    publication_date_value = datetime.fromisoformat(publication_date_value).date()
                except Exception:
                    publication_date_value = None
            elif isinstance(publication_date_value, datetime):
                # If it's already a datetime object, extract date part
                publication_date_value = publication_date_value.date()

            search_result = SearchResult(
                id=str(bm25_result["id"]),
                title=bm25_result["title"],
                content=bm25_result["content"],
                category=bm25_result["category"],
                score=0.0,  # Will be calculated in hybrid scoring
                source=bm25_result["source"],
                source_url=bm25_result.get("source_url"),
                updated_at=updated_at_value,  # Guaranteed datetime or None
                publication_date=publication_date_value,  # Guaranteed date or None
                bm25_score=bm25_result["rank_score"],
                search_method="hybrid",
            )
            bm25_search_results.append(search_result)

        # Combine and deduplicate results
        combined_results = self._combine_and_deduplicate_results(bm25_search_results, vector_results)

        # Apply hybrid scoring
        scored_results = self._apply_hybrid_scoring(combined_results)

        # Sort by combined score
        scored_results.sort(key=lambda x: x.score, reverse=True)

        return scored_results[:max_results]

    def _extract_organization_filter(self, query: str, canonical_facts: list[str] | None = None) -> str | None:
        """Extract organization mention from Italian query using HYBRID approach:
        1. Fast pattern matching on query string (handles 95% of cases, no LLM cost)
        2. Fallback to LLM-extracted canonical facts (handles typos like "aginzia dll'entrata")

        Returns source pattern for LIKE matching, or None if no organization detected.
        This allows queries mentioning organizations to filter by source metadata
        instead of requiring organization names in document text.
        """
        query_lower = query.lower()

        # FAST PATH: Direct pattern matching on query with typo tolerance
        # Common Italian typos for "agenzia": aggenzia (double g), agensia (s→z), agenza (missing i)
        # Common Italian typos for "entrate": entrati (i→e), entarte (transposed)
        has_agenzia = any(pattern in query_lower for pattern in ["agenzi", "aggenzi", "agensi", "agenz"])
        has_entrate = any(pattern in query_lower for pattern in ["entrat", "entart"])

        if (has_agenzia and has_entrate) or "ade" in query_lower:
            return "agenzia_entrate%"  # matches agenzia_entrate_news, agenzia_entrate_normativa, etc.
        elif "inps" in query_lower:
            return "inps%"
        elif "gazzetta" in query_lower and ("ufficiale" in query_lower or "gu" in query_lower):
            return "gazzetta_ufficiale%"
        elif "governo" in query_lower or "presidenza" in query_lower:
            return "%governo%"

        # FALLBACK PATH: Check LLM-extracted canonical facts for organization mentions
        # This handles typos and variations that the LLM has already normalized
        # Example: "aginzia dll'entrata" → LLM extracts "Agenzia delle Entrate" correctly
        if canonical_facts:
            facts_text = " ".join(canonical_facts).lower()

            # Check for organization mentions in the normalized facts
            if ("agenzia" in facts_text or "ade" in facts_text) and "entrate" in facts_text:
                logger.info(
                    "organization_detected_from_canonical_facts",
                    query=query,
                    canonical_facts=canonical_facts,
                    detected_org="agenzia_entrate",
                    reason="pattern_match_failed_llm_fallback_succeeded",
                )
                return "agenzia_entrate%"
            elif "inps" in facts_text:
                logger.info(
                    "organization_detected_from_canonical_facts",
                    query=query,
                    canonical_facts=canonical_facts,
                    detected_org="inps",
                    reason="pattern_match_failed_llm_fallback_succeeded",
                )
                return "inps%"
            elif "gazzetta" in facts_text and "ufficiale" in facts_text:
                logger.info(
                    "organization_detected_from_canonical_facts",
                    query=query,
                    canonical_facts=canonical_facts,
                    detected_org="gazzetta_ufficiale",
                    reason="pattern_match_failed_llm_fallback_succeeded",
                )
                return "gazzetta_ufficiale%"

        return None

    def _remove_organization_keywords(self, query: str) -> str:
        """Remove Italian organization keywords from query for fallback search.

        Used when org-filtered search returns zero results - try again with just
        the core entity/temporal keywords.
        """
        # Organization keywords to remove (most specific to least specific)
        org_patterns = [
            "dell'agenzia delle entrate",
            "dell'agenzia entrate",
            "agenzia delle entrate",
            "agenzia entrate",
            "dell'inps",
            "inps",
            "della gazzetta ufficiale",
            "gazzetta ufficiale",
            "del governo",
            "governo",
        ]

        cleaned_query = query.lower()
        for pattern in org_patterns:
            cleaned_query = cleaned_query.replace(pattern, "")

        # Clean up extra spaces
        cleaned_query = " ".join(cleaned_query.split())

        return cleaned_query if cleaned_query != query.lower() else query

    def _generate_title_patterns(
        self,
        doc_type: str | None,
        doc_number: str,
        doc_year: str | None = None,
    ) -> list[str]:
        """Generate title matching patterns for Italian documents.

        Returns maximum 7 patterns, ordered by specificity (most specific first).
        Includes BOTH base number and compound patterns for maximum recall.

        Args:
            doc_type: Document type (e.g., "risoluzione", "messaggio", "DPR")
            doc_number: Document number (e.g., "64", "3585", "1124")
            doc_year: Optional year for compound references (e.g., "1965")

        Returns:
            List of title patterns to search (max 7)

        Examples:
            _generate_title_patterns("messaggio", "3585")
            → ["messaggio n. 3585", "messaggio numero 3585", "n. 3585", "n.3585", "numero 3585"]

            _generate_title_patterns("DPR", "1124", "1965")
            → ["DPR n. 1124/1965", "DPR 1124/1965", "DPR n. 1124", "DPR numero 1124",
               "n. 1124/1965", "1124/1965", "n. 1124"]
        """
        patterns = []

        # 1. Type + number + year (most specific - compound)
        if doc_type and doc_year:
            patterns.append(f"{doc_type} n. {doc_number}/{doc_year}")
            patterns.append(f"{doc_type} {doc_number}/{doc_year}")

        # 2. Type + number (base)
        if doc_type:
            patterns.append(f"{doc_type} n. {doc_number}")
            patterns.append(f"{doc_type} numero {doc_number}")

        # 3. Generic compound patterns (if year provided)
        if doc_year:
            patterns.append(f"n. {doc_number}/{doc_year}")
            patterns.append(f"{doc_number}/{doc_year}")

        # 4. Generic base number patterns (fallback - always included)
        patterns.append(f"n. {doc_number}")
        patterns.append(f"n.{doc_number}")  # No space variant
        patterns.append(f"numero {doc_number}")

        # Limit to 7 patterns max (100ms latency budget allows this)
        return patterns[:7]

    async def _perform_bm25_search(
        self,
        query: str,
        canonical_facts: list[str],
        max_results: int,
        filters: dict[str, Any],
        conversation_context: str | None = None,
    ) -> list[dict[str, Any]]:
        """Perform BM25 full-text search with OR fallback for zero results.

        Args:
            query: User query text
            canonical_facts: Extracted facts from query
            max_results: Maximum results to return
            filters: Search filters
            conversation_context: Optional conversation context for typo correction (DEV-251)
        """
        # Query expansion: prioritize canonical facts for better search
        search_query = query
        if canonical_facts:
            # If we have extracted canonical facts (like "risoluzione 56"),
            # use them as the primary search query since they represent
            # the actual entities being searched for, not conversational wrapper
            facts_query = " ".join(canonical_facts)

            # For document references, prioritize facts over full query
            # to avoid AND-query failures from conversational terms
            if any(
                "risoluzione" in fact or "circolare" in fact or "risposta" in fact or "interpello" in fact
                for fact in canonical_facts
            ):
                # Use facts as primary query, original query as boost
                search_query = facts_query
            else:
                # Otherwise enhance query with facts
                search_query = f"{query} {facts_query}"

        # Query simplification for aggregation queries
        # Detect aggregation intent (list all, summarize all, etc.)
        aggregation_indicators = [
            "tutte",
            "tutti",
            "elenco",
            "riassunto",
            "list",
            "summarize",
            "quali sono",
            "fammi un",
        ]
        query_lower = query.lower()
        is_aggregation = any(indicator in query_lower for indicator in aggregation_indicators)

        # ALWAYS simplify aggregation queries, regardless of canonical_facts
        # Canonical facts may contain extracted entities that shouldn't block simplification
        if is_aggregation:
            # Extract core entity types and temporal keywords only
            # Include both singular and plural forms for Italian documents
            entity_keywords = [
                "risoluzion",  # Matches risoluzione, risoluzioni
                "circolar",  # Matches circolare, circolari
                "decret",  # Matches decreto, decreti
                "interpell",  # Matches interpello, interpelli
                "rispost",  # Matches risposta, risposte
                "provvediment",  # Matches provvedimento, provvedimenti
                "comunicat",  # Matches comunicato, comunicati
            ]
            temporal_keywords = [
                "gennaio",
                "febbraio",
                "marzo",
                "aprile",
                "maggio",
                "giugno",
                "luglio",
                "agosto",
                "settembre",
                "ottobre",
                "novembre",
                "dicembre",
            ]

            query_words = search_query.lower().split()
            simplified_parts = []

            for word in query_words:
                # Keep entity type keywords (using substring match for stemming)
                if (
                    any(entity in word for entity in entity_keywords)
                    or any(month in word for month in temporal_keywords)
                    or word.isdigit()
                    and len(word) == 4
                ):
                    simplified_parts.append(word)
                # SKIP organization references in aggregation queries
                # Organization filtering is handled via source_pattern filter,
                # not as text search terms. This prevents failures when org names
                # aren't in document content (e.g., "Agenzia delle Entrate" may not
                # appear in every risoluzione's text despite being from that org).
                # elif "agenzi" in word or "entrat" in word or "inps" in word:
                #     simplified_parts.append(word)

            if simplified_parts and len(simplified_parts) < len(query_words):
                original_query = search_query
                search_query = " ".join(simplified_parts)
                logger.info(
                    "bm25_query_simplification",
                    original_query=original_query,
                    simplified_query=search_query,
                    reason="aggregation_query_detected",
                    canonical_facts_present=bool(canonical_facts),
                    canonical_facts_count=len(canonical_facts) if canonical_facts else 0,
                    removed_words=len(query_words) - len(simplified_parts),
                )

        # Extract year from query for SQL filtering (before stripping from FTS query)
        from app.core.text.date_parser import (
            extract_year_from_query,
            strip_years_from_text,
        )

        publication_year = extract_year_from_query(search_query)

        # Strip years from FTS query (PostgreSQL FTS doesn't index numbers)
        search_query_without_year = strip_years_from_text(search_query)
        if publication_year:
            logger.info(
                "year_filter_extracted",
                original_query=query[:100],
                publication_year=publication_year,
                fts_query_before=search_query,
                fts_query_after=search_query_without_year,
            )
            search_query = search_query_without_year

        # Extract filters
        category = filters.get("category")
        min_rank = filters.get("min_rank", 0.01)
        topics = filters.get("topics")  # DEV-242: Topic-based search filter (ADR-023)

        # DEV-242 ADR-023: Auto-extract topics from query if not provided in filters
        # This enables topic-based GIN index filtering for queries like "rottamazione quinquies"
        if not topics:
            topics = self._extract_topics_from_query(query)

        # DEV-242 ADR-023: Expand search query with topic synonyms for better recall
        # When user searches for "rottamazione quinquies", expand to also find
        # "definizione agevolata" content which is semantically equivalent
        if topics:
            expanded_terms = []
            for topic in topics:
                if topic in TOPIC_KEYWORDS:
                    # Add main topic synonyms (first 3 to avoid query explosion)
                    expanded_terms.extend(TOPIC_KEYWORDS[topic][:3])
            if expanded_terms:
                # Create OR search query with original terms plus synonyms
                original_terms = search_query.split()
                unique_terms = list(dict.fromkeys(original_terms + expanded_terms))
                search_query = " ".join(unique_terms)
                logger.info(
                    "topic_synonym_expansion",
                    original_query=query[:100],
                    detected_topics=topics,
                    expanded_terms=expanded_terms,
                    new_search_query=search_query[:100],
                    reason="adr_023_semantic_search_expansion",
                )

        # TDD INTEGRATION: LLM-BASED QUERY NORMALIZATION
        # Layer 1: Check if canonical_facts already has document reference (skip LLM)
        # Layer 2: Try QueryNormalizer if no canonical facts (handles written numbers, abbreviations, typos)
        # Layer 3: Fall back to regex detection
        # Layer 4: Multi-pass number fallback (implemented later in this method)

        llm_doc_ref = None
        has_canonical_doc_ref = any(
            fact
            for fact in canonical_facts
            if any(term in fact.lower() for term in ["risoluzione", "circolare", "decreto", "interpello", "risposta"])
        )

        if not has_canonical_doc_ref:
            # No document reference in canonical_facts - try LLM normalization
            try:
                normalizer = QueryNormalizer()
                # DEV-251: Pass conversation context for typo correction
                llm_doc_ref = await normalizer.normalize(query, conversation_context=conversation_context)

                if llm_doc_ref:
                    logger.info(
                        "llm_query_normalization_success",
                        original_query=query[:100],
                        extracted_type=llm_doc_ref.get("type"),
                        extracted_number=llm_doc_ref.get("number"),
                        extracted_year=llm_doc_ref.get("year"),
                        extracted_keywords=llm_doc_ref.get("keywords", []),
                        has_conversation_context=conversation_context is not None,
                        reason="llm_extracted_document_reference",
                    )
                else:
                    logger.info(
                        "llm_query_normalization_no_doc_found",
                        original_query=query[:100],
                        has_conversation_context=conversation_context is not None,
                        reason="llm_returned_none_no_document_reference",
                    )
            except Exception as e:
                logger.warning(
                    "llm_query_normalization_failed",
                    original_query=query[:100],
                    error=str(e),
                    error_type=type(e).__name__,
                    reason="llm_call_failed_falling_back_to_regex",
                )

        # DOCUMENT NUMBER QUERY SIMPLIFICATION
        # For queries like "Cosa dice la Risoluzione numero 56 dell'Agenzia delle Entrate?"
        # Extract document number AND preserve document type context with temporal info
        # This fixes issues where "n. 64" was simplified to just "64" (too generic)
        # TDD FIX: Add 'risoluzion\w*' for correct spelling, keep 'risluzion\w*' for typos
        doc_number_match = re.search(
            r"\b(n\.?|numero|risoluzion\w*|risluzion\w*|circolar\w*|decret\w*|interpell\w*|rispost\w*)\s*(\d+)",
            search_query,
            re.IGNORECASE,
        )
        # Only treat as document number query if we have an actual number
        # This prevents queries like "DL Sicurezza sul lavoro" (type detected but no number)
        # from entering the document number path and causing search failures
        is_document_number_query = doc_number_match is not None or (
            llm_doc_ref is not None and llm_doc_ref.get("number") is not None
        )

        if is_document_number_query:
            # ALWAYS prefer LLM when it has a specific document type
            # (regex might only capture "numero" which is useless for title matching)
            # This fixes queries like "ordinanza numero 30016" where regex captures
            # "numero 30016" but LLM correctly extracts type="ordinanza"
            if llm_doc_ref and llm_doc_ref.get("type"):
                # LLM extracted document type - use it (more reliable than regex)
                doc_number = llm_doc_ref.get("number")
                llm_type = str(llm_doc_ref.get("type", "")).lower()

                # Map LLM type to normalized stem using shared constant
                normalized_type = DOCUMENT_TYPE_MAPPING.get(llm_type, llm_type)
                doc_type_keyword = llm_type  # For logging compatibility

                logger.info(
                    "using_llm_extracted_document_reference",
                    doc_type=llm_type,
                    doc_number=doc_number,
                    normalized_type=normalized_type,
                    regex_also_matched=doc_number_match is not None,
                )

            elif doc_number_match:
                # Fall back to regex when LLM didn't extract a type
                doc_number = doc_number_match.group(2)
                doc_type_keyword = doc_number_match.group(1).lower()

                # FIX: Look backwards in query for full document type
                # If we matched "n. 64" but query has "Risoluzione n. 64", prefer "risoluzione"
                query_before_match = search_query[: doc_number_match.start()].lower()

                # Check for document type words before the match
                doc_type_patterns = [
                    (r"risoluzion\w*", "risoluzion"),
                    (r"circolar\w*", "circolar"),
                    (r"decret\w*", "decret"),
                    (r"interpell\w*", "interpell"),
                    (r"rispost\w*", "rispost"),
                    (r"provvediment\w*", "provvediment"),
                ]

                full_doc_type = None
                for pattern, stem in doc_type_patterns:
                    if re.search(pattern, query_before_match):
                        full_doc_type = stem
                        break

                # If found full document type (e.g., "risoluzione"), use it
                # Otherwise use the captured keyword with typo mapping
                if full_doc_type:
                    normalized_type = full_doc_type
                else:
                    # Map common typos and filler words
                    typo_mapping = {
                        "risluzion": "risoluzion",
                        "risluzione": "risoluzion",
                        "risoluzion": "risoluzion",
                        "circolar": "circolar",
                        "decret": "decret",
                        "interpell": "interpell",
                        "rispost": "rispost",
                        "numero": "numero",  # KEEP numero (don't strip to empty)
                        "n.": "numero",  # MAP n. to numero (don't strip)
                        "n": "numero",
                    }

                    normalized_type = doc_type_keyword
                    for typo, correct in typo_mapping.items():
                        if doc_type_keyword.startswith(typo):
                            normalized_type = correct
                            break

            else:
                # Edge case: LLM has number but no type, and regex didn't match
                # Use LLM's number with generic "numero" type
                doc_number = llm_doc_ref.get("number") if llm_doc_ref else None
                normalized_type = "numero"
                doc_type_keyword = "numero"

                logger.info(
                    "using_llm_number_without_type",
                    doc_number=doc_number,
                    normalized_type=normalized_type,
                )

            # Extract temporal context from query (month/year)
            temporal_context = []
            for month in [
                "gennaio",
                "febbraio",
                "marzo",
                "aprile",
                "maggio",
                "giugno",
                "luglio",
                "agosto",
                "settembre",
                "ottobre",
                "novembre",
                "dicembre",
            ]:
                if month in search_query.lower():
                    temporal_context.append(month)
                    break  # Only first month

            # Build simplified query: type + number + temporal context
            query_parts: list[str] = [normalized_type]
            if doc_number:
                query_parts.append(doc_number)
            if temporal_context:
                query_parts.extend(temporal_context)

            search_query = " ".join(query_parts)

            # Lower min_rank for document number queries (more forgiving)
            min_rank = 0.001

            logger.info(
                "bm25_document_number_query_simplification",
                original_query=query,
                simplified_query=search_query,
                doc_number=doc_number,
                doc_type_original=doc_type_keyword,
                doc_type_normalized=normalized_type,
                temporal_context=temporal_context,
                min_rank=min_rank,
                reason="extracting_core_terms_with_temporal_context",
            )

            # MULTI-PATTERN TITLE MATCHING for document number queries
            # PostgreSQL FTS doesn't index numbers well, so we need direct ILIKE filters
            # Generate multiple patterns to handle all Italian document title formats:
            # - INPS: "Messaggio numero 3585" (uses "numero" not "n.")
            # - Agenzia Entrate: "Risoluzione n. 64"
            # - Legislative: "DPR n. 1124/1965" (compound references)
            if doc_number:
                # Get year for compound references (e.g., "DPR 1124/1965")
                doc_year = llm_doc_ref.get("year") if llm_doc_ref else None

                # Get document type for pattern generation
                # normalized_type is set above from either LLM or regex extraction
                doc_type_for_patterns = normalized_type if normalized_type not in ("numero", "n.", "n") else None

                # Generate multiple title patterns for better recall
                title_patterns = self._generate_title_patterns(
                    doc_type=doc_type_for_patterns,
                    doc_number=doc_number,
                    doc_year=doc_year,
                )

                # Store for use in search service SQL filter
                filters["title_patterns"] = title_patterns

                # CRITICAL: Remove category filter for document number queries
                # Users reference documents by number regardless of category
                # (e.g., "Risoluzione n. 64" exists in DB but category mismatch would exclude it)
                if "category" in filters:
                    removed_category = filters.pop("category")
                    logger.info(
                        "bm25_document_number_category_filter_removed",
                        doc_number=doc_number,
                        removed_category=removed_category,
                        reason="document_numbers_are_category_agnostic",
                    )

                logger.info(
                    "bm25_document_number_title_patterns_generated",
                    doc_number=doc_number,
                    doc_type=doc_type_for_patterns,
                    doc_year=doc_year,
                    patterns_count=len(title_patterns),
                    patterns=title_patterns,
                    reason="multi_pattern_matching_for_all_document_formats",
                )

        # ITALIAN ORGANIZATION HANDLING: Extract organization from query and map to source filter
        # HYBRID approach: tries pattern matching first, falls back to canonical facts for typos
        # This handles queries like "dell'agenzia delle entrate" which don't appear in document text
        source_pattern = self._extract_organization_filter(query, canonical_facts)
        if source_pattern:
            filters["source_pattern"] = source_pattern
            logger.info(
                "bm25_organization_filter_detected",
                original_query=query,
                source_pattern=source_pattern,
                reason="mapping_org_mention_to_source_filter",
            )

        # LLM KEYWORDS HANDLING: Use semantic keywords for topic-based searches
        # When LLM extracts keywords but no document number, use keywords for better search
        # This handles queries like "DL sicurezza lavoro" or "bonus psicologo 2025"
        if llm_doc_ref and not is_document_number_query:
            raw_keywords = llm_doc_ref.get("keywords")  # Can be list, str, or None
            llm_keywords: list[str] = raw_keywords if isinstance(raw_keywords, list) else []
            if llm_keywords:
                # Build search query from LLM keywords (core semantic concepts)
                # Include document type if present (e.g., "DL", "decreto")
                kw_doc_type: str | None = llm_doc_ref.get("type")
                kw_doc_year: str | None = llm_doc_ref.get("year")

                keyword_parts: list[str] = []
                if kw_doc_type:
                    keyword_parts.append(str(kw_doc_type))
                keyword_parts.extend(llm_keywords)
                if kw_doc_year:
                    keyword_parts.append(str(kw_doc_year))

                search_query = " ".join(keyword_parts)

                logger.info(
                    "bm25_using_llm_keywords_for_topic_search",
                    original_query=query,
                    llm_keywords=llm_keywords,
                    llm_type=kw_doc_type,
                    llm_year=kw_doc_year,
                    new_search_query=search_query,
                    reason="no_document_number_but_keywords_present",
                )

                # DEV-242 ADR-023: Re-apply topic synonym expansion after LLM keyword processing
                # Since LLM keywords override the earlier synonym expansion
                if topics:
                    expanded_terms = []
                    for topic in topics:
                        if topic in TOPIC_KEYWORDS:
                            expanded_terms.extend(TOPIC_KEYWORDS[topic][:3])
                    if expanded_terms:
                        search_terms = search_query.split()
                        unique_terms = list(dict.fromkeys(search_terms + expanded_terms))
                        search_query = " ".join(unique_terms)
                        logger.info(
                            "topic_synonym_expansion_post_llm",
                            topics=topics,
                            expanded_terms=expanded_terms,
                            final_search_query=search_query[:100],
                            reason="adr_023_semantic_expansion_after_llm",
                        )

        # For aggregation queries with multiple months, try single-month searches FIRST
        # This avoids strict AND failures when documents only match one month
        months_in_query = []
        if is_aggregation:
            for month in [
                "gennaio",
                "febbraio",
                "marzo",
                "aprile",
                "maggio",
                "giugno",
                "luglio",
                "agosto",
                "settembre",
                "ottobre",
                "novembre",
                "dicembre",
            ]:
                if month in search_query.lower():
                    months_in_query.append(month)

        search_results = []

        if is_aggregation and len(months_in_query) > 1:
            # Multi-month aggregation: try each month separately with OR search (more forgiving)
            logger.info(
                "bm25_multi_month_aggregation_detected",
                original_query=search_query,
                months_found=months_in_query,
                reason="trying_single_months_first_for_better_recall",
            )

            all_month_results = []
            seen_ids = set()

            for month in months_in_query:
                # Create single-month query by removing other months
                month_query = search_query.lower()
                for other_month in months_in_query:
                    if other_month != month:
                        month_query = month_query.replace(other_month, "").strip()

                # Clean up extra spaces
                month_query = " ".join(month_query.split())

                logger.info("bm25_trying_single_month", month=month, month_query=month_query)

                # Use OR search for better recall with single month
                month_results = await self.search_service.search_with_or_fallback(
                    query=month_query,
                    limit=max_results,
                    offset=0,
                    category=category,
                    min_rank=min_rank * 0.5,  # Lower threshold for multi-month aggregation
                    source_pattern=filters.get("source_pattern"),
                    publication_year=publication_year,
                    title_patterns=filters.get("title_patterns"),
                    topics=topics,  # DEV-242: Topic-based filter (ADR-023)
                )

                if month_results:
                    logger.info(
                        "bm25_single_month_success",
                        month=month,
                        results_count=len(month_results),
                        month_query=month_query,
                    )
                    # Deduplicate by ID
                    for result in month_results:
                        if result.id not in seen_ids:
                            all_month_results.append(result)
                            seen_ids.add(result.id)

            search_results = all_month_results[:max_results]  # Respect max_results limit

            if search_results:
                logger.info(
                    "bm25_multi_month_aggregation_success",
                    total_results=len(search_results),
                    unique_documents=len(seen_ids),
                )
        else:
            # Single month or non-aggregation: use standard search flow
            # First attempt: strict AND search (websearch_to_tsquery)
            search_results = await self.search_service.search(
                query=search_query,
                limit=max_results,
                offset=0,
                category=category,
                min_rank=min_rank,
                source_pattern=filters.get("source_pattern"),
                publication_year=publication_year,
                title_patterns=filters.get("title_patterns"),
                topics=topics,  # DEV-242: Topic-based filter (ADR-023)
            )

            # Fallback: if no results with strict AND, try relaxed OR search
            if not search_results and search_query:
                logger.info(
                    "bm25_search_fallback_triggered",
                    original_query=query,
                    search_query=search_query,
                    reason="strict_and_returned_zero",
                )

                # Try OR-based fallback search (plainto_tsquery)
                search_results = await self.search_service.search_with_or_fallback(
                    query=search_query,
                    limit=max_results,
                    offset=0,
                    category=category,
                    min_rank=min_rank * 0.5,  # Lower threshold for fallback
                    source_pattern=filters.get("source_pattern"),
                    publication_year=publication_year,
                    title_patterns=filters.get("title_patterns"),
                    topics=topics,  # DEV-242: Topic-based filter (ADR-023)
                )

                if search_results:
                    logger.info(
                        "bm25_search_fallback_success", results_count=len(search_results), fallback_query=search_query
                    )

        # FINAL FALLBACK: If still no results and query had organization keywords, try without them
        # This handles cases where source filter might be too restrictive or pattern doesn't match
        if not search_results and source_pattern:
            query_without_org = self._remove_organization_keywords(search_query)

            if query_without_org != search_query:
                logger.info(
                    "bm25_org_keyword_removal_fallback",
                    original_query=search_query,
                    query_without_org=query_without_org,
                    source_pattern_used=source_pattern,
                    reason="zero_results_with_org_filter_trying_without",
                )

                # Try search without organization keywords and without source filter
                search_results = await self.search_service.search_with_or_fallback(
                    query=query_without_org,
                    limit=max_results,
                    offset=0,
                    category=category,
                    min_rank=min_rank * 0.3,  # Very low threshold for last resort
                    source_pattern=None,  # Remove source filter too
                    publication_year=publication_year,
                    title_patterns=filters.get("title_patterns"),
                    topics=topics,  # DEV-242: Topic-based filter (ADR-023)
                )

                if search_results:
                    logger.info(
                        "bm25_org_keyword_removal_success",
                        results_count=len(search_results),
                        query_without_org=query_without_org,
                    )

        # TDD: MULTI-PASS FALLBACK - Extract any numbers and try as document numbers
        # This handles edge cases like "la 64" where regex doesn't detect document type
        # but user is clearly asking about a numbered document
        if not search_results:
            numbers = re.findall(r"\d+", query)
            if numbers:
                logger.info(
                    "bm25_multipass_number_fallback_triggered",
                    query=query,
                    numbers_found=numbers,
                    reason="all_other_searches_failed_trying_numbers_as_document_refs",
                )

                for num in numbers:
                    # Try each number as a document number using multiple patterns
                    fallback_patterns = self._generate_title_patterns(
                        doc_type=None,  # No type context in last-resort fallback
                        doc_number=num,
                        doc_year=None,
                    )
                    fallback_results = await self.search_service.search(
                        query=search_query,
                        title_patterns=fallback_patterns,
                        limit=max_results,
                        category=category,
                        source_pattern=None,  # Remove restrictive filters
                        publication_year=publication_year,
                        topics=topics,  # DEV-242: Topic-based filter (ADR-023)
                    )

                    if fallback_results:
                        search_results = fallback_results
                        logger.info(
                            "bm25_multipass_number_fallback_success",
                            number=num,
                            results_count=len(fallback_results),
                            patterns_tried=fallback_patterns,
                            reason=f"found_documents_matching_number_{num}",
                        )
                        break  # Found results, stop trying other numbers

        # Log warning for document number queries that returned no results
        # This helps identify patterns that need to be added in the future
        if is_document_number_query and not search_results:
            title_patterns = filters.get("title_patterns", [])
            # Variables are defined inside 'if is_document_number_query:' block
            # so they will be available here when is_document_number_query is True
            logger.warning(
                "bm25_document_number_no_results",
                original_query=query,
                search_query=search_query,
                doc_number=doc_number,
                doc_type=locals().get("doc_type_for_patterns"),
                doc_year=locals().get("doc_year"),
                patterns_tried=title_patterns,
                reason="no_documents_matched_any_title_patterns_may_need_new_pattern",
            )

        # Convert to dict format for consistency
        bm25_results = []
        for result in search_results:
            bm25_results.append(
                {
                    "id": result.id,
                    "title": result.title,
                    "content": result.content,
                    "category": result.category,
                    "source": result.source or "unknown",
                    "source_url": result.source_url,
                    "rank_score": result.rank_score,
                    "relevance_score": result.relevance_score,
                    "updated_at": result.updated_at,
                    "publication_date": result.publication_date,
                    "highlight": result.highlight,
                }
            )

        return bm25_results

    async def _perform_vector_search(
        self, query: str, canonical_facts: list[str], filters: dict[str, Any]
    ) -> list[SearchResult]:
        """Perform vector semantic search."""
        if not self.vector_service or not self.vector_service.is_available():
            # Graceful degradation - return empty results if vector service unavailable
            logger.warning("vector_service_unavailable", query=query)
            return []

        try:
            # Create embedding for query
            query_text = query
            if canonical_facts:
                # Enhance with canonical facts
                query_text = f"{query} {' '.join(canonical_facts)}"

            embedding = self.vector_service.create_embedding(query_text)
            if not embedding:
                logger.warning("vector_embedding_failed", query=query)
                return []

            # Perform vector search
            vector_results = self.vector_service.search_similar(
                embedding=embedding, top_k=self.config.vector_top_k, filters=filters
            )

            # Convert to SearchResult format
            search_results = []
            for i, result in enumerate(vector_results):
                # Extract publication_date from metadata if available
                metadata = result.get("metadata", {})
                publication_date_value = metadata.get("publication_date")

                # Convert publication_date string to date object if needed
                publication_date_obj = None
                if publication_date_value:
                    if isinstance(publication_date_value, str):
                        try:
                            from datetime import datetime

                            publication_date_obj = datetime.fromisoformat(publication_date_value).date()
                        except Exception:
                            pass
                    elif isinstance(publication_date_value, date):
                        publication_date_obj = publication_date_value

                search_result = SearchResult(
                    id=str(result["id"]),
                    title=metadata.get("title", "Unknown Title"),
                    content=metadata.get("content", ""),
                    category=metadata.get("category", "unknown"),
                    score=0.0,  # Will be calculated in hybrid scoring
                    source=metadata.get("source", "vector_db"),
                    publication_date=publication_date_obj,
                    vector_score=float(result["score"]),
                    search_method="hybrid",
                    rank_position=i + 1,
                    metadata=metadata,
                )
                search_results.append(search_result)

            return search_results

        except Exception as e:
            logger.error("vector_search_error", error=str(e), query=query)
            return []

    def _combine_and_deduplicate_results(
        self, bm25_results: list[SearchResult], vector_results: list[SearchResult]
    ) -> list[SearchResult]:
        """Combine results from BM25 and vector search, removing duplicates."""
        results_by_id: dict[str, SearchResult] = {}

        # Add BM25 results
        for result in bm25_results:
            results_by_id[result.id] = result

        # Add vector results, merging with BM25 results if duplicate IDs found
        for result in vector_results:
            if result.id in results_by_id:
                # Merge vector score into existing result
                existing = results_by_id[result.id]
                existing.vector_score = result.vector_score
                # Use better metadata if vector result has more info
                if len(result.metadata) > len(existing.metadata):
                    existing.metadata.update(result.metadata)
            else:
                results_by_id[result.id] = result

        return list(results_by_id.values())

    def _apply_hybrid_scoring(self, results: list[SearchResult]) -> list[SearchResult]:
        """Apply hybrid scoring combining BM25, vector, recency, quality, and source authority.

        DEV-BE-78: Enhanced scoring with text_quality and source authority weighting.
        """
        if not results:
            return results

        # Import ranking utilities
        from app.services.ranking_utils import clamp_quality, get_source_authority_boost

        # Normalize scores to 0-1 range for fair combination
        bm25_scores = [r.bm25_score for r in results if r.bm25_score is not None]
        vector_scores = [r.vector_score for r in results if r.vector_score is not None]

        max_bm25 = max(bm25_scores) if bm25_scores else 1.0
        max_vector = max(vector_scores) if vector_scores else 1.0

        # Avoid division by zero
        max_bm25 = max(max_bm25, 0.001)
        max_vector = max(max_vector, 0.001)

        # Apply hybrid scoring to each result
        for result in results:
            # Normalize individual scores
            norm_bm25 = (result.bm25_score or 0.0) / max_bm25
            norm_vector = (result.vector_score or 0.0) / max_vector

            # Calculate recency boost
            recency_boost = self._calculate_recency_boost(result.updated_at)
            result.recency_score = recency_boost

            # DEV-BE-78: Calculate text quality score
            # Get quality from metadata or use neutral value (0.5)
            raw_quality = result.metadata.get("text_quality")
            quality_score = clamp_quality(raw_quality)

            # DEV-BE-78: Calculate source authority boost
            source_boost = get_source_authority_boost(result.source)

            # Store additional scores in metadata for debugging/logging
            result.metadata["quality_score"] = quality_score
            result.metadata["source_boost"] = source_boost

            # Combine scores using configured weights (sum to 1.0)
            # Weights are guaranteed non-None after __post_init__
            bm25_w = self.config.bm25_weight or 0.0
            vector_w = self.config.vector_weight or 0.0
            recency_w = self.config.recency_weight or 0.0
            quality_w = self.config.quality_weight or 0.0
            source_w = self.config.source_weight or 0.0

            combined_score = (
                bm25_w * norm_bm25
                + vector_w * norm_vector
                + recency_w * recency_boost
                + quality_w * quality_score
                + source_w * source_boost
            )

            # DEV-242 Phase 11: Apply tier-based multiplier
            # Laws (tier 1) get 1.25x boost, news (tier 3) get 0.80x penalty
            tier = result.metadata.get("tier")
            tier_multiplier = get_tier_multiplier(tier)
            combined_score *= tier_multiplier

            result.score = combined_score

        return results

    def _calculate_recency_boost(self, updated_at: datetime | str | None) -> float:
        """Calculate recency boost based on document age.

        Handles both datetime objects and ISO string representations (from cache/serialization).
        """
        if not updated_at:
            return 0.0  # No boost for documents without timestamp

        # FIX: Handle string datetime (from cache or serialization)
        # This prevents AttributeError: 'str' object has no attribute 'tzinfo'
        if isinstance(updated_at, str):
            try:
                updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            except Exception as e:
                logger.warning(
                    "invalid_datetime_format", updated_at=updated_at, error=str(e), reason="cannot_parse_iso_string"
                )
                return 0.0

        # At this point, updated_at is guaranteed to be datetime (str case is handled above)
        # Ensure timezone-aware comparison
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=UTC)

        now = datetime.now(UTC)
        age_days = (now - updated_at).total_seconds() / 86400  # Convert to days

        # Apply exponential decay: newer documents get higher boost
        decay_factor = math.exp(-age_days / self.config.recency_decay_days)

        # Scale to 0-1 range
        recency_boost = min(max(decay_factor, 0.0), 1.0)

        return recency_boost

    def _apply_final_ranking(self, results: list[SearchResult], max_results: int) -> list[SearchResult]:
        """Apply final ranking and filtering."""
        # Filter by minimum score threshold
        filtered_results = [r for r in results if r.score >= self.config.min_score_threshold]

        # Sort by combined score (already done but ensure consistency)
        filtered_results.sort(key=lambda x: x.score, reverse=True)

        # Add rank positions
        for i, result in enumerate(filtered_results[:max_results]):
            result.rank_position = i + 1

        return filtered_results[:max_results]

    async def fetch_recent_kb_for_changes(self, query_data: dict[str, Any]) -> list[SearchResult]:
        """RAG STEP 26 — KnowledgeSearch.context_topk fetch recent KB for changes.

        This method specifically fetches recent KB changes when a Golden Set hit occurs,
        to determine if KB has newer or conflicting information that should be merged
        with the Golden Set response.

        Args:
            query_data: Dictionary containing:
                - query: The user's query text
                - canonical_facts: List of extracted canonical facts (optional)
                - user_id: User identifier
                - session_id: Session identifier
                - trace_id: Trace identifier for logging
                - golden_timestamp: Timestamp of the Golden Set entry
                - context_check: Flag indicating this is for context checking
                - recency_threshold_days: Days threshold for considering "recent" (default: 14)
                - golden_metadata: Golden Set metadata for conflict detection (optional)

        Returns:
            List of SearchResult objects with recent KB changes that might conflict
            or provide newer information than the Golden Set
        """
        start_time = time.perf_counter()

        # Extract parameters
        query = query_data.get("query", "").strip()
        trace_id = query_data.get("trace_id")
        golden_timestamp = query_data.get("golden_timestamp")
        recency_threshold_days = query_data.get("recency_threshold_days", 14)
        golden_metadata = query_data.get("golden_metadata", {})

        # RAG STEP 26 constants
        STEP_NUM = 26
        STEP_ID = "RAG.kb.knowledgesearch.context.topk.fetch.recent.kb.for.changes"
        NODE_LABEL = "KBContextCheck"

        try:
            # Use timer context manager for performance tracking
            with rag_step_timer(STEP_NUM, STEP_ID, NODE_LABEL, query=query, trace_id=trace_id):
                # Initial logging
                rag_step_log(
                    step=STEP_NUM,
                    step_id=STEP_ID,
                    node_label=NODE_LABEL,
                    query=query,
                    trace_id=trace_id,
                    golden_timestamp=golden_timestamp.isoformat() if golden_timestamp else None,
                    recency_threshold_days=recency_threshold_days,
                    processing_stage="started",
                )

                if not query:
                    rag_step_log(
                        step=STEP_NUM,
                        step_id=STEP_ID,
                        node_label=NODE_LABEL,
                        trace_id=trace_id,
                        processing_stage="empty_query",
                        recent_changes_count=0,
                    )
                    return []

                # Perform hybrid search to get potential recent changes
                canonical_facts = query_data.get("canonical_facts", [])
                filters = query_data.get("filters", {})
                max_results = query_data.get("max_results", self.config.max_results * 2)  # Get more for filtering

                # Search for recent knowledge items
                all_results = await self._perform_hybrid_search(query, canonical_facts, filters, max_results)

                # Filter for recent changes
                recent_results = self._filter_recent_changes(all_results, golden_timestamp, recency_threshold_days)

                # Detect potential conflicts with Golden Set
                conflict_results = self._detect_conflicts_with_golden(recent_results, golden_metadata)

                # Final filtering and ranking for context
                context_results = self._rank_for_context_check(conflict_results)

                # Log results
                rag_step_log(
                    step=STEP_NUM,
                    step_id=STEP_ID,
                    node_label=NODE_LABEL,
                    query=query,
                    trace_id=trace_id,
                    recent_changes_count=len(context_results),
                    potential_conflicts=len([r for r in context_results if r.metadata.get("conflict_detected")]),
                    golden_timestamp=golden_timestamp.isoformat() if golden_timestamp else None,
                    processing_stage="completed",
                )

                if len(context_results) == 0:
                    rag_step_log(
                        step=STEP_NUM,
                        step_id=STEP_ID,
                        node_label=NODE_LABEL,
                        query=query,
                        trace_id=trace_id,
                        processing_stage="no_recent_changes",
                        message="No recent KB changes found newer than Golden Set",
                    )

                return context_results

        except Exception as exc:
            # Calculate latency even on error
            end_time = time.perf_counter()
            latency_ms = round((end_time - start_time) * 1000.0, 2)

            # Log error
            rag_step_log(
                step=STEP_NUM,
                step_id=STEP_ID,
                node_label=NODE_LABEL,
                level="ERROR",
                query=query,
                error=str(exc),
                latency_ms=latency_ms,
                trace_id=trace_id,
                processing_stage="error",
            )

            # Return empty results on error (graceful degradation)
            logger.error("kb_context_check_error", error=str(exc), trace_id=trace_id)
            return []

    def _filter_recent_changes(
        self, results: list[SearchResult], golden_timestamp: datetime | None, recency_threshold_days: int
    ) -> list[SearchResult]:
        """Filter results to only include recent changes."""
        if not results:
            return []

        now = datetime.now(UTC)

        # Calculate cutoff time - use the more recent of golden_timestamp or recency_threshold
        cutoff_time = now - timedelta(days=recency_threshold_days)
        if golden_timestamp:
            # Ensure timezone-aware comparison
            if golden_timestamp.tzinfo is None:
                golden_timestamp = golden_timestamp.replace(tzinfo=UTC)
            cutoff_time = max(cutoff_time, golden_timestamp)

        # Filter for recent results
        recent_results = []
        for result in results:
            if result.updated_at:
                # Ensure timezone-aware comparison
                updated_at = result.updated_at
                if updated_at.tzinfo is None:
                    updated_at = updated_at.replace(tzinfo=UTC)

                if updated_at > cutoff_time:
                    recent_results.append(result)

        return recent_results

    def _detect_conflicts_with_golden(
        self, results: list[SearchResult], golden_metadata: dict[str, Any]
    ) -> list[SearchResult]:
        """Detect potential conflicts between KB results and Golden Set."""
        if not results or not golden_metadata:
            return results

        golden_category = golden_metadata.get("category", "")
        golden_tags = set(golden_metadata.get("tags", []))

        for result in results:
            conflict_detected = False
            conflict_reasons = []

            # Check category conflicts
            if golden_category and result.category == golden_category:
                # Same category might indicate conflicting information
                conflict_detected = True
                conflict_reasons.append("same_category")

            # Check for conflict tags in metadata
            result_tags = set(result.metadata.get("conflict_tags", []))
            if result_tags.intersection({"supersedes_previous", "rate_change", "law_change"}):
                conflict_detected = True
                conflict_reasons.append("explicit_conflict_tags")

            # Check for overlapping content indicators
            if golden_tags and result.metadata.get("tags"):
                result_tag_set = set(result.metadata.get("tags", []))
                if golden_tags.intersection(result_tag_set):
                    conflict_detected = True
                    conflict_reasons.append("overlapping_tags")

            # Store conflict information in metadata
            if conflict_detected:
                result.metadata["conflict_detected"] = True
                result.metadata["conflict_reasons"] = conflict_reasons

                # Log potential conflict
                logger.info(
                    "potential_conflict_detected",
                    kb_result_id=result.id,
                    kb_title=result.title,
                    conflict_reasons=conflict_reasons,
                    golden_category=golden_category,
                )

        return results

    def _rank_for_context_check(self, results: list[SearchResult]) -> list[SearchResult]:
        """Apply specialized ranking for context checking."""
        if not results:
            return []

        # Sort by combination of recency and conflict importance
        def context_score(result: SearchResult) -> float:
            base_score = result.score

            # Boost for recent updates
            recency_boost = result.recency_score or 0.0

            # Boost for potential conflicts
            conflict_boost = 0.2 if result.metadata.get("conflict_detected") else 0.0

            return base_score + (0.3 * recency_boost) + conflict_boost

        # Sort by context score
        results.sort(key=context_score, reverse=True)

        # Apply final filtering - limit to most relevant for context
        max_context_results = min(5, len(results))  # At most 5 context items

        return results[:max_context_results]


# Convenience function for direct usage
async def retrieve_knowledge_topk(query_data: dict[str, Any]) -> list[SearchResult]:
    """Convenience function to retrieve top-k knowledge items.

    Args:
        query_data: Query data dictionary with db_session and vector_service

    Returns:
        List of SearchResult objects
    """
    db_session = query_data.pop("db_session")
    vector_service = query_data.pop("vector_service", None)

    service = KnowledgeSearchService(db_session=db_session, vector_service=vector_service)

    return await service.retrieve_topk(query_data)
