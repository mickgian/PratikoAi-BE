"""
Test suite for Atomic Facts Extraction System.

This module contains comprehensive tests for extracting and canonicalizing
atomic facts from Italian professional queries, following TDD principles.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional

import pytest

# Import the classes we'll implement
from app.services.atomic_facts_extractor import (
    AtomicFacts,
    AtomicFactsExtractor,
    DateFact,
    ExtractionSpan,
    GeographicInfo,
    LegalEntity,
    MonetaryAmount,
    ProfessionalCategory,
)


class TestAtomicFactsExtractor:
    """Test cases for the AtomicFactsExtractor class."""

    @pytest.fixture
    def extractor(self):
        """Create an instance of the AtomicFactsExtractor for testing."""
        return AtomicFactsExtractor()

    # === MONETARY AMOUNT EXTRACTION TESTS ===

    @pytest.mark.parametrize(
        "query,expected_amounts,expected_currency",
        [
            # Euro amounts - numeric format
            ("calcola IRPEF su 50.000 euro", [50000.0], "EUR"),
            ("stipendio di €35.000", [35000.0], "EUR"),
            ("fattura da 1.250,50 euro", [1250.5], "EUR"),
            ("rimborso € 150", [150.0], "EUR"),
            # Euro amounts - written format
            ("cinquantamila euro di reddito", [50000.0], "EUR"),
            ("ventimila cinquecento euro", [20500.0], "EUR"),
            ("duemila euro", [2000.0], "EUR"),
            # Multiple amounts
            ("stipendio 30000 euro più bonus 5000 euro", [30000.0, 5000.0], "EUR"),
            # Edge cases
            ("zero euro", [0.0], "EUR"),
            ("un euro", [1.0], "EUR"),
            ("1 euro e 50 centesimi", [1.5], "EUR"),
        ],
    )
    def test_monetary_amount_extraction(self, extractor, query, expected_amounts, expected_currency):
        """Test extraction of monetary amounts from Italian queries."""
        facts = extractor.extract(query)

        assert len(facts.monetary_amounts) == len(expected_amounts)
        for i, expected in enumerate(expected_amounts):
            assert facts.monetary_amounts[i].amount == expected
            assert facts.monetary_amounts[i].currency == expected_currency

    @pytest.mark.parametrize(
        "query,expected_percentages",
        [
            # Percentage formats
            ("aliquota IVA al 22%", [22.0]),
            ("sconto del 15 percento", [15.0]),
            ("interesse al 3,5%", [3.5]),
            ("ritenuta 20% su onorari", [20.0]),
            ("deduzione al cento per cento", [100.0]),
            # Multiple percentages
            ("IVA 4% su libri, 10% su farmaci", [4.0, 10.0]),
        ],
    )
    def test_percentage_extraction(self, extractor, query, expected_percentages):
        """Test extraction of percentage values."""
        facts = extractor.extract(query)

        extracted_percentages = [amt.amount for amt in facts.monetary_amounts if amt.is_percentage]
        assert extracted_percentages == expected_percentages

    # === DATE AND TIME EXTRACTION TESTS ===

    @pytest.mark.parametrize(
        "query,expected_dates",
        [
            # Specific dates - various formats
            ("scadenza F24 del 16 marzo 2024", ["2024-03-16"]),
            ("dichiarazione entro il 15/04/2024", ["2024-04-15"]),
            ("fattura del 1° gennaio 2024", ["2024-01-01"]),
            ("pagamento il 30-06-2024", ["2024-06-30"]),
            # Italian month names
            ("termine il 15 febbraio", ["2024-02-15"]),  # Assuming current year
            ("scadenza 31 dicembre 2023", ["2023-12-31"]),
            # Multiple dates
            ("periodo dal 1 gennaio al 31 marzo 2024", ["2024-01-01", "2024-03-31"]),
        ],
    )
    def test_specific_date_extraction(self, extractor, query, expected_dates):
        """Test extraction of specific dates."""
        facts = extractor.extract(query)

        extracted_dates = [df.iso_date for df in facts.dates if df.date_type == "specific"]
        assert extracted_dates == expected_dates

    @pytest.mark.parametrize(
        "query,expected_relative_dates",
        [
            # Relative date expressions
            ("anno scorso", ["previous_year"]),
            ("prossimo trimestre", ["next_quarter"]),
            ("la settimana scorsa", ["previous_week"]),
            ("fra due mesi", ["in_2_months"]),
        ],
    )
    def test_relative_date_extraction(self, extractor, query, expected_relative_dates):
        """Test extraction of relative date expressions."""
        facts = extractor.extract(query)

        relative_dates = [df.relative_expression for df in facts.dates if df.date_type == "relative"]
        assert relative_dates == expected_relative_dates

    @pytest.mark.parametrize(
        "query,expected_tax_years",
        [
            ("anno d'imposta 2023", [2023]),
            ("dichiarazione 2024", [2024]),
            ("redditi anno 2022", [2022]),
        ],
    )
    def test_tax_year_extraction(self, extractor, query, expected_tax_years):
        """Test extraction of tax years."""
        facts = extractor.extract(query)

        tax_years = [df.tax_year for df in facts.dates if df.date_type == "tax_year"]
        assert tax_years == expected_tax_years

    @pytest.mark.parametrize(
        "query,expected_durations",
        [
            ("lavoro da 5 anni", ["5 years"]),
            ("contratto di 2 mesi", ["2 months"]),
            ("anzianità di 10 anni", ["10 years"]),
            ("preavviso 30 giorni", ["30 days"]),
        ],
    )
    def test_duration_extraction(self, extractor, query, expected_durations):
        """Test extraction of time durations."""
        facts = extractor.extract(query)

        durations = [df.duration_text for df in facts.dates if df.date_type == "duration"]
        assert durations == expected_durations

    # === LEGAL/TAX ENTITY EXTRACTION TESTS ===

    @pytest.mark.parametrize(
        "query,expected_tax_codes",
        [
            ("Codice Fiscale RSSMRA80A01H501Z", ["RSSMRA80A01H501Z"]),
            ("CF: RSSMRA80A01H501Z", ["RSSMRA80A01H501Z"]),
            ("Partita IVA 12345678901", ["12345678901"]),
            ("P.IVA IT12345678901", ["IT12345678901"]),
        ],
    )
    def test_tax_code_extraction(self, extractor, query, expected_tax_codes):
        """Test extraction of Italian tax codes."""
        facts = extractor.extract(query)

        tax_codes = [
            le.identifier for le in facts.legal_entities if le.entity_type in ["codice_fiscale", "partita_iva"]
        ]
        assert tax_codes == expected_tax_codes

    @pytest.mark.parametrize(
        "query,expected_company_types",
        [
            ("costituzione SRL", ["SRL"]),
            ("società per azioni SPA", ["SPA"]),
            ("s.r.l. semplificata", ["SRL"]),  # Canonicalized
            ("ditta individuale", ["DITTA_INDIVIDUALE"]),
            ("società in nome collettivo SNC", ["SNC"]),
        ],
    )
    def test_company_type_extraction(self, extractor, query, expected_company_types):
        """Test extraction and canonicalization of company types."""
        facts = extractor.extract(query)

        company_types = [le.canonical_form for le in facts.legal_entities if le.entity_type == "company_type"]
        assert company_types == expected_company_types

    @pytest.mark.parametrize(
        "query,expected_documents",
        [
            ("compilazione F24", ["F24"]),
            ("modello 730", ["730"]),
            ("fattura elettronica", ["FATTURA_ELETTRONICA"]),
            ("dichiarazione dei redditi", ["DICHIARAZIONE_REDDITI"]),
            ("modello UNICO", ["UNICO"]),
            ("CUD", ["CUD"]),
        ],
    )
    def test_document_type_extraction(self, extractor, query, expected_documents):
        """Test extraction of Italian tax/legal document types."""
        facts = extractor.extract(query)

        doc_types = [le.canonical_form for le in facts.legal_entities if le.entity_type == "document_type"]
        assert doc_types == expected_documents

    @pytest.mark.parametrize(
        "query,expected_legal_refs",
        [
            ("ricorso ex art. 633 c.p.c.", ["art. 633 c.p.c."]),
            ("articolo 2082 del codice civile", ["art. 2082 c.c."]),
            ("DPR 633/72", ["DPR 633/72"]),
            ("Legge 104/92", ["L. 104/92"]),
            ("art. 36 comma 2 c.p.c.", ["art. 36 comma 2 c.p.c."]),
        ],
    )
    def test_legal_reference_extraction(self, extractor, query, expected_legal_refs):
        """Test extraction of Italian legal references."""
        facts = extractor.extract(query)

        legal_refs = [le.canonical_form for le in facts.legal_entities if le.entity_type == "legal_reference"]
        assert legal_refs == expected_legal_refs

    # === PROFESSIONAL CATEGORY EXTRACTION TESTS ===

    @pytest.mark.parametrize(
        "query,expected_ccnl_sectors",
        [
            ("ferie CCNL metalmeccanici", ["metalmeccanici"]),
            ("contratto commercio", ["commercio"]),
            ("CCNL industria chimica", ["industria_chimica"]),
            ("settore costruzioni", ["costruzioni"]),
            ("tessile abbigliamento", ["tessile_abbigliamento"]),
        ],
    )
    def test_ccnl_sector_extraction(self, extractor, query, expected_ccnl_sectors):
        """Test extraction of CCNL sectors."""
        facts = extractor.extract(query)

        sectors = [pc.sector for pc in facts.professional_categories if pc.category_type == "ccnl_sector"]
        assert sectors == expected_ccnl_sectors

    @pytest.mark.parametrize(
        "query,expected_job_levels",
        [
            ("operaio livello 5", ["5"]),
            ("impiegato 3° livello", ["3"]),
            ("quadro", ["quadro"]),
            ("dirigente", ["dirigente"]),
            ("apprendista", ["apprendista"]),
        ],
    )
    def test_job_level_extraction(self, extractor, query, expected_job_levels):
        """Test extraction of job levels and categories."""
        facts = extractor.extract(query)

        levels = [pc.level for pc in facts.professional_categories if pc.category_type == "job_level"]
        assert levels == expected_job_levels

    @pytest.mark.parametrize(
        "query,expected_contract_types",
        [
            ("contratto a tempo determinato", ["tempo_determinato"]),
            ("tempo indeterminato", ["tempo_indeterminato"]),
            ("contratto di apprendistato", ["apprendistato"]),
            ("lavoro stagionale", ["stagionale"]),
        ],
    )
    def test_contract_type_extraction(self, extractor, query, expected_contract_types):
        """Test extraction of contract types."""
        facts = extractor.extract(query)

        contract_types = [
            pc.contract_type for pc in facts.professional_categories if pc.category_type == "contract_type"
        ]
        assert contract_types == expected_contract_types

    # === GEOGRAPHIC INFORMATION EXTRACTION TESTS ===

    @pytest.mark.parametrize(
        "query,expected_regions",
        [
            ("tasse in Lombardia", ["Lombardia"]),
            ("normativa Sicilia", ["Sicilia"]),
            ("regione Veneto", ["Veneto"]),
        ],
    )
    def test_region_extraction(self, extractor, query, expected_regions):
        """Test extraction of Italian regions."""
        facts = extractor.extract(query)

        regions = [gi.region for gi in facts.geographic_info if gi.geo_type == "region"]
        assert regions == expected_regions

    @pytest.mark.parametrize(
        "query,expected_cities",
        [
            ("ufficio a Milano", ["Milano"]),
            ("sede di Roma", ["Roma"]),
            ("comune di Napoli", ["Napoli"]),
        ],
    )
    def test_city_extraction(self, extractor, query, expected_cities):
        """Test extraction of Italian cities."""
        facts = extractor.extract(query)

        cities = [gi.city for gi in facts.geographic_info if gi.geo_type == "city"]
        assert cities == expected_cities

    @pytest.mark.parametrize(
        "query,expected_areas",
        [
            ("normativa del Nord", ["Nord"]),
            ("regioni del Sud", ["Sud"]),
            ("Centro Italia", ["Centro"]),
        ],
    )
    def test_area_extraction(self, extractor, query, expected_areas):
        """Test extraction of macro geographic areas."""
        facts = extractor.extract(query)

        areas = [gi.area for gi in facts.geographic_info if gi.geo_type == "area"]
        assert areas == expected_areas

    # === COMPLEX INTEGRATION TESTS ===

    def test_complex_query_integration(self, extractor):
        """Test extraction from a complex multi-fact query."""
        query = "calcola TFR per 10 anni con stipendio 30.000 euro, scadenza entro il 31 dicembre 2024"

        facts = extractor.extract(query)

        # Check monetary amounts
        assert len(facts.monetary_amounts) == 1
        assert facts.monetary_amounts[0].amount == 30000.0

        # Check dates
        date_strings = [df.iso_date for df in facts.dates if df.date_type == "specific"]
        assert "2024-12-31" in date_strings

        # Check durations
        durations = [df.duration_text for df in facts.dates if df.date_type == "duration"]
        assert "10 years" in durations

    def test_ccnl_with_amounts_and_levels(self, extractor):
        """Test extraction from CCNL-specific query with multiple fact types."""
        query = "calcola stipendio CCNL metalmeccanici livello 5 con €28.000 annui"

        facts = extractor.extract(query)

        # Check professional category
        sectors = [pc.sector for pc in facts.professional_categories if pc.category_type == "ccnl_sector"]
        assert "metalmeccanici" in sectors

        levels = [pc.level for pc in facts.professional_categories if pc.category_type == "job_level"]
        assert "5" in levels

        # Check monetary amounts
        assert len(facts.monetary_amounts) == 1
        assert facts.monetary_amounts[0].amount == 28000.0

    def test_legal_query_with_references_and_dates(self, extractor):
        """Test extraction from legal query with references and deadlines."""
        query = "ricorso ex art. 633 c.p.c. entro 30 giorni dalla notifica del 15 marzo 2024"

        facts = extractor.extract(query)

        # Check legal references
        legal_refs = [le.canonical_form for le in facts.legal_entities if le.entity_type == "legal_reference"]
        assert "art. 633 c.p.c." in legal_refs

        # Check specific dates
        dates = [df.iso_date for df in facts.dates if df.date_type == "specific"]
        assert "2024-03-15" in dates

        # Check durations
        durations = [df.duration_text for df in facts.dates if df.date_type == "duration"]
        assert "30 days" in durations

    # === CANONICALIZATION TESTS ===

    @pytest.mark.parametrize(
        "input_number,expected_decimal",
        [
            ("1.000,50", 1000.5),
            ("50.000", 50000.0),
            ("1,5", 1.5),
            ("1000", 1000.0),
            ("cinquanta", 50.0),
            ("duemila", 2000.0),
            ("ventimila", 20000.0),
        ],
    )
    def test_number_canonicalization(self, extractor, input_number, expected_decimal):
        """Test canonicalization of Italian number formats."""
        canonical = extractor._canonicalize_number(input_number)
        assert canonical == expected_decimal

    @pytest.mark.parametrize(
        "input_date,expected_iso",
        [
            ("15 marzo 2024", "2024-03-16"),
            ("1° gennaio", "2024-01-01"),  # Assuming current year
            ("31/12/2023", "2023-12-31"),
        ],
    )
    def test_date_canonicalization(self, extractor, input_date, expected_iso):
        """Test canonicalization of Italian date formats."""
        canonical = extractor._canonicalize_date(input_date)
        assert canonical == expected_iso

    @pytest.mark.parametrize(
        "input_entity,expected_canonical",
        [
            ("s.r.l.", "SRL"),
            ("società per azioni", "SPA"),
            ("ditta individuale", "DITTA_INDIVIDUALE"),
            ("art. 633 del c.p.c.", "art. 633 c.p.c."),
        ],
    )
    def test_entity_canonicalization(self, extractor, input_entity, expected_canonical):
        """Test canonicalization of legal entities."""
        canonical = extractor._canonicalize_entity(input_entity)
        assert canonical == expected_canonical

    # === PERFORMANCE TESTS ===

    def test_extraction_performance(self, extractor):
        """Test that extraction completes within performance requirements (<50ms)."""
        query = "calcola TFR per 10 anni CCNL metalmeccanici livello 5 con stipendio 35.000 euro scadenza 31/12/2024"

        import time

        start_time = time.time()
        extractor.extract(query)
        end_time = time.time()

        extraction_time_ms = (end_time - start_time) * 1000
        assert extraction_time_ms < 50.0, f"Extraction took {extraction_time_ms}ms, should be <50ms"

    # === ERROR HANDLING TESTS ===

    def test_empty_query_handling(self, extractor):
        """Test handling of empty or whitespace-only queries."""
        facts = extractor.extract("")
        assert facts.is_empty()

        facts = extractor.extract("   ")
        assert facts.is_empty()

    def test_malformed_input_handling(self, extractor):
        """Test graceful handling of malformed input."""
        malformed_queries = [
            "€€€ invalid amount",
            "32/45/2024",  # Invalid date
            "articolo senza numero",
            "livello xyz",  # Invalid level
        ]

        for query in malformed_queries:
            facts = extractor.extract(query)
            # Should not raise exception, may have empty or partial results
            assert isinstance(facts, AtomicFacts)

    def test_confidence_scoring(self, extractor):
        """Test that confidence scores are properly calculated."""
        query = "stipendio 30.000 euro"
        facts = extractor.extract(query)

        assert len(facts.monetary_amounts) == 1
        assert 0.0 <= facts.monetary_amounts[0].confidence <= 1.0

    # === SPAN EXTRACTION TESTS ===

    def test_extraction_spans(self, extractor):
        """Test that extraction spans correctly identify text positions."""
        query = "calcola IRPEF su 50.000 euro scadenza 31/12/2024"
        facts = extractor.extract(query)

        # Check that monetary amount span is correct
        amount_span = facts.monetary_amounts[0].span
        assert query[amount_span.start : amount_span.end] in ["50.000 euro", "50.000"]

        # Check date span
        date_span = facts.dates[0].span
        assert query[date_span.start : date_span.end] == "31/12/2024"


class TestAtomicFactsDataModels:
    """Test the data models used for storing atomic facts."""

    def test_atomic_facts_model(self):
        """Test the AtomicFacts container model."""
        facts = AtomicFacts()
        assert facts.is_empty()

        # Add some facts
        facts.monetary_amounts.append(MonetaryAmount(amount=1000.0, currency="EUR", confidence=0.95))
        assert not facts.is_empty()

    def test_monetary_amount_model(self):
        """Test the MonetaryAmount model."""
        amount = MonetaryAmount(
            amount=1500.5,
            currency="EUR",
            is_percentage=False,
            confidence=0.9,
            original_text="1.500,50 euro",
            span=ExtractionSpan(start=10, end=25),
        )

        assert amount.amount == 1500.5
        assert amount.currency == "EUR"
        assert not amount.is_percentage
        assert amount.confidence == 0.9

    def test_date_fact_model(self):
        """Test the DateFact model."""
        date_fact = DateFact(
            date_type="specific",
            iso_date="2024-03-15",
            original_text="15 marzo 2024",
            confidence=0.95,
            span=ExtractionSpan(start=5, end=18),
        )

        assert date_fact.date_type == "specific"
        assert date_fact.iso_date == "2024-03-15"
        assert date_fact.confidence == 0.95


# === FIXTURES FOR REALISTIC TEST DATA ===


@pytest.fixture
def sample_professional_queries():
    """Real-world Italian professional queries for testing."""
    return [
        "Calcolo IRPEF su reddito di 45.000 euro per l'anno d'imposta 2023",
        "Scadenza F24 INPS entro il 16 marzo 2024 per contributi dipendenti",
        "Ferie CCNL metalmeccanici livello 5 con 10 anni di anzianità",
        "Costituzione SRL con capitale sociale €10.000 a Milano",
        "Ricorso ex art. 633 c.p.c. contro decreto ingiuntivo",
        "TFR dipendente con stipendio €28.000 dopo 8 anni di servizio",
        "Aliquota IVA 22% su servizi professionali fattura elettronica",
        "Contratto tempo determinato 6 mesi CCNL commercio",
        "Deduzione spese professionali 20% su reddito €35.000",
        "Dichiarazione successione entro 12 mesi eredità Lombardia",
    ]


@pytest.fixture
def expected_extractions():
    """Expected extractions for the sample queries."""
    return [
        # Query 1: "Calcolo IRPEF su reddito di 45.000 euro per l'anno d'imposta 2023"
        {"monetary_amounts": [45000.0], "dates": [{"tax_year": 2023}], "legal_entities": [{"document_type": "IRPEF"}]},
        # Add more expected results...
    ]
