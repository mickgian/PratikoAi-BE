"""DEV-360: Bilancio Document Parser.

Parses client financial statements (bilanci) extracting key data:
fatturato, utile, patrimonio netto, etc.
"""

import re
from decimal import Decimal
from typing import Any

from app.core.logging import logger

# Patterns for common Italian financial statement fields
PATTERNS: dict[str, list[str]] = {
    "fatturato": [
        r"fatturato[\s:]+(?:€\s*)?([0-9.,]+)",
        r"ricavi[\s:]+(?:€\s*)?([0-9.,]+)",
        r"ricavi delle vendite[\s:]+(?:€\s*)?([0-9.,]+)",
    ],
    "utile_netto": [
        r"utile[\s(]netto[)\s:]+(?:€\s*)?([0-9.,]+)",
        r"risultato[\s(]netto[)\s:]+(?:€\s*)?([0-9.,]+)",
        r"utile d.esercizio[\s:]+(?:€\s*)?([0-9.,]+)",
    ],
    "patrimonio_netto": [
        r"patrimonio netto[\s:]+(?:€\s*)?([0-9.,]+)",
        r"totale patrimonio[\s:]+(?:€\s*)?([0-9.,]+)",
    ],
    "totale_attivo": [
        r"totale attivo[\s:]+(?:€\s*)?([0-9.,]+)",
        r"totale dell.attivo[\s:]+(?:€\s*)?([0-9.,]+)",
    ],
    "debiti": [
        r"totale debiti[\s:]+(?:€\s*)?([0-9.,]+)",
    ],
    "costi_produzione": [
        r"costi della produzione[\s:]+(?:€\s*)?([0-9.,]+)",
        r"costi di produzione[\s:]+(?:€\s*)?([0-9.,]+)",
    ],
}


def _parse_italian_number(s: str) -> float | None:
    """Parse Italian-formatted number (1.234,56 → 1234.56)."""
    if not s:
        return None
    cleaned = s.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


class BilancioParser:
    """Parser for Italian financial statement documents."""

    def parse(self, content: str) -> dict[str, Any]:
        """Parse financial statement text content.

        Args:
            content: Text content of the bilancio document.

        Returns:
            Dict with extracted financial data.

        Raises:
            ValueError: If content is empty.
        """
        if not content or not content.strip():
            raise ValueError("Il contenuto del bilancio è vuoto")

        extracted: dict[str, Any] = {}
        content_lower = content.lower()

        for field, patterns in PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, content_lower)
                if match:
                    value = _parse_italian_number(match.group(1))
                    if value is not None:
                        extracted[field] = value
                        break

        # Extract year if present
        year_match = re.search(r"esercizio\s+(\d{4})|bilancio\s+(\d{4})|anno\s+(\d{4})", content_lower)
        if year_match:
            extracted["anno_esercizio"] = int(next(g for g in year_match.groups() if g))

        # Calculate derived metrics
        if "fatturato" in extracted and "utile_netto" in extracted:
            fatturato = extracted["fatturato"]
            if fatturato > 0:
                extracted["margine_netto_pct"] = round(extracted["utile_netto"] / fatturato * 100, 2)

        if "patrimonio_netto" in extracted and "totale_attivo" in extracted:
            totale = extracted["totale_attivo"]
            if totale > 0:
                extracted["rapporto_patrimonio_attivo"] = round(extracted["patrimonio_netto"] / totale * 100, 2)

        logger.info(
            "bilancio_parsed",
            fields_extracted=list(extracted.keys()),
        )

        return extracted


bilancio_parser = BilancioParser()
