"""DEV-414: Calendar Sync Integration (Google/Outlook).

MVP: Generate downloadable .ics files for individual deadlines and bulk export.
Phase 2: Bidirectional sync via Google Calendar API / Microsoft Graph API.

Reference: PRD AC-006.2.
"""

from datetime import date, datetime, timedelta
from typing import Any
from uuid import uuid4

from app.core.logging import logger


def _format_date(d: date) -> str:
    """Format date as iCalendar date string (YYYYMMDD)."""
    return d.strftime("%Y%m%d")


def _format_datetime_utc(dt: datetime) -> str:
    """Format datetime as iCalendar UTC string."""
    return dt.strftime("%Y%m%dT%H%M%SZ")


class CalendarSyncService:
    """Service for calendar integration via .ics file generation."""

    def generate_ics(
        self,
        summary: str,
        due_date: date,
        description: str = "",
        alarm_days_before: int | None = None,
        timezone: str = "Europe/Rome",
    ) -> str:
        """Generate a single-event .ics file.

        Args:
            summary: Event title/summary.
            due_date: Due date of the deadline.
            description: Event description.
            alarm_days_before: Days before to trigger alarm (optional).
            timezone: Timezone for the event.

        Returns:
            iCalendar formatted string.

        Raises:
            ValueError: If summary is empty.
        """
        if not summary:
            raise ValueError("Il summary non può essere vuoto")

        uid = str(uuid4())
        now = _format_datetime_utc(datetime.utcnow())
        date_str = _format_date(due_date)

        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//PratikoAI//Scadenze//IT",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
        ]

        # Add timezone component
        if timezone:
            lines.extend(
                [
                    "BEGIN:VTIMEZONE",
                    f"TZID:{timezone}",
                    "END:VTIMEZONE",
                ]
            )

        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{now}",
                f"DTSTART;TZID={timezone}:{date_str}",
                f"DTEND;TZID={timezone}:{date_str}",
                f"SUMMARY:{self._escape_ics(summary)}",
            ]
        )

        if description:
            lines.append(f"DESCRIPTION:{self._escape_ics(description)}")

        # Add alarm if requested
        if alarm_days_before is not None and alarm_days_before > 0:
            lines.extend(
                [
                    "BEGIN:VALARM",
                    "ACTION:DISPLAY",
                    f"DESCRIPTION:Promemoria: {self._escape_ics(summary)}",
                    f"TRIGGER:-P{alarm_days_before}D",
                    "END:VALARM",
                ]
            )

        lines.extend(
            [
                "END:VEVENT",
                "END:VCALENDAR",
            ]
        )

        return "\r\n".join(lines)

    def generate_bulk_ics(
        self,
        deadlines: list[dict[str, Any]],
        timezone: str = "Europe/Rome",
    ) -> str:
        """Generate a multi-event .ics file.

        Args:
            deadlines: List of dicts with 'summary' and 'due_date' keys.
            timezone: Timezone for events.

        Returns:
            iCalendar formatted string with all events.
        """
        now = _format_datetime_utc(datetime.utcnow())

        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//PratikoAI//Scadenze//IT",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
        ]

        for deadline in deadlines:
            summary = deadline.get("summary", "Scadenza")
            due = deadline.get("due_date")
            description = deadline.get("description", "")
            uid = str(uuid4())

            if due is None:
                continue

            date_str = _format_date(due)
            lines.extend(
                [
                    "BEGIN:VEVENT",
                    f"UID:{uid}",
                    f"DTSTAMP:{now}",
                    f"DTSTART;TZID={timezone}:{date_str}",
                    f"DTEND;TZID={timezone}:{date_str}",
                    f"SUMMARY:{self._escape_ics(summary)}",
                ]
            )

            if description:
                lines.append(f"DESCRIPTION:{self._escape_ics(description)}")

            lines.append("END:VEVENT")

        lines.append("END:VCALENDAR")

        logger.info(
            "bulk_ics_generated",
            event_count=len(deadlines),
        )

        return "\r\n".join(lines)

    @staticmethod
    def _escape_ics(text: str) -> str:
        """Escape special characters for iCalendar format."""
        return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


calendar_sync_service = CalendarSyncService()
