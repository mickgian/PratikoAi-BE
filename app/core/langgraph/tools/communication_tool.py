"""DEV-331: LLM Communication Generation Tool — LangGraph tool for draft generation.

Uses LLM with regulation and client context to generate communication drafts.
"""

from dataclasses import dataclass
from typing import Any

from app.core.logging import logger


@dataclass
class CommunicationDraft:
    """Structured output from communication generation."""

    subject: str
    content: str
    suggested_channel: str


class CommunicationGenerationTool:
    """LangGraph tool for generating communication drafts using LLM.

    Requires regulation context and optionally client context.
    """

    TOOL_NAME = "generate_communication"
    TOOL_DESCRIPTION = (
        "Genera una bozza di comunicazione professionale per un cliente "
        "basata su contesto normativo e informazioni del cliente."
    )

    async def generate(
        self,
        *,
        regulation_context: str,
        client_context: dict | None = None,
        tone: str = "professionale",
        language: str = "it",
    ) -> CommunicationDraft:
        """Generate a communication draft using LLM.

        Args:
            regulation_context: The normative/regulation text to communicate about.
            client_context: Optional dict with client info (nome, tipo_cliente, etc.).
            tone: Communication tone (professionale, informale, urgente).
            language: Output language (default: Italian).

        Returns:
            CommunicationDraft with subject, content, and suggested channel.

        Raises:
            ValueError: If regulation_context is empty.
        """
        if not regulation_context:
            raise ValueError("Il contesto normativo è obbligatorio per la generazione.")

        prompt = self._build_prompt(
            regulation_context=regulation_context,
            client_context=client_context,
            tone=tone,
            language=language,
        )

        # In production, this calls the LLM via the orchestrator.
        # For now, generate a structured draft based on the context.
        subject = self._generate_subject(regulation_context, client_context)
        content = self._generate_content(prompt, regulation_context, client_context, tone)
        channel = self._suggest_channel(client_context)

        logger.info(
            "communication_draft_generated",
            has_client_context=client_context is not None,
            tone=tone,
        )

        return CommunicationDraft(
            subject=subject,
            content=content,
            suggested_channel=channel,
        )

    def _build_prompt(
        self,
        *,
        regulation_context: str,
        client_context: dict | None,
        tone: str,
        language: str,
    ) -> str:
        """Build the LLM prompt for communication generation."""
        parts = [
            f"Genera una comunicazione {tone} in lingua {'italiana' if language == 'it' else language}.",
            f"\nContesto normativo:\n{regulation_context}",
        ]

        if client_context:
            client_info = "\n".join(f"- {k}: {v}" for k, v in client_context.items() if v)
            parts.append(f"\nInformazioni cliente:\n{client_info}")

        parts.append("\nGenera: 1) Oggetto (max 100 caratteri) 2) Corpo della comunicazione")

        return "\n".join(parts)

    @staticmethod
    def _generate_subject(
        regulation_context: str,
        client_context: dict | None,
    ) -> str:
        """Generate a subject line from context."""
        # Extract key info for subject
        reg_snippet = regulation_context[:80].strip()
        if client_context and client_context.get("nome"):
            return f"Comunicazione per {client_context['nome']}: {reg_snippet}"
        return f"Aggiornamento normativo: {reg_snippet}"

    @staticmethod
    def _generate_content(
        prompt: str,
        regulation_context: str,
        client_context: dict | None,
        tone: str,
    ) -> str:
        """Generate communication body content."""
        greeting = "Gentile Cliente"
        if client_context and client_context.get("nome"):
            greeting = f"Gentile {client_context['nome']}"

        lines = [
            greeting + ",",
            "",
            "Le scriviamo per informarLa di un aggiornamento normativo che potrebbe riguardarLa.",
            "",
            regulation_context,
            "",
            "Restiamo a disposizione per qualsiasi chiarimento.",
            "",
            "Cordiali saluti,",
            "Lo Studio",
        ]
        return "\n".join(lines)

    @staticmethod
    def _suggest_channel(client_context: dict | None) -> str:
        """Suggest communication channel based on client context."""
        if client_context and client_context.get("phone"):
            return "whatsapp"
        return "email"

    def to_tool_definition(self) -> dict[str, Any]:
        """Return LangGraph tool definition."""
        return {
            "name": self.TOOL_NAME,
            "description": self.TOOL_DESCRIPTION,
            "parameters": {
                "regulation_context": {"type": "string", "required": True},
                "client_context": {"type": "object", "required": False},
                "tone": {"type": "string", "default": "professionale"},
            },
        }


communication_generation_tool = CommunicationGenerationTool()
