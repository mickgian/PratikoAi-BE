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
    Any,
    Dict,
    Optional,
    cast,
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

    async def normalize(
        self,
        query: str,
        conversation_context: str | None = None,
    ) -> dict[str, str | None] | None:
        """Normalize query to extract document reference.

        Args:
            query: Italian natural language query
            conversation_context: Optional recent conversation for typo correction (DEV-251)

        Returns:
            {"type": "risoluzione", "number": "64", "year": null} if document found
            None if no document reference or on error

        Examples:
            - "risoluzione sessantaquattro" → {"type": "risoluzione", "number": "64", "year": null}
            - "messaggio 3585 INPS" → {"type": "messaggio", "number": "3585", "year": null}
            - "DPR 1124/1965" → {"type": "DPR", "number": "1124", "year": "1965"}
            - "come calcolare le tasse" → None
        """
        try:
            # Call LLM with structured prompt
            response = await self.client.chat.completions.create(
                model=self.config.QUERY_NORMALIZATION_MODEL,
                messages=[
                    {"role": "system", "content": self._get_system_prompt(conversation_context)},
                    {"role": "user", "content": query},
                ],
                temperature=0,  # Deterministic for consistency
                max_tokens=100,  # Small response (just JSON)
                timeout=2.0,  # Fast timeout for production use
            )

            # Parse JSON response
            result_text = response.choices[0].message.content.strip()
            result = cast(dict[str, str | None], json.loads(result_text))

            # Check if we have useful information (type OR keywords)
            has_document_ref = result.get("type") is not None
            has_keywords = bool(result.get("keywords"))

            # Return None only if NO useful information extracted
            if not has_document_ref and not has_keywords:
                logger.info("query_normalization_no_useful_info", query=query[:80])
                return None

            # Success - document reference and/or keywords extracted
            logger.info(
                "query_normalization_success",
                query=query[:80],
                extracted_type=result.get("type"),
                extracted_number=result.get("number"),
                extracted_year=result.get("year"),
                extracted_keywords=result.get("keywords", []),
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

    def _get_system_prompt(self, conversation_context: str | None = None) -> str:
        """Get system prompt for LLM normalization.

        Args:
            conversation_context: Optional conversation for typo correction (DEV-251)

        Returns structured JSON with document type, number, year, and keywords extraction.
        Supports all Italian government document sources and formats.
        Keywords enable semantic search when no document number is found.
        """
        base_prompt = """Extract document reference AND search keywords from this Italian tax/legal query.

Document types to recognize:
- Agenzia Entrate: risoluzione, circolare, interpello, risposta
- INPS: messaggio, circolare
- Judicial: sentenza, ordinanza, provvedimento
- Legislative: decreto, DPR, DL, DPCM, legge

Number formats to recognize:
- Standard: "n. 64", "n.64", "numero 64"
- INPS style: "messaggio numero 3585 del 27-11-2025"
- Compound: "DPR 1124/1965", "1124 del 1965"
- Slash notation: "15/E", "45/E/2024"

Keywords extraction rules:
- Extract SEMANTIC keywords (core concepts, not stopwords)
- For topic-based queries, keywords enable search when no number exists
- Normalize to base form: "sicurezza sul lavoro" → ["sicurezza", "lavoro"]
- Include entity names: "INPS", "IVA", "TFR"
- Include years if mentioned: "bonus 2025" → keywords include "2025"

Rules:
1. Convert written numbers to digits: "sessantaquattro" → "64", "venti" → "20"
2. Expand abbreviations: "ris" → "risoluzione", "circ" → "circolare", "msg" → "messaggio", "ord" → "ordinanza"
3. Correct typos: "risouzione" → "risoluzione", "risluzione" → "risoluzione"
4. Ignore conversational words: "cosa dice", "mi serve", "parlami di", "la", "dell'"
5. Infer document type from context if possible
6. For compound references (e.g., "DPR 1124/1965"), extract both number and year
7. ALWAYS extract keywords - even for pure topic queries without document numbers

Return ONLY valid JSON (no other text):
{
  "type": "risoluzione",
  "number": "64",
  "year": null,
  "keywords": []
}

For topic-based queries without document number:
{
  "type": "DL",
  "number": null,
  "year": null,
  "keywords": ["sicurezza", "lavoro"]
}

For general topic queries:
{
  "type": null,
  "number": null,
  "year": "2025",
  "keywords": ["bonus", "psicologo"]
}

Examples:
- "risoluzione sessantaquattro" → {"type": "risoluzione", "number": "64", "year": null, "keywords": []}
- "ris 64" → {"type": "risoluzione", "number": "64", "year": null, "keywords": []}
- "messaggio 3585 INPS" → {"type": "messaggio", "number": "3585", "year": null, "keywords": ["INPS"]}
- "DPR 1124/1965" → {"type": "DPR", "number": "1124", "year": "1965", "keywords": []}
- "decreto 212 del 2023" → {"type": "decreto", "number": "212", "year": "2023", "keywords": []}
- "DL sicurezza lavoro" → {"type": "DL", "number": null, "year": null, "keywords": ["sicurezza", "lavoro"]}
- "bonus psicologo 2025" → {"type": null, "number": null, "year": "2025", "keywords": ["bonus", "psicologo"]}
- "come calcolare le tasse" → {"type": null, "number": null, "year": null, "keywords": ["tasse", "calcolo"]}
"""

        # DEV-251: Add conversation context for typo correction
        if conversation_context and conversation_context.strip():
            context_section = f"""

CONVERSATION CONTEXT (use for typo correction):
{conversation_context}

TYPO CORRECTION RULES:
- If user query contains a term similar to one discussed in context, correct it
- Example: Context discusses "IRAP", query says "l'rap" → correct to "IRAP"
- Example: Context discusses "IMU", query says "l'imu" or "l'inu" → correct to "IMU"
- Add corrected term to keywords if applicable
"""
            return base_prompt + context_section

        return base_prompt


# Export for backward compatibility
__all__ = ["QueryNormalizer"]
