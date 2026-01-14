"""VerdettResponseFormatter service for parsing structured sources.

DEV-242: Parses INDICE DELLE FONTI ASCII table from LLM responses
into structured JSON for proper frontend rendering.
"""

import re
from dataclasses import dataclass
from typing import Any

from app.core.logging import logger


@dataclass
class StructuredFonte:
    """A structured source citation."""

    numero: int
    data: str
    ente: str
    tipo: str
    riferimento: str
    url: str | None = None


@dataclass
class VerdettoParsedResponse:
    """Parsed response with structured sources."""

    content: str  # Main content without the table
    structured_sources: list[dict[str, Any]]
    verdetto_operativo: dict[str, Any] | None = None
    has_sources_table: bool = False


class VerdettResponseFormatter:
    """Formats and parses LLM responses with source citations.

    DEV-242: Extracts INDICE DELLE FONTI table into structured data
    for proper rendering in the frontend.
    """

    # Pattern to match the INDICE DELLE FONTI section
    INDICE_PATTERN = re.compile(
        r"(?:#{1,3}\s*)?(?:INDICE DELLE FONTI|Indice delle Fonti|FONTI)\s*\n"
        r"(?:\|[-:\s|]+\|\n)?"  # Optional table header separator
        r"((?:\|.*\|\n?)+)",  # Table rows
        re.IGNORECASE | re.MULTILINE,
    )

    # Alternative pattern for numbered list format
    NUMBERED_LIST_PATTERN = re.compile(
        r"(?:#{1,3}\s*)?(?:INDICE DELLE FONTI|Indice delle Fonti|FONTI)\s*\n"
        r"((?:\d+\.\s+.+\n?)+)",  # Numbered list items
        re.IGNORECASE | re.MULTILINE,
    )

    # Pattern for table row parsing
    TABLE_ROW_PATTERN = re.compile(
        r"\|\s*(\d+)\s*\|\s*([^|]*)\s*\|\s*([^|]*)\s*\|\s*([^|]*)\s*\|\s*([^|]*)\s*\|",
    )

    def parse_response(self, content: str) -> VerdettoParsedResponse:
        """Parse LLM response and extract structured sources.

        Args:
            content: Raw LLM response content

        Returns:
            VerdettoParsedResponse with content and structured_sources
        """
        if not content:
            return VerdettoParsedResponse(
                content="",
                structured_sources=[],
                has_sources_table=False,
            )

        # Try to extract INDICE DELLE FONTI table
        sources = self._extract_sources_table(content)

        if sources:
            # Remove the table from content for cleaner rendering
            cleaned_content = self._remove_sources_table(content)
            logger.info(
                "verdetto_sources_extracted",
                sources_count=len(sources),
            )
            return VerdettoParsedResponse(
                content=cleaned_content,
                structured_sources=sources,
                has_sources_table=True,
            )

        # No table found - return original content
        return VerdettoParsedResponse(
            content=content,
            structured_sources=[],
            has_sources_table=False,
        )

    def _extract_sources_table(self, content: str) -> list[dict[str, Any]]:
        """Extract sources from ASCII table format.

        Args:
            content: Raw content with potential table

        Returns:
            List of source dicts
        """
        sources: list[dict[str, Any]] = []

        # Try table format first
        table_match = self.INDICE_PATTERN.search(content)
        if table_match:
            table_content = table_match.group(1)
            sources = self._parse_table_rows(table_content)
            if sources:
                return sources

        # Try numbered list format
        list_match = self.NUMBERED_LIST_PATTERN.search(content)
        if list_match:
            list_content = list_match.group(1)
            sources = self._parse_numbered_list(list_content)
            if sources:
                return sources

        return sources

    def _parse_table_rows(self, table_content: str) -> list[dict[str, Any]]:
        """Parse markdown table rows into source dicts.

        Args:
            table_content: Table rows content

        Returns:
            List of parsed source dicts
        """
        sources: list[dict[str, Any]] = []

        for line in table_content.split("\n"):
            line = line.strip()
            if not line or line.startswith("|--") or line.startswith("|-"):
                continue

            # Try to parse as table row
            match = self.TABLE_ROW_PATTERN.match(line)
            if match:
                numero, data, ente, tipo, riferimento = match.groups()
                sources.append(
                    {
                        "numero": int(numero.strip()),
                        "data": data.strip(),
                        "ente": ente.strip(),
                        "tipo": tipo.strip(),
                        "riferimento": riferimento.strip(),
                    }
                )
            else:
                # Try simpler parsing for rows with fewer columns
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) >= 3:
                    try:
                        numero = int(parts[0])
                        sources.append(
                            {
                                "numero": numero,
                                "data": parts[1] if len(parts) > 1 else "",
                                "ente": parts[2] if len(parts) > 2 else "",
                                "tipo": parts[3] if len(parts) > 3 else "",
                                "riferimento": parts[4] if len(parts) > 4 else "",
                            }
                        )
                    except ValueError:
                        continue

        return sources

    def _parse_numbered_list(self, list_content: str) -> list[dict[str, Any]]:
        """Parse numbered list format into source dicts.

        Args:
            list_content: Numbered list content

        Returns:
            List of parsed source dicts
        """
        sources: list[dict[str, Any]] = []

        for line in list_content.split("\n"):
            line = line.strip()
            if not line:
                continue

            # Match "1. Source reference - details"
            match = re.match(r"(\d+)\.\s+(.+)", line)
            if match:
                numero = int(match.group(1))
                reference = match.group(2).strip()

                # Try to extract date from reference
                date_match = re.search(
                    r"(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\d{4})",
                    reference,
                )
                data = date_match.group(1) if date_match else ""

                # Try to extract ente (entity)
                ente = ""
                ente_patterns = [
                    r"Agenzia delle Entrate",
                    r"AdE",
                    r"INPS",
                    r"INAIL",
                    r"MEF",
                    r"Ministero",
                ]
                for pattern in ente_patterns:
                    if re.search(pattern, reference, re.IGNORECASE):
                        ente = pattern.replace(r"\s+", " ")
                        break

                # Try to identify tipo (type)
                tipo = ""
                tipo_patterns = {
                    "Circolare": r"[Cc]ircolare",
                    "Risoluzione": r"[Rr]isoluzione",
                    "Provvedimento": r"[Pp]rovvedimento",
                    "Legge": r"[Ll]egge",
                    "Decreto": r"[Dd]ecreto",
                    "DPR": r"DPR",
                    "D.Lgs.": r"D\.?Lgs\.?",
                }
                for tipo_name, pattern in tipo_patterns.items():
                    if re.search(pattern, reference):
                        tipo = tipo_name
                        break

                sources.append(
                    {
                        "numero": numero,
                        "data": data,
                        "ente": ente,
                        "tipo": tipo,
                        "riferimento": reference,
                    }
                )

        return sources

    def _remove_sources_table(self, content: str) -> str:
        """Remove the sources table from content.

        Args:
            content: Original content with table

        Returns:
            Content with table removed
        """
        # Remove table format
        cleaned = self.INDICE_PATTERN.sub("", content)

        # Remove numbered list format
        cleaned = self.NUMBERED_LIST_PATTERN.sub("", cleaned)

        # Clean up extra whitespace
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        cleaned = cleaned.strip()

        return cleaned

    def format_sources_for_display(
        self,
        sources: list[dict[str, Any]],
    ) -> str:
        """Format structured sources back to markdown table.

        Args:
            sources: List of source dicts

        Returns:
            Markdown table string
        """
        if not sources:
            return ""

        lines = [
            "### INDICE DELLE FONTI",
            "",
            "| # | Data | Ente | Tipo | Riferimento |",
            "|---|------|------|------|-------------|",
        ]

        for source in sources:
            lines.append(
                f"| {source.get('numero', '')} | "
                f"{source.get('data', '')} | "
                f"{source.get('ente', '')} | "
                f"{source.get('tipo', '')} | "
                f"{source.get('riferimento', '')} |"
            )

        return "\n".join(lines)


# Singleton instance
verdetto_response_formatter = VerdettResponseFormatter()
