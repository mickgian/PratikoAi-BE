"""
Test suite for Italian Query Normalization system.
Following TDD principles - these tests are written before implementation.

This system normalizes Italian tax/legal queries to improve cache hit rates
from 70% to 80%+, directly supporting the €2/user/month cost target.
"""

import time
from typing import Dict, List, Set
from unittest.mock import Mock, patch

import pytest

from app.models.query_normalization import QueryNormalizationLog

# These imports will be created during implementation
from app.services.italian_query_normalizer import ItalianQueryNormalizer, NormalizationResult, NormalizationStats


class TestItalianTaxTerminologyNormalization:
    """Test normalization of common Italian tax terminology variations."""

    @pytest.fixture
    def normalizer(self):
        """Create normalizer instance for testing."""
        return ItalianQueryNormalizer()

    def test_iva_variations_normalization(self, normalizer):
        """Test IVA variations are normalized to canonical form."""
        test_cases = [
            ("IVA sui servizi digitali", "iva servizi digitali"),
            ("imposta valore aggiunto servizi", "iva servizi"),
            ("i.v.a. per fatturazione", "iva fatturazione"),
            ("Imposta sul Valore Aggiunto", "iva"),
            ("iva 22%", "iva 22%"),  # Preserve percentages
            ("IVA al 22 percento", "iva 22%"),
        ]

        for input_query, expected_normalized in test_cases:
            result = normalizer.normalize(input_query)
            assert result.normalized_query == expected_normalized
            assert "iva_synonym_mapping" in result.applied_rules

    def test_irpef_variations_normalization(self, normalizer):
        """Test IRPEF variations are normalized correctly."""
        test_cases = [
            ("IRPEF calcolo", "irpef calcolo"),
            ("imposta reddito persone fisiche", "irpef"),
            ("I.R.P.E.F. 2025", "irpef 2025"),
            ("imposta sui redditi delle persone fisiche", "irpef"),
            ("IRPEF aliquote", "irpef aliquote"),
            ("calcolo IRPEF dipendenti", "calcolo irpef dipendenti"),
        ]

        for input_query, expected_normalized in test_cases:
            result = normalizer.normalize(input_query)
            assert result.normalized_query == expected_normalized

    def test_imu_variations_normalization(self, normalizer):
        """Test IMU variations are normalized correctly."""
        test_cases = [
            ("IMU prima casa", "imu prima casa"),
            ("imposta municipale unica", "imu"),
            ("I.M.U. 2025", "imu 2025"),
            ("IMU seconda casa", "imu seconda casa"),
            ("pagamento IMU", "pagamento imu"),
            ("scadenze IMU", "scadenze imu"),
        ]

        for input_query, expected_normalized in test_cases:
            result = normalizer.normalize(input_query)
            assert result.normalized_query == expected_normalized

    def test_tari_variations_normalization(self, normalizer):
        """Test TARI variations are normalized correctly."""
        test_cases = [
            ("TARI rifiuti", "tari rifiuti"),
            ("tassa rifiuti", "tari"),
            ("T.A.R.I. calcolo", "tari calcolo"),
            ("tassa sui rifiuti urbani", "tari"),
            ("TARI 2025", "tari 2025"),
        ]

        for input_query, expected_normalized in test_cases:
            result = normalizer.normalize(input_query)
            assert result.normalized_query == expected_normalized

    def test_fattura_variations_normalization(self, normalizer):
        """Test fattura variations are normalized correctly."""
        test_cases = [
            ("fattura elettronica", "fattura elettronica"),
            ("fatturazione B2B", "fattura b2b"),
            ("emissione fatture", "emissione fattura"),
            ("fatture in cloud", "fattura cloud"),
            ("fatturazione automatica", "fattura automatica"),
        ]

        for input_query, expected_normalized in test_cases:
            result = normalizer.normalize(input_query)
            assert result.normalized_query == expected_normalized

    def test_f24_variations_normalization(self, normalizer):
        """Test F24 variations are normalized correctly."""
        test_cases = [
            ("modello F24", "f24"),
            ("F 24 compilazione", "f24 compilazione"),
            ("f24 online", "f24 online"),
            ("F24 semplificato", "f24 semplificato"),
            ("pagamento con F24", "pagamento f24"),
        ]

        for input_query, expected_normalized in test_cases:
            result = normalizer.normalize(input_query)
            assert result.normalized_query == expected_normalized


