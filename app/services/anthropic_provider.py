"""Anthropic Provider for LLM API calls.

This module provides an interface to Anthropic's Claude API with proper error handling,
cost tracking, and response formatting for integration with the resilient LLM service.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings
from app.core.logging import logger
from app.models.query import LLMResponse


@dataclass
class AnthropicResponse:
    """Anthropic API response structure."""

    text: str
    model: str
    tokens_used: int
    cost: float
    stop_reason: str


class AnthropicProvider:
    """Anthropic Claude LLM provider implementation."""

    def __init__(self, model: str = "claude-3-haiku-20240307"):
        """Initialize Anthropic provider.

        Args:
            model: Anthropic model to use
        """
        self.settings = settings
        self.model = model
        self.base_url = "https://api.anthropic.com/v1"
        self.api_key = getattr(self.settings, "anthropic_api_key", None)

        if not self.api_key:
            logger.warning("Anthropic API key not configured")

    async def complete(
        self,
        prompt: str,
        user_id: str,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        system_prompt: str | None = None,
        timeout: float | None = None,
    ) -> LLMResponse:
        """Complete text using Anthropic Claude API.

        Args:
            prompt: Text prompt for completion
            user_id: User identifier
            model: Model override
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            system_prompt: System prompt/instructions
            timeout: Request timeout

        Returns:
            LLMResponse with completion
        """
        if not self.api_key:
            raise Exception("Anthropic API key not configured")

        # Use provided model or default
        model_to_use = model or self.model

        # Prepare request
        request_data = {
            "model": model_to_use,
            "max_tokens": max_tokens or 150,
            "messages": [{"role": "user", "content": prompt}],
        }

        if system_prompt:
            request_data["system"] = system_prompt

        if temperature is not None:
            request_data["temperature"] = temperature

        headers = {"x-api-key": self.api_key, "Content-Type": "application/json", "anthropic-version": "2023-06-01"}

        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=timeout or 25.0) as client:
                response = await client.post(f"{self.base_url}/messages", json=request_data, headers=headers)
                response.raise_for_status()

                data = response.json()

                # Extract response
                content = data["content"][0]
                response_text = content["text"]
                stop_reason = data.get("stop_reason", "end_turn")

                # Calculate usage and cost
                usage = data.get("usage", {})
                input_tokens = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)
                total_tokens = input_tokens + output_tokens

                # Estimate cost
                cost = self._calculate_cost(model_to_use, input_tokens, output_tokens)

                processing_time = time.time() - start_time

                logger.debug(f"Anthropic completion: {total_tokens} tokens, €{cost:.4f}, {processing_time:.2f}s")

                return LLMResponse(
                    text=response_text,
                    model=model_to_use,
                    tokens_used=total_tokens,
                    cost=cost,
                    processing_time=processing_time,
                    provider="anthropic",
                    response_metadata={
                        "stop_reason": stop_reason,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                    },
                )

        except httpx.HTTPStatusError as e:
            logger.error(f"Anthropic API error {e.response.status_code}: {e}")
            raise
        except httpx.TimeoutException as e:
            logger.error(f"Anthropic API timeout: {e}")
            raise TimeoutError("Anthropic API request timed out")
        except Exception as e:
            logger.error(f"Anthropic API unexpected error: {e}")
            raise

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate approximate cost in EUR."""
        # Approximate Anthropic pricing (as of 2024)
        pricing = {
            "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},  # Per 1K tokens
            "claude-3-sonnet-20240229": {"input": 0.003, "output": 0.015},
            "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
        }

        # Default to Haiku pricing if model not found
        rates = pricing.get(model, pricing["claude-3-haiku-20240307"])

        input_cost = (input_tokens / 1000) * rates["input"]
        output_cost = (output_tokens / 1000) * rates["output"]

        return input_cost + output_cost

    async def health_check(self) -> dict[str, Any]:
        """Perform health check on Anthropic API."""
        if not self.api_key:
            return {"status": "error", "message": "API key not configured"}

        try:
            # Simple test request
            test_response = await self.complete(prompt="Hello", user_id="health_check", max_tokens=5, timeout=10.0)

            return {"status": "healthy", "model": self.model, "response_time": test_response.processing_time}

        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
