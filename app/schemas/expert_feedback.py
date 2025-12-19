"""Pydantic schemas for Expert Feedback System API.

This module defines all request/response schemas for:
- Expert feedback submission
- Feedback history retrieval
- Expert profile management
- Task generation tracking
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class FeedbackSubmission(BaseModel):
    """Request schema for submitting expert feedback.

    Security: Field length limits enforced to prevent DoS attacks (V-002).
    """

    query_id: UUID = Field(..., description="UUID of the query being reviewed")
    feedback_type: str = Field(..., description="Type of feedback: 'correct', 'incomplete', or 'incorrect'")
    category: str | None = Field(None, description="Italian category for detailed feedback")
    query_text: str = Field(
        ...,
        description="Original question text",
        min_length=1,
        max_length=2000,  # V-002: Enforce max length
    )
    original_answer: str = Field(
        ...,
        description="AI-generated answer being reviewed",
        min_length=1,
        max_length=5000,  # V-002: Enforce max length
    )
    expert_answer: str | None = Field(
        None,
        description="Expert's corrected answer",
        max_length=5000,  # V-002: Enforce max length
    )
    improvement_suggestions: list[str] | None = Field(
        default=None,
        description="List of improvement suggestions (max 500 chars each)",
    )
    regulatory_references: list[str] | None = Field(
        default=None,
        description="List of regulatory references (max 500 chars each)",
    )
    confidence_score: float = Field(..., description="Expert confidence (0.0-1.0)", ge=0.0, le=1.0)
    time_spent_seconds: int = Field(..., description="Time spent reviewing (seconds)", gt=0)
    complexity_rating: int | None = Field(None, description="Complexity rating (1-5)", ge=1, le=5)
    additional_details: str | None = Field(
        None,
        description="Additional details for task generation (required for incomplete/incorrect feedback)",
        max_length=2000,  # V-002: Enforce max length
    )

    @field_validator("feedback_type")
    @classmethod
    def validate_feedback_type(cls, v: str) -> str:
        """Validate feedback type is one of the allowed values."""
        allowed = ["correct", "incomplete", "incorrect"]
        if v not in allowed:
            raise ValueError(f"feedback_type must be one of {allowed}")
        return v

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str | None) -> str | None:
        """Validate category is one of the allowed Italian categories."""
        if v is None:
            return v
        allowed = [
            "normativa_obsoleta",
            "interpretazione_errata",
            "caso_mancante",
            "calcolo_sbagliato",
            "troppo_generico",
        ]
        if v not in allowed:
            raise ValueError(f"category must be one of {allowed}")
        return v

    @field_validator("query_text")
    @classmethod
    def validate_query_text_not_placeholder(cls, v: str) -> str:
        """Reject placeholder strings to ensure real query text is provided.

        Placeholders indicate that frontend failed to extract the actual user query
        from chat history. This is a critical bug that must be caught and rejected.

        Args:
            v: The query_text value to validate

        Returns:
            The validated query_text (unchanged if valid)

        Raises:
            ValueError: If query_text is a known placeholder pattern
        """
        # List of known placeholder patterns (case-insensitive)
        placeholders = [
            "[Domanda precedente dell'utente]",  # Italian placeholder
            "[User query]",  # English placeholder
            "[TODO]",  # Developer TODO marker
            "[Query text]",  # Generic placeholder
            "TODO: Extract from chat history",  # Comment as placeholder
        ]

        # Check if value matches any placeholder (case-insensitive)
        normalized_value = v.strip()
        for placeholder in placeholders:
            if normalized_value.lower() == placeholder.lower():
                raise ValueError(
                    f"query_text cannot be a placeholder: '{placeholder}'. "
                    "Frontend must extract actual user query from chat history."
                )

        # Check for empty/whitespace-only strings (additional safety check)
        if not normalized_value:
            raise ValueError("query_text cannot be empty or whitespace-only.")

        return v

    @field_validator("improvement_suggestions")
    @classmethod
    def validate_improvement_suggestions(cls, v: list[str] | None) -> list[str] | None:
        """Validate each improvement suggestion does not exceed max length.

        Security: Prevents V-002 by enforcing per-item length limits.

        Args:
            v: List of improvement suggestions to validate

        Returns:
            The validated list (unchanged if valid)

        Raises:
            ValueError: If any suggestion exceeds 500 characters
        """
        if v is None:
            return v

        max_length = 500
        for i, suggestion in enumerate(v):
            if len(suggestion) > max_length:
                raise ValueError(f"Suggerimento {i + 1} troppo lungo: massimo {max_length} caratteri")
        return v

    @field_validator("regulatory_references")
    @classmethod
    def validate_regulatory_references(cls, v: list[str] | None) -> list[str] | None:
        """Validate each regulatory reference does not exceed max length.

        Security: Prevents V-002 by enforcing per-item length limits.

        Args:
            v: List of regulatory references to validate

        Returns:
            The validated list (unchanged if valid)

        Raises:
            ValueError: If any reference exceeds 500 characters
        """
        if v is None:
            return v

        max_length = 500
        for i, ref in enumerate(v):
            if len(ref) > max_length:
                raise ValueError(f"Riferimento normativo {i + 1} troppo lungo: massimo {max_length} caratteri")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "query_id": "123e4567-e89b-12d3-a456-426614174000",
                "feedback_type": "incomplete",
                "category": "calcolo_sbagliato",
                "query_text": "Come si calcola l'IVA per il regime forfettario?",
                "original_answer": "Nel regime forfettario non si applica l'IVA.",
                "expert_answer": "Nel regime forfettario non si applica l'IVA in fattura. Tuttavia, "
                "per alcune categorie specifiche...",
                "improvement_suggestions": ["Aggiungere casi specifici", "Citare normativa aggiornata"],
                "regulatory_references": ["Art. 1, comma 54-89, L. 190/2014"],
                "confidence_score": 0.9,
                "time_spent_seconds": 180,
                "complexity_rating": 3,
                "additional_details": "La risposta è incompleta perché non tratta i casi di cessione "
                "di beni UE che richiedono adempimenti IVA specifici anche per i forfettari.",
            }
        }


class FeedbackResult(BaseModel):
    """Response schema for feedback submission."""

    feedback_id: UUID = Field(..., description="UUID of the created feedback record")
    feedback_type: str = Field(..., description="Type of feedback submitted")
    expert_trust_score: float = Field(..., description="Current trust score of the expert")
    task_creation_attempted: bool = Field(
        ..., description="Whether automatic task creation was attempted (for incomplete/incorrect feedback)"
    )
    generated_task_id: str | None = Field(None, description="ID of generated task (e.g., DEV-BE-123)")
    generated_faq_id: str | None = Field(
        None, description="ID of FAQ entry created in Golden Set (for correct feedback)"
    )
    message: str = Field(..., description="Success message")

    class Config:
        json_schema_extra = {
            "example": {
                "feedback_id": "123e4567-e89b-12d3-a456-426614174000",
                "feedback_type": "correct",
                "expert_trust_score": 0.85,
                "task_creation_attempted": False,
                "generated_task_id": None,
                "generated_faq_id": "faq_123e4567-e89b-12d3-a456-426614174000",
                "message": "Feedback submitted successfully",
            }
        }


class FeedbackRecord(BaseModel):
    """Schema for a single feedback record in history."""

    id: UUID
    query_id: UUID
    feedback_type: str
    category: str | None
    query_text: str
    original_answer: str
    expert_answer: str | None
    confidence_score: float
    time_spent_seconds: int
    complexity_rating: int | None
    feedback_timestamp: datetime
    generated_task_id: str | None
    generated_faq_id: str | None
    task_creation_success: bool | None

    class Config:
        from_attributes = True


class FeedbackHistoryResponse(BaseModel):
    """Response schema for feedback history."""

    total_count: int = Field(..., description="Total number of feedback records")
    limit: int = Field(..., description="Page size limit")
    offset: int = Field(..., description="Current offset")
    items: list[FeedbackRecord] = Field(..., description="List of feedback records")

    class Config:
        json_schema_extra = {
            "example": {
                "total_count": 42,
                "limit": 20,
                "offset": 0,
                "items": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "query_id": "987e6543-e21b-43d2-b654-426614174111",
                        "feedback_type": "incomplete",
                        "category": "calcolo_sbagliato",
                        "query_text": "Come si calcola l'IVA?",
                        "original_answer": "Si applica il 22%",
                        "expert_answer": "Si applica il 22% sulla base imponibile...",
                        "confidence_score": 0.9,
                        "time_spent_seconds": 180,
                        "complexity_rating": 3,
                        "feedback_timestamp": "2025-11-21T10:30:00",
                        "generated_task_id": "DEV-BE-123",
                        "task_creation_success": True,
                    }
                ],
            }
        }


class FeedbackDetailResponse(BaseModel):
    """Detailed response schema for a single feedback record."""

    id: UUID
    query_id: UUID
    feedback_type: str
    category: str | None
    query_text: str
    original_answer: str
    expert_answer: str | None
    improvement_suggestions: list[str]
    regulatory_references: list[str]
    confidence_score: float
    time_spent_seconds: int
    complexity_rating: int | None
    additional_details: str | None
    feedback_timestamp: datetime
    generated_task_id: str | None
    generated_faq_id: str | None
    task_creation_attempted: bool
    task_creation_success: bool | None
    task_creation_error: str | None
    action_taken: str | None
    improvement_applied: bool

    class Config:
        from_attributes = True


class ExpertProfileResponse(BaseModel):
    """Response schema for expert profile."""

    id: UUID
    user_id: int  # User model uses integer IDs, not UUIDs
    role: str = Field(..., description="User role: 'user', 'super_user', or 'admin'")
    credentials: list[str]
    credential_types: list[str]
    experience_years: int
    specializations: list[str]
    feedback_count: int
    feedback_accuracy_rate: float
    average_response_time_seconds: int
    trust_score: float
    professional_registration_number: str | None
    organization: str | None
    location_city: str | None
    is_verified: bool
    verification_date: datetime | None
    is_active: bool

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "987e6543-e21b-43d2-b654-426614174111",
                "role": "super_user",
                "credentials": ["Dottore Commercialista", "Revisore Legale"],
                "credential_types": ["dottore_commercialista", "revisore_legale"],
                "experience_years": 15,
                "specializations": ["diritto_tributario", "lavoro"],
                "feedback_count": 142,
                "feedback_accuracy_rate": 0.95,
                "average_response_time_seconds": 210,
                "trust_score": 0.92,
                "professional_registration_number": "AA123456",
                "organization": "Studio Rossi & Associati",
                "location_city": "Milano",
                "is_verified": True,
                "verification_date": "2024-01-15T09:00:00",
                "is_active": True,
            }
        }
