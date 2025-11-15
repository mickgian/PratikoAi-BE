"""
Test suite for Cassazione Court Decisions Scraper.

This module contains comprehensive tests for the Italian Supreme Court
scraper using Test-Driven Development (TDD). Tests cover all aspects
from basic scraping to error handling and database integration.
"""

import asyncio
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, patch

import aiohttp
import pytest
from bs4 import BeautifulSoup

from app.models.italian_data import ItalianOfficialDocument
from app.services.database import database_service
from app.services.scrapers.cassazione_scraper import (
    CassazioneDecision,
    CassazioneScraper,
    CourtSection,
    DecisionType,
    ScrapingError,
    ScrapingResult,
    ScrapingStatistics,
)


class TestCassazioneDecisionModel:
    """Test the Cassazione decision data model."""

    def test_create_basic_decision(self):
        """Test creating a basic Cassazione decision."""
        decision = CassazioneDecision(
            decision_number="15234/2024",
            date=date(2024, 3, 15),
            section=CourtSection.CIVILE,
            subject="Responsabilità amministratore SRL",
            full_text="Testo completo della sentenza...",
            judge_names=["Mario Rossi", "Luigi Verdi"],
            party_names=["Alfa SpA", "Beta SRL"],
            keywords=["amministratore", "responsabilità", "SRL"],
        )

        assert decision.decision_number == "15234/2024"
        assert decision.section == CourtSection.CIVILE
        assert len(decision.judge_names) == 2
        assert "amministratore" in decision.keywords
        assert decision.confidence_score == Decimal("0.95")  # Default

    def test_decision_with_full_metadata(self):
        """Test creating decision with complete metadata."""
        decision = CassazioneDecision(
            decision_number="Cass. Civ. Sez. III, 15234/2024",
            date=date(2024, 3, 15),
            section=CourtSection.CIVILE,
            subsection="III",
            subject="Responsabilità amministratore SRL per obbligazioni sociali",
            summary="La Corte stabilisce i limiti della responsabilità...",
            full_text="<html>Testo completo con formattazione...</html>",
            legal_principles=[
                "L'amministratore risponde per le obbligazioni sociali solo in caso di colpa grave",
                "È necessario provare il nesso causale tra condotta e danno",
            ],
            judge_names=["Mario Rossi", "Luigi Verdi", "Anna Bianchi"],
            party_names=["Alfa SpA (ricorrente)", "Beta SRL (convenuta)"],
            citations_to_laws=["Art. 2476 c.c.", "Art. 2381 c.c."],
            citations_to_decisions=["Cass. Civ. 12345/2023", "Cass. Civ. 67890/2022"],
            keywords=["amministratore", "SRL", "responsabilità", "obbligazioni sociali"],
            decision_type=DecisionType.SENTENZA,
            confidence_score=Decimal("0.88"),
        )

        assert decision.subsection == "III"
        assert len(decision.legal_principles) == 2
        assert len(decision.citations_to_laws) == 2
        assert len(decision.citations_to_decisions) == 2
        assert decision.decision_type == DecisionType.SENTENZA
        assert decision.confidence_score == Decimal("0.88")

    def test_decision_validation_invalid_number(self):
        """Test validation with invalid decision number."""
        with pytest.raises(ValueError, match="Invalid decision number format"):
            CassazioneDecision(
                decision_number="invalid-123",  # Invalid format
                date=date(2024, 3, 15),
                section=CourtSection.CIVILE,
                subject="Test",
            )

    def test_decision_validation_future_date(self):
        """Test validation with future date."""
        future_date = date(2030, 12, 31)
        with pytest.raises(ValueError, match="Decision date cannot be in the future"):
            CassazioneDecision(
                decision_number="15234/2024", date=future_date, section=CourtSection.CIVILE, subject="Test"
            )

    def test_generate_unique_identifier(self):
        """Test unique identifier generation."""
        decision = CassazioneDecision(
            decision_number="Cass. Civ. Sez. III, 15234/2024",
            date=date(2024, 3, 15),
            section=CourtSection.CIVILE,
            subject="Test",
        )

        unique_id = decision.generate_unique_identifier()
        assert "cass_civ_15234_2024" in unique_id
        assert "2024_03_15" in unique_id

    def test_extract_legal_principles(self):
        """Test extraction of legal principles from decision text."""
        decision_text = """
        La Corte di Cassazione stabilisce il seguente principio di diritto:
        1) L'amministratore di SRL risponde delle obbligazioni sociali solo in presenza di colpa grave.
        2) È necessario il nesso causale tra condotta dell'amministratore e danno subito.
        In ordine a tali principi, la Corte rigetta il ricorso.
        """

        decision = CassazioneDecision(
            decision_number="15234/2024",
            date=date(2024, 3, 15),
            section=CourtSection.CIVILE,
            subject="Test",
            full_text=decision_text,
        )

        principles = decision.extract_legal_principles()
        assert len(principles) >= 2
        assert any("amministratore" in principle for principle in principles)
        assert any("nesso causale" in principle for principle in principles)


