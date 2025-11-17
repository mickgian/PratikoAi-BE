"""Payment and subscription schemas."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field

from app.models.payment import PaymentStatus, PlanType, SubscriptionStatus


class CustomerResponse(BaseModel):
    """Customer response schema."""

    customer_id: str
    email: str
    name: str | None = None
    created_at: datetime


class CheckoutSessionResponse(BaseModel):
    """Checkout session response schema."""

    checkout_session_id: str
    checkout_url: str
    expires_at: int


class SubscriptionInfo(BaseModel):
    """Subscription information schema."""

    id: str
    status: SubscriptionStatus
    plan_type: PlanType
    amount_eur: float
    currency: str = "eur"
    current_period_start: datetime
    current_period_end: datetime
    is_trial: bool = False
    trial_days_remaining: int = 0
    days_until_renewal: int = 0
    created_at: datetime
    canceled_at: datetime | None = None


class BillingInfo(BaseModel):
    """Billing information schema."""

    next_payment_amount_eur: float
    next_payment_date: datetime
    billing_interval: str = "month"


class SubscriptionFeatures(BaseModel):
    """Subscription features schema."""

    chat_requests_included: str = "unlimited"
    api_cost_limit_eur: float = 2.00
    priority_support: bool = True
    advanced_features: bool = True


class SubscriptionResponse(BaseModel):
    """Complete subscription response schema."""

    subscription: SubscriptionInfo | None = None
    status: str
    trial_available: bool = True
    billing: BillingInfo | None = None
    features: SubscriptionFeatures | None = None


class InvoiceInfo(BaseModel):
    """Invoice information schema."""

    id: str
    invoice_number: str
    amount_eur: float
    tax_eur: float
    total_eur: float
    currency: str = "eur"
    status: str
    paid: bool
    period_start: datetime
    period_end: datetime
    created_at: datetime
    due_date: datetime | None = None
    paid_at: datetime | None = None
    download_url: str | None = None
    hosted_url: str | None = None


class InvoicesResponse(BaseModel):
    """Invoices list response schema."""

    invoices: list[InvoiceInfo]
    total: int


class PaymentInfo(BaseModel):
    """Payment information schema."""

    id: str
    amount_eur: float
    currency: str = "eur"
    status: PaymentStatus
    payment_method_type: str | None = None
    payment_method_last4: str | None = None
    payment_method_brand: str | None = None
    created_at: datetime
    paid_at: datetime | None = None
    failed_at: datetime | None = None
    failure_reason: str | None = None


class PlanLimits(BaseModel):
    """Plan limits schema."""

    api_cost_eur_per_month: float
    chat_requests: str
    document_generations: str
    storage_gb: int


class PricingPlan(BaseModel):
    """Pricing plan schema."""

    id: str
    name: str
    price_eur: float
    currency: str = "eur"
    interval: str = "month"
    trial_days: int = 7
    features: list[str]
    limits: PlanLimits
    target_audience: str
    value_proposition: str


class TrialInfo(BaseModel):
    """Trial information schema."""

    duration_days: int
    features_included: str = "all"
    no_credit_card_required: bool = False


class BillingSettings(BaseModel):
    """Billing settings schema."""

    accepted_cards: list[str]
    currencies: list[str]
    tax_handling: str = "automatic"
    invoicing: str = "automatic"


class PricingResponse(BaseModel):
    """Pricing information response schema."""

    plans: list[PricingPlan]
    trial: TrialInfo
    billing: BillingSettings


class CancellationResponse(BaseModel):
    """Subscription cancellation response schema."""

    success: bool
    message: str
    canceled_at: datetime
    access_until: datetime


class BillingPortalResponse(BaseModel):
    """Billing portal response schema."""

    portal_url: str
    return_url: str


class WebhookResponse(BaseModel):
    """Webhook response schema."""

    received: bool


class CreateCustomerRequest(BaseModel):
    """Create customer request schema."""

    email: EmailStr
    name: str | None = None


class CreateCheckoutSessionRequest(BaseModel):
    """Create checkout session request schema."""

    success_url: str | None = None
    cancel_url: str | None = None


class SubscriptionAnalytics(BaseModel):
    """Subscription analytics schema."""

    active_subscriptions: int
    trial_subscriptions: int
    canceled_subscriptions: int
    monthly_recurring_revenue_eur: float
    average_revenue_per_user_eur: float
    churn_rate_percentage: float
    trial_conversion_rate_percentage: float


class PaymentAnalytics(BaseModel):
    """Payment analytics schema."""

    total_payments: int
    successful_payments: int
    failed_payments: int
    total_revenue_eur: float
    average_payment_amount_eur: float
    payment_failure_rate_percentage: float


class RevenueBreakdown(BaseModel):
    """Revenue breakdown schema."""

    monthly_subscriptions_eur: float
    yearly_subscriptions_eur: float
    one_time_payments_eur: float
    refunds_eur: float
    net_revenue_eur: float


class BillingAnalytics(BaseModel):
    """Complete billing analytics schema."""

    subscription_analytics: SubscriptionAnalytics
    payment_analytics: PaymentAnalytics
    revenue_breakdown: RevenueBreakdown
    period: dict[str, Any]


class SubscriptionUsage(BaseModel):
    """Subscription usage tracking schema."""

    user_id: str
    subscription_id: str
    period_start: datetime
    period_end: datetime
    api_requests: int
    api_cost_eur: float
    chat_messages: int
    document_generations: int
    storage_used_gb: float
    overage_charges_eur: float = 0.0


class UsageAlert(BaseModel):
    """Usage alert schema."""

    alert_type: str  # "usage_limit", "cost_limit", "storage_limit"
    threshold_percentage: float
    current_usage: float
    limit: float
    recommendation: str
