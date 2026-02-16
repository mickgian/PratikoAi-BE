"""Usage credit service for pay-as-you-go billing (DEV-257).

Manages user credit balances, recharges via Stripe, and credit
consumption with plan-specific markup.
"""

from datetime import UTC, datetime

from sqlalchemy import select

from app.core.config import settings
from app.core.logging import logger
from app.models.billing import CreditTransaction, TransactionType, UserCredit
from app.services.database import database_service


class UsageCreditService:
    """Manages user credits for pay-as-you-go usage."""

    async def get_balance(self, user_id: int) -> float:
        """Get user's current credit balance.

        Args:
            user_id: User ID

        Returns:
            Credit balance in EUR (0.0 for new users)
        """
        async with database_service.get_db() as db:
            query = select(UserCredit).where(UserCredit.user_id == user_id)
            result = await db.execute(query)
            credit = result.scalar_one_or_none()
            return credit.balance_eur if credit else 0.0

    async def recharge(
        self,
        user_id: int,
        amount_eur: int,
        stripe_payment_intent_id: str | None = None,
    ) -> float:
        """Add credits to user balance.

        Args:
            user_id: User ID
            amount_eur: Recharge amount (must be in allowed amounts: 5, 10, 25, 50, 100)
            stripe_payment_intent_id: Stripe payment intent ID

        Returns:
            New balance after recharge

        Raises:
            ValueError: If amount is not in allowed recharge amounts
        """
        allowed = settings.BILLING_CREDIT_RECHARGE_AMOUNTS
        if amount_eur not in allowed:
            raise ValueError(f"Importo non valido. Importi consentiti: {allowed}")

        async with database_service.get_db() as db:
            query = select(UserCredit).where(UserCredit.user_id == user_id)
            result = await db.execute(query)
            credit = result.scalar_one_or_none()

            if credit is None:
                credit = UserCredit(user_id=user_id, balance_eur=0.0)
                db.add(credit)

            credit.balance_eur += amount_eur
            credit.updated_at = datetime.now(UTC)
            new_balance = credit.balance_eur

            # Record transaction
            tx = CreditTransaction(
                user_id=user_id,
                transaction_type=TransactionType.RECHARGE,
                amount_eur=float(amount_eur),
                balance_after_eur=new_balance,
                stripe_payment_intent_id=stripe_payment_intent_id,
                description=f"Ricarica credito di {amount_eur} EUR",
            )
            db.add(tx)

            await db.commit()

            logger.info(
                "credit_recharged",
                user_id=user_id,
                amount_eur=amount_eur,
                new_balance=new_balance,
            )

            return new_balance

    async def consume(
        self,
        user_id: int,
        cost_eur: float,
        markup_factor: float,
        usage_event_id: int | None = None,
    ) -> float:
        """Consume credits with plan-specific markup.

        Args:
            user_id: User ID
            cost_eur: Raw LLM cost in EUR
            markup_factor: Plan markup factor (e.g., 1.5 for base = 50% markup)
            usage_event_id: Optional link to UsageEvent

        Returns:
            Amount charged (cost * markup)

        Raises:
            ValueError: If insufficient credit balance
        """
        charged = cost_eur * markup_factor

        async with database_service.get_db() as db:
            query = select(UserCredit).where(UserCredit.user_id == user_id)
            result = await db.execute(query)
            credit = result.scalar_one_or_none()

            if credit is None or credit.balance_eur < charged:
                raise ValueError(
                    f"Credito insufficiente. Necessario: {charged:.2f} EUR, "
                    f"Disponibile: {credit.balance_eur if credit else 0:.2f} EUR"
                )

            credit.balance_eur -= charged
            credit.updated_at = datetime.now(UTC)

            tx = CreditTransaction(
                user_id=user_id,
                transaction_type=TransactionType.CONSUMPTION,
                amount_eur=charged,
                balance_after_eur=credit.balance_eur,
                usage_event_id=usage_event_id,
                description=f"Consumo credito: {cost_eur:.4f} EUR x {markup_factor} markup",
            )
            db.add(tx)

            await db.commit()

            logger.info(
                "credit_consumed",
                user_id=user_id,
                raw_cost=cost_eur,
                markup_factor=markup_factor,
                charged=charged,
                remaining_balance=credit.balance_eur,
            )

            return charged

    async def enable_extra_usage(self, user_id: int, enabled: bool) -> None:
        """Toggle extra usage (credit consumption) on/off.

        Args:
            user_id: User ID
            enabled: Whether to enable credit consumption
        """
        async with database_service.get_db() as db:
            query = select(UserCredit).where(UserCredit.user_id == user_id)
            result = await db.execute(query)
            credit = result.scalar_one_or_none()

            if credit is None:
                credit = UserCredit(user_id=user_id, balance_eur=0.0)
                db.add(credit)

            credit.extra_usage_enabled = enabled
            credit.updated_at = datetime.now(UTC)

            await db.commit()

            logger.info("extra_usage_toggled", user_id=user_id, enabled=enabled)

    async def get_transaction_history(self, user_id: int, limit: int = 50, offset: int = 0) -> list[CreditTransaction]:
        """Get credit transaction history ordered by most recent first.

        Args:
            user_id: User ID
            limit: Max records to return
            offset: Skip N records

        Returns:
            List of CreditTransaction records
        """
        async with database_service.get_db() as db:
            query = (
                select(CreditTransaction)
                .where(CreditTransaction.user_id == user_id)
                .order_by(CreditTransaction.created_at.desc())  # type: ignore[union-attr]
                .limit(limit)
                .offset(offset)
            )
            result = await db.execute(query)
            return list(result.scalars().all())


# Global instance
usage_credit_service = UsageCreditService()
