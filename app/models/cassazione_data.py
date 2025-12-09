"""Data models for Italian Supreme Court (Cassazione) decisions.

This module provides data structures for storing and manipulating
Cassazione court decisions with comprehensive metadata and legal analysis.
"""

import hashlib
import json
import re
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class CourtSection(str, Enum):
    """Enumeration of Cassazione court sections."""

    CIVILE = "civile"
    TRIBUTARIA = "tributaria"
    LAVORO = "lavoro"
    PENALE = "penale"
    SEZIONI_UNITE = "sezioni_unite"

    @classmethod
    def from_italian_text(cls, text: str) -> "CourtSection":
        """Create court section from Italian text."""
        text = text.lower().strip()
        if "civile" in text:
            return cls.CIVILE
        elif "tributaria" in text:
            return cls.TRIBUTARIA
        elif "lavoro" in text:
            return cls.LAVORO
        elif "penale" in text:
            return cls.PENALE
        elif "sezioni unite" in text or "unite" in text:
            return cls.SEZIONI_UNITE
        else:
            return cls.CIVILE  # Default fallback

    def italian_name(self) -> str:
        """Get Italian display name."""
        names = {
            self.CIVILE: "Sezione Civile",
            self.TRIBUTARIA: "Sezione Tributaria",
            self.LAVORO: "Sezione Lavoro",
            self.PENALE: "Sezione Penale",
            self.SEZIONI_UNITE: "Sezioni Unite",
        }
        return names[self]


class DecisionType(str, Enum):
    """Enumeration of decision types."""

    SENTENZA = "sentenza"
    ORDINANZA = "ordinanza"
    DECRETO = "decreto"
    AUTO = "auto"

    @classmethod
    def from_italian_text(cls, text: str) -> "DecisionType":
        """Create decision type from Italian text."""
        text = text.lower().strip()
        if "sentenza" in text:
            return cls.SENTENZA
        elif "ordinanza" in text:
            return cls.ORDINANZA
        elif "decreto" in text:
            return cls.DECRETO
        elif "auto" in text:
            return cls.AUTO
        else:
            return cls.SENTENZA  # Default fallback

    def italian_name(self) -> str:
        """Get Italian display name."""
        names = {self.SENTENZA: "Sentenza", self.ORDINANZA: "Ordinanza", self.DECRETO: "Decreto", self.AUTO: "Auto"}
        return names[self]


class JuridicalSubject(str, Enum):
    """Enumeration of juridical subject areas."""

    DIRITTO_CIVILE = "diritto_civile"
    DIRITTO_COMMERCIALE = "diritto_commerciale"
    DIRITTO_TRIBUTARIO = "diritto_tributario"
    DIRITTO_DEL_LAVORO = "diritto_del_lavoro"
    DIRITTO_SOCIETARIO = "diritto_societario"
    DIRITTO_PENALE = "diritto_penale"
    DIRITTO_AMMINISTRATIVO = "diritto_amministrativo"
    DIRITTO_COSTITUZIONALE = "diritto_costituzionale"
    OTHER = "other"

    @classmethod
    def classify_from_keywords(cls, keywords: list[str]) -> "JuridicalSubject":
        """Classify juridical subject from keywords."""
        keywords_lower = [k.lower() for k in keywords]

        # Tax law keywords
        tax_keywords = ["iva", "imposte", "tasse", "detrazioni", "tributi", "fiscale", "erariale"]
        if any(kw in " ".join(keywords_lower) for kw in tax_keywords):
            return cls.DIRITTO_TRIBUTARIO

        # Corporate law keywords
        corporate_keywords = ["società", "amministratore", "srl", "spa", "consiglio", "assemblea"]
        if any(kw in " ".join(keywords_lower) for kw in corporate_keywords):
            return cls.DIRITTO_SOCIETARIO

        # Labor law keywords
        labor_keywords = ["lavoro", "licenziamento", "tfr", "inps", "inail", "contratto lavoro"]
        if any(kw in " ".join(keywords_lower) for kw in labor_keywords):
            return cls.DIRITTO_DEL_LAVORO

        # Civil law keywords
        civil_keywords = ["contratto", "responsabilità", "risarcimento", "proprietà", "famiglia"]
        if any(kw in " ".join(keywords_lower) for kw in civil_keywords):
            return cls.DIRITTO_CIVILE

        # Commercial law keywords
        commercial_keywords = ["commercio", "vendita", "impresa", "contratti commerciali"]
        if any(kw in " ".join(keywords_lower) for kw in commercial_keywords):
            return cls.DIRITTO_COMMERCIALE

        return cls.OTHER


