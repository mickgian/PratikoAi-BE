"""Tests for payment and subscription models."""

from datetime import UTC, datetime, timedelta

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


class TestSubscriptionStatus:
    """Test SubscriptionStatus enum."""

    def test_subscription_status_values(self):
        """Test that subscription statuses have correct values."""
        assert SubscriptionStatus.ACTIVE.value == "active"
        assert SubscriptionStatus.INACTIVE.value == "inactive"
        assert SubscriptionStatus.PAST_DUE.value == "past_due"
        assert SubscriptionStatus.CANCELED.value == "canceled"
        assert SubscriptionStatus.UNPAID.value == "unpaid"
        assert SubscriptionStatus.INCOMPLETE.value == "incomplete"
        assert SubscriptionStatus.INCOMPLETE_EXPIRED.value == "incomplete_expired"
        assert SubscriptionStatus.TRIALING.value == "trialing"

    def test_subscription_status_enum_members(self):
        """Test that all expected subscription statuses exist."""
        expected = {
            "ACTIVE",
            "INACTIVE",
            "PAST_DUE",
            "CANCELED",
            "UNPAID",
            "INCOMPLETE",
            "INCOMPLETE_EXPIRED",
            "TRIALING",
        }
        actual = {member.name for member in SubscriptionStatus}
        assert actual == expected


class TestPaymentStatus:
    """Test PaymentStatus enum."""

    def test_payment_status_values(self):
        """Test that payment statuses have correct values."""
        assert PaymentStatus.PENDING.value == "pending"
        assert PaymentStatus.SUCCEEDED.value == "succeeded"
        assert PaymentStatus.FAILED.value == "failed"
        assert PaymentStatus.CANCELED.value == "canceled"
        assert PaymentStatus.REFUNDED.value == "refunded"

    def test_payment_status_enum_members(self):
        """Test that all expected payment statuses exist."""
        expected = {"PENDING", "SUCCEEDED", "FAILED", "CANCELED", "REFUNDED"}
        actual = {member.name for member in PaymentStatus}
        assert actual == expected


class TestPlanType:
    """Test PlanType enum."""

    def test_plan_type_values(self):
        """Test that plan types have correct values."""
        assert PlanType.TRIAL.value == "trial"
        assert PlanType.MONTHLY.value == "monthly"
        assert PlanType.YEARLY.value == "yearly"
        assert PlanType.ENTERPRISE.value == "enterprise"

    def test_plan_type_enum_members(self):
        """Test that all expected plan types exist."""
        expected = {"TRIAL", "MONTHLY", "YEARLY", "ENTERPRISE"}
        actual = {member.name for member in PlanType}
        assert actual == expected


class TestSubscription:
    """Test Subscription model."""

    def test_create_subscription_minimal(self):
        """Test creating subscription with required fields."""
        period_start = datetime.now(UTC)
        period_end = period_start + timedelta(days=30)

        subscription = Subscription(
            user_id="user_123",
            stripe_subscription_id="sub_abc123",
            stripe_customer_id="cus_xyz789",
            stripe_price_id="price_monthly",
            amount_eur=2.00,
            current_period_start=period_start,
            current_period_end=period_end,
        )

        assert subscription.user_id == "user_123"
        assert subscription.stripe_subscription_id == "sub_abc123"
        assert subscription.stripe_customer_id == "cus_xyz789"
        assert subscription.stripe_price_id == "price_monthly"
        assert subscription.amount_eur == 2.00
        assert subscription.currency == "eur"
        assert subscription.status == SubscriptionStatus.INACTIVE
        assert subscription.plan_type == PlanType.MONTHLY
        assert subscription.trial_start is None
        assert subscription.trial_end is None
        assert subscription.canceled_at is None
        assert subscription.ended_at is None

    def test_create_subscription_with_trial(self):
        """Test creating subscription with trial period."""
        trial_start = datetime.now(UTC)
        trial_end = trial_start + timedelta(days=14)
        period_start = trial_start
        period_end = trial_end + timedelta(days=30)

        subscription = Subscription(
            user_id="user_123",
            stripe_subscription_id="sub_abc123",
            stripe_customer_id="cus_xyz789",
            stripe_price_id="price_monthly",
            amount_eur=2.00,
            current_period_start=period_start,
            current_period_end=period_end,
            status=SubscriptionStatus.TRIALING,
            trial_start=trial_start,
            trial_end=trial_end,
        )

        assert subscription.status == SubscriptionStatus.TRIALING
        assert subscription.trial_start == trial_start
        assert subscription.trial_end == trial_end

    def test_create_subscription_yearly(self):
        """Test creating yearly subscription."""
        period_start = datetime.now(UTC)
        period_end = period_start + timedelta(days=365)

        subscription = Subscription(
            user_id="user_123",
            stripe_subscription_id="sub_abc123",
            stripe_customer_id="cus_xyz789",
            stripe_price_id="price_yearly",
            amount_eur=20.00,
            plan_type=PlanType.YEARLY,
            current_period_start=period_start,
            current_period_end=period_end,
            status=SubscriptionStatus.ACTIVE,
        )

        assert subscription.plan_type == PlanType.YEARLY
        assert subscription.amount_eur == 20.00
        assert subscription.status == SubscriptionStatus.ACTIVE

    def test_subscription_canceled(self):
        """Test canceled subscription."""
        period_start = datetime.now(UTC)
        period_end = period_start + timedelta(days=30)
        canceled_at = datetime.now(UTC)

        subscription = Subscription(
            user_id="user_123",
            stripe_subscription_id="sub_abc123",
            stripe_customer_id="cus_xyz789",
            stripe_price_id="price_monthly",
            amount_eur=2.00,
            current_period_start=period_start,
            current_period_end=period_end,
            status=SubscriptionStatus.CANCELED,
            canceled_at=canceled_at,
        )

        assert subscription.status == SubscriptionStatus.CANCELED
        assert subscription.canceled_at == canceled_at