class TestAccentedCharacterHandling:
    """Test handling of Italian accented characters."""

    @pytest.fixture
    def normalizer(self):
        return ItalianQueryNormalizer()

    def test_accent_normalization_preserves_meaning(self, normalizer):
        """Test accented characters are handled while preserving meaning."""
        test_cases = [
            ("società di capitali", "società capitali"),  # Keep meaningful accents
            ("attività commerciale", "attività commerciale"),
            ("più detrazioni", "più detrazioni"),
            ("perché pagare", "perché pagare"),
            ("così si calcola", "così calcola"),
            ("età pensionabile", "età pensionabile"),
        ]

        for input_query, expected_normalized in test_cases:
            result = normalizer.normalize(input_query)
            assert result.normalized_query == expected_normalized
            # Verify accents are preserved where linguistically important
            assert any(
                "à" in result.normalized_query
                or "è" in result.normalized_query
                or "ì" in result.normalized_query
                or "ò" in result.normalized_query
                or "ù" in result.normalized_query
                for _ in [None]
            )

    def test_accent_variations_normalization(self, normalizer):
        """Test different accent variations are normalized consistently."""
        test_cases = [
            # Same semantic meaning, different accent patterns
            ("societa", "società"),  # Missing accent should be added
            ("attivita", "attività"),
            ("piu", "più"),
            ("perche", "perché"),
            ("cosi", "così"),
        ]

        for input_query, expected_normalized in test_cases:
            result = normalizer.normalize(input_query)
            # Should normalize to the correct accented form
            assert (
                expected_normalized in result.normalized_query
                or result.normalized_query.replace(
                    expected_normalized.replace("à", "a")
                    .replace("è", "e")
                    .replace("ì", "i")
                    .replace("ò", "o")
                    .replace("ù", "u"),
                    expected_normalized,
                )
                == result.normalized_query
            )


class TestPluralSingularNormalization:
    """Test plural/singular normalization for Italian terms."""

    @pytest.fixture
    def normalizer(self):
        return ItalianQueryNormalizer()

    def test_common_tax_term_plural_normalization(self, normalizer):
        """Test common tax terms are normalized to singular form."""
        test_cases = [
            ("tasse sui redditi", "tassa redditi"),
            ("imposte dirette", "imposta diretta"),
            ("detrazioni fiscali", "detrazione fiscale"),
            ("deduzioni spese", "deduzione spesa"),
            ("fatture elettroniche", "fattura elettronica"),
            ("società di persone", "società persona"),  # Note: some exceptions
            ("aliquote IVA", "aliquota iva"),
            ("scadenze fiscali", "scadenza fiscale"),
            ("contributi previdenziali", "contributo previdenziale"),
            ("versamenti periodici", "versamento periodico"),
        ]

        for input_query, expected_normalized in test_cases:
            result = normalizer.normalize(input_query)
            assert result.normalized_query == expected_normalized
            assert "plural_to_singular" in result.applied_rules

    def test_irregular_plural_normalization(self, normalizer):
        """Test irregular Italian plurals are handled correctly."""
        test_cases = [
            ("uomini d'affari", "uomo affari"),  # uomini -> uomo
            ("mogli fiscalmente", "moglie fiscalmente"),  # mogli -> moglie
            ("importi dovuti", "importo dovuto"),  # importi -> importo
            ("casi particolari", "caso particolare"),  # casi -> caso
        ]

        for input_query, expected_normalized in test_cases:
            result = normalizer.normalize(input_query)
            assert result.normalized_query == expected_normalized

    def test_plural_preservation_when_needed(self, normalizer):
        """Test plurals are preserved when semantically important."""
        test_cases = [
            # Some terms should remain plural when they have specific meaning
            ("società di capitali", "società capitali"),  # "capitali" has specific meaning
            ("redditi diversi", "redditi diversi"),  # Tax category name
            ("beni strumentali", "beni strumentali"),  # Technical term
        ]

        for input_query, expected_normalized in test_cases:
            result = normalizer.normalize(input_query)
            assert result.normalized_query == expected_normalized


