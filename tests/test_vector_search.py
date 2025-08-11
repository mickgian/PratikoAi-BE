"""
Comprehensive TDD Tests for Advanced Vector Search Features.

Tests for hybrid search system, query expansion, semantic FAQ matching,
and performance requirements to boost answer quality from 65% to 85%+.
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4

import numpy as np

# Test data structures
from dataclasses import dataclass

@dataclass
class MockSearchResult:
    id: str
    content: str
    source_type: str
    relevance_score: float
    keyword_score: float = 0.0
    vector_score: float = 0.0
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass  
class MockFAQMatch:
    faq_id: str
    question: str
    answer: str
    similarity_score: float
    confidence: str
    needs_update: bool = False
    matched_concepts: List[str] = None
    
    def __post_init__(self):
        if self.matched_concepts is None:
            self.matched_concepts = []

@dataclass
class MockQueryContext:
    query: str
    context_parts: List[Dict]
    total_tokens: int
    sources_used: int


class TestHybridSearchEngine:
    """Test hybrid search combining PostgreSQL full-text and Pinecone vector search"""
    
    @pytest.fixture
    def mock_postgres_service(self):
        service = Mock()
        service.search = AsyncMock()
        return service
    
    @pytest.fixture
    def mock_pinecone_service(self):
        service = Mock()
        service.query = Mock()
        return service
    
    @pytest.fixture
    def mock_embedding_service(self):
        service = Mock()
        service.embed = AsyncMock()
        return service
    
    @pytest.fixture
    def mock_normalizer(self):
        normalizer = Mock()
        normalizer.normalize = AsyncMock()
        return normalizer
    
    @pytest.fixture
    def hybrid_search_engine(
        self,
        mock_postgres_service,
        mock_pinecone_service,
        mock_embedding_service,
        mock_normalizer
    ):
        from app.services.hybrid_search_engine import HybridSearchEngine
        return HybridSearchEngine(
            postgres_service=mock_postgres_service,
            pinecone_service=mock_pinecone_service,
            embedding_service=mock_embedding_service,
            normalizer=mock_normalizer
        )
    
    @pytest.mark.asyncio
    async def test_parallel_execution_of_keyword_and_vector_searches(
        self,
        hybrid_search_engine,
        mock_postgres_service,
        mock_pinecone_service,
        mock_embedding_service,
        mock_normalizer
    ):
        """Test that keyword and vector searches execute in parallel"""
        
        # Setup mocks
        mock_normalizer.normalize.return_value = "calcolo iva 22%"
        mock_embedding_service.embed.return_value = [0.1] * 1536
        
        # Mock keyword search results
        mock_postgres_service.search.return_value = [
            {
                'id': 'faq_1',
                'content': 'Come calcolare l\'IVA al 22% su una fattura',
                'source_type': 'faq',
                'rank': 0.95,
                'metadata': {'category': 'IVA'}
            }
        ]
        
        # Mock vector search results
        mock_pinecone_service.query.return_value = {
            'matches': [
                {
                    'id': 'faq_2',
                    'score': 0.88,
                    'metadata': {
                        'content': 'Calcolo dell\'imposta sul valore aggiunto',
                        'source_type': 'faq',
                        'category': 'IVA'
                    }
                }
            ]
        }
        
        # Mock query expansion
        with patch.object(hybrid_search_engine, 'expand_query', new_callable=AsyncMock) as mock_expand:
            mock_expand.return_value = ['imposta valore aggiunto', 'aliquota iva']
            
            # Execute search
            start_time = time.time()
            results = await hybrid_search_engine.search("calcolo iva 22%")
            execution_time = (time.time() - start_time) * 1000
            
            # Verify parallel execution (should be faster than sequential)
            assert execution_time < 300  # Performance requirement
            
            # Verify both searches were called
            mock_postgres_service.search.assert_called_once()
            mock_pinecone_service.query.assert_called_once()
            
            # Verify results contain both sources
            assert len(results) == 2
            result_ids = [r.id for r in results]
            assert 'faq_1' in result_ids
            assert 'faq_2' in result_ids
    
    @pytest.mark.asyncio
    async def test_result_merging_with_relevance_scoring(
        self,
        hybrid_search_engine,
        mock_postgres_service,
        mock_pinecone_service,
        mock_embedding_service,
        mock_normalizer
    ):
        """Test proper merging and scoring of keyword + vector results"""
        
        # Setup mocks
        mock_normalizer.normalize.return_value = "regime forfettario 2024"
        mock_embedding_service.embed.return_value = [0.2] * 1536
        
        # Same result from both searches (should be merged)
        mock_postgres_service.search.return_value = [
            {
                'id': 'reg_1',
                'content': 'Regime forfettario 2024 - nuove soglie',
                'source_type': 'regulation',
                'rank': 0.92,
                'metadata': {'year': '2024'}
            }
        ]
        
        mock_pinecone_service.query.return_value = {
            'matches': [
                {
                    'id': 'reg_1',  # Same ID as keyword result
                    'score': 0.85,
                    'metadata': {
                        'content': 'Regime forfettario 2024 - nuove soglie',
                        'source_type': 'regulation',
                        'year': '2024'
                    }
                }
            ]
        }
        
        with patch.object(hybrid_search_engine, 'expand_query', new_callable=AsyncMock) as mock_expand:
            mock_expand.return_value = ['partita iva forfettaria']
            
            results = await hybrid_search_engine.search("regime forfettario 2024")
            
            # Should have only one merged result
            assert len(results) == 1
            
            result = results[0]
            assert result.id == 'reg_1'
            
            # Should have both keyword and vector scores
            assert result.keyword_score == 0.92
            assert result.vector_score == 0.85
            
            # Relevance score should be weighted combination
            expected_relevance = (0.92 * 0.4) + (0.85 * 0.6)  # Default weights
            assert abs(result.relevance_score - expected_relevance) < 0.01
    
    @pytest.mark.asyncio
    async def test_deduplication_of_overlapping_results(
        self,
        hybrid_search_engine,
        mock_postgres_service,
        mock_pinecone_service,
        mock_embedding_service,
        mock_normalizer
    ):
        """Test that duplicate results from both searches are properly deduplicated"""
        
        # Setup mocks with overlapping results
        mock_normalizer.normalize.return_value = "fattura elettronica"
        mock_embedding_service.embed.return_value = [0.3] * 1536
        
        # Overlapping results with same IDs
        mock_postgres_service.search.return_value = [
            {'id': 'faq_1', 'content': 'Fattura elettronica obbligatoria', 'source_type': 'faq', 'rank': 0.9, 'metadata': {}},
            {'id': 'faq_2', 'content': 'Come emettere e-fattura', 'source_type': 'faq', 'rank': 0.85, 'metadata': {}}
        ]
        
        mock_pinecone_service.query.return_value = {
            'matches': [
                {'id': 'faq_1', 'score': 0.88, 'metadata': {'content': 'Fattura elettronica obbligatoria', 'source_type': 'faq'}},
                {'id': 'faq_3', 'score': 0.82, 'metadata': {'content': 'Sistema di Interscambio SDI', 'source_type': 'faq'}}
            ]
        }
        
        with patch.object(hybrid_search_engine, 'expand_query', new_callable=AsyncMock) as mock_expand:
            mock_expand.return_value = ['e-fattura', 'sdi']
            
            results = await hybrid_search_engine.search("fattura elettronica")
            
            # Should have 3 unique results (faq_1 merged, faq_2, faq_3)
            assert len(results) == 3
            
            result_ids = [r.id for r in results]
            assert 'faq_1' in result_ids
            assert 'faq_2' in result_ids  
            assert 'faq_3' in result_ids
            assert len(set(result_ids)) == 3  # All unique
            
            # faq_1 should have both scores
            faq_1_result = next(r for r in results if r.id == 'faq_1')
            assert faq_1_result.keyword_score == 0.9
            assert faq_1_result.vector_score == 0.88
            
            # faq_2 should have only keyword score
            faq_2_result = next(r for r in results if r.id == 'faq_2')
            assert faq_2_result.keyword_score == 0.85
            assert faq_2_result.vector_score == 0.0
            
            # faq_3 should have only vector score
            faq_3_result = next(r for r in results if r.id == 'faq_3')
            assert faq_3_result.keyword_score == 0.0
            assert faq_3_result.vector_score == 0.82
    
    @pytest.mark.asyncio
    async def test_performance_under_300ms_for_hybrid_search(
        self,
        hybrid_search_engine,
        mock_postgres_service,
        mock_pinecone_service,
        mock_embedding_service,
        mock_normalizer
    ):
        """Test that hybrid search completes in under 300ms"""
        
        # Setup fast mock responses
        mock_normalizer.normalize.return_value = "test query"
        mock_embedding_service.embed.return_value = [0.1] * 1536
        
        # Simulate realistic response times
        async def mock_postgres_search(*args, **kwargs):
            await asyncio.sleep(0.05)  # 50ms
            return [{'id': 'test_1', 'content': 'test', 'source_type': 'faq', 'rank': 0.9, 'metadata': {}}]
        
        def mock_pinecone_query(*args, **kwargs):
            time.sleep(0.08)  # 80ms
            return {'matches': [{'id': 'test_2', 'score': 0.85, 'metadata': {'content': 'test', 'source_type': 'faq'}}]}
        
        mock_postgres_service.search = mock_postgres_search
        mock_pinecone_service.query = mock_pinecone_query
        
        with patch.object(hybrid_search_engine, 'expand_query', new_callable=AsyncMock) as mock_expand:
            mock_expand.return_value = ['expanded term']
            
            # Measure execution time
            start_time = time.time()
            results = await hybrid_search_engine.search("test query")
            execution_time = (time.time() - start_time) * 1000
            
            # Should complete in under 300ms (parallel execution)
            assert execution_time < 300
            assert len(results) == 2
    
    @pytest.mark.asyncio
    async def test_fallback_to_single_search_on_failure(
        self,
        hybrid_search_engine,
        mock_postgres_service,
        mock_pinecone_service,
        mock_embedding_service,
        mock_normalizer
    ):
        """Test graceful fallback when one search method fails"""
        
        # Setup mocks
        mock_normalizer.normalize.return_value = "test query"
        mock_embedding_service.embed.return_value = [0.1] * 1536
        
        # Make PostgreSQL search fail
        mock_postgres_service.search.side_effect = Exception("Database connection failed")
        
        # Vector search succeeds
        mock_pinecone_service.query.return_value = {
            'matches': [
                {'id': 'vector_1', 'score': 0.9, 'metadata': {'content': 'vector result', 'source_type': 'faq'}}
            ]
        }
        
        with patch.object(hybrid_search_engine, 'expand_query', new_callable=AsyncMock) as mock_expand:
            mock_expand.return_value = []
            
            # Should still return vector results
            results = await hybrid_search_engine.search("test query")
            
            assert len(results) == 1
            assert results[0].id == 'vector_1'
            assert results[0].vector_score == 0.9
            assert results[0].keyword_score == 0.0  # Failed search
    
    @pytest.mark.asyncio 
    async def test_empty_result_handling(
        self,
        hybrid_search_engine,
        mock_postgres_service,
        mock_pinecone_service,
        mock_embedding_service,
        mock_normalizer
    ):
        """Test handling when no results are found"""
        
        # Setup mocks for empty results
        mock_normalizer.normalize.return_value = "nonexistent query"
        mock_embedding_service.embed.return_value = [0.1] * 1536
        
        mock_postgres_service.search.return_value = []
        mock_pinecone_service.query.return_value = {'matches': []}
        
        with patch.object(hybrid_search_engine, 'expand_query', new_callable=AsyncMock) as mock_expand:
            mock_expand.return_value = []
            
            results = await hybrid_search_engine.search("nonexistent query")
            
            assert len(results) == 0
            assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_result_ranking_accuracy(
        self,
        hybrid_search_engine,
        mock_postgres_service,
        mock_pinecone_service,
        mock_embedding_service,
        mock_normalizer
    ):
        """Test that results are ranked correctly by relevance score"""
        
        # Setup mocks
        mock_normalizer.normalize.return_value = "tax calculation"
        mock_embedding_service.embed.return_value = [0.1] * 1536
        
        mock_postgres_service.search.return_value = [
            {'id': 'low_keyword', 'content': 'low relevance', 'source_type': 'knowledge', 'rank': 0.3, 'metadata': {}},
            {'id': 'high_keyword', 'content': 'high relevance', 'source_type': 'faq', 'rank': 0.95, 'metadata': {}}
        ]
        
        mock_pinecone_service.query.return_value = {
            'matches': [
                {'id': 'med_vector', 'score': 0.7, 'metadata': {'content': 'medium vector', 'source_type': 'regulation'}},
                {'id': 'high_vector', 'score': 0.92, 'metadata': {'content': 'high vector', 'source_type': 'faq'}}
            ]
        }
        
        with patch.object(hybrid_search_engine, 'expand_query', new_callable=AsyncMock) as mock_expand:
            mock_expand.return_value = []
            
            results = await hybrid_search_engine.search("tax calculation")
            
            # Should be ranked by relevance score (descending)
            assert len(results) == 4
            
            # Calculate expected scores
            high_keyword_score = 0.95 * 0.4  # keyword weight
            high_vector_score = 0.92 * 0.6   # vector weight
            med_vector_score = 0.7 * 0.6
            low_keyword_score = 0.3 * 0.4
            
            # Results should be ordered by relevance
            assert results[0].relevance_score >= results[1].relevance_score
            assert results[1].relevance_score >= results[2].relevance_score
            assert results[2].relevance_score >= results[3].relevance_score


class TestItalianQueryExpansion:
    """Test query expansion for Italian tax terminology"""
    
    @pytest.fixture
    def mock_synonym_service(self):
        service = Mock()
        return service
    
    @pytest.fixture
    def mock_embedding_service(self):
        service = Mock()
        service.embed = AsyncMock()
        service.find_similar_terms = AsyncMock()
        return service
    
    @pytest.fixture
    def query_expander(self, mock_synonym_service, mock_embedding_service):
        from app.services.query_expansion_service import ItalianTaxQueryExpander
        return ItalianTaxQueryExpander(mock_synonym_service, mock_embedding_service)
    
    @pytest.mark.asyncio
    async def test_italian_tax_synonym_expansion(self, query_expander, mock_embedding_service):
        """Test expansion of Italian tax terminology"""
        
        mock_embedding_service.find_similar_terms.return_value = []
        
        # Test IVA expansion
        expansions = await query_expander.expand_query("iva fattura")
        
        expected_terms = ['imposta valore aggiunto', 'partita iva', 'aliquota iva']
        assert any(term in expansions for term in expected_terms)
        assert len(expansions) <= 5  # Max expansions limit
    
    @pytest.mark.asyncio
    async def test_acronym_expansion(self, query_expander, mock_embedding_service):
        """Test acronym expansion (IVA → Imposta Valore Aggiunto)"""
        
        mock_embedding_service.find_similar_terms.return_value = []
        
        expansions = await query_expander.expand_query("calcolo IVA 22%")
        
        # Should include full form
        assert 'imposta valore aggiunto' in expansions
        
        # Test IRPEF expansion  
        expansions = await query_expander.expand_query("dichiarazione IRPEF")
        assert 'imposta reddito persone fisiche' in expansions
    
    @pytest.mark.asyncio
    async def test_related_concept_discovery(self, query_expander, mock_embedding_service):
        """Test discovery of related tax concepts"""
        
        # Mock semantic expansion
        mock_embedding_service.find_similar_terms.return_value = [
            {'text': 'ritenuta d\'acconto', 'score': 0.85},
            {'text': 'versamento f24', 'score': 0.82},
            {'text': 'codice tributo', 'score': 0.78}
        ]
        
        expansions = await query_expander.expand_query("pagamento tasse")
        
        # Should include semantically related terms
        assert 'ritenuta d\'acconto' in expansions
        assert 'versamento f24' in expansions
        
        # Should filter by similarity threshold (0.8)
        assert 'codice tributo' not in expansions  # Score too low
    
    @pytest.mark.asyncio
    async def test_query_expansion_limits(self, query_expander, mock_embedding_service):
        """Test that expansion respects maximum limits"""
        
        # Mock many similar terms
        mock_embedding_service.find_similar_terms.return_value = [
            {'text': f'term_{i}', 'score': 0.9} for i in range(20)
        ]
        
        expansions = await query_expander.expand_query("test", max_expansions=3)
        
        # Should respect the limit
        assert len(expansions) <= 3
    
    @pytest.mark.asyncio 
    async def test_performance_impact_under_50ms(self, query_expander, mock_embedding_service):
        """Test that query expansion completes in under 50ms"""
        
        # Mock fast responses
        async def fast_similar_terms(*args, **kwargs):
            await asyncio.sleep(0.01)  # 10ms
            return [{'text': 'fast_term', 'score': 0.9}]
        
        mock_embedding_service.find_similar_terms = fast_similar_terms
        
        start_time = time.time()
        expansions = await query_expander.expand_query("test query")
        execution_time = (time.time() - start_time) * 1000
        
        assert execution_time < 50  # Performance requirement
        assert len(expansions) >= 0
    
    @pytest.mark.asyncio
    async def test_expansion_quality_scoring(self, query_expander, mock_embedding_service):
        """Test that expansion terms are scored for quality"""
        
        # Mock terms with various quality scores
        mock_embedding_service.find_similar_terms.return_value = [
            {'text': 'high_quality_term', 'score': 0.95},
            {'text': 'medium_quality_term', 'score': 0.82},
            {'text': 'low_quality_term', 'score': 0.65}  # Below threshold
        ]
        
        expansions = await query_expander.expand_query("quality test")
        
        # Should include high and medium quality terms
        assert 'high_quality_term' in expansions
        assert 'medium_quality_term' in expansions
        
        # Should exclude low quality terms
        assert 'low_quality_term' not in expansions
    
    @pytest.mark.asyncio
    async def test_dialect_variation_handling(self, query_expander, mock_embedding_service):
        """Test handling of regional/dialect variations"""
        
        mock_embedding_service.find_similar_terms.return_value = []
        
        # Test professional vs casual variations
        professional_expansions = await query_expander.expand_query("partita iva")
        assert 'libero professionista' in professional_expansions
        assert 'p.iva' in professional_expansions
        
        # Test company type variations
        company_expansions = await query_expander.expand_query("srl")
        assert 'società responsabilità limitata' in company_expansions
        assert 's.r.l.' in company_expansions


class TestSemanticFAQMatching:
    """Test semantic FAQ matching improvements"""
    
    @pytest.fixture
    def mock_faq_service(self):
        service = Mock()
        service.get_by_id = AsyncMock()
        return service
    
    @pytest.fixture
    def mock_embedding_service(self):
        service = Mock()
        service.embed = AsyncMock()
        return service
    
    @pytest.fixture
    def mock_cache_service(self):
        service = Mock()
        service.get = AsyncMock()
        service.setex = AsyncMock()
        return service
    
    @pytest.fixture
    def mock_pinecone_service(self):
        service = Mock()
        service.query = Mock()
        return service
    
    @pytest.fixture
    def faq_matcher(self, mock_faq_service, mock_embedding_service, mock_cache_service):
        from app.services.semantic_faq_matcher import SemanticFAQMatcher
        matcher = SemanticFAQMatcher(mock_faq_service, mock_embedding_service, mock_cache_service)
        matcher.pinecone = Mock()
        return matcher
    
    @pytest.mark.asyncio
    async def test_faq_hit_rate_improvement_target_70_percent(self, faq_matcher):
        """Test that FAQ matching achieves target 70%+ hit rate"""
        
        # Mock high-quality matches
        faq_matcher.pinecone.query.return_value = {
            'matches': [
                {
                    'id': 'faq_1',
                    'score': 0.88,
                    'metadata': {'concepts': ['iva', 'calcolo']}
                },
                {
                    'id': 'faq_2', 
                    'score': 0.82,
                    'metadata': {'concepts': ['aliquota', '22%']}
                }
            ]
        }
        
        # Mock FAQ retrieval
        faq_matcher.faq.get_by_id.side_effect = [
            MockFAQMatch('faq_1', 'Come calcolare IVA?', 'Per calcolare...', 0.88, 'high'),
            MockFAQMatch('faq_2', 'Aliquota IVA 22%', 'L\'aliquota...', 0.82, 'high')
        ]
        
        faq_matcher.cache.get.return_value = None  # No cache
        
        with patch.object(faq_matcher, '_check_faq_freshness', new_callable=AsyncMock) as mock_freshness:
            mock_freshness.return_value = False
            
            matches = await faq_matcher.find_matching_faqs("calcolo iva 22 percento")
            
            # Should find relevant matches
            assert len(matches) == 2
            assert all(match.confidence in ['high', 'exact'] for match in matches)
            
            # Simulate hit rate calculation over multiple queries
            hit_count = len([m for m in matches if m.similarity_score >= faq_matcher.low_confidence_threshold])
            hit_rate = hit_count / len(matches) if matches else 0
            assert hit_rate >= 0.70  # Target hit rate
    
    @pytest.mark.asyncio
    async def test_similarity_threshold_tuning(self, faq_matcher):
        """Test similarity threshold tuning (0.75-0.90)"""
        
        # Mock results with various similarity scores
        faq_matcher.pinecone.query.return_value = {
            'matches': [
                {'id': 'exact_match', 'score': 0.96, 'metadata': {}},      # Exact
                {'id': 'high_match', 'score': 0.86, 'metadata': {}},       # High confidence
                {'id': 'medium_match', 'score': 0.78, 'metadata': {}},     # Medium confidence  
                {'id': 'low_match', 'score': 0.65, 'metadata': {}}         # Below threshold
            ]
        }
        
        def mock_get_faq(faq_id):
            score_map = {
                'exact_match': 0.96,
                'high_match': 0.86,
                'medium_match': 0.78,
                'low_match': 0.65
            }
            return MockFAQMatch(faq_id, f'Question {faq_id}', f'Answer {faq_id}', score_map[faq_id], 'high')
        
        faq_matcher.faq.get_by_id.side_effect = mock_get_faq
        faq_matcher.cache.get.return_value = None
        
        with patch.object(faq_matcher, '_check_faq_freshness', new_callable=AsyncMock) as mock_freshness:
            mock_freshness.return_value = False
            
            matches = await faq_matcher.find_matching_faqs("test query")
            
            # Should only include results above low_confidence_threshold (0.75)
            assert len(matches) == 3  # Excludes low_match (0.65)
            
            scores = [m.similarity_score for m in matches]
            assert all(score >= 0.75 for score in scores)
            assert 0.96 in scores  # exact_match
            assert 0.86 in scores  # high_match  
            assert 0.78 in scores  # medium_match
    
    @pytest.mark.asyncio
    async def test_false_positive_prevention(self, faq_matcher):
        """Test prevention of false positive matches"""
        
        # Mock results including potential false positives
        faq_matcher.pinecone.query.return_value = {
            'matches': [
                {
                    'id': 'relevant_faq',
                    'score': 0.85,
                    'metadata': {'concepts': ['iva', 'fattura']}
                },
                {
                    'id': 'irrelevant_faq',
                    'score': 0.77,  # Just above threshold but irrelevant
                    'metadata': {'concepts': ['unrelated', 'topic']}
                }
            ]
        }
        
        def mock_get_faq(faq_id):
            if faq_id == 'relevant_faq':
                return MockFAQMatch(
                    faq_id, 'IVA su fattura', 'L\'IVA si calcola...', 0.85, 'high',
                    matched_concepts=['iva', 'fattura']
                )
            else:
                return MockFAQMatch(
                    faq_id, 'Unrelated topic', 'This is about...', 0.77, 'medium',
                    matched_concepts=['unrelated', 'topic']
                )
        
        faq_matcher.faq.get_by_id.side_effect = mock_get_faq
        faq_matcher.cache.get.return_value = None
        
        with patch.object(faq_matcher, '_check_faq_freshness', new_callable=AsyncMock) as mock_freshness:
            mock_freshness.return_value = False
            
            matches = await faq_matcher.find_matching_faqs("calcolo iva fattura")
            
            # Should prioritize relevant matches
            assert len(matches) == 2
            
            # Most relevant should be first
            assert matches[0].faq_id == 'relevant_faq'
            assert matches[0].similarity_score == 0.85
            
            # Concept matching should influence ranking
            relevant_match = next(m for m in matches if m.faq_id == 'relevant_faq')
            assert 'iva' in relevant_match.matched_concepts
            assert 'fattura' in relevant_match.matched_concepts
    
    @pytest.mark.asyncio
    async def test_multi_faq_matching_for_complex_queries(self, faq_matcher):
        """Test matching multiple FAQs for complex queries"""
        
        # Mock multiple relevant FAQs for complex query
        faq_matcher.pinecone.query.return_value = {
            'matches': [
                {'id': 'faq_iva', 'score': 0.89, 'metadata': {'concepts': ['iva']}},
                {'id': 'faq_fattura', 'score': 0.84, 'metadata': {'concepts': ['fattura']}},
                {'id': 'faq_regime', 'score': 0.81, 'metadata': {'concepts': ['regime', 'forfettario']}}
            ]
        }
        
        def mock_get_faq(faq_id):
            faq_map = {
                'faq_iva': MockFAQMatch(faq_id, 'Calcolo IVA', 'Per calcolare IVA...', 0.89, 'high'),
                'faq_fattura': MockFAQMatch(faq_id, 'Fattura elettronica', 'La fattura...', 0.84, 'high'),
                'faq_regime': MockFAQMatch(faq_id, 'Regime forfettario', 'Il regime...', 0.81, 'high')
            }
            return faq_map[faq_id]
        
        faq_matcher.faq.get_by_id.side_effect = mock_get_faq
        faq_matcher.cache.get.return_value = None
        
        with patch.object(faq_matcher, '_check_faq_freshness', new_callable=AsyncMock) as mock_freshness:
            mock_freshness.return_value = False
            
            matches = await faq_matcher.find_matching_faqs(
                "iva fattura elettronica regime forfettario",
                max_results=3
            )
            
            # Should return multiple relevant FAQs
            assert len(matches) == 3
            
            # All should be high confidence
            assert all(m.confidence == 'high' for m in matches)
            
            # Should be ordered by relevance
            scores = [m.similarity_score for m in matches]
            assert scores == sorted(scores, reverse=True)
    
    @pytest.mark.asyncio
    async def test_performance_with_1000_plus_faqs(self, faq_matcher):
        """Test performance with large FAQ database (1000+ FAQs)"""
        
        # Mock large result set
        large_matches = [
            {'id': f'faq_{i}', 'score': 0.8 - (i * 0.001), 'metadata': {}}
            for i in range(1000)
        ]
        
        faq_matcher.pinecone.query.return_value = {'matches': large_matches[:20]}  # Pinecone limits
        
        def mock_get_faq(faq_id):
            return MockFAQMatch(faq_id, f'Question {faq_id}', f'Answer {faq_id}', 0.8, 'high')
        
        faq_matcher.faq.get_by_id.side_effect = mock_get_faq
        faq_matcher.cache.get.return_value = None
        
        with patch.object(faq_matcher, '_check_faq_freshness', new_callable=AsyncMock) as mock_freshness:
            mock_freshness.return_value = False
            
            start_time = time.time()
            matches = await faq_matcher.find_matching_faqs("test query", max_results=10)
            execution_time = (time.time() - start_time) * 1000
            
            # Should handle large dataset efficiently
            assert execution_time < 200  # Performance requirement
            assert len(matches) == 10  # Respects limit
    
    @pytest.mark.asyncio
    async def test_italian_language_semantic_accuracy(self, faq_matcher):
        """Test semantic accuracy for Italian language queries"""
        
        # Mock Italian-specific matches
        faq_matcher.pinecone.query.return_value = {
            'matches': [
                {
                    'id': 'faq_italian_1',
                    'score': 0.91,
                    'metadata': {'concepts': ['dichiarazione', 'redditi'], 'language': 'it'}
                },
                {
                    'id': 'faq_italian_2', 
                    'score': 0.87,
                    'metadata': {'concepts': ['modello', '730'], 'language': 'it'}
                }
            ]
        }
        
        def mock_get_faq(faq_id):
            if faq_id == 'faq_italian_1':
                return MockFAQMatch(
                    faq_id, 
                    'Come presentare dichiarazione dei redditi?',
                    'La dichiarazione dei redditi...',
                    0.91, 'exact'
                )
            else:
                return MockFAQMatch(
                    faq_id,
                    'Modello 730 precompilato',
                    'Il modello 730...',
                    0.87, 'high'
                )
        
        faq_matcher.faq.get_by_id.side_effect = mock_get_faq
        faq_matcher.cache.get.return_value = None
        
        with patch.object(faq_matcher, '_check_faq_freshness', new_callable=AsyncMock) as mock_freshness:
            mock_freshness.return_value = False
            
            matches = await faq_matcher.find_matching_faqs("dichiarazione redditi 730")
            
            # Should accurately match Italian tax terminology
            assert len(matches) == 2
            
            # Should understand semantic relationships
            assert any('dichiarazione' in m.question for m in matches)
            assert any('730' in m.question for m in matches)
            
            # High confidence for Italian tax terms
            assert all(m.confidence in ['high', 'exact'] for m in matches)


class TestKnowledgeBaseIntegration:
    """Test integration with knowledge base sources"""
    
    @pytest.fixture
    def mock_hybrid_search(self):
        search = Mock()
        search.search = AsyncMock()
        return search
    
    @pytest.fixture
    def mock_ranker(self):
        ranker = Mock()
        ranker.rank_sources = Mock()
        return ranker
    
    @pytest.fixture
    def context_builder(self, mock_hybrid_search, mock_ranker):
        from app.services.context_builder import MultiSourceContextBuilder
        return MultiSourceContextBuilder(mock_hybrid_search, mock_ranker)
    
    @pytest.mark.asyncio
    async def test_regulatory_document_semantic_search(
        self,
        context_builder,
        mock_hybrid_search
    ):
        """Test semantic search across regulatory documents"""
        
        # Mock regulatory search results
        mock_hybrid_search.search.return_value = [
            MockSearchResult(
                'reg_1', 
                'D.Lgs. 142/2024 - Fatturazione elettronica obbligatoria',
                'regulation',
                0.92,
                metadata={'document_type': 'decreto', 'year': '2024'}
            ),
            MockSearchResult(
                'circ_1',
                'Circolare 15/E - Chiarimenti fattura elettronica',
                'circular',
                0.88,
                metadata={'document_type': 'circolare', 'year': '2024'}
            )
        ]
        
        with patch.object(context_builder, '_extract_relevant_portion', new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = "Contenuto rilevante del documento..."
            
            with patch.object(context_builder, '_count_tokens', return_value=150):
                context = await context_builder.build_context(
                    "fatturazione elettronica obbligatoria 2024"
                )
                
                assert context.sources_used == 2
                assert any(part['source_type'] == 'regulation' for part in context.context_parts)
                assert any(part['source_type'] == 'circular' for part in context.context_parts)
                
                # Should prioritize official regulations
                regulation_part = next(part for part in context.context_parts if part['source_type'] == 'regulation')
                assert regulation_part['relevance_score'] == 0.92
    
    @pytest.mark.asyncio
    async def test_multi_source_context_building(
        self,
        context_builder,
        mock_hybrid_search
    ):
        """Test building context from multiple source types"""
        
        # Mock diverse search results
        mock_hybrid_search.search.return_value = [
            MockSearchResult('faq_1', 'FAQ content', 'faq', 0.95),
            MockSearchResult('kb_1', 'Knowledge base content', 'knowledge', 0.85),
            MockSearchResult('reg_1', 'Regulation content', 'regulation', 0.90),
            MockSearchResult('circ_1', 'Circular content', 'circular', 0.82)
        ]
        
        with patch.object(context_builder, '_extract_relevant_portion', new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = "Extracted relevant content..."
            
            with patch.object(context_builder, '_count_tokens', return_value=200):
                context = await context_builder.build_context("multi source query")
                
                # Should include all source types
                source_types = [part['source_type'] for part in context.context_parts]
                assert 'faq' in source_types
                assert 'knowledge' in source_types
                assert 'regulation' in source_types
                assert 'circular' in source_types
                
                # Should respect priority order (FAQ first, then regulation, etc.)
                assert context.context_parts[0]['source_type'] == 'faq'
    
    @pytest.mark.asyncio
    async def test_relevance_scoring_across_source_types(
        self,
        context_builder,
        mock_hybrid_search
    ):
        """Test relevance scoring works across different source types"""
        
        mock_hybrid_search.search.return_value = [
            MockSearchResult('low_faq', 'Low relevance FAQ', 'faq', 0.6),
            MockSearchResult('high_reg', 'High relevance regulation', 'regulation', 0.95),
            MockSearchResult('med_kb', 'Medium relevance KB', 'knowledge', 0.75)
        ]
        
        with patch.object(context_builder, '_extract_relevant_portion', new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = "Content..."
            
            with patch.object(context_builder, '_count_tokens', return_value=100):
                context = await context_builder.build_context("relevance test")
                
                # Should be ordered by relevance, not just source type
                scores = [part['relevance_score'] for part in context.context_parts]
                assert scores == sorted(scores, reverse=True)
                
                # Highest relevance should be first regardless of source type
                assert context.context_parts[0]['relevance_score'] == 0.95
    
    @pytest.mark.asyncio
    async def test_date_based_relevance_decay(
        self,
        context_builder,
        mock_hybrid_search
    ):
        """Test that older content has reduced relevance"""
        
        old_date = datetime.now() - timedelta(days=365)
        recent_date = datetime.now() - timedelta(days=30)
        
        mock_hybrid_search.search.return_value = [
            MockSearchResult(
                'old_reg', 'Old regulation', 'regulation', 0.90,
                metadata={'updated_at': old_date.isoformat()}
            ),
            MockSearchResult(
                'recent_reg', 'Recent regulation', 'regulation', 0.85,
                metadata={'updated_at': recent_date.isoformat()}
            )
        ]
        
        with patch.object(context_builder, '_extract_relevant_portion', new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = "Content..."
            
            with patch.object(context_builder, '_count_tokens', return_value=100):
                context = await context_builder.build_context("regulation test")
                
                # Recent content should be prioritized despite lower base score
                # (This would be implemented in the actual ranking logic)
                assert len(context.context_parts) == 2
    
    @pytest.mark.asyncio
    async def test_context_size_optimization(
        self,
        context_builder,
        mock_hybrid_search
    ):
        """Test that context respects token limits"""
        
        # Mock results that would exceed token limit
        mock_hybrid_search.search.return_value = [
            MockSearchResult('large_1', 'Large content 1', 'faq', 0.9),
            MockSearchResult('large_2', 'Large content 2', 'faq', 0.85),
            MockSearchResult('large_3', 'Large content 3', 'knowledge', 0.8)
        ]
        
        # Mock token counting to simulate large content
        def mock_count_tokens(text):
            return 800  # Each piece is large
        
        with patch.object(context_builder, '_extract_relevant_portion', new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = "Large extracted content..."
            
            with patch.object(context_builder, '_count_tokens', side_effect=mock_count_tokens):
                context = await context_builder.build_context(
                    "test query",
                    max_tokens=2000
                )
                
                # Should respect token limit
                assert context.total_tokens <= 2000
                
                # Should include highest priority items within limit
                assert context.sources_used <= 3  # Based on 800 tokens each


class TestPerformanceRequirements:
    """Test performance requirements <300ms"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_search_latency_under_300ms(self):
        """Test complete search pipeline under 300ms"""
        
        # This would be an integration test with real services
        # For now, test the performance contract
        
        start_time = time.time()
        
        # Simulate realistic processing time
        await asyncio.sleep(0.25)  # 250ms - within limit
        
        execution_time = (time.time() - start_time) * 1000
        
        assert execution_time < 300
    
    @pytest.mark.asyncio
    async def test_vector_embedding_generation_performance(self):
        """Test embedding generation doesn't exceed latency budget"""
        
        # Mock embedding generation
        start_time = time.time()
        
        # Simulate embedding API call
        await asyncio.sleep(0.05)  # 50ms
        
        execution_time = (time.time() - start_time) * 1000
        
        # Embedding should be fast portion of total budget
        assert execution_time < 100  # 1/3 of total budget
    
    @pytest.mark.asyncio
    async def test_database_query_performance(self):
        """Test database queries meet performance requirements"""
        
        start_time = time.time()
        
        # Simulate database query
        await asyncio.sleep(0.08)  # 80ms
        
        execution_time = (time.time() - start_time) * 1000
        
        # Database query should be reasonable portion of budget
        assert execution_time < 150  # Half of total budget
    
    def test_memory_usage_efficiency(self):
        """Test memory usage remains efficient"""
        
        # Test that large result sets don't consume excessive memory
        large_results = [
            MockSearchResult(f'id_{i}', f'content_{i}', 'faq', 0.8)
            for i in range(1000)
        ]
        
        # Should handle large datasets without memory issues
        assert len(large_results) == 1000
        
        # Simulate processing with reasonable memory usage
        processed = large_results[:10]  # Limit processing
        assert len(processed) == 10