@dataclass
class LegalPrinciple:
    """Represents a legal principle extracted from a decision."""

    text: str
    confidence_score: Decimal = field(default_factory=lambda: Decimal("0.80"))
    supporting_citations: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)

    def categorize(self) -> JuridicalSubject:
        """Categorize the principle by juridical subject."""
        return JuridicalSubject.classify_from_keywords(self.keywords + [self.text])

    @classmethod
    def extract_from_text(cls, text: str) -> list["LegalPrinciple"]:
        """Extract legal principles from decision text."""
        principles = []

        # Look for numbered principles
        pattern = r"\d+\)\s*([^\n]+(?:\n[^\d\n][^\n]*)*?)(?=\d+\)|$)"
        matches = re.findall(pattern, text, re.MULTILINE)

        for match in matches:
            principle_text = match.strip()
            if len(principle_text) > 20:  # Filter out short matches
                principles.append(
                    cls(
                        text=principle_text,
                        confidence_score=Decimal("0.85"),
                        keywords=cls._extract_keywords(principle_text),
                    )
                )

        # Look for "principio di diritto" sections
        principle_pattern = r"principio[^:]*:?\s*([^\n]+(?:\n[^\n]*?)*?)(?=\n\s*\n|$)"
        principle_matches = re.findall(principle_pattern, text, re.IGNORECASE | re.MULTILINE)

        for match in principle_matches:
            principle_text = match.strip()
            if len(principle_text) > 20:
                principles.append(
                    cls(
                        text=principle_text,
                        confidence_score=Decimal("0.90"),
                        keywords=cls._extract_keywords(principle_text),
                    )
                )

        return principles

    @staticmethod
    def _extract_keywords(text: str) -> list[str]:
        """Extract keywords from principle text."""
        # Common Italian legal terms
        legal_terms = [
            "amministratore",
            "società",
            "responsabilità",
            "contratto",
            "inadempimento",
            "risarcimento",
            "danno",
            "colpa",
            "dolo",
            "obbligazione",
            "diritto",
            "dovere",
            "iva",
            "imposta",
            "tributo",
            "lavoro",
            "licenziamento",
            "tfr",
        ]

        found_keywords = []
        text_lower = text.lower()

        for term in legal_terms:
            if term in text_lower:
                found_keywords.append(term)

        return found_keywords[:5]  # Limit to 5 keywords


@dataclass
class Citation:
    """Represents a citation to law or other decisions."""

    type: str  # "law", "decision", "regulation"
    reference: str
    title: str | None = None
    url: str | None = None
    court_section: CourtSection | None = None
    decision_date: date | None = None

    def is_law_citation(self) -> bool:
        """Check if this is a citation to law."""
        return self.type == "law"

    def is_decision_citation(self) -> bool:
        """Check if this is a citation to another decision."""
        return self.type == "decision"

    def is_valid(self) -> bool:
        """Validate the citation."""
        return bool(self.reference and self.reference.strip())

    @classmethod
    def extract_from_text(cls, text: str) -> list["Citation"]:
        """Extract citations from decision text."""
        citations = []

        # Extract law citations (Art. X c.c., DPR, etc.)
        law_pattern = r"(?:Art\.?\s*\d+[^\n]*?(?:Codice Civile|c\.c\.|DPR|D\.Lgs|Legge)[^\n]*?)"
        law_matches = re.findall(law_pattern, text, re.IGNORECASE)

        for match in law_matches:
            citations.append(cls(type="law", reference=match.strip()))

        # Extract decision citations (Cass. Civ., etc.)
        decision_pattern = r"(?:Cass\.?\s*(?:Civ\.?|Trib\.?|Lav\.?|Pen\.?)?[^\n]*?\d+/\d+)"
        decision_matches = re.findall(decision_pattern, text, re.IGNORECASE)

        for match in decision_matches:
            citations.append(cls(type="decision", reference=match.strip()))

        return citations