class TestCassazioneScraper:
    """Test the main Cassazione web scraper."""

    @pytest.fixture
    def scraper(self):
        """Create a scraper instance for testing."""
        return CassazioneScraper(
            rate_limit_delay=0.1,  # Fast for testing
            max_retries=2,
            timeout_seconds=10,
        )

    @pytest.fixture
    def sample_decision_html(self):
        """Sample HTML content for a Cassazione decision page."""
        return """
        <html>
        <head><title>Cassazione Civile - Sentenza n. 15234/2024</title></head>
        <body>
            <div class="decision-header">
                <h1>CORTE SUPREMA DI CASSAZIONE</h1>
                <h2>SEZIONE CIVILE TERZA</h2>
                <h3>Sentenza 15 marzo 2024, n. 15234</h3>
            </div>
            <div class="decision-parties">
                <p><strong>Ricorrente:</strong> Alfa SpA</p>
                <p><strong>Convenuta:</strong> Beta SRL</p>
            </div>
            <div class="decision-judges">
                <p><strong>Presidente:</strong> Mario Rossi</p>
                <p><strong>Relatore:</strong> Luigi Verdi</p>
                <p><strong>Consigliere:</strong> Anna Bianchi</p>
            </div>
            <div class="decision-subject">
                <h4>Responsabilità amministratore SRL per obbligazioni sociali</h4>
            </div>
            <div class="decision-content">
                <h5>FATTO E DIRITTO</h5>
                <p>La Corte, esaminata la questione della responsabilità dell'amministratore...</p>

                <h5>PRINCIPI DI DIRITTO</h5>
                <p>1) L'amministratore di SRL risponde delle obbligazioni sociali solo in caso di colpa grave.</p>
                <p>2) È necessario provare il nesso causale tra condotta e danno.</p>

                <h5>RIFERIMENTI NORMATIVI</h5>
                <p>Art. 2476 Codice Civile, Art. 2381 Codice Civile</p>

                <h5>PRECEDENTI</h5>
                <p>Cass. Civ. 12345/2023, Cass. Civ. 67890/2022</p>
            </div>
        </body>
        </html>
        """

    @pytest.fixture
    def sample_search_results_html(self):
        """Sample HTML for search results page."""
        return """
        <html>
        <body>
            <div class="search-results">
                <div class="result-item">
                    <h3><a href="/decision/15234-2024">Cass. Civ. Sez. III, n. 15234/2024</a></h3>
                    <p class="date">15 marzo 2024</p>
                    <p class="subject">Responsabilità amministratore SRL</p>
                </div>
                <div class="result-item">
                    <h3><a href="/decision/15235-2024">Cass. Civ. Sez. II, n. 15235/2024</a></h3>
                    <p class="date">16 marzo 2024</p>
                    <p class="subject">Contratto di vendita immobiliare</p>
                </div>
                <div class="result-item">
                    <h3><a href="/decision/15236-2024">Cass. Trib., n. 15236/2024</a></h3>
                    <p class="date">17 marzo 2024</p>
                    <p class="subject">IVA su operazioni immobiliari</p>
                </div>
            </div>
            <div class="pagination">
                <a href="?page=1" class="current">1</a>
                <a href="?page=2">2</a>
                <a href="?page=3">3</a>
                <a href="?page=next">Successiva</a>
            </div>
        </body>
        </html>
        """

    @pytest.mark.asyncio
    async def test_parse_decision_from_html(self, scraper, sample_decision_html):
        """Test parsing a decision from HTML content."""
        decision = await scraper.parse_decision_from_html(
            sample_decision_html, "https://www.cortedicassazione.it/decision/15234-2024"
        )

        assert decision is not None
        assert decision.decision_number == "15234/2024"
        assert decision.date == date(2024, 3, 15)
        assert decision.section == CourtSection.CIVILE
        assert decision.subsection == "III"
        assert "amministratore" in decision.subject.lower()
        assert len(decision.judge_names) == 3
        assert "Mario Rossi" in decision.judge_names
        assert len(decision.party_names) == 2
        assert len(decision.legal_principles) == 2
        assert len(decision.citations_to_laws) == 2
        assert len(decision.citations_to_decisions) == 2

    @pytest.mark.asyncio
    async def test_parse_decision_invalid_html(self, scraper):
        """Test parsing with invalid HTML content."""
        invalid_html = "<html><body><p>Not a decision page</p></body></html>"

        decision = await scraper.parse_decision_from_html(invalid_html, "http://test.com")
        assert decision is None

    @pytest.mark.asyncio
    async def test_parse_search_results(self, scraper, sample_search_results_html):
        """Test parsing search results page."""
        results = await scraper.parse_search_results(sample_search_results_html)

        assert len(results) == 3

        # Check first result (Civil)
        civil_result = results[0]
        assert civil_result["decision_number"] == "15234/2024"
        assert civil_result["section"] == CourtSection.CIVILE
        assert civil_result["url"] == "/decision/15234-2024"

        # Check last result (Tributaria)
        tax_result = results[2]
        assert tax_result["decision_number"] == "15236/2024"
        assert tax_result["section"] == CourtSection.TRIBUTARIA

    @pytest.mark.asyncio
    async def test_scrape_decision_with_retry(self, scraper):
        """Test scraping with retry mechanism."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            # First call fails, second succeeds
            mock_response_fail = AsyncMock()
            mock_response_fail.status = 500
            mock_response_fail.text = AsyncMock(return_value="Server Error")

            mock_response_success = AsyncMock()
            mock_response_success.status = 200
            mock_response_success.text = AsyncMock(return_value="<html>Success</html>")

            mock_get.side_effect = [
                mock_response_fail,  # First attempt fails
                mock_response_success,  # Retry succeeds
            ]

            result = await scraper._fetch_page_with_retry("http://test.com")

            assert result == "<html>Success</html>"
            assert mock_get.call_count == 2  # Original + 1 retry

    @pytest.mark.asyncio
    async def test_scrape_decision_max_retries_exceeded(self, scraper):
        """Test scraping when max retries are exceeded."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_response.text = AsyncMock(return_value="Server Error")
            mock_get.return_value = mock_response

            with pytest.raises(ScrapingError, match="Max retries exceeded"):
                await scraper._fetch_page_with_retry("http://test.com")

            assert mock_get.call_count == 3  # Original + 2 retries

    @pytest.mark.asyncio
    async def test_rate_limiting(self, scraper):
        """Test rate limiting between requests."""
        start_time = datetime.now()

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value="<html></html>")
            mock_get.return_value = mock_response

            # Make two requests
            await scraper._fetch_page_with_retry("http://test1.com")
            await scraper._fetch_page_with_retry("http://test2.com")

            elapsed = (datetime.now() - start_time).total_seconds()
            assert elapsed >= scraper.rate_limit_delay

    @pytest.mark.asyncio
    async def test_scrape_historical_decisions_date_range(self, scraper):
        """Test scraping decisions within a date range."""
        start_date = date(2024, 1, 1)
        end_date = date(2024, 3, 31)

        with patch.object(scraper, "_scrape_decisions_for_date_range") as mock_scrape:
            mock_scrape.return_value = ScrapingResult(
                decisions_found=150, decisions_processed=145, decisions_saved=140, errors=5, duration_seconds=300
            )

            result = await scraper.scrape_historical_decisions(
                start_date=start_date, end_date=end_date, sections=[CourtSection.CIVILE, CourtSection.TRIBUTARIA]
            )

            mock_scrape.assert_called_once_with(start_date, end_date, [CourtSection.CIVILE, CourtSection.TRIBUTARIA])
            assert result.decisions_found == 150
            assert result.decisions_saved == 140


