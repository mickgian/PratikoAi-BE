"""PII detection and anonymization utilities for GDPR compliance.

This module provides comprehensive PII detection and removal capabilities,
with specific support for Italian data patterns and GDPR requirements.
"""

import hashlib
import re
import uuid
from dataclasses import (
    dataclass,
    field,
)
from datetime import datetime
from enum import Enum
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
)

from app.core.logging import logger


class PIIType(str, Enum):
    """Types of Personally Identifiable Information."""

    EMAIL = "email"
    PHONE = "phone"
    CODICE_FISCALE = "codice_fiscale"  # Italian tax code
    PARTITA_IVA = "partita_iva"  # Italian VAT number
    IBAN = "iban"
    CREDIT_CARD = "credit_card"
    NAME = "name"
    ADDRESS = "address"
    DATE_OF_BIRTH = "date_of_birth"
    GENERIC_ID = "generic_id"


@dataclass
class PIIMatch:
    """Represents a detected PII match."""

    pii_type: PIIType
    original_value: str
    anonymized_value: str
    start_pos: int
    end_pos: int
    confidence: float = 1.0


@dataclass
class AnonymizationResult:
    """Result of anonymization process."""

    anonymized_text: str
    pii_matches: list[PIIMatch] = field(default_factory=list)
    anonymization_map: dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


