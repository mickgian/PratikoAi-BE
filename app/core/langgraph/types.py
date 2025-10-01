"""Enhanced types for LangGraph RAG implementation."""

from typing import Any, Dict, List, Optional
from app.schemas.graph import GraphState

# Type alias for RAG State - extends GraphState with additional fields
RAGState = GraphState

# Additional state fields that may be used by nodes
class RAGStateFields:
    """Additional state fields used by RAG nodes."""

    # Validation and authentication results
    request_valid: Optional[bool] = None
    user_authenticated: Optional[bool] = None

    # Privacy processing
    privacy_enabled: Optional[bool] = None
    pii_detected: Optional[bool] = None
    anonymized_messages: Optional[List[Any]] = None

    # Cache results
    cache_key: Optional[str] = None
    cache_hit: Optional[bool] = None
    cached_response: Optional[Any] = None

    # LLM processing
    llm_response: Optional[Any] = None
    llm_success: Optional[bool] = None

    # Error handling
    error_message: Optional[str] = None
    error_code: Optional[int] = None

    # Processing metadata
    processing_stage: str = "start"
    node_history: List[str] = []

# For backwards compatibility, re-export GraphState
__all__ = ["RAGState", "RAGStateFields", "GraphState"]