"""LLM-based query reformulation for short follow-up queries.

DEV-245: Industry-standard approach used by Google, Perplexity, and ChatGPT.
Semantic reformulation is more effective than keyword prepending.
"""

import logging
from typing import Any

from .constants import SHORT_QUERY_THRESHOLD

logger = logging.getLogger(__name__)


async def reformulate_short_query_llm(query: str, messages: list[dict[str, Any]] | None) -> str:
    """Use LLM to reformulate short follow-up queries into complete questions.

    Example:
        - Previous response: discussion about "rottamazione quinquies"
        - Short query: "e l'irap?"
        - Reformulated: "L'IRAP può essere inclusa nella rottamazione quinquies?"

    Args:
        query: The user's query (potentially short/incomplete)
        messages: Conversation history from state["messages"]

    Returns:
        The reformulated query if short, or original query if >= 5 words
    """
    words = query.strip().split()
    word_count = len(words)

    # If query is long enough, no reformulation needed
    if word_count >= SHORT_QUERY_THRESHOLD:
        return query

    # No messages, can't reformulate
    if not messages:
        logger.info(f"short_query_no_reformulation: reason=no_conversation_history, word_count={word_count}")
        return query

    # Get last assistant message as context (more relevant than user messages)
    last_assistant_content: str | None = None
    for msg in reversed(messages):
        if isinstance(msg, dict):
            role = msg.get("role", "")
            if role in ("assistant", "ai"):
                last_assistant_content = (msg.get("content") or "")[:500]
                break
        else:
            msg_type = getattr(msg, "type", "") or getattr(msg, "role", "")
            if msg_type in ("assistant", "ai"):
                last_assistant_content = (getattr(msg, "content", "") or "")[:500]
                break

    if not last_assistant_content:
        logger.info(f"short_query_no_reformulation: reason=no_assistant_context, word_count={word_count}")
        return query

    # Build reformulation prompt
    prompt = f"""Reformula questa domanda breve in una domanda completa e autonoma.

Contesto della risposta precedente:
{last_assistant_content}

Domanda breve dell'utente: "{query}"

REGOLE:
- Rispondi SOLO con la domanda riformulata
- Nessuna spiegazione o preambolo
- La domanda deve essere comprensibile senza contesto

Esempio: "e l'imu?" dopo discussione su rottamazione → "L'IMU può essere inclusa nella rottamazione quinquies?"
"""

    try:
        from openai import AsyncOpenAI

        from app.core.llm.model_config import ModelTier, get_model_config

        config = get_model_config()  # Get singleton (no args)
        model = config.get_model(ModelTier.BASIC)  # gpt-4o-mini for fast reformulation
        client = AsyncOpenAI()

        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=100,
        )

        reformulated = (response.choices[0].message.content or "").strip()

        # Clean up common LLM artifacts
        reformulated = reformulated.strip('"').strip("'")

        # Validate we got something meaningful
        if not reformulated or len(reformulated) < 5:
            logger.warning(f"short_query_reformulation_invalid: original={query!r}, result={reformulated!r}")
            return query

        logger.info(f"short_query_reformulated_llm: original={query!r}, reformulated={reformulated!r}")

        return reformulated

    except Exception as e:
        logger.warning(f"short_query_reformulation_failed: error={e}, query={query!r}")
        return query  # Fallback to original
