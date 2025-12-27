"""Atomic Facts Extraction System for PratikoAI.

This module extracts and canonicalizes atomic facts from Italian professional queries
to improve classification accuracy, cache hit rates, and search relevance.
"""

import re
import time
from dataclasses import (
    dataclass,
    field,
)
from datetime import datetime
from typing import (
    Dict,
    List,
    Optional,
    TypedDict,
)

from app.core.logging import logger
from app.schemas.proactivity import ExtractedParameter, ParameterExtractionResult


class IntentSchema(TypedDict):
    """Schema defining required and optional parameters for an intent."""

    required: list[str]
    optional: list[str]
    defaults: dict[str, int | str | float]


# Intent schemas defining required/optional parameters per intent type
# DEV-154: Parameter coverage calculation for proactive assistant
INTENT_SCHEMAS: dict[str, IntentSchema] = {
    "calcolo_irpef": {
        "required": ["tipo_contribuente", "reddito"],
        "optional": ["detrazioni", "anno_fiscale", "regione"],
        "defaults": {"anno_fiscale": 2025},
    },
    "calcolo_iva": {
        "required": ["importo"],
        "optional": ["aliquota", "tipo_operazione"],
        "defaults": {"aliquota": 22},
    },
    "calcolo_contributi_inps": {
        "required": ["importo", "tipo_contribuente"],
        "optional": ["anno"],
        "defaults": {"anno": 2025},
    },
    "calcolo_tfr": {
        "required": ["retribuzione_annua", "anni_servizio"],
        "optional": ["rivalutazione"],
        "defaults": {},
    },
    "calcolo_netto": {
        "required": ["importo_lordo"],
        "optional": ["tipo_contratto", "regione"],
        "defaults": {},
    },
    "verifica_scadenza": {
        "required": ["tipo_adempimento"],
        "optional": ["data_riferimento"],
        "defaults": {},
    },
    "cerca_normativa": {
        "required": ["argomento"],
        "optional": ["anno", "tipo_documento"],
        "defaults": {},
    },
}


@dataclass
class ExtractionSpan:
    """Represents a span of text where a fact was extracted."""

    start: int
    end: int

    @property
    def length(self) -> int:
        return self.end - self.start


@dataclass
class MonetaryAmount:
    """Represents an extracted monetary amount with metadata."""

    amount: float
    currency: str = "EUR"
    is_percentage: bool = False
    confidence: float = 0.0
    original_text: str = ""
    span: ExtractionSpan | None = None

    def __post_init__(self):
        """Validate monetary amount after initialization."""
        if self.amount < 0:
            logger.warning(f"Negative monetary amount extracted: {self.amount}")
        if not 0.0 <= self.confidence <= 1.0:
            self.confidence = max(0.0, min(1.0, self.confidence))


@dataclass
class DateFact:
    """Represents an extracted date or time-related fact."""

    date_type: str  # "specific", "relative", "tax_year", "duration", "deadline"
    original_text: str = ""
    confidence: float = 0.0
    span: ExtractionSpan | None = None

    # Specific date fields
    iso_date: str | None = None

    # Relative date fields
    relative_expression: str | None = None

    # Tax year fields
    tax_year: int | None = None

    # Duration fields
    duration_text: str | None = None
    duration_value: int | None = None
    duration_unit: str | None = None  # "days", "months", "years"

    def __post_init__(self):
        """Validate date fact after initialization."""
        if not 0.0 <= self.confidence <= 1.0:
            self.confidence = max(0.0, min(1.0, self.confidence))


@dataclass
class LegalEntity:
    """Represents an extracted legal or tax entity."""

    entity_type: str  # "codice_fiscale", "partita_iva", "company_type", "document_type", "legal_reference"
    original_text: str = ""
    canonical_form: str = ""
    identifier: str | None = None
    confidence: float = 0.0
    span: ExtractionSpan | None = None

    def __post_init__(self):
        """Validate legal entity after initialization."""
        if not 0.0 <= self.confidence <= 1.0:
            self.confidence = max(0.0, min(1.0, self.confidence))


@dataclass
class ProfessionalCategory:
    """Represents an extracted professional category or classification."""

    category_type: str  # "ccnl_sector", "job_level", "contract_type"
    original_text: str = ""
    confidence: float = 0.0
    span: ExtractionSpan | None = None

    # CCNL sector fields
    sector: str | None = None

    # Job level fields
    level: str | None = None

    # Contract type fields
    contract_type: str | None = None

    def __post_init__(self):
        """Validate professional category after initialization."""
        if not 0.0 <= self.confidence <= 1.0:
            self.confidence = max(0.0, min(1.0, self.confidence))


@dataclass
class GeographicInfo:
    """Represents extracted geographic information."""

    geo_type: str  # "region", "city", "area"
    original_text: str = ""
    confidence: float = 0.0
    span: ExtractionSpan | None = None

    # Geographic fields
    region: str | None = None
    city: str | None = None
    area: str | None = None  # "Nord", "Centro", "Sud"

    def __post_init__(self):
        """Validate geographic info after initialization."""
        if not 0.0 <= self.confidence <= 1.0:
            self.confidence = max(0.0, min(1.0, self.confidence))


