"""
Test suite for Domain-Action Classification System.

Tests all 35 sample queries across different Italian professional domains
to ensure accurate classification with >80% confidence.
"""

import asyncio
from typing import List, Tuple

import pytest

from app.services.domain_action_classifier import Action, Domain, DomainActionClassification, DomainActionClassifier


class TestDomainActionClassifier:
    """Test suite for domain-action classification"""

    @pytest.fixture(scope="class")
    def classifier(self):
        """Create classifier instance for tests"""
        return DomainActionClassifier()

    @pytest.fixture(scope="class")
    def test_cases(self) -> list[tuple[str, Domain, Action, str, str]]:
        """
        Test cases with expected results.
        Format: (query, expected_domain, expected_action, expected_sub_domain, expected_doc_type)
        """
        return [
            # TAX DOMAIN TESTS
            (
                "Scrivi un atto di pignoramento verso terzi ex art. 543 c.p.c.",
                Domain.LEGAL,
                Action.DOCUMENT_GENERATION,
                "civile",
                "atto",
            ),
            ("Posso dedurre il costo dell'amministratore?", Domain.TAX, Action.COMPLIANCE_CHECK, "ires", None),
            ("Calcola l'IRPEF su 50.000 euro", Domain.TAX, Action.CALCULATION_REQUEST, "irpef", None),
            ("Cos'è il reverse charge IVA?", Domain.TAX, Action.INFORMATION_REQUEST, "iva", None),
            (
                "Analizza questa fattura elettronica",
                Domain.ACCOUNTING,
                Action.DOCUMENT_ANALYSIS,
                "registrazioni",
                None,
            ),
            (
                "Conviene il regime forfettario per un consulente?",
                Domain.TAX,
                Action.STRATEGIC_ADVICE,
                "forfettario",
                None,
            ),
            # LEGAL DOMAIN TESTS
            (
                "Redigi una citazione per danni da inadempimento contrattuale",
                Domain.LEGAL,
                Action.DOCUMENT_GENERATION,
                "civile",
                "citazione",
            ),
            (
                "È legale licenziare per giustificato motivo oggettivo?",
                Domain.LABOR,
                Action.COMPLIANCE_CHECK,
                "licenziamento",
                None,
            ),
            (
                "Prepara un ricorso al TAR contro diniego autorizzazione",
                Domain.LEGAL,
                Action.DOCUMENT_GENERATION,
                "amministrativo",
                "ricorso",
            ),
            (
                "Esamina questo contratto di locazione commerciale",
                Domain.LEGAL,
                Action.DOCUMENT_ANALYSIS,
                "civile",
                None,
            ),
            ("Cosa prevede l'art. 2043 del Codice Civile?", Domain.LEGAL, Action.INFORMATION_REQUEST, "civile", None),
            ("È meglio transigere o proseguire il giudizio?", Domain.LEGAL, Action.STRATEGIC_ADVICE, "civile", None),
            # LABOR DOMAIN TESTS
            ("Compila un F24 per contributi INPS artigiani", Domain.TAX, Action.DOCUMENT_GENERATION, None, "f24"),
            (
                "Calcola il TFR maturato in 5 anni con stipendio 30.000",
                Domain.LABOR,
                Action.CALCULATION_REQUEST,
                "subordinato",
                None,
            ),
            (
                "Verifica la correttezza di questa busta paga",
                Domain.LABOR,
                Action.DOCUMENT_ANALYSIS,
                "subordinato",
                None,
            ),
            ("Che CCNL si applica ai metalmeccanici?", Domain.LABOR, Action.INFORMATION_REQUEST, "ccnl", None),
            ("Devo dare preavviso per le dimissioni?", Domain.LABOR, Action.COMPLIANCE_CHECK, "subordinato", None),
            (
                "Conviene assumere con contratto determinato o indeterminato?",
                Domain.LABOR,
                Action.STRATEGIC_ADVICE,
                "subordinato",
                None,
            ),
            # BUSINESS DOMAIN TESTS
            (
                "Scrivi lo statuto per una SRL innovativa",
                Domain.BUSINESS,
                Action.DOCUMENT_GENERATION,
                "costituzione",
                "contratto",
            ),
            ("Quanto costa costituire una SPA?", Domain.BUSINESS, Action.CALCULATION_REQUEST, "costituzione", None),
            ("Analizza questo bilancio consolidato", Domain.ACCOUNTING, Action.DOCUMENT_ANALYSIS, "bilancio", None),
            (
                "Come funziona la fusione per incorporazione?",
                Domain.BUSINESS,
                Action.INFORMATION_REQUEST,
                "straordinaria",
                None,
            ),
            (
                "Posso distribuire utili con patrimonio netto negativo?",
                Domain.BUSINESS,
                Action.COMPLIANCE_CHECK,
                "governance",
                None,
            ),
            (
                "È meglio aumentare il capitale o chiedere un finanziamento?",
                Domain.BUSINESS,
                Action.STRATEGIC_ADVICE,
                "finanziamento",
                None,
            ),
            # ACCOUNTING DOMAIN TESTS
            (
                "Prepara la nota integrativa secondo OIC 12",
                Domain.ACCOUNTING,
                Action.DOCUMENT_GENERATION,
                "bilancio",
                "dichiarazione",
            ),
            (
                "Calcola l'ammortamento di un impianto da 100.000 euro",
                Domain.ACCOUNTING,
                Action.CALCULATION_REQUEST,
                "principi",
                None,
            ),
            (
                "Controlla la quadratura di questo stato patrimoniale",
                Domain.ACCOUNTING,
                Action.DOCUMENT_ANALYSIS,
                "bilancio",
                None,
            ),
            ("Cosa sono i principi contabili OIC?", Domain.ACCOUNTING, Action.INFORMATION_REQUEST, "principi", None),
            (
                "Devo iscrivere i costi di ricerca nell'attivo?",
                Domain.ACCOUNTING,
                Action.COMPLIANCE_CHECK,
                "principi",
                None,
            ),
            (
                "Conviene la rivalutazione dei beni strumentali?",
                Domain.ACCOUNTING,
                Action.STRATEGIC_ADVICE,
                "bilancio",
                None,
            ),
            # MIXED/COMPLEX TESTS
            (
                "Scrivi una lettera di diffida per mancato pagamento fatture",
                Domain.LEGAL,
                Action.DOCUMENT_GENERATION,
                "civile",
                "lettera",
            ),
            ("Calcola sanzioni e interessi per ravvedimento F24", Domain.TAX, Action.CALCULATION_REQUEST, "iva", None),
            (
                "È obbligatorio nominare il sindaco nella SRL?",
                Domain.BUSINESS,
                Action.COMPLIANCE_CHECK,
                "governance",
                None,
            ),
            (
                "Come si contabilizza un leasing finanziario?",
                Domain.ACCOUNTING,
                Action.INFORMATION_REQUEST,
                "principi",
                None,
            ),
            (
                "Analizza la convenienza fiscale di questa operazione straordinaria",
                Domain.TAX,
                Action.STRATEGIC_ADVICE,
                "ires",
                None,
            ),
            # EDGE CASES
            ("Help me with tax calculation", Domain.TAX, Action.CALCULATION_REQUEST, None, None),  # English input
            ("Ciao, come stai?", Domain.TAX, Action.INFORMATION_REQUEST, None, None),  # Generic greeting
        ]

    @pytest.mark.asyncio
    async def test_individual_classifications(self, classifier, test_cases):
        """Test each query individually for correct classification"""

        failed_tests = []

        for i, (query, expected_domain, expected_action, _expected_sub, _expected_doc) in enumerate(test_cases):
            try:
                result = await classifier.classify(query)

                # Check domain and action
                domain_correct = result.domain == expected_domain
                action_correct = result.action == expected_action
                confidence_ok = result.confidence >= 0.6  # Minimum confidence threshold

                # Log detailed results
                print(f"\nTest {i + 1}: {query[:50]}...")
                print(f"  Expected: {expected_domain.value} + {expected_action.value}")
                print(f"  Got: {result.domain.value} + {result.action.value}")
                print(f"  Confidence: {result.confidence:.3f}")
                print(f"  Sub-domain: {result.sub_domain}")
                print(f"  Doc-type: {result.document_type}")
                print(f"  Fallback used: {result.fallback_used}")

                if not (domain_correct and action_correct and confidence_ok):
                    failed_tests.append(
                        {
                            "query": query,
                            "expected": f"{expected_domain.value}+{expected_action.value}",
                            "actual": f"{result.domain.value}+{result.action.value}",
                            "confidence": result.confidence,
                            "issues": {
                                "domain_wrong": not domain_correct,
                                "action_wrong": not action_correct,
                                "low_confidence": not confidence_ok,
                            },
                        }
                    )

            except Exception as e:
                failed_tests.append(
                    {"query": query, "error": str(e), "expected": f"{expected_domain.value}+{expected_action.value}"}
                )

        # Report results
        total_tests = len(test_cases)
        passed_tests = total_tests - len(failed_tests)
        success_rate = (passed_tests / total_tests) * 100

        print("\n=== CLASSIFICATION TEST RESULTS ===")
        print(f"Total tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {len(failed_tests)}")
        print(f"Success rate: {success_rate:.1f}%")

        if failed_tests:
            print("\nFAILED TESTS:")
            for i, failure in enumerate(failed_tests):
                print(f"{i + 1}. {failure['query'][:50]}...")
                if "error" in failure:
                    print(f"   ERROR: {failure['error']}")
                else:
                    print(f"   Expected: {failure['expected']}")
                    print(f"   Actual: {failure['actual']}")
                    print(f"   Confidence: {failure.get('confidence', 'N/A')}")
                    print(f"   Issues: {failure.get('issues', {})}")

        # Assert minimum success rate
        assert success_rate >= 80.0, f"Success rate {success_rate:.1f}% is below required 80%"

    @pytest.mark.asyncio
    async def test_confidence_scores(self, classifier, test_cases):
        """Test that confidence scores are reasonable for different query types"""

        confidence_stats = {
            "high_confidence": [],  # >0.8
            "medium_confidence": [],  # 0.6-0.8
            "low_confidence": [],  # <0.6
        }

        for query, _expected_domain, _expected_action, _, _ in test_cases:
            result = await classifier.classify(query)

            if result.confidence >= 0.8:
                confidence_stats["high_confidence"].append(result)
            elif result.confidence >= 0.6:
                confidence_stats["medium_confidence"].append(result)
            else:
                confidence_stats["low_confidence"].append(result)

        total = len(test_cases)
        high_pct = len(confidence_stats["high_confidence"]) / total * 100
        medium_pct = len(confidence_stats["medium_confidence"]) / total * 100
        low_pct = len(confidence_stats["low_confidence"]) / total * 100

        print("\n=== CONFIDENCE DISTRIBUTION ===")
        print(f"High confidence (>0.8): {high_pct:.1f}%")
        print(f"Medium confidence (0.6-0.8): {medium_pct:.1f}%")
        print(f"Low confidence (<0.6): {low_pct:.1f}%")

        # Should have at least 60% high confidence classifications
        assert high_pct >= 60.0, f"Only {high_pct:.1f}% high confidence, expected >=60%"

        # Should have less than 15% low confidence
        assert low_pct <= 15.0, f"Too many low confidence: {low_pct:.1f}%, expected <=15%"

    @pytest.mark.asyncio
    async def test_sub_domain_extraction(self, classifier):
        """Test sub-domain extraction for specific queries"""

        sub_domain_tests = [
            ("Calcola l'IVA al 22%", "iva"),
            ("Regime forfettario 15%", "forfettario"),
            ("Contributi INPS artigiani", "contributi"),
            ("Ricorso al TAR", "amministrativo"),
            ("Fusione per incorporazione", "straordinaria"),
            ("Principi contabili OIC", "principi"),
        ]

        for query, expected_sub in sub_domain_tests:
            result = await classifier.classify(query)
            print(f"Query: {query}")
            print(f"Expected sub-domain: {expected_sub}")
            print(f"Actual sub-domain: {result.sub_domain}")
            print(f"Domain: {result.domain.value}, Action: {result.action.value}")
            print("---")

            # Sub-domain should be detected for these specific cases
            if expected_sub:
                assert result.sub_domain is not None, f"Sub-domain not detected for: {query}"

    @pytest.mark.asyncio
    async def test_document_type_extraction(self, classifier):
        """Test document type extraction for document generation requests"""

        doc_type_tests = [
            ("Scrivi una citazione", "citazione"),
            ("Redigi un contratto", "contratto"),
            ("Prepara un ricorso", "ricorso"),
            ("Compila una lettera di diffida", "lettera"),
            ("Formula una procura", "procura"),
        ]

        for query, expected_doc_type in doc_type_tests:
            result = await classifier.classify(query)
            print(f"Query: {query}")
            print(f"Expected doc-type: {expected_doc_type}")
            print(f"Actual doc-type: {result.document_type}")
            print(f"Action: {result.action.value}")
            print("---")

            # Should be classified as document generation
            assert result.action == Action.DOCUMENT_GENERATION, f"Not classified as doc generation: {query}"

            # Document type should be detected
            assert result.document_type is not None, f"Document type not detected for: {query}"

    @pytest.mark.asyncio
    async def test_performance(self, classifier):
        """Test classification performance (should be <100ms per classification)"""

        test_queries = [
            "Calcola l'IRPEF su 50000 euro",
            "Scrivi un ricorso al TAR",
            "È legale questa clausola contrattuale?",
            "Analizza questo bilancio",
            "Conviene il regime forfettario?",
        ]

        import time

        total_time = 0

        for query in test_queries:
            start_time = time.time()
            await classifier.classify(query)
            end_time = time.time()

            query_time = (end_time - start_time) * 1000  # Convert to ms
            total_time += query_time

            print(f"Query: {query[:30]}... -> {query_time:.1f}ms")

            # Each classification should be under 100ms
            assert query_time < 100, f"Classification too slow: {query_time:.1f}ms > 100ms"

        avg_time = total_time / len(test_queries)
        print(f"\nAverage classification time: {avg_time:.1f}ms")

        # Average should be well under 50ms for rule-based classification
        assert avg_time < 50, f"Average classification time too high: {avg_time:.1f}ms"

    def test_classification_stats(self, classifier):
        """Test that classification statistics are available and reasonable"""

        stats = classifier.get_classification_stats()

        assert "domains" in stats
        assert "actions" in stats

        # Should have all 5 domains
        assert len(stats["domains"]) == 5

        # Should have all 6 actions
        assert len(stats["actions"]) == 6

        # Each domain should have keywords
        for domain_name, domain_info in stats["domains"].items():
            assert domain_info["keywords_count"] > 0, f"No keywords for domain: {domain_name}"

        print("\n=== CLASSIFICATION STATS ===")
        print(f"Domains: {list(stats['domains'].keys())}")
        print(f"Actions: {list(stats['actions'].keys())}")

        for domain, info in stats["domains"].items():
            print(f"{domain}: {info['keywords_count']} keywords, {len(info['sub_domains'])} sub-domains")


if __name__ == "__main__":
    # Run specific test manually
    async def main():
        classifier = DomainActionClassifier()

        # Test a few key examples
        test_queries = [
            "Scrivi un atto di pignoramento verso terzi ex art. 543 c.p.c.",
            "Posso dedurre il costo dell'amministratore?",
            "Calcola l'IRPEF su 50.000 euro",
            "Conviene il regime forfettario per un consulente?",
        ]

        print("=== MANUAL TEST RESULTS ===")
        for query in test_queries:
            result = await classifier.classify(query)
            print(f"\nQuery: {query}")
            print(f"Domain: {result.domain.value}")
            print(f"Action: {result.action.value}")
            print(f"Confidence: {result.confidence:.3f}")
            print(f"Sub-domain: {result.sub_domain}")
            print(f"Doc-type: {result.document_type}")
            print(f"Reasoning: {result.reasoning}")

    asyncio.run(main())