class TestSynonymMapping:
    """Test synonym mapping for Italian tax and legal terms."""

    @pytest.fixture
    def normalizer(self):
        return ItalianQueryNormalizer()

    def test_tax_synonym_mapping(self, normalizer):
        """Test various tax term synonyms are mapped correctly."""
        synonym_groups = {
            "iva": ["IVA", "imposta valore aggiunto", "i.v.a.", "Imposta sul Valore Aggiunto", "iva"],
            "irpef": [
                "IRPEF",
                "imposta reddito persone fisiche",
                "i.r.p.e.f.",
                "imposta sui redditi delle persone fisiche",
            ],
            "fattura": ["fattura", "fatturazione", "documento fiscale", "nota di addebito", "ricevuta fiscale"],
            "detrazione": [
                "detrazione",
                "sconto fiscale",
                "agevolazione fiscale",
                "beneficio fiscale",
                "riduzione imposta",
            ],
            "scadenza": ["scadenza", "termine", "data limite", "entro quando", "quando pagare", "quando versare"],
        }

        for canonical_form, synonyms in synonym_groups.items():
            for synonym in synonyms:
                result = normalizer.normalize(f"{synonym} calcolo")
                assert canonical_form in result.normalized_query
                assert "synonym_mapping" in result.applied_rules

    def test_regional_terminology_mapping(self, normalizer):
        """Test regional terminology variations are mapped to standard terms."""
        regional_mappings = {
            # Northern Italy variations
            ("contributo unificato", "contributo"),
            ("tassa di registro", "imposta registro"),
            # Southern Italy variations
            ("gabella", "tassa"),  # Old term still used in some regions
            ("tributo", "imposta"),
            # Formal vs informal terms
            ("versamento", "pagamento"),
            ("adempimento", "obbligo"),
            ("contribuente", "persona"),
        }

        for regional_term, standard_term in regional_mappings:
            result = normalizer.normalize(f"{regional_term} fiscale")
            assert standard_term in result.normalized_query


class TestAbbreviationExpansion:
    """Test abbreviation expansion for Italian tax terms."""

    @pytest.fixture
    def normalizer(self):
        return ItalianQueryNormalizer()

    def test_common_tax_abbreviations(self, normalizer):
        """Test common tax abbreviations are expanded appropriately."""
        abbreviations = {
            "CF": "codice fiscale",
            "P.IVA": "partita iva",
            "PIVA": "partita iva",
            "DPR": "decreto presidente repubblica",
            "DM": "decreto ministeriale",
            "DL": "decreto legge",
            "DLGS": "decreto legislativo",
            "TUIR": "testo unico imposte redditi",
            "CU": "certificazione unica",
            "DSU": "dichiarazione situazione unica",
            "ISEE": "indicatore situazione economica equivalente",
            "RED": "redditometro",
            "INPS": "istituto nazionale previdenza sociale",
            "INAIL": "istituto nazionale assicurazione infortuni",
        }

        for abbrev, expansion in abbreviations.items():
            # Test with period
            result = normalizer.normalize(f"{abbrev}. calcolo")
            assert any(word in result.normalized_query for word in expansion.split())

            # Test without period
            result = normalizer.normalize(f"{abbrev} calcolo")
            assert any(word in result.normalized_query for word in expansion.split())

    def test_contextual_abbreviation_expansion(self, normalizer):
        """Test abbreviations are expanded based on context."""
        contextual_cases = [
            ("art. 7 DPR", "articolo 7 decreto presidente repubblica"),
            ("comma 3 DL", "comma 3 decreto legge"),
            ("allegato B DM", "allegato b decreto ministeriale"),
            ("modifica TUIR", "modifica testo unico imposte redditi"),
        ]

        for input_query, expected_expansion in contextual_cases:
            result = normalizer.normalize(input_query)
            # Check that key expansion terms are present
            expansion_words = expected_expansion.split()
            assert any(word in result.normalized_query for word in expansion_words[-3:])


