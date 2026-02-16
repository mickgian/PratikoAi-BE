"""Stripe payment service for subscription management."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import stripe
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.core.config import settings
from app.core.logging import logger
from app.core.monitoring.metrics import track_trial_conversion, update_monthly_revenue, update_subscription_metrics
from app.models.payment import (
    Customer,
    Invoice,
    Payment,
    PaymentStatus,
    PlanType,
    Subscription,
    SubscriptionStatus,
    WebhookEvent,
)
from app.services.database import database_service


class StripeService:
    """Service for handling Stripe payment operations."""

    def __init__(self):
        """Initialize Stripe service with API key."""
        stripe.api_key = settings.STRIPE_SECRET_KEY
        self.webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    async def create_customer(self, user_id: str, email: str, name: str | None = None) -> Customer:
        """Create a new Stripe customer and store in database.

        Args:
            user_id: User ID from session
            email: Customer email
            name: Optional customer name

        Returns:
            Customer: Created customer record

        Raises:
            Exception: If customer creation fails
        """
        try:
            # Check if customer already exists
            async with database_service.get_db() as db:
                query = select(Customer).where(Customer.user_id == user_id)
                result = await db.execute(query)
                existing_customer = result.scalar_one_or_none()

                if existing_customer:
                    return existing_customer

            # Create customer in Stripe
            stripe_customer = stripe.Customer.create(
                email=email, name=name, metadata={"user_id": user_id, "source": "normoai"}
            )

            # Create customer record in database
            customer = Customer(user_id=user_id, stripe_customer_id=stripe_customer.id, email=email, name=name)

            async with database_service.get_db() as db:
                db.add(customer)
                await db.commit()
                await db.refresh(customer)

            logger.info("stripe_customer_created", user_id=user_id, stripe_customer_id=stripe_customer.id, email=email)

            return customer

        except Exception as e:
            logger.error("stripe_customer_creation_failed", user_id=user_id, email=email, error=str(e), exc_info=True)
            raise Exception(f"Failed to create customer: {str(e)}")

    async def create_checkout_session(
        self, user_id: str, customer_id: str, success_url: str | None = None, cancel_url: str | None = None
    ) -> dict[str, Any]:
        """Create a Stripe checkout session for subscription.

        Args:
            user_id: User ID from session
            customer_id: Stripe customer ID
            success_url: Custom success URL
            cancel_url: Custom cancel URL

        Returns:
            Dict containing checkout session details

        Raises:
            Exception: If checkout session creation fails
        """
        try:
            # Use configured URLs if not provided
            success_url = success_url or settings.STRIPE_SUCCESS_URL
            cancel_url = cancel_url or settings.STRIPE_CANCEL_URL

            # Create checkout session
            checkout_session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                mode="subscription",
                line_items=[
                    {
                        "price": settings.STRIPE_MONTHLY_PRICE_ID,
                        "quantity": 1,
                    }
                ],
                success_url=f"{success_url}?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=cancel_url,
                metadata={
                    "user_id": user_id,
                },
                subscription_data={
                    "trial_period_days": settings.STRIPE_TRIAL_PERIOD_DAYS,
                    "metadata": {
                        "user_id": user_id,
                        "plan_type": PlanType.MONTHLY.value,
                    },
                },
                customer_update={"address": "auto", "name": "auto"},
                tax_id_collection={"enabled": True},
                automatic_tax={"enabled": True},
            )

            logger.info(
                "stripe_checkout_session_created",
                user_id=user_id,
                customer_id=customer_id,
                session_id=checkout_session.id,
            )

            return {
                "checkout_session_id": checkout_session.id,
                "checkout_url": checkout_session.url,
                "expires_at": checkout_session.expires_at,
            }

        except Exception as e:
            logger.error(
                "stripe_checkout_session_creation_failed",
                user_id=user_id,
                customer_id=customer_id,
                error=str(e),
                exc_info=True,
            )
            raise Exception(f"Failed to create checkout session: {str(e)}")

    async def retrieve_subscription(self, subscription_id: str) -> Subscription | None:
        """Retrieve subscription from database by Stripe ID.

        Args:
            subscription_id: Stripe subscription ID

        Returns:
            Subscription record if found
        """
        try:
            async with database_service.get_db() as db:
                query = select(Subscription).where(Subscription.stripe_subscription_id == subscription_id)
                result = await db.execute(query)
                return result.scalar_one_or_none()

        except Exception as e:
            logger.error("subscription_retrieval_failed", subscription_id=subscription_id, error=str(e))
            return None

    async def create_subscription_from_stripe(self, stripe_subscription: Any) -> Subscription:
        """Create subscription record from Stripe subscription object.

        Args:
            stripe_subscription: Stripe subscription object

        Returns:
            Created subscription record
        """
        try:
            # Calculate trial dates
            trial_start = None
            trial_end = None
            if stripe_subscription.trial_start and stripe_subscription.trial_end:
                trial_start = datetime.fromtimestamp(stripe_subscription.trial_start)
                trial_end = datetime.fromtimestamp(stripe_subscription.trial_end)

            subscription = Subscription(
                user_id=stripe_subscription.metadata.get("user_id", ""),
                stripe_subscription_id=stripe_subscription.id,
                stripe_customer_id=stripe_subscription.customer,
                stripe_price_id=stripe_subscription.items.data[0].price.id,
                status=SubscriptionStatus(stripe_subscription.status),
                plan_type=PlanType(stripe_subscription.metadata.get("plan_type", PlanType.MONTHLY.value)),
                amount_eur=stripe_subscription.items.data[0].price.unit_amount / 100,  # Convert from cents
                currency=stripe_subscription.items.data[0].price.currency,
                current_period_start=datetime.fromtimestamp(stripe_subscription.current_period_start),
                current_period_end=datetime.fromtimestamp(stripe_subscription.current_period_end),
                trial_start=trial_start,
                trial_end=trial_end,
                created_at=datetime.fromtimestamp(stripe_subscription.created),
                metadata=dict(stripe_subscription.metadata) if stripe_subscription.metadata else {},
            )

            async with database_service.get_db() as db:
                db.add(subscription)
                await db.commit()
                await db.refresh(subscription)

            logger.info(
                "subscription_created_from_stripe",
                user_id=subscription.user_id,
                stripe_subscription_id=subscription.stripe_subscription_id,
                status=subscription.status.value,
            )

            return subscription

        except IntegrityError:
            # Subscription already exists, retrieve it
            return await self.retrieve_subscription(stripe_subscription.id)
        except Exception as e:
            logger.error(
                "subscription_creation_from_stripe_failed",
                stripe_subscription_id=stripe_subscription.id,
                error=str(e),
                exc_info=True,
            )
            raise Exception(f"Failed to create subscription from Stripe: {str(e)}")

    async def update_subscription_from_stripe(self, stripe_subscription: Any) -> Subscription | None:
        """Update existing subscription from Stripe data.

        Args:
            stripe_subscription: Stripe subscription object

        Returns:
            Updated subscription record
        """
        try:
            async with database_service.get_db() as db:
                query = select(Subscription).where(Subscription.stripe_subscription_id == stripe_subscription.id)
                result = await db.execute(query)
                subscription = result.scalar_one_or_none()

                if not subscription:
                    logger.warning("subscription_not_found_for_update", stripe_subscription_id=stripe_subscription.id)
                    return None

                # Update subscription fields
                subscription.status = SubscriptionStatus(stripe_subscription.status)
                subscription.current_period_start = datetime.fromtimestamp(stripe_subscription.current_period_start)
                subscription.current_period_end = datetime.fromtimestamp(stripe_subscription.current_period_end)
                subscription.updated_at = datetime.utcnow()

                # Handle cancellation
                if stripe_subscription.canceled_at:
                    subscription.canceled_at = datetime.fromtimestamp(stripe_subscription.canceled_at)

                # Handle end
                if stripe_subscription.ended_at:
                    subscription.ended_at = datetime.fromtimestamp(stripe_subscription.ended_at)

                await db.commit()
                await db.refresh(subscription)

                logger.info(
                    "subscription_updated_from_stripe",
                    user_id=subscription.user_id,
                    stripe_subscription_id=subscription.stripe_subscription_id,
                    status=subscription.status.value,
                )

                return subscription

        except Exception as e:
            logger.error(
                "subscription_update_from_stripe_failed",
                stripe_subscription_id=stripe_subscription.id,
                error=str(e),
                exc_info=True,
            )
            return None

    async def cancel_subscription(self, subscription_id: str, user_id: str) -> bool:
        """Cancel a user's subscription.

        Args:
            subscription_id: Stripe subscription ID
            user_id: User ID for validation

        Returns:
            True if cancellation successful
        """
        try:
            # Verify subscription belongs to user
            subscription = await self.retrieve_subscription(subscription_id)
            if not subscription or subscription.user_id != user_id:
                logger.warning(
                    "subscription_cancellation_unauthorized", subscription_id=subscription_id, user_id=user_id
                )
                return False

            # Cancel in Stripe
            stripe.Subscription.cancel(subscription_id)

            # Update local record
            async with database_service.get_db() as db:
                subscription.status = SubscriptionStatus.CANCELED
                subscription.canceled_at = datetime.utcnow()
                subscription.updated_at = datetime.utcnow()
                await db.commit()

            logger.info("subscription_canceled", subscription_id=subscription_id, user_id=user_id)

            return True

        except Exception as e:
            logger.error(
                "subscription_cancellation_failed",
                subscription_id=subscription_id,
                user_id=user_id,
                error=str(e),
                exc_info=True,
            )
            return False

    async def create_payment_from_stripe(self, stripe_payment_intent: Any) -> Payment:
        """Create payment record from Stripe payment intent.

        Args:
            stripe_payment_intent: Stripe payment intent object

        Returns:
            Created payment record
        """
        try:
            # Get payment method details
            payment_method = None
            if stripe_payment_intent.payment_method:
                payment_method = stripe.PaymentMethod.retrieve(stripe_payment_intent.payment_method)

            payment = Payment(
                user_id=stripe_payment_intent.metadata.get("user_id", ""),
                stripe_payment_intent_id=stripe_payment_intent.id,
                stripe_invoice_id=stripe_payment_intent.invoice if hasattr(stripe_payment_intent, "invoice") else None,
                amount_eur=stripe_payment_intent.amount / 100,  # Convert from cents
                currency=stripe_payment_intent.currency,
                status=PaymentStatus(stripe_payment_intent.status),
                payment_method_type=payment_method.type if payment_method else None,
                payment_method_last4=payment_method.card.last4
                if payment_method and payment_method.type == "card"
                else None,
                payment_method_brand=payment_method.card.brand
                if payment_method and payment_method.type == "card"
                else None,
                created_at=datetime.fromtimestamp(stripe_payment_intent.created),
                metadata=dict(stripe_payment_intent.metadata) if stripe_payment_intent.metadata else {},
            )

            # Set payment completion time
            if stripe_payment_intent.status == "succeeded":
                payment.paid_at = datetime.utcnow()
            elif stripe_payment_intent.status == "failed":
                payment.failed_at = datetime.utcnow()
                if hasattr(stripe_payment_intent, "last_payment_error") and stripe_payment_intent.last_payment_error:
                    payment.failure_reason = stripe_payment_intent.last_payment_error.message
                    payment.failure_code = stripe_payment_intent.last_payment_error.code

            async with database_service.get_db() as db:
                db.add(payment)
                await db.commit()
                await db.refresh(payment)

            logger.info(
                "payment_created_from_stripe",
                user_id=payment.user_id,
                stripe_payment_intent_id=payment.stripe_payment_intent_id,
                status=payment.status.value,
                amount_eur=payment.amount_eur,
            )

            return payment

        except Exception as e:
            logger.error(
                "payment_creation_from_stripe_failed",
                stripe_payment_intent_id=stripe_payment_intent.id,
                error=str(e),
                exc_info=True,
            )
            raise Exception(f"Failed to create payment from Stripe: {str(e)}")

    async def create_invoice_from_stripe(self, stripe_invoice: Any) -> Invoice:
        """Create invoice record from Stripe invoice.

        Args:
            stripe_invoice: Stripe invoice object

        Returns:
            Created invoice record
        """
        try:
            invoice = Invoice(
                user_id=stripe_invoice.metadata.get("user_id", ""),
                stripe_invoice_id=stripe_invoice.id,
                stripe_subscription_id=stripe_invoice.subscription,
                invoice_number=stripe_invoice.number or f"INV-{stripe_invoice.id}",
                amount_eur=stripe_invoice.amount_due / 100,  # Convert from cents
                tax_eur=stripe_invoice.tax / 100 if stripe_invoice.tax else 0.0,
                total_eur=stripe_invoice.total / 100,
                currency=stripe_invoice.currency,
                status=stripe_invoice.status,
                paid=stripe_invoice.paid,
                period_start=datetime.fromtimestamp(stripe_invoice.period_start),
                period_end=datetime.fromtimestamp(stripe_invoice.period_end),
                created_at=datetime.fromtimestamp(stripe_invoice.created),
                due_date=datetime.fromtimestamp(stripe_invoice.due_date) if stripe_invoice.due_date else None,
                paid_at=datetime.fromtimestamp(stripe_invoice.status_transitions.paid_at)
                if stripe_invoice.status_transitions.paid_at
                else None,
                invoice_pdf_url=stripe_invoice.invoice_pdf,
                hosted_invoice_url=stripe_invoice.hosted_invoice_url,
                metadata=dict(stripe_invoice.metadata) if stripe_invoice.metadata else {},
            )

            async with database_service.get_db() as db:
                db.add(invoice)
                await db.commit()
                await db.refresh(invoice)

            logger.info(
                "invoice_created_from_stripe",
                user_id=invoice.user_id,
                stripe_invoice_id=invoice.stripe_invoice_id,
                amount_eur=invoice.amount_eur,
            )

            return invoice

        except Exception as e:
            logger.error(
                "invoice_creation_from_stripe_failed", stripe_invoice_id=stripe_invoice.id, error=str(e), exc_info=True
            )
            raise Exception(f"Failed to create invoice from Stripe: {str(e)}")

    async def process_webhook_event(self, payload: bytes, signature: str) -> bool:
        """Process Stripe webhook event.

        Args:
            payload: Raw webhook payload
            signature: Stripe signature header

        Returns:
            True if event processed successfully
        """
        try:
            # Verify webhook signature
            event = stripe.Webhook.construct_event(payload, signature, self.webhook_secret)

            # Check if event already processed
            async with database_service.get_db() as db:
                query = select(WebhookEvent).where(WebhookEvent.stripe_event_id == event["id"])
                result = await db.execute(query)
                existing_event = result.scalar_one_or_none()

                if existing_event and existing_event.processed:
                    logger.info("webhook_event_already_processed", event_id=event["id"], event_type=event["type"])
                    return True

                # Create or update webhook event record
                if not existing_event:
                    webhook_event = WebhookEvent(
                        stripe_event_id=event["id"], event_type=event["type"], event_data=event["data"]
                    )
                    db.add(webhook_event)
                    await db.commit()
                    await db.refresh(webhook_event)
                else:
                    webhook_event = existing_event

            # Process event based on type
            success = await self._handle_webhook_event(event)

            # Update webhook event status
            async with database_service.get_db() as db:
                webhook_event.processed = success
                webhook_event.processed_at = datetime.utcnow()
                if not success:
                    webhook_event.error_count += 1
                    webhook_event.last_error = "Event processing failed"
                    webhook_event.last_error_at = datetime.utcnow()
                await db.commit()

            return success

        except stripe.error.SignatureVerificationError:
            logger.error("webhook_signature_verification_failed")
            return False
        except Exception as e:
            logger.error("webhook_event_processing_failed", error=str(e), exc_info=True)
            return False

    async def _handle_webhook_event(self, event: dict[str, Any]) -> bool:
        """Handle specific webhook event types.

        Args:
            event: Stripe event data

        Returns:
            True if handled successfully
        """
        try:
            event_type = event["type"]
            event_data = event["data"]["object"]

            if event_type == "customer.subscription.created":
                await self.create_subscription_from_stripe(event_data)

            elif event_type in ["customer.subscription.updated", "customer.subscription.deleted"]:
                await self.update_subscription_from_stripe(event_data)

            elif event_type == "invoice.payment_succeeded":
                # Create invoice and payment records
                await self.create_invoice_from_stripe(event_data)
                if event_data.payment_intent:
                    payment_intent = stripe.PaymentIntent.retrieve(event_data.payment_intent)
                    await self.create_payment_from_stripe(payment_intent)

            elif event_type == "invoice.payment_failed":
                await self.create_invoice_from_stripe(event_data)

            elif event_type == "payment_intent.succeeded":
                await self.create_payment_from_stripe(event_data)

            elif event_type == "checkout.session.completed":
                # DEV-257: Handle credit recharge checkout completion
                metadata = event_data.get("metadata", {})
                if metadata.get("type") == "credit_recharge":
                    await self._handle_credit_recharge(event_data, metadata)

            else:
                logger.info("webhook_event_not_handled", event_type=event_type, event_id=event["id"])

            return True

        except Exception as e:
            logger.error(
                "webhook_event_handling_failed",
                event_type=event.get("type"),
                event_id=event.get("id"),
                error=str(e),
                exc_info=True,
            )
            return False

    async def _handle_credit_recharge(self, session_data: dict, metadata: dict) -> None:
        """Handle credit recharge checkout completion (DEV-257).

        Args:
            session_data: Stripe checkout session data
            metadata: Session metadata with user_id and amount
        """
        try:
            from app.services.usage_credit_service import usage_credit_service

            user_id = int(metadata["user_id"])
            amount_eur = int(metadata["amount_eur"])
            payment_intent_id = session_data.get("payment_intent")

            await usage_credit_service.recharge(
                user_id=user_id,
                amount_eur=amount_eur,
                stripe_payment_intent_id=payment_intent_id,
            )

            logger.info(
                "credit_recharge_completed",
                user_id=user_id,
                amount_eur=amount_eur,
                payment_intent_id=payment_intent_id,
            )
        except Exception as e:
            logger.error(
                "credit_recharge_failed",
                error=str(e),
                metadata=metadata,
            )

    async def get_user_subscription(self, user_id: str) -> Subscription | None:
        """Get user's active subscription.

        Args:
            user_id: User ID from session

        Returns:
            Active subscription if found
        """
        try:
            async with database_service.get_db() as db:
                query = (
                    select(Subscription)
                    .where(
                        Subscription.user_id == user_id,
                        Subscription.status.in_(
                            [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING, SubscriptionStatus.PAST_DUE]
                        ),
                    )
                    .order_by(Subscription.created_at.desc())
                )

                result = await db.execute(query)
                return result.first()

        except Exception as e:
            logger.error("user_subscription_retrieval_failed", user_id=user_id, error=str(e))
            return None

    async def get_user_invoices(self, user_id: str, limit: int = 10) -> list[Invoice]:
        """Get user's invoice history.

        Args:
            user_id: User ID from session
            limit: Maximum number of invoices to return

        Returns:
            List of invoices
        """
        try:
            async with database_service.get_db() as db:
                query = (
                    select(Invoice).where(Invoice.user_id == user_id).order_by(Invoice.created_at.desc()).limit(limit)
                )

                result = await db.execute(query)
                return result.scalars().all()

        except Exception as e:
            logger.error("user_invoices_retrieval_failed", user_id=user_id, error=str(e))
            return []

    async def update_business_metrics(self):
        """Update Prometheus metrics for business performance."""
        try:
            async with database_service.get_db() as db:
                # Count active subscriptions by status
                active_query = select(Subscription).where(Subscription.status == SubscriptionStatus.ACTIVE)
                active_result = await db.execute(active_query)
                active_subscriptions = len(active_result.scalars().all())

                trial_query = select(Subscription).where(Subscription.status == SubscriptionStatus.TRIALING)
                trial_result = await db.execute(trial_query)
                trial_subscriptions = len(trial_result.scalars().all())

                cancelled_query = select(Subscription).where(Subscription.status == SubscriptionStatus.CANCELLED)
                cancelled_result = await db.execute(cancelled_query)
                cancelled_subscriptions = len(cancelled_result.scalars().all())

                # Update subscription metrics
                update_subscription_metrics("monthly", "active", active_subscriptions)
                update_subscription_metrics("monthly", "trial", trial_subscriptions)
                update_subscription_metrics("monthly", "cancelled", cancelled_subscriptions)

                # Calculate monthly revenue (€69 per active subscription)
                monthly_revenue_eur = active_subscriptions * 69.0
                update_monthly_revenue(monthly_revenue_eur)

                logger.info(
                    "business_metrics_updated",
                    active_subscriptions=active_subscriptions,
                    trial_subscriptions=trial_subscriptions,
                    cancelled_subscriptions=cancelled_subscriptions,
                    monthly_revenue_eur=monthly_revenue_eur,
                )

        except Exception as e:
            logger.error("business_metrics_update_failed", error=str(e))


# Global instance
stripe_service = StripeService()
