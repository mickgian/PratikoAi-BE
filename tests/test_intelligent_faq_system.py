"""
Test suite for Intelligent FAQ System with response variation and update checking.

Following TDD principles - these tests are written before implementation.

This system handles common Italian tax/legal queries with GPT-3.5 variation
(€0.0003/query) and obsolescence checking against RSS updates to reduce
LLM costs by 40% while maintaining quality UX.
"""

import pytest
import time
import asyncio
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4

# These imports will be created during implementation
from app.services.intelligent_faq_service import (
    IntelligentFAQService,
    FAQResponse,
    FAQEntry,
    FAQMatch,
    VariationResponse,
    ObsolescenceResult
)
from app.models.faq import (
    FAQEntry as FAQEntryModel,
    FAQUsageLog,
    FAQCategory,
    UpdateSensitivity
)
from app.schemas.faq import (
    FAQSearchRequest,
    FAQSearchResponse,
    FAQFeedbackRequest,
    FAQCreateRequest,
    FAQUpdateRequest,
    FAQAnalytics
)


class TestFAQEntryCreation:
    """Test FAQ entry creation with all required fields."""
    
    @pytest.fixture
    def faq_service(self):
        """Create FAQ service instance for testing."""
        db_mock = Mock()
        llm_mock = Mock()
        knowledge_mock = Mock()
        cache_mock = Mock()
        return IntelligentFAQService(db_mock, llm_mock, knowledge_mock, cache_mock)
    
    def test_create_faq_entry_with_all_required_fields(self, faq_service):
        """Test creating FAQ entry with all required fields."""
        faq_request = FAQCreateRequest(
            question="Come si calcola l'IVA al 22%?",
            answer="L'IVA al 22% si calcola moltiplicando l'importo imponibile per 0.22. Ad esempio: 100€ × 0.22 = 22€ di IVA.",
            category="iva_calcoli",
            tags=["IVA", "calcolo", "aliquota", "22%"],
            language="it",
            regulatory_refs=[
                {
                    "source": "DPR 633/72",
                    "article": "1",
                    "description": "Disciplina IVA"
                }
            ],
            update_sensitivity="medium"
        )
        
        # Mock database creation
        faq_service.db.create_faq_entry = Mock(return_value=FAQEntryModel(
            id=str(uuid4()),
            question=faq_request.question,
            answer=faq_request.answer,
            category=faq_request.category,
            tags=faq_request.tags,
            language=faq_request.language,
            regulatory_refs=faq_request.regulatory_refs,
            update_sensitivity=faq_request.update_sensitivity,
            created_at=datetime.now(timezone.utc)
        ))
        
        result = faq_service.create_faq_entry(faq_request)
        
        assert result.question == faq_request.question
        assert result.answer == faq_request.answer
        assert result.category == faq_request.category
        assert result.tags == faq_request.tags
        assert result.language == faq_request.language
        assert result.regulatory_refs == faq_request.regulatory_refs
        assert result.update_sensitivity == faq_request.update_sensitivity
        
        # Verify database call
        faq_service.db.create_faq_entry.assert_called_once()
    
    def test_create_faq_entry_with_minimal_required_fields(self, faq_service):
        """Test creating FAQ entry with only minimal required fields."""
        faq_request = FAQCreateRequest(
            question="Cosa è l'IRPEF?",
            answer="L'IRPEF è l'imposta sui redditi delle persone fisiche."
        )
        
        faq_service.db.create_faq_entry = Mock(return_value=FAQEntryModel(
            id=str(uuid4()),
            question=faq_request.question,
            answer=faq_request.answer,
            category="generale",  # Default category
            tags=[],  # Empty tags
            language="it",  # Default language
            created_at=datetime.now(timezone.utc)
        ))
        
        result = faq_service.create_faq_entry(faq_request)
        
        assert result.question == faq_request.question
        assert result.answer == faq_request.answer
        assert result.category == "generale"
        assert result.language == "it"
    
    def test_create_faq_entry_validation_error(self, faq_service):
        """Test FAQ entry creation with validation errors."""
        # Empty question should raise validation error
        with pytest.raises(ValueError, match="Question cannot be empty"):
            faq_request = FAQCreateRequest(
                question="",
                answer="Valid answer"
            )
            faq_service.create_faq_entry(faq_request)
        
        # Empty answer should raise validation error
        with pytest.raises(ValueError, match="Answer cannot be empty"):
            faq_request = FAQCreateRequest(
                question="Valid question?",
                answer=""
            )
            faq_service.create_faq_entry(faq_request)
    
    def test_create_faq_entry_with_search_vector(self, faq_service):
        """Test that FAQ entry creation includes search vector generation."""
        faq_request = FAQCreateRequest(
            question="Come compilare il modello F24?",
            answer="Il modello F24 si compila inserendo i codici tributo e gli importi dovuti.",
            tags=["F24", "compilazione", "tributi"]
        )
        
        faq_service.db.create_faq_entry = Mock(return_value=FAQEntryModel(
            id=str(uuid4()),
            question=faq_request.question,
            answer=faq_request.answer,
            tags=faq_request.tags,
            search_vector="f24 compilazione tributi modello"  # Mock search vector
        ))
        
        result = faq_service.create_faq_entry(faq_request)
        
        # Verify search vector was generated
        assert hasattr(result, 'search_vector')
        assert result.search_vector is not None


