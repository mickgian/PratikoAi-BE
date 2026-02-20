"""Pydantic schemas for Intent Labeling System API.

DEV-253: Expert labeling UI for intent classifier training.

This module defines all request/response schemas for:
- Labeling queue retrieval
- Label submission
- Labeling statistics
- Training data export
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.intent_labeling import IntentLabel


class LabelSubmission(BaseModel):
    """Request schema for submitting an expert label.

    Security: Field length limits enforced to prevent DoS attacks.
    """

    query_id: UUID = Field(..., description="UUID of the query to label")
    expert_intent: str = Field(
        ...,
        description="Expert-assigned intent label",
    )
    notes: str | None = Field(
        None,
        description="Optional notes explaining the label",
        max_length=500,
    )

    @field_validator("expert_intent")
    @classmethod
    def validate_expert_intent(cls, v: str) -> str:
        """Validate expert_intent is one of the allowed IntentLabel values."""
        allowed = [intent.value for intent in IntentLabel]
        if v not in allowed:
            raise ValueError(f"Intento non valido. Valori permessi: {allowed}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "query_id": "123e4567-e89b-12d3-a456-426614174000",
                "expert_intent": "calculator",
                "notes": "Richiesta di calcolo IVA, non ricerca tecnica",
            }
        }


class QueueItem(BaseModel):
    """Schema for a single item in the labeling queue."""

    id: UUID = Field(..., description="UUID of the labeled query record")
    query: str = Field(..., description="The user query text")
    predicted_intent: str = Field(..., description="HF classifier's prediction")
    confidence: float = Field(..., description="HF classifier's confidence (0.0-1.0)")
    all_scores: dict[str, Any] = Field(..., description="Full score distribution from HF classifier")
    expert_intent: str | None = Field(None, description="Expert label (null if not yet labeled)")
    skip_count: int = Field(0, description="Number of times this query was skipped")
    created_at: datetime = Field(..., description="When the query was captured")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "query": "Come si calcola l'imposta sostitutiva?",
                "predicted_intent": "technical_research",
                "confidence": 0.45,
                "all_scores": {
                    "technical_research": 0.45,
                    "theoretical_definition": 0.30,
                    "calculator": 0.15,
                    "chitchat": 0.05,
                    "normative_reference": 0.05,
                },
                "expert_intent": None,
                "skip_count": 0,
                "created_at": "2026-02-03T10:30:00",
            }
        }


class QueueResponse(BaseModel):
    """Response schema for labeling queue."""

    total_count: int = Field(..., description="Total number of unlabeled queries")
    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Number of items per page")
    items: list[QueueItem] = Field(..., description="List of queries to label")

    class Config:
        json_schema_extra = {
            "example": {
                "total_count": 150,
                "page": 1,
                "page_size": 50,
                "items": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "query": "Come si calcola l'imposta sostitutiva?",
                        "predicted_intent": "technical_research",
                        "confidence": 0.35,
                        "all_scores": {"technical_research": 0.35},
                        "expert_intent": None,
                        "skip_count": 0,
                        "created_at": "2026-02-03T10:30:00",
                    }
                ],
            }
        }


class LabelingStatsResponse(BaseModel):
    """Response schema for labeling statistics."""

    total_queries: int = Field(..., description="Total queries in labeling system")
    labeled_queries: int = Field(..., description="Number of labeled queries")
    pending_queries: int = Field(..., description="Number of queries awaiting labels")
    completion_percentage: float = Field(..., description="Percentage of queries labeled (0.0-100.0)")
    labels_by_intent: dict[str, int] = Field(default_factory=dict, description="Count of labels per intent category")
    new_since_export: int = Field(..., description="Labeled queries not yet exported")

    class Config:
        json_schema_extra = {
            "example": {
                "total_queries": 500,
                "labeled_queries": 125,
                "pending_queries": 375,
                "completion_percentage": 25.0,
                "labels_by_intent": {
                    "chitchat": 30,
                    "technical_research": 45,
                    "calculator": 25,
                    "theoretical_definition": 15,
                    "normative_reference": 10,
                },
                "new_since_export": 50,
            }
        }


class LabeledQueryResponse(BaseModel):
    """Response schema for a labeled query after submission."""

    id: UUID = Field(..., description="UUID of the labeled query record")
    query: str = Field(..., description="The user query text")
    predicted_intent: str = Field(..., description="HF classifier's prediction")
    expert_intent: str = Field(..., description="Expert-assigned intent")
    labeled_by: int = Field(..., description="User ID of the expert who labeled")
    labeled_at: datetime = Field(..., description="When the label was submitted")
    labeling_notes: str | None = Field(None, description="Optional notes from expert")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "query": "Come si calcola l'imposta sostitutiva?",
                "predicted_intent": "technical_research",
                "expert_intent": "calculator",
                "labeled_by": 1,
                "labeled_at": "2026-02-03T11:45:00",
                "labeling_notes": "Richiesta di calcolo, non ricerca",
            }
        }


class SkipResponse(BaseModel):
    """Response schema for skipping a query."""

    id: UUID = Field(..., description="UUID of the skipped query")
    skip_count: int = Field(..., description="Updated skip count")
    message: str = Field(..., description="Success message")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "skip_count": 2,
                "message": "Query saltata con successo",
            }
        }


class ExportResponse(BaseModel):
    """Response metadata for training data export."""

    total_exported: int = Field(..., description="Number of records exported")
    format: str = Field(..., description="Export format (jsonl or csv)")
    message: str = Field(..., description="Success message")

    class Config:
        json_schema_extra = {
            "example": {
                "total_exported": 125,
                "format": "jsonl",
                "message": "Dati esportati con successo",
            }
        }
