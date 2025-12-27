"""Verdetto Operativo Schemas for DEV-193.

Pydantic models for parsed Verdetto Operativo sections from LLM synthesis output
per Section 13.8.4.

Usage:
    from app.schemas.verdetto import ParsedSynthesis, VerdettoOperativo

    result = parser.parse(llm_response)
    if result.verdetto:
        print(result.verdetto.azione_consigliata)
"""

from pydantic import BaseModel, Field


class FonteReference(BaseModel):
    """Reference to a source document from INDICE DELLE FONTI.

    Attributes:
        numero: Row number in the table (1-indexed)
        data: Publication date in DD/MM/YYYY format
        ente: Issuing entity (e.g., "Agenzia Entrate", "Parlamento")
        tipo: Document type (e.g., "Circolare", "Legge")
        riferimento: Reference code (e.g., "Circ. 9/E/2025", "L. 234/2024")
    """

    numero: int = Field(..., ge=1, description="Row number in fonti table")
    data: str = Field(..., description="Publication date DD/MM/YYYY")
    ente: str = Field(..., description="Issuing entity name")
    tipo: str = Field(..., description="Document type")
    riferimento: str = Field(..., description="Reference code")


class VerdettoOperativo(BaseModel):
    """Structured Verdetto Operativo sections.

    Contains all sections extracted from the VERDETTO OPERATIVO block
    in LLM synthesis output per Section 13.8.4.

    Attributes:
        azione_consigliata: Recommended action (safest approach)
        analisi_rischio: Risk analysis (potential sanctions)
        scadenza: Imminent deadline or "Nessuna scadenza critica rilevata"
        documentazione: List of documents to preserve
        indice_fonti: List of source references from the fonti table
    """

    azione_consigliata: str | None = Field(
        default=None,
        description="Recommended action from ✅ AZIONE CONSIGLIATA section",
    )
    analisi_rischio: str | None = Field(
        default=None,
        description="Risk analysis from ⚠️ ANALISI DEL RISCHIO section",
    )
    scadenza: str | None = Field(
        default=None,
        description="Deadline from 📅 SCADENZA IMMINENTE section",
    )
    documentazione: list[str] = Field(
        default_factory=list,
        description="Documents from 📁 DOCUMENTAZIONE NECESSARIA section",
    )
    indice_fonti: list[FonteReference] = Field(
        default_factory=list,
        description="Source references from INDICE DELLE FONTI table",
    )


class ParsedSynthesis(BaseModel):
    """Result of parsing LLM synthesis output.

    Contains both the main answer text (before the Verdetto) and
    the structured Verdetto Operativo sections if present.

    Attributes:
        answer_text: Main response text before VERDETTO OPERATIVO
        verdetto: Structured Verdetto sections (None if not found)
        raw_response: Original full LLM response
        parse_successful: True if parsing completed without errors
    """

    answer_text: str = Field(
        default="",
        description="Main answer text before VERDETTO OPERATIVO",
    )
    verdetto: VerdettoOperativo | None = Field(
        default=None,
        description="Structured Verdetto Operativo (None if not present)",
    )
    raw_response: str = Field(
        default="",
        description="Original full LLM response",
    )
    parse_successful: bool = Field(
        default=True,
        description="True if parsing completed without errors",
    )