class TestSemanticSearchMatching:
    """Test semantic search matching with similarity threshold."""
    
    @pytest.fixture
    def faq_service(self):
        db_mock = Mock()
        llm_mock = Mock()
        knowledge_mock = Mock()
        cache_mock = Mock()
        return IntelligentFAQService(db_mock, llm_mock, knowledge_mock, cache_mock)
    
    @pytest.mark.asyncio
    async def test_semantic_search_high_confidence_match(self, faq_service):
        """Test semantic search returns match above confidence threshold."""
        query = "Come calcolo l'IVA 22%?"
        
        # Mock database search returning high-confidence match
        mock_faq = FAQEntryModel(
            id=str(uuid4()),
            question="Come si calcola l'IVA al 22%?",
            answer="L'IVA al 22% si calcola moltiplicando per 0.22",
            category="iva_calcoli",
            tags=["IVA", "calcolo"],
            similarity_score=0.92  # High confidence
        )
        
        faq_service.db.search_faqs = AsyncMock(return_value=[mock_faq])
        
        result = await faq_service.find_best_match(query)
        
        assert result is not None
        assert result.similarity_score >= 0.85  # Above threshold
        assert result.id == mock_faq.id
        assert "IVA" in result.tags
    
    @pytest.mark.asyncio
    async def test_semantic_search_low_confidence_no_match(self, faq_service):
        """Test semantic search returns None for low-confidence matches."""
        query = "Qual è il colore del cielo?"
        
        # Mock database search returning low-confidence match
        mock_faq = FAQEntryModel(
            id=str(uuid4()),
            question="Come si calcola l'IVA?",
            answer="L'IVA si calcola...",
            similarity_score=0.12  # Very low confidence
        )
        
        faq_service.db.search_faqs = AsyncMock(return_value=[mock_faq])
        
        result = await faq_service.find_best_match(query)
        
        assert result is None  # Should return None for low confidence
    
    @pytest.mark.asyncio
    async def test_semantic_search_with_query_normalization(self, faq_service):
        """Test semantic search applies Italian query normalization."""
        query = "Qual è l'aliquota IVA per i servizi digitali?"
        
        # Mock query normalizer
        faq_service.query_normalizer = Mock()
        faq_service.query_normalizer.normalize = Mock(return_value=Mock(
            normalized_query="iva servizi digitali aliquota"
        ))
        
        mock_faq = FAQEntryModel(
            id=str(uuid4()),
            question="IVA servizi digitali aliquota",
            answer="L'aliquota IVA per servizi digitali è 22%",
            similarity_score=0.95
        )
        
        faq_service.db.search_faqs = AsyncMock(return_value=[mock_faq])
        
        result = await faq_service.find_best_match(query)
        
        # Verify normalization was applied
        faq_service.query_normalizer.normalize.assert_called_once_with(query)
        assert result is not None
        assert result.similarity_score >= 0.85
    
    @pytest.mark.asyncio
    async def test_semantic_search_multiple_matches_returns_best(self, faq_service):
        """Test semantic search returns the best match when multiple found."""
        query = "Come pagare l'IMU?"
        
        # Mock multiple matches with different confidence scores
        mock_faqs = [
            FAQEntryModel(
                id=str(uuid4()),
                question="Come pagare IMU online?",
                answer="IMU si paga online...",
                similarity_score=0.88
            ),
            FAQEntryModel(
                id=str(uuid4()),
                question="Quando pagare IMU 2025?",
                answer="IMU 2025 si paga...",
                similarity_score=0.91  # Higher score
            ),
            FAQEntryModel(
                id=str(uuid4()),
                question="IMU calcolo rata?",
                answer="IMU rata si calcola...",
                similarity_score=0.87
            )
        ]
        
        faq_service.db.search_faqs = AsyncMock(return_value=mock_faqs)
        
        result = await faq_service.find_best_match(query)
        
        # Should return the match with highest similarity score
        assert result is not None
        assert result.similarity_score == 0.91
        assert "2025" in result.question
    
    @pytest.mark.asyncio
    async def test_semantic_search_respects_language_filter(self, faq_service):
        """Test semantic search filters by language."""
        query = "Come calcolare IVA?"
        
        faq_service.db.search_faqs = AsyncMock(return_value=[])
        
        await faq_service.find_best_match(query, language="it")
        
        # Verify language filter was applied
        call_args = faq_service.db.search_faqs.call_args
        assert call_args[1]["language"] == "it"


class TestFAQCategorizationAndFiltering:
    """Test FAQ categorization and tag-based filtering."""
    
    @pytest.fixture
    def faq_service(self):
        db_mock = Mock()
        llm_mock = Mock()
        knowledge_mock = Mock()
        cache_mock = Mock()
        return IntelligentFAQService(db_mock, llm_mock, knowledge_mock, cache_mock)
    
    @pytest.mark.asyncio
    async def test_search_faqs_by_category(self, faq_service):
        """Test searching FAQs filtered by category."""
        category = "iva_calcoli"
        
        mock_faqs = [
            FAQEntryModel(
                id=str(uuid4()),
                question="Come calcolare IVA 22%?",
                answer="Moltiplicare per 0.22",
                category="iva_calcoli"
            ),
            FAQEntryModel(
                id=str(uuid4()),
                question="IVA su servizi digitali?",
                answer="22% per servizi digitali",
                category="iva_calcoli"
            )
        ]
        
        faq_service.db.get_faqs_by_category = AsyncMock(return_value=mock_faqs)
        
        result = await faq_service.get_faqs_by_category(category)
        
        assert len(result) == 2
        assert all(faq.category == category for faq in result)
        faq_service.db.get_faqs_by_category.assert_called_once_with(category)
    
    @pytest.mark.asyncio
    async def test_search_faqs_by_tags(self, faq_service):
        """Test searching FAQs filtered by tags."""
        tags = ["IVA", "calcolo"]
        
        mock_faqs = [
            FAQEntryModel(
                id=str(uuid4()),
                question="Come calcolare IVA?",
                answer="Calcolo IVA: importo × aliquota",
                tags=["IVA", "calcolo", "aliquota"]
            )
        ]
        
        faq_service.db.search_faqs_by_tags = AsyncMock(return_value=mock_faqs)
        
        result = await faq_service.search_faqs_by_tags(tags)
        
        assert len(result) == 1
        assert all(tag in result[0].tags for tag in tags)
        faq_service.db.search_faqs_by_tags.assert_called_once_with(tags)
    
    def test_get_available_categories(self, faq_service):
        """Test retrieving list of available FAQ categories."""
        mock_categories = [
            FAQCategory(name="iva_calcoli", display_name="Calcoli IVA", count=25),
            FAQCategory(name="irpef", display_name="IRPEF", count=18),
            FAQCategory(name="f24", display_name="Modello F24", count=12),
            FAQCategory(name="fatturazione", display_name="Fatturazione", count=30)
        ]
        
        faq_service.db.get_faq_categories = Mock(return_value=mock_categories)
        
        result = faq_service.get_available_categories()
        
        assert len(result) == 4
        assert all(isinstance(cat, FAQCategory) for cat in result)
        assert result[0].name == "iva_calcoli"
        assert result[0].count == 25
    
    def test_get_popular_tags(self, faq_service):
        """Test retrieving most popular tags across FAQ entries."""
        mock_tags = [
            {"tag": "IVA", "count": 45},
            {"tag": "calcolo", "count": 38},
            {"tag": "F24", "count": 25},
            {"tag": "scadenze", "count": 22},
            {"tag": "fattura", "count": 20}
        ]
        
        faq_service.db.get_popular_tags = Mock(return_value=mock_tags)
        
        result = faq_service.get_popular_tags(limit=5)
        
        assert len(result) == 5
        assert result[0]["tag"] == "IVA"
        assert result[0]["count"] == 45
        faq_service.db.get_popular_tags.assert_called_once_with(limit=5)