class TestQueryStructureNormalization:
    """Test normalization of query structure patterns."""

    @pytest.fixture
    def normalizer(self):
        return ItalianQueryNormalizer()

    def test_question_to_canonical_form(self, normalizer):
        """Test questions are normalized to canonical forms."""
        question_patterns = [
            ("Qual è l'aliquota IVA per i servizi?", "aliquota iva servizi"),
            ("Come si calcola l'IRPEF?", "calcolo irpef"),
            ("Quando si paga l'IMU?", "scadenza imu"),
            ("Dove si presenta la dichiarazione?", "presentazione dichiarazione"),
            ("Quanto costa la marca da bollo?", "costo marca bollo"),
            ("Chi deve pagare la TARI?", "soggetto tari"),
            ("Perché devo versare l'acconto?", "acconto versamento"),
            ("Cosa include la base imponibile?", "base imponibile elementi"),
        ]

        for question, expected_canonical in question_patterns:
            result = normalizer.normalize(question)
            assert result.normalized_query == expected_canonical
            assert "question_normalization" in result.applied_rules

    def test_imperative_to_canonical_form(self, normalizer):
        """Test imperative forms are normalized."""
        imperative_patterns = [
            ("Calcola l'IVA", "calcolo iva"),
            ("Dimmi l'aliquota IRPEF", "aliquota irpef"),
            ("Spiegami la detrazione", "detrazione spiegazione"),
            ("Mostrami il modello F24", "modello f24"),
            ("Aiutami con la dichiarazione", "assistenza dichiarazione"),
        ]

        for imperative, expected_canonical in imperative_patterns:
            result = normalizer.normalize(imperative)
            assert result.normalized_query == expected_canonical

    def test_complex_query_simplification(self, normalizer):
        """Test complex queries are simplified while preserving meaning."""
        complex_patterns = [
            (
                "Vorrei sapere qual è l'aliquota IVA applicabile ai servizi digitali prestati in regime B2B",
                "aliquota iva servizi digitali b2b",
            ),
            (
                "Mi puoi spiegare come funziona il calcolo dell'IRPEF per i dipendenti a tempo determinato?",
                "calcolo irpef dipendenti tempo determinato",
            ),
            (
                "È possibile avere informazioni sulle scadenze per il pagamento dell'IMU sulla seconda casa?",
                "scadenze pagamento imu seconda casa",
            ),
        ]

        for complex_query, expected_simple in complex_patterns:
            result = normalizer.normalize(complex_query)
            assert result.normalized_query == expected_simple
            assert "query_simplification" in result.applied_rules