@dataclass
class ScrapingResult:
    """Represents the result of a scraping operation."""

    decisions_found: int
    decisions_processed: int
    decisions_saved: int
    errors: int
    duration_seconds: int = 0
    start_date: date | None = None
    end_date: date | None = None

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.decisions_found == 0:
            return 0.0
        return self.decisions_saved / self.decisions_found

    @property
    def processing_rate(self) -> float:
        """Calculate processing rate."""
        if self.decisions_found == 0:
            return 0.0
        return self.decisions_processed / self.decisions_found

    @property
    def duration_minutes(self) -> float:
        """Get duration in minutes."""
        return self.duration_seconds / 60.0

    def is_valid(self) -> bool:
        """Validate the result."""
        return (
            self.decisions_processed <= self.decisions_found
            and self.decisions_saved <= self.decisions_processed
            and self.errors >= 0
        )

    @classmethod
    def combine(cls, results: list["ScrapingResult"]) -> "ScrapingResult":
        """Combine multiple scraping results."""
        if not results:
            return cls(0, 0, 0, 0)

        return cls(
            decisions_found=sum(r.decisions_found for r in results),
            decisions_processed=sum(r.decisions_processed for r in results),
            decisions_saved=sum(r.decisions_saved for r in results),
            errors=sum(r.errors for r in results),
            duration_seconds=sum(r.duration_seconds for r in results),
        )


