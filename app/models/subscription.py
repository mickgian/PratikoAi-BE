"""Subscription Models for Italian Market with Annual Plans.

This module defines subscription models supporting both monthly (€69) and annual (€599)
plans with Italian VAT (22% IVA), Partita IVA validation, and electronic invoice support.
"""

import re
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, ClassVar, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, String, Text, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel


class BillingPeriod(str, Enum):
    """Billing period options"""

    MONTHLY = "monthly"
    ANNUAL = "annual"


class SubscriptionStatus(str, Enum):
    """Subscription status options"""

    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    UNPAID = "unpaid"


class PlanChangeType(str, Enum):
    """Plan change types for tracking"""

    UPGRADE = "upgrade"
    DOWNGRADE = "downgrade"
    REACTIVATION = "reactivation"


class SubscriptionPlan(SQLModel, table=True):
    """Subscription plans for Italian market.

    Supports both monthly (€69) and annual (€599) plans with 22% IVA.
    Annual plan provides 27.7% discount (€229 savings per year).
    """

    __tablename__ = "subscription_plans"

    # Primary key
    id: str | None = Field(default_factory=lambda: str(uuid4()), primary_key=True)

    # Plan details
    name: str = Field(max_length=100)
    description: str | None = Field(default=None, sa_column=Column(Text, nullable=True))

    # Billing configuration (store enum as string)
    billing_period: str = Field(max_length=20)  # BillingPeriod enum value
    base_price_cents: int = Field()  # Price in cents before IVA

    # Stripe integration
    stripe_price_id: str = Field(max_length=255, unique=True)
    stripe_product_id: str = Field(max_length=255)

    # Plan configuration
    is_active: bool = Field(default=True)
    trial_period_days: int = Field(default=7)
    features: str | None = Field(default=None, sa_column=Column(Text, nullable=True))  # JSON string of features

    # Italian market specific
    supports_fattura_elettronica: bool = Field(default=True)
    iva_rate: Decimal = Field(
        default=Decimal("22.00"), sa_column=Column(Numeric(precision=5, scale=2), default=Decimal("22.00"))
    )

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, default=datetime.utcnow))
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, sa_column=Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    )

    # Relationships
    subscriptions: list["Subscription"] = Relationship(back_populates="plan")

    # Italian market plans configuration
    PROFESSIONAL_MONTHLY: ClassVar[dict[str, Any]] = {
        "name": "Professionale Mensile",
        "description": "Piano mensile per professionisti e PMI",
        "billing_period": BillingPeriod.MONTHLY,
        "base_price_cents": 6900,  # €69.00
        "stripe_price_id": "price_professional_monthly_it",
        "stripe_product_id": "prod_professional_it",
        "features": [
            "Domande illimitate",
            "Analisi documenti fiscali",
            "Aggiornamenti normativi in tempo reale",
            "Supporto email",
            "Fattura elettronica",
        ],
    }

    PROFESSIONAL_ANNUAL: ClassVar[dict[str, Any]] = {
        "name": "Professionale Annuale",
        "description": "Piano annuale con risparmi del 27.7% (€229/anno)",
        "billing_period": BillingPeriod.ANNUAL,
        "base_price_cents": 59900,  # €599.00
        "stripe_price_id": "price_professional_annual_it",
        "stripe_product_id": "prod_professional_it",
        "features": [
            "Tutto del piano mensile",
            "Risparmi €229 all'anno",
            "Supporto prioritario",
            "Fattura annuale",
            "Accesso anticipato a nuove funzionalità",
        ],
    }

    def base_price(self) -> Decimal:
        """Base price in euros (excluding IVA)"""
        return Decimal(self.base_price_cents) / 100

    def iva_amount(self) -> Decimal:
        """IVA amount in euros (22% of base price)"""
        return self.base_price() * (self.iva_rate / 100)

    def price_with_iva(self) -> Decimal:
        """Total price including 22% IVA"""
        return self.base_price() + self.iva_amount()

    def monthly_equivalent(self) -> Decimal:
        """Monthly equivalent price for annual plan"""
        if self.billing_period == BillingPeriod.ANNUAL.value:
            return self.base_price() / 12
        return self.base_price()

    def annual_savings(self) -> Decimal:
        """Annual savings compared to monthly plan"""
        if self.billing_period == BillingPeriod.ANNUAL.value:
            monthly_annual_cost = Decimal("69.00") * 12  # €828
            return monthly_annual_cost - self.base_price()  # €229
        return Decimal("0")

    def discount_percentage(self) -> Decimal:
        """Discount percentage for annual plan"""
        if self.billing_period == BillingPeriod.ANNUAL.value:
            monthly_annual_cost = Decimal("69.00") * 12
            return (self.annual_savings() / monthly_annual_cost) * 100
        return Decimal("0")

    def to_dict(self) -> dict[str, Any]:
        """Convert plan to dictionary for API responses"""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "billing_period": self.billing_period,
            "base_price": float(self.base_price()),
            "iva_amount": float(self.iva_amount()),
            "price_with_iva": float(self.price_with_iva()),
            "monthly_equivalent": float(self.monthly_equivalent()),
            "annual_savings": float(self.annual_savings()),
            "discount_percentage": float(self.discount_percentage()),
            "trial_period_days": self.trial_period_days,
            "features": self.features.split(",") if self.features else [],
            "currency": "EUR",
            "iva_rate": float(self.iva_rate),
        }