class TestEntityPreservation:
    """Test preservation of important entities during normalization."""

    @pytest.fixture
    def normalizer(self):
        return ItalianQueryNormalizer()

    def test_numeric_preservation(self, normalizer):
        """Test numbers and percentages are preserved."""
        numeric_cases = [
            ("IVA al 22%", "iva 22%"),
            ("aliquota del 4 percento", "aliquota 4%"),
            ("importo di 1000 euro", "importo 1000 euro"),
            ("reddito superiore a 15000€", "reddito superiore 15000€"),
            ("scadenza 30 giugno 2025", "scadenza 30 giugno 2025"),
            ("articolo 7-bis comma 3", "articolo 7-bis comma 3"),
            ("DPR 633/72", "decreto presidente repubblica 633/72"),
        ]

        for input_query, expected_normalized in numeric_cases:
            result = normalizer.normalize(input_query)
            assert result.normalized_query == expected_normalized
            assert "entity_preservation" in result.applied_rules

    def test_date_preservation(self, normalizer):
        """Test dates are preserved and standardized."""
        date_cases = [
            ("scadenza 30/06/2025", "scadenza 30/06/2025"),
            ("dal 1° gennaio 2025", "dal 01/01/2025"),
            ("entro il 15 marzo", "entro 15/03"),
            ("anno fiscale 2024", "anno fiscale 2024"),
            ("trimestre 2025", "trimestre 2025"),
        ]

        for input_query, expected_normalized in date_cases:
            result = normalizer.normalize(input_query)
            assert result.normalized_query == expected_normalized

    def test_legal_reference_preservation(self, normalizer):
        """Test legal references are preserved in proper format."""
        legal_cases = [
            ("art. 7 DPR 633/72", "articolo 7 decreto presidente repubblica 633/72"),
            ("comma 3-bis L. 104/92", "comma 3-bis legge 104/92"),
            ("allegato A DM 15/03/2024", "allegato a decreto ministeriale 15/03/2024"),
            ("Circolare AE n. 15/E", "circolare agenzia entrate 15/e"),
        ]

        for input_query, expected_normalized in legal_cases:
            result = normalizer.normalize(input_query)
            assert result.normalized_query == expected_normalized

    def test_tax_code_preservation(self, normalizer):
        """Test Italian tax codes and fiscal identifiers are preserved."""
        tax_code_cases = [
            ("CF RSSMRA80A01H501X", "codice fiscale RSSMRA80A01H501X"),
            ("P.IVA 12345678901", "partita iva 12345678901"),
            ("codice tributo 1001", "codice tributo 1001"),
            ("codice ufficio T30", "codice ufficio T30"),
        ]

        for input_query, expected_normalized in tax_code_cases:
            result = normalizer.normalize(input_query)
            assert result.normalized_query == expected_normalized


class TestRegionalDialectHandling:
    """Test handling of regional dialects and variations."""

    @pytest.fixture
    def normalizer(self):
        return ItalianQueryNormalizer()

    def test_northern_italy_variations(self, normalizer):
        """Test Northern Italian terminology variations."""
        northern_cases = [
            ("bollo auto", "tassa automobilistica"),  # Lombardy
            ("multa", "sanzione"),  # Veneto
            ("acconto", "anticipo"),  # Piemonte
            ("saldo", "conguaglio"),  # Liguria
        ]

        for regional_term, standard_term in northern_cases:
            result = normalizer.normalize(f"{regional_term} calcolo")
            assert (
                standard_term in result.normalized_query or regional_term in result.normalized_query
            )  # Accept either form

    def test_southern_italy_variations(self, normalizer):
        """Test Southern Italian terminology variations."""
        southern_cases = [
            ("contributo", "imposta"),  # Sicily
            ("balzello", "tassa"),  # Calabria - archaic but still used
            ("gravame", "onere fiscale"),  # Puglia
            ("aggravio", "maggiorazione"),  # Campania
        ]

        for regional_term, standard_term in southern_cases:
            result = normalizer.normalize(f"{regional_term} fiscale")
            # Should normalize to standard terminology
            assert any(word in result.normalized_query for word in standard_term.split())

    def test_formal_vs_colloquial_terms(self, normalizer):
        """Test formal vs colloquial term normalization."""
        formal_colloquial_pairs = [
            ("contribuente", "persona"),  # Formal -> simpler
            ("adempimento", "obbligo"),
            ("versamento", "pagamento"),
            ("erogazione", "pagamento"),
            ("liquidazione", "calcolo"),
            ("accertamento", "controllo"),
        ]

        for formal_term, colloquial_term in formal_colloquial_pairs:
            # Both should normalize to the same canonical form
            formal_result = normalizer.normalize(f"{formal_term} fiscale")
            colloquial_result = normalizer.normalize(f"{colloquial_term} fiscale")

            # Extract the key normalized terms
            formal_key_terms = set(formal_result.normalized_query.split())
            colloquial_key_terms = set(colloquial_result.normalized_query.split())

            # Should have significant overlap in key terms
            overlap = formal_key_terms.intersection(colloquial_key_terms)
            assert len(overlap) >= 1  # At least one common term


