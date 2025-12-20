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

from app.schemas.proactivity import Action, InteractiveQuestion


class AttachmentInfo(BaseModel):
    """Attachment metadata for messages with uploaded files."""

    id: str = Field(..., description="Document ID")
    filename: str = Field(..., description="Original filename")
    type: str | None = Field(None, description="MIME type")


class Message(BaseModel):
    """Message model for chat endpoint.

    Attributes:
        role: The role of the message sender (user or assistant).
        content: The content of the message.
        attachments: Optional list of attachment metadata (for user messages with files).
    """

    model_config = {"extra": "ignore"}

    role: Literal["user", "assistant", "system"] = Field(..., description="The role of the message sender")
    content: str = Field(..., description="The content of the message", min_length=1, max_length=50000)
    attachments: list[AttachmentInfo] | None = Field(
        default=None, description="Attachment metadata for messages with uploaded files"
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


class ChatResponse(BaseModel):
    """Response model for chat endpoint.

    Attributes:
        messages: List of messages in the conversation.
        metadata: Optional response metadata for debugging and monitoring.
        suggested_actions: Optional list of suggested actions for the user.
        interactive_question: Optional interactive question for clarification.
        extracted_params: Optional extracted parameters from the query.
    """

    messages: list[Message] = Field(..., description="List of messages in the conversation")
    metadata: ResponseMetadata | None = Field(None, description="Response metadata for debugging and monitoring")

    # Proactivity fields (DEV-157) - Optional for backward compatibility
    suggested_actions: list[Action] | None = Field(
        None, description="Suggested actions for the user based on context"
    )
    interactive_question: InteractiveQuestion | None = Field(
        None, description="Interactive question for parameter clarification"
    )
    extracted_params: dict[str, Any] | None = Field(
        None, description="Parameters extracted from the user query for confirmation"
    )


class StreamResponse(BaseModel):
    """Response model for streaming chat endpoint.

    Attributes:
        content: The content of the current chunk.
        done: Whether the stream is complete.
    """

    content: str = Field(default="", description="The content of the current chunk")
    done: bool = Field(default=False, description="Whether the stream is complete")