class Subscription(SQLModel, table=True):
    """User subscriptions with Italian market support.

    Handles both B2B (Partita IVA) and B2C (Codice Fiscale) customers
    with proper invoicing and electronic invoice (fattura elettronica) support.
    """

    __tablename__ = "subscriptions"

    # Primary key
    id: str | None = Field(default_factory=lambda: str(uuid4()), primary_key=True)

    # Foreign keys
    user_id: int = Field(foreign_key="user.id")
    plan_id: str = Field(foreign_key="subscription_plans.id")

    # Stripe integration
    stripe_subscription_id: str = Field(max_length=255, unique=True)
    stripe_customer_id: str = Field(max_length=255)

    # Subscription status and dates (store enum as string)
    status: str = Field(default=SubscriptionStatus.INCOMPLETE.value, max_length=30)
    current_period_start: datetime
    current_period_end: datetime
    trial_start: datetime | None = Field(default=None)
    trial_end: datetime | None = Field(default=None)

    # Cancellation
    cancel_at_period_end: bool = Field(default=False)
    canceled_at: datetime | None = Field(default=None)
    ended_at: datetime | None = Field(default=None)

    # Italian tax information
    is_business: bool = Field(default=False)
    partita_iva: str | None = Field(default=None, max_length=11)  # Italian VAT number (11 digits)
    codice_fiscale: str | None = Field(default=None, max_length=16)  # Italian tax code (16 chars)

    # Invoice information
    invoice_name: str = Field(max_length=255)  # Ragione sociale or full name
    invoice_address: str = Field(max_length=500)
    invoice_cap: str = Field(max_length=5)  # Italian postal code
    invoice_city: str = Field(max_length=100)
    invoice_province: str = Field(max_length=2)  # Italian province code
    invoice_country: str = Field(default="IT", max_length=2)

    # Electronic invoice (fattura elettronica) fields
    sdi_code: str | None = Field(default=None, max_length=7)  # Codice destinatario for SDI
    pec_email: str | None = Field(default=None, max_length=255)  # PEC email for electronic invoice

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, default=datetime.utcnow))
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, sa_column=Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    )

    # Relationships
    # Note: No relationship to User model - it uses SQLModel which is incompatible
    # with SQLAlchemy relationships. Access user via user_id foreign key instead.
    plan: Optional["SubscriptionPlan"] = Relationship(back_populates="subscriptions")
    plan_changes: list["SubscriptionPlanChange"] = Relationship(back_populates="subscription")
    invoices: list["Invoice"] = Relationship(back_populates="subscription")

    # Constraints
    __table_args__ = (
        # Ensure business customers have Partita IVA
        # Individual customers have Codice Fiscale
        UniqueConstraint("user_id", name="uq_user_subscription"),
    )

    def is_active(self) -> bool:
        """Check if subscription is currently active"""
        return self.status in [SubscriptionStatus.ACTIVE.value, SubscriptionStatus.TRIALING.value]

    def is_trial(self) -> bool:
        """Check if subscription is in trial period"""
        if not self.trial_end:
            return False
        return datetime.utcnow() < self.trial_end

    def days_until_renewal(self) -> int:
        """Days until next renewal"""
        if self.current_period_end:
            delta = self.current_period_end - datetime.utcnow()
            return max(0, delta.days)
        return 0

    def monthly_revenue(self) -> Decimal:
        """Monthly revenue for MRR calculation"""
        if self.plan is None:
            return Decimal("0")
        if self.plan.billing_period == BillingPeriod.ANNUAL.value:
            return self.plan.base_price() / 12
        return self.plan.base_price()

    def validate_italian_tax_data(self) -> dict[str, str]:
        """Validate Italian tax data and return errors"""
        errors = {}

        if self.is_business:
            if not self.partita_iva:
                errors["partita_iva"] = "Partita IVA richiesta per aziende"
            elif not self._validate_partita_iva(self.partita_iva):
                errors["partita_iva"] = "Partita IVA non valida"

            if not self.sdi_code and not self.pec_email:
                errors["sdi"] = "Codice destinatario SDI o email PEC richiesti per fattura elettronica"
        else:
            if not self.codice_fiscale:
                errors["codice_fiscale"] = "Codice Fiscale richiesto per privati"
            elif not self._validate_codice_fiscale(self.codice_fiscale):
                errors["codice_fiscale"] = "Codice Fiscale non valido"

        # Common validation
        if not self.invoice_name:
            errors["invoice_name"] = "Nome/Ragione sociale richiesto"
        if not self.invoice_address:
            errors["invoice_address"] = "Indirizzo richiesto"
        if not self.invoice_cap or not re.match(r"^\d{5}$", self.invoice_cap):
            errors["invoice_cap"] = "CAP deve essere 5 cifre"
        if not self.invoice_city:
            errors["invoice_city"] = "Città richiesta"
        if not self.invoice_province or len(self.invoice_province) != 2:
            errors["invoice_province"] = "Provincia deve essere 2 caratteri (es: RM, MI)"

        return errors

    def _validate_partita_iva(self, partita_iva: str) -> bool:
        """Validate Italian VAT number using Luhn algorithm.

        Args:
            partita_iva: 11-digit Italian VAT number

        Returns:
            True if valid, False otherwise
        """
        if not partita_iva or len(partita_iva) != 11:
            return False
        if not partita_iva.isdigit():
            return False

        # Luhn algorithm for Italian Partita IVA
        total = 0
        for i in range(0, 10):
            digit = int(partita_iva[i])
            if i % 2 == 0:  # Even position (0-indexed)
                total += digit
            else:  # Odd position
                doubled = digit * 2
                total += doubled if doubled < 10 else doubled - 9

        check_digit = (10 - (total % 10)) % 10
        return check_digit == int(partita_iva[10])

    def _validate_codice_fiscale(self, codice_fiscale: str) -> bool:
        """Basic validation for Italian tax code (Codice Fiscale).

        Args:
            codice_fiscale: 16-character Italian tax code

        Returns:
            True if format is valid, False otherwise
        """
        if not codice_fiscale or len(codice_fiscale) != 16:
            return False

        # Basic pattern check: 6 letters + 2 digits + 1 letter + 2 digits + 1 letter + 3 digits + 1 letter
        pattern = r"^[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]$"
        return bool(re.match(pattern, codice_fiscale.upper()))

    def can_change_to_plan(self, new_plan: "SubscriptionPlan") -> tuple[bool, str]:
        """Check if subscription can be changed to new plan.

        Args:
            new_plan: Target subscription plan

        Returns:
            Tuple of (can_change, reason)
        """
        if not self.is_active():
            return False, "Subscription must be active to change plans"

        if self.plan_id == new_plan.id:
            return False, "Already subscribed to this plan"

        if self.status == SubscriptionStatus.PAST_DUE.value:
            return False, "Cannot change plans with outstanding payments"

        return True, "Plan change allowed"

    def calculate_proration_credit(self, change_date: Optional[datetime] = None) -> Decimal:
        """Calculate proration credit for current plan.

        Args:
            change_date: Date of plan change (default: now)

        Returns:
            Credit amount in euros
        """
        if not change_date:
            change_date = datetime.utcnow()

        # Calculate unused portion of current period
        total_period = self.current_period_end - self.current_period_start
        change_date - self.current_period_start
        unused_period = self.current_period_end - change_date

        if unused_period.total_seconds() <= 0:
            return Decimal("0")

        # Calculate credit
        usage_ratio = unused_period.total_seconds() / total_period.total_seconds()
        if self.plan is None:
            return Decimal("0")
        credit = self.plan.base_price() * Decimal(str(usage_ratio))

        return credit.quantize(Decimal("0.01"))

    def to_dict(self) -> dict[str, Any]:
        """Convert subscription to dictionary for API responses"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "plan": self.plan.to_dict() if self.plan else None,
            "status": self.status,
            "current_period_start": self.current_period_start.isoformat() if self.current_period_start else None,
            "current_period_end": self.current_period_end.isoformat() if self.current_period_end else None,
            "trial_end": self.trial_end.isoformat() if self.trial_end else None,
            "cancel_at_period_end": self.cancel_at_period_end,
            "is_business": self.is_business,
            "partita_iva": self.partita_iva,
            "codice_fiscale": self.codice_fiscale,
            "invoice_name": self.invoice_name,
            "monthly_revenue": float(self.monthly_revenue()),
            "days_until_renewal": self.days_until_renewal(),
            "is_active": self.is_active(),
            "is_trial": self.is_trial(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class SubscriptionPlanChange(SQLModel, table=True):
    """Track subscription plan changes for analytics and billing.

    Records upgrades, downgrades, and reactivations with proration details.
    """

    __tablename__ = "subscription_plan_changes"

    # Primary key
    id: str | None = Field(default_factory=lambda: str(uuid4()), primary_key=True)

    # Foreign keys
    subscription_id: str = Field(foreign_key="subscriptions.id")
    from_plan_id: str = Field(foreign_key="subscription_plans.id")
    to_plan_id: str = Field(foreign_key="subscription_plans.id")

    # Plan change details (store enum as string)
    change_type: str = Field(max_length=20)  # PlanChangeType enum value

    # Financial details
    proration_credit: Decimal = Field(
        default=Decimal("0"), sa_column=Column(Numeric(precision=10, scale=2), default=Decimal("0"))
    )
    immediate_charge: Decimal = Field(
        default=Decimal("0"), sa_column=Column(Numeric(precision=10, scale=2), default=Decimal("0"))
    )

    # Stripe integration
    stripe_invoice_id: str | None = Field(default=None, max_length=255)
    stripe_payment_intent_id: str | None = Field(default=None, max_length=255)

    # Dates
    effective_date: datetime = Field(
        default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False, default=datetime.utcnow)
    )
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, default=datetime.utcnow))

    # Relationships
    subscription: Optional["Subscription"] = Relationship(back_populates="plan_changes")
    from_plan: Optional["SubscriptionPlan"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "SubscriptionPlanChange.from_plan_id"}
    )
    to_plan: Optional["SubscriptionPlan"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "SubscriptionPlanChange.to_plan_id"}
    )

    def is_upgrade(self) -> bool:
        """Check if this was an upgrade"""
        return self.change_type == PlanChangeType.UPGRADE.value

    def is_downgrade(self) -> bool:
        """Check if this was a downgrade"""
        return self.change_type == PlanChangeType.DOWNGRADE.value

    def net_charge(self) -> Decimal:
        """Net charge after proration"""
        return self.immediate_charge - self.proration_credit

    def to_dict(self) -> dict[str, Any]:
        """Convert plan change to dictionary"""
        return {
            "id": str(self.id),
            "subscription_id": str(self.subscription_id),
            "change_type": self.change_type,
            "from_plan": self.from_plan.name if self.from_plan else None,
            "to_plan": self.to_plan.name if self.to_plan else None,
            "proration_credit": float(self.proration_credit),
            "immediate_charge": float(self.immediate_charge),
            "net_charge": float(self.net_charge()),
            "effective_date": self.effective_date.isoformat(),
            "created_at": self.created_at.isoformat(),
        }


class Invoice(SQLModel, table=True):
    """Italian invoices with fattura elettronica support.

    Compliant with Italian invoice requirements including SDI integration.
    """

    __tablename__ = "invoices"

    # Primary key
    id: str | None = Field(default_factory=lambda: str(uuid4()), primary_key=True)

    # Foreign keys
    subscription_id: str = Field(foreign_key="subscriptions.id")

    # Invoice identification
    invoice_number: str = Field(max_length=50, unique=True)
    invoice_date: datetime = Field(
        default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False, default=datetime.utcnow)
    )
    due_date: datetime

    # Amounts (in euros)
    subtotal: Decimal = Field(sa_column=Column(Numeric(precision=10, scale=2), nullable=False))  # Imponibile
    iva_amount: Decimal = Field(sa_column=Column(Numeric(precision=10, scale=2), nullable=False))  # IVA 22%
    total_amount: Decimal = Field(sa_column=Column(Numeric(precision=10, scale=2), nullable=False))  # Totale

    # Payment
    payment_status: str = Field(default="pending", max_length=50)  # pending, paid, failed
    paid_at: datetime | None = Field(default=None)

    # Stripe integration
    stripe_invoice_id: str | None = Field(default=None, max_length=255, unique=True)
    stripe_payment_intent_id: str | None = Field(default=None, max_length=255)

    # Electronic invoice (fattura elettronica)
    fattura_elettronica_xml: str | None = Field(default=None, sa_column=Column(Text, nullable=True))  # Generated XML
    sdi_transmission_id: str | None = Field(default=None, max_length=255)  # SDI transmission reference
    sdi_status: str | None = Field(default=None, max_length=50)  # sent, accepted, rejected
    sdi_sent_at: datetime | None = Field(default=None)

    # PDF invoice
    pdf_path: str | None = Field(default=None, max_length=500)  # Path to generated PDF

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, default=datetime.utcnow))
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, sa_column=Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    )

    # Relationships
    subscription: Optional["Subscription"] = Relationship(back_populates="invoices")

    def is_paid(self) -> bool:
        """Check if invoice is paid"""
        return self.payment_status == "paid"

    def is_overdue(self) -> bool:
        """Check if invoice is overdue"""
        return datetime.utcnow() > self.due_date and not self.is_paid()

    def to_dict(self) -> dict[str, Any]:
        """Convert invoice to dictionary"""
        return {
            "id": str(self.id),
            "subscription_id": str(self.subscription_id),
            "invoice_number": self.invoice_number,
            "invoice_date": self.invoice_date.isoformat(),
            "due_date": self.due_date.isoformat(),
            "subtotal": float(self.subtotal),
            "iva_amount": float(self.iva_amount),
            "total_amount": float(self.total_amount),
            "payment_status": self.payment_status,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
            "is_paid": self.is_paid(),
            "is_overdue": self.is_overdue(),
            "sdi_status": self.sdi_status,
            "created_at": self.created_at.isoformat(),
        }
