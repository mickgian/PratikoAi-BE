"""
Golden Fast-Path Service - RAG STEP 20 Implementation.

Implements RAG STEP 20 — GoldenFastGate

This service implements the decision logic for determining whether a query
is eligible for the golden fast-path, bypassing document processing and
going directly to golden answer lookup.

Based on Mermaid diagram: GoldenFastGate (Golden fast-path eligible? no doc or quick check safe)
"""

import re
import time
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional, Any

import app.observability.rag_logging as rag_logging

STEP_NUM = 20
STEP_ID = "RAG.golden.golden.fast.path.eligible.no.doc.or.quick.check.safe"
NODE_LABEL = "GoldenFastGate"


class EligibilityDecision(str, Enum):
    """Decision outcomes for golden fast-path eligibility."""
    ELIGIBLE = "ELIGIBLE"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"


@dataclass
class EligibilityResult:
    """Result of golden fast-path eligibility check."""
    decision: EligibilityDecision
    confidence: float
    reasons: List[str]
    next_step: str
    allows_golden_lookup: bool
    safety_checks: Optional[Dict[str, Any]] = None
    latency_ms: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for structured logging."""
        return asdict(self)


class GoldenFastPathService:
    """Service for determining golden fast-path eligibility."""
    
    def __init__(self):
        """Initialize the golden fast-path service."""
        # Keywords that indicate document-dependent queries
        self.document_keywords = {
            "analizza", "verifica", "esamina", "controlla", "valuta", "studia",
            "documento", "contratto", "allegato", "file", "pdf", "fattura",
            "conformità", "validazione", "approvazione", "certificazione"
        }
        
        # Keywords that indicate safe, quick factual queries
        self.safe_keywords = {
            "cos'è", "cosa è", "quale", "quali", "quanto", "quando", "dove",
            "come", "perché", "aliquota", "aliquote", "scadenza", "scadenze",
            "calcola", "calcolo", "importo", "importi", "data", "date"
        }
        
        # Keywords that indicate complex analysis requirements
        self.complex_keywords = {
            "ottimizza", "strategia", "pianifica", "analisi completa",
            "tutti gli aspetti", "considerando", "implicazioni", "impatti",
            "conseguenze", "effetti", "scenario", "scenari"
        }
    
    async def is_eligible_for_fast_path(self, query_data: Dict[str, Any]) -> EligibilityResult:
        """
        Determine if a query is eligible for the golden fast-path.
        
        Args:
            query_data: Dictionary containing:
                - query: The user's query text
                - attachments: List of attachments (empty list if none)
                - user_id: User identifier
                - session_id: Session identifier 
                - canonical_facts: List of extracted canonical facts (optional)
                - query_signature: Query signature hash (optional)
                - trace_id: Trace identifier for logging
        
        Returns:
            EligibilityResult with decision and reasoning
        """
        start_time = time.perf_counter()
        
        try:
            query = query_data.get("query", "").lower()
            attachments = query_data.get("attachments", [])
            trace_id = query_data.get("trace_id")
            
            reasons = []
            confidence = 0.0
            
            # Rule 1: Check for attachments (highest priority)
            if attachments:
                decision = EligibilityDecision.NOT_ELIGIBLE
                confidence = 0.95
                reasons.append("has_attachments")
                next_step = "QuickPreIngest"
                allows_golden = False
            else:
                reasons.append("no_attachments")
                confidence += 0.3
                
                # Rule 2: Check for document-dependent language
                if self._contains_document_keywords(query):
                    decision = EligibilityDecision.NOT_ELIGIBLE
                    confidence = max(confidence, 0.85)
                    reasons.append("document_dependent")
                    next_step = "ClassifyDomain"
                    allows_golden = False
                
                # Rule 3: Check for complex analysis requirements
                elif self._contains_complex_keywords(query):
                    decision = EligibilityDecision.NOT_ELIGIBLE
                    confidence = max(confidence, 0.80)
                    reasons.append("complex_analysis")
                    next_step = "ClassifyDomain"
                    allows_golden = False
                
                # Rule 4: Check for safe, quick queries
                elif self._is_safe_quick_query(query):
                    decision = EligibilityDecision.ELIGIBLE
                    confidence += 0.4
                    reasons.extend(["quick_check_safe", "factual_knowledge"])
                    next_step = "GoldenLookup"
                    allows_golden = True
                
                # Rule 5: Check for simple FAQ-type queries
                elif self._is_simple_faq_query(query):
                    decision = EligibilityDecision.ELIGIBLE
                    confidence += 0.35
                    reasons.extend(["simple_faq", "factual_knowledge"])
                    next_step = "GoldenLookup"
                    allows_golden = True
                
                # Default: Not eligible for complex or unclear queries
                else:
                    decision = EligibilityDecision.NOT_ELIGIBLE
                    confidence = max(confidence, 0.75)
                    reasons.append("requires_detailed_processing")
                    next_step = "ClassifyDomain"
                    allows_golden = False
            
            # Perform additional safety checks
            safety_checks = self._perform_safety_checks(query_data)
            if not safety_checks.get("is_safe", True):
                decision = EligibilityDecision.NOT_ELIGIBLE
                confidence = max(confidence, 0.90)
                reasons.append("safety_check_failed")
                next_step = "ClassifyDomain"
                allows_golden = False
            
            # Apply confidence floors based on decision and reasons
            if decision == EligibilityDecision.ELIGIBLE:
                if "no_attachments" in reasons:
                    confidence = max(confidence, 0.81)
                if "quick_check_safe" in reasons:
                    confidence = max(confidence, 0.71)
            elif decision == EligibilityDecision.NOT_ELIGIBLE and "has_attachments" in reasons:
                confidence = max(confidence, 0.92)
            
            # Ensure confidence is in valid range
            confidence = min(max(confidence, 0.0), 1.0)
            
            # Calculate latency
            end_time = time.perf_counter()
            latency_ms = round((end_time - start_time) * 1000.0, 2)
            
            result = EligibilityResult(
                decision=decision,
                confidence=confidence,
                reasons=reasons,
                next_step=next_step,
                allows_golden_lookup=allows_golden,
                safety_checks=safety_checks,
                latency_ms=latency_ms
            )
            
            # Log the decision using structured RAG logging with exact signature
            rag_logging.rag_step_log(
                step=STEP_NUM,
                step_id=STEP_ID,
                node_label=NODE_LABEL,
                decision=result.decision if isinstance(result.decision, str) else result.decision.value,
                confidence=result.confidence,
                reasons=result.reasons,
                trace_id=query_data.get("trace_id"),
            )
            
            return result
            
        except Exception as exc:
            # Log error and return safe default
            end_time = time.perf_counter()
            latency_ms = round((end_time - start_time) * 1000.0, 2)
            
            # Create error result
            error_result = EligibilityResult(
                decision=EligibilityDecision.NOT_ELIGIBLE,
                confidence=0.0,
                reasons=["error_occurred"],
                next_step="ClassifyDomain",
                allows_golden_lookup=False,
                latency_ms=latency_ms
            )
            
            # Log with exact signature (error info can be added separately if needed)
            rag_logging.rag_step_log(
                step=STEP_NUM,
                step_id=STEP_ID,
                node_label=NODE_LABEL,
                decision=error_result.decision if isinstance(error_result.decision, str) else error_result.decision.value,
                confidence=error_result.confidence,
                reasons=error_result.reasons,
                trace_id=query_data.get("trace_id"),
            )
            
            # Return safe default (not eligible)
            return error_result
    
    def _contains_document_keywords(self, query: str) -> bool:
        """Check if query contains document-dependent keywords."""
        query_words = set(re.findall(r'\b\w+\b', query.lower()))
        return bool(query_words & self.document_keywords)
    
    def _contains_complex_keywords(self, query: str) -> bool:
        """Check if query contains complex analysis keywords."""
        query_lower = query.lower()
        # Check for exact phrases first
        complex_phrases = [
            "tutti gli aspetti", "analisi completa", "considerando",
            "implicazioni", "effetti", "conseguenze"
        ]
        if any(phrase in query_lower for phrase in complex_phrases):
            return True
        
        # Check for individual complex keywords
        query_words = set(re.findall(r'\b\w+\b', query_lower))
        return bool(query_words & self.complex_keywords)
    
    def _is_safe_quick_query(self, query: str) -> bool:
        """Check if query is a safe, quick factual query."""
        query_lower = query.lower()
        
        # Check for question words that indicate factual queries
        if any(word in query_lower for word in self.safe_keywords):
            return True
        
        # Check for simple calculation patterns
        if re.search(r'\bcalcol[aoi]\b.*\d+', query_lower):
            return True
        
        # Check for simple "what is" or "how much" patterns
        if re.search(r'\b(cos\'è|cosa è|quanto costa|come si)\b', query_lower):
            return True
        
        return False
    
    def _is_simple_faq_query(self, query: str) -> bool:
        """Check if query is a simple FAQ-type query."""
        query_lower = query.lower()
        
        # Simple factual questions about IVA, taxes, deadlines
        simple_patterns = [
            r'\b(aliquot[aei]|scadenz[aei]|dat[aei])\b',
            r'\b(iva|irpef|ires|irap)\b.*\b(cos\'è|cosa è|quanto)\b',
            r'\b(come|quando|dove)\b.*\b(pagare|presentare|dichiarare)\b'
        ]
        
        return any(re.search(pattern, query_lower) for pattern in simple_patterns)
    
    def _perform_safety_checks(self, query_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform additional safety checks on the query."""
        query = query_data.get("query", "").lower()
        
        # Check query length (very long queries may need special handling)
        query_length = len(query)
        if query_length > 500:
            return {
                "is_safe": False,
                "risk_level": "high",
                "reason": "query_too_long",
                "requires_doc_context": True
            }
        
        # Check for personal/sensitive data patterns
        sensitive_patterns = [
            r'\b\d{11}\b',  # Italian fiscal codes
            r'\b\d{16}\b',  # Credit card patterns
            r'\bemail\b.*@',  # Email references
        ]
        
        if any(re.search(pattern, query) for pattern in sensitive_patterns):
            return {
                "is_safe": False,
                "risk_level": "medium", 
                "reason": "potential_sensitive_data",
                "requires_doc_context": False
            }
        
        # Default: safe
        return {
            "is_safe": True,
            "risk_level": "low",
            "requires_doc_context": False
        }

    def can_serve_from_golden(
        self,
        confidence: float,
        kb_epoch: int,
        golden_epoch: int,
        confidence_threshold: float = 0.90
    ) -> bool:
        """Check if a Golden answer can be served based on confidence and epoch.

        This implements the policy: serve Golden only if:
        1. Confidence >= threshold (default 0.90)
        2. kb_epoch <= golden_epoch (KB hasn't been updated since Golden was created)

        Args:
            confidence: Confidence score of the Golden match
            kb_epoch: Current knowledge base epoch
            golden_epoch: Epoch when Golden answer was created
            confidence_threshold: Minimum confidence required (default 0.90)

        Returns:
            True if Golden can be served, False otherwise

        Examples:
            >>> service = GoldenFastPathService()
            >>> service.can_serve_from_golden(0.95, 100, 100)
            True
            >>> service.can_serve_from_golden(0.95, 101, 100)
            False
            >>> service.can_serve_from_golden(0.85, 100, 100)
            False
        """
        # Check confidence threshold
        if confidence < confidence_threshold:
            return False

        # Check epoch rule: KB must not be newer than Golden
        if kb_epoch > golden_epoch:
            return False

        return True


# Convenience function for direct usage
async def check_golden_fast_path_eligibility(query_data: Dict[str, Any]) -> EligibilityResult:
    """
    Convenience function to check golden fast-path eligibility.
    
    Args:
        query_data: Query data dictionary
        
    Returns:
        EligibilityResult with decision and reasoning
    """
    service = GoldenFastPathService()
    return await service.is_eligible_for_fast_path(query_data)