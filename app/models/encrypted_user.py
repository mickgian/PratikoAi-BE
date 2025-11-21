"""Enhanced User model with database encryption for PII fields.

This module extends the existing User model to add encryption for sensitive
personally identifiable information (PII) fields to comply with Italian
data protection requirements and GDPR.
"""

from datetime import UTC, datetime, timezone
from typing import TYPE_CHECKING, List, Optional

import bcrypt
from sqlalchemy import DateTime
from sqlmodel import Column, Field, Relationship, String

from app.core.encryption.encrypted_types import EncryptedEmail, EncryptedPersonalData, EncryptedPhone, EncryptedTaxID
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.session import Session


class EncryptedUser(BaseModel, table=True):
    """Enhanced User model with encrypted PII fields for Italian data protection compliance.

    This model encrypts sensitive fields including:
    - Email addresses
    - Phone numbers
    - Italian tax IDs (Codice Fiscale)
    - Personal data

    All encryption is transparent through SQLAlchemy type decorators.
    """

    __tablename__ = "users"

    # Primary identification (not encrypted)
    id: int = Field(default=None, primary_key=True)

    # Encrypted PII fields - automatically encrypted/decrypted
    email: str = Field(
        sa_column=Column(EncryptedEmail(255), unique=True, index=True), description="User's email address (encrypted)"
    )

    phone: str | None = Field(
        default=None, sa_column=Column(EncryptedPhone(50)), description="User's phone number (encrypted)"
    )

    tax_id: str | None = Field(
        default=None, sa_column=Column(EncryptedTaxID(50)), description="Italian tax ID - Codice Fiscale (encrypted)"
    )

    # Additional encrypted personal data
    full_name: str | None = Field(
        default=None, sa_column=Column(EncryptedPersonalData(200)), description="User's full name (encrypted)"
    )

    address: str | None = Field(
        default=None, sa_column=Column(EncryptedPersonalData(500)), description="User's address (encrypted)"
    )

    # Non-sensitive fields (not encrypted for performance)
    hashed_password: str = Field(description="Bcrypt hashed password")
    refresh_token_hash: str | None = Field(
        default=None, index=True, description="Hash of refresh token for secure validation"
    )

    # Account status and preferences (not encrypted)
    is_active: bool = Field(default=True, description="Whether user account is active")
    email_verified: bool = Field(default=False, description="Whether email is verified")
    phone_verified: bool = Field(default=False, description="Whether phone is verified")
    language_preference: str = Field(default="it", description="User's language preference")
    timezone: str = Field(default="Europe/Rome", description="User's timezone")

    # GDPR and privacy settings (not encrypted)
    gdpr_consent_given: bool = Field(default=False, description="GDPR consent status")
    gdpr_consent_date: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True)), description="When GDPR consent was given"
    )
    marketing_consent: bool = Field(default=False, description="Marketing consent status")
    data_retention_requested: bool = Field(default=False, description="User requested data retention")

    # Account security (not encrypted)
    last_login: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True)), description="Last login timestamp"
    )
    failed_login_attempts: int = Field(default=0, description="Number of failed login attempts")
    account_locked_until: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True)), description="Account locked until this timestamp"
    )

    # Audit fields for compliance
    pii_last_updated: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True)), description="When PII was last updated"
    )
    encryption_key_version: int | None = Field(
        default=None, description="Version of encryption key used for this user's data"
    )

    # Relationships
    sessions: list["Session"] = Relationship(back_populates="user")

    def verify_password(self, password: str) -> bool:
        """Verify if the provided password matches the hash.

        Truncates password to 72 bytes to comply with bcrypt limits.
        """
        password_bytes = password.encode("utf-8")[:72]
        return bcrypt.checkpw(password_bytes, self.hashed_password.encode("utf-8"))

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt.

        Truncates password to 72 bytes to comply with bcrypt limits.
        """
        password_bytes = password.encode("utf-8")[:72]
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password_bytes, salt).decode("utf-8")

    def set_refresh_token_hash(self, refresh_token: str) -> None:
        """Set the hash of the refresh token.

        Stores a bcrypt hash of the refresh token for secure validation.
        This allows us to revoke refresh tokens by clearing the hash.

        Args:
            refresh_token: The refresh token to hash and store

        Note:
            Truncates token to 72 bytes to comply with bcrypt limits.
        """
        token_bytes = refresh_token.encode("utf-8")[:72]
        salt = bcrypt.gensalt()
        self.refresh_token_hash = bcrypt.hashpw(token_bytes, salt).decode("utf-8")

    def verify_refresh_token(self, refresh_token: str) -> bool:
        """Verify if the provided refresh token matches the stored hash.

        Args:
            refresh_token: The refresh token to verify

        Returns:
            bool: True if the token matches, False otherwise

        Note:
            Truncates token to 72 bytes to comply with bcrypt limits.
        """
        if self.refresh_token_hash is None:
            return False
        token_bytes = refresh_token.encode("utf-8")[:72]
        return bcrypt.checkpw(token_bytes, self.refresh_token_hash.encode("utf-8"))

    def revoke_refresh_token(self) -> None:
        """Revoke the current refresh token by clearing its hash.

        This effectively invalidates all existing refresh tokens for this user.
        """
        self.refresh_token_hash = None

    def update_pii_timestamp(self) -> None:
        """Update the PII last updated timestamp for audit compliance."""
        self.pii_last_updated = datetime.now(UTC)

    def set_encryption_key_version(self, key_version: int) -> None:
        """Set the encryption key version used for this user's data."""
        self.encryption_key_version = key_version

    def validate_italian_tax_id(self) -> bool:
        """Validate Italian tax ID (Codice Fiscale) format.

        Returns:
            bool: True if tax_id is valid Italian format, False otherwise
        """
        if not self.tax_id:
            return True  # Optional field

        # Italian Codice Fiscale validation
        # Format: 16 characters - 6 letters, 2 digits, 1 letter, 2 digits, 1 letter, 3 alphanumeric
        import re

        pattern = r"^[A-Z]{6}[0-9]{2}[A-Z][0-9]{2}[A-Z][0-9A-Z]{3}$"
        return bool(re.match(pattern, self.tax_id.upper()))

    def validate_italian_phone(self) -> bool:
        """Validate Italian phone number format.

        Returns:
            bool: True if phone is valid Italian format, False otherwise
        """
        if not self.phone:
            return True  # Optional field

        # Italian phone number validation
        # Formats: +39 xxx xxx xxxx, 0xx xxx xxxx, 3xx xxx xxxx
        import re

        patterns = [
            r"^\+39\s?[0-9]{2,3}\s?[0-9]{3,4}\s?[0-9]{3,4}$",  # +39 format
            r"^0[0-9]{1,3}\s?[0-9]{3,4}\s?[0-9]{3,4}$",  # Landline
            r"^3[0-9]{2}\s?[0-9]{3}\s?[0-9]{4}$",  # Mobile
        ]

        phone_clean = self.phone.replace(" ", "").replace("-", "")
        return any(re.match(pattern, phone_clean) for pattern in patterns)

    def get_gdpr_data_export(self) -> dict:
        """Get user data for GDPR export request.

        Returns personal data in a structured format for export.

        Returns:
            dict: User's personal data for GDPR compliance
        """
        return {
            "user_id": self.id,
            "email": self.email,
            "phone": self.phone,
            "tax_id": self.tax_id,
            "full_name": self.full_name,
            "address": self.address,
            "language_preference": self.language_preference,
            "timezone": self.timezone,
            "gdpr_consent_given": self.gdpr_consent_given,
            "gdpr_consent_date": self.gdpr_consent_date.isoformat() if self.gdpr_consent_date else None,
            "marketing_consent": self.marketing_consent,
            "account_created": self.created_at.isoformat() if self.created_at else None,
            "pii_last_updated": self.pii_last_updated.isoformat() if self.pii_last_updated else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }

    def anonymize_for_gdpr_deletion(self) -> None:
        """Anonymize user data for GDPR "right to be forgotten" compliance.

        Replaces PII with anonymized values while preserving data structure
        for analytics and system integrity.
        """
        # Generate anonymous ID based on original user ID
        anonymous_id = f"deleted_user_{self.id}"

        # Replace PII with anonymized values
        self.email = f"{anonymous_id}@deleted.local"
        self.phone = None
        self.tax_id = None
        self.full_name = f"Deleted User {self.id}"
        self.address = None

        # Update audit fields
        self.pii_last_updated = datetime.now(UTC)
        self.is_active = False
        self.email_verified = False
        self.phone_verified = False

        # Clear tokens
        self.refresh_token_hash = None

        # Mark as deleted but preserve record for system integrity
        self.gdpr_consent_given = False
        self.marketing_consent = False
        self.data_retention_requested = False


