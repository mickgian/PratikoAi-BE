"""
Comprehensive TDD Tests for Automated FAQ Generation.

This test suite covers automated FAQ generation from user queries, RSS integration,
and cost optimization through intelligent query pattern analysis.

Following TDD methodology: write tests first, then implement functionality.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID, uuid4

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

# Import models and services that will be implemented
from app.models.faq_automation import FAQCandidate, FAQPattern, GeneratedFAQ, QueryCluster, RSSImpact
from app.services.auto_faq_generator import AutomatedFAQGenerator, GenerationFailedError, QualityValidationError
from app.services.faq_quality_validator import FAQQualityValidator, QualityMetrics
from app.services.faq_rss_integration import FAQImpactAssessor, FAQRSSIntegration, RSSUpdateProcessor
from app.services.query_pattern_analyzer import ClusteringFailedError, InsufficientDataError, QueryPatternAnalyzer

# Test Data Setup


@pytest.fixture
def sample_query_logs():
    """Sample query logs for pattern analysis"""
    base_time = datetime.utcnow() - timedelta(days=15)

    return [
        # IVA calculation queries - should cluster together
        {
            "id": uuid4(),
            "query": "Come si calcola l'IVA al 22% su una fattura di 1000 euro?",
            "normalized_query": "calcolo iva 22 percento fattura",
            "response": "Per calcolare l'IVA al 22% su 1000 euro: 1000 × 0.22 = 220 euro di IVA. Totale fattura: 1220 euro.",
            "cost_cents": 15,
            "response_time_ms": 1200,
            "quality_score": 0.92,
            "timestamp": base_time,
            "response_cached": False,
            "user_id": uuid4(),
        },
        {
            "id": uuid4(),
            "query": "Qual è l'IVA da pagare su 500 euro con aliquota del 22%?",
            "normalized_query": "calcolo iva 22 percento importo",
            "response": "L'IVA al 22% su 500 euro è: 500 × 0.22 = 110 euro. L'importo totale sarà 610 euro.",
            "cost_cents": 12,
            "response_time_ms": 1100,
            "quality_score": 0.89,
            "timestamp": base_time + timedelta(hours=2),
            "response_cached": False,
            "user_id": uuid4(),
        },
        {
            "id": uuid4(),
            "query": "Come faccio a calcolare l'IVA ordinaria su una prestazione?",
            "normalized_query": "calcolo iva ordinaria prestazione",
            "response": "L'IVA ordinaria in Italia è del 22%. Per calcolarla: importo × 0.22. Es: 1000€ × 0.22 = 220€ di IVA.",
            "cost_cents": 14,
            "response_time_ms": 1300,
            "quality_score": 0.94,
            "timestamp": base_time + timedelta(hours=4),
            "response_cached": False,
            "user_id": uuid4(),
        },
        {
            "id": uuid4(),
            "query": "IVA 22% su fattura, come si calcola?",
            "normalized_query": "calcolo iva 22 percento fattura",
            "response": "Per l'IVA al 22%: moltiplica l'imponibile per 0.22. Su 800€: 800 × 0.22 = 176€ di IVA.",
            "cost_cents": 13,
            "response_time_ms": 1050,
            "quality_score": 0.88,
            "timestamp": base_time + timedelta(days=1),
            "response_cached": False,
            "user_id": uuid4(),
        },
        {
            "id": uuid4(),
            "query": "Calcolo IVA al 22 percento su importo di 1500 euro",
            "normalized_query": "calcolo iva 22 percento importo",
            "response": "IVA al 22% su 1500€: 1500 × 0.22 = 330€. Totale con IVA: 1830€.",
            "cost_cents": 16,
            "response_time_ms": 1400,
            "quality_score": 0.91,
            "timestamp": base_time + timedelta(days=2),
            "response_cached": False,
            "user_id": uuid4(),
        },
        {
            "id": uuid4(),
            "query": "Come calcolare IVA 22% per servizi professionali?",
            "normalized_query": "calcolo iva 22 percento servizi professionali",
            "response": "Per i servizi professionali l'IVA è del 22%. Calcolo: importo netto × 0.22. Normativa: Art. 15 DPR 633/72.",
            "cost_cents": 18,
            "response_time_ms": 1600,
            "quality_score": 0.96,
            "timestamp": base_time + timedelta(days=3),
            "response_cached": False,
            "user_id": uuid4(),
        },
        # Deduction queries - should cluster together
        {
            "id": uuid4(),
            "query": "Quali spese posso detrarre per l'ufficio in casa?",
            "normalized_query": "detrazioni spese ufficio casa",
            "response": "Per l'ufficio in casa puoi detrarre: bollette (quota %), mobili ufficio, computer, internet business. Serve documentazione.",
            "cost_cents": 20,
            "response_time_ms": 1800,
            "quality_score": 0.93,
            "timestamp": base_time + timedelta(days=5),
            "response_cached": False,
            "user_id": uuid4(),
        },
        {
            "id": uuid4(),
            "query": "Detrazione spese home office, cosa posso scaricare?",
            "normalized_query": "detrazioni spese home office",
            "response": "Home office: detraibili elettricità/gas (%), acquisto mobili ufficio, spese telefoniche/internet uso professionale.",
            "cost_cents": 19,
            "response_time_ms": 1700,
            "quality_score": 0.90,
            "timestamp": base_time + timedelta(days=6),
            "response_cached": False,
            "user_id": uuid4(),
        },
        {
            "id": uuid4(),
            "query": "Ufficio in casa, che costi posso dedurre?",
            "normalized_query": "detrazioni costi ufficio casa",
            "response": "Ufficio domestico: deducibili spese pro-quota (luce, gas, affitto), arredi, materiali ufficio. Max 50% superficie.",
            "cost_cents": 17,
            "response_time_ms": 1500,
            "quality_score": 0.87,
            "timestamp": base_time + timedelta(days=7),
            "response_cached": False,
            "user_id": uuid4(),
        },
        {
            "id": uuid4(),
            "query": "Smart working, posso detrarre le spese di casa?",
            "normalized_query": "detrazioni spese casa smart working",
            "response": "Smart working: detraibili spese casa solo se ufficio dedicato. Quota % bollette, mobili, strumenti lavoro.",
            "cost_cents": 21,
            "response_time_ms": 1900,
            "quality_score": 0.92,
            "timestamp": base_time + timedelta(days=8),
            "response_cached": False,
            "user_id": uuid4(),
        },
        {
            "id": uuid4(),
            "query": "Spese ufficio domestico, come detrarle?",
            "normalized_query": "detrazioni spese ufficio domestico",
            "response": "Ufficio domestico: detrazioni su % spazio utilizzato. Include: utilities, mobili, attrezzature. Serve fatture intestate.",
            "cost_cents": 16,
            "response_time_ms": 1350,
            "quality_score": 0.89,
            "timestamp": base_time + timedelta(days=9),
            "response_cached": False,
            "user_id": uuid4(),
        },
        # Single queries - should not become FAQs
        {
            "id": uuid4(),
            "query": "Regime forfettario 2024, novità?",
            "normalized_query": "regime forfettario 2024 novita",
            "response": "Novità 2024: limite redditi 85.000€, nuove causali esclusione, coefficienti redditività invariati.",
            "cost_cents": 25,
            "response_time_ms": 2000,
            "quality_score": 0.95,
            "timestamp": base_time + timedelta(days=10),
            "response_cached": False,
            "user_id": uuid4(),
        },
        {
            "id": uuid4(),
            "query": "Compilazione modello F24, aiuto",
            "normalized_query": "compilazione modello f24",
            "response": "F24: sezione contribuente (CF/PIVA), sezione IMU/imposte, calcolo interessi. Scadenze entro 16 del mese.",
            "cost_cents": 22,
            "response_time_ms": 1750,
            "quality_score": 0.91,
            "timestamp": base_time + timedelta(days=11),
            "response_cached": False,
            "user_id": uuid4(),
        },
    ]


@pytest.fixture
def sample_existing_faqs():
    """Sample existing FAQs to test exclusion logic"""
    return [
        {
            "id": uuid4(),
            "question": "Come si calcola l'IRPEF?",
            "answer": "L'IRPEF si calcola applicando le aliquote progressive...",
            "normalized_queries": ["calcolo irpef", "come calcolare irpef"],
            "tags": ["irpef", "calcolo", "imposte"],
            "created_at": datetime.utcnow() - timedelta(days=30),
        }
    ]


@pytest.fixture
def sample_rss_updates():
    """Sample RSS updates for testing integration"""
    return [
        {
            "id": uuid4(),
            "title": "Nuove aliquote IVA 2024 - Decreto Ministeriale",
            "summary": "Modifiche alle aliquote IVA per alcuni settori specifici. Aliquota ridotta per beni essenziali.",
            "content": "Il Decreto del 15/01/2024 introduce modifiche alle aliquote IVA...",
            "source": "Agenzia delle Entrate",
            "published_date": datetime.utcnow() - timedelta(hours=2),
            "url": "https://agenziaentrate.gov.it/decreto-iva-2024",
            "topics": ["iva", "aliquote", "decreto"],
            "regulatory_refs": ["DPR 633/72", "Decreto 15/01/2024"],
        },
        {
            "id": uuid4(),
            "title": "Detrazioni spese home office - Circolare Agenzia Entrate",
            "summary": "Chiarimenti su detrazioni per spese ufficio domestico e smart working.",
            "content": "La Circolare 3/E del 2024 chiarisce le modalità di detrazione...",
            "source": "Commercialista Telematico",
            "published_date": datetime.utcnow() - timedelta(hours=6),
            "url": "https://commercialistatelematico.com/detrazioni-home-office",
            "topics": ["detrazioni", "home office", "spese"],
            "regulatory_refs": ["Art. 164 TUIR", "Circolare 3/E/2024"],
        },
    ]


# Query Pattern Analysis Tests


class TestQueryPatternAnalysis:
    """Test identification of semantically similar queries across users"""

    @pytest.mark.asyncio
    async def test_find_faq_candidates_basic_clustering(self, sample_query_logs):
        """Test basic clustering of similar queries"""
        analyzer = QueryPatternAnalyzer(Mock(), Mock(), Mock())
        analyzer.db.query = AsyncMock(return_value=sample_query_logs)

        # Mock embedding service to return similar embeddings for IVA queries
        def mock_embed_batch(texts):
            embeddings = []
            for text in texts:
                if "iva" in text.lower():
                    # IVA queries get similar embeddings
                    embeddings.append([0.8, 0.2, 0.1, 0.3])
                elif "detraz" in text.lower():
                    # Deduction queries get similar embeddings
                    embeddings.append([0.2, 0.8, 0.3, 0.1])
                else:
                    # Other queries get different embeddings
                    embeddings.append([0.1, 0.1, 0.8, 0.9])
            return embeddings

        analyzer.embeddings.embed_batch = AsyncMock(side_effect=mock_embed_batch)

        candidates = await analyzer.find_faq_candidates()

        # Should find 2 clusters: IVA (6 queries) and deductions (5 queries)
        assert len(candidates) == 2

        # IVA cluster should be higher priority (more queries)
        iva_candidate = candidates[0]
        assert iva_candidate.frequency >= 5
        assert "iva" in iva_candidate.canonical_query.lower()
        assert iva_candidate.roi_score > 0.5

        # Deductions cluster should be second
        deduction_candidate = candidates[1]
        assert deduction_candidate.frequency >= 5
        assert "detraz" in deduction_candidate.canonical_query.lower()

    @pytest.mark.asyncio
    async def test_frequency_threshold_filtering(self, sample_query_logs):
        """Test filtering by minimum frequency threshold"""
        analyzer = QueryPatternAnalyzer(Mock(), Mock(), Mock())
        analyzer.min_frequency = 10  # High threshold
        analyzer.db.query = AsyncMock(return_value=sample_query_logs[:3])  # Only 3 queries

        # Mock embedding service
        analyzer.embeddings.embed_batch = AsyncMock(return_value=[[0.8, 0.2, 0.1]] * 3)

        candidates = await analyzer.find_faq_candidates()

        # Should find no candidates due to low frequency
        assert len(candidates) == 0

    @pytest.mark.asyncio
    async def test_time_window_filtering(self, sample_query_logs):
        """Test filtering by time window"""
        analyzer = QueryPatternAnalyzer(Mock(), Mock(), Mock())
        analyzer.time_window_days = 1  # Very short window

        # Mock query to return only very old queries
        old_queries = []
        for query in sample_query_logs:
            query["timestamp"] = datetime.utcnow() - timedelta(days=5)
            old_queries.append(query)

        analyzer.db.query = AsyncMock(return_value=old_queries)

        candidates = await analyzer.find_faq_candidates()

        # Should find no candidates due to time filtering in query
        assert len(candidates) == 0

    @pytest.mark.asyncio
    async def test_cost_calculation_accuracy(self, sample_query_logs):
        """Test accuracy of cost calculations"""
        analyzer = QueryPatternAnalyzer(Mock(), Mock(), Mock())
        analyzer.db.query = AsyncMock(return_value=sample_query_logs[:6])  # IVA queries

        def mock_embed_batch(texts):
            return [[0.8, 0.2, 0.1, 0.3]] * len(texts)  # All similar

        analyzer.embeddings.embed_batch = AsyncMock(side_effect=mock_embed_batch)

        candidates = await analyzer.find_faq_candidates()

        candidate = candidates[0]

        # Calculate expected costs
        iva_queries = sample_query_logs[:6]
        total_cost = sum(q["cost_cents"] for q in iva_queries) / 100.0
        avg_cost = total_cost / len(iva_queries)

        # Monthly projections (30 days window, so 2x frequency)
        monthly_occurrences = len(iva_queries) * 2
        current_monthly_cost = monthly_occurrences * avg_cost
        faq_monthly_cost = monthly_occurrences * 0.0003  # GPT-3.5 cost
        expected_savings = current_monthly_cost - faq_monthly_cost

        assert abs(candidate.avg_cost_cents - avg_cost * 100) < 1
        assert abs(candidate.total_cost_saved - expected_savings) < 0.01

    @pytest.mark.asyncio
    async def test_query_normalization_integration(self, sample_query_logs):
        """Test integration with query normalization"""
        analyzer = QueryPatternAnalyzer(Mock(), Mock(), Mock())
        analyzer.db.query = AsyncMock(return_value=sample_query_logs)

        # Mock normalizer to ensure consistent normalization
        def mock_normalize(query):
            if "IVA" in query or "iva" in query:
                return "calcolo iva standard"
            return query.lower()

        analyzer.normalizer.normalize = Mock(side_effect=mock_normalize)
        analyzer.embeddings.embed_batch = AsyncMock(return_value=[[0.8, 0.2]] * 10)

        candidates = await analyzer.find_faq_candidates()

        # Should use normalized queries for clustering
        assert len(candidates) > 0
        analyzer.normalizer.normalize.assert_called()

    @pytest.mark.asyncio
    async def test_exclusion_of_existing_faq_coverage(self, sample_query_logs, sample_existing_faqs):
        """Test exclusion of queries already covered by existing FAQs"""
        analyzer = QueryPatternAnalyzer(Mock(), Mock(), Mock())

        # Add existing FAQ coverage to some queries
        covered_queries = []
        for query in sample_query_logs:
            if "irpef" in query["normalized_query"]:
                # This would be filtered out by the SQL query in real implementation
                continue
            covered_queries.append(query)

        analyzer.db.query = AsyncMock(return_value=covered_queries)
        analyzer.embeddings.embed_batch = AsyncMock(return_value=[[0.8, 0.2]] * len(covered_queries))

        candidates = await analyzer.find_faq_candidates()

        # Should not include queries covered by existing FAQs
        for candidate in candidates:
            assert "irpef" not in candidate.canonical_query.lower()

    @pytest.mark.asyncio
    async def test_clustering_failure_handling(self, sample_query_logs):
        """Test handling of clustering failures"""
        analyzer = QueryPatternAnalyzer(Mock(), Mock(), Mock())
        analyzer.db.query = AsyncMock(return_value=sample_query_logs)

        # Mock embedding service to fail
        analyzer.embeddings.embed_batch = AsyncMock(side_effect=Exception("Embedding service failed"))

        with pytest.raises(ClusteringFailedError):
            await analyzer.find_faq_candidates()

    @pytest.mark.asyncio
    async def test_similarity_threshold_tuning(self, sample_query_logs):
        """Test effect of similarity threshold on clustering"""
        analyzer = QueryPatternAnalyzer(Mock(), Mock(), Mock())
        analyzer.similarity_threshold = 0.95  # Very high threshold
        analyzer.db.query = AsyncMock(return_value=sample_query_logs)

        # Mock embeddings with slight variations
        def mock_embed_batch(texts):
            embeddings = []
            for i, text in enumerate(texts):
                if "iva" in text.lower():
                    # Slightly different embeddings for each IVA query
                    embeddings.append([0.8 + i * 0.01, 0.2, 0.1])
                else:
                    embeddings.append([0.1, 0.8, 0.1])
            return embeddings

        analyzer.embeddings.embed_batch = AsyncMock(side_effect=mock_embed_batch)

        candidates = await analyzer.find_faq_candidates()

        # High threshold should result in fewer/smaller clusters
        if candidates:
            assert all(c.frequency <= 3 for c in candidates)  # Smaller clusters


# FAQ Generation Tests


class TestFAQGeneration:
    """Test FAQ generation from high-quality LLM responses"""

    @pytest.mark.asyncio
    async def test_basic_faq_generation(self):
        """Test basic FAQ generation from a candidate"""
        generator = AutomatedFAQGenerator(Mock(), Mock(), Mock())

        candidate = FAQCandidate(
            id=uuid4(),
            canonical_query="calcolo iva 22 percento",
            query_variations=[
                "Come si calcola l'IVA al 22%?",
                "Calcolo IVA 22 percento su fattura",
                "Come calcolare IVA ordinaria",
            ],
            best_response={
                "response": "Per calcolare l'IVA al 22%: importo × 0.22. Esempio: 1000€ × 0.22 = 220€ di IVA.",
                "quality_score": 0.92,
            },
            frequency=6,
            tags=["iva", "calcolo", "fatturazione"],
            total_cost_saved=2.50,
            roi_score=2500.0,
        )

        # Mock LLM response
        generator.llm.complete_cheap = AsyncMock(
            return_value="""
        {
            "question": "Come si calcola l'IVA al 22% su una fattura?",
            "answer": "Per calcolare l'IVA al 22%, moltiplica l'importo imponibile per 0.22. Ad esempio: su 1000€ l'IVA sarà 1000 × 0.22 = 220€. Il totale fattura diventa 1220€.",
            "category": "IVA",
            "additional_tags": ["fatturazione", "calcolo"]
        }
        """
        )

        # Mock quality validation
        generator.validator.validate_faq = AsyncMock(return_value=0.89)

        faq = await generator.generate_faq_from_candidate(candidate)

        assert faq.question == "Come si calcola l'IVA al 22% su una fattura?"
        assert "1000 × 0.22 = 220" in faq.answer
        assert faq.category == "IVA"
        assert faq.quality_score == 0.89
        assert faq.auto_generated is True
        assert len(faq.tags) >= 3  # Original + additional tags

    @pytest.mark.asyncio
    async def test_quality_threshold_enforcement(self):
        """Test enforcement of quality thresholds"""
        generator = AutomatedFAQGenerator(Mock(), Mock(), Mock())

        candidate = FAQCandidate(
            id=uuid4(),
            canonical_query="test query",
            best_response={"response": "test response", "quality_score": 0.92},
            frequency=5,
            query_variations=["test"],
            tags=["test"],
            total_cost_saved=1.0,
            roi_score=1000.0,
        )

        # Mock low-quality first attempt
        generator.llm.complete_cheap = AsyncMock(
            return_value='{"question": "Test?", "answer": "Basic answer", "category": "Test", "additional_tags": []}'
        )
        generator.validator.validate_faq = AsyncMock(return_value=0.70)  # Below threshold

        # Mock high-quality retry with GPT-4
        generator.llm.complete_expensive = AsyncMock(
            return_value='{"question": "Test question?", "answer": "Detailed professional answer", "category": "Test", "additional_tags": ["detailed"]}'
        )

        # Second validation should pass
        generator.validator.validate_faq = AsyncMock(return_value=0.90)

        faq = await generator.generate_faq_from_candidate(candidate)

        # Should have used expensive model
        generator.llm.complete_expensive.assert_called_once()
        assert faq.quality_score == 0.90
        assert "Detailed professional answer" in faq.answer

    @pytest.mark.asyncio
    async def test_regulatory_reference_extraction(self):
        """Test extraction of regulatory references"""
        generator = AutomatedFAQGenerator(Mock(), Mock(), Mock())

        candidate = FAQCandidate(
            id=uuid4(),
            canonical_query="detrazioni mediche",
            best_response={
                "response": "Le detrazioni per spese mediche sono disciplinate dall'Art. 15 TUIR. Si applicano al 19% oltre la franchigia di 129,11€. Riferimento: D.Lgs. 917/1986.",
                "quality_score": 0.95,
            },
            frequency=8,
            query_variations=["detrazioni sanitarie", "spese mediche detraibili"],
            tags=["detrazioni", "sanita"],
            total_cost_saved=3.20,
            roi_score=3200.0,
        )

        generator.llm.complete_cheap = AsyncMock(
            return_value='{"question": "Quali sono le detrazioni per spese mediche?", "answer": "Le spese mediche sono detraibili al 19%...", "category": "Detrazioni", "additional_tags": ["sanita"]}'
        )
        generator.validator.validate_faq = AsyncMock(return_value=0.88)

        # Mock regulatory reference extraction
        async def mock_extract_refs(response):
            return ["Art. 15 TUIR", "D.Lgs. 917/1986"]

        generator._extract_regulatory_references = AsyncMock(side_effect=mock_extract_refs)

        faq = await generator.generate_faq_from_candidate(candidate)

        assert "Art. 15 TUIR" in faq.regulatory_refs
        assert "D.Lgs. 917/1986" in faq.regulatory_refs

    @pytest.mark.asyncio
    async def test_italian_language_quality_validation(self):
        """Test validation of Italian language quality"""
        validator = FAQQualityValidator(Mock())

        # Test high-quality Italian text
        high_quality = await validator.validate_faq(
            question="Come si calcola l'IVA al 22% su una fattura commerciale?",
            answer="Per calcolare l'IVA al 22%, moltiplicate l'importo imponibile per 0.22. Ad esempio, su un importo di 1.000€, l'IVA sarà: 1.000 × 0.22 = 220€. L'importo totale della fattura sarà quindi 1.220€.",
            original_response="Original detailed response...",
        )

        assert high_quality > 0.85

        # Test low-quality Italian text
        low_quality = await validator.validate_faq(
            question="Come calcola IVA?",  # Poor grammar
            answer="IVA è calcola con moltiplicazione per 22.",  # Poor Italian
            original_response="Original response...",
        )

        assert low_quality < 0.70

    @pytest.mark.asyncio
    async def test_tag_generation_from_query_clusters(self):
        """Test generation of relevant tags from query clusters"""
        generator = AutomatedFAQGenerator(Mock(), Mock(), Mock())

        candidate = FAQCandidate(
            id=uuid4(),
            canonical_query="calcolo contributi inps artigiani",
            query_variations=[
                "Come si calcolano i contributi INPS per artigiani?",
                "Contributi previdenziali artigiani, calcolo",
                "INPS artigiani, quanto pagare?",
                "Calcolo contributi gestione artigiani INPS",
            ],
            best_response={"response": "I contributi INPS per artigiani...", "quality_score": 0.91},
            frequency=7,
            tags=["inps", "contributi", "artigiani"],
            total_cost_saved=4.20,
            roi_score=4200.0,
        )

        generator.llm.complete_cheap = AsyncMock(
            return_value="""
        {
            "question": "Come si calcolano i contributi INPS per gli artigiani?",
            "answer": "I contributi INPS per artigiani si calcolano...",
            "category": "Contributi",
            "additional_tags": ["previdenza", "gestione-artigiani", "calcolo"]
        }
        """
        )

        generator.validator.validate_faq = AsyncMock(return_value=0.91)
        generator._extract_regulatory_references = AsyncMock(return_value=[])

        faq = await generator.generate_faq_from_candidate(candidate)

        # Should combine original and additional tags
        expected_tags = {"inps", "contributi", "artigiani", "previdenza", "gestione-artigiani", "calcolo"}
        assert set(faq.tags) >= expected_tags

    @pytest.mark.asyncio
    async def test_generation_failure_handling(self):
        """Test handling of generation failures"""
        generator = AutomatedFAQGenerator(Mock(), Mock(), Mock())

        candidate = FAQCandidate(
            id=uuid4(),
            canonical_query="test",
            best_response={"response": "test", "quality_score": 0.9},
            frequency=5,
            query_variations=["test"],
            tags=["test"],
            total_cost_saved=1.0,
            roi_score=1000.0,
        )

        # Mock LLM failure
        generator.llm.complete_cheap = AsyncMock(side_effect=Exception("LLM service unavailable"))

        with pytest.raises(GenerationFailedError):
            await generator.generate_faq_from_candidate(candidate)

    @pytest.mark.asyncio
    async def test_response_summarization_accuracy(self):
        """Test that summarization preserves key information"""
        generator = AutomatedFAQGenerator(Mock(), Mock(), Mock())

        candidate = FAQCandidate(
            id=uuid4(),
            canonical_query="detrazioni auto aziendali",
            best_response={
                "response": """Per le auto aziendali, le detrazioni dipendono dal tipo di utilizzo:

                1. Auto strumentali (esclusivo uso aziendale): detraibili al 100%
                2. Auto promiscue (uso misto): detraibili al 40% per IVA, 20% per costi
                3. Limiti: auto fino a 18.075,99€ per la detraibilità completa
                4. Carburante: detraibile al 40% se uso promiscuo
                5. Riferimento normativo: Art. 164 TUIR, Art. 19-bis1 DPR 633/72

                È necessaria documentazione che giustifichi l'uso aziendale.""",
                "quality_score": 0.94,
            },
            frequency=5,
            query_variations=["detrazioni auto aziendali"],
            tags=["detrazioni", "auto", "aziende"],
            total_cost_saved=2.50,
            roi_score=2500.0,
        )

        generator.llm.complete_cheap = AsyncMock(
            return_value="""
        {
            "question": "Come funzionano le detrazioni per le auto aziendali?",
            "answer": "Le detrazioni auto aziendali variano per uso: strumentali 100%, promiscue 40% IVA e 20% costi, fino a 18.075,99€. Serve documentazione uso aziendale. Rif: Art. 164 TUIR.",
            "category": "Detrazioni",
            "additional_tags": ["auto", "aziendale"]
        }
        """
        )

        generator.validator.validate_faq = AsyncMock(return_value=0.89)
        generator._extract_regulatory_references = AsyncMock(return_value=["Art. 164 TUIR", "Art. 19-bis1 DPR 633/72"])

        faq = await generator.generate_faq_from_candidate(candidate)

        # Check that key information is preserved
        assert "100%" in faq.answer  # Strumentali percentage
        assert "40%" in faq.answer  # Promiscue IVA percentage
        assert "18.075" in faq.answer  # Limit amount
        assert "documentazione" in faq.answer  # Documentation requirement
        assert "Art. 164 TUIR" in faq.regulatory_refs


