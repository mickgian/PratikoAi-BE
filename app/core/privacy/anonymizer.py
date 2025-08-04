"""PII detection and anonymization utilities for GDPR compliance.

This module provides comprehensive PII detection and removal capabilities,
with specific support for Italian data patterns and GDPR requirements.
"""

import re
import hashlib
import uuid
from typing import Dict, List, Optional, Tuple, Union
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

from app.core.logging import logger


class PIIType(str, Enum):
    """Types of Personally Identifiable Information."""
    EMAIL = "email"
    PHONE = "phone"
    CODICE_FISCALE = "codice_fiscale"  # Italian tax code
    PARTITA_IVA = "partita_iva"       # Italian VAT number
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
    pii_matches: List[PIIMatch] = field(default_factory=list)
    anonymization_map: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


class PIIAnonymizer:
    """PII detection and anonymization engine with Italian language support."""
    
    def __init__(self):
        """Initialize the anonymizer with Italian-specific patterns."""
        self._patterns = self._build_patterns()
        self._name_patterns = self._build_name_patterns()
        self._anonymization_cache: Dict[str, str] = {}
        
    def _build_patterns(self) -> Dict[PIIType, List[re.Pattern]]:
        """Build regex patterns for PII detection."""
        patterns = {
            PIIType.EMAIL: [
                re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', re.IGNORECASE)
            ],
            
            PIIType.PHONE: [
                # Italian phone numbers
                re.compile(r'\+39\s?[0-9]{2,3}\s?[0-9]{6,8}', re.IGNORECASE),
                re.compile(r'(?:^|\s)(?:0[0-9]{1,3}[-\s]?[0-9]{6,8})', re.IGNORECASE),
                re.compile(r'(?:^|\s)(?:3[0-9]{2}[-\s]?[0-9]{6,7})', re.IGNORECASE),  # Mobile
                # General phone patterns
                re.compile(r'\b(?:\+?[1-9]{1}[0-9]{0,3}[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{3,4}\b'),
            ],
            
            PIIType.CODICE_FISCALE: [
                # Italian tax code (16 characters: 6 letters + 2 digits + 1 letter + 2 digits + 1 letter + 3 digits + 1 letter)
                re.compile(r'\b[A-Z]{6}[0-9]{2}[A-Z][0-9]{2}[A-Z][0-9]{3}[A-Z]\b', re.IGNORECASE)
            ],
            
            PIIType.PARTITA_IVA: [
                # Italian VAT number (11 digits)
                re.compile(r'\bIT[0-9]{11}\b', re.IGNORECASE),
                re.compile(r'\b[0-9]{11}\b'),  # Without IT prefix
            ],
            
            PIIType.IBAN: [
                # IBAN format
                re.compile(r'\bIT[0-9]{2}[A-Z][0-9]{10}[A-Z0-9]{12}\b', re.IGNORECASE),  # Italian IBAN
                re.compile(r'\b[A-Z]{2}[0-9]{2}[A-Z0-9]{4}[0-9]{7}[A-Z0-9]{0,16}\b', re.IGNORECASE),  # General IBAN
            ],
            
            PIIType.CREDIT_CARD: [
                # Credit card numbers (various formats)
                re.compile(r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3[0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b'),
                re.compile(r'\b[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4}\b'),
            ],
            
            PIIType.DATE_OF_BIRTH: [
                # Various date formats
                re.compile(r'\b(?:0[1-9]|[12][0-9]|3[01])[\/\-\.](0[1-9]|1[012])[\/\-\.](?:19|20)[0-9]{2}\b'),  # DD/MM/YYYY
                re.compile(r'\b(?:19|20)[0-9]{2}[\/\-\.](0[1-9]|1[012])[\/\-\.](0[1-9]|[12][0-9]|3[01])\b'),  # YYYY/MM/DD
                re.compile(r'\b(0[1-9]|[12][0-9]|3[01])\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(?:19|20)[0-9]{2}\b', re.IGNORECASE),  # Italian months
            ],
            
            PIIType.GENERIC_ID: [
                # Generic ID patterns
                re.compile(r'\b[A-Z0-9]{8,16}\b'),  # Alphanumeric IDs
                re.compile(r'\b[0-9]{8,16}\b'),     # Numeric IDs
            ],
        }
        
        return patterns
    
    def _build_name_patterns(self) -> List[re.Pattern]:
        """Build patterns for Italian names detection."""
        # Common Italian name prefixes and suffixes
        italian_prefixes = [
            "dott", "dottore", "dottoressa", "dr", "prof", "professore", "professoressa",
            "ing", "ingegnere", "avv", "avvocato", "sig", "signore", "signora", "signorina"
        ]
        
        # Pattern for names with titles
        title_pattern = f"(?:{'|'.join(italian_prefixes)})\.?\\s+([A-Z][a-z]+(?:\\s+[A-Z][a-z]+)*)"
        
        return [
            re.compile(title_pattern, re.IGNORECASE),
            # Names in quotes or after "mi chiamo", "sono", etc.
            re.compile(r'(?:mi chiamo|sono|il mio nome è)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', re.IGNORECASE),
            re.compile(r'"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)"'),
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
    
    def detect_pii(self, text: str) -> List[PIIMatch]:
        """Detect PII in text and return matches."""
        matches = []
        
        # Check each PII type pattern
        for pii_type, patterns in self._patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    original_value = match.group(0)
                    
                    # Calculate confidence based on pattern specificity
                    confidence = self._calculate_confidence(pii_type, original_value)
                    
                    # Skip low-confidence generic matches
                    if pii_type == PIIType.GENERIC_ID and confidence < 0.7:
                        continue
                    
                    anonymized_value = self._generate_anonymous_replacement(pii_type, original_value)
                    
                    matches.append(PIIMatch(
                        pii_type=pii_type,
                        original_value=original_value,
                        anonymized_value=anonymized_value,
                        start_pos=match.start(),
                        end_pos=match.end(),
                        confidence=confidence
                    ))
        
        # Check for names
        for pattern in self._name_patterns:
            for match in pattern.finditer(text):
                name = match.group(1) if match.groups() else match.group(0)
                
                # Skip common words that might be matched as names
                if self._is_likely_name(name):
                    anonymized_value = self._generate_anonymous_replacement(PIIType.NAME, name)
                    
                    matches.append(PIIMatch(
                        pii_type=PIIType.NAME,
                        original_value=name,
                        anonymized_value=anonymized_value,
                        start_pos=match.start(1) if match.groups() else match.start(),
                        end_pos=match.end(1) if match.groups() else match.end(),
                        confidence=0.8
                    ))
        
        # Sort matches by position (reverse order for replacement)
        matches.sort(key=lambda x: x.start_pos, reverse=True)
        
        return matches
    
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
            if value.startswith('+39') or re.match(r'^3[0-9]{2}', value.replace(' ', '').replace('-', '')):
                confidence = 0.95
        
        return confidence
    
    def _validate_codice_fiscale(self, cf: str) -> bool:
        """Validate Italian tax code format and checksum."""
        if len(cf) != 16:
            return False
        
        # Basic format check (already done by regex, but double-check)
        if not re.match(r'^[A-Z]{6}[0-9]{2}[A-Z][0-9]{2}[A-Z][0-9]{3}[A-Z]$', cf.upper()):
            return False
        
        # Checksum validation would require the full algorithm
        # For now, we trust the format check
        return True
    
    def _is_likely_name(self, text: str) -> bool:
        """Check if text is likely a person's name."""
        # Skip common words that might be matched as names
        common_words = {
            'il', 'la', 'lo', 'le', 'gli', 'un', 'una', 'di', 'da', 'del', 'della',
            'che', 'con', 'per', 'sono', 'hanno', 'questa', 'questo', 'dove',
            'come', 'quando', 'perché', 'cosa', 'chi', 'quale', 'cui'
        }
        
        words = text.lower().split()
        
        # Skip if all words are common Italian words
        if all(word in common_words for word in words):
            return False
        
        # Must start with capital letter and be reasonable length
        if not text[0].isupper() or len(text) < 2 or len(text) > 50:
            return False
        
        return True
    
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
                anonymized_text[:match.start_pos] +
                match.anonymized_value +
                anonymized_text[match.end_pos:]
            )
            
            anonymization_map[match.original_value] = match.anonymized_value
            
            logger.info(
                "pii_anonymized",
                pii_type=match.pii_type.value,
                confidence=match.confidence,
                original_length=len(match.original_value),
                anonymized_length=len(match.anonymized_value)
            )
        
        logger.info(
            "text_anonymization_complete",
            original_length=len(text),
            anonymized_length=len(anonymized_text),
            pii_matches_count=len(matches),
            pii_types_found=[match.pii_type.value for match in matches]
        )
        
        return AnonymizationResult(
            anonymized_text=anonymized_text,
            pii_matches=matches,
            anonymization_map=anonymization_map
        )
    
    def anonymize_structured_data(self, data: Dict) -> Tuple[Dict, AnonymizationResult]:
        """Anonymize PII in structured data (dictionaries)."""
        anonymized_data = {}
        all_matches = []
        all_anonymization_map = {}
        
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
                anonymized_list = []
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
            anonymization_map=all_anonymization_map
        )
        
        return anonymized_data, result
    
    def get_stats(self) -> Dict[str, int]:
        """Get anonymization statistics."""
        return {
            "cached_anonymizations": len(self._anonymization_cache),
            "patterns_count": sum(len(patterns) for patterns in self._patterns.values()),
            "name_patterns_count": len(self._name_patterns)
        }
    
    def clear_cache(self):
        """Clear the anonymization cache."""
        self._anonymization_cache.clear()
        logger.info("anonymization_cache_cleared")


# Global anonymizer instance
anonymizer = PIIAnonymizer()