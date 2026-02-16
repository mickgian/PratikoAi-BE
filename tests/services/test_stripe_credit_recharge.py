"""Tests for Stripe credit recharge webhook handler (DEV-257)."""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.stripe_service import StripeService


@pytest.fixture
def service():
    with patch("app.services.stripe_service.stripe"):
        return StripeService()


class TestHandleCreditRecharge:
    @pytest.mark.asyncio
    async def test_successful_recharge(self, service):
        """Webhook should call usage_credit_service.recharge with correct args."""
        session_data = {"payment_intent": "pi_abc123"}
        metadata = {"type": "credit_recharge", "user_id": "1", "amount_eur": "25"}

        with patch("app.services.usage_credit_service.usage_credit_service") as mock_credit:
            mock_credit.recharge = AsyncMock(return_value=25.0)
            await service._handle_credit_recharge(session_data, metadata)

            mock_credit.recharge.assert_called_once_with(
                user_id=1, amount_eur=25, stripe_payment_intent_id="pi_abc123"
            )

    @pytest.mark.asyncio
    async def test_recharge_error_logs_but_does_not_raise(self, service):
        """Webhook handler should catch errors gracefully."""
        session_data = {"payment_intent": "pi_abc123"}
        metadata = {"type": "credit_recharge", "user_id": "1", "amount_eur": "7"}

        with patch("app.services.usage_credit_service.usage_credit_service") as mock_credit:
            mock_credit.recharge = AsyncMock(side_effect=ValueError("Importo non valido"))
            # Should not raise
            await service._handle_credit_recharge(session_data, metadata)
