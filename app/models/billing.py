"""Billing models for usage-based billing system (DEV-257).

Implements Claude Code-style tiered billing with rolling cost windows,
pay-as-you-go credits, and plan-specific markup.
"""

from datetime import datetime
from enum import Enum

from sqlalchemy import Column, DateTime, Index, func
from sqlmodel import Field, SQLModel


class WindowType(str, Enum):
    """Rolling window types for usage tracking."""

    FIVE_HOUR = "5h"
    SEVEN_DAY = "7d"


class TransactionType(str, Enum):
    """Credit transaction types."""

    RECHARGE = "recharge"
    CONSUMPTION = "consumption"
    REFUND = "refund"


class BillingPlan(SQLModel, table=True):  # type: ignore[call-arg]
    """Billing plan definitions.

    Stores the 3 tiers (Base, Pro, Premium) with their cost limits
    and markup factors. Plans are seed data with stable slugs.
    """

    __tablename__ = "billing_plans"

    id: int | None = Field(default=None, primary_key=True)
    slug: str = Field(max_length=50, unique=True, index=True)
    name: str = Field(max_length=100)
    price_eur_monthly: float = Field(description="Monthly subscription price in EUR")  # type: ignore[assignment]
    monthly_cost_limit_eur: float = Field(description="Monthly LLM cost cap in EUR")  # type: ignore[assignment]
    window_5h_cost_limit_eur: float = Field(description="5-hour rolling window cost limit")  # type: ignore[assignment]
    window_7d_cost_limit_eur: float = Field(description="7-day rolling window cost limit")  # type: ignore[assignment]
    credit_markup_factor: float = Field(default=1.0, description="Markup on credit consumption (1.5 = 50% markup)")  # type: ignore[assignment]
    stripe_price_id: str | None = Field(default=None, max_length=255)
    is_active: bool = Field(default=True, index=True)
    created_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )  # type: ignore[assignment]


class UsageWindow(SQLModel, table=True):  # type: ignore[call-arg]
    """Rolling window usage records.

    Tracks per-user cost in 5h and 7d windows. Used alongside Redis
    sorted sets for real-time checks with PostgreSQL as durable store.
    """

    __tablename__ = "usage_windows"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="user.id")
    window_type: str = Field(max_length=10, description="Window type: '5h' or '7d'")
    cost_eur: float = Field(description="Cost recorded for this event")  # type: ignore[assignment]
    recorded_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), index=True),
    )  # type: ignore[assignment]
    # FK to usage_events.id enforced at migration level (not model level)
    # to avoid SQLModel metadata resolution issues with create_all()
    usage_event_id: int | None = Field(default=None, description="Link to original UsageEvent")

    __table_args__ = (Index("ix_usage_windows_user_window_time", "user_id", "window_type", "recorded_at"),)


class UserCredit(SQLModel, table=True):  # type: ignore[call-arg]
    """User credit balance for pay-as-you-go usage.

    Each user has at most one credit record. Credits are consumed
    with plan-specific markup when rolling window limits are exceeded.
    """

    __tablename__ = "user_credits"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True, index=True)
    balance_eur: float = Field(default=0.0, description="Current credit balance in EUR")  # type: ignore[assignment]
    extra_usage_enabled: bool = Field(default=False, description="Whether user opted into credit consumption on limit")  # type: ignore[assignment]
    updated_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )  # type: ignore[assignment]


class CreditTransaction(SQLModel, table=True):  # type: ignore[call-arg]
    """Credit transaction log for auditing.

    Records all credit balance changes: recharges, consumptions, and refunds.
    """

    __tablename__ = "credit_transactions"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="user.id")
    transaction_type: str = Field(max_length=20, description="recharge, consumption, or refund")
    amount_eur: float = Field(description="Amount of this transaction (positive)")  # type: ignore[assignment]
    balance_after_eur: float = Field(description="Balance after this transaction")  # type: ignore[assignment]
    stripe_payment_intent_id: str | None = Field(default=None, max_length=255)
    # FK to usage_events.id enforced at migration level
    usage_event_id: int | None = Field(default=None)
    description: str | None = Field(default=None, max_length=500)
    created_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), index=True),
    )  # type: ignore[assignment]