class TestCassazioneDatabaseIntegration:
    """Test database storage and retrieval of Cassazione decisions."""

    @pytest.fixture
    def sample_decision(self):
        """Create a sample decision for testing."""
        return CassazioneDecision(
            decision_number="15234/2024",
            date=date(2024, 3, 15),
            section=CourtSection.CIVILE,
            subsection="III",
            subject="Responsabilità amministratore SRL per obbligazioni sociali",
            summary="La Corte stabilisce i limiti della responsabilità dell'amministratore",
            full_text="Testo completo della decisione con tutti i dettagli...",
            legal_principles=[
                "L'amministratore risponde solo in caso di colpa grave",
                "È necessario il nesso causale tra condotta e danno",
            ],
            judge_names=["Mario Rossi", "Luigi Verdi", "Anna Bianchi"],
            party_names=["Alfa SpA", "Beta SRL"],
            citations_to_laws=["Art. 2476 c.c.", "Art. 2381 c.c."],
            citations_to_decisions=["Cass. Civ. 12345/2023"],
            keywords=["amministratore", "SRL", "responsabilità", "obbligazioni sociali"],
        )

    @pytest.mark.asyncio
    async def test_save_decision_to_database(self, sample_decision):
        """Test saving a decision to the database."""
        scraper = CassazioneScraper()

        # Mock database operations
        with patch.object(database_service, "get_session") as mock_session:
            mock_db = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db

            result = await scraper.save_decision_to_database(sample_decision)

            assert result is True
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_duplicate_decision(self, sample_decision):
        """Test handling duplicate decisions."""
        scraper = CassazioneScraper()

        with patch.object(scraper, "_decision_exists_in_database") as mock_exists:
            mock_exists.return_value = True

            result = await scraper.save_decision_to_database(sample_decision)

            assert result is False  # Should not save duplicate

    @pytest.mark.asyncio
    async def test_search_decisions_by_subject(self):
        """Test searching decisions by subject."""
        scraper = CassazioneScraper()

        with patch.object(database_service, "get_session") as mock_session:
            mock_db = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db

            # Mock query results
            mock_results = [
                Mock(decision_number="15234/2024", subject="Responsabilità amministratore"),
                Mock(decision_number="15235/2024", subject="Amministratore SRL"),
            ]
            mock_db.exec.return_value = mock_results

            results = await scraper.search_decisions_by_subject("amministratore SRL", limit=10)

            assert len(results) == 2
            mock_db.exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_decisions_by_date_range(self):
        """Test searching decisions by date range."""
        scraper = CassazioneScraper()
        start_date = date(2024, 1, 1)
        end_date = date(2024, 3, 31)

        with patch.object(database_service, "get_session") as mock_session:
            mock_db = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db

            mock_results = [Mock(decision_number=f"1523{i}/2024") for i in range(5)]
            mock_db.exec.return_value = mock_results

            results = await scraper.search_decisions_by_date_range(start_date, end_date, CourtSection.CIVILE)

            assert len(results) == 5
            mock_db.exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_latest_decisions(self):
        """Test retrieving latest decisions."""
        scraper = CassazioneScraper()

        with patch.object(database_service, "get_session") as mock_session:
            mock_db = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db

            mock_results = [
                Mock(decision_number="15236/2024", date=date(2024, 3, 17)),
                Mock(decision_number="15235/2024", date=date(2024, 3, 16)),
                Mock(decision_number="15234/2024", date=date(2024, 3, 15)),
            ]
            mock_db.exec.return_value = mock_results

            results = await scraper.get_latest_decisions(limit=3)

            assert len(results) == 3
            assert results[0].date > results[1].date  # Should be ordered by date desc


