"""DEV-334: WhatsApp wa.me Link Integration — Link generation service.

Generates wa.me links for WhatsApp communication without API approval.
Uses wa.me/{phone}?text={message} format.
"""

import re
from urllib.parse import quote

from app.core.logging import logger


class WhatsAppService:
    """Service for generating WhatsApp wa.me links."""

    BASE_URL = "https://wa.me"

    def generate_link(
        self,
        *,
        phone: str,
        message: str | None = None,
    ) -> str:
        """Generate a wa.me link for a single recipient.

        Args:
            phone: Phone number (will be normalized to international format).
            message: Optional pre-filled message text.

        Returns:
            wa.me URL string.

        Raises:
            ValueError: If phone number is invalid.
        """
        normalized = self.normalize_phone(phone)
        url = f"{self.BASE_URL}/{normalized}"

        if message:
            encoded = quote(message, safe="")
            url = f"{url}?text={encoded}"

        return url

    def generate_bulk_links(
        self,
        *,
        phones: list[str],
        message: str | None = None,
    ) -> list[dict]:
        """Generate wa.me links for multiple recipients.

        Returns list of dicts: [{"phone": original, "link": url, "error": None|str}]
        """
        results = []
        for phone in phones:
            try:
                link = self.generate_link(phone=phone, message=message)
                results.append({"phone": phone, "link": link, "error": None})
            except ValueError as exc:
                results.append({"phone": phone, "link": None, "error": str(exc)})

        logger.info(
            "whatsapp_bulk_links_generated",
            total=len(phones),
            success=sum(1 for r in results if r["error"] is None),
        )
        return results

    @staticmethod
    def normalize_phone(phone: str) -> str:
        """Normalize phone number to international format (digits only, no +).

        Italian numbers: +39 prefix added if missing.
        Removes spaces, dashes, parentheses.

        Raises:
            ValueError: If phone number is invalid.
        """
        cleaned = re.sub(r"[\s\-\(\)\+]", "", phone)

        if not cleaned.isdigit():
            raise ValueError(f"Numero di telefono non valido: {phone}")

        if len(cleaned) < 6:
            raise ValueError(f"Numero di telefono troppo corto: {phone}")

        # Italian number normalization
        if cleaned.startswith("39") and len(cleaned) >= 11:
            return cleaned
        elif cleaned.startswith("3") and len(cleaned) == 10 or cleaned.startswith("0") and len(cleaned) >= 9:
            return f"39{cleaned}"

        # Already international format or other country
        if len(cleaned) >= 10:
            return cleaned

        raise ValueError(f"Numero di telefono non valido: {phone}")


whatsapp_service = WhatsAppService()