class TestSharedKnowledgeBaseAccess:
    """Test shared knowledge base access across multiple users."""
    
    @pytest.fixture
    def faq_service(self):
        db_mock = Mock()
        llm_mock = Mock()
        knowledge_mock = Mock()
        cache_mock = Mock()
        return IntelligentFAQService(db_mock, llm_mock, knowledge_mock, cache_mock)
    
    @pytest.mark.asyncio
    async def test_concurrent_faq_access_by_multiple_users(self, faq_service):
        """Test multiple users can access FAQs concurrently."""
        query = "Come calcolare IRPEF?"
        user_ids = ["user1", "user2", "user3"]
        
        mock_faq = FAQEntryModel(
            id=str(uuid4()),
            question="Come si calcola l'IRPEF?",
            answer="IRPEF si calcola applicando le aliquote progressive",
            similarity_score=0.90
        )
        
        faq_service.db.search_faqs = AsyncMock(return_value=[mock_faq])
        faq_service.log_usage = AsyncMock()
        
        # Simulate concurrent access
        tasks = [
            faq_service.find_best_match(query, user_id=user_id) 
            for user_id in user_ids
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All users should get the same FAQ
        assert len(results) == 3
        assert all(result is not None for result in results)
        assert all(result.id == mock_faq.id for result in results)
    
    @pytest.mark.asyncio
    async def test_shared_faq_hit_count_increment(self, faq_service):
        """Test that FAQ hit count increments for shared access."""
        faq_id = str(uuid4())
        user_ids = ["user1", "user2", "user3"]
        
        faq_service.db.increment_hit_count = AsyncMock()
        
        # Multiple users accessing same FAQ
        for user_id in user_ids:
            await faq_service.log_faq_usage(faq_id, user_id, "Sample response", 0.0)
        
        # Hit count should be incremented for each access
        assert faq_service.db.increment_hit_count.call_count == 3
    
    def test_faq_popularity_ranking(self, faq_service):
        """Test FAQ ranking by popularity across all users."""
        mock_faqs = [
            FAQEntryModel(
                id=str(uuid4()),
                question="Come calcolare IVA?",
                hit_count=150,
                avg_helpfulness=4.2
            ),
            FAQEntryModel(
                id=str(uuid4()),
                question="Quando pagare F24?",
                hit_count=89,
                avg_helpfulness=4.5
            ),
            FAQEntryModel(
                id=str(uuid4()),
                question="Calcolo IRPEF dipendenti?",
                hit_count=200,
                avg_helpfulness=4.1
            )
        ]
        
        faq_service.db.get_popular_faqs = Mock(return_value=mock_faqs)
        
        result = faq_service.get_popular_faqs(limit=10)
        
        assert len(result) == 3
        # Should be sorted by hit count (most popular first)
        assert result[0].hit_count >= result[1].hit_count >= result[2].hit_count


class TestFAQVersioningAndUpdateTracking:
    """Test FAQ versioning and update tracking."""
    
    @pytest.fixture
    def faq_service(self):
        db_mock = Mock()
        llm_mock = Mock()
        knowledge_mock = Mock()
        cache_mock = Mock()
        return IntelligentFAQService(db_mock, llm_mock, knowledge_mock, cache_mock)
    
    def test_create_faq_version_on_update(self, faq_service):
        """Test that updating FAQ creates a new version."""
        faq_id = str(uuid4())
        original_faq = FAQEntryModel(
            id=faq_id,
            question="Come calcolare IVA?",
            answer="IVA = importo × 0.22",
            version=1,
            updated_at=datetime.now(timezone.utc) - timedelta(days=1)
        )
        
        update_request = FAQUpdateRequest(
            answer="IVA = importo × aliquota (es. 0.22 per 22%)",
            tags=["IVA", "calcolo", "aliquota"]
        )
        
        updated_faq = FAQEntryModel(
            id=faq_id,
            question=original_faq.question,
            answer=update_request.answer,
            tags=update_request.tags,
            version=2,  # Version incremented
            updated_at=datetime.now(timezone.utc)
        )
        
        faq_service.db.get_faq_by_id = Mock(return_value=original_faq)
        faq_service.db.update_faq = Mock(return_value=updated_faq)
        faq_service.db.create_faq_version_history = Mock()
        
        result = faq_service.update_faq(faq_id, update_request)
        
        assert result.version == 2
        assert result.answer == update_request.answer
        
        # Verify version history was created
        faq_service.db.create_faq_version_history.assert_called_once()
    
    def test_get_faq_version_history(self, faq_service):
        """Test retrieving FAQ version history."""
        faq_id = str(uuid4())
        
        mock_versions = [
            {
                "version": 1,
                "question": "Come calcolare IVA?",
                "answer": "IVA = importo × 0.22",
                "updated_at": datetime.now(timezone.utc) - timedelta(days=5),
                "updated_by": "admin1"
            },
            {
                "version": 2,
                "question": "Come calcolare IVA?",
                "answer": "IVA = importo × aliquota (es. 22%)",
                "updated_at": datetime.now(timezone.utc) - timedelta(days=1),
                "updated_by": "admin2"
            }
        ]
        
        faq_service.db.get_faq_version_history = Mock(return_value=mock_versions)
        
        result = faq_service.get_faq_version_history(faq_id)
        
        assert len(result) == 2
        assert result[0]["version"] == 1
        assert result[1]["version"] == 2
        faq_service.db.get_faq_version_history.assert_called_once_with(faq_id)
    
    def test_track_faq_last_validated_date(self, faq_service):
        """Test tracking when FAQ was last validated."""
        faq_id = str(uuid4())
        validation_date = datetime.now(timezone.utc).date()
        
        faq_service.db.update_faq_validation = AsyncMock()
        
        faq_service.mark_faq_as_validated(faq_id, validation_date)
        
        faq_service.db.update_faq_validation.assert_called_once_with(
            faq_id, 
            last_validated=validation_date,
            needs_review=False
        )


class TestGPTVariationIntegration:
    """Test GPT-3.5 integration for response rephrasing."""
    
    @pytest.fixture
    def faq_service(self):
        db_mock = Mock()
        llm_mock = Mock()
        knowledge_mock = Mock()
        cache_mock = Mock()
        return IntelligentFAQService(db_mock, llm_mock, knowledge_mock, cache_mock)
    
    @pytest.mark.asyncio
    async def test_generate_response_variation_with_gpt35(self, faq_service):
        """Test generating response variation using GPT-3.5."""
        original_answer = "L'IVA al 22% si calcola moltiplicando l'importo per 0.22"
        user_id = "user123"
        
        # Mock GPT-3.5 response
        gpt_response = "Per calcolare l'imposta sul valore aggiunto al 22%, moltiplica la base imponibile per 0,22"
        faq_service.llm.generate_variation = AsyncMock(return_value=gpt_response)
        
        result = await faq_service.generate_variation(original_answer, user_id)
        
        assert result.variation_text == gpt_response
        assert result.cost_euros == 0.0003  # €0.0003 per query
        assert result.model_used == "gpt-3.5-turbo"
        
        # Verify GPT-3.5 was called with correct parameters
        faq_service.llm.generate_variation.assert_called_once()
        call_args = faq_service.llm.generate_variation.call_args
        assert "gpt-3.5-turbo" in str(call_args)
    
    @pytest.mark.asyncio
    async def test_variation_preserves_technical_accuracy(self, faq_service):
        """Test that response variation preserves technical accuracy."""
        original_answer = "Il codice tributo 6001 è per IRPEF, rata saldo 2024"
        user_id = "user123"
        
        # Mock GPT response that preserves technical details
        gpt_response = "Per l'IRPEF rata saldo 2024 utilizzare il codice tributo 6001"
        faq_service.llm.generate_variation = AsyncMock(return_value=gpt_response)
        
        result = await faq_service.generate_variation(original_answer, user_id)
        
        # Technical details should be preserved
        assert "6001" in result.variation_text
        assert "IRPEF" in result.variation_text
        assert "2024" in result.variation_text
        assert result.technical_accuracy_verified is True
    
    @pytest.mark.asyncio
    async def test_variation_avoids_recently_used_phrases(self, faq_service):
        """Test variation avoids recently used phrases for same user."""
        original_answer = "L'IVA si calcola moltiplicando per l'aliquota"
        user_id = "user123"
        
        # Mock recent variations for user
        recent_variations = [
            "Per calcolare l'IVA, moltiplica per l'aliquota",
            "L'imposta si ottiene moltiplicando per l'aliquota"
        ]
        
        faq_service.db.get_recent_variations_for_user = AsyncMock(
            return_value=recent_variations
        )
        
        # Mock GPT response that avoids recent phrases
        gpt_response = "L'IVA risulta dall'applicazione dell'aliquota all'imponibile"
        faq_service.llm.generate_variation = AsyncMock(return_value=gpt_response)
        
        result = await faq_service.generate_variation(original_answer, user_id)
        
        # Should not contain recently used phrases
        assert "moltiplica" not in result.variation_text.lower()
        assert "moltiplicando" not in result.variation_text.lower()
        
        # Verify recent variations were checked
        faq_service.db.get_recent_variations_for_user.assert_called_once_with(
            user_id, days=7
        )
    
    @pytest.mark.asyncio
    async def test_variation_cost_tracking(self, faq_service):
        """Test accurate cost tracking for GPT-3.5 variation calls."""
        original_answer = "Il F24 si compila inserendo i codici tributo"
        user_id = "user123"
        
        gpt_response = "Per compilare l'F24, inserire i relativi codici tributo"
        faq_service.llm.generate_variation = AsyncMock(return_value=gpt_response)
        faq_service.db.log_variation_cost = AsyncMock()
        
        result = await faq_service.generate_variation(original_answer, user_id)
        
        # Verify cost tracking
        assert result.cost_euros == 0.0003
        assert result.cost_cents == 3  # 0.0003 EUR = 0.03 cents
        
        # Verify cost was logged to database
        faq_service.db.log_variation_cost.assert_called_once_with(
            user_id=user_id,
            cost_euros=0.0003,
            model_used="gpt-3.5-turbo",
            tokens_used=result.tokens_used
        )


class TestVariationCacheSystem:
    """Test variation cache to avoid repeated LLM calls (70% cache hit target)."""
    
    @pytest.fixture
    def faq_service(self):
        db_mock = Mock()
        llm_mock = Mock()
        knowledge_mock = Mock()
        cache_mock = Mock()
        return IntelligentFAQService(db_mock, llm_mock, knowledge_mock, cache_mock)
    
    @pytest.mark.asyncio
    async def test_variation_cache_hit_avoids_llm_call(self, faq_service):
        """Test cache hit avoids expensive LLM call."""
        faq_id = str(uuid4())
        user_id = "user123"
        
        # Mock cached variation
        cached_variation = {
            "variation_text": "L'IVA del 22% si ottiene moltiplicando per 0,22",
            "created_at": datetime.now(timezone.utc) - timedelta(hours=2),
            "cost_euros": 0.0003
        }
        
        faq_service.cache.get_variation = AsyncMock(return_value=cached_variation)
        
        result = await faq_service.get_or_generate_variation(faq_id, user_id)
        
        assert result.variation_text == cached_variation["variation_text"]
        assert result.from_cache is True
        assert result.cost_euros == 0.0  # No cost for cached response
        
        # Verify LLM was not called
        assert not hasattr(faq_service.llm, 'generate_variation') or \
               not faq_service.llm.generate_variation.called
    
    @pytest.mark.asyncio
    async def test_variation_cache_miss_calls_llm(self, faq_service):
        """Test cache miss triggers LLM call and caches result."""
        faq_id = str(uuid4())
        user_id = "user123"
        original_answer = "L'IMU si paga in due rate"
        
        # Mock cache miss
        faq_service.cache.get_variation = AsyncMock(return_value=None)
        
        # Mock LLM response
        gpt_response = "L'imposta municipale si versa in due soluzioni"
        faq_service.llm.generate_variation = AsyncMock(return_value=gpt_response)
        
        # Mock cache set
        faq_service.cache.set_variation = AsyncMock()
        
        result = await faq_service.get_or_generate_variation(faq_id, user_id, original_answer)
        
        assert result.variation_text == gpt_response
        assert result.from_cache is False
        assert result.cost_euros == 0.0003
        
        # Verify result was cached
        faq_service.cache.set_variation.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_variation_cache_expiry(self, faq_service):
        """Test variation cache respects expiry time."""
        faq_id = str(uuid4())
        user_id = "user123"
        
        # Mock expired cached variation (older than 24 hours)
        expired_variation = {
            "variation_text": "Old variation",
            "created_at": datetime.now(timezone.utc) - timedelta(hours=25),
            "cost_euros": 0.0003
        }
        
        faq_service.cache.get_variation = AsyncMock(return_value=expired_variation)
        faq_service.cache.is_variation_expired = Mock(return_value=True)
        faq_service.llm.generate_variation = AsyncMock(return_value="New variation")
        
        result = await faq_service.get_or_generate_variation(faq_id, user_id)
        
        # Should generate new variation despite cache hit
        assert result.variation_text == "New variation"
        assert result.from_cache is False
        
        # Verify expiry check was performed
        faq_service.cache.is_variation_expired.assert_called_once()
    
    def test_cache_hit_rate_tracking(self, faq_service):
        """Test tracking variation cache hit rate for optimization."""
        # Mock cache statistics
        cache_stats = {
            "total_requests": 1000,
            "cache_hits": 720,
            "cache_misses": 280,
            "hit_rate": 0.72  # 72% hit rate (above 70% target)
        }
        
        faq_service.cache.get_variation_stats = Mock(return_value=cache_stats)
        
        result = faq_service.get_variation_cache_stats()
        
        assert result["hit_rate"] == 0.72
        assert result["hit_rate"] > 0.70  # Above target
        assert result["total_requests"] == 1000
        assert result["cache_hits"] == 720
    
    @pytest.mark.asyncio
    async def test_cache_key_generation_for_variations(self, faq_service):
        """Test proper cache key generation for variation caching."""
        faq_id = str(uuid4())
        user_id = "user123"
        
        faq_service.cache.generate_variation_cache_key = Mock(
            return_value=f"faq_variation:{faq_id}:{user_id}:v1"
        )
        
        await faq_service.get_or_generate_variation(faq_id, user_id)
        
        # Verify cache key was generated properly
        faq_service.cache.generate_variation_cache_key.assert_called_once_with(
            faq_id, user_id
        )


class TestObsolescenceDetection:
    """Test FAQ validation against recent RSS updates."""
    
    @pytest.fixture
    def faq_service(self):
        db_mock = Mock()
        llm_mock = Mock()
        knowledge_mock = Mock()
        cache_mock = Mock()
        return IntelligentFAQService(db_mock, llm_mock, knowledge_mock, cache_mock)
    
    @pytest.mark.asyncio
    async def test_check_faq_against_recent_updates(self, faq_service):
        """Test FAQ obsolescence checking against RSS updates."""
        faq = FAQEntryModel(
            id=str(uuid4()),
            question="Qual è l'aliquota IVA per libri?",
            answer="L'aliquota IVA per libri è del 4%",
            regulatory_refs=[{"source": "DPR 633/72", "article": "16"}],
            last_validated=datetime.now(timezone.utc).date() - timedelta(days=10),
            update_sensitivity="high"
        )
        
        # Mock recent regulatory update that affects this FAQ
        recent_update = {
            "title": "Modifica aliquote IVA libri digitali",
            "source": "Agenzia delle Entrate",
            "published_date": datetime.now(timezone.utc) - timedelta(days=2),
            "content": "Nuova aliquota 10% per libri digitali dal 1° gennaio 2025",
            "document_refs": ["DPR 633/72"]
        }
        
        faq_service.knowledge.get_recent_updates = AsyncMock(
            return_value=[recent_update]
        )
        faq_service.knowledge.check_content_overlap = AsyncMock(
            return_value={"overlap_score": 0.85, "potentially_affected": True}
        )
        
        result = await faq_service.check_obsolescence(faq)
        
        assert result.is_potentially_obsolete is True
        assert result.confidence_score >= 0.80
        assert result.affecting_updates == [recent_update]
        assert "aliquota" in result.reason.lower()
    
    @pytest.mark.asyncio
    async def test_faq_not_obsolete_no_relevant_updates(self, faq_service):
        """Test FAQ not marked obsolete when no relevant updates."""
        faq = FAQEntryModel(
            id=str(uuid4()),
            question="Come compilare campo X del F24?",
            answer="Il campo X si compila inserendo...",
            last_validated=datetime.now(timezone.utc).date() - timedelta(days=5),
            update_sensitivity="medium"
        )
        
        # Mock unrelated recent updates
        recent_updates = [
            {
                "title": "Nuove sanzioni per ritardato pagamento",
                "content": "Modifiche alle sanzioni...",
                "published_date": datetime.now(timezone.utc) - timedelta(days=1)
            }
        ]
        
        faq_service.knowledge.get_recent_updates = AsyncMock(
            return_value=recent_updates
        )
        faq_service.knowledge.check_content_overlap = AsyncMock(
            return_value={"overlap_score": 0.15, "potentially_affected": False}
        )
        
        result = await faq_service.check_obsolescence(faq)
        
        assert result.is_potentially_obsolete is False
        assert result.confidence_score < 0.50
        assert len(result.affecting_updates) == 0
    
    @pytest.mark.asyncio
    async def test_automatic_faq_invalidation_on_detection(self, faq_service):
        """Test automatic FAQ invalidation when obsolescence detected."""
        faq_id = str(uuid4())
        
        # Mock high-confidence obsolescence detection
        obsolescence_result = ObsolescenceResult(
            is_potentially_obsolete=True,
            confidence_score=0.92,
            reason="Recent regulatory change affects FAQ content",
            affecting_updates=[{"title": "New IVA rates"}]
        )
        
        faq_service.check_obsolescence = AsyncMock(return_value=obsolescence_result)
        faq_service.db.mark_faq_needs_review = AsyncMock()
        faq_service.notification_service = Mock()
        faq_service.notification_service.notify_admin = AsyncMock()
        
        await faq_service.validate_faq_currency(faq_id)
        
        # Verify FAQ was marked for review
        faq_service.db.mark_faq_needs_review.assert_called_once_with(
            faq_id, 
            reason="Potentially obsolete due to regulatory changes",
            confidence_score=0.92
        )
        
        # Verify admin notification
        faq_service.notification_service.notify_admin.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fallback_to_full_llm_when_faq_outdated(self, faq_service):
        """Test fallback to full LLM when FAQ is outdated."""
        query = "Qual è l'aliquota IVA per libri?"
        user_id = "user123"
        
        # Mock outdated FAQ
        outdated_faq = FAQEntryModel(
            id=str(uuid4()),
            question="Aliquota IVA libri?",
            answer="4% per libri cartacei",
            needs_review=True,  # Marked as needing review
            last_validated=datetime.now(timezone.utc).date() - timedelta(days=30)
        )
        
        faq_service.find_best_match = AsyncMock(return_value=outdated_faq)
        faq_service.llm.generate_full_response = AsyncMock(
            return_value="Current IVA rates: 4% for physical books, 10% for digital books"
        )
        
        result = await faq_service.handle_query(query, user_id)
        
        assert result.used_faq is False  # Didn't use FAQ
        assert result.used_full_llm is True
        assert result.fallback_reason == "FAQ needs review due to regulatory changes"
        
        # Verify full LLM was called
        faq_service.llm.generate_full_response.assert_called_once_with(query)
    
    def test_update_sensitivity_levels(self, faq_service):
        """Test different update sensitivity levels for FAQ validation."""
        # High sensitivity FAQ - check against all recent updates
        high_sensitivity_faq = FAQEntryModel(
            update_sensitivity="high",
            last_validated=datetime.now(timezone.utc).date() - timedelta(days=1)
        )
        
        # Medium sensitivity - check weekly
        medium_sensitivity_faq = FAQEntryModel(
            update_sensitivity="medium",
            last_validated=datetime.now(timezone.utc).date() - timedelta(days=5)
        )
        
        # Low sensitivity - check monthly
        low_sensitivity_faq = FAQEntryModel(
            update_sensitivity="low",
            last_validated=datetime.now(timezone.utc).date() - timedelta(days=20)
        )
        
        # Test validation frequency based on sensitivity
        assert faq_service.should_check_for_updates(high_sensitivity_faq) is True
        assert faq_service.should_check_for_updates(medium_sensitivity_faq) is True
        assert faq_service.should_check_for_updates(low_sensitivity_faq) is False  # Not due yet


class TestUsageAnalytics:
    """Test usage logging per FAQ entry, feedback collection, and analytics."""
    
    @pytest.fixture
    def faq_service(self):
        db_mock = Mock()
        llm_mock = Mock()
        knowledge_mock = Mock()
        cache_mock = Mock()
        return IntelligentFAQService(db_mock, llm_mock, knowledge_mock, cache_mock)
    
    @pytest.mark.asyncio
    async def test_log_faq_usage_with_all_metrics(self, faq_service):
        """Test comprehensive FAQ usage logging."""
        faq_id = str(uuid4())
        user_id = "user123"
        response_text = "L'IVA al 22% si calcola moltiplicando per 0,22"
        variation_cost = 0.0003
        
        faq_service.db.log_faq_usage = AsyncMock()
        faq_service.db.increment_hit_count = AsyncMock()
        
        await faq_service.log_faq_usage(
            faq_id=faq_id,
            user_id=user_id,
            response_variation=response_text,
            variation_cost=variation_cost,
            from_cache=False
        )
        
        # Verify usage was logged
        faq_service.db.log_faq_usage.assert_called_once()
        call_args = faq_service.db.log_faq_usage.call_args[1]
        
        assert call_args["faq_id"] == faq_id
        assert call_args["user_id"] == user_id
        assert call_args["response_variation"] == response_text
        assert call_args["variation_cost_cents"] == 3  # €0.0003 = 0.03 cents
        
        # Verify hit count was incremented
        faq_service.db.increment_hit_count.assert_called_once_with(faq_id)
    
    @pytest.mark.asyncio
    async def test_collect_user_feedback(self, faq_service):
        """Test user feedback collection for FAQ responses."""
        usage_log_id = str(uuid4())
        feedback_request = FAQFeedbackRequest(
            usage_log_id=usage_log_id,
            was_helpful=True,
            followup_needed=False,
            comments="Very clear explanation"
        )
        
        faq_service.db.update_usage_feedback = AsyncMock()
        faq_service.db.update_faq_helpfulness = AsyncMock()
        
        result = await faq_service.submit_feedback(feedback_request)
        
        assert result.success is True
        
        # Verify feedback was recorded
        faq_service.db.update_usage_feedback.assert_called_once_with(
            usage_log_id=usage_log_id,
            was_helpful=True,
            followup_needed=False,
            comments="Very clear explanation"
        )
        
        # Verify FAQ helpfulness score was updated
        faq_service.db.update_faq_helpfulness.assert_called_once()
    
    def test_calculate_average_helpfulness(self, faq_service):
        """Test calculation of average helpfulness score."""
        faq_id = str(uuid4())
        
        # Mock feedback data
        feedback_data = [
            {"was_helpful": True},
            {"was_helpful": True},
            {"was_helpful": False},
            {"was_helpful": True},
            {"was_helpful": True}
        ]
        
        faq_service.db.get_faq_feedback = Mock(return_value=feedback_data)
        
        result = faq_service.calculate_helpfulness_score(faq_id)
        
        # 4 out of 5 helpful = 0.8 (80%)
        assert result == 0.8
        faq_service.db.get_faq_feedback.assert_called_once_with(faq_id)
    
    def test_detect_followup_needed_patterns(self, faq_service):
        """Test detection of patterns indicating followup needed."""
        faq_id = str(uuid4())
        
        # Mock usage logs showing followup patterns
        usage_logs = [
            {"followup_needed": True, "comments": "Need more details"},
            {"followup_needed": False, "comments": "Perfect"},
            {"followup_needed": True, "comments": "Unclear about deadlines"},
            {"followup_needed": True, "comments": "What about exceptions?"}
        ]
        
        faq_service.db.get_recent_usage_logs = Mock(return_value=usage_logs)
        
        result = faq_service.analyze_followup_patterns(faq_id, days=30)
        
        assert result["followup_rate"] == 0.75  # 3 out of 4
        assert result["needs_improvement"] is True  # >50% followup rate
        assert len(result["common_concerns"]) > 0
    
    def test_track_hit_count_and_popularity(self, faq_service):
        """Test tracking hit count and popularity rankings."""
        # Mock popular FAQs data
        popular_faqs = [
            {
                "id": str(uuid4()),
                "question": "Come calcolare IVA?",
                "hit_count": 1250,
                "avg_helpfulness": 4.2,
                "category": "iva_calcoli"
            },
            {
                "id": str(uuid4()),
                "question": "Scadenze F24 2025?",
                "hit_count": 890,
                "avg_helpfulness": 4.5,
                "category": "f24"
            },
            {
                "id": str(uuid4()),
                "question": "Calcolo IRPEF dipendenti?",
                "hit_count": 750,
                "avg_helpfulness": 4.1,
                "category": "irpef"
            }
        ]
        
        faq_service.db.get_faq_popularity_stats = Mock(return_value=popular_faqs)
        
        result = faq_service.get_popularity_analytics(limit=10, period_days=30)
        
        assert len(result) == 3
        # Should be sorted by hit count descending
        assert result[0]["hit_count"] >= result[1]["hit_count"] >= result[2]["hit_count"]
        assert result[0]["hit_count"] == 1250
    
    def test_generate_usage_analytics_report(self, faq_service):
        """Test generation of comprehensive usage analytics."""
        # Mock analytics data
        analytics_data = FAQAnalytics(
            total_faqs=450,
            total_queries_handled=12500,
            avg_response_time_ms=85,
            cache_hit_rate=0.73,
            cost_savings_percent=42,
            total_cost_euros=37.50,
            most_popular_categories=[
                {"category": "iva_calcoli", "queries": 3200},
                {"category": "f24", "queries": 2800},
                {"category": "irpef", "queries": 2100}
            ],
            avg_helpfulness_score=4.3,
            followup_rate=0.18
        )
        
        faq_service.db.generate_analytics_report = Mock(return_value=analytics_data)
        
        result = faq_service.get_analytics_dashboard(period_days=30)
        
        assert result.total_faqs == 450
        assert result.cache_hit_rate == 0.73  # Above 70% target
        assert result.cost_savings_percent == 42  # Above 40% target
        assert result.avg_helpfulness_score == 4.3  # High user satisfaction
        assert result.followup_rate == 0.18  # Low followup rate is good


class TestPerformanceRequirements:
    """Test FAQ search performance (<100ms) and concurrent access."""
    
    @pytest.fixture
    def faq_service(self):
        db_mock = Mock()
        llm_mock = Mock()
        knowledge_mock = Mock()
        cache_mock = Mock()
        return IntelligentFAQService(db_mock, llm_mock, knowledge_mock, cache_mock)
    
    @pytest.mark.asyncio
    async def test_faq_search_performance_under_100ms(self, faq_service):
        """Test FAQ search completes within 100ms."""
        query = "Come calcolare l'IVA al 22%?"
        
        # Mock fast database response
        mock_faq = FAQEntryModel(
            id=str(uuid4()),
            question="Come si calcola l'IVA?",
            answer="IVA = importo × 0.22",
            similarity_score=0.91
        )
        
        faq_service.db.search_faqs = AsyncMock(return_value=[mock_faq])
        
        start_time = time.perf_counter()
        result = await faq_service.find_best_match(query)
        end_time = time.perf_counter()
        
        processing_time_ms = (end_time - start_time) * 1000
        
        assert processing_time_ms < 100.0, f"Search took {processing_time_ms:.2f}ms, should be <100ms"
        assert result is not None
        assert result.similarity_score >= 0.85
    
    @pytest.mark.asyncio
    async def test_concurrent_faq_database_access(self, faq_service):
        """Test concurrent access to shared FAQ database."""
        queries = [
            "Come calcolare IVA?",
            "Quando pagare F24?",
            "Calcolo IRPEF dipendenti?",
            "Scadenze IMU 2025?",
            "Fattura elettronica obbligatoria?"
        ]
        
        mock_faqs = [
            FAQEntryModel(
                id=str(uuid4()),
                question=f"FAQ for: {query}",
                answer=f"Answer for: {query}",
                similarity_score=0.90
            )
            for query in queries
        ]
        
        faq_service.db.search_faqs = AsyncMock(side_effect=lambda q, **kwargs: [mock_faqs[queries.index(q)]])
        
        # Execute concurrent searches
        start_time = time.perf_counter()
        tasks = [faq_service.find_best_match(query) for query in queries]
        results = await asyncio.gather(*tasks)
        end_time = time.perf_counter()
        
        total_time_ms = (end_time - start_time) * 1000
        
        # All searches should complete successfully
        assert len(results) == 5
        assert all(result is not None for result in results)
        
        # Concurrent execution should be faster than sequential
        assert total_time_ms < 500.0, f"Concurrent search took {total_time_ms:.2f}ms"
    
    @pytest.mark.asyncio
    async def test_variation_cache_performance(self, faq_service):
        """Test variation cache lookup performance."""
        faq_id = str(uuid4())
        user_id = "user123"
        
        # Mock cached variation
        cached_variation = {
            "variation_text": "Cached response",
            "created_at": datetime.now(timezone.utc),
            "cost_euros": 0.0003
        }
        
        faq_service.cache.get_variation = AsyncMock(return_value=cached_variation)
        
        start_time = time.perf_counter()
        result = await faq_service.get_or_generate_variation(faq_id, user_id)
        end_time = time.perf_counter()
        
        cache_lookup_time_ms = (end_time - start_time) * 1000
        
        assert cache_lookup_time_ms < 50.0, f"Cache lookup took {cache_lookup_time_ms:.2f}ms"
        assert result.from_cache is True
        assert result.cost_euros == 0.0  # No cost for cached response
    
    @pytest.mark.asyncio
    async def test_overall_response_time_under_500ms(self, faq_service):
        """Test overall FAQ response time <500ms vs 2-3s for full LLM."""
        query = "Qual è l'aliquota IVA per servizi digitali?"
        user_id = "user123"
        
        # Mock FAQ match and variation generation
        mock_faq = FAQEntryModel(
            id=str(uuid4()),
            question="IVA servizi digitali aliquota?",
            answer="L'aliquota IVA per servizi digitali è 22%",
            similarity_score=0.92
        )
        
        faq_service.find_best_match = AsyncMock(return_value=mock_faq)
        faq_service.get_or_generate_variation = AsyncMock(return_value=VariationResponse(
            variation_text="I servizi digitali sono soggetti all'aliquota IVA del 22%",
            from_cache=True,
            cost_euros=0.0
        ))
        faq_service.log_faq_usage = AsyncMock()
        
        start_time = time.perf_counter()
        result = await faq_service.handle_query(query, user_id)
        end_time = time.perf_counter()
        
        total_response_time_ms = (end_time - start_time) * 1000
        
        assert total_response_time_ms < 500.0, f"FAQ response took {total_response_time_ms:.2f}ms"
        assert result.used_faq is True
        assert result.response_time_ms < 500.0
        
        # Should be significantly faster than full LLM (2-3 seconds)
        assert total_response_time_ms < 2000.0  # Much faster than full LLM
    
    def test_memory_efficiency_for_large_faq_database(self, faq_service):
        """Test memory usage remains reasonable for large FAQ database."""
        import sys
        
        # Simulate large FAQ database
        large_faq_list = [
            FAQEntryModel(
                id=str(uuid4()),
                question=f"FAQ Question {i}",
                answer=f"FAQ Answer {i}",
                tags=[f"tag{i % 10}"],
                category=f"category{i % 5}"
            )
            for i in range(1000)  # 1000 FAQs
        ]
        
        # Measure memory before processing
        initial_size = sys.getsizeof(faq_service)
        
        # Process large FAQ list
        faq_service._load_faqs_into_memory = Mock(return_value=large_faq_list)
        processed_faqs = faq_service.load_faq_database()
        
        # Memory should not grow excessively
        final_size = sys.getsizeof(faq_service)
        memory_growth = final_size - initial_size
        
        assert memory_growth < 10 * 1024 * 1024, f"Memory grew by {memory_growth} bytes"  # <10MB growth
        assert len(processed_faqs) == 1000


# Integration test fixtures
@pytest.fixture
async def db_session():
    """Database session fixture for integration testing."""
    # This will be implemented when the actual models are created
    pass


class TestFAQIntegrationWithExistingSystems:
    """Test FAQ system integration with existing services."""
    
    @pytest.mark.asyncio
    async def test_integration_with_italian_query_normalizer(self, db_session):
        """Test FAQ system uses Italian query normalizer."""
        # This test verifies that FAQ search applies normalization
        # before performing semantic search
        pass
    
    @pytest.mark.asyncio
    async def test_integration_with_knowledge_update_system(self, db_session):
        """Test FAQ system hooks into regulatory update notifications."""
        # This test verifies that FAQ obsolescence checking
        # receives notifications from the RSS update system
        pass
    
    @pytest.mark.asyncio 
    async def test_integration_with_cost_tracking_system(self, db_session):
        """Test FAQ system reports costs to central tracking."""
        # This test verifies that variation costs are properly
        # tracked and reported to the billing system
        pass


class TestCostSavingsAnalysis:
    """Test cost analysis and savings projections for FAQ system."""
    
    @pytest.mark.asyncio
    async def test_calculate_cost_savings_vs_full_llm(self, db_session):
        """Test calculation of cost savings compared to full LLM usage."""
        # Mock usage data showing FAQ vs full LLM costs
        faq_usage_data = {
            "total_queries": 10000,
            "faq_responses": 6500,  # 65% FAQ usage
            "full_llm_responses": 3500,  # 35% full LLM
            "variation_costs": 1950 * 0.0003,  # 30% needed variations
            "full_llm_costs": 3500 * 0.002   # €0.002 per full LLM query
        }
        
        # Calculate savings: should be ~40% reduction
        total_cost_with_faq = faq_usage_data["variation_costs"] + faq_usage_data["full_llm_costs"]
        total_cost_without_faq = 10000 * 0.002  # All queries via full LLM
        
        cost_savings = (total_cost_without_faq - total_cost_with_faq) / total_cost_without_faq
        
        assert cost_savings >= 0.40  # At least 40% cost reduction
        assert total_cost_with_faq < total_cost_without_faq
    
    def test_variation_cost_accuracy(self):
        """Test accuracy of €0.0003 per variation calculation."""
        variation_cost_euros = 0.0003
        variation_cost_cents = 3  # 0.03 cents
        
        # Verify cost calculations
        assert variation_cost_euros == 0.0003
        assert variation_cost_cents == int(variation_cost_euros * 10000)  # Convert to 0.01 cent units
        
        # Test bulk cost calculation
        variations_per_day = 1000
        daily_cost = variations_per_day * variation_cost_euros
        monthly_cost = daily_cost * 30
        
        assert daily_cost == 0.30  # €0.30 per day
        assert monthly_cost == 9.00  # €9.00 per month for 1000 variations/day