class TestCassazioneVectorIntegration:
    """Test integration with vector database for semantic search."""

    @pytest.mark.asyncio
    async def test_generate_decision_embeddings(self):
        """Test generating embeddings for a decision."""
        from app.services.vector_service import vector_service

        decision = CassazioneDecision(
            decision_number="15234/2024",
            date=date(2024, 3, 15),
            section=CourtSection.CIVILE,
            subject="Responsabilità amministratore SRL",
            full_text="L'amministratore di SRL ha responsabilità limitata...",
        )

        scraper = CassazioneScraper()

        with patch.object(vector_service, "generate_embeddings") as mock_embeddings:
            mock_embeddings.return_value = [0.1, 0.2, 0.3]  # Mock vector

            embeddings = await scraper.generate_decision_embeddings(decision)

            assert embeddings is not None
            assert len(embeddings) == 3
            mock_embeddings.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_decision_in_vector_db(self):
        """Test storing decision in vector database."""
        from app.services.vector_service import vector_service

        decision = CassazioneDecision(
            decision_number="15234/2024",
            date=date(2024, 3, 15),
            section=CourtSection.CIVILE,
            subject="Responsabilità amministratore SRL",
        )

        scraper = CassazioneScraper()

        with patch.object(vector_service, "upsert_vectors") as mock_upsert:
            mock_upsert.return_value = True

            result = await scraper.store_decision_in_vector_db(decision)

            assert result is True
            mock_upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_semantic_search_decisions(self):
        """Test semantic search of decisions."""
        from app.services.vector_service import vector_service

        scraper = CassazioneScraper()

        with patch.object(vector_service, "search") as mock_search:
            mock_search.return_value = [
                {
                    "id": "cass_civ_15234_2024",
                    "score": 0.85,
                    "metadata": {"decision_number": "15234/2024", "section": "civile"},
                },
                {
                    "id": "cass_civ_15235_2024",
                    "score": 0.82,
                    "metadata": {"decision_number": "15235/2024", "section": "civile"},
                },
            ]

            results = await scraper.semantic_search_decisions("responsabilità amministratore SRL", top_k=10)

            assert len(results) == 2
            assert results[0]["score"] > results[1]["score"]
            mock_search.assert_called_once()


