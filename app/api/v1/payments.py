"""Payment API endpoints for subscription management."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr

from app.api.v1.auth import get_current_session
from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import logger
from app.models.session import Session
from app.services.stripe_service import stripe_service
from app.models.payment import SubscriptionStatus, PaymentStatus


router = APIRouter()


class CreateCustomerRequest(BaseModel):
    """Request model for creating a customer."""
    email: EmailStr
    name: Optional[str] = None


class CreateCheckoutSessionRequest(BaseModel):
    """Request model for creating checkout session."""
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


@router.post("/customer")
@limiter.limit("5 per minute")
async def create_customer(
    request: Request,
    customer_data: CreateCustomerRequest,
    session: Session = Depends(get_current_session),
):
    """Create a Stripe customer for the user.
    
    Args:
        request: FastAPI request object
        customer_data: Customer creation data
        session: Current user session
        
    Returns:
        Created customer information
    """
    try:
        user_id = session.user_id
        
        customer = await stripe_service.create_customer(
            user_id=user_id,
            email=customer_data.email,
            name=customer_data.name
        )
        
        return JSONResponse({
            "customer_id": customer.stripe_customer_id,
            "email": customer.email,
            "name": customer.name,
            "created_at": customer.created_at.isoformat(),
        })
        
    except Exception as e:
        logger.error(
            "customer_creation_api_failed",
            session_id=session.id,
            email=customer_data.email,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to create customer")


@router.post("/checkout/session")
@limiter.limit("10 per minute")
async def create_checkout_session(
    request: Request,
    checkout_data: CreateCheckoutSessionRequest,
    session: Session = Depends(get_current_session),
):
    """Create a Stripe checkout session for subscription.
    
    Args:
        request: FastAPI request object
        checkout_data: Checkout session configuration
        session: Current user session
        
    Returns:
        Checkout session details
    """
    try:
        user_id = session.user_id
        
        # Get or create customer first
        customer = await stripe_service.create_customer(
            user_id=user_id,
            email=session.user_email or "user@example.com"  # Fallback email
        )
        
        checkout_session = await stripe_service.create_checkout_session(
            user_id=user_id,
            customer_id=customer.stripe_customer_id,
            success_url=checkout_data.success_url,
            cancel_url=checkout_data.cancel_url
        )
        
        return JSONResponse({
            "checkout_session_id": checkout_session["checkout_session_id"],
            "checkout_url": checkout_session["checkout_url"],
            "expires_at": checkout_session["expires_at"],
        })
        
    except Exception as e:
        logger.error(
            "checkout_session_creation_api_failed",
            session_id=session.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@router.get("/subscription")
@limiter.limit("30 per minute")
async def get_user_subscription(
    request: Request,
    session: Session = Depends(get_current_session),
):
    """Get user's current subscription status.
    
    Args:
        request: FastAPI request object
        session: Current user session
        
    Returns:
        Subscription information
    """
    try:
        user_id = session.user_id
        
        subscription = await stripe_service.get_user_subscription(user_id)
        
        if not subscription:
            return JSONResponse({
                "subscription": None,
                "status": "no_subscription",
                "trial_available": True,
            })
        
        # Calculate trial and billing info
        is_trial = subscription.status == SubscriptionStatus.TRIALING
        trial_days_remaining = 0
        if is_trial and subscription.trial_end:
            trial_days_remaining = max(0, (subscription.trial_end - datetime.utcnow()).days)
        
        days_until_renewal = 0
        if subscription.current_period_end:
            days_until_renewal = max(0, (subscription.current_period_end - datetime.utcnow()).days)
        
        return JSONResponse({
            "subscription": {
                "id": subscription.stripe_subscription_id,
                "status": subscription.status.value,
                "plan_type": subscription.plan_type.value,
                "amount_eur": subscription.amount_eur,
                "currency": subscription.currency,
                "current_period_start": subscription.current_period_start.isoformat(),
                "current_period_end": subscription.current_period_end.isoformat(),
                "is_trial": is_trial,
                "trial_days_remaining": trial_days_remaining,
                "days_until_renewal": days_until_renewal,
                "created_at": subscription.created_at.isoformat(),
                "canceled_at": subscription.canceled_at.isoformat() if subscription.canceled_at else None,
            },
            "billing": {
                "next_payment_amount_eur": subscription.amount_eur,
                "next_payment_date": subscription.current_period_end.isoformat(),
                "billing_interval": "month",
            },
            "features": {
                "chat_requests_included": "unlimited",
                "api_cost_limit_eur": 2.00,
                "priority_support": True,
                "advanced_features": True,
            }
        })
        
    except Exception as e:
        logger.error(
            "subscription_retrieval_api_failed",
            session_id=session.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve subscription")


@router.post("/subscription/cancel")
@limiter.limit("5 per minute")
async def cancel_subscription(
    request: Request,
    session: Session = Depends(get_current_session),
):
    """Cancel user's subscription.
    
    Args:
        request: FastAPI request object
        session: Current user session
        
    Returns:
        Cancellation confirmation
    """
    try:
        user_id = session.user_id
        
        # Get user's subscription
        subscription = await stripe_service.get_user_subscription(user_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="No active subscription found")
        
        success = await stripe_service.cancel_subscription(
            subscription_id=subscription.stripe_subscription_id,
            user_id=user_id
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to cancel subscription")
        
        return JSONResponse({
            "success": True,
            "message": "Subscription canceled successfully",
            "canceled_at": datetime.utcnow().isoformat(),
            "access_until": subscription.current_period_end.isoformat(),
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "subscription_cancellation_api_failed",
            session_id=session.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to cancel subscription")


@router.get("/invoices")
@limiter.limit("20 per minute")
async def get_user_invoices(
    request: Request,
    limit: int = 10,
    session: Session = Depends(get_current_session),
):
    """Get user's invoice history.
    
    Args:
        request: FastAPI request object
        limit: Maximum number of invoices to return
        session: Current user session
        
    Returns:
        List of invoices
    """
    try:
        user_id = session.user_id
        
        invoices = await stripe_service.get_user_invoices(user_id, limit)
        
        formatted_invoices = [
            {
                "id": invoice.stripe_invoice_id,
                "invoice_number": invoice.invoice_number,
                "amount_eur": invoice.amount_eur,
                "tax_eur": invoice.tax_eur,
                "total_eur": invoice.total_eur,
                "currency": invoice.currency,
                "status": invoice.status,
                "paid": invoice.paid,
                "period_start": invoice.period_start.isoformat(),
                "period_end": invoice.period_end.isoformat(),
                "created_at": invoice.created_at.isoformat(),
                "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
                "paid_at": invoice.paid_at.isoformat() if invoice.paid_at else None,
                "download_url": invoice.invoice_pdf_url,
                "hosted_url": invoice.hosted_invoice_url,
            }
            for invoice in invoices
        ]
        
        return JSONResponse({
            "invoices": formatted_invoices,
            "total": len(invoices),
        })
        
    except Exception as e:
        logger.error(
            "invoices_retrieval_api_failed",
            session_id=session.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve invoices")


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    payload: bytes = Body(...),
):
    """Handle Stripe webhook events.
    
    Args:
        request: FastAPI request object
        payload: Raw webhook payload
        
    Returns:
        Webhook processing result
    """
    try:
        signature = request.headers.get("stripe-signature")
        if not signature:
            raise HTTPException(status_code=400, detail="Missing Stripe signature")
        
        success = await stripe_service.process_webhook_event(payload, signature)
        
        if success:
            return JSONResponse({"received": True})
        else:
            raise HTTPException(status_code=400, detail="Webhook processing failed")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "stripe_webhook_failed",
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/pricing")
@limiter.limit("50 per minute")
async def get_pricing_info(
    request: Request,
):
    """Get pricing information for the service.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Pricing details
    """
    return JSONResponse({
        "plans": [
            {
                "id": "monthly",
                "name": "NormoAI Professional",
                "price_eur": 69.00,
                "currency": "eur",
                "interval": "month",
                "trial_days": settings.STRIPE_TRIAL_PERIOD_DAYS,
                "features": [
                    "Unlimited chat requests",
                    "Italian tax and legal knowledge base",
                    "Document generation and templates",
                    "GDPR compliant data handling",
                    "Priority support",
                    "Advanced AI models",
                    "Cost optimization (€2 target per user)",
                    "API access",
                    "Invoice generation",
                ],
                "limits": {
                    "api_cost_eur_per_month": 2.00,
                    "chat_requests": "unlimited",
                    "document_generations": "unlimited",
                    "storage_gb": 10,
                },
                "target_audience": "Italian tax/legal professionals",
                "value_proposition": "Specialized AI assistant for Italian regulatory compliance"
            }
        ],
        "trial": {
            "duration_days": settings.STRIPE_TRIAL_PERIOD_DAYS,
            "features_included": "all",
            "no_credit_card_required": False,
        },
        "billing": {
            "accepted_cards": ["visa", "mastercard", "amex"],
            "currencies": ["eur"],
            "tax_handling": "automatic",
            "invoicing": "automatic",
        }
    })


@router.get("/subscription/portal")
@limiter.limit("10 per minute")
async def create_billing_portal_session(
    request: Request,
    session: Session = Depends(get_current_session),
):
    """Create a Stripe billing portal session for subscription management.
    
    Args:
        request: FastAPI request object
        session: Current user session
        
    Returns:
        Billing portal URL
    """
    try:
        user_id = session.user_id
        
        # Get user's customer
        import stripe
        
        # This would need customer lookup logic
        # For now, return a placeholder
        return JSONResponse({
            "portal_url": f"{settings.BASE_URL}/billing/portal",
            "return_url": f"{settings.BASE_URL}/dashboard/billing",
        })
        
    except Exception as e:
        logger.error(
            "billing_portal_creation_failed",
            session_id=session.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to create billing portal session")