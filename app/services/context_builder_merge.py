"""
RAG STEP 40 — ContextBuilder.merge facts and KB docs and optional doc facts

This module implements the context building logic that merges canonical facts,
KB search results, and optional document facts into a unified context for LLM processing.
It handles token budgets, content prioritization, and deduplication.

Based on Mermaid diagram: BuildContext (ContextBuilder.merge facts and KB docs and optional doc facts)
"""

import time
import re
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from app.services.knowledge_search_service import SearchResult
from app.observability.rag_logging import rag_step_log, rag_step_timer
from app.core.logging import logger


@dataclass
class ContextPart:
    """Individual piece of context from a source."""
    type: str  # "facts", "kb_docs", "document_facts"
    content: str
    tokens: int
    priority_score: float
    metadata: Dict[str, Any]


@dataclass
class MergedContext:
    """Result of context merging operation."""
    merged_context: str
    context_parts: List[Dict[str, Any]]
    token_count: int
    source_distribution: Dict[str, int]
    context_quality_score: float
    deduplication_applied: bool = False
    content_truncated: bool = False
    budget_exceeded: bool = False


class ContextBuilderMerge:
    """
    RAG STEP 40 — ContextBuilder for merging facts, KB docs, and document facts.
    
    This class handles the merging of different types of content into a unified
    context that will be passed to the LLM for response generation.
    """
    
    def __init__(self):
        self.STEP_NUM = 40
        self.STEP_ID = "RAG.facts.contextbuilder.merge.facts.and.kb.docs.and.optional.doc.facts"
        self.NODE_LABEL = "BuildContext"
        
        # Default configuration
        self.default_max_tokens = 1500
        self.default_priority_weights = {
            "facts": 0.3,
            "kb_docs": 0.5,
            "document_facts": 0.2
        }
        
    def merge_context(self, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge facts, KB docs, and optional document facts into unified context.
        
        Args:
            context_data: Dictionary containing:
                - canonical_facts: List of extracted canonical facts
                - kb_results: List of SearchResult from KB search
                - document_facts: Optional list of document-extracted facts
                - query: Original user query
                - trace_id: Trace identifier for logging
                - user_id: User identifier
                - session_id: Session identifier
                - max_context_tokens: Token budget limit (optional)
                - priority_weights: Weights for different content types (optional)
                
        Returns:
            Dict with merged context:
                - merged_context: Final context text
                - context_parts: List of individual context parts
                - token_count: Total tokens used
                - source_distribution: Distribution of content by type
                - context_quality_score: Quality assessment
        """
        start_time = time.perf_counter()
        
        # Extract parameters
        canonical_facts = context_data.get("canonical_facts", [])
        kb_results = context_data.get("kb_results", [])
        document_facts = context_data.get("document_facts", [])
        query = context_data.get("query", "")
        trace_id = context_data.get("trace_id")
        user_id = context_data.get("user_id")
        session_id = context_data.get("session_id")
        max_tokens = context_data.get("max_context_tokens", self.default_max_tokens)
        priority_weights = context_data.get("priority_weights", self.default_priority_weights)
        
        try:
            # Use timer context manager for performance tracking
            with rag_step_timer(
                self.STEP_NUM,
                self.STEP_ID,
                self.NODE_LABEL,
                query=query,
                trace_id=trace_id
            ):
                # Initial logging
                rag_step_log(
                    step=self.STEP_NUM,
                    step_id=self.STEP_ID,
                    node_label=self.NODE_LABEL,
                    query=query,
                    trace_id=trace_id,
                    user_id=user_id,
                    session_id=session_id,
                    facts_count=len(canonical_facts),
                    kb_results_count=len(kb_results),
                    document_facts_count=len(document_facts) if document_facts else 0,
                    max_tokens=max_tokens,
                    processing_stage="started"
                )
                
                # Handle empty inputs
                if not canonical_facts and not kb_results and not document_facts:
                    return self._create_empty_context_result(trace_id, user_id, session_id)
                
                # Convert inputs to ContextPart objects
                context_parts = self._create_context_parts(
                    canonical_facts, kb_results, document_facts, priority_weights
                )
                
                # Apply deduplication
                deduplicated_parts, deduplication_applied = self._deduplicate_content(context_parts)
                
                # Apply token budget and prioritization
                selected_parts, content_truncated, budget_exceeded = self._apply_token_budget(
                    deduplicated_parts, max_tokens
                )
                
                # Generate final merged context text
                merged_text = self._generate_merged_context_text(selected_parts, query)
                
                # Calculate metrics
                total_tokens = sum(part.tokens for part in selected_parts)
                source_distribution = self._calculate_source_distribution(selected_parts)
                quality_score = self._calculate_context_quality(selected_parts, query, total_tokens, max_tokens)
                
                # Create result
                result = MergedContext(
                    merged_context=merged_text,
                    context_parts=self._context_parts_to_dict(selected_parts),
                    token_count=total_tokens,
                    source_distribution=source_distribution,
                    context_quality_score=quality_score,
                    deduplication_applied=deduplication_applied,
                    content_truncated=content_truncated,
                    budget_exceeded=budget_exceeded
                )
                
                # Log completion
                rag_step_log(
                    step=self.STEP_NUM,
                    step_id=self.STEP_ID,
                    node_label=self.NODE_LABEL,
                    query=query,
                    trace_id=trace_id,
                    user_id=user_id,
                    session_id=session_id,
                    token_count=total_tokens,
                    max_tokens=max_tokens,
                    source_distribution=source_distribution,
                    context_quality_score=quality_score,
                    deduplication_applied=deduplication_applied,
                    content_truncated=content_truncated,
                    processing_stage="completed"
                )
                
                return self._convert_to_dict(result)
                
        except Exception as exc:
            # Calculate latency even on error
            end_time = time.perf_counter()
            latency_ms = round((end_time - start_time) * 1000.0, 2)
            
            # Log error
            rag_step_log(
                step=self.STEP_NUM,
                step_id=self.STEP_ID,
                node_label=self.NODE_LABEL,
                level="ERROR",
                query=query,
                error=str(exc),
                latency_ms=latency_ms,
                trace_id=trace_id,
                user_id=user_id,
                session_id=session_id,
                processing_stage="error"
            )
            
            # Return empty context on error (graceful degradation)
            logger.error("context_builder_merge_error", error=str(exc), trace_id=trace_id)
            return {
                "merged_context": "",
                "context_parts": [],
                "token_count": 0,
                "source_distribution": {"facts": 0, "kb_docs": 0, "document_facts": 0},
                "context_quality_score": 0.0,
                "deduplication_applied": False,
                "content_truncated": False,
                "budget_exceeded": False
            }
    
    def _create_context_parts(
        self, 
        canonical_facts: List[str], 
        kb_results: List[SearchResult], 
        document_facts: Optional[List[str]],
        priority_weights: Dict[str, float]
    ) -> List[ContextPart]:
        """Convert inputs to ContextPart objects."""
        
        parts = []
        
        # Process canonical facts
        for i, fact in enumerate(canonical_facts):
            if fact and fact.strip():
                tokens = self._estimate_tokens(fact)
                priority = priority_weights.get("facts", 0.3) + (0.1 / (i + 1))  # Earlier facts slightly higher priority
                
                parts.append(ContextPart(
                    type="facts",
                    content=fact.strip(),
                    tokens=tokens,
                    priority_score=priority,
                    metadata={"index": i, "source": "canonical_facts"}
                ))
        
        # Process KB results
        for i, result in enumerate(kb_results):
            if result.content and result.content.strip():
                # Use title + content for KB results
                kb_content = f"{result.title}: {result.content}"
                tokens = self._estimate_tokens(kb_content)
                
                # Priority based on weight, relevance score, and recency
                base_priority = priority_weights.get("kb_docs", 0.5)
                score_boost = result.score * 0.2 if result.score else 0.0
                recency_boost = self._calculate_recency_boost(result.updated_at) * 0.1
                priority = base_priority + score_boost + recency_boost - (0.05 * i)  # Slight penalty for lower rank
                
                parts.append(ContextPart(
                    type="kb_docs",
                    content=kb_content,
                    tokens=tokens,
                    priority_score=priority,
                    metadata={
                        "kb_id": result.id,
                        "title": result.title,
                        "score": result.score,
                        "category": result.category,
                        "source": result.source,
                        "updated_at": result.updated_at.isoformat() if result.updated_at else None,
                        "rank": i
                    }
                ))
        
        # Process document facts
        if document_facts:
            for i, doc_fact in enumerate(document_facts):
                if doc_fact and doc_fact.strip():
                    tokens = self._estimate_tokens(doc_fact)
                    priority = priority_weights.get("document_facts", 0.2) + (0.15 / (i + 1))  # High priority for early doc facts
                    
                    parts.append(ContextPart(
                        type="document_facts",
                        content=doc_fact.strip(),
                        tokens=tokens,
                        priority_score=priority,
                        metadata={"index": i, "source": "document_facts"}
                    ))
        
        return parts
    
    def _deduplicate_content(self, context_parts: List[ContextPart]) -> Tuple[List[ContextPart], bool]:
        """Remove duplicate or highly similar content."""
        
        if len(context_parts) <= 1:
            return context_parts, False
        
        deduplicated = []
        seen_content = []
        deduplication_applied = False
        
        # Sort by priority (highest first) to keep best content
        sorted_parts = sorted(context_parts, key=lambda x: x.priority_score, reverse=True)
        
        for part in sorted_parts:
            is_duplicate = False
            
            # Check for exact matches or high similarity
            for seen in seen_content:
                similarity = self._calculate_content_similarity(part.content, seen)
                if similarity > 0.8:  # 80% similarity threshold
                    is_duplicate = True
                    deduplication_applied = True
                    break
            
            if not is_duplicate:
                deduplicated.append(part)
                seen_content.append(part.content)
        
        return deduplicated, deduplication_applied
    
    def _apply_token_budget(
        self, 
        context_parts: List[ContextPart], 
        max_tokens: int
    ) -> Tuple[List[ContextPart], bool, bool]:
        """Apply token budget constraints with priority-based selection."""
        
        if not context_parts:
            return [], False, False
        
        # Sort by priority score (descending)
        sorted_parts = sorted(context_parts, key=lambda x: x.priority_score, reverse=True)
        
        selected_parts = []
        total_tokens = 0
        content_truncated = False
        budget_exceeded = False
        
        for part in sorted_parts:
            if total_tokens + part.tokens <= max_tokens:
                selected_parts.append(part)
                total_tokens += part.tokens
            else:
                # Try to fit truncated content
                remaining_tokens = max_tokens - total_tokens
                if remaining_tokens > 50:  # Minimum meaningful content
                    truncated_content = self._truncate_content(part.content, remaining_tokens)
                    if truncated_content:
                        truncated_part = ContextPart(
                            type=part.type,
                            content=truncated_content,
                            tokens=remaining_tokens,
                            priority_score=part.priority_score,
                            metadata={**part.metadata, "truncated": True}
                        )
                        selected_parts.append(truncated_part)
                        content_truncated = True
                        total_tokens = max_tokens
                        break
                
                budget_exceeded = True
        
        return selected_parts, content_truncated, budget_exceeded
    
    def _generate_merged_context_text(self, context_parts: List[ContextPart], query: str) -> str:
        """Generate final merged context text."""
        
        if not context_parts:
            return "No specific context available for this query."
        
        # Group parts by type
        facts_parts = [p for p in context_parts if p.type == "facts"]
        kb_parts = [p for p in context_parts if p.type == "kb_docs"]
        doc_parts = [p for p in context_parts if p.type == "document_facts"]
        
        sections = []
        
        # Facts section
        if facts_parts:
            facts_text = " ".join([p.content for p in facts_parts])
            sections.append(facts_text)
        
        # KB docs section
        if kb_parts:
            kb_text = "\n\nFrom knowledge base:\n" + "\n\n".join([p.content for p in kb_parts])
            sections.append(kb_text)
        
        # Document facts section
        if doc_parts:
            doc_text = "\n\nFrom your documents:\n" + " ".join([p.content for p in doc_parts])
            sections.append(doc_text)
        
        return "\n".join(sections).strip()
    
    def _calculate_source_distribution(self, context_parts: List[ContextPart]) -> Dict[str, int]:
        """Calculate distribution of content by source type."""
        
        distribution = {"facts": 0, "kb_docs": 0, "document_facts": 0}
        
        for part in context_parts:
            if part.type in distribution:
                distribution[part.type] += 1
        
        return distribution
    
    def _calculate_context_quality(
        self, 
        context_parts: List[ContextPart], 
        query: str, 
        total_tokens: int, 
        max_tokens: int
    ) -> float:
        """Calculate context quality score based on various factors."""
        
        if not context_parts:
            return 0.0
        
        # Base quality from priority scores
        avg_priority = sum(p.priority_score for p in context_parts) / len(context_parts)
        
        # Diversity bonus (having multiple types)
        types_present = len(set(p.type for p in context_parts))
        diversity_bonus = min(types_present * 0.1, 0.2)
        
        # Token utilization efficiency
        utilization = total_tokens / max_tokens if max_tokens > 0 else 0
        utilization_score = min(utilization * 0.15, 0.15)
        
        # Content relevance (simple keyword matching)
        query_keywords = set(query.lower().split())
        relevance_scores = []
        
        for part in context_parts:
            content_words = set(part.content.lower().split())
            overlap = len(query_keywords.intersection(content_words))
            relevance = overlap / len(query_keywords) if query_keywords else 0
            relevance_scores.append(relevance)
        
        avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0
        relevance_bonus = avg_relevance * 0.25
        
        # Final quality score (0.0 to 1.0)
        quality = min(avg_priority + diversity_bonus + utilization_score + relevance_bonus, 1.0)
        
        return round(quality, 2)
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text (rough approximation)."""
        if not text:
            return 0
        
        # Simple estimation: ~4 characters per token on average
        char_count = len(text)
        token_estimate = max(1, char_count // 4)
        
        return token_estimate
    
    def _calculate_recency_boost(self, updated_at: Optional[datetime]) -> float:
        """Calculate recency boost for content."""
        if not updated_at:
            return 0.0
        
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        
        now = datetime.now(timezone.utc)
        age_days = (now - updated_at).total_seconds() / 86400
        
        # Exponential decay: newer content gets higher boost
        if age_days <= 7:
            return 1.0  # Very recent
        elif age_days <= 30:
            return 0.7  # Recent
        elif age_days <= 90:
            return 0.4  # Somewhat recent
        else:
            return 0.1  # Old
    
    def _calculate_content_similarity(self, content1: str, content2: str) -> float:
        """Calculate similarity between two pieces of content."""
        if not content1 or not content2:
            return 0.0
        
        # Simple word-based similarity
        words1 = set(re.findall(r'\w+', content1.lower()))
        words2 = set(re.findall(r'\w+', content2.lower()))
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        similarity = len(intersection) / len(union) if union else 0.0
        return similarity
    
    def _truncate_content(self, content: str, max_tokens: int) -> str:
        """Truncate content to fit within token budget."""
        if not content:
            return ""
        
        # Rough truncation based on character count
        max_chars = max_tokens * 4  # ~4 chars per token
        
        if len(content) <= max_chars:
            return content
        
        # Try to truncate at sentence boundaries
        sentences = re.split(r'[.!?]+', content[:max_chars])
        if len(sentences) > 1:
            # Keep all but the last (potentially incomplete) sentence
            truncated = '. '.join(sentences[:-1]) + '.'
            if len(truncated) > 10:  # Ensure meaningful content
                return truncated + "..."
        
        # Fallback to character truncation
        return content[:max_chars-3] + "..."
    
    def _context_parts_to_dict(self, context_parts: List[ContextPart]) -> List[Dict[str, Any]]:
        """Convert ContextPart objects to dictionaries."""
        return [
            {
                "type": part.type,
                "content": part.content,
                "tokens": part.tokens,
                "priority_score": part.priority_score,
                **part.metadata
            }
            for part in context_parts
        ]
    
    def _create_empty_context_result(self, trace_id: Optional[str], user_id: Optional[str], session_id: Optional[str]) -> Dict[str, Any]:
        """Create result for empty input scenario."""
        
        rag_step_log(
            step=self.STEP_NUM,
            step_id=self.STEP_ID,
            node_label=self.NODE_LABEL,
            trace_id=trace_id,
            user_id=user_id,
            session_id=session_id,
            token_count=8,
            source_distribution={"facts": 0, "kb_docs": 0, "document_facts": 0},
            context_quality_score=0.0,
            processing_stage="empty_inputs"
        )
        
        return {
            "merged_context": "No specific context available for this query.",
            "context_parts": [],
            "token_count": 8,
            "source_distribution": {"facts": 0, "kb_docs": 0, "document_facts": 0},
            "context_quality_score": 0.0,
            "deduplication_applied": False,
            "content_truncated": False,
            "budget_exceeded": False
        }
    
    def _convert_to_dict(self, result: MergedContext) -> Dict[str, Any]:
        """Convert MergedContext to dictionary."""
        return {
            "merged_context": result.merged_context,
            "context_parts": result.context_parts,
            "token_count": result.token_count,
            "source_distribution": result.source_distribution,
            "context_quality_score": result.context_quality_score,
            "deduplication_applied": result.deduplication_applied,
            "content_truncated": result.content_truncated,
            "budget_exceeded": result.budget_exceeded
        }


# Convenience function for direct usage
def merge_context(context_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to merge context from facts, KB docs, and document facts.
    
    Args:
        context_data: Context data dictionary
        
    Returns:
        Dict with merged context result
    """
    service = ContextBuilderMerge()
    return service.merge_context(context_data)