class TestPerformanceRequirements:
    """Test performance requirements (<10ms normalization)."""

    @pytest.fixture
    def normalizer(self):
        return ItalianQueryNormalizer()

    def test_single_query_performance(self, normalizer):
        """Test single query normalization completes within 10ms."""
        test_query = "Qual è l'aliquota IVA applicabile ai servizi digitali in regime B2B?"

        start_time = time.perf_counter()
        result = normalizer.normalize(test_query)
        end_time = time.perf_counter()

        processing_time_ms = (end_time - start_time) * 1000

        assert processing_time_ms < 10.0, f"Normalization took {processing_time_ms:.2f}ms, should be <10ms"
        assert result.processing_time_ms < 10.0
        assert result.normalized_query is not None

    def test_batch_query_performance(self, normalizer):
        """Test batch normalization performance."""
        test_queries = [
            "Come si calcola l'IRPEF per i dipendenti?",
            "Qual è la scadenza dell'IMU 2025?",
            "Quando si paga la TARI?",
            "IVA sui servizi digitali B2B",
            "Detrazione spese mediche 730",
            "F24 online compilazione",
            "Società di capitali tassazione",
            "Fattura elettronica obbligatoria",
            "Codice fiscale verifica",
            "Partita IVA apertura",
        ] * 10  # 100 queries total

        start_time = time.perf_counter()
        results = [normalizer.normalize(query) for query in test_queries]
        end_time = time.perf_counter()

        total_time_ms = (end_time - start_time) * 1000
        avg_time_per_query = total_time_ms / len(test_queries)

        assert avg_time_per_query < 10.0, f"Average time {avg_time_per_query:.2f}ms > 10ms"
        assert all(r.processing_time_ms < 15.0 for r in results), "Some queries exceeded 15ms"
        assert len(results) == len(test_queries)

    def test_memory_efficiency(self, normalizer):
        """Test memory usage is reasonable for large-scale operations."""
        import sys

        # Test with 1000 different queries
        base_queries = [
            "IVA calcolo",
            "IRPEF aliquote",
            "IMU scadenze",
            "TARI pagamento",
            "F24 compilazione",
            "730 detrazioni",
            "fattura elettronica",
            "codice fiscale",
            "partita iva",
            "dichiarazione redditi",
        ]

        # Generate variations
        test_queries = []
        for base in base_queries:
            for i in range(100):
                test_queries.append(f"{base} {i}")

        # Measure memory before
        initial_size = sys.getsizeof(normalizer)

        # Process all queries
        results = [normalizer.normalize(query) for query in test_queries]

        # Memory should not grow excessively
        final_size = sys.getsizeof(normalizer)
        memory_growth = final_size - initial_size

        assert memory_growth < 1024 * 1024, f"Memory grew by {memory_growth} bytes"  # <1MB growth
        assert len(results) == 1000