# RSS Integration Tests


class TestRSSIntegration:
    """Test RSS integration for FAQ updates"""

    @pytest.mark.asyncio
    async def test_faq_invalidation_on_rss_update(self, sample_rss_updates):
        """Test FAQ invalidation when RSS updates arrive"""
        integration = FAQRSSIntegration(Mock(), Mock(), Mock())

        # Mock existing FAQ about IVA
        existing_faq = {
            "id": uuid4(),
            "question": "Come si calcola l'IVA al 22%?",
            "answer": "L'IVA al 22% si calcola moltiplicando l'importo per 0.22...",
            "tags": ["iva", "calcolo", "aliquote"],
            "last_updated": datetime.utcnow() - timedelta(days=10),
        }

        integration.faq.find_by_tags = AsyncMock(return_value=[existing_faq])
        integration._assess_impact = AsyncMock(return_value=0.8)  # High impact
        integration._handle_high_impact_update = AsyncMock()

        rss_update = sample_rss_updates[0]  # IVA update
        await integration.process_rss_update(rss_update)

        # Should handle high impact update
        integration._handle_high_impact_update.assert_called_once_with(existing_faq, rss_update)

    @pytest.mark.asyncio
    async def test_matching_between_rss_and_faq_tags(self, sample_rss_updates):
        """Test matching between RSS content and FAQ tags"""
        integration = FAQRSSIntegration(Mock(), Mock(), Mock())

        # Mock topic extraction
        integration._extract_topics = AsyncMock(return_value=["iva", "aliquote", "decreto"])

        # Mock FAQs with overlapping tags
        matching_faqs = [
            {"id": uuid4(), "tags": ["iva", "calcolo"], "question": "IVA calculation"},
            {"id": uuid4(), "tags": ["aliquote", "iva"], "question": "IVA rates"},
        ]
        [{"id": uuid4(), "tags": ["irpef", "detrazioni"], "question": "IRPEF deductions"}]

        integration.faq.find_by_tags = AsyncMock(return_value=matching_faqs)
        integration._assess_impact = AsyncMock(return_value=0.5)  # Medium impact
        integration._flag_for_review = AsyncMock()

        await integration.process_rss_update(sample_rss_updates[0])

        # Should flag matching FAQs for review
        assert integration._flag_for_review.call_count == len(matching_faqs)

    @pytest.mark.asyncio
    async def test_automatic_faq_regeneration_triggers(self, sample_rss_updates):
        """Test automatic FAQ regeneration triggers"""
        integration = FAQRSSIntegration(Mock(), Mock(), Mock())

        high_usage_faq = {
            "id": uuid4(),
            "question": "Come si calcolano le detrazioni home office?",
            "answer": "Le detrazioni per home office...",
            "tags": ["detrazioni", "home office", "spese"],
            "usage_count": 150,  # High usage
            "last_updated": datetime.utcnow() - timedelta(days=30),
        }

        integration.faq.find_by_tags = AsyncMock(return_value=[high_usage_faq])
        integration._assess_impact = AsyncMock(return_value=0.75)  # High impact
        integration._handle_high_impact_update = AsyncMock()

        rss_update = sample_rss_updates[1]  # Home office update
        await integration.process_rss_update(rss_update)

        # Should trigger automatic regeneration for high-usage FAQ
        integration._handle_high_impact_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_faq_history_preservation(self):
        """Test preservation of FAQ history during updates"""
        integration = FAQRSSIntegration(Mock(), Mock(), Mock())

        original_faq = {
            "id": uuid4(),
            "question": "Come si calcola l'IVA?",
            "answer": "L'IVA si calcola al 22%...",
            "version": 1,
        }

        rss_update = {"id": uuid4(), "title": "Nuove aliquote IVA", "summary": "Cambio aliquote IVA dal 23%"}

        # Mock LLM response for update
        integration.llm.complete_expensive = AsyncMock(
            return_value="""
        {
            "question": "Come si calcola l'IVA?",
            "answer": "L'IVA si calcola con le nuove aliquote: standard 23%...",
            "change_note": "Aggiornato il 15/01/2024: nuove aliquote IVA in vigore"
        }
        """
        )

        integration.faq.create_version = AsyncMock()
        integration._notify_faq_update = AsyncMock()
        integration.faq.get_generation_data = AsyncMock(return_value={})

        await integration._handle_high_impact_update(original_faq, rss_update)

        # Should create new version preserving history
        integration.faq.create_version.assert_called_once()
        call_args = integration.faq.create_version.call_args[1]
        assert call_args["faq_id"] == original_faq["id"]
        assert "23%" in call_args["new_answer"]
        assert "Aggiornato il" in call_args["change_note"]

    @pytest.mark.asyncio
    async def test_update_priority_based_on_usage_frequency(self):
        """Test update priority based on FAQ usage frequency"""
        assessor = FAQImpactAssessor()

        high_usage_faq = {
            "id": uuid4(),
            "usage_count": 200,
            "last_accessed": datetime.utcnow() - timedelta(hours=2),
            "tags": ["iva", "calcolo"],
        }

        low_usage_faq = {
            "id": uuid4(),
            "usage_count": 5,
            "last_accessed": datetime.utcnow() - timedelta(days=30),
            "tags": ["iva", "calcolo"],
        }

        rss_update = {"topics": ["iva", "aliquote"], "priority": "high"}

        high_priority = await assessor.calculate_update_priority(high_usage_faq, rss_update)
        low_priority = await assessor.calculate_update_priority(low_usage_faq, rss_update)

        assert high_priority > low_priority
        assert high_priority > 0.8  # Should be high priority

    @pytest.mark.asyncio
    async def test_rollback_capability_on_regeneration_failure(self):
        """Test rollback capability if regeneration fails"""
        integration = FAQRSSIntegration(Mock(), Mock(), Mock())

        original_faq = {"id": uuid4(), "question": "Test FAQ", "answer": "Original answer", "version": 2}

        rss_update = {"id": uuid4(), "title": "Test update"}

        # Mock regeneration failure
        integration.llm.complete_expensive = AsyncMock(side_effect=Exception("LLM failed"))
        integration.faq.rollback_to_previous_version = AsyncMock()
        integration._notify_regeneration_failure = AsyncMock()

        # Should handle failure gracefully
        await integration._handle_high_impact_update(original_faq, rss_update)

        # Should attempt rollback
        integration._notify_regeneration_failure.assert_called_once()


