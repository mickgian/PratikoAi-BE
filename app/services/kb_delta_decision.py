"""
RAG STEP 27 — KB newer than Golden as of or conflicting tags?

This module implements the decision logic that compares KB results from STEP 26
with Golden Set metadata to determine whether KB has newer or conflicting information
that requires merging context instead of serving Golden Set answer directly.

Based on Mermaid diagram: KBDelta (KB newer than Golden as of or conflicting tags?)
"""

import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Set

from app.services.knowledge_search_service import SearchResult
from app.observability.rag_logging import rag_step_log, rag_step_timer
from app.core.logging import logger


class KBDeltaDecision:
    """
    RAG STEP 27 — Decision logic for comparing KB results with Golden Set.
    
    This class encapsulates the decision logic that determines whether
    KB has newer or conflicting information compared to Golden Set.
    """
    
    def __init__(self):
        self.STEP_NUM = 27
        self.STEP_ID = "RAG.golden.kb.newer.than.golden.as.of.or.conflicting.tags"
        self.NODE_LABEL = "KBDelta"
    
    def evaluate_kb_vs_golden(self, decision_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate if KB has newer or conflicting information vs Golden Set.
        
        Args:
            decision_data: Dictionary containing:
                - kb_results: List of SearchResult from STEP 26
                - golden_metadata: Golden Set metadata (timestamp, tags, etc.)
                - trace_id: Trace identifier for logging
                - user_id: User identifier  
                - session_id: Session identifier
                
        Returns:
            Dict with decision result:
                - decision: "newer_kb" | "no_newer_kb"
                - reason: Explanation of the decision
                - newer_count: Number of newer KB results
                - conflict_count: Number of conflicting results
                - should_merge_context: Boolean flag
        """
        start_time = time.perf_counter()
        
        # Extract parameters
        kb_results = decision_data.get("kb_results", [])
        golden_metadata = decision_data.get("golden_metadata", {})
        trace_id = decision_data.get("trace_id")
        user_id = decision_data.get("user_id")
        session_id = decision_data.get("session_id")
        
        try:
            # Use timer context manager for performance tracking
            with rag_step_timer(
                self.STEP_NUM,
                self.STEP_ID,
                self.NODE_LABEL,
                trace_id=trace_id,
                kb_results_count=len(kb_results)
            ):
                # Initial logging
                rag_step_log(
                    step=self.STEP_NUM,
                    step_id=self.STEP_ID,
                    node_label=self.NODE_LABEL,
                    trace_id=trace_id,
                    user_id=user_id,
                    session_id=session_id,
                    kb_results_count=len(kb_results),
                    has_golden_metadata=bool(golden_metadata),
                    processing_stage="started"
                )
                
                # Handle edge case: no KB results
                if not kb_results:
                    result = self._create_decision_result(
                        decision="no_newer_kb",
                        reason="No KB results to compare with Golden Set",
                        newer_count=0,
                        conflict_count=0
                    )
                    
                    self._log_decision(result, trace_id, user_id, session_id, "no_kb_results")
                    return result
                
                # Handle edge case: no Golden metadata
                if not golden_metadata:
                    result = self._create_decision_result(
                        decision="newer_kb",
                        reason="No Golden Set metadata available, using KB results",
                        newer_count=len(kb_results),
                        conflict_count=0
                    )
                    
                    self._log_decision(result, trace_id, user_id, session_id, "no_golden_metadata")
                    return result
                
                # Perform main comparison
                comparison_result = self._compare_kb_with_golden(kb_results, golden_metadata)
                
                # Make decision based on comparison
                decision_result = self._make_decision(comparison_result)
                
                # Log final decision
                self._log_decision(decision_result, trace_id, user_id, session_id, "comparison_complete")
                
                return decision_result
                
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
                error=str(exc),
                latency_ms=latency_ms,
                trace_id=trace_id,
                user_id=user_id,
                session_id=session_id,
                processing_stage="error"
            )
            
            # Return safe default on error
            logger.error("kb_delta_decision_error", error=str(exc), trace_id=trace_id)
            return self._create_decision_result(
                decision="no_newer_kb",
                reason=f"Error in decision logic: {str(exc)}",
                newer_count=0,
                conflict_count=0
            )
    
    def _compare_kb_with_golden(self, kb_results: List[SearchResult], golden_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Compare KB results with Golden Set metadata."""
        
        # Extract Golden Set information
        golden_timestamp = golden_metadata.get("updated_at")
        golden_tags = set(golden_metadata.get("tags", []))
        golden_category = golden_metadata.get("category", "")
        
        # Ensure golden timestamp is timezone-aware
        if golden_timestamp and golden_timestamp.tzinfo is None:
            golden_timestamp = golden_timestamp.replace(tzinfo=timezone.utc)
        
        # Calculate Golden Set age
        now = datetime.now(timezone.utc)
        golden_age_days = None
        if golden_timestamp:
            golden_age_days = (now - golden_timestamp).total_seconds() / 86400
        
        # Analyze KB results
        newer_results = []
        conflict_results = []
        all_conflict_types = set()
        kb_newest_timestamp = None
        
        for result in kb_results:
            result_timestamp = result.updated_at
            if result_timestamp and result_timestamp.tzinfo is None:
                result_timestamp = result_timestamp.replace(tzinfo=timezone.utc)
            
            # Track newest KB timestamp
            if result_timestamp:
                if kb_newest_timestamp is None or result_timestamp > kb_newest_timestamp:
                    kb_newest_timestamp = result_timestamp
            
            # Check if KB result is newer than Golden
            is_newer = False
            if golden_timestamp and result_timestamp:
                is_newer = result_timestamp > golden_timestamp
            elif not golden_timestamp:
                is_newer = True  # No golden timestamp, consider KB as "newer"
            
            if is_newer:
                newer_results.append(result)
            
            # Check for conflicts
            has_conflict = self._detect_conflicts(result, golden_tags, golden_category)
            if has_conflict:
                conflict_results.append(result)
                # Collect conflict types
                conflict_reasons = result.metadata.get("conflict_reasons", [])
                all_conflict_types.update(conflict_reasons)
        
        # Calculate KB newest age
        kb_newest_age_days = None
        if kb_newest_timestamp:
            kb_newest_age_days = (now - kb_newest_timestamp).total_seconds() / 86400
        
        return {
            "newer_results": newer_results,
            "conflict_results": conflict_results,
            "newer_count": len(newer_results),
            "conflict_count": len(conflict_results),
            "conflict_types": list(all_conflict_types),
            "golden_age_days": golden_age_days,
            "kb_newest_age_days": kb_newest_age_days,
            "golden_timestamp": golden_timestamp,
            "kb_newest_timestamp": kb_newest_timestamp
        }
    
    def _detect_conflicts(self, kb_result: SearchResult, golden_tags: Set[str], golden_category: str) -> bool:
        """Detect if KB result conflicts with Golden Set."""
        
        # Check if conflict already detected by STEP 26
        if kb_result.metadata.get("conflict_detected", False):
            return True
        
        # Additional conflict detection logic
        result_tags = set(kb_result.metadata.get("tags", []))
        
        # Check for explicit conflict indicators
        conflict_indicators = {"supersedes_previous", "rate_change", "law_change", "updated_info"}
        if result_tags.intersection(conflict_indicators):
            return True
        
        # Check for same category only if there are strong conflict signals
        if golden_category and kb_result.category == golden_category:
            # Only flag as conflict if:
            # 1. There are overlapping tags AND explicit conflict indicators
            # 2. OR there are strong contradiction signals in the tags
            if golden_tags and result_tags.intersection(golden_tags):
                # Check for contradiction signals
                contradiction_signals = {"contradicts", "replaces", "overrides", "supersedes"}
                if result_tags.intersection(contradiction_signals):
                    return True
                # Or explicit conflict indicators
                if result_tags.intersection(conflict_indicators):
                    return True
        
        return False
    
    def _make_decision(self, comparison_result: Dict[str, Any]) -> Dict[str, Any]:
        """Make the final decision based on comparison results."""
        
        newer_count = comparison_result["newer_count"]
        conflict_count = comparison_result["conflict_count"]
        conflict_types = comparison_result["conflict_types"]
        golden_age_days = comparison_result["golden_age_days"]
        kb_newest_age_days = comparison_result["kb_newest_age_days"]
        
        # Decision logic
        should_merge_context = False
        decision = "no_newer_kb"
        reason_parts = []
        
        # Primary decision factors
        if newer_count > 0:
            should_merge_context = True
            decision = "newer_kb"
            if golden_age_days is not None:
                reason_parts.append(f"KB has {newer_count} results newer than Golden Set ({golden_age_days:.0f} days old)")
            else:
                reason_parts.append(f"KB has {newer_count} newer results")
        
        # Conflict-based decision
        if conflict_count > 0:
            should_merge_context = True
            decision = "newer_kb"
            if conflict_types:
                reason_parts.append(f"conflicts detected: {', '.join(conflict_types)}")
            else:
                reason_parts.append(f"{conflict_count} conflicts detected")
        
        # Final reason
        if not reason_parts:
            if golden_age_days is not None:
                reason = f"No KB results newer than Golden Set ({golden_age_days:.0f} days old)"
            else:
                reason = "No newer or conflicting KB results found"
        else:
            reason = ", with ".join(reason_parts)
        
        # Create result
        result = self._create_decision_result(
            decision=decision,
            reason=reason,
            newer_count=newer_count,
            conflict_count=conflict_count,
            should_merge_context=should_merge_context
        )
        
        # Add additional metadata
        if conflict_types:
            result["conflict_types"] = conflict_types
        if golden_age_days is not None:
            result["golden_age_days"] = round(golden_age_days, 1)
        if kb_newest_age_days is not None:
            result["kb_newest_age_days"] = round(kb_newest_age_days, 1)
        
        return result
    
    def _create_decision_result(
        self, 
        decision: str, 
        reason: str, 
        newer_count: int, 
        conflict_count: int,
        should_merge_context: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Create standardized decision result."""
        
        if should_merge_context is None:
            should_merge_context = (decision == "newer_kb")
        
        return {
            "decision": decision,
            "reason": reason,
            "newer_count": newer_count,
            "conflict_count": conflict_count,
            "should_merge_context": should_merge_context
        }
    
    def _log_decision(
        self, 
        result: Dict[str, Any], 
        trace_id: Optional[str], 
        user_id: Optional[str], 
        session_id: Optional[str],
        stage: str
    ):
        """Log the decision with structured logging."""
        
        rag_step_log(
            step=self.STEP_NUM,
            step_id=self.STEP_ID,
            node_label=self.NODE_LABEL,
            trace_id=trace_id,
            user_id=user_id,
            session_id=session_id,
            decision=result["decision"],
            should_merge_context=result["should_merge_context"],
            newer_count=result["newer_count"],
            conflict_count=result["conflict_count"],
            reason=result["reason"],
            processing_stage=stage,
            golden_age_days=result.get("golden_age_days"),
            kb_newest_age_days=result.get("kb_newest_age_days"),
            conflict_types=result.get("conflict_types", [])
        )


# Convenience function for direct usage
def evaluate_kb_vs_golden(decision_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to evaluate KB vs Golden Set.
    
    Args:
        decision_data: Decision data dictionary
        
    Returns:
        Dict with decision result
    """
    service = KBDeltaDecision()
    return service.evaluate_kb_vs_golden(decision_data)