class TestCacheKeyGeneration:
    """Test cache key generation consistency and effectiveness."""

    @pytest.fixture
    def normalizer(self):
        return ItalianQueryNormalizer()

    def test_identical_semantic_queries_same_cache_key(self, normalizer):
        """Test semantically identical queries generate same cache key."""
        semantically_identical_groups = [
            [
                "Qual è l'aliquota IVA per i servizi digitali?",
                "qual'è l'iva per servizi digitali",
                "Che percentuale di IVA si applica ai servizi digitali?",
                "iva servizi digitali aliquota",
                "servizi digitali: quale IVA?",
            ],
            [
                "Come si calcola l'IRPEF?",
                "calcolo IRPEF come fare",
                "IRPEF: come si calcola?",
                "metodo calcolo IRPEF",
                "come calcolare imposta reddito persone fisiche",
            ],
            [
                "Quando si paga l'IMU?",
                "scadenza IMU quando",
                "IMU: quando pagare?",
                "data scadenza imposta municipale unica",
                "quando versare IMU",
            ],
        ]

        for group in semantically_identical_groups:
            cache_keys = set()
            normalized_queries = set()

            for query in group:
                result = normalizer.normalize(query)
                cache_key = normalizer.generate_cache_key(result.normalized_query)

                cache_keys.add(cache_key)
                normalized_queries.add(result.normalized_query)

            # All should generate the same cache key
            assert len(cache_keys) == 1, f"Expected 1 unique cache key, got {len(cache_keys)}: {cache_keys}"

            # Should also have same or very similar normalized queries
            assert len(normalized_queries) <= 2, f"Too much variation in normalized queries: {normalized_queries}"

    def test_different_semantic_queries_different_cache_keys(self, normalizer):
        """Test semantically different queries generate different cache keys."""
        different_queries = [
            "aliquota IVA servizi digitali",
            "calcolo IRPEF dipendenti",
            "scadenza IMU 2025",
            "pagamento TARI rifiuti",
            "compilazione F24 online",
            "detrazione spese mediche",
            "fattura elettronica B2B",
            "partita IVA apertura",
            "codice fiscale verifica",
            "dichiarazione redditi 730",
        ]

        cache_keys = set()
        for query in different_queries:
            result = normalizer.normalize(query)
            cache_key = normalizer.generate_cache_key(result.normalized_query)
            cache_keys.add(cache_key)

        # Should generate different cache keys
        assert len(cache_keys) == len(
            different_queries
        ), f"Expected {len(different_queries)} unique keys, got {len(cache_keys)}"

    def test_cache_key_stability(self, normalizer):
        """Test cache keys are stable across multiple calls."""
        test_query = "Qual è l'aliquota IVA per i servizi digitali B2B?"

        cache_keys = []
        for _ in range(10):
            result = normalizer.normalize(test_query)
            cache_key = normalizer.generate_cache_key(result.normalized_query)
            cache_keys.append(cache_key)

        # All cache keys should be identical
        assert len(set(cache_keys)) == 1, f"Cache key not stable: {set(cache_keys)}"

    def test_cache_key_format_validity(self, normalizer):
        """Test cache keys have valid format."""
        test_queries = ["IVA calcolo servizi", "IRPEF aliquote 2025", "IMU prima casa", "F24 online pagamento"]

        for query in test_queries:
            result = normalizer.normalize(query)
            cache_key = normalizer.generate_cache_key(result.normalized_query)

            # Cache key should be a valid string
            assert isinstance(cache_key, str)
            assert len(cache_key) > 0

            # Should be reasonably short for efficiency
            assert len(cache_key) < 200, f"Cache key too long: {len(cache_key)} chars"

            # Should not contain problematic characters
            assert not any(char in cache_key for char in ["\n", "\r", "\t", "\0"])

    def test_semantic_hashing_effectiveness(self, normalizer):
        """Test semantic hashing groups similar queries effectively."""
        # Queries that should hash to similar/same values
        similar_query_pairs = [
            ("IVA 22% servizi", "servizi IVA 22%"),  # Word order
            ("calcolo IRPEF", "IRPEF calcolo"),
            ("fattura elettronica", "fatturazione elettronica"),
            ("pagamento IMU", "versamento IMU"),
        ]

        for query1, query2 in similar_query_pairs:
            result1 = normalizer.normalize(query1)
            result2 = normalizer.normalize(query2)

            cache_key1 = normalizer.generate_cache_key(result1.normalized_query)
            cache_key2 = normalizer.generate_cache_key(result2.normalized_query)

            # Should generate same cache key for semantically similar queries
            assert cache_key1 == cache_key2, f"Similar queries should have same cache key: '{query1}' vs '{query2}'"


