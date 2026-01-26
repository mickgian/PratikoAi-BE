"""Keyword extraction for web verification.

Extracts search keywords from user queries with context-aware ordering
for optimal Brave Search results.
"""

import re

from app.core.logging import logger


class KeywordExtractor:
    """Extracts and orders keywords for web search queries."""

    # Italian stop words to exclude (common words that don't add search value)
    STOP_WORDS = {
        # Articles
        "il",
        "lo",
        "la",
        "i",
        "gli",
        "le",
        "un",
        "uno",
        "una",
        # Prepositions
        "di",
        "a",
        "da",
        "in",
        "con",
        "su",
        "per",
        "tra",
        "fra",
        # Conjunctions
        "e",
        "o",
        "ma",
        "se",
        "che",
        "chi",
        # Question words
        "come",
        "dove",
        "quando",
        "perché",
        "quale",
        "quali",
        # Pronouns/demonstratives
        "questo",
        "quello",
        "suo",
        "loro",
        "mio",
        "tuo",
        # Common verbs
        "essere",
        "avere",
        "può",
        "sono",
        "è",
        "sia",
        "viene",
        "fare",
        # Preposition contractions
        "nel",
        "nella",
        "nei",
        "nelle",
        "del",
        "della",
        "dei",
        "delle",
        "al",
        "alla",
        "ai",
        "alle",
        "dal",
        "dalla",
        "sul",
        "sulla",
        # Other common words
        "non",
        "più",
        "anche",
        "solo",
        "già",
        "cosa",
        "tutto",
        "molto",
        # Question-specific
        "inclusa",
        "incluso",
        "rientra",
        "rientrare",
        "previsto",
        "prevista",
        # Conversational verbs
        "parlami",
        "dimmi",
        "spiegami",
        "raccontami",
        "descrivi",
        "vorrei",
        "sapere",
        "conoscere",
        "capire",
    }

    def extract_search_keywords(self, query: str) -> list[str]:
        """DEV-245 Phase 3.9: Extract significant keywords from query for Brave search.

        Natural language questions don't search well. Converting to keywords:
        "L'IRAP può essere inclusa nella rottamazione quinquies?"
        -> ["irap", "rottamazione", "quinquies"]

        Args:
            query: The user query (natural language)

        Returns:
            List of significant keywords for search (lowercase), max 5 keywords
        """
        # Extract words (alphanumeric including Italian accents, 3+ chars)
        words = re.findall(r"\b[a-zA-ZàèéìòùÀÈÉÌÒÙ]{3,}\b", query.lower())

        # Filter out stop words, keep significant terms
        keywords = [w for w in words if w not in self.STOP_WORDS]

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique.append(kw)

        return unique[:5]  # Cap at 5 keywords for focused search

    def extract_search_keywords_with_context(
        self,
        query: str,
        messages: list[dict] | None = None,
        topic_keywords: list[str] | None = None,
    ) -> list[str]:
        """DEV-245 Phase 3.9: Extract keywords with context-first ordering.

        CRITICAL: Do NOT remove this method - it ensures Brave search uses
        optimal keyword ordering for follow-up queries.

        Industry standard (BruceClay): "Most relevant keyword first"

        For follow-up queries, orders keywords so conversation context comes first,
        then new keywords from the follow-up.

        Example:
            - Context: "parlami della rottamazione quinquies"
            - Follow-up: "L'IRAP può essere inclusa nella rottamazione quinquies?"
            - Result: ["rottamazione", "quinquies", "irap"] (context first!)
            - Brave search: "rottamazione quinquies irap 2026"
            - NOT: "irap rottamazione quinquies 2026"

        DEV-245 Phase 5.3: Added topic_keywords parameter.
            If topic_keywords is provided, use those as context keywords (from state).
            This ensures the main topic is NEVER lost, even at Q4+ where messages[-4:]
            would exclude the first query/response.

        Args:
            query: The user query
            messages: Conversation history for context extraction
            topic_keywords: Pre-extracted topic keywords from state (Phase 5.3)

        Returns:
            List of keywords ordered: context keywords first, then new keywords
        """
        # Extract all keywords from query
        all_keywords = self.extract_search_keywords(query)

        # DEV-245 Phase 5.3: Check for topic_keywords FIRST before early return
        # If we have topic_keywords, we need to add them even if query has few keywords
        # DEV-245 Phase 5.4: Type safety - validate topic_keywords is actually a list
        if topic_keywords and isinstance(topic_keywords, list):
            # Use pre-extracted topic keywords from state (industry standard approach)
            # IMPORTANT: We ADD topic_keywords to the result, not just use them for ordering
            # This ensures the main topic is always in the search, even if not mentioned in query
            context_keywords = set(topic_keywords)
            logger.debug(
                "phase53_using_topic_keywords_web_verification",
                topic_keywords=topic_keywords,
            )

            # Combine: topic keywords first (context), then new query keywords
            new_keywords = [kw for kw in all_keywords if kw not in context_keywords]
            result = list(topic_keywords) + new_keywords
            result = result[:5]  # Cap at 5 keywords

            # Log for debugging
            if new_keywords:
                logger.debug(
                    "phase53_keyword_ordering_web_verification",
                    topic_keywords=topic_keywords,
                    query_keywords=all_keywords,
                    combined=result,
                )

            return result

        if len(all_keywords) <= 2:
            return all_keywords  # No reordering needed

        # DEV-245 Phase 5.3: Fallback path (no topic_keywords provided)
        # Extract context from messages for reordering
        fallback_context_keywords: set[str] = set()

        if messages:
            # DEV-245 Phase 3.9.3: Skip the LAST assistant message - it's the one we're verifying
            # At Step 100, the newest assistant message is the response just generated by LLM.
            # We want context from PREVIOUS assistant responses, not the current one.
            # Without this, ALL keywords become "context" and no reordering happens.
            #
            # Example:
            #   messages = [user1, assistant1 (old), user2, assistant2 (NEW)]
            #   We want context from assistant1, NOT assistant2
            messages_to_check = list(messages[-4:])  # Copy to avoid mutating original

            # Skip the last message if it's an assistant message (the one we're verifying)
            if messages_to_check:
                last_msg = messages_to_check[-1]
                if isinstance(last_msg, dict):
                    last_role = last_msg.get("role") or last_msg.get("type", "")
                else:
                    last_role = getattr(last_msg, "role", "") or getattr(last_msg, "type", "")

                if last_role in ("assistant", "ai"):
                    messages_to_check = messages_to_check[:-1]  # Exclude the newest assistant

            # Find context keywords from conversation history (excluding newest assistant)
            for msg in reversed(messages_to_check):
                # Handle both dict and LangChain message objects
                if isinstance(msg, dict):
                    # DEV-245 Phase 3.9.2: Check BOTH keys - dicts may use "role" (OpenAI)
                    # or "type" (LangChain serialization format)
                    role = msg.get("role") or msg.get("type", "")
                    content = msg.get("content", "")
                else:
                    role = getattr(msg, "role", "") or getattr(msg, "type", "")
                    content = getattr(msg, "content", "") or ""

                # DEV-245 Phase 3.9.1: Only extract context from ASSISTANT messages
                # User messages include the current follow-up query which would
                # incorrectly add new keywords to context, breaking the ordering
                if role in ("assistant", "ai") and content:
                    # Extract keywords from context message (first 500 chars)
                    msg_keywords = self.extract_search_keywords(content[:500])
                    fallback_context_keywords.update(msg_keywords[:5])

        # Separate: context keywords vs new keywords
        context_first = [kw for kw in all_keywords if kw in fallback_context_keywords]
        new_keywords = [kw for kw in all_keywords if kw not in fallback_context_keywords]

        result = context_first + new_keywords

        # Log for debugging keyword ordering
        if context_first and new_keywords:
            logger.debug(
                "web_verification_keyword_ordering",
                original_order=all_keywords,
                context_keywords=list(fallback_context_keywords)[:5],
                reordered=result,
            )

        return result

    def build_verification_query(
        self,
        user_query: str,
        kb_sources: list[dict],  # Kept for API compatibility but not used
        messages: list[dict] | None = None,
        topic_keywords: list[str] | None = None,
    ) -> str:
        """DEV-245 Phase 3.9: Build keyword-based search query with context-first ordering.

        CRITICAL: This method uses keyword extraction instead of full natural language
        query because Brave search returns better results with keywords.

        Previous behavior (wrong): "L'IRAP può essere inclusa nella rottamazione quinquies? 2026"
        Current behavior (correct): "rottamazione quinquies irap 2026"

        DEV-245 Phase 5.3: Added topic_keywords for long conversation support.

        Args:
            user_query: Original user query
            kb_sources: KB sources (unused - kept for API compatibility)
            messages: Conversation history for context-aware keyword ordering
            topic_keywords: Pre-extracted topic keywords from state (Phase 5.3)

        Returns:
            Keyword-based search query string
        """
        # DEV-245 Phase 3.9: Use context-aware keyword extraction
        # DEV-245 Phase 5.3: Pass topic_keywords for long conversation support
        keywords = self.extract_search_keywords_with_context(user_query, messages, topic_keywords)

        if keywords:
            query = " ".join(keywords)
        else:
            # Fallback to original query if no keywords extracted
            query = user_query.strip()

        # DEV-245 Phase 3.9.1: Removed automatic year suffix per user feedback
        # Let Brave search naturally without forcing a year

        logger.debug(
            "web_verification_query_built",
            original_query=user_query[:80],
            keywords=keywords,
            final_query=query,
        )

        return query


# Singleton instance
keyword_extractor = KeywordExtractor()