class TestPayment:
    """Test Payment model."""

    def test_create_payment_minimal(self):
        """Test creating payment with required fields."""
        payment = Payment(
            user_id="user_123",
            stripe_payment_intent_id="pi_abc123",
            amount_eur=2.00,
        )

        assert payment.user_id == "user_123"
        assert payment.stripe_payment_intent_id == "pi_abc123"
        assert payment.amount_eur == 2.00
        assert payment.currency == "eur"
        assert payment.status == PaymentStatus.PENDING
        assert payment.subscription_id is None
        assert payment.stripe_invoice_id is None
        assert payment.paid_at is None
        assert payment.failed_at is None

    def test_create_payment_succeeded(self):
        """Test creating successful payment."""
        paid_at = datetime.now(UTC)

        payment = Payment(
            user_id="user_123",
            subscription_id=1,
            stripe_payment_intent_id="pi_abc123",
            stripe_invoice_id="in_xyz789",
            stripe_charge_id="ch_123456",
            amount_eur=2.00,
            status=PaymentStatus.SUCCEEDED,
            payment_method_type="card",
            payment_method_last4="4242",
            payment_method_brand="visa",
            paid_at=paid_at,
        )

        assert payment.subscription_id == 1
        assert payment.status == PaymentStatus.SUCCEEDED
        assert payment.stripe_invoice_id == "in_xyz789"
        assert payment.stripe_charge_id == "ch_123456"
        assert payment.payment_method_type == "card"
        assert payment.payment_method_last4 == "4242"
        assert payment.payment_method_brand == "visa"
        assert payment.paid_at == paid_at

    def test_create_payment_failed(self):
        """Test creating failed payment."""
        failed_at = datetime.now(UTC)

        payment = Payment(
            user_id="user_123",
            stripe_payment_intent_id="pi_abc123",
            amount_eur=2.00,
            status=PaymentStatus.FAILED,
            failed_at=failed_at,
            failure_reason="Insufficient funds",
            failure_code="insufficient_funds",
        )

        assert payment.status == PaymentStatus.FAILED
        assert payment.failed_at == failed_at
        assert payment.failure_reason == "Insufficient funds"
        assert payment.failure_code == "insufficient_funds"

    def test_payment_with_extra_data(self):
        """Test payment with extra metadata."""
        payment = Payment(
            user_id="user_123",
            stripe_payment_intent_id="pi_abc123",
            amount_eur=2.00,
            extra_data={"risk_score": 0.1, "country": "IT"},
        )

        assert payment.extra_data is not None
        assert payment.extra_data["risk_score"] == 0.1
        assert payment.extra_data["country"] == "IT"


class TestInvoice:
    """Test Invoice model."""

    def test_create_invoice_minimal(self):
        """Test creating invoice with required fields."""
        period_start = datetime.now(UTC)
        period_end = period_start + timedelta(days=30)

        invoice = Invoice(
            user_id="user_123",
            stripe_invoice_id="in_abc123",
            invoice_number="INV-2025-001",
            amount_eur=2.00,
            total_eur=2.44,
            status="open",
            period_start=period_start,
            period_end=period_end,
        )

        assert invoice.user_id == "user_123"
        assert invoice.stripe_invoice_id == "in_abc123"
        assert invoice.invoice_number == "INV-2025-001"
        assert invoice.amount_eur == 2.00
        assert invoice.tax_eur == 0.0
        assert invoice.total_eur == 2.44
        assert invoice.currency == "eur"
        assert invoice.status == "open"
        assert invoice.paid is False
        assert invoice.subscription_id is None
        assert invoice.payment_id is None

    def test_create_invoice_paid(self):
        """Test creating paid invoice."""
        period_start = datetime.now(UTC)
        period_end = period_start + timedelta(days=30)
        paid_at = datetime.now(UTC)

        invoice = Invoice(
            user_id="user_123",
            subscription_id=1,
            payment_id=1,
            stripe_invoice_id="in_abc123",
            stripe_subscription_id="sub_xyz789",
            invoice_number="INV-2025-001",
            amount_eur=2.00,
            tax_eur=0.44,
            total_eur=2.44,
            status="paid",
            paid=True,
            period_start=period_start,
            period_end=period_end,
            paid_at=paid_at,
            invoice_pdf_url="https://stripe.com/invoice.pdf",
            hosted_invoice_url="https://stripe.com/invoice",
        )

        assert invoice.subscription_id == 1
        assert invoice.payment_id == 1
        assert invoice.stripe_subscription_id == "sub_xyz789"
        assert invoice.status == "paid"
        assert invoice.paid is True
        assert invoice.tax_eur == 0.44
        assert invoice.paid_at == paid_at
        assert invoice.invoice_pdf_url is not None
        assert invoice.hosted_invoice_url is not None

    def test_invoice_with_due_date(self):
        """Test invoice with due date."""
        period_start = datetime.now(UTC)
        period_end = period_start + timedelta(days=30)
        due_date = period_end + timedelta(days=7)

        invoice = Invoice(
            user_id="user_123",
            stripe_invoice_id="in_abc123",
            invoice_number="INV-2025-001",
            amount_eur=2.00,
            total_eur=2.44,
            status="open",
            period_start=period_start,
            period_end=period_end,
            due_date=due_date,
        )

        assert invoice.due_date == due_date


