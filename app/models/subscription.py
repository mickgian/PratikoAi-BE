"""
Subscription Models for Italian Market with Annual Plans.

This module defines subscription models supporting both monthly (€69) and annual (€599)
plans with Italian VAT (22% IVA), Partita IVA validation, and electronic invoice support.
"""

import re
from enum import Enum
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any
from uuid import uuid4

from sqlalchemy import (
    Column, String, Integer, DateTime, Boolean, ForeignKey, 
    Enum as SQLEnum, Text, Numeric, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property

from app.models.ccnl_database import Base


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


class SubscriptionPlan(Base):
    """
    Subscription plans for Italian market.
    
    Supports both monthly (€69) and annual (€599) plans with 22% IVA.
    Annual plan provides 27.7% discount (€229 savings per year).
    """
    __tablename__ = "subscription_plans"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    billing_period = Column(SQLEnum(BillingPeriod), nullable=False)
    base_price_cents = Column(Integer, nullable=False)  # Price in cents before IVA
    stripe_price_id = Column(String(255), unique=True, nullable=False)
    stripe_product_id = Column(String(255), nullable=False)
    
    # Plan configuration
    is_active = Column(Boolean, default=True)
    trial_period_days = Column(Integer, default=7)
    features = Column(Text)  # JSON string of features
    
    # Italian market specific
    supports_fattura_elettronica = Column(Boolean, default=True)
    iva_rate = Column(Numeric(precision=5, scale=2), default=Decimal("22.00"))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    subscriptions = relationship("Subscription", back_populates="plan")
    
    # Italian market plans configuration
    PROFESSIONAL_MONTHLY = {
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
            "Fattura elettronica"
        ]
    }
    
    PROFESSIONAL_ANNUAL = {
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
            "Accesso anticipato a nuove funzionalità"
        ]
    }
    
    @hybrid_property
    def base_price(self) -> Decimal:
        """Base price in euros (excluding IVA)"""
        return Decimal(self.base_price_cents) / 100
    
    @hybrid_property
    def iva_amount(self) -> Decimal:
        """IVA amount in euros (22% of base price)"""
        return self.base_price * (self.iva_rate / 100)
    
    @hybrid_property
    def price_with_iva(self) -> Decimal:
        """Total price including 22% IVA"""
        return self.base_price + self.iva_amount
    
    @hybrid_property
    def monthly_equivalent(self) -> Decimal:
        """Monthly equivalent price for annual plan"""
        if self.billing_period == BillingPeriod.ANNUAL:
            return self.base_price / 12
        return self.base_price
    
    @hybrid_property
    def annual_savings(self) -> Decimal:
        """Annual savings compared to monthly plan"""
        if self.billing_period == BillingPeriod.ANNUAL:
            monthly_annual_cost = Decimal("69.00") * 12  # €828
            return monthly_annual_cost - self.base_price  # €229
        return Decimal("0")
    
    @hybrid_property
    def discount_percentage(self) -> Decimal:
        """Discount percentage for annual plan"""
        if self.billing_period == BillingPeriod.ANNUAL:
            monthly_annual_cost = Decimal("69.00") * 12
            return (self.annual_savings / monthly_annual_cost) * 100
        return Decimal("0")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert plan to dictionary for API responses"""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "billing_period": self.billing_period.value,
            "base_price": float(self.base_price),
            "iva_amount": float(self.iva_amount),
            "price_with_iva": float(self.price_with_iva),
            "monthly_equivalent": float(self.monthly_equivalent),
            "annual_savings": float(self.annual_savings),
            "discount_percentage": float(self.discount_percentage),
            "trial_period_days": self.trial_period_days,
            "features": self.features.split(",") if self.features else [],
            "currency": "EUR",
            "iva_rate": float(self.iva_rate)
        }


class Subscription(Base):
    """
    User subscriptions with Italian market support.
    
    Handles both B2B (Partita IVA) and B2C (Codice Fiscale) customers
    with proper invoicing and electronic invoice (fattura elettronica) support.
    """
    __tablename__ = "subscriptions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("subscription_plans.id"), nullable=False)
    
    # Stripe integration
    stripe_subscription_id = Column(String(255), unique=True, nullable=False)
    stripe_customer_id = Column(String(255), nullable=False)
    
    # Subscription status and dates
    status = Column(SQLEnum(SubscriptionStatus), nullable=False, default=SubscriptionStatus.INCOMPLETE)
    current_period_start = Column(DateTime, nullable=False)
    current_period_end = Column(DateTime, nullable=False)
    trial_start = Column(DateTime)
    trial_end = Column(DateTime)
    
    # Cancellation
    cancel_at_period_end = Column(Boolean, default=False)
    canceled_at = Column(DateTime)
    ended_at = Column(DateTime)
    
    # Italian tax information
    is_business = Column(Boolean, default=False)
    partita_iva = Column(String(11))  # Italian VAT number (11 digits)
    codice_fiscale = Column(String(16))  # Italian tax code (16 chars)
    
    # Invoice information
    invoice_name = Column(String(255), nullable=False)  # Ragione sociale or full name
    invoice_address = Column(String(500), nullable=False)
    invoice_cap = Column(String(5), nullable=False)  # Italian postal code
    invoice_city = Column(String(100), nullable=False)
    invoice_province = Column(String(2), nullable=False)  # Italian province code
    invoice_country = Column(String(2), default="IT")
    
    # Electronic invoice (fattura elettronica) fields
    sdi_code = Column(String(7))  # Codice destinatario for SDI
    pec_email = Column(String(255))  # PEC email for electronic invoice
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="subscription")
    plan = relationship("SubscriptionPlan", back_populates="subscriptions")
    plan_changes = relationship("SubscriptionPlanChange", back_populates="subscription")
    invoices = relationship("Invoice", back_populates="subscription")
    
    # Constraints
    __table_args__ = (
        # Ensure business customers have Partita IVA
        # Individual customers have Codice Fiscale
        UniqueConstraint('user_id', name='uq_user_subscription'),
    )
    
    @hybrid_property
    def is_active(self) -> bool:
        """Check if subscription is currently active"""
        return self.status in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING]
    
    @hybrid_property
    def is_trial(self) -> bool:
        """Check if subscription is in trial period"""
        if not self.trial_end:
            return False
        return datetime.utcnow() < self.trial_end
    
    @hybrid_property
    def days_until_renewal(self) -> int:
        """Days until next renewal"""
        if self.current_period_end:
            delta = self.current_period_end - datetime.utcnow()
            return max(0, delta.days)
        return 0
    
    @hybrid_property
    def monthly_revenue(self) -> Decimal:
        """Monthly revenue for MRR calculation"""
        if self.plan.billing_period == BillingPeriod.ANNUAL:
            return self.plan.base_price / 12
        return self.plan.base_price
    
    def validate_italian_tax_data(self) -> Dict[str, str]:
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
        if not self.invoice_cap or not re.match(r'^\d{5}$', self.invoice_cap):
            errors["invoice_cap"] = "CAP deve essere 5 cifre"
        if not self.invoice_city:
            errors["invoice_city"] = "Città richiesta"
        if not self.invoice_province or len(self.invoice_province) != 2:
            errors["invoice_province"] = "Provincia deve essere 2 caratteri (es: RM, MI)"
        
        return errors
    
    def _validate_partita_iva(self, partita_iva: str) -> bool:
        """
        Validate Italian VAT number using Luhn algorithm.
        
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
        """
        Basic validation for Italian tax code (Codice Fiscale).
        
        Args:
            codice_fiscale: 16-character Italian tax code
            
        Returns:
            True if format is valid, False otherwise
        """
        if not codice_fiscale or len(codice_fiscale) != 16:
            return False
        
        # Basic pattern check: 6 letters + 2 digits + 1 letter + 2 digits + 1 letter + 3 digits + 1 letter
        pattern = r'^[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]$'
        return bool(re.match(pattern, codice_fiscale.upper()))
    
    def can_change_to_plan(self, new_plan: SubscriptionPlan) -> tuple[bool, str]:
        """
        Check if subscription can be changed to new plan.
        
        Args:
            new_plan: Target subscription plan
            
        Returns:
            Tuple of (can_change, reason)
        """
        if not self.is_active:
            return False, "Subscription must be active to change plans"
        
        if self.plan_id == new_plan.id:
            return False, "Already subscribed to this plan"
        
        if self.status == SubscriptionStatus.PAST_DUE:
            return False, "Cannot change plans with outstanding payments"
        
        return True, "Plan change allowed"
    
    def calculate_proration_credit(self, change_date: datetime = None) -> Decimal:
        """
        Calculate proration credit for current plan.
        
        Args:
            change_date: Date of plan change (default: now)
            
        Returns:
            Credit amount in euros
        """
        if not change_date:
            change_date = datetime.utcnow()
        
        # Calculate unused portion of current period
        total_period = self.current_period_end - self.current_period_start
        used_period = change_date - self.current_period_start
        unused_period = self.current_period_end - change_date
        
        if unused_period.total_seconds() <= 0:
            return Decimal("0")
        
        # Calculate credit
        usage_ratio = unused_period.total_seconds() / total_period.total_seconds()
        credit = self.plan.base_price * Decimal(str(usage_ratio))
        
        return credit.quantize(Decimal("0.01"))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert subscription to dictionary for API responses"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "plan": self.plan.to_dict() if self.plan else None,
            "status": self.status.value,
            "current_period_start": self.current_period_start.isoformat() if self.current_period_start else None,
            "current_period_end": self.current_period_end.isoformat() if self.current_period_end else None,
            "trial_end": self.trial_end.isoformat() if self.trial_end else None,
            "cancel_at_period_end": self.cancel_at_period_end,
            "is_business": self.is_business,
            "partita_iva": self.partita_iva,
            "codice_fiscale": self.codice_fiscale,
            "invoice_name": self.invoice_name,
            "monthly_revenue": float(self.monthly_revenue),
            "days_until_renewal": self.days_until_renewal,
            "is_active": self.is_active,
            "is_trial": self.is_trial,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class SubscriptionPlanChange(Base):
    """
    Track subscription plan changes for analytics and billing.
    
    Records upgrades, downgrades, and reactivations with proration details.
    """
    __tablename__ = "subscription_plan_changes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=False)
    
    # Plan change details
    from_plan_id = Column(UUID(as_uuid=True), ForeignKey("subscription_plans.id"), nullable=False)
    to_plan_id = Column(UUID(as_uuid=True), ForeignKey("subscription_plans.id"), nullable=False)
    change_type = Column(SQLEnum(PlanChangeType), nullable=False)
    
    # Financial details
    proration_credit = Column(Numeric(precision=10, scale=2), default=Decimal("0"))
    immediate_charge = Column(Numeric(precision=10, scale=2), default=Decimal("0"))
    
    # Stripe integration
    stripe_invoice_id = Column(String(255))
    stripe_payment_intent_id = Column(String(255))
    
    # Dates
    effective_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    subscription = relationship("Subscription", back_populates="plan_changes")
    from_plan = relationship("SubscriptionPlan", foreign_keys=[from_plan_id])
    to_plan = relationship("SubscriptionPlan", foreign_keys=[to_plan_id])
    
    @hybrid_property
    def is_upgrade(self) -> bool:
        """Check if this was an upgrade"""
        return self.change_type == PlanChangeType.UPGRADE
    
    @hybrid_property
    def is_downgrade(self) -> bool:
        """Check if this was a downgrade"""
        return self.change_type == PlanChangeType.DOWNGRADE
    
    @hybrid_property
    def net_charge(self) -> Decimal:
        """Net charge after proration"""
        return self.immediate_charge - self.proration_credit
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert plan change to dictionary"""
        return {
            "id": str(self.id),
            "subscription_id": str(self.subscription_id),
            "change_type": self.change_type.value,
            "from_plan": self.from_plan.name if self.from_plan else None,
            "to_plan": self.to_plan.name if self.to_plan else None,
            "proration_credit": float(self.proration_credit),
            "immediate_charge": float(self.immediate_charge),
            "net_charge": float(self.net_charge),
            "effective_date": self.effective_date.isoformat(),
            "created_at": self.created_at.isoformat()
        }


class Invoice(Base):
    """
    Italian invoices with fattura elettronica support.
    
    Compliant with Italian invoice requirements including SDI integration.
    """
    __tablename__ = "invoices"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=False)
    
    # Invoice identification
    invoice_number = Column(String(50), unique=True, nullable=False)
    invoice_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=False)
    
    # Amounts (in euros)
    subtotal = Column(Numeric(precision=10, scale=2), nullable=False)  # Imponibile
    iva_amount = Column(Numeric(precision=10, scale=2), nullable=False)  # IVA 22%
    total_amount = Column(Numeric(precision=10, scale=2), nullable=False)  # Totale
    
    # Payment
    payment_status = Column(String(50), default="pending")  # pending, paid, failed
    paid_at = Column(DateTime)
    
    # Stripe integration
    stripe_invoice_id = Column(String(255), unique=True)
    stripe_payment_intent_id = Column(String(255))
    
    # Electronic invoice (fattura elettronica)
    fattura_elettronica_xml = Column(Text)  # Generated XML
    sdi_transmission_id = Column(String(255))  # SDI transmission reference
    sdi_status = Column(String(50))  # sent, accepted, rejected
    sdi_sent_at = Column(DateTime)
    
    # PDF invoice
    pdf_path = Column(String(500))  # Path to generated PDF
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    subscription = relationship("Subscription", back_populates="invoices")
    
    @hybrid_property
    def is_paid(self) -> bool:
        """Check if invoice is paid"""
        return self.payment_status == "paid"
    
    @hybrid_property
    def is_overdue(self) -> bool:
        """Check if invoice is overdue"""
        return datetime.utcnow() > self.due_date and not self.is_paid
    
    def to_dict(self) -> Dict[str, Any]:
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
            "is_paid": self.is_paid,
            "is_overdue": self.is_overdue,
            "sdi_status": self.sdi_status,
            "created_at": self.created_at.isoformat()
        }