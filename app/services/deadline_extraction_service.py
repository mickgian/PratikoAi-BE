"""DEV-382: Deadline Extraction Service — Extract deadlines from KB items.

Processes knowledge base text content and extracts deadline metadata
using regex patterns for Italian fiscal/regulatory deadlines.
"""

import re
from dataclasses import dataclass
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.deadline import Deadline, DeadlineSource, DeadlineType
from app.services.deadline_service import deadline_service

# ---------------------------------------------------------------------------
# Italian month mapping
# ---------------------------------------------------------------------------

_ITALIAN_MONTHS: dict[str, int] = {
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

# ---------------------------------------------------------------------------
# Regex patterns for Italian date formats
# ---------------------------------------------------------------------------

# "entro il 16 marzo 2026" / "entro il 30 settembre 2026"
_PATTERN_ENTRO_IL = re.compile(
    r"entro\s+il\s+(\d{1,2})\s+(" + "|".join(_ITALIAN_MONTHS.keys()) + r")\s+(\d{4})",
    re.IGNORECASE,
)

# "scadenza DD/MM/YYYY" or standalone "il DD/MM/YYYY"
_PATTERN_SLASH_DATE = re.compile(
    r"(?:scadenza|il|del|entro\s+il)\s+(\d{1,2})/(\d{1,2})/(\d{4})",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Keyword-to-type mapping
# ---------------------------------------------------------------------------

_TYPE_KEYWORDS: list[tuple[DeadlineType, list[str]]] = [
    # CONTRIBUTIVO must be checked before FISCALE because "tribut" is
    # a substring of "contribut" and would otherwise cause false matches.
    (DeadlineType.CONTRIBUTIVO, ["inps", "contribut", "previdenzial"]),
    (DeadlineType.FISCALE, ["iva", "irpef", "ires", "irap", "imposta", "imposte", "tributar"]),
    (DeadlineType.SOCIETARIO, ["assemblea", "bilancio", "societar"]),
    # ADEMPIMENTO is the fallback — no keywords needed
]

# ---------------------------------------------------------------------------
# Recurrence mapping
# ---------------------------------------------------------------------------

_RECURRENCE_KEYWORDS: dict[str, str] = {
    "mensile": "MONTHLY",
    "trimestrale": "QUARTERLY",
    "semestrale": "SEMIANNUAL",
    "annuale": "YEARLY",
}


@dataclass
class ExtractedDeadline:
    """A deadline extracted from free-form Italian text."""

    title: str
    due_date: date
    deadline_type: DeadlineType
    source: DeadlineSource
    description: str | None = None
    recurrence_rule: str | None = None


class DeadlineExtractionService:
    """Extracts deadline metadata from Italian fiscal/regulatory text."""

    def extract_deadlines(self, text: str) -> list[ExtractedDeadline]:
        """Extract deadlines from free-form Italian text.

        Scans for Italian date patterns and determines deadline type
        and recurrence from surrounding keywords.

        Args:
            text: Free-form Italian text potentially containing deadline info.

        Returns:
            List of ExtractedDeadline dataclass instances.
        """
        if not text.strip():
            return []

        results: list[ExtractedDeadline] = []
        seen_dates: set[tuple[date, DeadlineType]] = set()

        # --- Pattern 1: "entro il DD MMMM YYYY" ---
        for match in _PATTERN_ENTRO_IL.finditer(text):
            day = int(match.group(1))
            month = _ITALIAN_MONTHS[match.group(2).lower()]
            year = int(match.group(3))
            due = date(year, month, day)

            # Get surrounding context (the sentence containing the match)
            context = self._get_sentence_context(text, match.start(), match.end())
            dtype = self._detect_type(context)
            recurrence = self._detect_recurrence(context)
            title = self._build_title(context, due)

            key = (due, dtype)
            if key not in seen_dates:
                seen_dates.add(key)
                results.append(
                    ExtractedDeadline(
                        title=title,
                        due_date=due,
                        deadline_type=dtype,
                        source=DeadlineSource.REGULATORY,
                        description=context.strip(),
                        recurrence_rule=recurrence,
                    )
                )

        # --- Pattern 2: "scadenza DD/MM/YYYY" or "il DD/MM/YYYY" ---
        for match in _PATTERN_SLASH_DATE.finditer(text):
            day = int(match.group(1))
            month = int(match.group(2))
            year = int(match.group(3))
            due = date(year, month, day)

            context = self._get_sentence_context(text, match.start(), match.end())
            dtype = self._detect_type(context)
            recurrence = self._detect_recurrence(context)
            title = self._build_title(context, due)

            key = (due, dtype)
            if key not in seen_dates:
                seen_dates.add(key)
                results.append(
                    ExtractedDeadline(
                        title=title,
                        due_date=due,
                        deadline_type=dtype,
                        source=DeadlineSource.REGULATORY,
                        description=context.strip(),
                        recurrence_rule=recurrence,
                    )
                )

        logger.info(
            "deadlines_extracted",
            count=len(results),
            text_length=len(text),
        )
        return results

    async def persist_extracted(
        self,
        db: AsyncSession,
        extracted: list[ExtractedDeadline],
    ) -> list[Deadline]:
        """Persist a list of extracted deadlines via DeadlineService.

        Args:
            db: Async database session.
            extracted: List of ExtractedDeadline dataclass instances.

        Returns:
            List of persisted Deadline ORM objects.
        """
        if not extracted:
            return []

        persisted: list[Deadline] = []
        for item in extracted:
            record = await deadline_service.create(
                db,
                title=item.title,
                deadline_type=item.deadline_type,
                source=item.source,
                due_date=item.due_date,
                description=item.description,
                recurrence_rule=item.recurrence_rule,
            )
            persisted.append(record)

        logger.info("deadlines_persisted", count=len(persisted))
        return persisted

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_sentence_context(text: str, start: int, end: int) -> str:
        """Extract the sentence surrounding a regex match.

        Looks for sentence boundaries (newline, period, dash list marker)
        to return the most relevant surrounding text.
        """
        # Walk backwards to find sentence start
        sent_start = start
        for i in range(start - 1, -1, -1):
            if text[i] in (".", "\n"):
                sent_start = i + 1
                break
        else:
            sent_start = 0

        # Walk forward to find sentence end
        sent_end = end
        for i in range(end, len(text)):
            if text[i] in (".", "\n"):
                sent_end = i + 1
                break
        else:
            sent_end = len(text)

        return text[sent_start:sent_end].strip(" -\n")

    @staticmethod
    def _detect_type(context: str) -> DeadlineType:
        """Detect deadline type from keywords in surrounding text."""
        lower = context.lower()
        for dtype, keywords in _TYPE_KEYWORDS:
            for kw in keywords:
                if kw in lower:
                    return dtype
        return DeadlineType.ADEMPIMENTO

    @staticmethod
    def _detect_recurrence(context: str) -> str | None:
        """Detect recurrence rule from keywords in surrounding text."""
        lower = context.lower()
        for keyword, rule in _RECURRENCE_KEYWORDS.items():
            if keyword in lower:
                return rule
        return None

    @staticmethod
    def _build_title(context: str, due: date) -> str:
        """Build a concise title from the sentence context.

        Truncates to a reasonable length and ensures readability.
        """
        # Clean up and truncate
        clean = context.strip(" .-\n")
        # Cap title length at 200 chars
        if len(clean) > 200:
            clean = clean[:197] + "..."
        return clean


deadline_extraction_service = DeadlineExtractionService()
