"""LLM synthesis for web verification.

Synthesizes KB answers with web search results using LLM.
"""

from app.core.logging import logger

from .exclusion_detector import _web_has_genuine_exclusions


class ResponseSynthesizer:
    """Synthesizes KB answers with web content using LLM."""

    async def synthesize_with_brave(
        self,
        kb_answer: str,
        brave_summary: str,
        user_query: str,
    ) -> str | None:
        """Use LLM to merge KB answer with Brave AI insights.

        Creates a comprehensive response that combines:
        - KB answer accuracy and structure
        - Brave AI additional context and nuances
        - Important conditions and warnings

        Args:
            kb_answer: Original answer from knowledge base
            brave_summary: AI summary from Brave Search
            user_query: User's original question

        Returns:
            Synthesized response or None on error
        """
        try:
            from app.core.llm.factory import get_llm_factory
            from app.schemas.chat import Message

            # DEV-245 Phase 5.14: Check if Brave summary has genuine exclusions
            # Wrap brave_summary in a list structure for _web_has_genuine_exclusions
            has_exclusions, matched_keywords = _web_has_genuine_exclusions([{"snippet": brave_summary}])

            logger.info(
                "DEV245_synthesis_brave_exclusion_check",
                has_exclusions=has_exclusions,
                matched_keywords=matched_keywords[:3] if matched_keywords else [],
                will_use_inclusion_exclusion_format=has_exclusions,
            )

            logger.info(
                "BRAVE_synthesis_starting",
                kb_answer_length=len(kb_answer),
                brave_summary_length=len(brave_summary),
                user_query_length=len(user_query),
            )

            # DEV-245 Phase 5.14: Build conditional instruction based on exclusion presence
            if has_exclusions:
                exclusion_instruction = f"""4. **ESCLUSIONI TROVATE**: Brave indica esclusioni ({", ".join(matched_keywords[:3])}).
   Evidenziale chiaramente usando questo formato:
   - \u2705 Incluso: [caso ammissibile con riferimento normativo se presente]
   - \u274c Escluso: [caso NON ammissibile]
   Esempio: se IRAP da dichiarazione \u00e8 inclusa ma IRAP da accertamento \u00e8 esclusa, d\u00ec ENTRAMBE le cose!"""
            else:
                exclusion_instruction = """4. **FORMATO**: Usa un formato narrativo chiaro.
   NON usare \u2705/\u274c perch\u00e9 Brave non indica esclusioni specifiche."""

            # Build synthesis prompt
            synthesis_prompt = f"""Combina queste due risposte in una risposta completa e coerente.

DOMANDA UTENTE: {user_query}

RISPOSTA KB (base affidabile, da mantenere come struttura principale):
{kb_answer}

APPROFONDIMENTO WEB (Brave AI - da integrare se aggiunge valore):
{brave_summary}

ISTRUZIONI:
1. Mantieni la risposta KB come base principale
2. Integra le informazioni aggiuntive da Brave SOLO se pertinenti e utili
3. Aggiungi condizioni, requisiti o avvertenze importanti dal web
{exclusion_instruction}
5. Se il web indica condizioni specifiche (articoli di legge, requisiti), includile esplicitamente
6. Mantieni un tono professionale in italiano
7. IMPORTANTE: NON aggiungere frasi generiche come "Se hai domande..." o "Non esitare a chiedere" alla fine
8. Termina con informazioni concrete, non con chiusure generiche

RISPOSTA COMBINATA:"""

            factory = get_llm_factory()
            # Use the default/basic provider for synthesis
            from app.core.config import settings

            provider = factory.create_provider(
                provider_type="openai",
                model=settings.LLM_MODEL or "gpt-4o-mini",
            )

            messages = [
                Message(
                    role="system",
                    content="Sei un esperto di normativa fiscale italiana. Il tuo compito \u00e8 combinare informazioni da fonti diverse in risposte chiare e complete. NON aggiungere mai frasi di chiusura generiche.",
                ),
                Message(role="user", content=synthesis_prompt),
            ]

            response = await provider.chat_completion(
                messages=messages,
                temperature=0.3,  # Low temperature for consistency
                max_tokens=1000,
            )

            synthesized = response.content.strip() if response.content else None

            if synthesized:
                logger.info(
                    "BRAVE_synthesis_complete",
                    synthesized_length=len(synthesized),
                    original_kb_length=len(kb_answer),
                )

            return synthesized

        except Exception as e:
            logger.error(
                "BRAVE_synthesis_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    async def synthesize_with_snippets(
        self,
        kb_answer: str,
        web_results: list[dict],
        user_query: str,
    ) -> str | None:
        """Use LLM to merge KB answer with web snippets (fallback when Brave AI unavailable).

        Creates a comprehensive response that combines:
        - KB answer accuracy and structure
        - Web snippets for additional context
        - Important conditions and warnings from web sources

        Args:
            kb_answer: Original answer from knowledge base
            web_results: List of web search results with snippets
            user_query: User's original question

        Returns:
            Synthesized response or None on error
        """
        try:
            from app.core.llm.factory import get_llm_factory
            from app.schemas.chat import Message

            # Build web context from snippets
            web_context_parts = []
            for i, result in enumerate(web_results[:5], 1):  # Limit to top 5 results
                title = result.get("title", "Fonte sconosciuta")
                snippet = result.get("snippet", "")
                if snippet:
                    web_context_parts.append(f"{i}. {title}:\n   {snippet}")

            if not web_context_parts:
                logger.debug("BRAVE_synthesis_snippets_no_context")
                return None

            web_context = "\n\n".join(web_context_parts)

            # DEV-245 Phase 5.14: Check if web has genuine exclusions
            # Only use checkmark/cross format when web results ACTUALLY contain exclusion keywords
            has_exclusions, matched_keywords = _web_has_genuine_exclusions(web_results)

            logger.info(
                "DEV245_synthesis_exclusion_check",
                has_exclusions=has_exclusions,
                matched_keywords=matched_keywords[:3] if matched_keywords else [],
                will_use_inclusion_exclusion_format=has_exclusions,
            )

            logger.info(
                "BRAVE_synthesis_snippets_starting",
                kb_answer_length=len(kb_answer),
                web_snippets_count=len(web_context_parts),
                web_context_length=len(web_context),
            )

            # DEV-245 Phase 5.14: Build conditional instruction based on exclusion presence
            if has_exclusions:
                exclusion_instruction = f"""4. **ESCLUSIONI TROVATE**: I risultati web contengono esclusioni ({", ".join(matched_keywords[:3])}).
   Evidenziale chiaramente usando questo formato:
   - \u2705 Incluso: [caso ammissibile con riferimento normativo se presente]
   - \u274c Escluso: [caso NON ammissibile]
   Esempio: se IRAP da dichiarazione \u00e8 inclusa ma IRAP da accertamento \u00e8 esclusa, d\u00ec ENTRAMBE le cose!"""
            else:
                exclusion_instruction = """4. **FORMATO**: Usa un formato narrativo chiaro.
   NON usare \u2705/\u274c perch\u00e9 i risultati web non indicano esclusioni specifiche."""

            synthesis_prompt = f"""Arricchisci la risposta KB con informazioni rilevanti dai risultati web.

DOMANDA UTENTE: {user_query}

RISPOSTA KB (base affidabile):
{kb_answer}

RISULTATI WEB (da integrare se aggiungono valore):
{web_context}

ISTRUZIONI:
1. Mantieni la risposta KB come base principale - non modificare le informazioni corrette
2. Integra SOLO informazioni aggiuntive e pertinenti dai risultati web
3. Se i risultati web indicano condizioni, limitazioni o requisiti, aggiungili
{exclusion_instruction}
5. Se il web indica condizioni specifiche (articoli di legge, requisiti), includile esplicitamente
6. Mantieni un tono professionale in italiano
7. IMPORTANTE: NON aggiungere frasi generiche come "Se hai domande..." alla fine
8. Se i risultati web non aggiungono nulla di utile, restituisci solo la risposta KB migliorata

RISPOSTA ARRICCHITA:"""

            factory = get_llm_factory()
            from app.core.config import settings

            provider = factory.create_provider(
                provider_type="openai",
                model=settings.LLM_MODEL or "gpt-4o-mini",
            )

            messages = [
                Message(
                    role="system",
                    content="Sei un esperto di normativa fiscale italiana. Arricchisci risposte esistenti con informazioni web pertinenti. NON aggiungere mai frasi di chiusura generiche.",
                ),
                Message(role="user", content=synthesis_prompt),
            ]

            response = await provider.chat_completion(
                messages=messages,
                temperature=0.3,
                max_tokens=1000,
            )

            synthesized = response.content.strip() if response.content else None

            if synthesized:
                # DEV-245 Phase 2: Don't append inline "sources" citations
                # Web sources are now in kb_sources_metadata and appear in the unified
                # Fonti section alongside KB sources (with "web" label).
                # Removing inline citations to avoid duplicate display.
                logger.info(
                    "BRAVE_synthesis_snippets_complete",
                    synthesized_length=len(synthesized),
                    original_kb_length=len(kb_answer),
                )

            return synthesized

        except Exception as e:
            logger.error(
                "BRAVE_synthesis_snippets_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            return None


# Singleton instance
response_synthesizer = ResponseSynthesizer()
