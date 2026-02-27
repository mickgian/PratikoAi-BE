"""DEV-382: Tests for DeadlineExtractionService — Extract deadlines from KB text.

Tests cover:
- Happy path: extract deadline from text with Italian date pattern
- Happy path: extract multiple deadlines from text
- Edge case: no deadlines found in text
- Deadline type detection (FISCALE for IVA/IRPEF, CONTRIBUTIVO for INPS, etc.)
- Recurrence detection (mensile, trimestrale, annuale)
- Persist extracted deadlines via DeadlineService
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.deadline import DeadlineSource, DeadlineType
from app.services.deadline_extraction_service import (
    DeadlineExtractionService,
    ExtractedDeadline,
)


@pytest.fixture
def extraction_service() -> DeadlineExtractionService:
    return DeadlineExtractionService()


@pytest.fixture
def mock_db() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    return session


class TestExtractDeadlinesSingleDate:
    """Test extraction of a single deadline from text."""

    def test_extract_single_deadline_entro_il(
        self,
        extraction_service: DeadlineExtractionService,
    ) -> None:
        """Happy path: extract deadline with 'entro il DD MMMM YYYY' pattern."""
        text = "Il versamento dell'IVA trimestrale deve essere effettuato entro il 16 marzo 2026."

        results = extraction_service.extract_deadlines(text)

        assert len(results) == 1
        assert results[0].due_date == date(2026, 3, 16)
        assert results[0].deadline_type == DeadlineType.FISCALE
        assert results[0].source == DeadlineSource.REGULATORY
        assert "IVA" in results[0].title

    def test_extract_single_deadline_scadenza_slash(
        self,
        extraction_service: DeadlineExtractionService,
    ) -> None:
        """Happy path: extract deadline with 'scadenza DD/MM/YYYY' pattern."""
        text = "La scadenza per il contributo INPS è il 16/02/2026."

        results = extraction_service.extract_deadlines(text)

        assert len(results) == 1
        assert results[0].due_date == date(2026, 2, 16)
        assert results[0].deadline_type == DeadlineType.CONTRIBUTIVO

    def test_extract_deadline_entro_il_with_accent(
        self,
        extraction_service: DeadlineExtractionService,
    ) -> None:
        """Handle accented month names correctly (e.g., no accent issues)."""
        text = "Versamento IRPEF entro il 16 giugno 2026."

        results = extraction_service.extract_deadlines(text)

        assert len(results) == 1
        assert results[0].due_date == date(2026, 6, 16)
        assert results[0].deadline_type == DeadlineType.FISCALE


class TestExtractDeadlinesMultiple:
    """Test extraction of multiple deadlines from text."""

    def test_extract_multiple_deadlines(
        self,
        extraction_service: DeadlineExtractionService,
    ) -> None:
        """Happy path: extract multiple deadlines from text with different dates."""
        text = (
            "Le scadenze del mese:\n"
            "- Versamento IVA trimestrale entro il 16 marzo 2026.\n"
            "- Versamento contributi INPS entro il 16 marzo 2026.\n"
            "- Dichiarazione annuale dei redditi entro il 30 settembre 2026."
        )

        results = extraction_service.extract_deadlines(text)

        assert len(results) >= 2
        due_dates = {r.due_date for r in results}
        assert date(2026, 3, 16) in due_dates
        assert date(2026, 9, 30) in due_dates


class TestExtractDeadlinesNoneFound:
    """Test edge case when no deadlines are found."""

    def test_no_deadlines_in_text(
        self,
        extraction_service: DeadlineExtractionService,
    ) -> None:
        """Edge case: text without any date patterns returns empty list."""
        text = "Informazioni generali sulla contabilità aziendale senza scadenze."

        results = extraction_service.extract_deadlines(text)

        assert results == []

    def test_empty_text(
        self,
        extraction_service: DeadlineExtractionService,
    ) -> None:
        """Edge case: empty text returns empty list."""
        results = extraction_service.extract_deadlines("")

        assert results == []


class TestDeadlineTypeDetection:
    """Test that deadline types are correctly detected from keywords."""

    def test_fiscale_iva_keyword(
        self,
        extraction_service: DeadlineExtractionService,
    ) -> None:
        """IVA keyword maps to FISCALE type."""
        text = "Versamento IVA entro il 16 aprile 2026."

        results = extraction_service.extract_deadlines(text)

        assert len(results) == 1
        assert results[0].deadline_type == DeadlineType.FISCALE

    def test_fiscale_irpef_keyword(
        self,
        extraction_service: DeadlineExtractionService,
    ) -> None:
        """IRPEF keyword maps to FISCALE type."""
        text = "Versamento acconto IRPEF entro il 30 novembre 2026."

        results = extraction_service.extract_deadlines(text)

        assert len(results) == 1
        assert results[0].deadline_type == DeadlineType.FISCALE

    def test_fiscale_imposta_keyword(
        self,
        extraction_service: DeadlineExtractionService,
    ) -> None:
        """imposta keyword maps to FISCALE type."""
        text = "Pagamento imposta di bollo entro il 30 aprile 2026."

        results = extraction_service.extract_deadlines(text)

        assert len(results) == 1
        assert results[0].deadline_type == DeadlineType.FISCALE

    def test_contributivo_inps_keyword(
        self,
        extraction_service: DeadlineExtractionService,
    ) -> None:
        """INPS keyword maps to CONTRIBUTIVO type."""
        text = "Versamento contributi INPS entro il 16 maggio 2026."

        results = extraction_service.extract_deadlines(text)

        assert len(results) == 1
        assert results[0].deadline_type == DeadlineType.CONTRIBUTIVO

    def test_contributivo_contributi_keyword(
        self,
        extraction_service: DeadlineExtractionService,
    ) -> None:
        """contributi keyword maps to CONTRIBUTIVO type."""
        text = "Scadenza contributi previdenziali entro il 16 maggio 2026."

        results = extraction_service.extract_deadlines(text)

        assert len(results) == 1
        assert results[0].deadline_type == DeadlineType.CONTRIBUTIVO

    def test_societario_keyword(
        self,
        extraction_service: DeadlineExtractionService,
    ) -> None:
        """assemblea/bilancio keyword maps to SOCIETARIO type."""
        text = "Approvazione bilancio entro il 30 aprile 2026."

        results = extraction_service.extract_deadlines(text)

        assert len(results) == 1
        assert results[0].deadline_type == DeadlineType.SOCIETARIO

    def test_adempimento_default(
        self,
        extraction_service: DeadlineExtractionService,
    ) -> None:
        """Unrecognized keyword defaults to ADEMPIMENTO type."""
        text = "Presentazione comunicazione obbligatoria entro il 28 febbraio 2026."

        results = extraction_service.extract_deadlines(text)

        assert len(results) == 1
        assert results[0].deadline_type == DeadlineType.ADEMPIMENTO


class TestRecurrenceDetection:
    """Test recurrence rule extraction from text."""

    def test_recurrence_mensile(
        self,
        extraction_service: DeadlineExtractionService,
    ) -> None:
        """'mensile' keyword maps to MONTHLY recurrence."""
        text = "Versamento IVA mensile entro il 16 aprile 2026."

        results = extraction_service.extract_deadlines(text)

        assert len(results) == 1
        assert results[0].recurrence_rule == "MONTHLY"

    def test_recurrence_trimestrale(
        self,
        extraction_service: DeadlineExtractionService,
    ) -> None:
        """'trimestrale' keyword maps to QUARTERLY recurrence."""
        text = "Versamento IVA trimestrale entro il 16 marzo 2026."

        results = extraction_service.extract_deadlines(text)

        assert len(results) == 1
        assert results[0].recurrence_rule == "QUARTERLY"

    def test_recurrence_annuale(
        self,
        extraction_service: DeadlineExtractionService,
    ) -> None:
        """'annuale' keyword maps to YEARLY recurrence."""
        text = "Dichiarazione annuale IVA entro il 30 aprile 2026."

        results = extraction_service.extract_deadlines(text)

        assert len(results) == 1
        assert results[0].recurrence_rule == "YEARLY"

    def test_recurrence_semestrale(
        self,
        extraction_service: DeadlineExtractionService,
    ) -> None:
        """'semestrale' keyword maps to SEMIANNUAL recurrence."""
        text = "Versamento semestrale contributi INPS entro il 16 giugno 2026."

        results = extraction_service.extract_deadlines(text)

        assert len(results) == 1
        assert results[0].recurrence_rule == "SEMIANNUAL"

    def test_no_recurrence(
        self,
        extraction_service: DeadlineExtractionService,
    ) -> None:
        """No recurrence keyword means recurrence_rule is None."""
        text = "Presentazione comunicazione entro il 28 febbraio 2026."

        results = extraction_service.extract_deadlines(text)

        assert len(results) == 1
        assert results[0].recurrence_rule is None


class TestPersistExtracted:
    """Test persisting extracted deadlines to the database."""

    @pytest.mark.asyncio
    async def test_persist_extracted_creates_records(
        self,
        extraction_service: DeadlineExtractionService,
        mock_db: AsyncMock,
    ) -> None:
        """Happy path: persist extracted deadlines creates Deadline records."""
        extracted = [
            ExtractedDeadline(
                title="Versamento IVA trimestrale",
                due_date=date(2026, 3, 16),
                deadline_type=DeadlineType.FISCALE,
                source=DeadlineSource.REGULATORY,
                description="Versamento IVA trimestrale",
                recurrence_rule="QUARTERLY",
            ),
            ExtractedDeadline(
                title="Contributi INPS",
                due_date=date(2026, 3, 16),
                deadline_type=DeadlineType.CONTRIBUTIVO,
                source=DeadlineSource.REGULATORY,
            ),
        ]

        with patch("app.services.deadline_extraction_service.deadline_service") as mock_deadline_svc:
            mock_deadline_svc.create = AsyncMock(side_effect=lambda db, **kw: MagicMock(id="fake-id", **kw))

            results = await extraction_service.persist_extracted(mock_db, extracted)

        assert len(results) == 2
        assert mock_deadline_svc.create.await_count == 2

    @pytest.mark.asyncio
    async def test_persist_empty_list(
        self,
        extraction_service: DeadlineExtractionService,
        mock_db: AsyncMock,
    ) -> None:
        """Edge case: persisting empty list returns empty list."""
        results = await extraction_service.persist_extracted(mock_db, [])

        assert results == []
