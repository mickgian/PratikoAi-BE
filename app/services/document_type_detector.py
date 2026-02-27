"""DEV-421: Document Type Auto-Detection (>90% accuracy target).

Detects document type from:
- File extension / MIME type
- XML namespace (for fatture elettroniche)
- Content keyword heuristics
"""

import re
from typing import Any

from app.core.logging import logger

# Keyword patterns for each document type, ordered by specificity
CONTENT_PATTERNS: dict[str, list[tuple[str, float]]] = {
    "fattura_elettronica": [
        (r"fattura\s*elettronica|FatturaElettronica|ivaservizi\.agenziaentrate", 0.95),
        (r"FatturaPA|CedentePrestatore|CessionarioCommittente", 0.90),
        (r"SDI|Sistema\s+di\s+Interscambio", 0.70),
    ],
    "f24": [
        (r"modello\s+f24|MODELLO\s+F24", 0.90),
        (r"sezione\s+erario.*codice\s+tributo", 0.85),
        (r"codice\s+tributo\s+\d{4}.*periodo\s+di\s+riferimento", 0.80),
    ],
    "certificazione_unica": [
        (r"certificazione\s+unica\s+\d{4}", 0.90),
        (r"CU\s+\d{4}.*redditi\s+\d{4}", 0.85),
        (r"ritenute\s+(operate|irpef).*redditi\s+di\s+lavoro", 0.75),
    ],
    "bilancio": [
        (r"bilancio\s+di\s+esercizio|bilancio\s+\d{4}", 0.85),
        (r"stato\s+patrimoniale.*conto\s+economico", 0.80),
        (r"nota\s+integrativa.*fatturato", 0.75),
    ],
    "busta_paga": [
        (r"busta\s+paga|cedolino\s+stipendio", 0.90),
        (r"retribuzione\s+(lorda|netta).*inps.*trattenute", 0.80),
        (r"mensilit[aà].*ferie.*permessi", 0.70),
    ],
    "visura_camerale": [
        (r"visura\s+camerale|registro\s+imprese", 0.90),
        (r"camera\s+di\s+commercio.*partita\s+iva", 0.80),
    ],
    "contratto": [
        (r"contratto\s+di\s+(locazione|lavoro|servizio)", 0.85),
        (r"tra\s+le\s+parti.*premesso\s+che|si\s+conviene", 0.70),
    ],
}

# Extension-based hints
EXTENSION_HINTS: dict[str, tuple[str, float]] = {
    ".xml": ("fattura_elettronica", 0.70),
    ".p7m": ("fattura_elettronica", 0.75),
}

# Filename keyword hints
FILENAME_HINTS: dict[str, tuple[str, float]] = {
    "fattura": ("fattura_elettronica", 0.60),
    "f24": ("f24", 0.70),
    "bilancio": ("bilancio", 0.65),
    "cu_": ("certificazione_unica", 0.65),
    "certificazione": ("certificazione_unica", 0.60),
    "busta": ("busta_paga", 0.65),
    "cedolino": ("busta_paga", 0.65),
    "visura": ("visura_camerale", 0.65),
    "contratto": ("contratto", 0.60),
}


class DocumentTypeDetector:
    """Automatic document type detection service."""

    def detect(
        self,
        filename: str,
        content: str | None = None,
        mime_type: str | None = None,
    ) -> dict[str, Any]:
        """Detect document type from filename, content, and MIME type.

        Args:
            filename: Original filename.
            content: Text content (if available).
            mime_type: MIME type (if known).

        Returns:
            Dict with detected_type, confidence, and method.
        """
        if not filename:
            return {"detected_type": "unknown", "confidence": 0.0, "method": "none"}

        best_type = "unknown"
        best_confidence = 0.0
        method = "none"

        # Step 1: Check extension
        filename_lower = filename.lower()
        for ext, (doc_type, conf) in EXTENSION_HINTS.items():
            if filename_lower.endswith(ext):
                if conf > best_confidence:
                    best_type = doc_type
                    best_confidence = conf
                    method = "extension"

        # Step 2: Check filename keywords
        for keyword, (doc_type, conf) in FILENAME_HINTS.items():
            if keyword in filename_lower:
                if conf > best_confidence:
                    best_type = doc_type
                    best_confidence = conf
                    method = "filename"

        # Step 3: Check MIME type for xlsx → bilancio hint
        if mime_type and "spreadsheet" in mime_type:
            if "bilancio" in filename_lower:
                best_type = "bilancio"
                best_confidence = max(best_confidence, 0.60)
                method = "mime+filename"

        # Step 4: Content analysis (highest priority)
        if content:
            content_result = self._analyze_content(content)
            if content_result["confidence"] > best_confidence:
                best_type = content_result["detected_type"]
                best_confidence = content_result["confidence"]
                method = "content"

        logger.info(
            "document_type_detected",
            filename=filename,
            detected_type=best_type,
            confidence=best_confidence,
            method=method,
        )

        return {
            "detected_type": best_type,
            "confidence": best_confidence,
            "method": method,
        }

    def _analyze_content(self, content: str) -> dict[str, Any]:
        """Analyze text content to detect document type."""
        best_type = "unknown"
        best_confidence = 0.0

        for doc_type, patterns in CONTENT_PATTERNS.items():
            for pattern, confidence in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    if confidence > best_confidence:
                        best_type = doc_type
                        best_confidence = confidence
                        break  # Take first (highest confidence) match per type

        return {"detected_type": best_type, "confidence": best_confidence}


document_type_detector = DocumentTypeDetector()
