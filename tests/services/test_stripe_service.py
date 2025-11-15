"""Tests for Stripe payment service."""

from datetime import datetime, timedelta
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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
from app.services.stripe_service import StripeService, stripe_service


@pytest.fixture
def mock_stripe_customer():
    """Mock Stripe customer object."""
    customer = MagicMock()
    customer.id = "cus_test123"
    customer.email = "test@normoai.it"
    customer.name = "Test User"
    customer.metadata = {"user_id": "test_user_123", "source": "normoai"}
    return customer


@pytest.fixture
def mock_stripe_subscription():
    """Mock Stripe subscription object."""
    subscription = MagicMock()
    subscription.id = "sub_test123"
    subscription.customer = "cus_test123"
    subscription.status = "trialing"
    subscription.items.data[0].price.id = "price_test123"
    subscription.items.data[0].price.unit_amount = 6900  # €69.00 in cents
    subscription.items.data[0].price.currency = "eur"
    subscription.current_period_start = 1706515200  # timestamp
    subscription.current_period_end = 1709193600  # timestamp
    subscription.trial_start = 1706515200
    subscription.trial_end = 1707120000
    subscription.created = 1706515200
    subscription.canceled_at = None
    subscription.ended_at = None
    subscription.metadata = {"user_id": "test_user_123", "plan_type": "monthly"}
    return subscription


@pytest.fixture
def mock_stripe_payment_intent():
    """Mock Stripe payment intent object."""
    payment_intent = MagicMock()
    payment_intent.id = "pi_test123"
    payment_intent.amount = 6900  # €69.00 in cents
    payment_intent.currency = "eur"
    payment_intent.status = "succeeded"
    payment_intent.payment_method = "pm_test123"
    payment_intent.created = 1706515200
    payment_intent.metadata = {"user_id": "test_user_123"}
    payment_intent.invoice = "in_test123"
    return payment_intent


@pytest.fixture
def mock_stripe_invoice():
    """Mock Stripe invoice object."""
    invoice = MagicMock()
    invoice.id = "in_test123"
    invoice.subscription = "sub_test123"
    invoice.number = "INV-001"
    invoice.amount_due = 6900  # €69.00 in cents
    invoice.tax = 0
    invoice.total = 6900
    invoice.currency = "eur"
    invoice.status = "paid"
    invoice.paid = True
    invoice.period_start = 1706515200
    invoice.period_end = 1709193600
    invoice.created = 1706515200
    invoice.due_date = 1709193600
    invoice.status_transitions.paid_at = 1706515200
    invoice.invoice_pdf = "https://stripe.com/invoice.pdf"
    invoice.hosted_invoice_url = "https://stripe.com/invoice"
    invoice.metadata = {"user_id": "test_user_123"}
    return invoice