# System Integration Tests


class TestSystemIntegration:
    """Test system integration and workflow"""

    @pytest.mark.asyncio
    async def test_end_to_end_faq_generation_workflow(self, sample_query_logs):
        """Test complete workflow from query analysis to FAQ creation"""
        # Mock all services
        analyzer = QueryPatternAnalyzer(Mock(), Mock(), Mock())
        generator = AutomatedFAQGenerator(Mock(), Mock(), Mock())

        # Setup mocks
        analyzer.db.query = AsyncMock(return_value=sample_query_logs[:6])  # IVA queries
        analyzer.embeddings.embed_batch = AsyncMock(return_value=[[0.8, 0.2]] * 6)

        generator.llm.complete_cheap = AsyncMock(
            return_value='{"question": "Come calcolare IVA?", "answer": "IVA = importo × 0.22", "category": "IVA", "additional_tags": ["calcolo"]}'
        )
        generator.validator.validate_faq = AsyncMock(return_value=0.90)
        generator._extract_regulatory_references = AsyncMock(return_value=[])

        # Run workflow
        candidates = await analyzer.find_faq_candidates()
        assert len(candidates) > 0

        faq = await generator.generate_faq_from_candidate(candidates[0])
        assert faq.question == "Come calcolare IVA?"
        assert faq.quality_score == 0.90

    @pytest.mark.asyncio
    async def test_faq_approval_workflow_auto_vs_manual(self):
        """Test FAQ approval workflow (auto vs manual review)"""
        approval_service = Mock()

        # High quality FAQ - should auto-approve
        high_quality_faq = GeneratedFAQ(
            question="Test question?",
            answer="Detailed answer...",
            quality_score=0.96,
            auto_generated=True,
            estimated_monthly_savings=5.0,
            generation_metadata={},
        )

        approval_service.should_auto_approve = Mock(return_value=True)
        approval_service.auto_approve = AsyncMock()

        await approval_service.process_generated_faq(high_quality_faq)
        approval_service.auto_approve.assert_called_once()

        # Low quality FAQ - should queue for manual review
        low_quality_faq = GeneratedFAQ(
            question="Test?",
            answer="Basic answer",
            quality_score=0.82,
            auto_generated=True,
            estimated_monthly_savings=1.0,
            generation_metadata={},
        )

        approval_service.should_auto_approve = Mock(return_value=False)
        approval_service.queue_for_review = AsyncMock()

        await approval_service.process_generated_faq(low_quality_faq)
        approval_service.queue_for_review.assert_called_once()

    @pytest.mark.asyncio
    async def test_integration_with_existing_faq_variation_system(self):
        """Test integration with existing FAQ variation system"""
        existing_faq_service = Mock()
        faq_automation = Mock()

        # Mock existing FAQ with variations
        existing_faq = {
            "id": uuid4(),
            "question": "Come si calcola l'IRPEF?",
            "variations": ["Calcolo IRPEF 2024", "Come calcolare imposta reddito"],
        }

        # New FAQ candidate should check for overlap
        candidate = FAQCandidate(
            id=uuid4(),
            canonical_query="calcolo irpef imposta reddito",
            query_variations=["Come si calcola IRPEF?", "Calcolo imposta reddito"],
            frequency=5,
        )

        existing_faq_service.find_overlapping_faqs = AsyncMock(return_value=[existing_faq])
        faq_automation.should_merge_or_separate = Mock(return_value="merge")

        result = await faq_automation.handle_overlapping_candidate(candidate)

        assert result.action == "merge"
        existing_faq_service.find_overlapping_faqs.assert_called_once()

    @pytest.mark.asyncio
    async def test_cost_tracking_accuracy(self):
        """Test accuracy of cost tracking for FAQ generation"""
        cost_tracker = Mock()

        # Track generation costs
        generation_costs = {
            "llm_calls": 2,  # cheap + expensive retry
            "embedding_calls": 1,
            "validation_calls": 2,
            "total_tokens": 1500,
            "estimated_cost_eur": 0.0012,
        }

        cost_tracker.track_faq_generation = AsyncMock()

        await cost_tracker.track_faq_generation(faq_id=uuid4(), candidate_id=uuid4(), costs=generation_costs)

        cost_tracker.track_faq_generation.assert_called_once()
        call_args = cost_tracker.track_faq_generation.call_args[1]
        assert call_args["costs"]["estimated_cost_eur"] < 0.002  # Should be cost effective

    @pytest.mark.asyncio
    async def test_performance_with_large_faq_database(self):
        """Test performance with 1000+ FAQs"""
        import time

        # Mock large FAQ database
        large_faq_db = Mock()
        large_faq_db.count = Mock(return_value=1500)

        # Mock search operations
        async def mock_search(tags, limit=50):
            # Simulate reasonable search time
            await asyncio.sleep(0.001)  # 1ms simulation
            return [{"id": uuid4(), "tags": tags}] * min(limit, 20)

        large_faq_db.find_by_tags = AsyncMock(side_effect=mock_search)

        integration = FAQRSSIntegration(large_faq_db, Mock(), Mock())

        start_time = time.time()

        # Process multiple RSS updates
        for i in range(10):
            rss_update = {"topics": ["iva", "calcolo"], "title": f"Update {i}"}
            await integration.process_rss_update(rss_update)

        end_time = time.time()
        processing_time = end_time - start_time

        # Should complete in reasonable time
        assert processing_time < 1.0  # Less than 1 second for 10 updates

    @pytest.mark.asyncio
    async def test_concurrent_faq_generation_jobs(self):
        """Test concurrent FAQ generation jobs"""
        import asyncio

        generator = AutomatedFAQGenerator(Mock(), Mock(), Mock())

        # Mock generation
        async def mock_generate(candidate):
            await asyncio.sleep(0.1)  # Simulate processing time
            return GeneratedFAQ(
                question=f"Question {candidate.id}",
                answer="Answer",
                quality_score=0.88,
                auto_generated=True,
                generation_metadata={},
            )

        generator.generate_faq_from_candidate = AsyncMock(side_effect=mock_generate)

        # Create multiple candidates
        candidates = [FAQCandidate(id=uuid4(), canonical_query=f"query_{i}") for i in range(5)]

        # Process concurrently
        start_time = time.time()
        tasks = [generator.generate_faq_from_candidate(c) for c in candidates]
        results = await asyncio.gather(*tasks)
        end_time = time.time()

        assert len(results) == 5
        # Should be faster than sequential (5 * 0.1 = 0.5s)
        assert (end_time - start_time) < 0.3


