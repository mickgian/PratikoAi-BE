"""DEV-361: CU (Certificazione Unica) Document Parser.

Extracts income and withholding data from Certificazione Unica documents.
"""

import re
from typing import Any

from app.core.logging import logger

CU_PATTERNS: dict[str, list[str]] = {
    "redditi_lavoro_dipendente": [
        r"redditi di lavoro dipendente[\s:]+(?:€\s*)?([0-9.,]+)",
        r"punto\s+1[\s:]+(?:€\s*)?([0-9.,]+)",
    ],
    "redditi_assimilati": [
        r"redditi assimilati[\s:]+(?:€\s*)?([0-9.,]+)",
    ],
    "ritenute_irpef": [
        r"ritenute irpef[\s:]+(?:€\s*)?([0-9.,]+)",
        r"ritenute d.acconto[\s:]+(?:€\s*)?([0-9.,]+)",
        r"punto\s+21[\s:]+(?:€\s*)?([0-9.,]+)",
    ],
    "addizionale_regionale": [
        r"addizionale regionale[\s:]+(?:€\s*)?([0-9.,]+)",
        r"punto\s+22[\s:]+(?:€\s*)?([0-9.,]+)",
    ],
    "addizionale_comunale": [
        r"addizionale comunale[\s:]+(?:€\s*)?([0-9.,]+)",
        r"punto\s+26[\s:]+(?:€\s*)?([0-9.,]+)",
    ],
    "contributi_previdenziali": [
        r"contributi previdenziali[\s:]+(?:€\s*)?([0-9.,]+)",
        r"contributi inps[\s:]+(?:€\s*)?([0-9.,]+)",
    ],
    "giorni_lavoro": [
        r"giorni[\s(]di lavoro[)\s:]+(\d+)",
        r"punto\s+6[\s:]+(\d+)",
    ],
}


def _parse_number(s: str) -> float | None:
    """Parse Italian-formatted number."""
    if not s:
        return None
    cleaned = s.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


class CuParser:
    """Parser for Certificazione Unica documents."""

    def parse(self, content: str) -> dict[str, Any]:
        """Parse CU document text content.

        Args:
            content: Text content of the CU document.

        Returns:
            Dict with extracted income and withholding data.

        Raises:
            ValueError: If content is empty.
        """
        if not content or not content.strip():
            raise ValueError("Il contenuto della CU è vuoto")

        extracted: dict[str, Any] = {}
        content_lower = content.lower()

        for field, patterns in CU_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, content_lower)
                if match:
                    value = _parse_number(match.group(1))
                    if value is not None:
                        extracted[field] = value
                        break

        # Extract year
        year_match = re.search(r"certificazione unica\s+(\d{4})", content_lower)
        if year_match:
            extracted["anno_cu"] = int(year_match.group(1))

        # Extract sostituto d'imposta info
        cf_match = re.search(r"codice fiscale[\s:]+([A-Z0-9]{11,16})", content.upper())
        if cf_match:
            extracted["codice_fiscale_sostituto"] = cf_match.group(1)

        logger.info(
            "cu_parsed",
            fields_extracted=list(extracted.keys()),
        )

        return extracted


cu_parser = CuParser()
