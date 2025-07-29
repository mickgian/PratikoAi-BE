"""Privacy-related schemas and data models.

This module defines Pydantic models for privacy and GDPR compliance features.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum

from app.core.privacy.anonymizer import PIIType
from app.core.privacy.gdpr import ConsentType, ProcessingPurpose, DataCategory


class PIIDetectionRequest(BaseModel):
    """Request for PII detection."""
    text: str = Field(..., description="Text to analyze for PII")
    detect_names: bool = Field(default=True, description="Whether to detect person names")
    confidence_threshold: float = Field(default=0.7, description="Minimum confidence for PII detection")


class PIIMatchResponse(BaseModel):
    """Response for detected PII match."""
    pii_type: str = Field(..., description="Type of PII detected")
    original_value: str = Field(..., description="Original PII value")
    anonymized_value: str = Field(..., description="Anonymized replacement")
    start_pos: int = Field(..., description="Start position in text")
    end_pos: int = Field(..., description="End position in text")
    confidence: float = Field(..., description="Confidence score (0-1)")


class AnonymizationResponse(BaseModel):
    """Response for text anonymization."""
    anonymized_text: str = Field(..., description="Anonymized text")
    pii_matches: List[PIIMatchResponse] = Field(default_factory=list, description="Detected PII matches")
    anonymization_map: Dict[str, str] = Field(default_factory=dict, description="Mapping of original to anonymized values")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Processing timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ConsentRequest(BaseModel):
    """Request to grant or withdraw consent."""
    user_id: str = Field(..., description="User identifier")
    consent_type: str = Field(..., description="Type of consent")
    granted: bool = Field(..., description="Whether consent is granted")
    ip_address: Optional[str] = Field(None, description="User's IP address")
    user_agent: Optional[str] = Field(None, description="User's browser agent")
    expiry_days: Optional[int] = Field(None, description="Days until consent expires")


class ConsentResponse(BaseModel):
    """Response for consent operation."""
    consent_id: str = Field(..., description="Unique consent identifier")
    user_id: str = Field(..., description="User identifier")
    consent_type: str = Field(..., description="Type of consent")
    granted: bool = Field(..., description="Whether consent is granted")
    timestamp: datetime = Field(..., description="When consent was granted/withdrawn")
    expiry_date: Optional[datetime] = Field(None, description="When consent expires")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ConsentStatusRequest(BaseModel):
    """Request to check consent status."""
    user_id: str = Field(..., description="User identifier")
    consent_types: Optional[List[str]] = Field(None, description="Specific consent types to check")


class ConsentStatusResponse(BaseModel):
    """Response for consent status check."""
    user_id: str = Field(..., description="User identifier")
    consents: Dict[str, bool] = Field(..., description="Consent status by type")
    last_updated: Optional[datetime] = Field(None, description="Last consent update")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DataProcessingRequest(BaseModel):
    """Request to record data processing."""
    user_id: str = Field(..., description="User identifier")
    data_category: str = Field(..., description="Category of data being processed")
    processing_purpose: str = Field(..., description="Purpose of processing")
    data_source: str = Field(..., description="Source of the data")
    legal_basis: str = Field(..., description="Legal basis for processing")
    anonymized: bool = Field(default=False, description="Whether data is anonymized")


class DataProcessingResponse(BaseModel):
    """Response for data processing record."""
    processing_id: str = Field(..., description="Unique processing identifier")
    user_id: str = Field(..., description="User identifier")
    data_category: str = Field(..., description="Category of data processed")
    processing_purpose: str = Field(..., description="Purpose of processing")
    timestamp: datetime = Field(..., description="When processing occurred")
    legal_basis: str = Field(..., description="Legal basis for processing")
    retention_period_days: Optional[int] = Field(None, description="Data retention period in days")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DataSubjectRequest(BaseModel):
    """Data subject request under GDPR."""
    user_id: str = Field(..., description="User identifier")
    request_type: str = Field(..., description="Type of request (access, deletion, portability)")
    additional_info: Optional[Dict[str, Any]] = Field(None, description="Additional request information")


class DataSubjectResponse(BaseModel):
    """Response to data subject request."""
    request_id: str = Field(..., description="Unique request identifier")
    user_id: str = Field(..., description="User identifier")
    request_type: str = Field(..., description="Type of request")
    status: str = Field(..., description="Request status")
    data: Optional[Dict[str, Any]] = Field(None, description="Requested data (for access requests)")
    message: Optional[str] = Field(None, description="Additional information")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Request processing timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AuditEventResponse(BaseModel):
    """Audit event information."""
    event_id: str = Field(..., description="Unique event identifier")
    event_type: str = Field(..., description="Type of audit event")
    user_id: Optional[str] = Field(None, description="User identifier")
    timestamp: datetime = Field(..., description="Event timestamp")
    details: Dict[str, Any] = Field(..., description="Event details")
    ip_address: Optional[str] = Field(None, description="IP address")
    session_id: Optional[str] = Field(None, description="Session identifier")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ComplianceStatusResponse(BaseModel):
    """Overall GDPR compliance status."""
    consent_records_count: int = Field(..., description="Total consent records")
    processing_records_count: int = Field(..., description="Total processing records")
    audit_events_count: int = Field(..., description="Total audit events")
    retention_policies: Dict[str, str] = Field(..., description="Data retention policies")
    compliance_features: List[str] = Field(..., description="Available compliance features")
    last_cleanup: Optional[datetime] = Field(None, description="Last automated cleanup")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PrivacySettingsRequest(BaseModel):
    """Request to update privacy settings."""
    user_id: str = Field(..., description="User identifier")
    anonymize_logs: bool = Field(default=True, description="Anonymize user data in logs")
    data_retention_days: Optional[int] = Field(None, description="Custom data retention period")
    consent_preferences: Dict[str, bool] = Field(default_factory=dict, description="Consent preferences")


class PrivacySettingsResponse(BaseModel):
    """Privacy settings information."""
    user_id: str = Field(..., description="User identifier")
    anonymize_logs: bool = Field(..., description="Whether logs are anonymized")
    data_retention_days: int = Field(..., description="Data retention period")
    consent_preferences: Dict[str, bool] = Field(..., description="Consent preferences")
    last_updated: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# Validation helpers for enum values
def validate_consent_type(consent_type: str) -> str:
    """Validate consent type string."""
    try:
        ConsentType(consent_type)
        return consent_type
    except ValueError:
        valid_types = [t.value for t in ConsentType]
        raise ValueError(f"Invalid consent type. Must be one of: {valid_types}")


def validate_processing_purpose(purpose: str) -> str:
    """Validate processing purpose string."""
    try:
        ProcessingPurpose(purpose)
        return purpose
    except ValueError:
        valid_purposes = [p.value for p in ProcessingPurpose]
        raise ValueError(f"Invalid processing purpose. Must be one of: {valid_purposes}")


def validate_data_category(category: str) -> str:
    """Validate data category string."""
    try:
        DataCategory(category)
        return category
    except ValueError:
        valid_categories = [c.value for c in DataCategory]
        raise ValueError(f"Invalid data category. Must be one of: {valid_categories}")


def validate_pii_type(pii_type: str) -> str:
    """Validate PII type string."""
    try:
        PIIType(pii_type)
        return pii_type
    except ValueError:
        valid_types = [t.value for t in PIIType]
        raise ValueError(f"Invalid PII type. Must be one of: {valid_types}")