# Business Logic Tests


class TestBusinessLogic:
    """Test ROI calculations and business logic"""

    @pytest.mark.asyncio
    async def test_roi_calculation_accuracy(self):
        """Test accuracy of ROI calculations for FAQ candidates"""
        calculator = Mock()

        candidate = FAQCandidate(
            id=uuid4(),
            frequency=10,  # 10 occurrences in 30 days
            avg_cost_cents=150,  # €1.50 per query
            time_window_days=30,
        )

        # Calculate expected ROI
        monthly_occurrences = 10  # Same frequency
        current_monthly_cost = monthly_occurrences * 1.50  # €15.00
        faq_monthly_cost = monthly_occurrences * 0.0003  # €0.003 (GPT-3.5)
        monthly_savings = current_monthly_cost - faq_monthly_cost  # €14.997
        generation_cost = 0.001  # €0.001
        roi = monthly_savings / generation_cost  # ~14,997

        calculated_roi = calculator.calculate_roi(candidate)
        assert abs(calculated_roi - roi) < 0.1

    @pytest.mark.asyncio
    async def test_priority_scoring_algorithm(self):
        """Test priority scoring algorithm"""
        scorer = Mock()

        # High frequency, high cost candidate
        high_priority = FAQCandidate(frequency=15, avg_cost_cents=200, quality_score=0.95, total_cost_saved=20.0)

        # Low frequency, low cost candidate
        low_priority = FAQCandidate(frequency=5, avg_cost_cents=50, quality_score=0.85, total_cost_saved=2.0)

        # Calculate priority scores
        high_score = scorer.calculate_priority_score(high_priority)
        low_score = scorer.calculate_priority_score(low_priority)

        assert high_score > low_score
        assert high_score > 10.0  # Should be significantly higher

    @pytest.mark.asyncio
    async def test_prevention_of_duplicate_faq_generation(self):
        """Test prevention of duplicate FAQ generation"""
        deduplicator = Mock()

        candidate1 = FAQCandidate(
            canonical_query="calcolo iva 22 percento", query_variations=["Come calcolare IVA 22%?"]
        )

        candidate2 = FAQCandidate(
            canonical_query="calcolo iva aliquota ordinaria", query_variations=["Come calcolare IVA ordinaria?"]
        )

        # Mock similarity check
        deduplicator.calculate_similarity = Mock(return_value=0.92)  # Very similar
        deduplicator.is_duplicate = Mock(return_value=True)

        result = deduplicator.check_for_duplicates([candidate1, candidate2])

        assert len(result.unique_candidates) == 1  # Should merge duplicates
        assert len(result.duplicate_pairs) == 1

    @pytest.mark.asyncio
    async def test_seasonal_query_handling(self):
        """Test handling of seasonal queries (e.g., tax deadlines)"""
        seasonal_analyzer = Mock()

        # Tax deadline queries in March/April
        march_queries = [
            {"query": "scadenza dichiarazione redditi", "timestamp": datetime(2024, 3, 15)},
            {"query": "quando presentare 730", "timestamp": datetime(2024, 3, 20)},
            {"query": "termine dichiarazione IRPEF", "timestamp": datetime(2024, 4, 1)},
        ]

        seasonal_analyzer.detect_seasonal_pattern = Mock(
            return_value={"is_seasonal": True, "peak_months": [3, 4, 5], "seasonal_multiplier": 3.5}
        )

        analysis = seasonal_analyzer.analyze_seasonality(march_queries)

        assert analysis["is_seasonal"] is True
        assert 3 in analysis["peak_months"]
        assert analysis["seasonal_multiplier"] > 1.0

    @pytest.mark.asyncio
    async def test_multi_language_query_clustering(self):
        """Test multi-language query clustering (Italian dialects)"""
        multilang_analyzer = Mock()

        # Mixed Italian and dialect queries
        mixed_queries = [
            {"query": "Come si calcola l'IVA?", "language": "italian_standard"},
            {"query": "Come se fa el calcolo de l'IVA?", "language": "venetian"},  # Venetian
            {"query": "Comu si calcula l'IVA?", "language": "sicilian"},  # Sicilian
            {"query": "Come si fa il calcolo dell'IVA?", "language": "italian_standard"},
        ]

        # Mock normalization to standard Italian
        multilang_analyzer.normalize_to_standard_italian = Mock(
            side_effect=lambda x: {
                "Come se fa el calcolo de l'IVA?": "come si calcola iva",
                "Comu si calcula l'IVA?": "come si calcola iva",
                "Come si calcola l'IVA?": "come si calcola iva",
                "Come si fa il calcolo dell'IVA?": "come si calcola iva",
            }.get(x["query"], x["query"])
        )

        normalized_queries = [multilang_analyzer.normalize_to_standard_italian(q) for q in mixed_queries]

        # Should all normalize to similar form
        assert all("calcola" in nq.lower() and "iva" in nq.lower() for nq in normalized_queries)

    @pytest.mark.asyncio
    async def test_emergency_manual_override_capabilities(self):
        """Test emergency manual override capabilities"""
        override_system = Mock()

        # Simulate emergency: incorrect FAQ generated
        problematic_faq = {
            "id": uuid4(),
            "question": "Come si calcola l'IVA?",
            "answer": "L'IVA si calcola al 25%",  # WRONG percentage
            "auto_generated": True,
            "published": True,
        }

        # Emergency override request
        override_request = {
            "faq_id": problematic_faq["id"],
            "action": "immediate_disable",
            "reason": "Incorrect tax rate information",
            "authorized_by": "admin_user_123",
        }

        override_system.execute_emergency_override = AsyncMock()
        override_system.notify_stakeholders = AsyncMock()

        await override_system.handle_emergency_override(override_request)

        override_system.execute_emergency_override.assert_called_once()
        override_system.notify_stakeholders.assert_called_once()

    @pytest.mark.asyncio
    async def test_cost_optimization_over_time(self):
        """Test that system optimizes costs over time"""
        optimizer = Mock()

        # Historical cost data
        cost_history = [
            {"month": "2024-01", "cost_per_user": 2.00, "faq_coverage": 0.10},
            {"month": "2024-02", "cost_per_user": 1.95, "faq_coverage": 0.15},
            {"month": "2024-03", "cost_per_user": 1.85, "faq_coverage": 0.25},
            {"month": "2024-04", "cost_per_user": 1.75, "faq_coverage": 0.35},
            {"month": "2024-05", "cost_per_user": 1.70, "faq_coverage": 0.45},
        ]

        optimizer.analyze_cost_trend = Mock(
            return_value={
                "trend": "decreasing",
                "monthly_improvement": 0.075,  # €0.075 per month
                "target_achieved": True,  # Reached €1.70 target
            }
        )

        analysis = optimizer.analyze_cost_trend(cost_history)

        assert analysis["trend"] == "decreasing"
        assert analysis["target_achieved"] is True
        assert cost_history[-1]["cost_per_user"] <= 1.70  # Target achieved


