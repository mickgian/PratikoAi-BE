"""This file contains the chat schema for the application.

Security: Includes prompt injection detection in monitoring mode (V-003).
Proactivity: Extended with suggested_actions and interactive_question (DEV-157).
"""

import re
from typing import (
    Any,
    Dict,
    List,
    Literal,
    Optional,
)
from uuid import UUID

from pydantic import (
    BaseModel,
    Field,
    field_validator,
)

# DEV-245 Phase 5.15: Action and ActionContext removed per user feedback
from app.schemas.proactivity import InteractiveQuestion


class AttachmentInfo(BaseModel):
    """Attachment metadata for messages with uploaded files."""

    id: str = Field(..., description="Document ID")
    filename: str = Field(..., description="Original filename")
    type: str | None = Field(None, description="MIME type")


class StructuredSource(BaseModel):
    """Structured source citation for frontend rendering (DEV-242 Phase 12B).

    Parsed from INDICE DELLE FONTI table in LLM responses by VerdettResponseFormatter.
    Rendered by SourcesIndex component in frontend.
    """

    numero: int = Field(..., description="Source number in the citation index")
    data: str | None = Field(None, description="Publication date of the source")
    ente: str | None = Field(None, description="Issuing entity (e.g., Agenzia Entrate, INPS)")
    tipo: str | None = Field(None, description="Document type (e.g., Circolare, Risoluzione, Legge)")
    riferimento: str = Field(..., description="Full reference text")
    url: str | None = Field(None, description="URL link to the source document")


class ReasoningTrace(BaseModel):
    """Chain of Thought reasoning trace for assistant messages.

    DEV-241: Structured reasoning data extracted from LLM response.
    This is displayed in the frontend via the ReasoningTrace component.
    """

    tema_identificato: str | None = Field(None, description="Main topic identified from the query")
    fonti_utilizzate: list[str] | None = Field(None, description="Sources used for the response")
    elementi_chiave: list[str] | None = Field(None, description="Key elements extracted")
    conclusione: str | None = Field(None, description="Reasoning conclusion")


