"""DEV-414: Tests for Calendar Sync Service.

Tests: single .ics generation, bulk .ics, valid iCalendar format, timezone handling.
"""

from datetime import date, datetime

import pytest

from app.services.calendar_sync_service import CalendarSyncService


@pytest.fixture
def svc():
    return CalendarSyncService()


class TestGenerateIcs:
    def test_single_deadline_ics(self, svc):
        ics = svc.generate_ics(
            summary="Scadenza F24",
            due_date=date(2026, 6, 16),
            description="Versamento imposte tramite F24",
        )
        assert "BEGIN:VCALENDAR" in ics
        assert "BEGIN:VEVENT" in ics
        assert "END:VEVENT" in ics
        assert "END:VCALENDAR" in ics
        assert "Scadenza F24" in ics
        assert "20260616" in ics

    def test_ics_with_alarm(self, svc):
        ics = svc.generate_ics(
            summary="IVA Trimestrale",
            due_date=date(2026, 3, 16),
            alarm_days_before=7,
        )
        assert "BEGIN:VALARM" in ics
        assert "TRIGGER" in ics

    def test_ics_prodid(self, svc):
        ics = svc.generate_ics(summary="Test", due_date=date(2026, 1, 1))
        assert "PRODID" in ics
        assert "PratikoAI" in ics

    def test_empty_summary_raises(self, svc):
        with pytest.raises(ValueError, match="summary"):
            svc.generate_ics(summary="", due_date=date(2026, 1, 1))


class TestBulkIcs:
    def test_bulk_export(self, svc):
        deadlines = [
            {"summary": "F24", "due_date": date(2026, 6, 16)},
            {"summary": "IVA", "due_date": date(2026, 3, 16)},
        ]
        ics = svc.generate_bulk_ics(deadlines)
        assert "BEGIN:VCALENDAR" in ics
        assert ics.count("BEGIN:VEVENT") == 2
        assert "F24" in ics
        assert "IVA" in ics

    def test_empty_list(self, svc):
        ics = svc.generate_bulk_ics([])
        assert "BEGIN:VCALENDAR" in ics
        assert "BEGIN:VEVENT" not in ics


class TestTimezone:
    def test_europe_rome_timezone(self, svc):
        ics = svc.generate_ics(
            summary="Test TZ",
            due_date=date(2026, 7, 15),
            timezone="Europe/Rome",
        )
        assert "Europe/Rome" in ics
