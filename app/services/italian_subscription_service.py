"""
Italian Subscription Service with Stripe Integration.

This service handles subscription creation, plan changes, and billing for Italian customers
with support for annual plans (€599), IVA calculations, and Partita IVA/Codice Fiscale validation.
"""

import re
import stripe
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.config import settings
from app.core.logging import logger
from app.models.subscription import (
    Subscription, 
    SubscriptionPlan, 
    SubscriptionPlanChange,
    BillingPeriod, 
    SubscriptionStatus,
    PlanChangeType
)
from app.models.user import User
from app.services.email_service import EmailService
from app.services.cache import get_redis_client


@dataclass
class SubscriptionResult:
    """Result of subscription operation"""
    success: bool
    subscription: Optional[Subscription] = None
    error_message: Optional[str] = None
    stripe_subscription: Optional[stripe.Subscription] = None


@dataclass
class PlanChangeResult:
    """Result of plan change operation"""
    success: bool
    subscription: Optional[Subscription] = None
    new_plan: Optional[SubscriptionPlan] = None
    prorated_charge: Decimal = Decimal("0")
    credit_applied: Decimal = Decimal("0")
    error_message: Optional[str] = None
    stripe_invoice: Optional[stripe.Invoice] = None


@dataclass
class CancellationResult:
    """Result of subscription cancellation"""
    success: bool
    subscription: Optional[Subscription] = None
    refund_amount: Decimal = Decimal("0")
    access_until: Optional[datetime] = None
    cancel_at_period_end: bool = True
    error_message: Optional[str] = None