@dataclass
class ScrapingStatistics:
    """Tracks scraping performance statistics."""

    total_pages_attempted: int = 0
    total_pages_successful: int = 0
    total_decisions_found: int = 0
    total_decisions_saved: int = 0
    page_durations: list[float] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Calculate page success rate."""
        if self.total_pages_attempted == 0:
            return 0.0
        return self.total_pages_successful / self.total_pages_attempted

    @property
    def save_rate(self) -> float:
        """Calculate decision save rate."""
        if self.total_decisions_found == 0:
            return 0.0
        return self.total_decisions_saved / self.total_decisions_found

    @property
    def average_page_duration(self) -> float:
        """Calculate average page duration."""
        if not self.page_durations:
            return 0.0
        return sum(self.page_durations) / len(self.page_durations)

    def record_page_scraped(self, success: bool, duration: float):
        """Record a page scraping attempt."""
        self.total_pages_attempted += 1
        if success:
            self.total_pages_successful += 1
        self.page_durations.append(duration)

    def record_decision_processed(self, saved: bool):
        """Record a decision processing attempt."""
        self.total_decisions_found += 1
        if saved:
            self.total_decisions_saved += 1

    def reset(self):
        """Reset all statistics."""
        self.total_pages_attempted = 0
        self.total_pages_successful = 0
        self.total_decisions_found = 0
        self.total_decisions_saved = 0
        self.page_durations.clear()


@dataclass
class ScrapingError(Exception):
    """Represents a scraping error with context."""

    message: str
    error_code: str
    url: str | None = None
    timestamp: datetime | None = None
    retry_count: int = 0
    is_recoverable: bool = True

    def __post_init__(self):
        super().__init__(self.message)

    def category(self) -> str:
        """Categorize the error."""
        code_lower = self.error_code.lower()
        message_lower = self.message.lower()

        if "timeout" in code_lower or "timeout" in message_lower:
            return "network"
        elif "parse" in code_lower or "html" in message_lower:
            return "parsing"
        elif "http" in code_lower or "server" in message_lower:
            return "server"
        elif "database" in code_lower or "db" in message_lower:
            return "database"
        else:
            return "unknown"

    def get_recovery_suggestions(self) -> list[str]:
        """Get suggestions for recovering from this error."""
        category = self.category()

        suggestions = {
            "network": [
                "Retry with exponential backoff",
                "Increase timeout duration",
                "Add delay between requests",
                "Check network connectivity",
            ],
            "parsing": [
                "Update HTML parsing selectors",
                "Handle malformed HTML gracefully",
                "Log HTML content for inspection",
            ],
            "server": ["Retry after delay", "Check server status", "Implement rate limiting"],
            "database": ["Check database connection", "Retry database operation", "Validate data before saving"],
        }

        return suggestions.get(category, ["Review error details", "Contact system administrator"])


@dataclass
class CassazioneDecision:
    """Represents a complete Cassazione court decision."""

    decision_number: str
    date: date
    section: CourtSection
    subject: str
    full_text: str | None = None
    subsection: str | None = None
    summary: str | None = None
    source_url: str | None = None
    legal_principles: list[str] = field(default_factory=list)
    judge_names: list[str] = field(default_factory=list)
    party_names: list[str] = field(default_factory=list)
    citations_to_laws: list[str] = field(default_factory=list)
    citations_to_decisions: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    decision_type: DecisionType = DecisionType.SENTENZA
    confidence_score: Decimal = field(default_factory=lambda: Decimal("0.95"))

    def __post_init__(self):
        """Validate decision data after initialization."""
        # Validate decision number format - should look like a proper court decision
        # Accept formats: "30016", "30016/2025", or text containing cass./sentenza/ordinanza
        if not re.search(r"\d{4,}|\d+[/]\d+|cass\.|sentenza|ordinanza", self.decision_number, re.IGNORECASE):
            raise ValueError(f"Invalid decision number format: {self.decision_number}")

        # Validate date is not in future
        if self.date > date.today():
            raise ValueError("Decision date cannot be in the future")

    @property
    def juridical_subject(self) -> JuridicalSubject:
        """Auto-classify juridical subject from keywords and content."""
        all_keywords = self.keywords + [self.subject]
        if self.full_text:
            all_keywords.append(self.full_text[:500])  # First 500 chars

        return JuridicalSubject.classify_from_keywords(all_keywords)

    def generate_unique_identifier(self) -> str:
        """Generate unique identifier for this decision."""
        # Create a more readable identifier
        # Extract core numbers from decision number
        numbers = re.findall(r"\d+", self.decision_number)
        if numbers and len(numbers) >= 2:
            # Format as decision_number_year
            core_number = f"{numbers[0]}_{numbers[1]}"
        else:
            # Fallback to cleaned full decision number
            core_number = re.sub(r"[^\w\d]", "_", self.decision_number.lower()).strip("_")

        date_str = self.date.strftime("%Y_%m_%d")

        # Create cass_section_number_year format
        section_prefix = {
            CourtSection.CIVILE: "cass_civ",
            CourtSection.TRIBUTARIA: "cass_trib",
            CourtSection.LAVORO: "cass_lav",
            CourtSection.PENALE: "cass_pen",
            CourtSection.SEZIONI_UNITE: "cass_su",
        }

        prefix = section_prefix.get(self.section, f"cass_{self.section.value}")

        return f"{prefix}_{core_number}_{date_str}"

    def extract_legal_principles(self) -> list[str]:
        """Extract legal principles from decision text."""
        if not self.full_text:
            return self.legal_principles

        principles = LegalPrinciple.extract_from_text(self.full_text)
        return [p.text for p in principles]

    def to_dict(self) -> dict[str, Any]:
        """Convert decision to dictionary for storage."""
        data = asdict(self)
        # Convert enum values to strings
        data["section"] = self.section.value
        data["decision_type"] = self.decision_type.value
        data["juridical_subject"] = self.juridical_subject.value
        # Convert date to string
        data["date"] = self.date.isoformat()
        # Convert Decimal to float
        data["confidence_score"] = float(self.confidence_score)

        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CassazioneDecision":
        """Create decision from dictionary."""
        # Convert string values back to enums and types
        if "section" in data and isinstance(data["section"], str):
            data["section"] = CourtSection(data["section"])

        if "decision_type" in data and isinstance(data["decision_type"], str):
            data["decision_type"] = DecisionType(data["decision_type"])

        if "date" in data and isinstance(data["date"], str):
            data["date"] = date.fromisoformat(data["date"])

        if "confidence_score" in data and isinstance(data["confidence_score"], int | float):
            data["confidence_score"] = Decimal(str(data["confidence_score"]))

        # Remove fields that aren't in the dataclass
        allowed_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in allowed_fields}

        return cls(**filtered_data)
