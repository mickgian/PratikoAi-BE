"""Italian Market Subscription API Endpoints.

This module provides REST API endpoints for managing Italian market subscriptions
with support for annual plans (€599), IVA calculations, and electronic invoicing.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.core.database import get_async_session as get_db
from app.core.logging import logger
from app.models.subscription import BillingPeriod, Subscription, SubscriptionPlan
from app.models.user import User
from app.services.invoice_service import ItalianInvoiceService
from app.services.italian_subscription_service import (
    CancellationResult,
    ItalianSubscriptionService,
    PlanChangeResult,
    SubscriptionResult,
)

router = APIRouter(prefix="/italian-subscriptions", tags=["Italian Subscriptions"])


# Request Models


class ItalianCustomerData(BaseModel):
    """Italian customer data for subscription creation"""

    is_business: bool = Field(..., description="True for B2B customers (Partita IVA required)")
    partita_iva: str | None = Field(None, min_length=11, max_length=11, description="11-digit Italian VAT number")
    codice_fiscale: str | None = Field(None, min_length=16, max_length=16, description="16-character Italian tax code")

    # Invoice information
    invoice_name: str = Field(..., min_length=1, max_length=255, description="Company name or full name")
    invoice_address: str = Field(..., min_length=1, max_length=500, description="Street address")
    invoice_cap: str = Field(..., pattern=r"^\d{5}$", description="5-digit Italian postal code")
    invoice_city: str = Field(..., min_length=1, max_length=100, description="City name")
    invoice_province: str = Field(..., min_length=2, max_length=2, description="2-letter province code (e.g., RM, MI)")
    invoice_country: str = Field(default="IT", description="Country code")

    # Electronic invoice fields (for business customers)
    sdi_code: str | None = Field(None, min_length=7, max_length=7, description="SDI destination code")
    pec_email: str | None = Field(None, description="PEC email for electronic invoice")

    @field_validator("partita_iva")
    @classmethod
    def validate_partita_iva_format(cls, v, info):
        # Access other field values via info.data
        if info.data and info.data.get("is_business") and not v:
            raise ValueError("Partita IVA is required for business customers")
        if v and not v.isdigit():
            raise ValueError("Partita IVA must contain only digits")
        return v

    @model_validator(mode="after")
    def validate_business_requirements(self):
        if self.is_business and not self.partita_iva:
            raise ValueError("Partita IVA is required for business customers")
        if not self.is_business and not self.codice_fiscale:
            raise ValueError("Codice Fiscale is required for individual customers")
        if self.is_business and not self.sdi_code and not self.pec_email:
            raise ValueError("Either SDI code or PEC email is required for business customers")
        return self


class CreateSubscriptionRequest(BaseModel):
    """Request to create new subscription"""

    plan_type: str = Field(..., pattern=r"^(monthly|annual)$", description="Subscription plan type")
    payment_method_id: str = Field(..., description="Stripe payment method ID")
    customer_data: ItalianCustomerData
    trial_days: int | None = Field(None, ge=0, le=30, description="Trial period override (0-30 days)")


class ChangePlanRequest(BaseModel):
    """Request to change subscription plan"""

    new_plan_type: str = Field(..., pattern=r"^(monthly|annual)$", description="New plan type")
    prorate: bool = Field(default=True, description="Whether to prorate the change")


class CancelSubscriptionRequest(BaseModel):
    """Request to cancel subscription"""

    immediately: bool = Field(default=False, description="Cancel immediately or at period end")
    reason: str | None = Field(None, max_length=500, description="Cancellation reason")


class ReactivateSubscriptionRequest(BaseModel):
    """Request to reactivate subscription"""

    payment_method_id: str | None = Field(None, description="New payment method ID")


# Response Models


class SubscriptionPlanResponse(BaseModel):
    """Subscription plan response"""

    id: str
    name: str
    description: str
    billing_period: str
    base_price: float
    iva_amount: float
    price_with_iva: float
    monthly_equivalent: float
    annual_savings: float
    discount_percentage: float
    trial_period_days: int
    features: list[str]
    currency: str
    iva_rate: float
    popular: bool | None = None
    savings_message: str | None = None
    monthly_equivalent_message: str | None = None


class SubscriptionResponse(BaseModel):
    """Subscription response"""

    id: str
    user_id: str
    plan: SubscriptionPlanResponse
    status: str
    current_period_start: str | None
    current_period_end: str | None
    trial_end: str | None
    cancel_at_period_end: bool
    is_business: bool
    partita_iva: str | None
    codice_fiscale: str | None
    invoice_name: str
    monthly_revenue: float
    days_until_renewal: int
    is_active: bool
    is_trial: bool
    created_at: str | None


class PlanChangeResponse(BaseModel):
    """Plan change response"""

    success: bool
    subscription: SubscriptionResponse | None
    new_plan: SubscriptionPlanResponse | None
    prorated_charge: float
    credit_applied: float
    message: str


class CancellationResponse(BaseModel):
    """Cancellation response"""

    success: bool
    subscription: SubscriptionResponse | None
    refund_amount: float
    access_until: str | None
    cancel_at_period_end: bool
    message: str


class InvoiceResponse(BaseModel):
    """Invoice response"""

    id: str
    subscription_id: str
    invoice_number: str
    invoice_date: str
    due_date: str
    subtotal: float
    iva_amount: float
    total_amount: float
    payment_status: str
    is_paid: bool
    is_overdue: bool
    sdi_status: str | None
    created_at: str


# API Endpoints


@router.get("/plans", response_model=list[SubscriptionPlanResponse])
async def get_subscription_plans(db: AsyncSession = Depends(get_db)) -> list[SubscriptionPlanResponse]:
    """Get available subscription plans for Italian market.

    Returns both monthly (€69) and annual (€599) plans with Italian pricing,
    IVA calculations, and feature comparisons.
    """
    try:
        service = ItalianSubscriptionService(db)
        plans_data = await service.get_subscription_plans()

        return [SubscriptionPlanResponse(**plan) for plan in plans_data]

    except Exception as e:
        logger.error(f"Error getting subscription plans: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Errore interno del sistema")


@router.post("/create", response_model=SubscriptionResponse)
async def create_subscription(
    request: CreateSubscriptionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionResponse:
    """Create new Italian market subscription.

    Supports both monthly (€69) and annual (€599) plans with:
    - Italian VAT (22% IVA) calculations
    - Partita IVA validation for business customers
    - Codice Fiscale validation for individual customers
    - Electronic invoice (fattura elettronica) preparation
    - 7-day trial period by default
    """
    try:
        service = ItalianSubscriptionService(db)

        # Convert Pydantic model to dict
        invoice_data = request.customer_data.dict()
        invoice_data["user_id"] = str(current_user.id)

        result = await service.create_subscription(
            user_id=str(current_user.id),
            plan_type=request.plan_type,
            payment_method_id=request.payment_method_id,
            invoice_data=invoice_data,
            trial_days=request.trial_days,
        )

        if not result.success:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.error_message)

        return SubscriptionResponse(**result.subscription.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating subscription: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Errore interno del sistema")


@router.get("/current", response_model=Optional[SubscriptionResponse])
async def get_current_subscription(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> SubscriptionResponse | None:
    """Get current user's subscription.

    Returns subscription details including Italian tax information,
    billing period, and renewal dates.
    """
    try:
        service = ItalianSubscriptionService(db)
        subscription = await service._get_user_subscription(str(current_user.id))

        if not subscription:
            return None

        return SubscriptionResponse(**subscription.to_dict())

    except Exception as e:
        logger.error(f"Error getting current subscription: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Errore interno del sistema")


@router.put("/{subscription_id}/change-plan", response_model=PlanChangeResponse)
async def change_subscription_plan(
    subscription_id: UUID,
    request: ChangePlanRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PlanChangeResponse:
    """Change subscription plan with proration.

    Supports upgrading from monthly to annual (€69→€599) or downgrading
    from annual to monthly with proper proration calculations and
    Stripe invoice generation.
    """
    try:
        service = ItalianSubscriptionService(db)

        # Verify subscription belongs to current user
        subscription = await service._get_subscription(str(subscription_id))
        if not subscription or subscription.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Abbonamento non trovato")

        result = await service.change_plan(
            subscription_id=str(subscription_id), new_plan_type=request.new_plan_type, prorate=request.prorate
        )

        if not result.success:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.error_message)

        return PlanChangeResponse(
            success=True,
            subscription=SubscriptionResponse(**result.subscription.to_dict()) if result.subscription else None,
            new_plan=SubscriptionPlanResponse(**result.new_plan.to_dict()) if result.new_plan else None,
            prorated_charge=float(result.prorated_charge),
            credit_applied=float(result.credit_applied),
            message="Piano cambiato con successo",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing plan: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Errore interno del sistema")


@router.delete("/{subscription_id}/cancel", response_model=CancellationResponse)
async def cancel_subscription(
    subscription_id: UUID,
    request: CancelSubscriptionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CancellationResponse:
    """Cancel subscription.

    Supports both immediate cancellation and cancellation at period end.
    No refunds are provided as per Italian market terms.
    """
    try:
        service = ItalianSubscriptionService(db)

        # Verify subscription belongs to current user
        subscription = await service._get_subscription(str(subscription_id))
        if not subscription or subscription.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Abbonamento non trovato")

        result = await service.cancel_subscription(
            subscription_id=str(subscription_id), immediately=request.immediately, reason=request.reason
        )

        if not result.success:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.error_message)

        return CancellationResponse(
            success=True,
            subscription=SubscriptionResponse(**result.subscription.to_dict()) if result.subscription else None,
            refund_amount=float(result.refund_amount),
            access_until=result.access_until.isoformat() if result.access_until else None,
            cancel_at_period_end=result.cancel_at_period_end,
            message="Abbonamento cancellato con successo",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error canceling subscription: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Errore interno del sistema")


@router.post("/{subscription_id}/reactivate", response_model=SubscriptionResponse)
async def reactivate_subscription(
    subscription_id: UUID,
    request: ReactivateSubscriptionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionResponse:
    """Reactivate canceled subscription.

    Creates new Stripe subscription with updated payment method if provided.
    Maintains original Italian tax information and invoice settings.
    """
    try:
        service = ItalianSubscriptionService(db)

        # Verify subscription belongs to current user
        subscription = await service._get_subscription(str(subscription_id))
        if not subscription or subscription.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Abbonamento non trovato")

        result = await service.reactivate_subscription(
            subscription_id=str(subscription_id), payment_method_id=request.payment_method_id
        )

        if not result.success:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.error_message)

        return SubscriptionResponse(**result.subscription.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reactivating subscription: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Errore interno del sistema")


@router.get("/{subscription_id}/invoices", response_model=list[InvoiceResponse])
async def get_subscription_invoices(
    subscription_id: UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[InvoiceResponse]:
    """Get subscription invoices.

    Returns list of invoices with Italian formatting, IVA calculations,
    and electronic invoice (fattura elettronica) status.
    """
    try:
        service = ItalianSubscriptionService(db)

        # Verify subscription belongs to current user
        subscription = await service._get_subscription(str(subscription_id))
        if not subscription or subscription.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Abbonamento non trovato")

        # Get invoices (would need to add this method to the service)
        invoices = subscription.invoices
        return [InvoiceResponse(**invoice.to_dict()) for invoice in invoices]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting invoices: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Errore interno del sistema")


@router.get("/{subscription_id}/invoices/{invoice_id}/pdf")
async def download_invoice_pdf(
    subscription_id: UUID,
    invoice_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Download invoice PDF.

    Returns Italian formatted PDF invoice with proper VAT calculations
    and compliance with Italian invoicing regulations.
    """
    try:
        service = ItalianSubscriptionService(db)
        invoice_service = ItalianInvoiceService(db)

        # Verify subscription belongs to current user
        subscription = await service._get_subscription(str(subscription_id))
        if not subscription or subscription.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Abbonamento non trovato")

        # Find specific invoice
        invoice = None
        for inv in subscription.invoices:
            if str(inv.id) == str(invoice_id):
                invoice = inv
                break

        if not invoice:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fattura non trovata")

        # Generate PDF if not already cached
        invoice_data, pdf_content = await invoice_service.generate_invoice(
            subscription=subscription, payment_amount=invoice.total_amount
        )

        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=fattura_{invoice.invoice_number.replace('/', '_')}.pdf"
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading invoice PDF: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Errore interno del sistema")