class TestCustomer:
    """Test Customer model."""

    def test_create_customer_minimal(self):
        """Test creating customer with required fields."""
        customer = Customer(
            user_id="user_123",
            stripe_customer_id="cus_abc123",
            email="user@example.com",
        )

        assert customer.user_id == "user_123"
        assert customer.stripe_customer_id == "cus_abc123"
        assert customer.email == "user@example.com"
        assert customer.name is None
        assert customer.tax_exempt is False
        assert customer.tax_id is None

    def test_create_customer_with_address(self):
        """Test creating customer with full address."""
        customer = Customer(
            user_id="user_123",
            stripe_customer_id="cus_abc123",
            email="user@example.com",
            name="John Doe",
            address_line1="Via Roma 123",
            address_line2="Apt 4B",
            address_city="Milano",
            address_state="MI",
            address_postal_code="20100",
            address_country="IT",
        )

        assert customer.name == "John Doe"
        assert customer.address_line1 == "Via Roma 123"
        assert customer.address_line2 == "Apt 4B"
        assert customer.address_city == "Milano"
        assert customer.address_state == "MI"
        assert customer.address_postal_code == "20100"
        assert customer.address_country == "IT"

    def test_create_customer_with_tax_info(self):
        """Test creating customer with tax information."""
        customer = Customer(
            user_id="user_123",
            stripe_customer_id="cus_abc123",
            email="user@example.com",
            tax_id="IT12345678901",
            tax_exempt=True,
        )

        assert customer.tax_id == "IT12345678901"
        assert customer.tax_exempt is True

    def test_customer_with_extra_data(self):
        """Test customer with extra metadata."""
        customer = Customer(
            user_id="user_123",
            stripe_customer_id="cus_abc123",
            email="user@example.com",
            extra_data={"preferred_language": "it", "marketing_opt_in": True},
        )

        assert customer.extra_data is not None
        assert customer.extra_data["preferred_language"] == "it"
        assert customer.extra_data["marketing_opt_in"] is True


class TestWebhookEvent:
    """Test WebhookEvent model."""

    def test_create_webhook_event_minimal(self):
        """Test creating webhook event with required fields."""
        event = WebhookEvent(
            stripe_event_id="evt_abc123",
            event_type="invoice.payment_succeeded",
            event_data={"id": "evt_abc123", "type": "invoice.payment_succeeded"},
        )

        assert event.stripe_event_id == "evt_abc123"
        assert event.event_type == "invoice.payment_succeeded"
        assert event.processed is False
        assert event.processed_at is None
        assert event.error_count == 0
        assert event.last_error is None
        assert event.last_error_at is None
        assert event.event_data is not None

    def test_webhook_event_processed(self):
        """Test processed webhook event."""
        processed_at = datetime.now(UTC)

        event = WebhookEvent(
            stripe_event_id="evt_abc123",
            event_type="customer.subscription.created",
            event_data={"id": "evt_abc123"},
            processed=True,
            processed_at=processed_at,
        )

        assert event.processed is True
        assert event.processed_at == processed_at

    def test_webhook_event_with_errors(self):
        """Test webhook event with processing errors."""
        last_error_at = datetime.now(UTC)

        event = WebhookEvent(
            stripe_event_id="evt_abc123",
            event_type="payment_intent.failed",
            event_data={"id": "evt_abc123"},
            error_count=3,
            last_error="Database connection timeout",
            last_error_at=last_error_at,
        )

        assert event.error_count == 3
        assert event.last_error == "Database connection timeout"
        assert event.last_error_at == last_error_at

    def test_webhook_event_types(self):
        """Test various webhook event types."""
        event_types = [
            "invoice.payment_succeeded",
            "invoice.payment_failed",
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
            "payment_intent.succeeded",
            "payment_intent.failed",
        ]

        for event_type in event_types:
            event = WebhookEvent(
                stripe_event_id=f"evt_{event_type}",
                event_type=event_type,
                event_data={"id": f"evt_{event_type}", "type": event_type},
            )
            assert event.event_type == event_type
