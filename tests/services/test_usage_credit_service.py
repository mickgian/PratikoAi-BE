"""Tests for UsageCreditService (DEV-257).

TDD: Tests written FIRST before implementation.
Tests credit balance, recharges, consumption with markup, and transaction history.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.billing import CreditTransaction, TransactionType, UserCredit
from app.services.usage_credit_service import UsageCreditService


@pytest.fixture
def service():
    return UsageCreditService()


class TestGetBalance:
    """Tests for get_balance method."""

    @pytest.mark.asyncio
    async def test_new_user_returns_zero(self, service):
        """New user with no credit record should return 0.0."""
        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with patch("app.services.usage_credit_service.database_service") as mock_db_svc:
            mock_db_svc.get_db.return_value = mock_db
            balance = await service.get_balance(user_id=1)
            assert balance == 0.0


class TestRecharge:
    """Tests for recharge method."""

    @pytest.mark.asyncio
    async def test_recharge_adds_balance_and_creates_transaction(self, service):
        """Recharge should increase balance and create transaction record."""
        existing_credit = UserCredit(id=1, user_id=1, balance_eur=5.0, extra_usage_enabled=False)
        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_credit
        mock_db.execute.return_value = mock_result

        with patch("app.services.usage_credit_service.database_service") as mock_db_svc:
            mock_db_svc.get_db.return_value = mock_db
            new_balance = await service.recharge(user_id=1, amount_eur=10)

            assert new_balance == 15.0
            assert existing_credit.balance_eur == 15.0
            # Should have added a transaction
            added_objs = [call.args[0] for call in mock_db.add.call_args_list]
            transactions = [o for o in added_objs if isinstance(o, CreditTransaction)]
            assert len(transactions) == 1
            assert transactions[0].transaction_type == TransactionType.RECHARGE
            assert transactions[0].amount_eur == 10.0
            assert transactions[0].balance_after_eur == 15.0

    @pytest.mark.asyncio
    async def test_recharge_invalid_amount_raises(self, service):
        """Recharge with non-allowed amount should raise ValueError."""
        with pytest.raises(ValueError, match="Importo non valido"):
            await service.recharge(user_id=1, amount_eur=7)

    @pytest.mark.asyncio
    async def test_recharge_creates_credit_for_new_user(self, service):
        """Recharge for user without credit record should create one."""
        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # No existing credit
        mock_db.execute.return_value = mock_result

        with patch("app.services.usage_credit_service.database_service") as mock_db_svc:
            mock_db_svc.get_db.return_value = mock_db
            new_balance = await service.recharge(user_id=1, amount_eur=25)

            assert new_balance == 25.0
            # Should have added UserCredit + CreditTransaction
            added_objs = [call.args[0] for call in mock_db.add.call_args_list]
            credit_records = [o for o in added_objs if isinstance(o, UserCredit)]
            assert len(credit_records) == 1
            assert credit_records[0].balance_eur == 25.0


class TestConsume:
    """Tests for consume method."""

    @pytest.mark.asyncio
    async def test_consume_with_markup_base(self, service):
        """Base plan: 50% markup on credit consumption."""
        existing_credit = UserCredit(id=1, user_id=1, balance_eur=10.0, extra_usage_enabled=True)
        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_credit
        mock_db.execute.return_value = mock_result

        with patch("app.services.usage_credit_service.database_service") as mock_db_svc:
            mock_db_svc.get_db.return_value = mock_db
            # cost=0.10, markup=1.5 -> charged=0.15
            charged = await service.consume(user_id=1, cost_eur=0.10, markup_factor=1.50)

            assert charged == pytest.approx(0.15)
            assert existing_credit.balance_eur == pytest.approx(9.85)

    @pytest.mark.asyncio
    async def test_consume_insufficient_balance_raises(self, service):
        """Consume more than balance should raise ValueError."""
        existing_credit = UserCredit(id=1, user_id=1, balance_eur=0.01, extra_usage_enabled=True)
        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_credit
        mock_db.execute.return_value = mock_result

        with patch("app.services.usage_credit_service.database_service") as mock_db_svc:
            mock_db_svc.get_db.return_value = mock_db
            with pytest.raises(ValueError, match="Credito insufficiente"):
                await service.consume(user_id=1, cost_eur=1.00, markup_factor=1.50)

    @pytest.mark.asyncio
    async def test_consume_exact_balance_succeeds(self, service):
        """Consuming exactly the balance should succeed."""
        existing_credit = UserCredit(id=1, user_id=1, balance_eur=1.50, extra_usage_enabled=True)
        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_credit
        mock_db.execute.return_value = mock_result

        with patch("app.services.usage_credit_service.database_service") as mock_db_svc:
            mock_db_svc.get_db.return_value = mock_db
            # cost=1.00, markup=1.5 -> charged=1.50 == balance
            charged = await service.consume(user_id=1, cost_eur=1.00, markup_factor=1.50)

            assert charged == pytest.approx(1.50)
            assert existing_credit.balance_eur == pytest.approx(0.0)


class TestEnableExtraUsage:
    """Tests for enable_extra_usage method."""

    @pytest.mark.asyncio
    async def test_toggles_flag(self, service):
        """enable_extra_usage should toggle the extra_usage_enabled flag."""
        existing_credit = UserCredit(id=1, user_id=1, balance_eur=5.0, extra_usage_enabled=False)
        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_credit
        mock_db.execute.return_value = mock_result

        with patch("app.services.usage_credit_service.database_service") as mock_db_svc:
            mock_db_svc.get_db.return_value = mock_db
            await service.enable_extra_usage(user_id=1, enabled=True)

            assert existing_credit.extra_usage_enabled is True


class TestTransactionHistory:
    """Tests for get_transaction_history method."""

    @pytest.mark.asyncio
    async def test_returns_ordered_desc(self, service):
        """Transaction history should be ordered by created_at descending."""
        tx1 = CreditTransaction(
            id=1,
            user_id=1,
            transaction_type="recharge",
            amount_eur=10.0,
            balance_after_eur=10.0,
        )
        tx2 = CreditTransaction(
            id=2,
            user_id=1,
            transaction_type="consumption",
            amount_eur=0.15,
            balance_after_eur=9.85,
        )
        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [tx2, tx1]  # desc order
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        with patch("app.services.usage_credit_service.database_service") as mock_db_svc:
            mock_db_svc.get_db.return_value = mock_db
            history = await service.get_transaction_history(user_id=1)

            assert len(history) == 2
            assert history[0].id == 2  # most recent first
            assert history[1].id == 1
