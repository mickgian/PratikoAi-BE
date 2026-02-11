"""Exchange rate service using Frankfurter API (ECB data).

ADR-026: Uses Frankfurter API for EUR/USD exchange rates with 24-hour caching.
The API provides official European Central Bank reference rates, updated daily.
"""

from datetime import datetime, timedelta

import httpx

from app.core.logging import logger

# Cache exchange rate for 24 hours (ECB updates daily ~16:00 CET)
_cached_rate: float | None = None
_cached_at: datetime | None = None
CACHE_DURATION = timedelta(hours=24)

# Frankfurter API - free, no auth required, uses ECB data
FRANKFURTER_URL = "https://api.frankfurter.dev/v1/latest"

# Fallback rate if API is unavailable and no cache exists
DEFAULT_EUR_USD_RATE = 1.08


async def get_eur_to_usd_rate() -> float:
    """Get EUR to USD exchange rate, cached for 24 hours.

    Returns:
        Exchange rate (1 EUR = X USD)
    """
    global _cached_rate, _cached_at

    # Return cached rate if still valid
    if _cached_rate and _cached_at and datetime.now() - _cached_at < CACHE_DURATION:
        return _cached_rate

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                FRANKFURTER_URL,
                params={"from": "EUR", "to": "USD"},
            )
            response.raise_for_status()
            data = response.json()
            rate: float = data["rates"]["USD"]
            _cached_rate = rate
            _cached_at = datetime.now()
            logger.info(
                "exchange_rate_updated",
                rate=rate,
                date=data.get("date"),
                source="frankfurter",
            )
            return rate
    except Exception as e:
        logger.warning(
            "exchange_rate_fetch_failed",
            error=str(e),
            error_type=type(e).__name__,
            using_cached=_cached_rate is not None,
        )
        # Return cached rate if available, otherwise use fallback
        return _cached_rate or DEFAULT_EUR_USD_RATE


def convert_eur_to_usd(eur_amount: float | None, rate: float) -> float | None:
    """Convert EUR amount to USD.

    Args:
        eur_amount: Amount in EUR (can be None)
        rate: Exchange rate (1 EUR = X USD)

    Returns:
        Amount in USD, or None if input was None
    """
    if eur_amount is None:
        return None
    return round(eur_amount * rate, 6)


def convert_usd_to_eur(usd_amount: float | None, rate: float) -> float | None:
    """Convert USD amount to EUR.

    Args:
        usd_amount: Amount in USD (can be None)
        rate: Exchange rate (1 EUR = X USD)

    Returns:
        Amount in EUR, or None if input was None
    """
    if usd_amount is None:
        return None
    return round(usd_amount / rate, 6)


def clear_cache() -> None:
    """Clear the cached exchange rate (for testing)."""
    global _cached_rate, _cached_at
    _cached_rate = None
    _cached_at = None