class Message(BaseModel):
    """Message model for chat endpoint.

    Attributes:
        role: The role of the message sender (user or assistant).
        content: The content of the message.
        attachments: Optional list of attachment metadata (for user messages with files).
        reasoning: Optional Chain of Thought reasoning trace (DEV-241).
    """

    model_config = {"extra": "ignore"}

    role: Literal["user", "assistant", "system"] = Field(..., description="The role of the message sender")
    content: str = Field(
        ..., description="The content of the message", min_length=1, max_length=80000
    )  # DEV-244: Kept at 80000 - KB context now hard-capped at 35000 chars in context_builder_merge.py
    attachments: list[AttachmentInfo] | None = Field(
        default=None, description="Attachment metadata for messages with uploaded files"
    )
    # DEV-241: Chain of Thought reasoning for assistant messages
    reasoning: ReasoningTrace | None = Field(
        default=None, description="Chain of Thought reasoning trace (for assistant messages)"
    )
    # DEV-242 Phase 12B: Structured sources for proper frontend rendering
    structured_sources: list[StructuredSource] | None = Field(
        default=None, description="Structured source citations parsed from LLM response"
    )
    # DEV-245 Phase 5.15: action_context removed (suggested actions feature removed)
    # DEV-244: Deterministic KB source URLs for Fonti section (persisted in query_history)
    kb_source_urls: list[dict] | None = Field(
        default=None, description="Source URLs from KB retrieval for Fonti display"
    )

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate the message content.

        Security: Detects prompt injection patterns (V-003) in monitoring mode.
        Patterns are logged but NOT blocked to avoid false positives on
        legitimate Italian legal/tax queries.

        Args:
            v: The content to validate

        Returns:
            str: The validated content (always returns, logs warnings only)

        Raises:
            ValueError: If the content contains disallowed patterns (XSS, null bytes)
        """
        # Check for potentially harmful content (XSS)
        if re.search(r"<script.*?>.*?</script>", v, re.IGNORECASE | re.DOTALL):
            raise ValueError("Content contains potentially harmful script tags")

        # Check for null bytes
        if "\0" in v:
            raise ValueError("Content contains null bytes")

        # Prompt injection detection (MONITORING MODE - log only, don't block)
        # This addresses V-003 from security audit
        # Import inside function to avoid circular import
        from app.utils.security import detect_prompt_injection, log_injection_attempt

        detected, pattern = detect_prompt_injection(v)
        if detected:
            # Log the attempt but allow the request to proceed
            # This prevents false positives from blocking legitimate users
            log_injection_attempt(
                text=v,
                pattern=pattern or "unknown",
                user_id=None,  # User context not available in schema validation
                request_id=None,
            )

        return v


class QueryClassificationMetadata(BaseModel):
    """Metadata about query classification for debugging and monitoring."""

    domain: str = Field(..., description="The classified professional domain")
    action: str = Field(..., description="The classified user action/intent")
    confidence: float = Field(..., description="Classification confidence score (0-1)")
    sub_domain: str | None = Field(None, description="Specific sub-domain if detected")
    document_type: str | None = Field(None, description="Document type for generation requests")
    fallback_used: bool = Field(False, description="Whether LLM fallback was used")
    domain_prompt_used: bool = Field(False, description="Whether domain-specific prompt was used")
    reasoning: str | None = Field(None, description="Classification reasoning")


class ResponseMetadata(BaseModel):
    """Response metadata for debugging and monitoring."""

    model_used: str = Field(..., description="LLM model that generated the response")
    provider: str = Field(..., description="LLM provider used")
    strategy: str = Field(..., description="Routing strategy applied")
    cost_eur: float | None = Field(None, description="Estimated cost in EUR")
    processing_time_ms: int | None = Field(None, description="Total processing time in milliseconds")
    classification: QueryClassificationMetadata | None = Field(None, description="Query classification metadata")


class ChatRequest(BaseModel):
    """Request model for chat endpoint.

    Attributes:
        messages: List of messages in the conversation.
        attachment_ids: Optional list of uploaded document IDs to include in context.
        skip_proactivity: If True, skip pre-response proactivity checks (used for
                         follow-up queries from answered clarifying questions).
    """

    messages: list[Message] = Field(
        ...,
        description="List of messages in the conversation",
        min_length=1,
    )
    attachment_ids: list[UUID] | None = Field(
        default=None,
        description="IDs of uploaded documents to include in context",
        max_length=5,
    )
    skip_proactivity: bool = Field(
        default=False,
        description="Skip pre-response proactivity for follow-up queries",
    )


class ChatResponse(BaseModel):
    """Response model for chat endpoint.

    Attributes:
        messages: List of messages in the conversation.
        metadata: Optional response metadata for debugging and monitoring.
        interactive_question: Optional interactive question for clarification.
        extracted_params: Optional extracted parameters from the query.
    """

    messages: list[Message] = Field(..., description="List of messages in the conversation")
    metadata: ResponseMetadata | None = Field(None, description="Response metadata for debugging and monitoring")

    # Proactivity fields (DEV-157) - Optional for backward compatibility
    # DEV-245 Phase 5.15: suggested_actions removed per user feedback
    interactive_question: InteractiveQuestion | None = Field(
        None, description="Interactive question for parameter clarification"
    )
    extracted_params: dict[str, Any] | None = Field(
        None, description="Parameters extracted from the user query for confirmation"
    )

    # DEV-255: Trace ID for user feedback attachment
    trace_id: str | None = Field(default=None, description="Langfuse trace ID for attaching user feedback scores")


class StreamResponse(BaseModel):
    """Response model for streaming chat endpoint.

    Supports different event types for proactivity (DEV-159, DEV-201, DEV-242):
    - content: Text content chunks (default)
    - content_cleaned: Final cleaned content with XML tags stripped (DEV-201)
    - interactive_question: Interactive question for clarification
    - reasoning: Chain of Thought reasoning trace (DEV-242)
    - structured_sources: Parsed source citations for frontend rendering (DEV-242 Phase 12B)
    - kb_source_urls: Deterministic KB source URLs (DEV-244)
    - web_verification: Web verification results from Brave Search (DEV-245)

    Attributes:
        content: The content of the current chunk.
        done: Whether the stream is complete.
        event_type: Type of SSE event.
        interactive_question: Question for parameter clarification.
        extracted_params: Parameters extracted from user query.
        reasoning: Chain of Thought reasoning trace (DEV-242).
        structured_sources: Structured source citations (DEV-242 Phase 12B).
    """

    content: str = Field(default="", description="The content of the current chunk")
    done: bool = Field(default=False, description="Whether the stream is complete")

    # Proactivity and reasoning fields (DEV-159, DEV-201, DEV-242, DEV-244) - Optional for backward compatibility
    # DEV-245 Phase 5.15: suggested_actions event type removed per user feedback
    event_type: (
        Literal[
            "content",
            "content_cleaned",
            "interactive_question",
            "reasoning",
            "structured_sources",
            "kb_source_urls",  # DEV-244: Deterministic KB source URLs
            "web_verification",  # DEV-245: Web verification results (Brave Search)
        ]
        | None
    ) = Field(default=None, description="Type of SSE event for proactivity or reasoning")
    interactive_question: dict[str, Any] | None = Field(
        default=None, description="Interactive question for parameter clarification"
    )
    extracted_params: dict[str, Any] | None = Field(default=None, description="Parameters extracted from user query")
    reasoning: dict[str, Any] | None = Field(default=None, description="Chain of Thought reasoning trace (DEV-242)")
    # DEV-242 Phase 12B: Structured sources for proper frontend rendering
    structured_sources: list[dict[str, Any]] | None = Field(
        default=None, description="Structured source citations parsed from LLM response"
    )
    # DEV-244: Deterministic KB source URLs (independent of LLM output)
    kb_source_urls: list[dict[str, Any]] | None = Field(
        default=None, description="Source URLs from KB retrieval (deterministic, always complete)"
    )
    # DEV-245: Web verification results from Brave Search
    web_verification: dict[str, Any] | None = Field(
        default=None, description="Web verification results including caveats and web sources"
    )

    # DEV-255: Trace ID for user feedback attachment
    trace_id: str | None = Field(default=None, description="Langfuse trace ID for attaching user feedback scores")
