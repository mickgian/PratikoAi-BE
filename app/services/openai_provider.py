"""
OpenAI Provider for LLM API calls.

This module provides an interface to OpenAI's API with proper error handling,
cost tracking, and response formatting for integration with the resilient LLM service.
"""

import asyncio
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass
import httpx

from app.models.query import LLMResponse
from app.core.logging import logger
from app.core.config import settings


@dataclass
class OpenAIResponse:
    """OpenAI API response structure."""
    text: str
    model: str
    tokens_used: int
    cost: float
    finish_reason: str


class OpenAIProvider:
    """OpenAI LLM provider implementation."""
    
    def __init__(self, model: str = "gpt-4o-mini"):
        """
        Initialize OpenAI provider.
        
        Args:
            model: OpenAI model to use
        """
        self.settings = settings
        self.model = model
        self.base_url = "https://api.openai.com/v1"
        self.api_key = getattr(self.settings, 'openai_api_key', None)
        
        if not self.api_key:
            logger.warning("OpenAI API key not configured")
    
    async def complete(
        self,
        prompt: str,
        user_id: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None,
        timeout: Optional[float] = None
    ) -> LLMResponse:
        """
        Complete text using OpenAI API.
        
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
            raise Exception("OpenAI API key not configured")
        
        # Use provided model or default
        model_to_use = model or self.model
        
        # Prepare messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Prepare request
        request_data = {
            "model": model_to_use,
            "messages": messages,
            "max_tokens": max_tokens or 150,
            "temperature": temperature or 0.7,
            "user": user_id
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=timeout or 30.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=request_data,
                    headers=headers
                )
                response.raise_for_status()
                
                data = response.json()
                
                # Extract response
                choice = data["choices"][0]
                response_text = choice["message"]["content"]
                finish_reason = choice["finish_reason"]
                
                # Calculate usage and cost
                usage = data.get("usage", {})
                total_tokens = usage.get("total_tokens", 0)
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                
                # Estimate cost (approximate rates)
                cost = self._calculate_cost(model_to_use, prompt_tokens, completion_tokens)
                
                processing_time = time.time() - start_time
                
                logger.debug(
                    f"OpenAI completion: {total_tokens} tokens, "
                    f"€{cost:.4f}, {processing_time:.2f}s"
                )
                
                return LLMResponse(
                    text=response_text,
                    model=model_to_use,
                    tokens_used=total_tokens,
                    cost=cost,
                    processing_time=processing_time,
                    provider="openai",
                    metadata={
                        "finish_reason": finish_reason,
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens
                    }
                )
                
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenAI API error {e.response.status_code}: {e}")
            raise
        except httpx.TimeoutException as e:
            logger.error(f"OpenAI API timeout: {e}")
            raise asyncio.TimeoutError("OpenAI API request timed out")
        except Exception as e:
            logger.error(f"OpenAI API unexpected error: {e}")
            raise
    
    def _calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate approximate cost in EUR."""
        # Approximate OpenAI pricing (as of 2024)
        pricing = {
            "gpt-4": {"input": 0.03, "output": 0.06},  # Per 1K tokens
            "gpt-4o": {"input": 0.005, "output": 0.015},
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015}
        }
        
        # Default to GPT-4 pricing if model not found
        rates = pricing.get(model, pricing["gpt-4"])
        
        input_cost = (prompt_tokens / 1000) * rates["input"]
        output_cost = (completion_tokens / 1000) * rates["output"]
        
        return input_cost + output_cost
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on OpenAI API."""
        if not self.api_key:
            return {"status": "error", "message": "API key not configured"}
        
        try:
            # Simple test request
            test_response = await self.complete(
                prompt="Hello",
                user_id="health_check",
                max_tokens=5,
                timeout=10.0
            )
            
            return {
                "status": "healthy",
                "model": self.model,
                "response_time": test_response.processing_time
            }
            
        except Exception as e:
            return {
                "status": "unhealthy", 
                "error": str(e)
            }