class TestStripeService:
    """Test cases for the Stripe service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = StripeService()

    @pytest.mark.asyncio
    @patch("app.services.stripe_service.database_service")
    @patch("stripe.Customer.create")
    async def test_create_customer_new(self, mock_stripe_create, mock_db, mock_stripe_customer):
        """Test creating a new customer."""
        # Mock database - no existing customer
        mock_db.get_db.return_value.__aenter__.return_value.execute.return_value.scalar_one_or_none.return_value = None
        mock_db.get_db.return_value.__aenter__.return_value.add = MagicMock()
        mock_db.get_db.return_value.__aenter__.return_value.commit = AsyncMock()
        mock_db.get_db.return_value.__aenter__.return_value.refresh = AsyncMock()

        # Mock Stripe customer creation
        mock_stripe_create.return_value = mock_stripe_customer

        await self.service.create_customer(user_id="test_user_123", email="test@normoai.it", name="Test User")

        # Verify Stripe API call
        mock_stripe_create.assert_called_once_with(
            email="test@normoai.it", name="Test User", metadata={"user_id": "test_user_123", "source": "normoai"}
        )

        # Verify database operations
        mock_db.get_db.return_value.__aenter__.return_value.add.assert_called_once()
        mock_db.get_db.return_value.__aenter__.return_value.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.stripe_service.database_service")
    async def test_create_customer_existing(self, mock_db):
        """Test returning existing customer."""
        # Mock existing customer
        existing_customer = Customer(
            user_id="test_user_123", stripe_customer_id="cus_test123", email="test@normoai.it"
        )
        mock_db.get_db.return_value.__aenter__.return_value.execute.return_value.scalar_one_or_none.return_value = (
            existing_customer
        )

        result = await self.service.create_customer(user_id="test_user_123", email="test@normoai.it")

        assert result == existing_customer

    @pytest.mark.asyncio
    @patch("app.services.stripe_service.database_service")
    @patch("stripe.checkout.Session.create")
    async def test_create_checkout_session(self, mock_stripe_create, mock_db):
        """Test creating checkout session."""
        # Mock checkout session
        checkout_session = MagicMock()
        checkout_session.id = "cs_test123"
        checkout_session.url = "https://checkout.stripe.com/test"
        checkout_session.expires_at = 1706601600
        mock_stripe_create.return_value = checkout_session

        result = await self.service.create_checkout_session(user_id="test_user_123", customer_id="cus_test123")

        assert result["checkout_session_id"] == "cs_test123"
        assert result["checkout_url"] == "https://checkout.stripe.com/test"
        assert result["expires_at"] == 1706601600

    @pytest.mark.asyncio
    @patch("app.services.stripe_service.database_service")
    async def test_retrieve_subscription(self, mock_db):
        """Test retrieving subscription by Stripe ID."""
        # Mock subscription
        subscription = Subscription(
            user_id="test_user_123",
            stripe_subscription_id="sub_test123",
            stripe_customer_id="cus_test123",
            stripe_price_id="price_test123",
            amount_eur=69.00,
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=30),
        )
        mock_db.get_db.return_value.__aenter__.return_value.execute.return_value.scalar_one_or_none.return_value = (
            subscription
        )

        result = await self.service.retrieve_subscription("sub_test123")

        assert result == subscription

    @pytest.mark.asyncio
    @patch("app.services.stripe_service.database_service")
    async def test_create_subscription_from_stripe(self, mock_db, mock_stripe_subscription):
        """Test creating subscription from Stripe object."""
        mock_db.get_db.return_value.__aenter__.return_value.add = MagicMock()
        mock_db.get_db.return_value.__aenter__.return_value.commit = AsyncMock()
        mock_db.get_db.return_value.__aenter__.return_value.refresh = AsyncMock()

        result = await self.service.create_subscription_from_stripe(mock_stripe_subscription)

        assert result.stripe_subscription_id == "sub_test123"
        assert result.status == SubscriptionStatus.TRIALING
        assert result.amount_eur == 69.00
        assert result.plan_type == PlanType.MONTHLY

    @pytest.mark.asyncio
    @patch("app.services.stripe_service.database_service")
    async def test_update_subscription_from_stripe(self, mock_db, mock_stripe_subscription):
        """Test updating subscription from Stripe object."""
        # Mock existing subscription
        existing_subscription = Subscription(
            user_id="test_user_123",
            stripe_subscription_id="sub_test123",
            stripe_customer_id="cus_test123",
            stripe_price_id="price_test123",
            amount_eur=69.00,
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=30),
        )
        mock_db.get_db.return_value.__aenter__.return_value.execute.return_value.scalar_one_or_none.return_value = (
            existing_subscription
        )
        mock_db.get_db.return_value.__aenter__.return_value.commit = AsyncMock()
        mock_db.get_db.return_value.__aenter__.return_value.refresh = AsyncMock()

        result = await self.service.update_subscription_from_stripe(mock_stripe_subscription)

        assert result.status == SubscriptionStatus.TRIALING

    @pytest.mark.asyncio
    @patch("app.services.stripe_service.database_service")
    @patch("stripe.Subscription.cancel")
    async def test_cancel_subscription(self, mock_stripe_cancel, mock_db):
        """Test canceling subscription."""
        # Mock existing subscription
        subscription = Subscription(
            user_id="test_user_123",
            stripe_subscription_id="sub_test123",
            stripe_customer_id="cus_test123",
            stripe_price_id="price_test123",
            amount_eur=69.00,
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=30),
        )

        with patch.object(self.service, "retrieve_subscription", return_value=subscription):
            mock_db.get_db.return_value.__aenter__.return_value.commit = AsyncMock()

            result = await self.service.cancel_subscription("sub_test123", "test_user_123")

            assert result is True
            mock_stripe_cancel.assert_called_once_with("sub_test123")

    @pytest.mark.asyncio
    @patch("app.services.stripe_service.database_service")
    @patch("stripe.PaymentMethod.retrieve")
    async def test_create_payment_from_stripe(self, mock_payment_method, mock_db, mock_stripe_payment_intent):
        """Test creating payment from Stripe payment intent."""
        # Mock payment method
        payment_method = MagicMock()
        payment_method.type = "card"
        payment_method.card.last4 = "4242"
        payment_method.card.brand = "visa"
        mock_payment_method.return_value = payment_method

        mock_db.get_db.return_value.__aenter__.return_value.add = MagicMock()
        mock_db.get_db.return_value.__aenter__.return_value.commit = AsyncMock()
        mock_db.get_db.return_value.__aenter__.return_value.refresh = AsyncMock()

        result = await self.service.create_payment_from_stripe(mock_stripe_payment_intent)

        assert result.stripe_payment_intent_id == "pi_test123"
        assert result.amount_eur == 69.00
        assert result.status == PaymentStatus.SUCCEEDED
        assert result.payment_method_last4 == "4242"

    @pytest.mark.asyncio
    @patch("app.services.stripe_service.database_service")
    async def test_create_invoice_from_stripe(self, mock_db, mock_stripe_invoice):
        """Test creating invoice from Stripe invoice."""
        mock_db.get_db.return_value.__aenter__.return_value.add = MagicMock()
        mock_db.get_db.return_value.__aenter__.return_value.commit = AsyncMock()
        mock_db.get_db.return_value.__aenter__.return_value.refresh = AsyncMock()

        result = await self.service.create_invoice_from_stripe(mock_stripe_invoice)

        assert result.stripe_invoice_id == "in_test123"
        assert result.amount_eur == 69.00
        assert result.paid is True

    @pytest.mark.asyncio
    @patch("app.services.stripe_service.database_service")
    @patch("stripe.Webhook.construct_event")
    async def test_process_webhook_event(self, mock_construct_event, mock_db):
        """Test processing webhook event."""
        # Mock webhook event
        event = {
            "id": "evt_test123",
            "type": "customer.subscription.created",
            "data": {"object": {"id": "sub_test123", "status": "trialing"}},
        }
        mock_construct_event.return_value = event

        # Mock no existing event
        mock_db.get_db.return_value.__aenter__.return_value.execute.return_value.scalar_one_or_none.return_value = None
        mock_db.get_db.return_value.__aenter__.return_value.add = MagicMock()
        mock_db.get_db.return_value.__aenter__.return_value.commit = AsyncMock()
        mock_db.get_db.return_value.__aenter__.return_value.refresh = AsyncMock()

        with patch.object(self.service, "_handle_webhook_event", return_value=True):
            result = await self.service.process_webhook_event(b"payload", "signature")

            assert result is True

    @pytest.mark.asyncio
    @patch("app.services.stripe_service.database_service")
    async def test_get_user_subscription(self, mock_db):
        """Test getting user's active subscription."""
        subscription = Subscription(
            user_id="test_user_123",
            stripe_subscription_id="sub_test123",
            stripe_customer_id="cus_test123",
            stripe_price_id="price_test123",
            status=SubscriptionStatus.ACTIVE,
            amount_eur=69.00,
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=30),
        )
        mock_db.get_db.return_value.__aenter__.return_value.execute.return_value.first.return_value = subscription

        result = await self.service.get_user_subscription("test_user_123")

        assert result == subscription

    @pytest.mark.asyncio
    @patch("app.services.stripe_service.database_service")
    async def test_get_user_invoices(self, mock_db):
        """Test getting user's invoice history."""
        invoices = [
            Invoice(
                user_id="test_user_123",
                stripe_invoice_id="in_test123",
                invoice_number="INV-001",
                amount_eur=69.00,
                total_eur=69.00,
                status="paid",
                paid=True,
                period_start=datetime.utcnow(),
                period_end=datetime.utcnow() + timedelta(days=30),
                created_at=datetime.utcnow(),
            )
        ]
        mock_db.get_db.return_value.__aenter__.return_value.execute.return_value.scalars.return_value.all.return_value = invoices

        result = await self.service.get_user_invoices("test_user_123")

        assert len(result) == 1
        assert result[0].stripe_invoice_id == "in_test123"

    def test_global_stripe_service_instance(self):
        """Test that global stripe service instance is available."""
        assert stripe_service is not None
        assert isinstance(stripe_service, StripeService)

    @pytest.mark.asyncio
    async def test_webhook_event_handling_subscription_created(self):
        """Test handling subscription.created webhook event."""
        event = {
            "id": "evt_test123",
            "type": "customer.subscription.created",
            "data": {
                "object": {
                    "id": "sub_test123",
                    "customer": "cus_test123",
                    "status": "trialing",
                    "items": {"data": [{"price": {"id": "price_test123", "unit_amount": 6900, "currency": "eur"}}]},
                    "current_period_start": 1706515200,
                    "current_period_end": 1709193600,
                    "trial_start": 1706515200,
                    "trial_end": 1707120000,
                    "created": 1706515200,
                    "canceled_at": None,
                    "ended_at": None,
                    "metadata": {"user_id": "test_user_123", "plan_type": "monthly"},
                }
            },
        }

        with patch.object(self.service, "create_subscription_from_stripe", return_value=True):
            result = await self.service._handle_webhook_event(event)
            assert result is True

    @pytest.mark.asyncio
    async def test_error_handling_customer_creation(self):
        """Test error handling in customer creation."""
        with patch("stripe.Customer.create", side_effect=Exception("Stripe error")):
            with pytest.raises(Exception) as exc_info:
                await self.service.create_customer(user_id="test_user_123", email="test@normoai.it")
            assert "Failed to create customer" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_unauthorized_subscription_cancellation(self):
        """Test unauthorized subscription cancellation."""
        subscription = Subscription(
            user_id="other_user",  # Different user
            stripe_subscription_id="sub_test123",
            stripe_customer_id="cus_test123",
            stripe_price_id="price_test123",
            amount_eur=69.00,
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=30),
        )

        with patch.object(self.service, "retrieve_subscription", return_value=subscription):
            result = await self.service.cancel_subscription("sub_test123", "test_user_123")
            assert result is False