class TestIntegrationWithExistingSystems:
    """Test integration with existing cache and search systems."""

    @pytest.fixture
    def normalizer(self):
        return ItalianQueryNormalizer()

    def test_cache_service_integration(self, normalizer):
        """Test integration with existing cache service."""
        with patch("app.services.cache.cache_service") as mock_cache:
            mock_cache.get.return_value = None
            mock_cache.set.return_value = True

            # Simulate cache lookup with normalized query
            test_query = "Qual è l'aliquota IVA?"
            result = normalizer.normalize(test_query)
            cache_key = normalizer.generate_cache_key(result.normalized_query)

            # Should be able to use the cache key
            assert isinstance(cache_key, str)
            assert len(cache_key) > 0

            # Verify normalization result contains required fields
            assert hasattr(result, "normalized_query")
            assert hasattr(result, "applied_rules")
            assert hasattr(result, "processing_time_ms")

    def test_search_service_integration(self, normalizer):
        """Test integration with PostgreSQL FTS search service."""
        # Mock the search service
        with patch("app.services.search_service.SearchService") as MockSearchService:
            mock_search = MockSearchService.return_value
            mock_search.search.return_value = []

            test_query = "fatturazione elettronica B2B"
            result = normalizer.normalize(test_query)

            # Normalized query should be suitable for FTS
            assert result.normalized_query is not None
            assert len(result.normalized_query.strip()) > 0

            # Should not contain problematic characters for SQL
            problematic_chars = ["'", '"', ";", "--", "/*", "*/"]
            assert not any(char in result.normalized_query for char in problematic_chars)

    def test_api_endpoint_integration(self, normalizer):
        """Test integration with API endpoints."""
        # Test that normalization result can be serialized
        test_query = "Come calcolare l'IRPEF 2025?"
        result = normalizer.normalize(test_query)

        # Should be JSON serializable
        import json

        serialized = json.dumps(
            {
                "original_query": test_query,
                "normalized_query": result.normalized_query,
                "applied_rules": result.applied_rules,
                "processing_time_ms": result.processing_time_ms,
            }
        )

        assert isinstance(serialized, str)

        # Should be deserializable
        deserialized = json.loads(serialized)
        assert deserialized["normalized_query"] == result.normalized_query


@pytest.fixture
def db_session():
    """Database session fixture for testing."""
    # This will be implemented when the actual models are created
    pass


class TestNormalizationLogging:
    """Test normalization logging and analytics."""

    def test_normalization_stats_tracking(self, db_session):
        """Test normalization statistics are tracked correctly."""
        # This test will verify that normalization patterns are logged
        # for continuous improvement and cache hit analysis
        pass

    def test_cache_hit_improvement_measurement(self, db_session):
        """Test measurement of cache hit rate improvement."""
        # This test will verify the system can measure the improvement
        # in cache hit rates due to normalization
        pass


class TestCostOptimizationImpact:
    """Test the cost optimization impact of normalization."""

    def test_estimated_cost_reduction(self):
        """Test estimated cost reduction from improved cache hits."""
        # Before normalization: 4 different cache keys
        pre_normalization_queries = [
            "Qual è l'aliquota IVA per i servizi digitali?",
            "qual'è l'iva per servizi digitali",
            "Che percentuale di IVA si applica ai servizi digitali?",
            "iva servizi digitali aliquota",
        ]

        # After normalization: should be 1 cache key
        normalizer = ItalianQueryNormalizer()

        cache_keys = set()
        for query in pre_normalization_queries:
            result = normalizer.normalize(query)
            cache_key = normalizer.generate_cache_key(result.normalized_query)
            cache_keys.add(cache_key)

        # Should consolidate to 1 cache entry
        assert len(cache_keys) == 1

        # This represents 75% cost reduction for these queries
        cost_reduction_percentage = (
            (len(pre_normalization_queries) - len(cache_keys)) / len(pre_normalization_queries) * 100
        )
        assert cost_reduction_percentage == 75.0

    def test_faq_system_foundation(self):
        """Test that normalization provides foundation for FAQ system."""
        normalizer = ItalianQueryNormalizer()

        # Common tax questions should normalize to consistent patterns
        faq_candidate_queries = [
            "Come si calcola l'IVA?",
            "Calcolo IVA come fare",
            "IVA: metodo di calcolo",
            "Come calcolare imposta valore aggiunto",
        ]

        normalized_forms = []
        for query in faq_candidate_queries:
            result = normalizer.normalize(query)
            normalized_forms.append(result.normalized_query)

        # Should identify common patterns suitable for FAQ responses
        unique_patterns = set(normalized_forms)
        assert len(unique_patterns) <= 2  # Should consolidate to 1-2 patterns max

        # The most common pattern should be suitable for an FAQ entry
        assert "calcolo iva" in normalized_forms[0] or "iva calcolo" in normalized_forms[0]