@dataclass
class AtomicFacts:
    """Container for all extracted atomic facts from a query."""

    monetary_amounts: list[MonetaryAmount] = field(default_factory=list)
    dates: list[DateFact] = field(default_factory=list)
    legal_entities: list[LegalEntity] = field(default_factory=list)
    professional_categories: list[ProfessionalCategory] = field(default_factory=list)
    geographic_info: list[GeographicInfo] = field(default_factory=list)

    # Metadata
    extraction_time_ms: float = 0.0
    original_query: str = ""

    def is_empty(self) -> bool:
        """Check if no facts were extracted."""
        return (
            not self.monetary_amounts
            and not self.dates
            and not self.legal_entities
            and not self.professional_categories
            and not self.geographic_info
        )

    def fact_count(self) -> int:
        """Get total number of extracted facts."""
        return (
            len(self.monetary_amounts)
            + len(self.dates)
            + len(self.legal_entities)
            + len(self.professional_categories)
            + len(self.geographic_info)
        )

    def get_summary(self) -> dict[str, int]:
        """Get a summary of extracted fact types and counts."""
        return {
            "monetary_amounts": len(self.monetary_amounts),
            "dates": len(self.dates),
            "legal_entities": len(self.legal_entities),
            "professional_categories": len(self.professional_categories),
            "geographic_info": len(self.geographic_info),
            "total": self.fact_count(),
        }

    def to_canonical_strings(self) -> list[str]:
        """Convert extracted facts to canonical string representations for search.

        Returns list of canonical strings that represent key information:
        - Document references: "risoluzione 56"
        - Legal entities: "partita iva 12345678901"
        - Geographic info: "milano", "lombardia"

        These strings can be used to enhance search queries.
        """
        canonical_strings = []

        # Document references (highest priority for search)
        for entity in self.legal_entities:
            if entity.entity_type == "document_reference":
                # Use canonical form directly: "risoluzione 56"
                canonical_strings.append(entity.canonical_form)
            elif entity.entity_type == "legal_reference":
                # Include legal references: "articolo 69"
                canonical_strings.append(entity.canonical_form)

        # Geographic information (cities, regions for location-specific queries)
        for geo in self.geographic_info:
            if geo.location_type in ["city", "region"]:
                canonical_strings.append(geo.canonical_form.lower())

        return canonical_strings