class EncryptedQueryLog(BaseModel, table=True):
    """Query log model with encrypted query content for privacy compliance."""

    __tablename__ = "query_logs"

    id: int = Field(default=None, primary_key=True)

    # Encrypted fields
    query: str = Field(sa_column=Column(EncryptedPersonalData(2000)), description="User query content (encrypted)")

    user_query_context: str | None = Field(
        default=None, sa_column=Column(EncryptedPersonalData(1000)), description="Additional query context (encrypted)"
    )

    # Non-encrypted fields for performance and analytics
    user_id: int | None = Field(default=None, foreign_key="user.id", description="User who made the query")
    session_id: str | None = Field(default=None, description="Session identifier")

    # Query metadata (not encrypted)
    query_type: str = Field(default="general", description="Type of query")
    language_detected: str = Field(default="it", description="Detected query language")
    response_cached: bool = Field(default=False, description="Whether response was cached")
    response_time_ms: float | None = Field(default=None, description="Response time in milliseconds")

    # Cost tracking (not encrypted)
    llm_tokens_used: int | None = Field(default=None, description="LLM tokens consumed")
    estimated_cost_euros: float | None = Field(default=None, description="Estimated cost in EUR")

    # Audit fields
    encryption_key_version: int | None = Field(default=None, description="Version of encryption key used")


