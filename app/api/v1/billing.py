"""Billing API endpoints (DEV-257).

Usage-based billing with rolling windows, credits, and plan management.
All user-facing messages in Italian.
"""

from datetime import UTC, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.v1.auth import get_current_user
from app.core.logging import logger
from app.models.billing import UserCredit, WindowType
from app.models.user import User, UserRole
from app.schemas.billing import (
    BillingPlanSchema,
    CreditBalanceResponse,
    CreditInfoSchema,
    CreditRechargeRequest,
    CreditTransactionSchema,
    EnableExtraUsageRequest,
    PlansListResponse,
    PlanSubscribedResponse,
    ResetUsageResponse,
    SimulateUsageRequest,
    SimulateUsageResponse,
    TransactionHistoryResponse,
    UpgradePlanRequest,
    UsageStatusResponse,
    WindowInfoSchema,
)
from app.services.billing_plan_service import billing_plan_service
from app.services.rolling_window_service import rolling_window_service
from app.services.usage_credit_service import usage_credit_service

router = APIRouter()


def _minutes_until(dt: datetime | None) -> int | None:
    """Compute minutes from now until a future datetime."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    delta = (dt - datetime.now(UTC)).total_seconds()
    return max(0, int(delta / 60))


async def _get_credit_info(user_id: int) -> tuple[bool, float]:
    """Get credit enabled status and balance for a user."""
    from app.services.database import database_service

    async with database_service.get_db() as db:
        query = select(UserCredit).where(UserCredit.user_id == user_id)
        result = await db.execute(query)
        credit = result.scalar_one_or_none()
        if credit is None:
            return False, 0.0
        return credit.extra_usage_enabled, credit.balance_eur


@router.get("/usage", response_model=UsageStatusResponse)
async def get_usage_status(
    user: User = Depends(get_current_user),
) -> UsageStatusResponse:
    """Get current usage status across rolling windows."""
    try:
        user_id = user.id
        plan = await billing_plan_service.get_user_plan(user_id)
        usage = await rolling_window_service.get_current_usage(user_id)
        extra_enabled, balance = await _get_credit_info(user_id)

        reset_5h = await rolling_window_service.get_reset_time(user_id, WindowType.FIVE_HOUR)
        reset_7d = await rolling_window_service.get_reset_time(user_id, WindowType.SEVEN_DAY)

        pct_5h = (usage.cost_5h_eur / plan.window_5h_cost_limit_eur * 100) if plan.window_5h_cost_limit_eur > 0 else 0
        pct_7d = (usage.cost_7d_eur / plan.window_7d_cost_limit_eur * 100) if plan.window_7d_cost_limit_eur > 0 else 0

        # Generate Italian message
        max_pct = max(pct_5h, pct_7d)
        if max_pct >= 100:
            message = "Limite di utilizzo raggiunto. Ricarica crediti o attendi il reset."
        elif max_pct >= 80:
            message = "Stai per raggiungere il limite di utilizzo."
        else:
            message = "Utilizzo nella norma."

        return UsageStatusResponse(
            plan_slug=plan.slug,
            plan_name=plan.name,
            window_5h=WindowInfoSchema(
                window_type="5h",
                current_cost_eur=round(usage.cost_5h_eur, 4),
                limit_cost_eur=plan.window_5h_cost_limit_eur,
                usage_percentage=round(min(pct_5h, 100), 1),
                reset_at=reset_5h,
                reset_in_minutes=_minutes_until(reset_5h),
            ),
            window_7d=WindowInfoSchema(
                window_type="7d",
                current_cost_eur=round(usage.cost_7d_eur, 4),
                limit_cost_eur=plan.window_7d_cost_limit_eur,
                usage_percentage=round(min(pct_7d, 100), 1),
                reset_at=reset_7d,
                reset_in_minutes=_minutes_until(reset_7d),
            ),
            credits=CreditInfoSchema(balance_eur=balance, extra_usage_enabled=extra_enabled),
            is_admin=user.role in [UserRole.SUPER_USER.value, UserRole.ADMIN.value],
            message_it=message,
        )
    except Exception as e:
        logger.error("billing_usage_status_failed", user_id=user.id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Errore interno nel calcolo dello stato di utilizzo.")


@router.get("/credits/balance", response_model=CreditBalanceResponse)
async def get_credit_balance(
    user: User = Depends(get_current_user),
) -> CreditBalanceResponse:
    """Get user's credit balance."""
    extra_enabled, balance = await _get_credit_info(user.id)
    return CreditBalanceResponse(balance_eur=balance, extra_usage_enabled=extra_enabled)


