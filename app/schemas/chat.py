"""This file contains the chat schema for the application."""

import re
from typing import (
    Dict,
    List,
    Literal,
    Optional,
    Any,
)

from pydantic import (
    BaseModel,
    Field,
    field_validator,
)


class Message(BaseModel):
    """Message model for chat endpoint.

    Attributes:
        role: The role of the message sender (user or assistant).
        content: The content of the message.
    """

    model_config = {"extra": "ignore"}

    role: Literal["user", "assistant", "system"] = Field(..., description="The role of the message sender")
    content: str = Field(..., description="The content of the message", min_length=1, max_length=3000)

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate the message content.

        Args:
            v: The content to validate

        Returns:
            str: The validated content

        Raises:
            ValueError: If the content contains disallowed patterns
        """
        # Check for potentially harmful content
        if re.search(r"<script.*?>.*?</script>", v, re.IGNORECASE | re.DOTALL):
            raise ValueError("Content contains potentially harmful script tags")

        # Check for null bytes
        if "\0" in v:
            raise ValueError("Content contains null bytes")

        return v


class QueryClassificationMetadata(BaseModel):
    """Metadata about query classification for debugging and monitoring."""
    
    domain: str = Field(..., description="The classified professional domain")
    action: str = Field(..., description="The classified user action/intent")
    confidence: float = Field(..., description="Classification confidence score (0-1)")
    sub_domain: Optional[str] = Field(None, description="Specific sub-domain if detected")
    document_type: Optional[str] = Field(None, description="Document type for generation requests")
    fallback_used: bool = Field(False, description="Whether LLM fallback was used")
    domain_prompt_used: bool = Field(False, description="Whether domain-specific prompt was used")
    reasoning: Optional[str] = Field(None, description="Classification reasoning")


class ResponseMetadata(BaseModel):
    """Response metadata for debugging and monitoring."""
    
    model_used: str = Field(..., description="LLM model that generated the response")
    provider: str = Field(..., description="LLM provider used")
    strategy: str = Field(..., description="Routing strategy applied")
    cost_eur: Optional[float] = Field(None, description="Estimated cost in EUR")
    processing_time_ms: Optional[int] = Field(None, description="Total processing time in milliseconds")
    classification: Optional[QueryClassificationMetadata] = Field(None, description="Query classification metadata")


class ChatRequest(BaseModel):
    """Request model for chat endpoint.

    Attributes:
        messages: List of messages in the conversation.
    """

    messages: List[Message] = Field(
        ...,
        description="List of messages in the conversation",
        min_length=1,
    )


class ChatResponse(BaseModel):
    """Response model for chat endpoint.

    Attributes:
        messages: List of messages in the conversation.
        metadata: Optional response metadata for debugging and monitoring.
    """

    messages: List[Message] = Field(..., description="List of messages in the conversation")
    metadata: Optional[ResponseMetadata] = Field(None, description="Response metadata for debugging and monitoring")


class StreamResponse(BaseModel):
    """Response model for streaming chat endpoint.

    Attributes:
        content: The content of the current chunk.
        done: Whether the stream is complete.
    """

    content: str = Field(default="", description="The content of the current chunk")
    done: bool = Field(default=False, description="Whether the stream is complete")