@router.get("/{subscription_id}/invoices/{invoice_id}/xml")
async def download_invoice_xml(
    subscription_id: UUID,
    invoice_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Download electronic invoice XML (fattura elettronica).

    Returns XML formatted for SDI (Sistema di Interscambio) transmission.
    Only available for business customers with Partita IVA.
    """
    try:
        service = ItalianSubscriptionService(db)
        invoice_service = ItalianInvoiceService(db)

        # Verify subscription belongs to current user
        subscription = await service._get_subscription(str(subscription_id))
        if not subscription or subscription.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Abbonamento non trovato")

        if not subscription.is_business:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Fattura elettronica disponibile solo per aziende"
            )

        # Find specific invoice
        invoice = None
        for inv in subscription.invoices:
            if str(inv.id) == str(invoice_id):
                invoice = inv
                break

        if not invoice:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fattura non trovata")

        # Generate XML if not already available
        if not invoice.fattura_elettronica_xml:
            xml_content = await invoice_service.generate_fattura_elettronica_xml(
                subscription=subscription, payment_amount=invoice.total_amount, invoice_number=invoice.invoice_number
            )
        else:
            xml_content = invoice.fattura_elettronica_xml

        return Response(
            content=xml_content,
            media_type="application/xml",
            headers={
                "Content-Disposition": f"attachment; filename=fattura_elettronica_{invoice.invoice_number.replace('/', '_')}.xml"
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading invoice XML: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Errore interno del sistema")


@router.post("/validate-partita-iva")
async def validate_partita_iva(partita_iva: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Validate Italian Partita IVA using Luhn algorithm.

    Returns validation result and formatted Partita IVA if valid.
    """
    try:
        service = ItalianSubscriptionService(db)
        is_valid = service.validate_partita_iva(partita_iva)

        return {
            "partita_iva": partita_iva,
            "is_valid": is_valid,
            "formatted": f"IT{partita_iva}" if is_valid else None,
            "message": "Partita IVA valida" if is_valid else "Partita IVA non valida",
        }

    except Exception as e:
        logger.error(f"Error validating Partita IVA: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Errore interno del sistema")


@router.post("/validate-codice-fiscale")
async def validate_codice_fiscale(codice_fiscale: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Validate Italian Codice Fiscale format.

    Returns validation result and normalized Codice Fiscale if valid.
    """
    try:
        service = ItalianSubscriptionService(db)
        is_valid = service.validate_codice_fiscale(codice_fiscale)

        return {
            "codice_fiscale": codice_fiscale,
            "is_valid": is_valid,
            "normalized": codice_fiscale.upper() if is_valid else None,
            "message": "Codice Fiscale valido" if is_valid else "Codice Fiscale non valido",
        }

    except Exception as e:
        logger.error(f"Error validating Codice Fiscale: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Errore interno del sistema")