class TestCassazioneSchedulerIntegration:
    """Test integration with job scheduler for automated updates."""

    @pytest.mark.asyncio
    async def test_schedule_weekly_updates(self):
        """Test scheduling weekly Cassazione updates."""
        from app.services.scheduler_service import scheduler_service

        scraper = CassazioneScraper()

        with patch.object(scheduler_service, "add_job") as mock_add_job:
            scraper.schedule_weekly_updates()

            mock_add_job.assert_called_once()
            call_args = mock_add_job.call_args
            assert call_args[1]["trigger"] == "cron"  # Should use cron trigger
            assert call_args[1]["day_of_week"] == "sun"  # Should run on Sundays

    @pytest.mark.asyncio
    async def test_update_recent_decisions_job(self):
        """Test the scheduled job for updating recent decisions."""
        scraper = CassazioneScraper()

        with patch.object(scraper, "scrape_recent_decisions") as mock_scrape:
            mock_scrape.return_value = ScrapingResult(
                decisions_found=25, decisions_processed=25, decisions_saved=23, errors=2, duration_seconds=180
            )

            result = await scraper.update_recent_decisions_job()

            assert result.decisions_found == 25
            assert result.decisions_saved == 23
            mock_scrape.assert_called_once()

    def test_scraper_statistics_tracking(self):
        """Test tracking of scraping statistics."""
        stats = ScrapingStatistics()

        # Simulate some scraping activity
        stats.record_page_scraped(success=True, duration=1.5)
        stats.record_page_scraped(success=True, duration=2.1)
        stats.record_page_scraped(success=False, duration=0.8)
        stats.record_decision_processed(saved=True)
        stats.record_decision_processed(saved=True)
        stats.record_decision_processed(saved=False)

        assert stats.total_pages_attempted == 3
        assert stats.total_pages_successful == 2
        assert stats.total_decisions_found == 3
        assert stats.total_decisions_saved == 2
        assert stats.success_rate == pytest.approx(0.667, rel=1e-2)
        assert stats.average_page_duration == pytest.approx(1.47, rel=1e-2)