class EncryptedSubscriptionData(BaseModel, table=True):
    """Subscription data model with encrypted financial information."""

    __tablename__ = "subscription_data"

    id: int = Field(default=None, primary_key=True)

    user_id: int = Field(foreign_key="user.id", description="Associated user")

    # Encrypted financial data
    stripe_customer_id: str | None = Field(
        default=None, sa_column=Column(EncryptedPersonalData(100)), description="Stripe customer ID (encrypted)"
    )

    invoice_data: str | None = Field(
        default=None, sa_column=Column(EncryptedPersonalData(2000)), description="Invoice and billing data (encrypted)"
    )

    payment_method_last4: str | None = Field(
        default=None,
        sa_column=Column(EncryptedPersonalData(10)),
        description="Last 4 digits of payment method (encrypted)",
    )

    # Non-encrypted subscription metadata
    subscription_tier: str = Field(default="free", description="Subscription tier")
    subscription_status: str = Field(default="active", description="Subscription status")

    # Billing information (dates and amounts not encrypted for analytics)
    current_period_start: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True)), description="Current billing period start"
    )
    current_period_end: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True)), description="Current billing period end"
    )

    monthly_cost_euros: float | None = Field(default=None, description="Monthly cost in EUR")

    # Audit fields
    encryption_key_version: int | None = Field(default=None, description="Version of encryption key used")


# Backward compatibility alias
User = EncryptedUser

# Avoid circular imports
from app.models.session import Session  # noqa: E402