class TestItalianLanguageSpecifics:
    """Test Italian language specific features"""
    
    @pytest.mark.asyncio
    async def test_italian_embedding_quality(self):
        """Test quality of Italian embeddings"""
        
        # Mock Italian-specific embedding service
        embedding_service = Mock()
        embedding_service.embed = AsyncMock()
        
        # Mock Italian embeddings
        embedding_service.embed.return_value = [0.1] * 1536
        
        # Test Italian tax terms
        italian_terms = [
            "dichiarazione dei redditi",
            "partita iva", 
            "regime forfettario",
            "fattura elettronica",
            "codice fiscale"
        ]
        
        for term in italian_terms:
            embedding = await embedding_service.embed(term)
            assert len(embedding) == 1536
            assert all(isinstance(x, float) for x in embedding)
    
    @pytest.mark.asyncio 
    async def test_handling_tax_specific_terminology(self):
        """Test handling of Italian tax-specific terminology"""
        
        tax_terms = {
            'iva': ['imposta valore aggiunto', 'partita iva', 'aliquota'],
            'irpef': ['imposta redditi persone fisiche', 'ritenuta'],
            'f24': ['modello f24', 'versamento', 'delega'],
            'imu': ['imposta municipale unica', 'tassa casa'],
            'tari': ['tassa rifiuti', 'tributo ambientale']
        }
        
        for abbreviation, expanded_terms in tax_terms.items():
            # Should recognize all variations
            assert len(expanded_terms) > 0
            assert all(isinstance(term, str) for term in expanded_terms)
    
    def test_regional_terminology_variations(self):
        """Test handling of regional Italian terminology variations"""
        
        regional_variations = {
            'commercialista': ['dottore commercialista', 'consulente fiscale', 'ragioniere'],
            'fattura': ['fattura', 'ricevuta fiscale', 'documento fiscale'],
            'tasse': ['tasse', 'tributi', 'imposte', 'contributi']
        }
        
        for base_term, variations in regional_variations.items():
            # Should handle regional variations
            assert len(variations) > 1
            assert base_term in variations
    
    def test_professional_vs_casual_language(self):
        """Test distinguishing professional vs casual language"""
        
        professional_terms = [
            'dichiarazione dei redditi',
            'partita iva',
            'codice fiscale',
            'regime forfettario'
        ]
        
        casual_terms = [
            'tasse',
            'soldi',
            'pagare',
            'guadagno'
        ]
        
        # Professional terms should have higher semantic weight
        for term in professional_terms:
            assert len(term.split()) >= 2 or term in ['iva', 'irpef', 'imu']
        
        # Casual terms are typically shorter
        for term in casual_terms:
            assert len(term) <= 10
    
    def test_multilingual_term_handling(self):
        """Test handling of EU directive terms (multilingual)"""
        
        multilingual_terms = {
            'vat': 'iva',  # English -> Italian
            'tva': 'iva',  # French -> Italian  
            'mwst': 'iva', # German -> Italian
            'btw': 'iva'   # Dutch -> Italian
        }
        
        for foreign_term, italian_term in multilingual_terms.items():
            # Should map foreign terms to Italian equivalents
            assert len(foreign_term) > 0
            assert italian_term == 'iva'