"""Payment and subscription models."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from sqlalchemy import Index
from sqlmodel import JSON, Column, Field, SQLModel


class SubscriptionStatus(str, Enum):
    """Subscription status types."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    UNPAID = "unpaid"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    TRIALING = "trialing"


class PaymentStatus(str, Enum):
    """Payment status types."""

    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"
    REFUNDED = "refunded"


class PlanType(str, Enum):
    """Subscription plan types."""

    TRIAL = "trial"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    ENTERPRISE = "enterprise"


class Subscription(SQLModel, table=True):
    """User subscription model."""

    __tablename__ = "subscriptions"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(..., foreign_key="user.id", description="User ID from session")

    # Stripe-specific fields
    stripe_subscription_id: str = Field(..., description="Stripe subscription ID")
    stripe_customer_id: str = Field(..., description="Stripe customer ID")
    stripe_price_id: str = Field(..., description="Stripe price ID")

    # Subscription details
    status: SubscriptionStatus = Field(default=SubscriptionStatus.INACTIVE)
    plan_type: PlanType = Field(default=PlanType.MONTHLY)
    amount_eur: float = Field(..., description="Monthly amount in EUR")
    currency: str = Field(default="eur", description="Currency code")

    # Billing cycle
    current_period_start: datetime = Field(..., description="Current billing period start")
    current_period_end: datetime = Field(..., description="Current billing period end")

    # Trial information
    trial_start: datetime | None = Field(default=None, description="Trial period start")
    trial_end: datetime | None = Field(default=None, description="Trial period end")

    # Subscription lifecycle
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    canceled_at: datetime | None = Field(default=None, description="Cancellation timestamp")
    ended_at: datetime | None = Field(default=None, description="End timestamp")

    # Additional data
    extra_data: dict[str, Any] | None = Field(default_factory=dict, sa_column=Column(JSON))

    __table_args__ = (
        Index("idx_subscription_user_id", "user_id"),
        Index("idx_subscription_stripe_id", "stripe_subscription_id"),
        Index("idx_subscription_customer_id", "stripe_customer_id"),
        Index("idx_subscription_status", "status"),
    )


class Payment(SQLModel, table=True):
    """Payment transaction model."""

    __tablename__ = "payments"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(..., foreign_key="user.id", description="User ID from session")
    subscription_id: int | None = Field(default=None, foreign_key="subscriptions.id")

    # Stripe-specific fields
    stripe_payment_intent_id: str = Field(..., description="Stripe payment intent ID")
    stripe_invoice_id: str | None = Field(default=None, description="Stripe invoice ID")
    stripe_charge_id: str | None = Field(default=None, description="Stripe charge ID")

    # Payment details
    amount_eur: float = Field(..., description="Payment amount in EUR")
    currency: str = Field(default="eur", description="Currency code")
    status: PaymentStatus = Field(default=PaymentStatus.PENDING)

    # Payment method
    payment_method_type: str | None = Field(default=None, description="e.g., card, sepa_debit")
    payment_method_last4: str | None = Field(default=None, description="Last 4 digits of payment method")
    payment_method_brand: str | None = Field(default=None, description="e.g., visa, mastercard")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    paid_at: datetime | None = Field(default=None, description="Payment completion timestamp")
    failed_at: datetime | None = Field(default=None, description="Payment failure timestamp")

    # Failure information
    failure_reason: str | None = Field(default=None, description="Reason for payment failure")
    failure_code: str | None = Field(default=None, description="Stripe failure code")

    # Additional data
    extra_data: dict[str, Any] | None = Field(default_factory=dict, sa_column=Column(JSON))

    __table_args__ = (
        Index("idx_payment_user_id", "user_id"),
        Index("idx_payment_subscription_id", "subscription_id"),
        Index("idx_payment_stripe_intent_id", "stripe_payment_intent_id"),
        Index("idx_payment_status", "status"),
        Index("idx_payment_created_at", "created_at"),
    )


