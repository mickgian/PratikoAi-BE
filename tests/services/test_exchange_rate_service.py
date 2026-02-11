"""Tests for exchange rate service (ADR-026)."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.exchange_rate_service import (
    CACHE_DURATION,
    DEFAULT_EUR_USD_RATE,
    clear_cache,
    convert_eur_to_usd,
    convert_usd_to_eur,
    get_eur_to_usd_rate,
)


@pytest.fixture(autouse=True)
def reset_cache():
    """Clear cache before and after each test."""
    clear_cache()
    yield
    clear_cache()


class TestGetEurToUsdRate:
    """Tests for get_eur_to_usd_rate function."""

    @pytest.mark.asyncio
    async def test_fetches_rate_from_api(self):
        """Should fetch rate from Frankfurter API."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "amount": 1,
            "base": "EUR",
            "date": "2026-02-11",
            "rates": {"USD": 1.0875},
        }
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.exchange_rate_service.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance

            rate = await get_eur_to_usd_rate()

            assert rate == 1.0875

    @pytest.mark.asyncio
    async def test_returns_cached_rate_within_duration(self):
        """Should return cached rate without API call if cache is valid."""
        # First call - fetch from API
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "rates": {"USD": 1.10},
            "date": "2026-02-11",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.exchange_rate_service.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance

            rate1 = await get_eur_to_usd_rate()
            assert rate1 == 1.10

            # Second call - should use cache, not call API again
            mock_instance.get.reset_mock()
            rate2 = await get_eur_to_usd_rate()

            assert rate2 == 1.10
            mock_instance.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_fallback_on_api_error(self):
        """Should return fallback rate when API fails and no cache."""
        with patch("app.services.exchange_rate_service.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.side_effect = Exception("Network error")
            mock_client.return_value.__aenter__.return_value = mock_instance

            rate = await get_eur_to_usd_rate()

            assert rate == DEFAULT_EUR_USD_RATE

    @pytest.mark.asyncio
    async def test_returns_cached_rate_on_api_error(self):
        """Should return cached rate when API fails but cache exists."""
        # First call - successful
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "rates": {"USD": 1.15},
            "date": "2026-02-11",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.exchange_rate_service.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance

            rate1 = await get_eur_to_usd_rate()
            assert rate1 == 1.15

        # Expire the cache manually
        with patch(
            "app.services.exchange_rate_service._cached_at", datetime.now() - CACHE_DURATION - timedelta(hours=1)
        ):
            # Second call - API fails, should return cached rate
            with patch("app.services.exchange_rate_service.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.side_effect = Exception("API down")
                mock_client.return_value.__aenter__.return_value = mock_instance

                # Need to also patch the cache check
                with patch("app.services.exchange_rate_service._cached_rate", 1.15):
                    rate2 = await get_eur_to_usd_rate()
                    assert rate2 == 1.15


class TestConvertEurToUsd:
    """Tests for convert_eur_to_usd function."""

    def test_converts_eur_to_usd(self):
        """Should convert EUR to USD correctly."""
        result = convert_eur_to_usd(10.0, 1.10)
        assert result == 11.0

    def test_handles_small_amounts(self):
        """Should handle small amounts with precision."""
        result = convert_eur_to_usd(0.001, 1.0875)
        assert result == 0.001087  # 0.001 * 1.0875 = 0.0010875, rounded to 6 decimals

    def test_returns_none_for_none_input(self):
        """Should return None when input is None."""
        result = convert_eur_to_usd(None, 1.10)
        assert result is None

    def test_handles_zero(self):
        """Should handle zero amount."""
        result = convert_eur_to_usd(0.0, 1.10)
        assert result == 0.0


class TestConvertUsdToEur:
    """Tests for convert_usd_to_eur function."""

    def test_converts_usd_to_eur(self):
        """Should convert USD to EUR correctly."""
        result = convert_usd_to_eur(11.0, 1.10)
        assert result == 10.0

    def test_handles_small_amounts(self):
        """Should handle small amounts with precision."""
        result = convert_usd_to_eur(0.001087, 1.0875)
        assert result == pytest.approx(0.000999, rel=0.01)

    def test_returns_none_for_none_input(self):
        """Should return None when input is None."""
        result = convert_usd_to_eur(None, 1.10)
        assert result is None

    def test_handles_zero(self):
        """Should handle zero amount."""
        result = convert_usd_to_eur(0.0, 1.10)
        assert result == 0.0


class TestClearCache:
    """Tests for clear_cache function."""

    @pytest.mark.asyncio
    async def test_clears_cached_values(self):
        """Should clear cached rate and timestamp."""
        # Populate cache
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "rates": {"USD": 1.12},
            "date": "2026-02-11",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.exchange_rate_service.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance
            await get_eur_to_usd_rate()

        # Clear and verify next call fetches from API
        clear_cache()

        with patch("app.services.exchange_rate_service.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance

            await get_eur_to_usd_rate()

            # API should be called because cache was cleared
            mock_instance.get.assert_called_once()
