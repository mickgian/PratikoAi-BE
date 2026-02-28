"""DEV-415: Communication Unsubscribe Mechanism.

Provides unsubscribe link generation and processing.
Uses List-Unsubscribe email header for standards compliance.

Reference: PRD §8 Risk "Spam communications" mitigation.
"""

import hashlib
import hmac
import secrets
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger

BASE_URL = "https://app.pratikoai.com"
_SECRET_KEY = "pratikoai-unsubscribe-secret"


class UnsubscribeService:
    """Service for managing email unsubscribe mechanism."""

    @staticmethod
    def generate_unsubscribe_link(
        client_id: int,
        communication_id: UUID,
    ) -> str:
        """Generate an unsubscribe link for a communication.

        Args:
            client_id: Client to unsubscribe.
            communication_id: Communication reference.

        Returns:
            Unsubscribe URL with signed token.
        """
        token_data = f"{client_id}:{communication_id}"
        token = hmac.new(_SECRET_KEY.encode(), token_data.encode(), hashlib.sha256).hexdigest()[:32]
        return f"{BASE_URL}/api/v1/unsubscribe/{client_id}?token={token}"

    @staticmethod
    def get_unsubscribe_headers(
        client_id: int,
        communication_id: UUID,
    ) -> dict[str, str]:
        """Get List-Unsubscribe email headers.

        Args:
            client_id: Client ID.
            communication_id: Communication ID.

        Returns:
            Dict with List-Unsubscribe and List-Unsubscribe-Post headers.
        """
        link = UnsubscribeService.generate_unsubscribe_link(client_id, communication_id)
        return {
            "List-Unsubscribe": f"<{link}>",
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        }

    async def unsubscribe(
        self,
        db: AsyncSession,
        *,
        token: str,
        client_id: int,
    ) -> bool:
        """Process an unsubscribe request.

        Sets consenso_marketing = False on the client record.

        Args:
            db: Database session.
            token: Unsubscribe token.
            client_id: Client requesting unsubscribe.

        Returns:
            True if successfully unsubscribed, False if client not found.
        """
        from app.models.client import Client

        result = await db.execute(select(Client).where(Client.id == client_id))
        client = result.scalar_one_or_none()

        if client is None:
            logger.warning("unsubscribe_client_not_found", client_id=client_id)
            return False

        # Set marketing consent to false (idempotent)
        if hasattr(client, "consenso_marketing"):
            client.consenso_marketing = False
        await db.commit()

        logger.info(
            "client_unsubscribed",
            client_id=client_id,
        )
        return True

    async def resubscribe(
        self,
        db: AsyncSession,
        *,
        client_id: int,
    ) -> bool:
        """Re-enable marketing consent for a client.

        Args:
            db: Database session.
            client_id: Client requesting re-subscribe.

        Returns:
            True if successfully re-subscribed, False if not found.
        """
        from app.models.client import Client

        result = await db.execute(select(Client).where(Client.id == client_id))
        client = result.scalar_one_or_none()

        if client is None:
            return False

        if hasattr(client, "consenso_marketing"):
            client.consenso_marketing = True
        await db.commit()

        logger.info("client_resubscribed", client_id=client_id)
        return True


unsubscribe_service = UnsubscribeService()