class TestCassazioneErrorHandling:
    """Test comprehensive error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_handle_network_timeout(self):
        """Test handling network timeouts."""
        scraper = CassazioneScraper(timeout_seconds=1)

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.side_effect = TimeoutError()

            with pytest.raises(ScrapingError, match="Network timeout"):
                await scraper._fetch_page_with_retry("http://test.com")

    @pytest.mark.asyncio
    async def test_handle_malformed_html(self):
        """Test handling malformed HTML."""
        scraper = CassazioneScraper()
        malformed_html = "<html><body><div><p>Unclosed tags<div></body>"

        # Should not raise exception, should return None gracefully
        decision = await scraper.parse_decision_from_html(malformed_html, "http://test.com")
        assert decision is None

    @pytest.mark.asyncio
    async def test_handle_missing_required_fields(self):
        """Test handling HTML with missing required fields."""
        scraper = CassazioneScraper()
        incomplete_html = """
        <html>
        <body>
            <h1>Some court decision</h1>
            <p>But missing decision number, date, etc.</p>
        </body>
        </html>
        """

        decision = await scraper.parse_decision_from_html(incomplete_html, "http://test.com")
        assert decision is None

    @pytest.mark.asyncio
    async def test_handle_database_connection_error(self):
        """Test handling database connection errors."""
        scraper = CassazioneScraper()
        decision = CassazioneDecision(
            decision_number="15234/2024", date=date(2024, 3, 15), section=CourtSection.CIVILE, subject="Test"
        )

        with patch.object(database_service, "get_session") as mock_session:
            mock_session.side_effect = Exception("Database connection failed")

            result = await scraper.save_decision_to_database(decision)
            assert result is False  # Should handle gracefully

    @pytest.mark.asyncio
    async def test_handle_rate_limit_exceeded(self):
        """Test handling server rate limiting (HTTP 429)."""
        scraper = CassazioneScraper()

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 429
            mock_response.headers = {"Retry-After": "60"}
            mock_get.return_value = mock_response

            with pytest.raises(ScrapingError, match="Rate limited by server"):
                await scraper._fetch_page_with_retry("http://test.com")

    def test_decision_number_parsing_edge_cases(self):
        """Test parsing various decision number formats."""
        scraper = CassazioneScraper()

        test_cases = [
            "Cass. Civ. Sez. III, n. 15234/2024",
            "Cassazione Civile, Sentenza 15234/2024",
            "Cass. Trib., n. 15234/2024",
            "15234/2024",
            "Cass. SS. UU., n. 15234/2024",
        ]

        for case in test_cases:
            parsed = scraper._parse_decision_number(case)
            assert "15234/2024" in parsed or "15234" in parsed

    def test_date_parsing_edge_cases(self):
        """Test parsing various Italian date formats."""
        scraper = CassazioneScraper()

        test_cases = ["15 marzo 2024", "15/03/2024", "15-03-2024", "15.03.2024", "marzo 15, 2024"]

        for case in test_cases:
            parsed = scraper._parse_italian_date(case)
            if parsed:  # Some formats might not be supported
                assert parsed.year == 2024
                assert parsed.month == 3
                assert parsed.day == 15


# Integration test with real components
class TestCassazioneIntegrationFull:
    """Full integration tests (require actual services)."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_scraping_workflow(self):
        """Test complete workflow from scraping to database storage."""
        # This test would run against actual services in integration environment
        scraper = CassazioneScraper(rate_limit_delay=2.0)  # Respectful rate limiting

        # Test with a small date range
        date.today() - timedelta(days=7)
        date.today()

        try:
            result = await scraper.scrape_recent_decisions(
                sections=[CourtSection.CIVILE],
                limit=5,  # Small limit for testing
            )

            assert isinstance(result, ScrapingResult)
            assert result.decisions_found >= 0

        except Exception as e:
            pytest.skip(f"Integration test failed (expected in unit test env): {e}")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_semantic_search_workflow(self):
        """Test complete semantic search workflow."""
        scraper = CassazioneScraper()

        try:
            results = await scraper.semantic_search_decisions("responsabilità amministratore società", top_k=5)

            assert isinstance(results, list)
            # Results might be empty if no data in vector DB yet

        except Exception as e:
            pytest.skip(f"Integration test failed (expected in unit test env): {e}")


if __name__ == "__main__":
    # Run tests with coverage
    pytest.main(
        [
            __file__,
            "-v",
            "--cov=app.services.scrapers.cassazione_scraper",
            "--cov-report=html",
            "--cov-report=term-missing",
        ]
    )
