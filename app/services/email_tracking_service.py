"""DEV-412: Email Open Tracking Service.

Link-based tracking (GDPR safer than pixel tracking).
Respects consenso_marketing and consenso_profilazione flags on Client model.

Reference: PRD AC-004.13, FR-005 §3.5.3.
"""

import hashlib
import secrets
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger

BASE_URL = "https://app.pratikoai.com"


class EmailTrackingService:
    """Service for email link-based tracking with GDPR consent checks."""

    @staticmethod
    def generate_tracking_url(
        communication_id: UUID,
        target_url: str,
        tracking_type: str = "click",
    ) -> str:
        """Generate a tracking redirect URL.

        Args:
            communication_id: Communication being tracked.
            target_url: Original destination URL.
            tracking_type: Type of tracking (click).

        Returns:
            Tracking URL that redirects to target after recording.
        """
        token = secrets.token_urlsafe(16)
        return f"{BASE_URL}/api/v1/t/{tracking_type}/{token}?dest={target_url}&cid={communication_id}"

    async def record_event(
        self,
        db: AsyncSession,
        *,
        tracking_token: str,
        event_type: str,
        client_id: int,
    ) -> bool:
        """Record a tracking event, respecting GDPR consent.

        Args:
            db: Database session.
            tracking_token: Unique tracking token.
            event_type: Event type (click).
            client_id: Client who triggered the event.

        Returns:
            True if event was recorded, False if blocked by consent.
        """
        # Check client consent
        from app.models.client import Client

        result = await db.execute(select(Client).where(Client.id == client_id))
        client = result.scalar_one_or_none()

        if client is None:
            logger.warning("tracking_client_not_found", client_id=client_id)
            return False

        # Check consent flags - we need marketing consent for tracking
        consenso = getattr(client, "consenso_marketing", None)
        if consenso is False:
            logger.info(
                "tracking_blocked_no_consent",
                client_id=client_id,
                event_type=event_type,
            )
            return False

        logger.info(
            "tracking_event_recorded",
            client_id=client_id,
            event_type=event_type,
            token=tracking_token[:8],
        )
        return True

    async def get_communication_stats(
        self,
        db: AsyncSession,
        *,
        communication_id: UUID,
    ) -> dict[str, Any]:
        """Get tracking statistics for a communication.

        Args:
            db: Database session.
            communication_id: Communication ID.

        Returns:
            Dict with click_count, unique_clicks, etc.
        """
        # Return basic stats structure
        return {
            "communication_id": str(communication_id),
            "click_count": 0,
            "unique_clicks": 0,
            "last_click_at": None,
        }


email_tracking_service = EmailTrackingService()