@router.post("/credits/recharge", response_model=CreditBalanceResponse)
async def recharge_credits(
    request: CreditRechargeRequest,
    user: User = Depends(get_current_user),
) -> CreditBalanceResponse:
    """Recharge credits with a fixed amount."""
    try:
        new_balance = await usage_credit_service.recharge(user_id=user.id, amount_eur=request.amount_eur)
        return CreditBalanceResponse(balance_eur=new_balance, extra_usage_enabled=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/credits/enable-extra-usage")
async def enable_extra_usage(
    request: EnableExtraUsageRequest,
    user: User = Depends(get_current_user),
) -> dict:
    """Toggle credit consumption when limit is reached."""
    await usage_credit_service.enable_extra_usage(user_id=user.id, enabled=request.enabled)
    return {"success": True, "extra_usage_enabled": request.enabled}


@router.get("/credits/transactions", response_model=TransactionHistoryResponse)
async def get_credit_transactions(
    limit: int = 50,
    offset: int = 0,
    user: User = Depends(get_current_user),
) -> TransactionHistoryResponse:
    """Get credit transaction history."""
    transactions = await usage_credit_service.get_transaction_history(user_id=user.id, limit=limit, offset=offset)
    return TransactionHistoryResponse(
        transactions=[
            CreditTransactionSchema(
                id=tx.id,
                transaction_type=tx.transaction_type,
                amount_eur=tx.amount_eur,
                balance_after_eur=tx.balance_after_eur,
                description=tx.description,
                created_at=tx.created_at,
            )
            for tx in transactions
        ],
        total=len(transactions),
    )


@router.get("/plans", response_model=PlansListResponse)
async def get_plans() -> PlansListResponse:
    """Get available billing plans (public endpoint)."""
    plans = await billing_plan_service.get_plans()
    return PlansListResponse(plans=[BillingPlanSchema.from_plan(p) for p in plans])


@router.post("/plans/{plan_slug}/subscribe", response_model=PlanSubscribedResponse)
async def subscribe_plan(
    plan_slug: str,
    user: User = Depends(get_current_user),
) -> PlanSubscribedResponse:
    """Subscribe to a billing plan."""
    try:
        plan = await billing_plan_service.subscribe(user_id=user.id, plan_slug=plan_slug)
        return PlanSubscribedResponse(
            success=True,
            plan=BillingPlanSchema.from_plan(plan),
            message_it=f"Iscrizione al piano {plan.name} completata.",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/plans/upgrade", response_model=PlanSubscribedResponse)
async def upgrade_plan(
    request: UpgradePlanRequest,
    user: User = Depends(get_current_user),
) -> PlanSubscribedResponse:
    """Upgrade to a different billing plan."""
    try:
        plan = await billing_plan_service.upgrade_plan(user_id=user.id, new_plan_slug=request.new_plan_slug)
        return PlanSubscribedResponse(
            success=True,
            plan=BillingPlanSchema.from_plan(plan),
            message_it=f"Upgrade al piano {plan.name} completato.",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- Admin simulator endpoints ---


def _require_super_user(user: User) -> None:
    """Validate user has SUPER_USER or ADMIN role.

    Args:
        user: Authenticated user

    Raises:
        HTTPException: 403 if user lacks required role
    """
    if user.role not in [UserRole.SUPER_USER.value, UserRole.ADMIN.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accesso non autorizzato",
        )


@router.post("/simulate-usage", response_model=SimulateUsageResponse)
async def simulate_usage(
    request: SimulateUsageRequest,
    user: User = Depends(get_current_user),
) -> SimulateUsageResponse:
    """Simulate usage at a target percentage (admin only)."""
    _require_super_user(user)

    plan = await billing_plan_service.get_user_plan(user.id)

    if request.window_type == "5h":
        limit = plan.window_5h_cost_limit_eur
        window = WindowType.FIVE_HOUR
    elif request.window_type == "7d":
        limit = plan.window_7d_cost_limit_eur
        window = WindowType.SEVEN_DAY
    else:
        raise HTTPException(status_code=400, detail="window_type deve essere '5h' o '7d'")

    target_cost = request.target_percentage / 100.0 * limit
    await rolling_window_service.replace_usage_for_window(user.id, window, target_cost)

    logger.info(
        "usage_simulated",
        user_id=user.id,
        window_type=request.window_type,
        target_percentage=request.target_percentage,
        simulated_cost_eur=round(target_cost, 4),
    )

    return SimulateUsageResponse(
        success=True,
        window_type=request.window_type,
        target_percentage=request.target_percentage,
        simulated_cost_eur=round(target_cost, 4),
        limit_cost_eur=limit,
        message_it=f"Utilizzo simulato al {request.target_percentage:.0f}% della finestra {request.window_type}.",
    )


@router.post("/reset-usage", response_model=ResetUsageResponse)
async def reset_usage(
    user: User = Depends(get_current_user),
) -> ResetUsageResponse:
    """Reset all usage to zero (admin only)."""
    _require_super_user(user)

    pg_deleted, redis_deleted = await rolling_window_service.clear_usage(user.id)

    logger.info(
        "usage_reset",
        user_id=user.id,
        pg_deleted=pg_deleted,
        redis_deleted=redis_deleted,
    )

    return ResetUsageResponse(
        success=True,
        windows_cleared=pg_deleted,
        redis_keys_cleared=redis_deleted,
        message_it="Utilizzo azzerato con successo.",
    )
