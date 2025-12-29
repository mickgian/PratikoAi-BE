"""Verdetto Operativo Output Parser for DEV-193.

Parses LLM synthesis output to extract structured Verdetto Operativo sections
per Section 13.8.4.

Usage:
    from app.services.verdetto_parser import VerdettoOperativoParser

    parser = VerdettoOperativoParser()
    result = parser.parse(llm_response)

    if result.verdetto:
        print(result.verdetto.azione_consigliata)
"""

import re
from typing import Optional

from app.core.logging import logger
from app.schemas.verdetto import FonteReference, ParsedSynthesis, VerdettoOperativo


class VerdettoOperativoParser:
    """Parses LLM synthesis output to extract Verdetto Operativo.

    Extracts structured sections from LLM output:
    - AZIONE CONSIGLIATA
    - ANALISI DEL RISCHIO
    - SCADENZA IMMINENTE
    - DOCUMENTAZIONE NECESSARIA
    - INDICE DELLE FONTI

    Example:
        parser = VerdettoOperativoParser()
        result = parser.parse(llm_response)

        if result.verdetto:
            print(f"Azione: {result.verdetto.azione_consigliata}")
            for doc in result.verdetto.documentazione:
                print(f"  - {doc}")
    """

    # Section markers with emojis
    SECTION_MARKERS = {
        "azione": "✅ AZIONE CONSIGLIATA",
        "rischio": "⚠️ ANALISI DEL RISCHIO",
        "scadenza": "📅 SCADENZA IMMINENTE",
        "documentazione": "📁 DOCUMENTAZIONE NECESSARIA",
    }

    # Headers for major sections
    VERDETTO_HEADER = "VERDETTO OPERATIVO"
    FONTI_HEADER = "INDICE DELLE FONTI"

    # Divider line pattern
    DIVIDER_PATTERN = r"━+"

    def parse(self, response: str | None) -> ParsedSynthesis:
        """Parse LLM synthesis output to extract Verdetto Operativo.

        Args:
            response: Full LLM response text

        Returns:
            ParsedSynthesis with answer_text and verdetto sections
        """
        # Handle None or empty input
        if not response:
            return ParsedSynthesis(
                answer_text="",
                verdetto=None,
                raw_response=response or "",
                parse_successful=True,
            )

        try:
            # Extract answer text (before VERDETTO OPERATIVO)
            answer_text = self._extract_answer_text(response)

            # Check if verdetto exists
            verdetto_section = self._extract_verdetto_section(response)

            if not verdetto_section:
                logger.info(
                    "verdetto_not_found",
                    response_length=len(response),
                )
                return ParsedSynthesis(
                    answer_text=answer_text,
                    verdetto=None,
                    raw_response=response,
                    parse_successful=True,
                )

            # Extract all verdetto sections
            verdetto = self._parse_verdetto(verdetto_section, response)

            logger.info(
                "verdetto_parsed",
                has_azione=verdetto.azione_consigliata is not None,
                has_rischio=verdetto.analisi_rischio is not None,
                has_scadenza=verdetto.scadenza is not None,
                num_docs=len(verdetto.documentazione),
                num_fonti=len(verdetto.indice_fonti),
            )

            return ParsedSynthesis(
                answer_text=answer_text,
                verdetto=verdetto,
                raw_response=response,
                parse_successful=True,
            )

        except Exception as e:
            logger.warning(
                "verdetto_parse_error",
                error_type=type(e).__name__,
                error_message=str(e),
            )
            # Never raise - return raw response
            return ParsedSynthesis(
                answer_text=response,
                verdetto=None,
                raw_response=response,
                parse_successful=True,
            )

    def _extract_answer_text(self, text: str) -> str:
        """Extract main answer text before VERDETTO OPERATIVO.

        Args:
            text: Full response text

        Returns:
            Text before the VERDETTO OPERATIVO header
        """
        # Find VERDETTO OPERATIVO header (may be preceded by divider)
        verdetto_pattern = rf"({self.DIVIDER_PATTERN}\s*)?\s*{self.VERDETTO_HEADER}"
        match = re.search(verdetto_pattern, text)

        if match:
            return text[: match.start()].strip()

        return text.strip()

    def _extract_verdetto_section(self, text: str) -> str | None:
        """Extract the VERDETTO OPERATIVO section from response.

        Args:
            text: Full response text

        Returns:
            Verdetto section text or None if not found
        """
        # Find VERDETTO OPERATIVO header
        verdetto_pattern = rf"{self.VERDETTO_HEADER}"
        match = re.search(verdetto_pattern, text)

        if not match:
            return None

        # Return everything from VERDETTO OPERATIVO onwards
        return text[match.start() :]

    def _parse_verdetto(self, verdetto_section: str, full_response: str) -> VerdettoOperativo:
        """Parse all sections from verdetto text.

        Args:
            verdetto_section: Text from VERDETTO OPERATIVO onwards
            full_response: Full original response

        Returns:
            VerdettoOperativo with extracted sections
        """
        # Extract each section
        azione = self._extract_section(
            verdetto_section,
            self.SECTION_MARKERS["azione"],
            self._get_next_marker("azione"),
        )

        rischio = self._extract_section(
            verdetto_section,
            self.SECTION_MARKERS["rischio"],
            self._get_next_marker("rischio"),
        )

        scadenza = self._extract_section(
            verdetto_section,
            self.SECTION_MARKERS["scadenza"],
            self._get_next_marker("scadenza"),
        )

        documentazione = self._extract_documentazione_list(
            self._extract_section(
                verdetto_section,
                self.SECTION_MARKERS["documentazione"],
                self._get_next_marker("documentazione"),
            )
        )

        # Extract fonti table from full response
        fonti = self._parse_fonti_table(full_response)

        return VerdettoOperativo(
            azione_consigliata=azione,
            analisi_rischio=rischio,
            scadenza=scadenza,
            documentazione=documentazione,
            indice_fonti=fonti,
        )

    def _get_next_marker(self, current_key: str) -> list[str]:
        """Get list of possible next markers after current section.

        Args:
            current_key: Key of current section in SECTION_MARKERS

        Returns:
            List of possible next section markers
        """
        keys = list(self.SECTION_MARKERS.keys())
        markers = list(self.SECTION_MARKERS.values())

        current_idx = keys.index(current_key)

        # Include all markers after current, plus dividers and FONTI header
        next_markers = markers[current_idx + 1 :] + [
            self.DIVIDER_PATTERN,
            self.FONTI_HEADER,
        ]

        return next_markers

    def _extract_section(
        self,
        text: str,
        start_marker: str,
        end_markers: list[str],
    ) -> str | None:
        """Extract content between start marker and next section.

        Args:
            text: Text to search in
            start_marker: Marker that starts this section
            end_markers: List of markers that could end this section

        Returns:
            Extracted section content or None
        """
        # Find start marker
        start_match = re.search(re.escape(start_marker), text)
        if not start_match:
            return None

        start_pos = start_match.end()

        # Find end position (first of any end markers)
        end_pos = len(text)
        for marker in end_markers:
            if marker == self.DIVIDER_PATTERN:
                pattern = marker
            else:
                pattern = re.escape(marker)
            match = re.search(pattern, text[start_pos:])
            if match:
                candidate_end = start_pos + match.start()
                if candidate_end < end_pos:
                    end_pos = candidate_end

        # Extract and clean content
        content = text[start_pos:end_pos].strip()

        # Remove leading divider line if present
        content = re.sub(r"^━+\s*", "", content).strip()

        return content if content else None

    def _extract_documentazione_list(self, section_text: str | None) -> list[str]:
        """Extract bulleted list from DOCUMENTAZIONE section.

        Args:
            section_text: Raw section text

        Returns:
            List of document items
        """
        if not section_text:
            return []

        documents = []

        # Match lines starting with "- " or "• "
        lines = section_text.split("\n")
        for line in lines:
            line = line.strip()
            # Match bullet points
            if line.startswith("- ") or line.startswith("• "):
                doc = line[2:].strip()
                if doc:
                    documents.append(doc)
            # Also match numbered items like "1. "
            elif re.match(r"^\d+\.\s+", line):
                doc = re.sub(r"^\d+\.\s+", "", line).strip()
                if doc:
                    documents.append(doc)

        return documents

    def _parse_fonti_table(self, text: str) -> list[FonteReference]:
        """Parse INDICE DELLE FONTI markdown table.

        Args:
            text: Full response text

        Returns:
            List of FonteReference objects
        """
        fonti = []

        # Find INDICE DELLE FONTI section
        fonti_match = re.search(self.FONTI_HEADER, text)
        if not fonti_match:
            return []

        fonti_section = text[fonti_match.end() :]

        # Find table rows (skip header and separator)
        # Pattern: | # | Data | Ente | Tipo | Riferimento |
        table_pattern = r"\|\s*(\d+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|"

        for match in re.finditer(table_pattern, fonti_section):
            try:
                numero = int(match.group(1).strip())
                data = match.group(2).strip()
                ente = match.group(3).strip()
                tipo = match.group(4).strip()
                riferimento = match.group(5).strip()

                # Skip header row (if it somehow matched) or separator row
                if data.lower() == "data" or "-" * 3 in data:
                    continue

                fonti.append(
                    FonteReference(
                        numero=numero,
                        data=data,
                        ente=ente,
                        tipo=tipo,
                        riferimento=riferimento,
                    )
                )
            except (ValueError, IndexError) as e:
                logger.debug(
                    "fonti_row_parse_error",
                    row=match.group(0),
                    error=str(e),
                )
                continue

        return fonti
