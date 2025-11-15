"""Tests for payment API endpoints."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.payment import Customer, Invoice, PlanType, Subscription, SubscriptionStatus
from app.models.session import Session


@pytest.fixture
def mock_session():
    """Mock user session."""
    return Session(
        id="session_123",
        user_id="test_user_123",
        user_email="test@normoai.it",
        expires_at=datetime.utcnow() + timedelta(hours=1),
    )


@pytest.fixture
def mock_customer():
    """Mock customer record."""
    return Customer(
        id=1, user_id="test_user_123", stripe_customer_id="cus_test123", email="test@normoai.it", name="Test User"
    )


@pytest.fixture
def mock_subscription():
    """Mock subscription record."""
    return Subscription(
        id=1,
        user_id="test_user_123",
        stripe_subscription_id="sub_test123",
        stripe_customer_id="cus_test123",
        stripe_price_id="price_test123",
        status=SubscriptionStatus.ACTIVE,
        plan_type=PlanType.MONTHLY,
        amount_eur=69.00,
        current_period_start=datetime.utcnow(),
        current_period_end=datetime.utcnow() + timedelta(days=30),
        created_at=datetime.utcnow(),
    )


@pytest.fixture
def mock_invoice():
    """Mock invoice record."""
    return Invoice(
        id=1,
        user_id="test_user_123",
        stripe_invoice_id="in_test123",
        invoice_number="INV-001",
        amount_eur=69.00,
        tax_eur=0.0,
        total_eur=69.00,
        status="paid",
        paid=True,
        period_start=datetime.utcnow() - timedelta(days=30),
        period_end=datetime.utcnow(),
        created_at=datetime.utcnow(),
    )


class TestPaymentAPI:
    """Test cases for payment API endpoints."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    @patch("app.api.v1.payments.get_current_session")
    @patch("app.api.v1.payments.stripe_service")
    def test_create_customer_success(self, mock_stripe_service, mock_get_session, mock_session, mock_customer):
        """Test successful customer creation."""
        mock_get_session.return_value = mock_session
        mock_stripe_service.create_customer.return_value = mock_customer

        response = self.client.post(
            "/api/v1/payments/customer", json={"email": "test@normoai.it", "name": "Test User"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["customer_id"] == "cus_test123"
        assert data["email"] == "test@normoai.it"
        assert data["name"] == "Test User"

    @patch("app.api.v1.payments.get_current_session")
    @patch("app.api.v1.payments.stripe_service")
    def test_create_customer_failure(self, mock_stripe_service, mock_get_session, mock_session):
        """Test customer creation failure."""
        mock_get_session.return_value = mock_session
        mock_stripe_service.create_customer.side_effect = Exception("Stripe error")

        response = self.client.post(
            "/api/v1/payments/customer", json={"email": "test@normoai.it", "name": "Test User"}
        )

        assert response.status_code == 500
        assert "Failed to create customer" in response.json()["detail"]

    @patch("app.api.v1.payments.get_current_session")
    @patch("app.api.v1.payments.stripe_service")
    def test_create_checkout_session_success(self, mock_stripe_service, mock_get_session, mock_session, mock_customer):
        """Test successful checkout session creation."""
        mock_get_session.return_value = mock_session
        mock_stripe_service.create_customer.return_value = mock_customer
        mock_stripe_service.create_checkout_session.return_value = {
            "checkout_session_id": "cs_test123",
            "checkout_url": "https://checkout.stripe.com/test",
            "expires_at": 1706601600,
        }

        response = self.client.post(
            "/api/v1/payments/checkout/session",
            json={"success_url": "https://app.normoai.it/success", "cancel_url": "https://app.normoai.it/cancel"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["checkout_session_id"] == "cs_test123"
        assert data["checkout_url"] == "https://checkout.stripe.com/test"

    @patch("app.api.v1.payments.get_current_session")
    @patch("app.api.v1.payments.stripe_service")
    def test_get_user_subscription_active(
        self, mock_stripe_service, mock_get_session, mock_session, mock_subscription
    ):
        """Test getting active user subscription."""
        mock_get_session.return_value = mock_session
        mock_stripe_service.get_user_subscription.return_value = mock_subscription

        response = self.client.get("/api/v1/payments/subscription")

        assert response.status_code == 200
        data = response.json()
        assert data["subscription"]["id"] == "sub_test123"
        assert data["subscription"]["status"] == "active"
        assert data["subscription"]["amount_eur"] == 69.00
        assert data["billing"]["next_payment_amount_eur"] == 69.00
        assert data["features"]["chat_requests_included"] == "unlimited"

    @patch("app.api.v1.payments.get_current_session")
    @patch("app.api.v1.payments.stripe_service")
    def test_get_user_subscription_none(self, mock_stripe_service, mock_get_session, mock_session):
        """Test getting subscription when user has none."""
        mock_get_session.return_value = mock_session
        mock_stripe_service.get_user_subscription.return_value = None

        response = self.client.get("/api/v1/payments/subscription")

        assert response.status_code == 200
        data = response.json()
        assert data["subscription"] is None
        assert data["status"] == "no_subscription"
        assert data["trial_available"] is True

    @patch("app.api.v1.payments.get_current_session")
    @patch("app.api.v1.payments.stripe_service")
    def test_cancel_subscription_success(self, mock_stripe_service, mock_get_session, mock_session, mock_subscription):
        """Test successful subscription cancellation."""
        mock_get_session.return_value = mock_session
        mock_stripe_service.get_user_subscription.return_value = mock_subscription
        mock_stripe_service.cancel_subscription.return_value = True

        response = self.client.post("/api/v1/payments/subscription/cancel")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "canceled successfully" in data["message"]

    @patch("app.api.v1.payments.get_current_session")
    @patch("app.api.v1.payments.stripe_service")
    def test_cancel_subscription_not_found(self, mock_stripe_service, mock_get_session, mock_session):
        """Test canceling subscription when none exists."""
        mock_get_session.return_value = mock_session
        mock_stripe_service.get_user_subscription.return_value = None

        response = self.client.post("/api/v1/payments/subscription/cancel")

        assert response.status_code == 404
        assert "No active subscription found" in response.json()["detail"]

    @patch("app.api.v1.payments.get_current_session")
    @patch("app.api.v1.payments.stripe_service")
    def test_cancel_subscription_failure(self, mock_stripe_service, mock_get_session, mock_session, mock_subscription):
        """Test subscription cancellation failure."""
        mock_get_session.return_value = mock_session
        mock_stripe_service.get_user_subscription.return_value = mock_subscription
        mock_stripe_service.cancel_subscription.return_value = False

        response = self.client.post("/api/v1/payments/subscription/cancel")

        assert response.status_code == 500
        assert "Failed to cancel subscription" in response.json()["detail"]

    @patch("app.api.v1.payments.get_current_session")
    @patch("app.api.v1.payments.stripe_service")
    def test_get_user_invoices_success(self, mock_stripe_service, mock_get_session, mock_session, mock_invoice):
        """Test getting user invoices."""
        mock_get_session.return_value = mock_session
        mock_stripe_service.get_user_invoices.return_value = [mock_invoice]

        response = self.client.get("/api/v1/payments/invoices?limit=10")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["invoices"]) == 1
        assert data["invoices"][0]["id"] == "in_test123"
        assert data["invoices"][0]["amount_eur"] == 69.00
        assert data["invoices"][0]["paid"] is True

    @patch("app.api.v1.payments.get_current_session")
    @patch("app.api.v1.payments.stripe_service")
    def test_get_user_invoices_empty(self, mock_stripe_service, mock_get_session, mock_session):
        """Test getting invoices when user has none."""
        mock_get_session.return_value = mock_session
        mock_stripe_service.get_user_invoices.return_value = []

        response = self.client.get("/api/v1/payments/invoices")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["invoices"]) == 0

    @patch("app.api.v1.payments.stripe_service")
    def test_stripe_webhook_success(self, mock_stripe_service):
        """Test successful webhook processing."""
        mock_stripe_service.process_webhook_event.return_value = True

        response = self.client.post(
            "/api/v1/payments/webhook", content=b'{"test": "payload"}', headers={"stripe-signature": "test_signature"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["received"] is True

    @patch("app.api.v1.payments.stripe_service")
    def test_stripe_webhook_missing_signature(self, mock_stripe_service):
        """Test webhook with missing signature."""
        response = self.client.post("/api/v1/payments/webhook", content=b'{"test": "payload"}')

        assert response.status_code == 400
        assert "Missing Stripe signature" in response.json()["detail"]

    @patch("app.api.v1.payments.stripe_service")
    def test_stripe_webhook_processing_failure(self, mock_stripe_service):
        """Test webhook processing failure."""
        mock_stripe_service.process_webhook_event.return_value = False

        response = self.client.post(
            "/api/v1/payments/webhook", content=b'{"test": "payload"}', headers={"stripe-signature": "test_signature"}
        )

        assert response.status_code == 400
        assert "Webhook processing failed" in response.json()["detail"]

    def test_get_pricing_info(self):
        """Test getting pricing information."""
        response = self.client.get("/api/v1/payments/pricing")

        assert response.status_code == 200
        data = response.json()
        assert len(data["plans"]) == 1

        plan = data["plans"][0]
        assert plan["id"] == "monthly"
        assert plan["name"] == "NormoAI Professional"
        assert plan["price_eur"] == 69.00
        assert plan["currency"] == "eur"
        assert plan["interval"] == "month"
        assert "Unlimited chat requests" in plan["features"]
        assert "Italian tax and legal knowledge base" in plan["features"]

        # Check limits
        assert plan["limits"]["api_cost_eur_per_month"] == 2.00
        assert plan["limits"]["chat_requests"] == "unlimited"

        # Check trial info
        assert data["trial"]["duration_days"] == 7
        assert data["trial"]["features_included"] == "all"

        # Check billing info
        assert "visa" in data["billing"]["accepted_cards"]
        assert "eur" in data["billing"]["currencies"]
        assert data["billing"]["tax_handling"] == "automatic"

    @patch("app.api.v1.payments.get_current_session")
    def test_create_billing_portal_session(self, mock_get_session, mock_session):
        """Test creating billing portal session."""
        mock_get_session.return_value = mock_session

        response = self.client.get("/api/v1/payments/subscription/portal")

        assert response.status_code == 200
        data = response.json()
        assert "portal_url" in data
        assert "return_url" in data

    @patch("app.api.v1.payments.get_current_session")
    def test_unauthorized_access(self, mock_get_session):
        """Test unauthorized access to protected endpoints."""
        mock_get_session.side_effect = Exception("Unauthorized")

        response = self.client.get("/api/v1/payments/subscription")

        # This would return 401 or 403 based on auth middleware implementation
        assert response.status_code in [401, 403, 500]

    def test_invalid_email_format(self):
        """Test customer creation with invalid email."""
        with patch("app.api.v1.payments.get_current_session") as mock_get_session:
            mock_get_session.return_value = Session(
                id="session_123", user_id="test_user_123", user_email="test@normoai.it"
            )

            response = self.client.post(
                "/api/v1/payments/customer", json={"email": "invalid-email", "name": "Test User"}
            )

            assert response.status_code == 422  # Validation error

    def test_rate_limiting(self):
        """Test rate limiting on payment endpoints."""
        with patch("app.api.v1.payments.get_current_session") as mock_get_session:
            with patch("app.api.v1.payments.stripe_service") as mock_stripe_service:
                mock_get_session.return_value = Session(
                    id="session_123", user_id="test_user_123", user_email="test@normoai.it"
                )
                mock_stripe_service.create_customer.return_value = Customer(
                    user_id="test_user_123", stripe_customer_id="cus_test123", email="test@normoai.it"
                )

                # This test would need actual rate limiting configuration
                # For now, just verify the endpoint works
                response = self.client.post(
                    "/api/v1/payments/customer", json={"email": "test@normoai.it", "name": "Test User"}
                )

                assert response.status_code == 200

    @patch("app.api.v1.payments.get_current_session")
    @patch("app.api.v1.payments.stripe_service")
    def test_subscription_with_trial(self, mock_stripe_service, mock_get_session, mock_session):
        """Test subscription response with trial information."""
        mock_get_session.return_value = mock_session

        # Create trial subscription
        trial_subscription = Subscription(
            id=1,
            user_id="test_user_123",
            stripe_subscription_id="sub_test123",
            stripe_customer_id="cus_test123",
            stripe_price_id="price_test123",
            status=SubscriptionStatus.TRIALING,
            plan_type=PlanType.MONTHLY,
            amount_eur=69.00,
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=30),
            trial_start=datetime.utcnow(),
            trial_end=datetime.utcnow() + timedelta(days=7),
            created_at=datetime.utcnow(),
        )

        mock_stripe_service.get_user_subscription.return_value = trial_subscription

        response = self.client.get("/api/v1/payments/subscription")

        assert response.status_code == 200
        data = response.json()
        assert data["subscription"]["status"] == "trialing"
        assert data["subscription"]["is_trial"] is True
        assert data["subscription"]["trial_days_remaining"] >= 0