class AtomicFactsExtractor:
    """Extracts and canonicalizes atomic facts from Italian professional queries.

    This system processes user queries before classification to extract, normalize,
    and structure key information including monetary amounts, dates, legal entities,
    professional categories, and geographic information.
    """

    def __init__(self):
        """Initialize the atomic facts extractor with Italian patterns."""
        self._load_patterns()
        self._load_canonicalization_rules()

    def _load_patterns(self):
        """Load regex patterns for extracting different types of facts."""
        # Monetary amount patterns
        self.monetary_patterns = {
            # Euro amounts - numeric format
            # Euro symbol followed by amount
            "euro_symbol": re.compile(r"€\s*(\d{1,3}(?:\.\d{3})*(?:,\d{1,2})?)", re.IGNORECASE),
            # Amount followed by euro word (handles both formats: 1.000,50 and 30000)
            "euro_word": re.compile(r"\b(\d+(?:\.\d{3})*(?:,\d{1,2})?|\d+(?:,\d{1,2})?)\s*euro\b", re.IGNORECASE),
            # Percentage patterns - numeric
            "percentage": re.compile(r"(\d+(?:,\d+)?)\s*(?:%|percento|per\s*cento)", re.IGNORECASE),
            # Percentage patterns - written
            "percentage_written": re.compile(
                r"\b((?:zero|un|uno|due|tre|quattro|cinque|sei|sette|otto|nove|dieci|"
                r"venti|trenta|quaranta|cinquanta|sessanta|settanta|ottanta|novanta|"
                r"cento|mille|duemila|tremila|quattromila|cinquemila|seimila|"
                r"settemila|ottomila|novemila|diecimila|ventimila|trentamila|"
                r"quarantamila|cinquantamila|centomila)+)\s+per\s+cento",
                re.IGNORECASE,
            ),
            # Written amounts in Italian (includes compound numbers)
            "euro_written": re.compile(
                r"\b((?:(?:zero|un|uno|due|tre|quattro|cinque|sei|sette|otto|nove|dieci|"
                r"venti|trenta|quaranta|cinquanta|sessanta|settanta|ottanta|novanta|"
                r"cento|mille|duemila|tremila|quattromila|cinquemila|seimila|"
                r"settemila|ottomila|novemila|diecimila|ventimila|trentamila|"
                r"quarantamila|cinquantamila|centomila|cinque|cento|cinquecento)\s*)+)\s+euro",
                re.IGNORECASE,
            ),
            # Euro-centesimi combination pattern
            "euro_centesimi": re.compile(r"(\d+)\s+euro\s+e\s+(\d+)\s+centesimi", re.IGNORECASE),
        }

        # Date patterns
        self.date_patterns = {
            # Numeric dates: dd/mm/yyyy, dd-mm-yyyy
            "date_dmy": re.compile(r"\b(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})\b"),
            # Italian dates with month names: "16 marzo 2024", "1° gennaio 2024"
            "date_italian_full": re.compile(
                r"\b(\d{1,2})°?\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|"
                r"luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(\d{4})\b",
                re.IGNORECASE,
            ),
            # Italian dates without year: "15 febbraio", "31 dicembre" (assumes current year)
            "date_italian_no_year": re.compile(
                r"\b(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|"
                r"luglio|agosto|settembre|ottobre|novembre|dicembre)(?!\s+\d{4})\b",
                re.IGNORECASE,
            ),
            # Date ranges: "dal 1 gennaio al 31 marzo 2024"
            "date_range": re.compile(
                r"dal\s+(\d{1,2})°?\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|"
                r"luglio|agosto|settembre|ottobre|novembre|dicembre)\s+al\s+(\d{1,2})°?\s+"
                r"(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(\d{4})",
                re.IGNORECASE,
            ),
            # Relative dates
            "relative_date": re.compile(
                r"\b(anno\s+scorso|prossimo\s+trimestre|settimana\s+scorsa|"
                r"fra\s+\w+\s+(?:giorni|mesi|anni)|prossimo\s+\w+)\b",
                re.IGNORECASE,
            ),
            # Tax years
            "tax_year": re.compile(
                r"anno\s+d[''']imposta\s+(\d{4})|dichiarazione\s+(\d{4})|redditi\s+anno\s+(\d{4})", re.IGNORECASE
            ),
            # Durations
            "duration": re.compile(r"(\d+)\s+(giorni|mesi|anni|anno)", re.IGNORECASE),
        }

        # Legal entity patterns
        self.legal_patterns = {
            # Italian tax codes
            "codice_fiscale": re.compile(
                r"\b(?:codice\s+fiscale|CF):?\s*([A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z])\b", re.IGNORECASE
            ),
            "partita_iva": re.compile(r"\b(?:partita\s+iva|p\.iva|p\.i\.v\.a\.):?\s*((?:IT)?\d{11})\b", re.IGNORECASE),
            # Company types
            "company_type": re.compile(
                r"\b(s\.r\.l\.?|srl|società\s+per\s+azioni|spa|s\.p\.a\.?|"
                r"società\s+in\s+nome\s+collettivo|snc|s\.n\.c\.?|"
                r"ditta\s+individuale)\b",
                re.IGNORECASE,
            ),
            # Document types (including regulatory documents)
            "document_type": re.compile(
                r"\b(f24|modello\s+730|730|fattura\s+elettronica|"
                r"dichiarazione\s+(?:dei\s+)?redditi|unico|cud|"
                r"risoluzione|circolare|risposta|interpello|sentenza|provvedimento)\b",
                re.IGNORECASE,
            ),
            # Document references with numbers (risoluzione n. 56, circolare n. 123, etc.)
            "document_reference": re.compile(
                r"\b(risoluzione|circolare|risposta|interpello|sentenza|provvedimento)"
                r"\s+n(?:umero)?\.?\s*(\d+(?:/\d{4})?)",
                re.IGNORECASE,
            ),
            # Legal references
            "legal_reference": re.compile(
                r"\b(?:art\.|articolo)\s*(\d+)(?:\s+comma\s+\d+)?\s+(c\.p\.c\.?|"
                r"del\s+codice\s+civile|c\.c\.?)|"
                r"\b(DPR|L\.|Legge)\s*(\d+\/\d{2,4})\b",
                re.IGNORECASE,
            ),
        }

        # Professional category patterns
        self.professional_patterns = {
            # CCNL sectors
            "ccnl_sector": re.compile(
                r"\b(?:ccnl\s+)?(metalmeccanici|commercio|industria\s+chimica|"
                r"costruzioni|tessile\s+abbigliamento|alimentare|bancari|"
                r"telecomunicazioni|trasporti|sanità|scuola)\b",
                re.IGNORECASE,
            ),
            # Job levels
            "job_level": re.compile(
                r"\b(?:livello\s+)?([1-8]°?\s+livello|livello\s+[1-8]|"
                r"quadro|dirigente|apprendista|operaio|impiegato)\b",
                re.IGNORECASE,
            ),
            # Contract types
            "contract_type": re.compile(
                r"\b(?:contratto\s+)?(?:a\s+)?(tempo\s+determinato|tempo\s+indeterminato|"
                r"apprendistato|stagionale|part\s*time|full\s*time)\b",
                re.IGNORECASE,
            ),
        }

        # Geographic patterns
        self.geographic_patterns = {
            # Italian regions
            "region": re.compile(
                r"\b(Lombardia|Veneto|Piemonte|Emilia[-\s]Romagna|Toscana|Lazio|"
                r"Campania|Sicilia|Puglia|Calabria|Sardegna|Liguria|Marche|"
                r"Abruzzo|Friuli[-\s]Venezia\s+Giulia|Trentino[-\s]Alto\s+Adige|"
                r"Umbria|Basilicata|Molise|Valle\s+d[\'\']Aosta)\b",
                re.IGNORECASE,
            ),
            # Major Italian cities
            "city": re.compile(
                r"\b(?:città\s+di\s+|comune\s+di\s+|a\s+|di\s+|sede\s+di\s+)?"
                r"(Milano|Roma|Napoli|Torino|Palermo|Genova|Bologna|Firenze|"
                r"Bari|Catania|Venezia|Verona|Messina|Padova|Trieste|Brescia|"
                r"Parma|Modena|Reggio\s+Calabria|Reggio\s+Emilia|Perugia|"
                r"Livorno|Ravenna|Cagliari|Foggia|Rimini|Salerno|Ferrara)\b",
                re.IGNORECASE,
            ),
            # Macro areas
            "area": re.compile(r"\b(?:del\s+|regioni\s+del\s+)?(Nord|Centro|Sud)(?:\s+Italia)?\b", re.IGNORECASE),
        }

    def _load_canonicalization_rules(self):
        """Load rules for canonicalizing extracted facts."""
        # Number word to digit mappings for Italian
        self.italian_numbers = {
            "zero": 0,
            "un": 1,
            "uno": 1,
            "due": 2,
            "tre": 3,
            "quattro": 4,
            "cinque": 5,
            "sei": 6,
            "sette": 7,
            "otto": 8,
            "nove": 9,
            "dieci": 10,
            "venti": 20,
            "trenta": 30,
            "quaranta": 40,
            "cinquanta": 50,
            "sessanta": 60,
            "settanta": 70,
            "ottanta": 80,
            "novanta": 90,
            "cento": 100,
            "mille": 1000,
            "duemila": 2000,
            "tremila": 3000,
            "quattromila": 4000,
            "cinquemila": 5000,
            "seimila": 6000,
            "settemila": 7000,
            "ottomila": 8000,
            "novemila": 9000,
            "diecimila": 10000,
            "ventimila": 20000,
            "trentamila": 30000,
            "quarantamila": 40000,
            "cinquantamila": 50000,
            "centomila": 100000,
            "cinquecento": 500,
            "millecento": 1100,
            "milleduecento": 1200,
            "milletrecento": 1300,
            "millequattrocento": 1400,
            "millecinquecento": 1500,
        }

        # Italian month names to numbers
        self.italian_months = {
            "gennaio": 1,
            "febbraio": 2,
            "marzo": 3,
            "aprile": 4,
            "maggio": 5,
            "giugno": 6,
            "luglio": 7,
            "agosto": 8,
            "settembre": 9,
            "ottobre": 10,
            "novembre": 11,
            "dicembre": 12,
        }

        # Company type canonicalization
        self.company_canonicalization = {
            "s.r.l.": "SRL",
            "srl": "SRL",
            "società per azioni": "SPA",
            "spa": "SPA",
            "s.p.a.": "SPA",
            "società in nome collettivo": "SNC",
            "snc": "SNC",
            "s.n.c.": "SNC",
            "ditta individuale": "DITTA_INDIVIDUALE",
        }

        # Document type canonicalization
        self.document_canonicalization = {
            "f24": "F24",
            "modello 730": "730",
            "730": "730",
            "fattura elettronica": "FATTURA_ELETTRONICA",
            "dichiarazione dei redditi": "DICHIARAZIONE_REDDITI",
            "dichiarazione redditi": "DICHIARAZIONE_REDDITI",
            "unico": "UNICO",
            "cud": "CUD",
        }

    def extract(self, query: str) -> AtomicFacts:
        """Extract atomic facts from an Italian professional query.

        Args:
            query: The user query to process

        Returns:
            AtomicFacts object containing all extracted information
        """
        start_time = time.time()

        if not query or not query.strip():
            return AtomicFacts(original_query=query, extraction_time_ms=0.0)

        query = query.strip()
        facts = AtomicFacts(original_query=query)

        try:
            # Extract different types of facts
            facts.monetary_amounts = self._extract_monetary_amounts(query)
            facts.dates = self._extract_dates(query)
            facts.legal_entities = self._extract_legal_entities(query)
            facts.professional_categories = self._extract_professional_categories(query)
            facts.geographic_info = self._extract_geographic_info(query)

        except Exception as e:
            logger.error(f"Error during atomic facts extraction: {e}", exc_info=True)

        # Calculate extraction time
        end_time = time.time()
        facts.extraction_time_ms = (end_time - start_time) * 1000

        if facts.extraction_time_ms > 50:
            logger.warning(f"Atomic facts extraction took {facts.extraction_time_ms:.2f}ms (target: <50ms)")

        logger.debug(f"Extracted {facts.fact_count()} facts from query: {facts.get_summary()}")

        return facts

    def _extract_monetary_amounts(self, query: str) -> list[MonetaryAmount]:
        """Extract monetary amounts and percentages from the query."""
        amounts = []

        # First, handle euro-centesimi combinations to avoid double parsing
        for match in self.monetary_patterns["euro_centesimi"].finditer(query):
            euros = int(match.group(1))
            centesimi = int(match.group(2))
            total_amount = euros + (centesimi / 100.0)
            amounts.append(
                MonetaryAmount(
                    amount=total_amount,
                    currency="EUR",
                    confidence=0.95,
                    original_text=match.group(0),
                    span=ExtractionSpan(match.start(), match.end()),
                )
            )

        # Track spans to avoid overlapping extractions
        used_spans = {(amt.span.start, amt.span.end) for amt in amounts if amt.span}

        # Extract euro symbol amounts (€35.000)
        for match in self.monetary_patterns["euro_symbol"].finditer(query):
            # Skip if this span overlaps with already extracted amounts
            if any(match.start() < end and match.end() > start for start, end in used_spans):
                continue

            amount_text = match.group(1)
            try:
                amount = self._canonicalize_number(amount_text)
                amounts.append(
                    MonetaryAmount(
                        amount=amount,
                        currency="EUR",
                        confidence=0.9,
                        original_text=match.group(0),
                        span=ExtractionSpan(match.start(), match.end()),
                    )
                )
                used_spans.add((match.start(), match.end()))
            except ValueError:
                continue

        # Extract euro word amounts (35000 euro)
        for match in self.monetary_patterns["euro_word"].finditer(query):
            # Skip if this span overlaps with already extracted amounts
            if any(match.start() < end and match.end() > start for start, end in used_spans):
                continue

            amount_text = match.group(1)
            try:
                amount = self._canonicalize_number(amount_text)
                amounts.append(
                    MonetaryAmount(
                        amount=amount,
                        currency="EUR",
                        confidence=0.9,
                        original_text=match.group(0),
                        span=ExtractionSpan(match.start(), match.end()),
                    )
                )
                used_spans.add((match.start(), match.end()))
            except ValueError:
                continue

        # Extract numeric percentages
        for match in self.monetary_patterns["percentage"].finditer(query):
            # Skip if this span overlaps with already extracted amounts
            if any(match.start() < end and match.end() > start for start, end in used_spans):
                continue

            percentage_text = match.group(1)
            try:
                percentage = self._canonicalize_number(percentage_text)
                amounts.append(
                    MonetaryAmount(
                        amount=percentage,
                        currency="%",
                        is_percentage=True,
                        confidence=0.85,
                        original_text=match.group(0),
                        span=ExtractionSpan(match.start(), match.end()),
                    )
                )
                used_spans.add((match.start(), match.end()))
            except ValueError:
                continue

        # Extract written percentages
        for match in self.monetary_patterns["percentage_written"].finditer(query):
            # Skip if this span overlaps with already extracted amounts
            if any(match.start() < end and match.end() > start for start, end in used_spans):
                continue

            written_percentage = match.group(1).lower().strip()
            percentage = self._parse_italian_compound_number(written_percentage)
            if percentage is not None:
                amounts.append(
                    MonetaryAmount(
                        amount=float(percentage),
                        currency="%",
                        is_percentage=True,
                        confidence=0.8,
                        original_text=match.group(0),
                        span=ExtractionSpan(match.start(), match.end()),
                    )
                )
                used_spans.add((match.start(), match.end()))

        # Extract written amounts
        for match in self.monetary_patterns["euro_written"].finditer(query):
            # Skip if this span overlaps with already extracted amounts
            if any(match.start() < end and match.end() > start for start, end in used_spans):
                continue

            written_amount = match.group(1).lower().strip()
            amount = self._parse_italian_compound_number(written_amount)
            if amount is not None:
                amounts.append(
                    MonetaryAmount(
                        amount=float(amount),
                        currency="EUR",
                        confidence=0.8,
                        original_text=match.group(0),
                        span=ExtractionSpan(match.start(), match.end()),
                    )
                )
                used_spans.add((match.start(), match.end()))

        return amounts

    def _extract_dates(self, query: str) -> list[DateFact]:
        """Extract dates, durations, and time-related facts from the query."""
        dates = []
        used_spans = set()

        # Extract date ranges first (most specific)
        for match in self.date_patterns["date_range"].finditer(query):
            start_day, start_month, end_day, end_month, year = match.groups()
            try:
                start_month_num = self.italian_months.get(start_month.lower())
                end_month_num = self.italian_months.get(end_month.lower())
                if start_month_num and end_month_num:
                    start_date = f"{int(year):04d}-{start_month_num:02d}-{int(start_day):02d}"
                    end_date = f"{int(year):04d}-{end_month_num:02d}-{int(end_day):02d}"

                    dates.append(
                        DateFact(
                            date_type="specific",
                            iso_date=start_date,
                            original_text=match.group(0),
                            confidence=0.9,
                            span=ExtractionSpan(match.start(), match.end()),
                        )
                    )
                    dates.append(
                        DateFact(
                            date_type="specific",
                            iso_date=end_date,
                            original_text=match.group(0),
                            confidence=0.9,
                            span=ExtractionSpan(match.start(), match.end()),
                        )
                    )
                    used_spans.add((match.start(), match.end()))
            except (ValueError, TypeError):
                continue

        # Extract numeric dates (dd/mm/yyyy)
        for match in self.date_patterns["date_dmy"].finditer(query):
            if any(match.start() < end and match.end() > start for start, end in used_spans):
                continue

            day, month, year = match.groups()
            try:
                iso_date = self._canonicalize_date(f"{day}/{month}/{year}")
                dates.append(
                    DateFact(
                        date_type="specific",
                        iso_date=iso_date,
                        original_text=match.group(0),
                        confidence=0.9,
                        span=ExtractionSpan(match.start(), match.end()),
                    )
                )
                used_spans.add((match.start(), match.end()))
            except ValueError:
                continue

        # Extract Italian dates with year (16 marzo 2024)
        for match in self.date_patterns["date_italian_full"].finditer(query):
            if any(match.start() < end and match.end() > start for start, end in used_spans):
                continue

            day, month_name, year = match.groups()
            try:
                month_num = self.italian_months.get(month_name.lower())
                if month_num:
                    iso_date = f"{int(year):04d}-{month_num:02d}-{int(day):02d}"
                    dates.append(
                        DateFact(
                            date_type="specific",
                            iso_date=iso_date,
                            original_text=match.group(0),
                            confidence=0.85,
                            span=ExtractionSpan(match.start(), match.end()),
                        )
                    )
                    used_spans.add((match.start(), match.end()))
            except (ValueError, TypeError):
                continue

        # Extract Italian dates without year (15 febbraio) - assumes current year
        for match in self.date_patterns["date_italian_no_year"].finditer(query):
            if any(match.start() < end and match.end() > start for start, end in used_spans):
                continue

            day, month_name = match.groups()
            try:
                current_year = datetime.now().year
                month_num = self.italian_months.get(month_name.lower())
                if month_num:
                    iso_date = f"{current_year:04d}-{month_num:02d}-{int(day):02d}"
                    dates.append(
                        DateFact(
                            date_type="specific",
                            iso_date=iso_date,
                            original_text=match.group(0),
                            confidence=0.8,
                            span=ExtractionSpan(match.start(), match.end()),
                        )
                    )
                    used_spans.add((match.start(), match.end()))
            except (ValueError, TypeError):
                continue

        # Extract tax years
        for match in self.date_patterns["tax_year"].finditer(query):
            year_groups = match.groups()
            year = next((y for y in year_groups if y), None)
            if year:
                dates.append(
                    DateFact(
                        date_type="tax_year",
                        tax_year=int(year),
                        original_text=match.group(0),
                        confidence=0.9,
                        span=ExtractionSpan(match.start(), match.end()),
                    )
                )

        # Extract durations
        for match in self.date_patterns["duration"].finditer(query):
            value, unit = match.groups()
            canonical_unit = self._canonicalize_duration_unit(unit)
            dates.append(
                DateFact(
                    date_type="duration",
                    duration_text=f"{value} {canonical_unit}",
                    duration_value=int(value),
                    duration_unit=canonical_unit,
                    original_text=match.group(0),
                    confidence=0.85,
                    span=ExtractionSpan(match.start(), match.end()),
                )
            )

        # Extract relative dates
        for match in self.date_patterns["relative_date"].finditer(query):
            relative_expr = self._canonicalize_relative_date(match.group(0))
            dates.append(
                DateFact(
                    date_type="relative",
                    relative_expression=relative_expr,
                    original_text=match.group(0),
                    confidence=0.7,
                    span=ExtractionSpan(match.start(), match.end()),
                )
            )

        return dates

    def _extract_legal_entities(self, query: str) -> list[LegalEntity]:
        """Extract legal entities, tax codes, and document types."""
        entities = []

        # Extract Codice Fiscale
        for match in self.legal_patterns["codice_fiscale"].finditer(query):
            entities.append(
                LegalEntity(
                    entity_type="codice_fiscale",
                    identifier=match.group(1),
                    canonical_form=match.group(1).upper(),
                    original_text=match.group(0),
                    confidence=0.95,
                    span=ExtractionSpan(match.start(), match.end()),
                )
            )

        # Extract Partita IVA
        for match in self.legal_patterns["partita_iva"].finditer(query):
            entities.append(
                LegalEntity(
                    entity_type="partita_iva",
                    identifier=match.group(1),
                    canonical_form=match.group(1).upper(),
                    original_text=match.group(0),
                    confidence=0.95,
                    span=ExtractionSpan(match.start(), match.end()),
                )
            )

        # Extract company types
        for match in self.legal_patterns["company_type"].finditer(query):
            company_type = match.group(1).lower()
            canonical = self.company_canonicalization.get(company_type, company_type.upper())
            entities.append(
                LegalEntity(
                    entity_type="company_type",
                    canonical_form=canonical,
                    original_text=match.group(0),
                    confidence=0.85,
                    span=ExtractionSpan(match.start(), match.end()),
                )
            )

        # Extract document types
        for match in self.legal_patterns["document_type"].finditer(query):
            doc_type = match.group(1).lower()
            canonical = self.document_canonicalization.get(doc_type, doc_type.upper())
            entities.append(
                LegalEntity(
                    entity_type="document_type",
                    canonical_form=canonical,
                    original_text=match.group(0),
                    confidence=0.8,
                    span=ExtractionSpan(match.start(), match.end()),
                )
            )

        # Extract document references (risoluzione n. 56, circolare n. 123, etc.)
        for match in self.legal_patterns["document_reference"].finditer(query):
            doc_type = match.group(1).lower()
            doc_number = match.group(2)
            # Create canonical form: "risoluzione 56"
            canonical = f"{doc_type} {doc_number}"
            entities.append(
                LegalEntity(
                    entity_type="document_reference",
                    canonical_form=canonical,
                    original_text=match.group(0),
                    identifier=doc_number,
                    confidence=0.95,  # High confidence for numbered documents
                    span=ExtractionSpan(match.start(), match.end()),
                )
            )

        # Extract legal references
        for match in self.legal_patterns["legal_reference"].finditer(query):
            canonical = self._canonicalize_legal_reference(match.group(0))
            entities.append(
                LegalEntity(
                    entity_type="legal_reference",
                    canonical_form=canonical,
                    original_text=match.group(0),
                    confidence=0.85,
                    span=ExtractionSpan(match.start(), match.end()),
                )
            )

        return entities

    def _extract_professional_categories(self, query: str) -> list[ProfessionalCategory]:
        """Extract professional categories, job levels, and contract types."""
        categories = []

        # Extract CCNL sectors
        for match in self.professional_patterns["ccnl_sector"].finditer(query):
            sector = match.group(1).lower().replace(" ", "_")
            categories.append(
                ProfessionalCategory(
                    category_type="ccnl_sector",
                    sector=sector,
                    original_text=match.group(0),
                    confidence=0.85,
                    span=ExtractionSpan(match.start(), match.end()),
                )
            )

        # Extract job levels
        for match in self.professional_patterns["job_level"].finditer(query):
            level_text = match.group(1).lower()
            level = self._extract_job_level(level_text)
            categories.append(
                ProfessionalCategory(
                    category_type="job_level",
                    level=level,
                    original_text=match.group(0),
                    confidence=0.8,
                    span=ExtractionSpan(match.start(), match.end()),
                )
            )

        # Extract contract types
        for match in self.professional_patterns["contract_type"].finditer(query):
            contract = match.group(1).lower().replace(" ", "_")
            categories.append(
                ProfessionalCategory(
                    category_type="contract_type",
                    contract_type=contract,
                    original_text=match.group(0),
                    confidence=0.8,
                    span=ExtractionSpan(match.start(), match.end()),
                )
            )

        return categories

    def _extract_geographic_info(self, query: str) -> list[GeographicInfo]:
        """Extract geographic information like regions, cities, and areas."""
        geo_info = []

        # Extract regions
        for match in self.geographic_patterns["region"].finditer(query):
            region = match.group(1)
            geo_info.append(
                GeographicInfo(
                    geo_type="region",
                    region=region,
                    original_text=match.group(0),
                    confidence=0.9,
                    span=ExtractionSpan(match.start(), match.end()),
                )
            )

        # Extract cities
        for match in self.geographic_patterns["city"].finditer(query):
            city = match.group(1)
            geo_info.append(
                GeographicInfo(
                    geo_type="city",
                    city=city,
                    original_text=match.group(0),
                    confidence=0.85,
                    span=ExtractionSpan(match.start(), match.end()),
                )
            )

        # Extract macro areas
        for match in self.geographic_patterns["area"].finditer(query):
            area = match.group(1)
            geo_info.append(
                GeographicInfo(
                    geo_type="area",
                    area=area,
                    original_text=match.group(0),
                    confidence=0.8,
                    span=ExtractionSpan(match.start(), match.end()),
                )
            )

        return geo_info

    # === CANONICALIZATION HELPER METHODS ===

    def _parse_italian_compound_number(self, written_text: str) -> float | None:
        """Parse compound Italian numbers like 'ventimila cinquecento'."""
        words = written_text.strip().split()
        if not words:
            return None

        # Single word numbers
        if len(words) == 1:
            return self.italian_numbers.get(words[0].lower())

        # Compound numbers
        total = 0
        for word in words:
            word = word.lower()
            if word in self.italian_numbers:
                total += self.italian_numbers[word]
            else:
                # Unknown word, return None
                return None

        return total

    def _canonicalize_number(self, number_text: str) -> float:
        """Convert Italian number format to decimal."""
        # Handle Italian decimal format (1.000,50)
        if "," in number_text and "." in number_text:
            # Format: 1.000,50 -> 1000.50
            parts = number_text.split(",")
            if len(parts) == 2:
                integer_part = parts[0].replace(".", "")
                decimal_part = parts[1]
                return float(f"{integer_part}.{decimal_part}")

        # Handle comma as decimal separator (1,5 -> 1.5)
        elif "," in number_text and "." not in number_text:
            return float(number_text.replace(",", "."))

        # Handle dot as thousands separator (1.000 -> 1000)
        elif "." in number_text and not number_text.endswith("."):
            # Check if it's thousands separator or decimal
            parts = number_text.split(".")
            if len(parts[-1]) == 3 and len(parts) > 1:
                # Thousands separator
                return float(number_text.replace(".", ""))
            else:
                # Decimal separator
                return float(number_text)

        # Standard number
        return float(number_text)

    def _canonicalize_date(self, date_text: str) -> str:
        """Convert Italian date format to ISO format (YYYY-MM-DD)."""
        # Handle dd/mm/yyyy or dd-mm-yyyy format
        if "/" in date_text or "-" in date_text:
            separator = "/" if "/" in date_text else "-"
            parts = date_text.split(separator)

            if len(parts) == 3:
                day, month, year = parts

                # Convert month name to number if necessary
                if month.lower() in self.italian_months:
                    month = str(self.italian_months[month.lower()])

                # Ensure proper formatting
                day = int(day)
                month = int(month)
                year = int(year)

                return f"{year:04d}-{month:02d}-{day:02d}"

        raise ValueError(f"Unable to parse date: {date_text}")

    def _canonicalize_entity(self, entity_text: str) -> str:
        """Canonicalize legal entity text."""
        entity_lower = entity_text.lower().strip()

        # Try company canonicalization
        if entity_lower in self.company_canonicalization:
            return self.company_canonicalization[entity_lower]

        # Try document canonicalization
        if entity_lower in self.document_canonicalization:
            return self.document_canonicalization[entity_lower]

        # Default: uppercase
        return entity_text.upper()

    def _canonicalize_duration_unit(self, unit: str) -> str:
        """Canonicalize duration units to English plurals."""
        unit_map = {
            "giorno": "days",
            "giorni": "days",
            "mese": "months",
            "mesi": "months",
            "anno": "years",
            "anni": "years",
        }
        return unit_map.get(unit.lower(), unit.lower())

    def _canonicalize_relative_date(self, relative_text: str) -> str:
        """Canonicalize relative date expressions."""
        relative_map = {
            "anno scorso": "previous_year",
            "prossimo trimestre": "next_quarter",
            "settimana scorsa": "previous_week",
        }

        # Handle "fra X mesi/anni" pattern
        if "fra" in relative_text.lower():
            match = re.search(r"fra\s+(\w+)\s+(mesi|anni)", relative_text, re.IGNORECASE)
            if match:
                number_word, unit = match.groups()
                if number_word.lower() in self.italian_numbers:
                    number = self.italian_numbers[number_word.lower()]
                    return f"in_{number}_{unit}"

        return relative_map.get(relative_text.lower(), relative_text.lower())

    def _canonicalize_legal_reference(self, legal_text: str) -> str:
        """Canonicalize legal reference format."""
        # Handle "art. X c.p.c." format
        art_match = re.search(
            r"(?:art\.|articolo)\s*(\d+)(?:\s+comma\s+(\d+))?\s+(c\.p\.c\.?|del\s+codice\s+civile|c\.c\.?)",
            legal_text,
            re.IGNORECASE,
        )
        if art_match:
            article, comma, code = art_match.groups()
            code_canonical = "c.p.c." if "c.p.c" in code.lower() or "codice civile" not in code.lower() else "c.c."

            if comma:
                return f"art. {article} comma {comma} {code_canonical}"
            else:
                return f"art. {article} {code_canonical}"

        # Handle "DPR/L. XXX/YY" format
        decree_match = re.search(r"(DPR|L\.|Legge)\s*(\d+\/\d{2,4})", legal_text, re.IGNORECASE)
        if decree_match:
            decree_type, number = decree_match.groups()
            decree_canonical = "DPR" if "DPR" in decree_type.upper() else "L."
            return f"{decree_canonical} {number}"

        return legal_text

    def _extract_job_level(self, level_text: str) -> str:
        """Extract and canonicalize job level."""
        # Extract number from level text
        number_match = re.search(r"(\d+)", level_text)
        if number_match:
            return number_match.group(1)

        # Handle special level names
        level_map = {
            "quadro": "quadro",
            "dirigente": "dirigente",
            "apprendista": "apprendista",
            "operaio": "operaio",
            "impiegato": "impiegato",
        }

        for key, value in level_map.items():
            if key in level_text.lower():
                return value

        return level_text

    # =========================================================================
    # DEV-154: Parameter Coverage Calculation Methods
    # =========================================================================

    def _parse_italian_number(self, text: str) -> float | None:
        """Parse Italian number format to float.

        Handles both Italian (1.000,50) and standard (1000.50) formats.

        Args:
            text: Number string to parse

        Returns:
            Float value or None if parsing fails
        """
        if not text or not text.strip():
            return None

        text = text.strip()

        try:
            return self._canonicalize_number(text)
        except (ValueError, AttributeError):
            return None

    def calculate_coverage(
        self,
        intent: str,
        extracted: list[ExtractedParameter],
    ) -> float:
        """Calculate parameter coverage for an intent.

        Coverage is the ratio of extracted required parameters to total required
        parameters. Parameters with confidence < 0.7 are not counted.

        Args:
            intent: The intent to calculate coverage for
            extracted: List of extracted parameters

        Returns:
            Coverage ratio (0.0 to 1.0), 0.0 for unknown intents
        """
        if intent not in INTENT_SCHEMAS:
            logger.warning(f"Unknown intent for coverage calculation: {intent}")
            return 0.0

        schema = INTENT_SCHEMAS[intent]
        required_params = set(schema["required"])

        if not required_params:
            return 1.0  # No required params means full coverage

        # Build map of param name to highest confidence value
        confidence_threshold = 0.7
        param_confidences: dict[str, float] = {}

        for param in extracted:
            if param.confidence >= confidence_threshold:
                current = param_confidences.get(param.name, 0.0)
                param_confidences[param.name] = max(current, param.confidence)

        # Count how many required params are covered
        covered_count = sum(1 for p in required_params if p in param_confidences)

        return covered_count / len(required_params)

    def get_missing_required(
        self,
        intent: str,
        extracted: list[ExtractedParameter],
    ) -> list[str]:
        """Get list of missing required parameters for an intent.

        Parameters with confidence < 0.7 are considered missing.

        Args:
            intent: The intent to check
            extracted: List of extracted parameters

        Returns:
            List of missing required parameter names
        """
        if intent not in INTENT_SCHEMAS:
            return []

        schema = INTENT_SCHEMAS[intent]
        required_params = set(schema["required"])

        # Get params that meet confidence threshold
        confidence_threshold = 0.7
        covered_params: set[str] = set()

        for param in extracted:
            if param.confidence >= confidence_threshold:
                covered_params.add(param.name)

        # Return missing required params
        return [p for p in required_params if p not in covered_params]

    def extract_with_coverage(
        self,
        query: str,
        intent: str | None = None,
    ) -> ParameterExtractionResult:
        """Extract parameters from query and calculate coverage.

        This method extracts atomic facts from the query, maps them to
        intent parameters, and calculates coverage against the intent schema.

        Args:
            query: User query to extract from
            intent: Optional intent to calculate coverage for

        Returns:
            ParameterExtractionResult with extracted params, coverage, and can_proceed
        """
        # Default result for unknown/missing intent
        if not intent:
            intent = "unknown"

        extracted_params: list[ExtractedParameter] = []

        try:
            # Extract atomic facts
            facts = self.extract(query)

            # Map extracted facts to intent parameters
            extracted_params = self._map_facts_to_params(facts, intent, query)

        except Exception as e:
            logger.error(
                f"Error during parameter extraction: {e}",
                extra={"query": query, "intent": intent},
                exc_info=True,
            )
            # Smart fallback - allow proceeding on extraction failure
            return ParameterExtractionResult(
                intent=intent,
                extracted=[],
                missing_required=[],
                coverage=0.0,
                can_proceed=True,
            )

        # Calculate coverage
        coverage = self.calculate_coverage(intent, extracted_params)

        # Get missing required params
        missing_required = self.get_missing_required(intent, extracted_params)

        # Determine if can proceed (coverage >= 0.8 for smart fallback)
        can_proceed = coverage >= 0.8

        logger.debug(
            "Parameter extraction complete",
            extra={
                "intent": intent,
                "coverage": coverage,
                "can_proceed": can_proceed,
                "extracted_count": len(extracted_params),
                "missing_count": len(missing_required),
            },
        )

        return ParameterExtractionResult(
            intent=intent,
            extracted=extracted_params,
            missing_required=missing_required,
            coverage=coverage,
            can_proceed=can_proceed,
        )

    def _map_facts_to_params(
        self,
        facts: "AtomicFacts",
        intent: str,
        query: str,
    ) -> list[ExtractedParameter]:
        """Map extracted atomic facts to intent parameters.

        Args:
            facts: Extracted atomic facts
            intent: The intent to map parameters for
            query: Original query for context

        Returns:
            List of ExtractedParameter objects
        """
        params: list[ExtractedParameter] = []

        # Extract monetary amounts as 'importo', 'reddito', etc.
        if facts.monetary_amounts:
            # Get highest confidence monetary amount
            best_amount = max(facts.monetary_amounts, key=lambda x: x.confidence)

            if not best_amount.is_percentage:
                # Map to intent-specific parameter name
                if intent == "calcolo_irpef":
                    param_name = "reddito"
                elif intent in ("calcolo_iva", "calcolo_contributi_inps"):
                    param_name = "importo"
                elif intent == "calcolo_netto":
                    param_name = "importo_lordo"
                elif intent == "calcolo_tfr":
                    param_name = "retribuzione_annua"
                else:
                    param_name = "importo"

                params.append(
                    ExtractedParameter(
                        name=param_name,
                        value=str(best_amount.amount),
                        confidence=best_amount.confidence,
                        source="query",
                    )
                )

        # Extract contributor type from query text
        contributor_type = self._extract_contributor_type(query)
        if contributor_type:
            params.append(
                ExtractedParameter(
                    name="tipo_contribuente",
                    value=contributor_type,
                    confidence=0.9,
                    source="query",
                )
            )

        # Extract tax year from dates
        for date_fact in facts.dates:
            if date_fact.date_type == "tax_year" and date_fact.tax_year:
                params.append(
                    ExtractedParameter(
                        name="anno_fiscale",
                        value=str(date_fact.tax_year),
                        confidence=date_fact.confidence,
                        source="query",
                    )
                )
                break

        # Extract regions from geographic info
        for geo in facts.geographic_info:
            if geo.region:
                params.append(
                    ExtractedParameter(
                        name="regione",
                        value=geo.region,
                        confidence=geo.confidence,
                        source="query",
                    )
                )
                break

        return params

    def _extract_contributor_type(self, query: str) -> str | None:
        """Extract contributor type from query text.

        Args:
            query: User query

        Returns:
            Contributor type string or None
        """
        query_lower = query.lower()

        # Define contributor type patterns
        contributor_patterns = {
            "dipendente": [
                r"\blavoratore\s+dipendente\b",
                r"\bdipendente\b",
                r"\blavoro\s+dipendente\b",
            ],
            "autonomo": [
                r"\blavoratore\s+autonomo\b",
                r"\bautonomo\b",
                r"\bpartita\s+iva\b",
                r"\blibero\s+professionista\b",
                r"\bprofessionista\b",
            ],
            "pensionato": [
                r"\bpensionato\b",
                r"\bpensione\b",
            ],
            "imprenditore": [
                r"\bimprenditore\b",
                r"\bditta\s+individuale\b",
            ],
        }

        for contrib_type, patterns in contributor_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return contrib_type

        return None