class ItalianSubscriptionService:
    """
    Service for managing Italian market subscriptions with Stripe integration.
    
    Handles:
    - Subscription creation with Italian tax data validation
    - Plan changes with proper proration
    - Italian invoice requirements
    - Partita IVA and Codice Fiscale validation
    - Electronic invoice (fattura elettronica) preparation
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.stripe = stripe
        self.stripe.api_key = settings.STRIPE_SECRET_KEY
        self.email_service = EmailService()
        self.redis = get_redis_client()
        
        # Italian market configuration
        self.iva_rate = Decimal("22.00")
        self.default_trial_days = 7
        
        # Stripe configuration for Italian market
        self.stripe_config = {
            "italian_tax_rate_id": "txr_italian_iva_22",  # Pre-configured in Stripe
            "default_payment_method_types": ["card", "sepa_debit"],
            "currency": "eur"
        }
    
    async def create_subscription(
        self,
        user_id: str,
        plan_type: str,  # "monthly" or "annual"
        payment_method_id: str,
        invoice_data: Dict[str, Any],
        trial_days: Optional[int] = None
    ) -> SubscriptionResult:
        """
        Create subscription for Italian customer.
        
        Args:
            user_id: User ID
            plan_type: "monthly" or "annual"
            payment_method_id: Stripe payment method ID
            invoice_data: Italian invoice data
            trial_days: Override default trial period
            
        Returns:
            SubscriptionResult with success status and subscription
        """
        try:
            # Get user
            user = await self._get_user(user_id)
            if not user:
                return SubscriptionResult(
                    success=False,
                    error_message="User not found"
                )
            
            # Check if user already has active subscription
            existing_subscription = await self._get_user_subscription(user_id)
            if existing_subscription and existing_subscription.is_active:
                return SubscriptionResult(
                    success=False,
                    error_message="User already has an active subscription"
                )
            
            # Validate Italian tax data
            validation_errors = self._validate_italian_tax_data(invoice_data)
            if validation_errors:
                return SubscriptionResult(
                    success=False,
                    error_message=f"Dati non validi: {', '.join(validation_errors.values())}"
                )
            
            # Get subscription plan
            plan = await self._get_plan_by_type(plan_type)
            if not plan:
                return SubscriptionResult(
                    success=False,
                    error_message=f"Piano {plan_type} non trovato"
                )
            
            # Create Stripe customer if needed
            if not user.stripe_customer_id:
                stripe_customer = await self._create_stripe_customer(user, invoice_data)
                user.stripe_customer_id = stripe_customer.id
                await self.db.commit()
            
            # Create Stripe subscription
            stripe_subscription = await self._create_stripe_subscription(
                customer_id=user.stripe_customer_id,
                plan=plan,
                payment_method_id=payment_method_id,
                trial_days=trial_days or self.default_trial_days,
                invoice_data=invoice_data
            )
            
            # Create database subscription
            subscription = Subscription(
                user_id=user_id,
                plan_id=plan.id,
                stripe_subscription_id=stripe_subscription.id,
                stripe_customer_id=user.stripe_customer_id,
                status=SubscriptionStatus(stripe_subscription.status),
                current_period_start=datetime.fromtimestamp(stripe_subscription.current_period_start),
                current_period_end=datetime.fromtimestamp(stripe_subscription.current_period_end),
                trial_start=datetime.fromtimestamp(stripe_subscription.trial_start) if stripe_subscription.trial_start else None,
                trial_end=datetime.fromtimestamp(stripe_subscription.trial_end) if stripe_subscription.trial_end else None,
                **invoice_data
            )
            
            self.db.add(subscription)
            await self.db.commit()
            await self.db.refresh(subscription)
            
            # Send welcome email
            await self._send_welcome_email(user, subscription)
            
            # Track analytics
            await self._track_subscription_created(subscription)
            
            logger.info(f"Created subscription {subscription.id} for user {user_id}, plan: {plan_type}")
            
            return SubscriptionResult(
                success=True,
                subscription=subscription,
                stripe_subscription=stripe_subscription
            )
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating subscription: {e}")
            return SubscriptionResult(
                success=False,
                error_message=f"Errore di pagamento: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error creating subscription: {e}")
            await self.db.rollback()
            return SubscriptionResult(
                success=False,
                error_message="Errore interno del sistema"
            )
    
    async def change_plan(
        self,
        subscription_id: str,
        new_plan_type: str,
        prorate: bool = True
    ) -> PlanChangeResult:
        """
        Change subscription plan with proration.
        
        Args:
            subscription_id: Subscription ID
            new_plan_type: "monthly" or "annual"
            prorate: Whether to prorate the change
            
        Returns:
            PlanChangeResult with change details
        """
        try:
            # Get subscription
            subscription = await self._get_subscription(subscription_id)
            if not subscription:
                return PlanChangeResult(
                    success=False,
                    error_message="Abbonamento non trovato"
                )
            
            # Get new plan
            new_plan = await self._get_plan_by_type(new_plan_type)
            if not new_plan:
                return PlanChangeResult(
                    success=False,
                    error_message=f"Piano {new_plan_type} non trovato"
                )
            
            # Check if change is allowed
            can_change, reason = subscription.can_change_to_plan(new_plan)
            if not can_change:
                return PlanChangeResult(
                    success=False,
                    error_message=reason
                )
            
            # Calculate proration
            credit_applied = Decimal("0")
            immediate_charge = Decimal("0")
            
            if prorate:
                credit_applied = subscription.calculate_proration_credit()
                immediate_charge = new_plan.base_price - credit_applied
                
                # Ensure charge is not negative for downgrades
                if immediate_charge < 0:
                    credit_applied = new_plan.base_price
                    immediate_charge = Decimal("0")
            else:
                immediate_charge = new_plan.base_price
            
            # Update Stripe subscription
            stripe_subscription = await self._update_stripe_subscription(
                subscription.stripe_subscription_id,
                new_plan,
                prorate
            )
            
            # Record plan change
            change_type = self._determine_change_type(subscription.plan, new_plan)
            plan_change = SubscriptionPlanChange(
                subscription_id=subscription.id,
                from_plan_id=subscription.plan_id,
                to_plan_id=new_plan.id,
                change_type=change_type,
                proration_credit=credit_applied,
                immediate_charge=immediate_charge,
                effective_date=datetime.utcnow()
            )
            
            # Update subscription
            subscription.plan_id = new_plan.id
            subscription.status = SubscriptionStatus(stripe_subscription.status)
            subscription.current_period_start = datetime.fromtimestamp(stripe_subscription.current_period_start)
            subscription.current_period_end = datetime.fromtimestamp(stripe_subscription.current_period_end)
            
            self.db.add(plan_change)
            await self.db.commit()
            await self.db.refresh(subscription)
            
            # Send notification email
            await self._send_plan_change_email(subscription, plan_change)
            
            # Track analytics
            await self._track_plan_changed(subscription, plan_change)
            
            logger.info(f"Changed plan for subscription {subscription_id}: {change_type.value}")
            
            return PlanChangeResult(
                success=True,
                subscription=subscription,
                new_plan=new_plan,
                prorated_charge=immediate_charge,
                credit_applied=credit_applied
            )
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error changing plan: {e}")
            return PlanChangeResult(
                success=False,
                error_message=f"Errore di pagamento: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error changing plan: {e}")
            await self.db.rollback()
            return PlanChangeResult(
                success=False,
                error_message="Errore interno del sistema"
            )
    
    async def cancel_subscription(
        self,
        subscription_id: str,
        immediately: bool = False,
        reason: Optional[str] = None
    ) -> CancellationResult:
        """
        Cancel subscription.
        
        Args:
            subscription_id: Subscription ID
            immediately: Cancel immediately or at period end
            reason: Cancellation reason
            
        Returns:
            CancellationResult with cancellation details
        """
        try:
            subscription = await self._get_subscription(subscription_id)
            if not subscription:
                return CancellationResult(
                    success=False,
                    error_message="Abbonamento non trovato"
                )
            
            if not subscription.is_active:
                return CancellationResult(
                    success=False,
                    error_message="Abbonamento già cancellato"
                )
            
            # Cancel in Stripe
            if immediately:
                stripe_subscription = self.stripe.Subscription.delete(
                    subscription.stripe_subscription_id
                )
                subscription.status = SubscriptionStatus.CANCELED
                subscription.ended_at = datetime.utcnow()
                access_until = datetime.utcnow()
            else:
                stripe_subscription = self.stripe.Subscription.modify(
                    subscription.stripe_subscription_id,
                    cancel_at_period_end=True
                )
                subscription.cancel_at_period_end = True
                subscription.canceled_at = datetime.utcnow()
                access_until = subscription.current_period_end
            
            await self.db.commit()
            
            # Send cancellation email
            await self._send_cancellation_email(subscription, immediately)
            
            # Track analytics
            await self._track_subscription_canceled(subscription, reason)
            
            logger.info(f"Canceled subscription {subscription_id}, immediately: {immediately}")
            
            return CancellationResult(
                success=True,
                subscription=subscription,
                refund_amount=Decimal("0"),  # No refund policy
                access_until=access_until,
                cancel_at_period_end=not immediately
            )
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error canceling subscription: {e}")
            return CancellationResult(
                success=False,
                error_message=f"Errore di pagamento: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error canceling subscription: {e}")
            await self.db.rollback()
            return CancellationResult(
                success=False,
                error_message="Errore interno del sistema"
            )
    
    async def reactivate_subscription(
        self,
        subscription_id: str,
        payment_method_id: Optional[str] = None
    ) -> SubscriptionResult:
        """
        Reactivate canceled subscription.
        
        Args:
            subscription_id: Subscription ID
            payment_method_id: New payment method ID (optional)
            
        Returns:
            SubscriptionResult with reactivated subscription
        """
        try:
            subscription = await self._get_subscription(subscription_id)
            if not subscription:
                return SubscriptionResult(
                    success=False,
                    error_message="Abbonamento non trovato"
                )
            
            # Check if reactivation is possible
            if subscription.status not in [SubscriptionStatus.CANCELED, SubscriptionStatus.UNPAID]:
                return SubscriptionResult(
                    success=False,
                    error_message="Abbonamento non può essere riattivato"
                )
            
            # Update payment method if provided
            if payment_method_id:
                self.stripe.PaymentMethod.attach(
                    payment_method_id,
                    customer=subscription.stripe_customer_id
                )
                self.stripe.Customer.modify(
                    subscription.stripe_customer_id,
                    invoice_settings={'default_payment_method': payment_method_id}
                )
            
            # Create new Stripe subscription
            stripe_subscription = self.stripe.Subscription.create(
                customer=subscription.stripe_customer_id,
                items=[{'price': subscription.plan.stripe_price_id}],
                default_tax_rates=[self.stripe_config["italian_tax_rate_id"]],
                metadata={
                    'user_id': str(subscription.user_id),
                    'reactivated_from': subscription.stripe_subscription_id
                }
            )
            
            # Update subscription
            subscription.stripe_subscription_id = stripe_subscription.id
            subscription.status = SubscriptionStatus(stripe_subscription.status)
            subscription.current_period_start = datetime.fromtimestamp(stripe_subscription.current_period_start)
            subscription.current_period_end = datetime.fromtimestamp(stripe_subscription.current_period_end)
            subscription.cancel_at_period_end = False
            subscription.canceled_at = None
            subscription.ended_at = None
            
            await self.db.commit()
            
            # Send reactivation email
            await self._send_reactivation_email(subscription)
            
            # Track analytics
            await self._track_subscription_reactivated(subscription)
            
            logger.info(f"Reactivated subscription {subscription_id}")
            
            return SubscriptionResult(
                success=True,
                subscription=subscription,
                stripe_subscription=stripe_subscription
            )
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error reactivating subscription: {e}")
            return SubscriptionResult(
                success=False,
                error_message=f"Errore di pagamento: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error reactivating subscription: {e}")
            await self.db.rollback()
            return SubscriptionResult(
                success=False,
                error_message="Errore interno del sistema"
            )
    
    def validate_partita_iva(self, partita_iva: str) -> bool:
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
    
    def validate_codice_fiscale(self, codice_fiscale: str) -> bool:
        """
        Basic validation for Italian tax code (Codice Fiscale).
        
        Args:
            codice_fiscale: 16-character Italian tax code
            
        Returns:
            True if format is valid, False otherwise
        """
        if not codice_fiscale or len(codice_fiscale) != 16:
            return False
        
        # Normalize to uppercase
        codice_fiscale = codice_fiscale.upper()
        
        # Basic pattern check
        pattern = r'^[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]$'
        return bool(re.match(pattern, codice_fiscale))
    
    async def get_subscription_plans(self) -> List[Dict[str, Any]]:
        """Get available subscription plans for Italian market"""
        try:
            stmt = select(SubscriptionPlan).where(SubscriptionPlan.is_active == True)
            result = await self.db.execute(stmt)
            plans = result.scalars().all()
            
            plans_data = []
            for plan in plans:
                plan_data = plan.to_dict()
                
                # Add Italian market specific information
                if plan.billing_period == BillingPeriod.ANNUAL:
                    plan_data.update({
                        "popular": True,
                        "savings_message": f"Risparmi €{plan.annual_savings} all'anno!",
                        "monthly_equivalent_message": f"Solo €{plan.monthly_equivalent:.2f}/mese"
                    })
                
                plans_data.append(plan_data)
            
            return plans_data
            
        except Exception as e:
            logger.error(f"Error getting subscription plans: {e}")
            return []
    
    # Private helper methods
    
    async def _get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _get_subscription(self, subscription_id: str) -> Optional[Subscription]:
        """Get subscription by ID with plan"""
        stmt = select(Subscription).where(Subscription.id == subscription_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _get_user_subscription(self, user_id: str) -> Optional[Subscription]:
        """Get user's current subscription"""
        stmt = select(Subscription).where(
            and_(
                Subscription.user_id == user_id,
                Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING])
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _get_plan_by_type(self, plan_type: str) -> Optional[SubscriptionPlan]:
        """Get plan by billing period type"""
        billing_period = BillingPeriod.ANNUAL if plan_type == "annual" else BillingPeriod.MONTHLY
        stmt = select(SubscriptionPlan).where(
            and_(
                SubscriptionPlan.billing_period == billing_period,
                SubscriptionPlan.is_active == True
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    def _validate_italian_tax_data(self, invoice_data: Dict[str, Any]) -> Dict[str, str]:
        """Validate Italian tax data"""
        errors = {}
        
        is_business = invoice_data.get("is_business", False)
        
        if is_business:
            partita_iva = invoice_data.get("partita_iva")
            if not partita_iva:
                errors["partita_iva"] = "Partita IVA richiesta per aziende"
            elif not self.validate_partita_iva(partita_iva):
                errors["partita_iva"] = "Partita IVA non valida"
            
            # SDI code or PEC required for electronic invoice
            sdi_code = invoice_data.get("sdi_code")
            pec_email = invoice_data.get("pec_email")
            if not sdi_code and not pec_email:
                errors["sdi"] = "Codice destinatario SDI o email PEC richiesti per fattura elettronica"
        else:
            codice_fiscale = invoice_data.get("codice_fiscale")
            if not codice_fiscale:
                errors["codice_fiscale"] = "Codice Fiscale richiesto per privati"
            elif not self.validate_codice_fiscale(codice_fiscale):
                errors["codice_fiscale"] = "Codice Fiscale non valido"
        
        # Common validation
        required_fields = ["invoice_name", "invoice_address", "invoice_cap", "invoice_city", "invoice_province"]
        for field in required_fields:
            if not invoice_data.get(field):
                errors[field] = f"{field.replace('_', ' ').title()} richiesto"
        
        # Validate CAP (Italian postal code)
        invoice_cap = invoice_data.get("invoice_cap", "")
        if invoice_cap and not re.match(r'^\d{5}$', invoice_cap):
            errors["invoice_cap"] = "CAP deve essere 5 cifre"
        
        # Validate province
        invoice_province = invoice_data.get("invoice_province", "")
        if invoice_province and len(invoice_province) != 2:
            errors["invoice_province"] = "Provincia deve essere 2 caratteri (es: RM, MI)"
        
        return errors
    
    async def _create_stripe_customer(self, user: User, invoice_data: Dict[str, Any]) -> stripe.Customer:
        """Create Stripe customer with Italian invoice data"""
        customer_data = {
            "email": user.email,
            "name": invoice_data["invoice_name"],
            "address": {
                "line1": invoice_data["invoice_address"],
                "postal_code": invoice_data["invoice_cap"],
                "city": invoice_data["invoice_city"],
                "state": invoice_data["invoice_province"],
                "country": "IT"
            },
            "metadata": {
                "user_id": str(user.id),
                "is_business": str(invoice_data.get("is_business", False)),
                "partita_iva": invoice_data.get("partita_iva", ""),
                "codice_fiscale": invoice_data.get("codice_fiscale", "")
            }
        }
        
        # Add tax ID for business customers
        if invoice_data.get("is_business") and invoice_data.get("partita_iva"):
            customer_data["tax_ids"] = [
                {
                    "type": "eu_vat",
                    "value": f"IT{invoice_data['partita_iva']}"
                }
            ]
        
        return self.stripe.Customer.create(**customer_data)
    
    async def _create_stripe_subscription(
        self,
        customer_id: str,
        plan: SubscriptionPlan,
        payment_method_id: str,
        trial_days: int,
        invoice_data: Dict[str, Any]
    ) -> stripe.Subscription:
        """Create Stripe subscription"""
        subscription_data = {
            "customer": customer_id,
            "items": [{"price": plan.stripe_price_id}],
            "default_payment_method": payment_method_id,
            "trial_period_days": trial_days,
            "default_tax_rates": [self.stripe_config["italian_tax_rate_id"]],
            "collection_method": "charge_automatically",
            "metadata": {
                "plan_type": plan.billing_period.value,
                "user_id": invoice_data.get("user_id", ""),
                "partita_iva": invoice_data.get("partita_iva", ""),
                "codice_fiscale": invoice_data.get("codice_fiscale", "")
            }
        }
        
        return self.stripe.Subscription.create(**subscription_data)
    
    async def _update_stripe_subscription(
        self,
        stripe_subscription_id: str,
        new_plan: SubscriptionPlan,
        prorate: bool
    ) -> stripe.Subscription:
        """Update Stripe subscription plan"""
        # Get current subscription
        subscription = self.stripe.Subscription.retrieve(stripe_subscription_id)
        
        return self.stripe.Subscription.modify(
            stripe_subscription_id,
            items=[{
                "id": subscription.items.data[0].id,
                "price": new_plan.stripe_price_id
            }],
            proration_behavior="create_prorations" if prorate else "none"
        )
    
    def _determine_change_type(self, old_plan: SubscriptionPlan, new_plan: SubscriptionPlan) -> PlanChangeType:
        """Determine if plan change is upgrade or downgrade"""
        if old_plan.billing_period == BillingPeriod.MONTHLY and new_plan.billing_period == BillingPeriod.ANNUAL:
            return PlanChangeType.UPGRADE
        elif old_plan.billing_period == BillingPeriod.ANNUAL and new_plan.billing_period == BillingPeriod.MONTHLY:
            return PlanChangeType.DOWNGRADE
        else:
            return PlanChangeType.UPGRADE  # Default assumption
    
    # Email notification methods
    
    async def _send_welcome_email(self, user: User, subscription: Subscription):
        """Send welcome email in Italian"""
        template = "subscription_welcome_annual" if subscription.plan.billing_period == BillingPeriod.ANNUAL else "subscription_welcome_monthly"
        
        await self.email_service.send_email(
            to_email=user.email,
            subject=f"Benvenuto in PratikoAI {subscription.plan.name}! 🎉",
            template=template,
            context={
                "user_name": user.name,
                "plan_name": subscription.plan.name,
                "base_price": subscription.plan.base_price,
                "price_with_iva": subscription.plan.price_with_iva,
                "savings": subscription.plan.annual_savings if subscription.plan.billing_period == BillingPeriod.ANNUAL else None,
                "next_billing_date": subscription.current_period_end.strftime("%d/%m/%Y"),
                "trial_end": subscription.trial_end.strftime("%d/%m/%Y") if subscription.trial_end else None
            }
        )
    
    async def _send_plan_change_email(self, subscription: Subscription, plan_change: SubscriptionPlanChange):
        """Send plan change notification email"""
        template = "subscription_plan_changed"
        
        await self.email_service.send_email(
            to_email=subscription.user.email,
            subject="Piano aggiornato con successo!",
            template=template,
            context={
                "user_name": subscription.user.name,
                "old_plan": plan_change.from_plan.name,
                "new_plan": plan_change.to_plan.name,
                "change_type": plan_change.change_type.value,
                "savings": subscription.plan.annual_savings if subscription.plan.billing_period == BillingPeriod.ANNUAL else None,
                "credit_applied": plan_change.proration_credit,
                "immediate_charge": plan_change.immediate_charge
            }
        )
    
    async def _send_cancellation_email(self, subscription: Subscription, immediately: bool):
        """Send cancellation confirmation email"""
        template = "subscription_canceled"
        
        await self.email_service.send_email(
            to_email=subscription.user.email,
            subject="Abbonamento cancellato",
            template=template,
            context={
                "user_name": subscription.user.name,
                "plan_name": subscription.plan.name,
                "immediately": immediately,
                "access_until": subscription.current_period_end.strftime("%d/%m/%Y") if not immediately else None
            }
        )
    
    async def _send_reactivation_email(self, subscription: Subscription):
        """Send reactivation confirmation email"""
        template = "subscription_reactivated"
        
        await self.email_service.send_email(
            to_email=subscription.user.email,
            subject="Abbonamento riattivato!",
            template=template,
            context={
                "user_name": subscription.user.name,
                "plan_name": subscription.plan.name,
                "next_billing_date": subscription.current_period_end.strftime("%d/%m/%Y")
            }
        )
    
    # Analytics tracking methods
    
    async def _track_subscription_created(self, subscription: Subscription):
        """Track subscription creation for analytics"""
        event_data = {
            "event": "subscription_created",
            "user_id": str(subscription.user_id),
            "plan_type": subscription.plan.billing_period.value,
            "plan_price": float(subscription.plan.base_price),
            "is_business": subscription.is_business,
            "trial_days": (subscription.trial_end - subscription.trial_start).days if subscription.trial_end else 0,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Store in Redis for analytics processing
        await self.redis.lpush("analytics_events", json.dumps(event_data))
    
    async def _track_plan_changed(self, subscription: Subscription, plan_change: SubscriptionPlanChange):
        """Track plan change for analytics"""
        event_data = {
            "event": "plan_changed",
            "user_id": str(subscription.user_id),
            "subscription_id": str(subscription.id),
            "change_type": plan_change.change_type.value,
            "from_plan": plan_change.from_plan.billing_period.value,
            "to_plan": plan_change.to_plan.billing_period.value,
            "credit_applied": float(plan_change.proration_credit),
            "immediate_charge": float(plan_change.immediate_charge),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.redis.lpush("analytics_events", json.dumps(event_data))
    
    async def _track_subscription_canceled(self, subscription: Subscription, reason: Optional[str]):
        """Track subscription cancellation for analytics"""
        event_data = {
            "event": "subscription_canceled",
            "user_id": str(subscription.user_id),
            "subscription_id": str(subscription.id),
            "plan_type": subscription.plan.billing_period.value,
            "reason": reason,
            "days_active": (datetime.utcnow() - subscription.created_at).days,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.redis.lpush("analytics_events", json.dumps(event_data))
    
    async def _track_subscription_reactivated(self, subscription: Subscription):
        """Track subscription reactivation for analytics"""
        event_data = {
            "event": "subscription_reactivated",
            "user_id": str(subscription.user_id),
            "subscription_id": str(subscription.id),
            "plan_type": subscription.plan.billing_period.value,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.redis.lpush("analytics_events", json.dumps(event_data))