class Invoice(SQLModel, table=True):
    """Invoice model for billing history."""

    __tablename__ = "invoices"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(..., foreign_key="user.id", description="User ID from session")
    subscription_id: int | None = Field(default=None, foreign_key="subscriptions.id")
    payment_id: int | None = Field(default=None, foreign_key="payments.id")

    # Stripe-specific fields
    stripe_invoice_id: str = Field(..., description="Stripe invoice ID")
    stripe_subscription_id: str | None = Field(default=None, description="Associated Stripe subscription")

    # Invoice details
    invoice_number: str = Field(..., description="Human-readable invoice number")
    amount_eur: float = Field(..., description="Invoice amount in EUR")
    tax_eur: float = Field(default=0.0, description="Tax amount in EUR")
    total_eur: float = Field(..., description="Total amount including tax")
    currency: str = Field(default="eur", description="Currency code")

    # Invoice status
    status: str = Field(..., description="Invoice status (draft, open, paid, void, uncollectible)")
    paid: bool = Field(default=False, description="Whether invoice is paid")

    # Billing period
    period_start: datetime = Field(..., description="Billing period start")
    period_end: datetime = Field(..., description="Billing period end")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    due_date: datetime | None = Field(default=None, description="Invoice due date")
    paid_at: datetime | None = Field(default=None, description="Payment timestamp")

    # Download URLs
    invoice_pdf_url: str | None = Field(default=None, description="URL to download PDF")
    hosted_invoice_url: str | None = Field(default=None, description="Stripe hosted invoice URL")

    # Additional data
    extra_data: dict[str, Any] | None = Field(default_factory=dict, sa_column=Column(JSON))

    __table_args__ = (
        Index("idx_invoice_user_id", "user_id"),
        Index("idx_invoice_subscription_id", "subscription_id"),
        Index("idx_invoice_stripe_id", "stripe_invoice_id"),
        Index("idx_invoice_status", "status"),
        Index("idx_invoice_period", "period_start", "period_end"),
    )


class Customer(SQLModel, table=True):
    """Stripe customer model."""

    __tablename__ = "customers"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(..., unique=True, foreign_key="user.id", description="User ID from session")

    # Stripe-specific fields
    stripe_customer_id: str = Field(..., unique=True, description="Stripe customer ID")

    # Customer details
    email: str = Field(..., description="Customer email")
    name: str | None = Field(default=None, description="Customer name")

    # Billing address
    address_line1: str | None = Field(default=None)
    address_line2: str | None = Field(default=None)
    address_city: str | None = Field(default=None)
    address_state: str | None = Field(default=None)
    address_postal_code: str | None = Field(default=None)
    address_country: str | None = Field(default=None)

    # Tax information
    tax_id: str | None = Field(default=None, description="VAT number or tax ID")
    tax_exempt: bool = Field(default=False, description="Tax exemption status")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Additional data
    extra_data: dict[str, Any] | None = Field(default_factory=dict, sa_column=Column(JSON))

    __table_args__ = (
        Index("idx_customer_user_id", "user_id"),
        Index("idx_customer_stripe_id", "stripe_customer_id"),
        Index("idx_customer_email", "email"),
    )


class WebhookEvent(SQLModel, table=True):
    """Stripe webhook event log."""

    __tablename__ = "webhook_events"

    id: int | None = Field(default=None, primary_key=True)

    # Stripe event details
    stripe_event_id: str = Field(..., unique=True, description="Stripe event ID")
    event_type: str = Field(..., description="Event type (e.g., invoice.payment_succeeded)")

    # Processing status
    processed: bool = Field(default=False, description="Whether event was processed")
    processed_at: datetime | None = Field(default=None, description="Processing timestamp")

    # Error handling
    error_count: int = Field(default=0, description="Number of processing errors")
    last_error: str | None = Field(default=None, description="Last processing error")
    last_error_at: datetime | None = Field(default=None, description="Last error timestamp")

    # Event data
    event_data: dict[str, Any] = Field(..., sa_column=Column(JSON), description="Full event data")

    created_at: datetime = Field(default_factory=datetime.utcnow)

    __table_args__ = (
        Index("idx_webhook_stripe_event_id", "stripe_event_id"),
        Index("idx_webhook_event_type", "event_type"),
        Index("idx_webhook_processed", "processed"),
        Index("idx_webhook_created_at", "created_at"),
    )
