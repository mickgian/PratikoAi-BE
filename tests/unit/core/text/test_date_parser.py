"""
Unit tests for Italian document date parsing.

Tests extract_publication_date() and extract_year_from_query() functions
used for filtering documents by publication date.
"""

from datetime import date

import pytest

from app.core.text.date_parser import (
    ITALIAN_MONTHS,
    extract_publication_date,
    extract_year_from_query,
)


class TestExtractPublicationDate:
    """Test extraction of publication dates from Italian documents."""

    def test_extract_roma_format(self):
        """Test 'Roma, DD month YYYY' format."""
        content = "Roma, 13 ottobre 2025\n\nRisoluzione n. 56..."
        result = extract_publication_date(content)

        assert result == date(2025, 10, 13)

    def test_extract_del_format(self):
        """Test 'del DD month YYYY' format."""
        content = "Risoluzione n. 56 del 13 ottobre 2025..."
        result = extract_publication_date(content)

        assert result == date(2025, 10, 13)

    def test_extract_simple_format(self):
        """Test 'DD month YYYY' format."""
        content = "Documento del 30 ottobre 2025..."
        result = extract_publication_date(content)

        assert result == date(2025, 10, 30)

    def test_extract_from_title(self):
        """Test extraction from title parameter."""
        title = "Risoluzione n. 56 del 13 ottobre 2025"
        content = "Some content without date"
        result = extract_publication_date(content, title=title)

        assert result == date(2025, 10, 13)

    def test_all_italian_months(self):
        """Test extraction for all Italian months."""
        months_tests = [
            ("1 gennaio 2025", date(2025, 1, 1)),
            ("15 febbraio 2025", date(2025, 2, 15)),
            ("20 marzo 2025", date(2025, 3, 20)),
            ("10 aprile 2025", date(2025, 4, 10)),
            ("5 maggio 2025", date(2025, 5, 5)),
            ("30 giugno 2025", date(2025, 6, 30)),
            ("15 luglio 2025", date(2025, 7, 15)),
            ("20 agosto 2025", date(2025, 8, 20)),
            ("10 settembre 2025", date(2025, 9, 10)),
            ("13 ottobre 2025", date(2025, 10, 13)),
            ("10 novembre 2025", date(2025, 11, 10)),
            ("25 dicembre 2025", date(2025, 12, 25)),
        ]

        for content, expected in months_tests:
            result = extract_publication_date(content)
            assert result == expected, f"Failed for: {content}"

    def test_case_insensitive(self):
        """Test that extraction is case-insensitive."""
        content_lower = "roma, 13 ottobre 2025"
        content_upper = "ROMA, 13 OTTOBRE 2025"
        content_mixed = "Roma, 13 OTTOBRE 2025"

        assert extract_publication_date(content_lower) == date(2025, 10, 13)
        assert extract_publication_date(content_upper) == date(2025, 10, 13)
        assert extract_publication_date(content_mixed) == date(2025, 10, 13)

    def test_single_digit_day(self):
        """Test extraction with single-digit day."""
        content = "Roma, 5 ottobre 2025"
        result = extract_publication_date(content)

        assert result == date(2025, 10, 5)

    def test_two_digit_day(self):
        """Test extraction with two-digit day."""
        content = "Roma, 30 ottobre 2025"
        result = extract_publication_date(content)

        assert result == date(2025, 10, 30)

    def test_no_date_found(self):
        """Test when no date pattern is found."""
        content = "This document has no recognizable Italian date"
        result = extract_publication_date(content)

        assert result is None

    def test_invalid_date(self):
        """Test handling of invalid dates (e.g., Feb 30)."""
        content = "30 febbraio 2025"  # February 30 doesn't exist
        result = extract_publication_date(content)

        assert result is None  # Should return None for invalid dates

    def test_first_500_chars_only(self):
        """Test that only first 500 chars of content are searched."""
        # Date in first 500 chars
        content_early = "Roma, 13 ottobre 2025" + "X" * 1000
        assert extract_publication_date(content_early) == date(2025, 10, 13)

        # Date after 500 chars (should not be found)
        content_late = "X" * 500 + "Roma, 13 ottobre 2025"
        assert extract_publication_date(content_late) is None

    def test_risoluzione_n_format(self):
        """Test 'Risoluzione n. X del DD month YYYY' format."""
        content = "Agenzia delle Entrate\nRisoluzione n. 56 del 13 ottobre 2025\n\nChiarimenti..."
        result = extract_publication_date(content)

        assert result == date(2025, 10, 13)

    def test_multiple_dates_takes_first(self):
        """Test that when multiple dates exist, the first is taken."""
        content = "Roma, 13 ottobre 2025\n\nRiferimento al 20 novembre 2025"
        result = extract_publication_date(content)

        # Should match first date (most specific pattern)
        assert result == date(2025, 10, 13)

    def test_year_range(self):
        """Test extraction works for reasonable year range."""
        test_years = [2020, 2021, 2022, 2023, 2024, 2025, 2026]

        for year in test_years:
            content = f"Roma, 15 ottobre {year}"
            result = extract_publication_date(content)
            assert result == date(year, 10, 15)

    def test_empty_content(self):
        """Test extraction with empty content."""
        assert extract_publication_date("") is None
        assert extract_publication_date("", title="") is None

    def test_real_world_example_risoluzione_56(self):
        """Test extraction from actual Risoluzione n. 56 format."""
        content = """
        RISOLUZIONE N. 56/E

        Roma, 13 ottobre 2025

        OGGETTO: Interpello articolo 11, comma 1, lettera a), legge 27 luglio 2000
        """
        result = extract_publication_date(content)

        assert result == date(2025, 10, 13)

    def test_real_world_example_risoluzione_62(self):
        """Test extraction from actual Risoluzione n. 62 format."""
        content = """
        Agenzia delle Entrate
        Risoluzione n. 62 del 30 ottobre 2025

        Chiarimenti in merito...
        """
        result = extract_publication_date(content)

        assert result == date(2025, 10, 30)


