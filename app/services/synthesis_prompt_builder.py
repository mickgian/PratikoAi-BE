"""Synthesis Prompt Builder Service for DEV-192.

Builds complete prompts for LLM synthesis step combining system prompt,
context from retrieval, and user query per Section 13.8.5.

Usage:
    from app.services.synthesis_prompt_builder import SynthesisPromptBuilder

    builder = SynthesisPromptBuilder()
    user_prompt = builder.build(context=formatted_context, query=user_query)
    system_prompt = builder.get_system_prompt()
"""

from app.core.logging import logger
from app.core.prompts.synthesis_critical import (
    HIERARCHY_RULES,
    SYNTHESIS_SYSTEM_PROMPT,
    VERDETTO_OPERATIVO_TEMPLATE,
)


class SynthesisPromptBuilder:
    """Builder for synthesis LLM prompts.

    Constructs prompts that include:
    - System prompt with 4 compiti (tasks)
    - Context from retrieval with metadata
    - User query
    - Instructions for Verdetto Operativo output

    Example:
        builder = SynthesisPromptBuilder()

        # Get system prompt for LLM
        system = builder.get_system_prompt()

        # Build user prompt with context
        user_prompt = builder.build(
            context=formatted_context,
            query="Quali sono i requisiti per il regime forfettario?"
        )

        # Use with LLM
        response = await llm.chat([
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ])
    """

    def __init__(self) -> None:
        """Initialize the synthesis prompt builder."""
        self._system_prompt = SYNTHESIS_SYSTEM_PROMPT
        self._hierarchy_rules = HIERARCHY_RULES
        self._verdetto_template = VERDETTO_OPERATIVO_TEMPLATE

    def get_system_prompt(self) -> str:
        """Get the system prompt for synthesis.

        Returns:
            System prompt string with all 4 compiti and guidelines
        """
        return self._system_prompt

    def build(self, context: str, query: str) -> str:
        """Build the user prompt for synthesis.

        Combines the context (from MetadataExtractor) with the user's
        query and instructions for producing Verdetto Operativo output.

        Args:
            context: Formatted context from MetadataExtractor.format_context_for_synthesis()
            query: User's original query

        Returns:
            Complete user prompt for LLM synthesis
        """
        # Handle empty context
        if not context or not context.strip():
            context = "Nessun documento rilevante trovato nella Knowledge Base."
            logger.warning(
                "synthesis_prompt_empty_context",
                query_length=len(query),
            )

        # Build the user prompt
        user_prompt = self._build_user_prompt(context, query)

        logger.info(
            "synthesis_prompt_built",
            context_length=len(context),
            query_length=len(query),
            prompt_length=len(user_prompt),
        )

        return user_prompt

    def _build_user_prompt(self, context: str, query: str) -> str:
        """Build the user prompt with context and query.

        Args:
            context: Formatted context string
            query: User's query

        Returns:
            Formatted user prompt
        """
        return f"""## Documenti dalla Knowledge Base

{context}

---

## Domanda dell'Utente

{query}

---

## Istruzioni

Analizza i documenti sopra seguendo i 4 compiti:
1. **ANALISI CRONOLOGICA** - Ordina per data, identifica evoluzione normativa
2. **RILEVAMENTO CONFLITTI** - Segnala discrepanze tra fonti
3. **APPLICAZIONE GERARCHIA** - Applica: Legge > Decreto > Circolare > Risoluzione > FAQ
4. **VERDETTO OPERATIVO** - Concludi con la sezione strutturata

Ricorda: approccio PRUDENTE. In caso di dubbio, consiglia l'opzione più sicura.
"""

    def get_hierarchy_rules(self) -> str:
        """Get the hierarchy rules reference.

        Returns:
            Hierarchy rules string
        """
        return self._hierarchy_rules

    def get_verdetto_template(self) -> str:
        """Get the Verdetto Operativo template.

        Returns:
            Verdetto Operativo template string
        """
        return self._verdetto_template

    def build_with_custom_instructions(
        self,
        context: str,
        query: str,
        additional_instructions: str,
    ) -> str:
        """Build prompt with additional custom instructions.

        Args:
            context: Formatted context string
            query: User's query
            additional_instructions: Extra instructions to append

        Returns:
            Complete user prompt with custom instructions
        """
        base_prompt = self.build(context, query)

        return f"""{base_prompt}

## Istruzioni Aggiuntive

{additional_instructions}
"""