class PIIAnonymizer:
    """PII detection and anonymization engine with Italian language support."""

    def __init__(self):
        """Initialize the anonymizer with Italian-specific patterns."""
        self._patterns = self._build_patterns()
        self._name_patterns = self._build_name_patterns()
        self._street_patterns = self._build_street_patterns()  # DEV-007
        self._anonymization_cache: dict[str, str] = {}

    def _build_patterns(self) -> dict[PIIType, list[re.Pattern]]:
        """Build regex patterns for PII detection."""
        patterns = {
            PIIType.EMAIL: [re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", re.IGNORECASE)],
            PIIType.PHONE: [
                # Italian phone numbers
                re.compile(r"\+39\s?[0-9]{2,3}\s?[0-9]{6,8}", re.IGNORECASE),
                re.compile(r"(?:^|\s)(?:0[0-9]{1,3}[-\s]?[0-9]{6,8})", re.IGNORECASE),
                re.compile(r"(?:^|\s)(?:3[0-9]{2}[-\s]?[0-9]{6,7})", re.IGNORECASE),  # Mobile
                # General phone patterns
                re.compile(r"\b(?:\+?[1-9]{1}[0-9]{0,3}[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{3,4}\b"),
            ],
            PIIType.CODICE_FISCALE: [
                # Italian tax code (16 characters: 6 letters + 2 digits + 1 letter + 2 digits + 1 letter + 3 digits + 1 letter)
                re.compile(r"\b[A-Z]{6}[0-9]{2}[A-Z][0-9]{2}[A-Z][0-9]{3}[A-Z]\b", re.IGNORECASE)
            ],
            PIIType.PARTITA_IVA: [
                # Italian VAT number (11 digits)
                re.compile(r"\bIT[0-9]{11}\b", re.IGNORECASE),
                re.compile(r"\b[0-9]{11}\b"),  # Without IT prefix
            ],
            PIIType.IBAN: [
                # IBAN format
                re.compile(r"\bIT[0-9]{2}[A-Z][0-9]{10}[A-Z0-9]{12}\b", re.IGNORECASE),  # Italian IBAN
                re.compile(r"\b[A-Z]{2}[0-9]{2}[A-Z0-9]{4}[0-9]{7}[A-Z0-9]{0,16}\b", re.IGNORECASE),  # General IBAN
            ],
            PIIType.CREDIT_CARD: [
                # Credit card numbers (various formats)
                re.compile(
                    r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3[0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b"
                ),
                re.compile(r"\b[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4}\b"),
            ],
            PIIType.DATE_OF_BIRTH: [
                # Various date formats
                re.compile(
                    r"\b(?:0[1-9]|[12][0-9]|3[01])[\/\-\.](0[1-9]|1[012])[\/\-\.](?:19|20)[0-9]{2}\b"
                ),  # DD/MM/YYYY
                re.compile(
                    r"\b(?:19|20)[0-9]{2}[\/\-\.](0[1-9]|1[012])[\/\-\.](0[1-9]|[12][0-9]|3[01])\b"
                ),  # YYYY/MM/DD
                # Italian month dates - will be context-filtered to avoid matching document publication dates
                re.compile(
                    r"\b(0[1-9]|[12][0-9]|3[01])\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(?:19|20)[0-9]{2}\b",
                    re.IGNORECASE,
                ),
            ],
            PIIType.GENERIC_ID: [
                # Generic ID patterns
                re.compile(r"\b[A-Z0-9]{8,16}\b"),  # Alphanumeric IDs
                re.compile(r"\b[0-9]{8,16}\b"),  # Numeric IDs
            ],
        }

        return patterns

    def _build_name_patterns(self) -> list[re.Pattern]:
        """Build patterns for Italian names detection."""
        # Common Italian name prefixes and suffixes
        italian_prefixes = [
            "dott",
            "dottore",
            "dottoressa",
            "dr",
            "prof",
            "professore",
            "professoressa",
            "ing",
            "ingegnere",
            "avv",
            "avvocato",
            "sig",
            "signore",
            "signora",
            "signorina",
        ]

        # Pattern for names with titles
        title_pattern = f"(?:{'|'.join(italian_prefixes)})\\.?\\s+([A-Z][a-z]+(?:\\s+[A-Z][a-z]+)*)"

        return [
            re.compile(title_pattern, re.IGNORECASE),
            # Names in quotes or after "mi chiamo", "sono", etc.
            re.compile(r"(?:mi chiamo|sono|il mio nome è)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)", re.IGNORECASE),
            re.compile(r'"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)"'),
            # DEV-007: English labels for document/payslip formats
            # Matches: "Name: John Doe", "Full Name John Smith", "Surname: Rossi"
            re.compile(
                r"(?:Name|Full\s*Name|Surname|Nome|Cognome)\s*[:\s]\s*([A-ZÀ-ÿ][a-zà-ÿ]+(?:\s+[A-ZÀ-ÿ][a-zà-ÿ]+)*)",
                re.IGNORECASE,
            ),
            # DEV-007: Surname Firstname format with employee code
            # Matches: "Giannone Michele (MICGIA)"
            re.compile(
                r"\b([A-ZÀ-ÿ][a-zà-ÿ]+\s+[A-ZÀ-ÿ][a-zà-ÿ]+)\s*\([A-Z]{3,10}\)",
                re.IGNORECASE,
            ),
            # DEV-007: "Name" followed directly by name on same line
            # Matches: "Name Giannone Michele"
            re.compile(
                r"(?:^|\n)\s*Name\s+([A-ZÀ-ÿ][a-zà-ÿ]+(?:\s+[A-ZÀ-ÿ][a-zà-ÿ]+)+)",
                re.MULTILINE | re.IGNORECASE,
            ),
        ]

    def _build_street_patterns(self) -> list[re.Pattern]:
        """Build patterns for street address detection (NOT CAP/city).

        DEV-007: Only anonymize street name + number.
        Keep CAP (zip code) and city visible for knowledge base matching.

        Example: "Via dei ciclamini 32, 96018 Pachino Italy"
        - Anonymize: "Via dei ciclamini 32" → "[INDIRIZZO_XXXX]"
        - Keep visible: "96018 Pachino Italy"
        """
        # Common street prefixes
        street_prefixes = r"(?:Via|Viale|Piazza|Corso|Largo|P\.za|V\.le|Vicolo|Strada|Contrada|Loc\.|Località)"
        # Civic number with optional letter suffix (e.g., 32, 15/A, 100B)
        civic_number = r"\d+(?:\s*[/]?\s*[a-zA-Z])?"

        return [
            # Italian street patterns: Via/Viale/Piazza + name + civic number
            # Captures only the street part, stops before comma or CAP (5 digits)
            re.compile(
                rf"({street_prefixes}\s+[A-Za-zÀ-ÿ\s']+\s*{civic_number})"
                r"(?=\s*,\s*\d{5}|\s*\d{5}|\s*$)",  # Lookahead: stops before comma+CAP, CAP, or end
                re.IGNORECASE,
            ),
        ]

    def _generate_anonymous_replacement(self, pii_type: PIIType, original: str) -> str:
        """Generate consistent anonymous replacement for PII."""
        # Use caching to ensure same value gets same replacement
        cache_key = f"{pii_type.value}:{original.lower()}"

        if cache_key in self._anonymization_cache:
            return self._anonymization_cache[cache_key]

        # Generate deterministic but anonymous replacement
        hash_input = f"{pii_type.value}:{original}:{uuid.getnode()}"  # Include MAC address for uniqueness
        hash_value = hashlib.sha256(hash_input.encode()).hexdigest()[:8].upper()

        replacements = {
            PIIType.EMAIL: f"user{hash_value[:6]}@example.com",
            PIIType.PHONE: f"+39 0{hash_value[:2]} {hash_value[2:8]}",
            PIIType.CODICE_FISCALE: f"CF{hash_value[:14]}",
            PIIType.PARTITA_IVA: f"IT{hash_value[:11]}",
            PIIType.IBAN: f"IT{hash_value[:2]}X{hash_value[2:12]}X{hash_value[12:24] if len(hash_value) >= 24 else hash_value[2:14]}",
            PIIType.CREDIT_CARD: f"**** **** **** {hash_value[:4]}",
            PIIType.NAME: f"[NOME_{hash_value[:4]}]",
            PIIType.ADDRESS: f"[INDIRIZZO_{hash_value[:4]}]",
            PIIType.DATE_OF_BIRTH: f"[DATA_{hash_value[:4]}]",
            PIIType.GENERIC_ID: f"[ID_{hash_value[:6]}]",
        }

        replacement = replacements.get(pii_type, f"[{pii_type.value.upper()}_{hash_value[:6]}]")
        self._anonymization_cache[cache_key] = replacement

        return replacement

    def _is_document_date_context(self, text: str, match_start: int, match_end: int) -> bool:
        """Check if date appears in document/publication context (not PII).

        Document publication dates (e.g., "Risoluzione n. 64 del 10 novembre 2025")
        are NOT personal data and should not be anonymized.

        Args:
            text: Full text being analyzed
            match_start: Start position of date match
            match_end: End position of date match

        Returns:
            True if date is in document context (should NOT be anonymized)
        """
        # Extract surrounding context (100 chars before/after for better accuracy)
        context_start = max(0, match_start - 100)
        context_end = min(len(text), match_end + 100)
        context = text[context_start:context_end].lower()

        # Document context indicators (NOT birth dates)
        # These patterns indicate regulatory/legal documents, not personal information
        document_indicators = [
            "risoluzion",  # Risoluzione
            "circolar",  # Circolare
            "decret",  # Decreto
            "interpell",  # Interpello
            "rispost",  # Risposta
            "provvediment",  # Provvedimento
            " del ",  # "del 10 novembre" (publication date marker)
            "n. ",  # Document number marker
            "numero ",  # Document number marker
            "n ",  # Short form
            "agenzia",  # Agenzia delle Entrate
            "inps",  # INPS
            "gazzetta",  # Gazzetta Ufficiale
            "pubblicat",  # Pubblicato/pubblicazione
            "dice",  # "cosa dice la risoluzione"
            "tutte le",  # "tutte le risoluzioni"
            "elenco",  # "elenco delle risoluzioni"
            "riassunto",  # "riassunto di tutte"
        ]

        return any(indicator in context for indicator in document_indicators)

    def detect_pii(self, text: str) -> list[PIIMatch]:
        """Detect PII in text and return matches."""
        matches = []

        # Check each PII type pattern
        for pii_type, patterns in self._patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    original_value = match.group(0)

                    # CRITICAL FIX: Skip dates in document context (not PII)
                    # Document publication dates like "del 10 novembre 2025" are NOT personal data
                    if pii_type == PIIType.DATE_OF_BIRTH:
                        if self._is_document_date_context(text, match.start(), match.end()):
                            logger.debug(
                                "pii_date_skipped_document_context",
                                date_value=original_value,
                                reason="document_publication_date_not_pii",
                            )
                            continue  # Skip - this is a document date, not PII

                    # Calculate confidence based on pattern specificity
                    confidence = self._calculate_confidence(pii_type, original_value)

                    # Skip low-confidence generic matches
                    if pii_type == PIIType.GENERIC_ID and confidence < 0.7:
                        continue

                    anonymized_value = self._generate_anonymous_replacement(pii_type, original_value)

                    matches.append(
                        PIIMatch(
                            pii_type=pii_type,
                            original_value=original_value,
                            anonymized_value=anonymized_value,
                            start_pos=match.start(),
                            end_pos=match.end(),
                            confidence=confidence,
                        )
                    )

        # Check for names
        for pattern in self._name_patterns:
            for match in pattern.finditer(text):
                name = match.group(1) if match.groups() else match.group(0)

                # Skip common words that might be matched as names
                if self._is_likely_name(name):
                    anonymized_value = self._generate_anonymous_replacement(PIIType.NAME, name)

                    matches.append(
                        PIIMatch(
                            pii_type=PIIType.NAME,
                            original_value=name,
                            anonymized_value=anonymized_value,
                            start_pos=match.start(1) if match.groups() else match.start(),
                            end_pos=match.end(1) if match.groups() else match.end(),
                            confidence=0.8,
                        )
                    )

        # DEV-007: Check for street addresses (preserving CAP/city for KB matching)
        for pattern in self._street_patterns:
            for match in pattern.finditer(text):
                street = match.group(1) if match.groups() else match.group(0)
                # Skip if it looks like a very short match (false positive)
                if len(street) < 8:
                    continue
                anonymized_value = self._generate_anonymous_replacement(PIIType.ADDRESS, street)
                matches.append(
                    PIIMatch(
                        pii_type=PIIType.ADDRESS,
                        original_value=street,
                        anonymized_value=anonymized_value,
                        start_pos=match.start(1) if match.groups() else match.start(),
                        end_pos=match.end(1) if match.groups() else match.end(),
                        confidence=0.9,
                    )
                )

        # DEV-007: Deduplicate matches by (start_pos, end_pos) to avoid double replacement
        # Multiple patterns can match the same text, causing position corruption
        seen_positions: set[tuple[int, int]] = set()
        deduplicated_matches: list[PIIMatch] = []
        for match in matches:
            pos_key = (match.start_pos, match.end_pos)
            if pos_key not in seen_positions:
                seen_positions.add(pos_key)
                deduplicated_matches.append(match)

        # Sort matches by position (reverse order for replacement)
        deduplicated_matches.sort(key=lambda x: x.start_pos, reverse=True)

        return deduplicated_matches

    def _calculate_confidence(self, pii_type: PIIType, value: str) -> float:
        """Calculate confidence score for PII detection."""
        base_confidence = {
            PIIType.EMAIL: 0.95,
            PIIType.CODICE_FISCALE: 0.98,
            PIIType.PARTITA_IVA: 0.90,
            PIIType.IBAN: 0.95,
            PIIType.CREDIT_CARD: 0.90,
            PIIType.PHONE: 0.85,
            PIIType.DATE_OF_BIRTH: 0.80,
            PIIType.GENERIC_ID: 0.60,
            PIIType.NAME: 0.70,
            PIIType.ADDRESS: 0.75,
        }

        confidence = base_confidence.get(pii_type, 0.5)

        # Adjust confidence based on value characteristics
        if pii_type == PIIType.CODICE_FISCALE:
            # More validation for Italian tax codes
            if self._validate_codice_fiscale(value):
                confidence = 0.99
            else:
                confidence = 0.60

        elif pii_type == PIIType.PHONE:
            # Higher confidence for Italian numbers
            if value.startswith("+39") or re.match(r"^3[0-9]{2}", value.replace(" ", "").replace("-", "")):
                confidence = 0.95

        return confidence

    def _validate_codice_fiscale(self, cf: str) -> bool:
        """Validate Italian tax code format and checksum."""
        if len(cf) != 16:
            return False

        # Basic format check (already done by regex, but double-check)
        if not re.match(r"^[A-Z]{6}[0-9]{2}[A-Z][0-9]{2}[A-Z][0-9]{3}[A-Z]$", cf.upper()):
            return False

        # Checksum validation would require the full algorithm
        # For now, we trust the format check
        return True

    def _is_likely_name(self, text: str) -> bool:
        """Check if text is likely a person's name."""
        # Skip common words that might be matched as names
        common_words = {
            "il",
            "la",
            "lo",
            "le",
            "gli",
            "un",
            "una",
            "di",
            "da",
            "del",
            "della",
            "che",
            "con",
            "per",
            "sono",
            "hanno",
            "questa",
            "questo",
            "dove",
            "come",
            "quando",
            "perché",
            "cosa",
            "chi",
            "quale",
            "cui",
        }

        words = text.lower().split()

        # Skip if all words are common Italian words
        if all(word in common_words for word in words):
            return False

        # Must start with capital letter and be reasonable length
        return not (not text[0].isupper() or len(text) < 2 or len(text) > 50)

    def anonymize_text(self, text: str, preserve_structure: bool = True) -> AnonymizationResult:
        """Anonymize PII in text while preserving structure."""
        if not text:
            return AnonymizationResult(anonymized_text="", pii_matches=[], anonymization_map={})

        matches = self.detect_pii(text)
        anonymized_text = text
        anonymization_map = {}

        # Replace PII with anonymous values (reverse order to maintain positions)
        for match in matches:
            anonymized_text = (
                anonymized_text[: match.start_pos] + match.anonymized_value + anonymized_text[match.end_pos :]
            )

            anonymization_map[match.original_value] = match.anonymized_value

            logger.info(
                "pii_anonymized",
                pii_type=match.pii_type.value,
                confidence=match.confidence,
                original_length=len(match.original_value),
                anonymized_length=len(match.anonymized_value),
            )

        logger.info(
            "text_anonymization_complete",
            original_length=len(text),
            anonymized_length=len(anonymized_text),
            pii_matches_count=len(matches),
            pii_types_found=[match.pii_type.value for match in matches],
        )

        return AnonymizationResult(
            anonymized_text=anonymized_text, pii_matches=matches, anonymization_map=anonymization_map
        )

    def anonymize_structured_data(self, data: dict) -> tuple[dict, AnonymizationResult]:
        """Anonymize PII in structured data (dictionaries)."""
        anonymized_data: dict = {}
        all_matches: list[PIIMatch] = []
        all_anonymization_map: dict[str, str] = {}

        for key, value in data.items():
            if isinstance(value, str):
                result = self.anonymize_text(value)
                anonymized_data[key] = result.anonymized_text
                all_matches.extend(result.pii_matches)
                all_anonymization_map.update(result.anonymization_map)

            elif isinstance(value, dict):
                nested_data, nested_result = self.anonymize_structured_data(value)
                anonymized_data[key] = nested_data
                all_matches.extend(nested_result.pii_matches)
                all_anonymization_map.update(nested_result.anonymization_map)

            elif isinstance(value, list):
                anonymized_list: list[Any] = []
                for item in value:
                    if isinstance(item, str):
                        result = self.anonymize_text(item)
                        anonymized_list.append(result.anonymized_text)
                        all_matches.extend(result.pii_matches)
                        all_anonymization_map.update(result.anonymization_map)
                    elif isinstance(item, dict):
                        nested_data, nested_result = self.anonymize_structured_data(item)
                        anonymized_list.append(nested_data)
                        all_matches.extend(nested_result.pii_matches)
                        all_anonymization_map.update(nested_result.anonymization_map)
                    else:
                        anonymized_list.append(item)
                anonymized_data[key] = anonymized_list

            else:
                # Keep non-string values as-is
                anonymized_data[key] = value

        result = AnonymizationResult(
            anonymized_text="",  # Not applicable for structured data
            pii_matches=all_matches,
            anonymization_map=all_anonymization_map,
        )

        return anonymized_data, result

    def get_stats(self) -> dict[str, int]:
        """Get anonymization statistics."""
        return {
            "cached_anonymizations": len(self._anonymization_cache),
            "patterns_count": sum(len(patterns) for patterns in self._patterns.values()),
            "name_patterns_count": len(self._name_patterns),
            "street_patterns_count": len(self._street_patterns),  # DEV-007
        }

    def clear_cache(self):
        """Clear the anonymization cache."""
        self._anonymization_cache.clear()
        logger.info("anonymization_cache_cleared")


# Global anonymizer instance
anonymizer = PIIAnonymizer()