class TestExtractYearFromQuery:
    """Test extraction of years from search queries."""

    def test_extract_year_2025(self):
        """Test extraction of year 2025."""
        query = "risoluzioni ottobre 2025"
        result = extract_year_from_query(query)

        assert result == 2025

    def test_extract_year_2024(self):
        """Test extraction of year 2024."""
        query = "documenti novembre 2024"
        result = extract_year_from_query(query)

        assert result == 2024

    def test_extract_year_from_middle(self):
        """Test extraction when year is in middle of query."""
        query = "documenti del 2023 sulla normativa"
        result = extract_year_from_query(query)

        assert result == 2023

    def test_no_year_found(self):
        """Test when no year is present."""
        query = "documenti sulla normativa fiscale"
        result = extract_year_from_query(query)

        assert result is None

    def test_multiple_years_takes_first(self):
        """Test that when multiple years exist, first valid one is taken."""
        query = "confronto 2024 vs 2025"
        result = extract_year_from_query(query)

        assert result == 2024  # First valid year in 2010-2029 range

    def test_year_range_validation(self):
        """Test that only years 2010-2029 are accepted."""
        # Valid years
        assert extract_year_from_query("anno 2010") == 2010
        assert extract_year_from_query("anno 2015") == 2015
        assert extract_year_from_query("anno 2020") == 2020
        assert extract_year_from_query("anno 2025") == 2025
        assert extract_year_from_query("anno 2029") == 2029

        # Invalid years (outside range)
        assert extract_year_from_query("anno 2009") is None
        assert extract_year_from_query("anno 2030") is None
        assert extract_year_from_query("anno 2050") is None
        assert extract_year_from_query("anno 1999") is None

    def test_empty_query(self):
        """Test extraction with empty query."""
        assert extract_year_from_query("") is None

    def test_year_as_standalone_number(self):
        """Test extraction when year is standalone."""
        assert extract_year_from_query("2025") == 2025

    def test_real_world_queries(self):
        """Test extraction from real user queries."""
        queries_and_expected = [
            ("Cosa sono le detrazioni fiscali per ottobre 2025?", 2025),
            ("risoluzioni di novembre 2024", 2024),
            ("normativa prassi ottobre e novembre 2025", 2025),
            ("list all risoluzioni for 2023", 2023),
            ("documenti agenziaentrate", None),  # No year
        ]

        for query, expected in queries_and_expected:
            result = extract_year_from_query(query)
            assert result == expected, f"Failed for query: {query}"


class TestItalianMonthsMapping:
    """Test ITALIAN_MONTHS constant."""

    def test_all_months_present(self):
        """Test that all 12 Italian months are mapped."""
        assert len(ITALIAN_MONTHS) == 12

    def test_correct_month_numbers(self):
        """Test that each month maps to correct number."""
        expected_mapping = {
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

        assert ITALIAN_MONTHS == expected_mapping

    def test_lowercase_keys(self):
        """Test that all keys are lowercase."""
        for month_name in ITALIAN_MONTHS.keys():
            assert month_name == month_name.lower()


class TestDateParserIntegration:
    """Integration tests for date parsing in document ingestion flow."""

    def test_parse_and_filter_october_documents(self):
        """Test that October documents can be parsed and filtered."""
        documents = [
            ("Risoluzione n. 56 del 13 ottobre 2025", "content1"),
            ("Risoluzione n. 62 del 30 ottobre 2025", "content2"),
            ("Risoluzione n. 63 del 10 novembre 2025", "content3"),
        ]

        # Extract dates
        parsed = []
        for title, content in documents:
            pub_date = extract_publication_date(content, title=title)
            parsed.append((title, pub_date))

        # Filter October 2025 documents
        october_docs = [
            (title, pub_date)
            for title, pub_date in parsed
            if pub_date and pub_date.year == 2025 and pub_date.month == 10
        ]

        # Should have 2 October documents
        assert len(october_docs) == 2
        assert all(doc[1].month == 10 for doc in october_docs)

    def test_query_year_matches_document_year(self):
        """Test that query year can be used to filter documents."""
        query = "risoluzioni ottobre 2025"
        query_year = extract_year_from_query(query)

        document_title = "Risoluzione n. 56 del 13 ottobre 2025"
        doc_date = extract_publication_date("", title=document_title)

        # Query year should match document year
        assert query_year == doc_date.year

    def test_chronological_ordering(self):
        """Test that extracted dates can be used for chronological ordering."""
        documents = [
            ("Risoluzione n. 62 del 30 ottobre 2025", "content1"),  # Later
            ("Risoluzione n. 56 del 13 ottobre 2025", "content2"),  # Earlier
            ("Risoluzione n. 63 del 10 novembre 2025", "content3"),  # Latest
        ]

        # Extract dates
        docs_with_dates = []
        for title, content in documents:
            pub_date = extract_publication_date(content, title=title)
            docs_with_dates.append((title, pub_date))

        # Sort chronologically
        sorted_docs = sorted(docs_with_dates, key=lambda x: x[1])

        # Check order (earliest first)
        assert sorted_docs[0][1].day == 13  # n. 56 (Oct 13)
        assert sorted_docs[1][1].day == 30  # n. 62 (Oct 30)
        assert sorted_docs[2][1].day == 10  # n. 63 (Nov 10)