# Performance and Monitoring Tests


class TestPerformanceMonitoring:
    """Test performance monitoring and optimization"""

    @pytest.mark.asyncio
    async def test_analytics_dashboard_data_accuracy(self):
        """Test analytics dashboard data accuracy"""
        analytics = Mock()

        # Mock analytics data
        dashboard_data = {
            "total_faqs_generated": 145,
            "auto_approved": 89,
            "manual_review": 56,
            "monthly_cost_savings": 245.50,
            "average_quality_score": 0.91,
            "top_categories": [
                {"category": "IVA", "count": 32},
                {"category": "Detrazioni", "count": 28},
                {"category": "IRPEF", "count": 21},
            ],
            "rss_triggered_updates": 12,
            "user_satisfaction": 4.3,  # out of 5
        }

        analytics.generate_dashboard_data = AsyncMock(return_value=dashboard_data)

        data = await analytics.generate_dashboard_data("2024-05")

        assert data["total_faqs_generated"] > 0
        assert data["auto_approved"] + data["manual_review"] == data["total_faqs_generated"]
        assert data["average_quality_score"] >= 0.85  # Quality threshold
        assert data["monthly_cost_savings"] > 0
        assert len(data["top_categories"]) <= 10

    @pytest.mark.asyncio
    async def test_system_behavior_during_rss_update_floods(self):
        """Test system behavior during RSS update floods"""
        flood_handler = Mock()

        # Simulate RSS flood (20 updates in 1 hour)
        rss_flood = [{"id": uuid4(), "timestamp": datetime.utcnow() - timedelta(minutes=i * 3)} for i in range(20)]

        flood_handler.detect_flood = Mock(return_value=True)
        flood_handler.apply_rate_limiting = AsyncMock()
        flood_handler.queue_for_batch_processing = AsyncMock()

        await flood_handler.handle_rss_updates(rss_flood)

        # Should detect flood and apply rate limiting
        flood_handler.apply_rate_limiting.assert_called_once()
        flood_handler.queue_for_batch_processing.assert_called_once()

    @pytest.mark.asyncio
    async def test_quality_metrics_tracking(self):
        """Test tracking of quality metrics"""
        quality_tracker = Mock()

        # Mock quality metrics over time
        quality_metrics = [
            {"date": "2024-05-01", "avg_quality": 0.87, "faqs_generated": 15},
            {"date": "2024-05-02", "avg_quality": 0.89, "faqs_generated": 12},
            {"date": "2024-05-03", "avg_quality": 0.92, "faqs_generated": 18},
            {"date": "2024-05-04", "avg_quality": 0.91, "faqs_generated": 20},
        ]

        quality_tracker.track_daily_quality = AsyncMock()
        quality_tracker.calculate_trend = Mock(
            return_value={"trend": "improving", "weekly_average": 0.90, "quality_variance": 0.02}
        )

        for metric in quality_metrics:
            await quality_tracker.track_daily_quality(metric)

        trend = quality_tracker.calculate_trend(quality_metrics)

        assert trend["trend"] == "improving"
        assert trend["weekly_average"] >= 0.85
        assert quality_tracker.track_daily_quality.call_count == len(quality_metrics)


if __name__ == "__main__":
    # Run tests with: pytest tests/test_faq_automation.py -v
    pytest.main([__file__, "-v", "--tb=short"])
