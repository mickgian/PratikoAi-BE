"""DEV-392: F24 Document Parser.

Specialized parser for F24 tax payment documents.
Extracts: codici tributo, importi, periodo di riferimento, sezioni.
"""

import re
from typing import Any

from app.core.logging import logger

F24_SECTION_PATTERNS: dict[str, list[str]] = {
    "sezione_erario": [
        r"sezione\s+erario",
        r"tributi\s+erariali",
    ],
    "sezione_regioni": [
        r"sezione\s+regioni",
        r"tributi\s+regionali",
    ],
    "sezione_enti_locali": [
        r"sezione\s+enti\s+locali",
        r"sezione\s+imu",
    ],
    "sezione_inps": [
        r"sezione\s+inps",
        r"contributi\s+inps",
    ],
    "sezione_inail": [
        r"sezione\s+inail",
    ],
}

CODICI_TRIBUTO: dict[str, str] = {
    "4001": "IRPEF saldo",
    "4033": "IRPEF acconto prima rata",
    "4034": "IRPEF acconto seconda rata",
    "3800": "IRAP saldo",
    "3801": "Addizionale regionale IRPEF",
    "3844": "Addizionale comunale IRPEF saldo",
    "3843": "Addizionale comunale IRPEF acconto",
    "6099": "IVA annuale versamento",
    "6031": "IVA I trimestre",
    "6032": "IVA II trimestre",
    "6033": "IVA III trimestre",
    "6034": "IVA IV trimestre",
    "1040": "Ritenute su redditi di lavoro autonomo",
    "1001": "Ritenute su redditi di lavoro dipendente",
    "3918": "IMU altri fabbricati",
    "3914": "IMU terreni",
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


class F24Parser:
    """Parser for Italian F24 tax payment documents."""

    def parse(self, content: str) -> dict[str, Any]:
        """Parse F24 document text content.

        Args:
            content: Text content of the F24 document.

        Returns:
            Dict with extracted payment data.

        Raises:
            ValueError: If content is empty.
        """
        if not content or not content.strip():
            raise ValueError("Il contenuto del modello F24 è vuoto")

        content_lower = content.lower()
        extracted: dict[str, Any] = {
            "tipo_documento": "F24",
            "sezioni": [],
            "tributi": [],
            "totale_versamento": 0.0,
        }

        # Detect which sections are present
        sezioni_presenti = []
        for sezione, patterns in F24_SECTION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, content_lower):
                    sezioni_presenti.append(sezione)
                    break
        extracted["sezioni"] = sezioni_presenti

        # Extract codici tributo
        tributo_pattern = r"(\d{4})\s+(\d{4})\s+(?:€\s*)?([0-9.,]+)"
        for match in re.finditer(tributo_pattern, content):
            codice = match.group(1)
            anno = match.group(2)
            importo = _parse_number(match.group(3))
            if importo is not None:
                tributo = {
                    "codice_tributo": codice,
                    "anno_riferimento": anno,
                    "importo": importo,
                    "descrizione": CODICI_TRIBUTO.get(codice, "Tributo sconosciuto"),
                }
                extracted["tributi"].append(tributo)

        # Also try simpler pattern: codice tributo followed by amount
        simple_pattern = r"codice\s+tributo[\s:]+(\d{4}).*?(?:€\s*)?([0-9.,]+)"
        for match in re.finditer(simple_pattern, content_lower):
            codice = match.group(1)
            importo = _parse_number(match.group(2))
            if importo is not None and not any(t["codice_tributo"] == codice for t in extracted["tributi"]):
                extracted["tributi"].append(
                    {
                        "codice_tributo": codice,
                        "importo": importo,
                        "descrizione": CODICI_TRIBUTO.get(codice, "Tributo sconosciuto"),
                    }
                )

        # Calculate total
        extracted["totale_versamento"] = sum(t["importo"] for t in extracted["tributi"])

        # Extract contribuente info
        cf_match = re.search(r"CODICE\s+FISCALE[\s:]+([A-Z0-9]{11,16})", content.upper())
        if cf_match:
            extracted["codice_fiscale"] = cf_match.group(1)

        # Extract date
        date_match = re.search(r"data\s+versamento[\s:]+(\d{2}[/.-]\d{2}[/.-]\d{4})", content_lower)
        if date_match:
            extracted["data_versamento"] = date_match.group(1)

        logger.info(
            "f24_parsed",
            tributi_count=len(extracted["tributi"]),
            totale=extracted["totale_versamento"],
        )

        return extracted

    @staticmethod
    def get_codice_tributo_description(codice: str) -> str:
        """Get human-readable description for a tributo code."""
        return CODICI_TRIBUTO.get(codice, "Codice tributo sconosciuto")


f24_parser = F24Parser()
