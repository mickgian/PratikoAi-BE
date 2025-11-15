"""Query Normalizer Service

LLM-based query normalization for Italian document queries.
Handles linguistic variations that regex cannot:
- Written numbers ("sessantaquattro" → "64")
- Abbreviations ("ris" → "risoluzione")
- Typos ("risouzione" → "risoluzione")
- Word order variations ("la 64" → document reference)

TDD GREEN Phase 2-1: Minimal implementation to pass unit tests
"""

import json
from typing import (
    Dict,
    Optional,
)

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.core.logging import logger


class QueryNormalizer:
    """LLM-based query normalization for Italian tax/legal document queries.

    Extracts document references (type + number) from natural language queries
    using GPT-4o-mini for maximum linguistic flexibility.
    """

    def __init__(self):
        """Initialize query normalizer with OpenAI client"""
        self.config = get_settings()
        self.client = AsyncOpenAI(api_key=self.config.OPENAI_API_KEY)

    async def normalize(self, query: str) -> dict[str, str] | None:
        """Normalize query to extract document reference.

        Args:
            query: Italian natural language query

        Returns:
            {"type": "risoluzione", "number": "64"} if document found
            None if no document reference or on error

        Examples:
            - "risoluzione sessantaquattro" → {"type": "risoluzione", "number": "64"}
            - "ris 64" → {"type": "risoluzione", "number": "64"}
            - "la 64 dell'agenzia" → {"type": "risoluzione", "number": "64"}
            - "come calcolare le tasse" → None
        """
        try:
            # Call LLM with structured prompt
            response = await self.client.chat.completions.create(
                model=self.config.QUERY_NORMALIZATION_MODEL,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": query},
                ],
                temperature=0,  # Deterministic for consistency
                max_tokens=100,  # Small response (just JSON)
                timeout=2.0,  # Fast timeout for production use
            )

            # Parse JSON response
            result_text = response.choices[0].message.content.strip()
            result = json.loads(result_text)

            # Return None if no document found
            if result.get("type") is None:
                logger.info("query_normalization_no_document_found", query=query[:80])
                return None

            # Success - document reference extracted
            logger.info(
                "query_normalization_success",
                query=query[:80],
                extracted_type=result.get("type"),
                extracted_number=result.get("number"),
            )

            return result

        except json.JSONDecodeError as e:
            # LLM returned invalid JSON - graceful degradation
            logger.warning(
                "query_normalization_invalid_json",
                query=query[:80],
                error=str(e),
                reason="llm_returned_non_json_response",
            )
            return None

        except TimeoutError as e:
            # LLM timeout - graceful degradation
            logger.warning("query_normalization_timeout", query=query[:80], error=str(e), reason="llm_took_too_long")
            return None

        except Exception as e:
            # Any other error - graceful degradation
            logger.warning(
                "query_normalization_error",
                query=query[:80],
                error=str(e),
                error_type=type(e).__name__,
                reason="unexpected_error",
            )
            return None

    def _get_system_prompt(self) -> str:
        """Get system prompt for LLM normalization.

        Returns structured JSON with document type and number extraction.
        """
        return """Extract document reference from this Italian tax/legal query.

If the query mentions a specific document (risoluzione, circolare, interpello, risposta, decreto, etc.) with a number, extract it.

Rules:
1. Convert written numbers to digits: "sessantaquattro" → "64", "venti" → "20"
2. Expand abbreviations: "ris" → "risoluzione", "circ" → "circolare"
3. Correct typos: "risouzione" → "risoluzione", "risluzione" → "risoluzione"
4. Ignore conversational words: "cosa dice", "mi serve", "parlami di", "la", "dell'"
5. Infer document type from context if possible

Return ONLY valid JSON (no other text):
{
  "type": "risoluzione",
  "number": "64"
}

If no document reference found, return:
{"type": null}

Examples:
- "risoluzione sessantaquattro" → {"type": "risoluzione", "number": "64"}
- "ris 64" → {"type": "risoluzione", "number": "64"}
- "cosa dice la 64?" → {"type": "risoluzione", "number": "64"}
- "come calcolare le tasse" → {"type": null}
"""


# Export for backward compatibility
__all__ = ["QueryNormalizer"]
