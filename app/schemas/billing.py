"""Billing schemas for usage-based billing API (DEV-257).

Request and response schemas for billing endpoints.
All user-facing text in Italian.
"""

from datetime import datetime

from pydantic import BaseModel, Field

# --- Request Schemas ---


class CreditRechargeRequest(BaseModel):
    """Request to recharge credits."""

    amount_eur: int = Field(description="Importo ricarica in EUR (5, 10, 25, 50, 100)")


class EnableExtraUsageRequest(BaseModel):
    """Request to toggle extra usage via credits."""

    enabled: bool = Field(description="Abilita consumo crediti oltre il limite")


class SubscribePlanRequest(BaseModel):
    """Request to subscribe to a billing plan."""

    success_url: str | None = None
    cancel_url: str | None = None


class UpgradePlanRequest(BaseModel):
    """Request to upgrade billing plan."""

    new_plan_slug: str = Field(description="Slug del nuovo piano (base, pro, premium)")


# --- Response Schemas ---


class WindowInfoSchema(BaseModel):
    """Info about a single rolling window."""

    window_type: str
    current_cost_eur: float
    limit_cost_eur: float
    usage_percentage: float
    reset_at: datetime | None = None
    reset_in_minutes: int | None = None


class CreditInfoSchema(BaseModel):
    """Credit balance and status."""

    balance_eur: float
    extra_usage_enabled: bool


class UsageStatusResponse(BaseModel):
    """Current usage status across all windows."""

    plan_slug: str
    plan_name: str
    window_5h: WindowInfoSchema
    window_7d: WindowInfoSchema
    credits: CreditInfoSchema
    is_admin: bool = False
    message_it: str = ""


class BillingPlanSchema(BaseModel):
    """Billing plan info for display."""

    slug: str
    name: str
    price_eur_monthly: float
    monthly_cost_limit_eur: float
    window_5h_cost_limit_eur: float
    window_7d_cost_limit_eur: float
    credit_markup_factor: float
    markup_percentage: int = Field(description="Markup as percentage (e.g., 50 for 1.5x)")

    @classmethod
    def from_plan(cls, plan) -> "BillingPlanSchema":
        return cls(
            slug=plan.slug,
            name=plan.name,
            price_eur_monthly=plan.price_eur_monthly,
            monthly_cost_limit_eur=plan.monthly_cost_limit_eur,
            window_5h_cost_limit_eur=plan.window_5h_cost_limit_eur,
            window_7d_cost_limit_eur=plan.window_7d_cost_limit_eur,
            credit_markup_factor=plan.credit_markup_factor,
            markup_percentage=int((plan.credit_markup_factor - 1) * 100),
        )


class CreditTransactionSchema(BaseModel):
    """Credit transaction record."""

    id: int
    transaction_type: str
    amount_eur: float
    balance_after_eur: float
    description: str | None
    created_at: datetime


class CreditBalanceResponse(BaseModel):
    """Credit balance response."""

    balance_eur: float
    extra_usage_enabled: bool


class TransactionHistoryResponse(BaseModel):
    """Credit transaction history."""

    transactions: list[CreditTransactionSchema]
    total: int


class PlansListResponse(BaseModel):
    """List of available billing plans."""

    plans: list[BillingPlanSchema]


class PlanSubscribedResponse(BaseModel):
    """Response after subscribing/upgrading."""

    success: bool
    plan: BillingPlanSchema
    message_it: str


# --- Admin Simulator Schemas ---


class SimulateUsageRequest(BaseModel):
    """Request to simulate usage at a target percentage."""

    window_type: str = Field(description="Tipo finestra: '5h' o '7d'")
    target_percentage: float = Field(ge=0, le=110)


class SimulateUsageResponse(BaseModel):
    """Response after simulating usage."""

    success: bool
    window_type: str
    target_percentage: float
    simulated_cost_eur: float
    limit_cost_eur: float
    message_it: str


class ResetUsageResponse(BaseModel):
    """Response after resetting all usage."""

    success: bool
    windows_cleared: int
    redis_keys_cleared: int
    message_it: str
