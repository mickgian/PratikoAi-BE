"""
Test suite for RAG STEP 20 - Golden fast-path eligibility check.

This module tests the golden fast-path eligibility logic that determines
whether a query can bypass document processing and use the golden answer
fast-path for known questions.

Based on Mermaid diagram: GoldenFastGate (Golden fast-path eligible? no doc or quick check safe)
"""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from app.services.golden_fast_path import (
    GoldenFastPathService,
    EligibilityResult,
    EligibilityDecision
)


class TestGoldenFastPathEligibility:
    """Test golden fast-path eligibility decision logic."""
    
    @pytest.fixture
    def golden_service(self):
        """Create golden fast-path service instance for testing."""
        return GoldenFastPathService()
    
    @pytest.fixture
    def sample_query(self):
        """Sample query data for testing."""
        return {
            "query": "Quali sono le aliquote IVA in Italia?",
            "attachments": [],
            "user_id": "test_user_123",
            "session_id": "session_456",
            "canonical_facts": ["aliquote", "iva", "italia"],
            "query_signature": "abc123def456",
            "trace_id": "trace_789"
        }
    
    @pytest.fixture
    def sample_query_with_attachments(self):
        """Sample query with attachments for testing."""
        return {
            "query": "Analizza questo contratto per le clausole IVA",
            "attachments": [
                {"filename": "contratto.pdf", "size": 1024},
                {"filename": "allegato.xlsx", "size": 512}
            ],
            "user_id": "test_user_123", 
            "session_id": "session_456",
            "canonical_facts": ["analizza", "contratto", "clausole", "iva"],
            "query_signature": "def456ghi789",
            "trace_id": "trace_abc"
        }
    
    @pytest.mark.asyncio
    async def test_eligible_for_fast_path_no_attachments(self, golden_service, sample_query):
        """Test that query without attachments is eligible for fast-path."""
        with patch('app.observability.rag_logging.rag_step_log') as mock_log:
            result = await golden_service.is_eligible_for_fast_path(sample_query)
            
            assert result.decision == EligibilityDecision.ELIGIBLE
            assert result.confidence > 0.8
            assert "no_attachments" in result.reasons
            assert result.allows_golden_lookup is True
            
            # Verify logging
            mock_log.assert_called_with(
                step=20,
                step_id="RAG.golden.golden.fast.path.eligible.no.doc.or.quick.check.safe",
                node_label="GoldenFastGate",
                decision="ELIGIBLE",
                confidence=result.confidence,
                reasons=result.reasons,
                trace_id="trace_789"
            )
    
    @pytest.mark.asyncio
    async def test_not_eligible_with_attachments(self, golden_service, sample_query_with_attachments):
        """Test that query with attachments is not eligible for fast-path."""
        with patch('app.observability.rag_logging.rag_step_log') as mock_log:
            result = await golden_service.is_eligible_for_fast_path(sample_query_with_attachments)
            
            assert result.decision == EligibilityDecision.NOT_ELIGIBLE
            assert result.confidence > 0.9
            assert "has_attachments" in result.reasons
            assert result.allows_golden_lookup is False
            
            # Verify logging
            mock_log.assert_called_with(
                step=20,
                step_id="RAG.golden.golden.fast.path.eligible.no.doc.or.quick.check.safe", 
                node_label="GoldenFastGate",
                decision="NOT_ELIGIBLE",
                confidence=result.confidence,
                reasons=result.reasons,
                trace_id="trace_abc"
            )
    
    @pytest.mark.asyncio
    async def test_eligible_quick_check_safe_query(self, golden_service):
        """Test that simple, safe queries are eligible for fast-path."""
        quick_safe_query = {
            "query": "Quanto costa aprire una partita IVA?",
            "attachments": [],
            "user_id": "test_user_123",
            "session_id": "session_456", 
            "canonical_facts": ["costo", "aprire", "partita", "iva"],
            "query_signature": "quick123safe456",
            "trace_id": "trace_quick"
        }
        
        result = await golden_service.is_eligible_for_fast_path(quick_safe_query)
        
        assert result.decision == EligibilityDecision.ELIGIBLE
        assert result.confidence > 0.7
        assert "quick_check_safe" in result.reasons
        assert result.allows_golden_lookup is True
    
    async def test_not_eligible_complex_document_query(self, golden_service):
        """Test that complex document-dependent queries are not eligible."""
        complex_query = {
            "query": "Analizza la conformità di questo documento alle normative IVA vigenti e calcola gli importi dovuti",
            "attachments": [],
            "user_id": "test_user_123",
            "session_id": "session_456",
            "canonical_facts": ["analizza", "conformità", "documento", "normative", "iva", "calcola", "importi"],
            "query_signature": "complex123doc456",
            "trace_id": "trace_complex"
        }
        
        result = await golden_service.is_eligible_for_fast_path(complex_query)
        
        assert result.decision == EligibilityDecision.NOT_ELIGIBLE
        assert "document_dependent" in result.reasons
        assert result.allows_golden_lookup is False
    
    async def test_eligible_factual_knowledge_query(self, golden_service):
        """Test that factual knowledge queries are eligible."""
        factual_query = {
            "query": "Quali sono le scadenze fiscali di dicembre 2024?",
            "attachments": [],
            "user_id": "test_user_123",
            "session_id": "session_456",
            "canonical_facts": ["scadenze", "fiscali", "dicembre", "2024"],
            "query_signature": "factual123know456",
            "trace_id": "trace_factual"
        }
        
        result = await golden_service.is_eligible_for_fast_path(factual_query)
        
        assert result.decision == EligibilityDecision.ELIGIBLE
        assert "factual_knowledge" in result.reasons
        assert result.allows_golden_lookup is True
    
    async def test_eligibility_with_safety_checks(self, golden_service):
        """Test eligibility with comprehensive safety checks."""
        query_data = {
            "query": "Come si calcola l'IVA?",
            "attachments": [],
            "user_id": "test_user_123",
            "session_id": "session_456",
            "canonical_facts": ["calcola", "iva"],
            "query_signature": "safe123calc456",
            "trace_id": "trace_safety"
        }
        
        with patch('app.services.golden_fast_path.GoldenFastPathService._perform_safety_checks') as mock_safety:
            mock_safety.return_value = {
                "is_safe": True,
                "risk_level": "low",
                "requires_doc_context": False
            }
            
            result = await golden_service.is_eligible_for_fast_path(query_data)
            
            assert result.decision == EligibilityDecision.ELIGIBLE
            assert result.safety_checks["is_safe"] is True
            mock_safety.assert_called_once()


class TestGoldenFastPathIntegration:
    """Test integration with RAG pipeline flow."""
    
    @pytest.fixture
    def mock_pipeline_context(self):
        """Mock pipeline context for integration testing."""
        return {
            "user_session": "session_123",
            "trace_id": "trace_456",
            "kb_epoch": "kb_20241201",
            "golden_epoch": "golden_20241201",
            "query_start_time": datetime.now(timezone.utc)
        }
    
    async def test_integration_with_attachment_check(self, mock_pipeline_context):
        """Test integration when attachments are present."""
        from app.services.golden_fast_path import GoldenFastPathService
        
        service = GoldenFastPathService()
        
        # Simulate pipeline flow: AttachCheck -> GoldenFastGate
        attachment_present = True
        query_data = {
            "query": "Verifica questo documento",
            "attachments": [{"filename": "doc.pdf"}] if attachment_present else [],
            "user_id": "test_user",
            "session_id": mock_pipeline_context["user_session"],
            "trace_id": mock_pipeline_context["trace_id"]
        }
        
        if attachment_present:
            # Should skip fast-path due to attachments
            result = await service.is_eligible_for_fast_path(query_data)
            assert result.decision == EligibilityDecision.NOT_ELIGIBLE
            assert result.next_step == "QuickPreIngest"
        else:
            # Should proceed to fast-path evaluation
            result = await service.is_eligible_for_fast_path(query_data)
            assert result.decision in [EligibilityDecision.ELIGIBLE, EligibilityDecision.NOT_ELIGIBLE]
            assert result.next_step in ["GoldenLookup", "ClassifyDomain"]
    
    async def test_integration_with_golden_lookup_flow(self, mock_pipeline_context):
        """Test flow when eligible for golden lookup."""
        from app.services.golden_fast_path import GoldenFastPathService
        
        service = GoldenFastPathService()
        
        eligible_query = {
            "query": "Aliquote IVA standard",
            "attachments": [],
            "user_id": "test_user",
            "session_id": mock_pipeline_context["user_session"],
            "canonical_facts": ["aliquote", "iva", "standard"],
            "trace_id": mock_pipeline_context["trace_id"]
        }
        
        result = await service.is_eligible_for_fast_path(eligible_query)
        
        if result.decision == EligibilityDecision.ELIGIBLE:
            assert result.next_step == "GoldenLookup"
            assert result.allows_golden_lookup is True
        else:
            assert result.next_step == "ClassifyDomain"
            assert result.allows_golden_lookup is False
    
    async def test_performance_requirements(self):
        """Test that eligibility check meets performance requirements."""
        from app.services.golden_fast_path import GoldenFastPathService
        import time
        
        service = GoldenFastPathService()
        
        query_data = {
            "query": "Test performance query",
            "attachments": [],
            "user_id": "perf_test",
            "session_id": "perf_session",
            "canonical_facts": ["test", "performance"],
            "trace_id": "perf_trace"
        }
        
        start_time = time.perf_counter()
        result = await service.is_eligible_for_fast_path(query_data)
        end_time = time.perf_counter()
        
        # Should complete in under 10ms for fast-path decisions
        elapsed_ms = (end_time - start_time) * 1000
        assert elapsed_ms < 10.0
        assert result.decision in [EligibilityDecision.ELIGIBLE, EligibilityDecision.NOT_ELIGIBLE]


class TestEligibilityResult:
    """Test the EligibilityResult data structure."""
    
    def test_eligibility_result_creation(self):
        """Test creating EligibilityResult with all fields."""
        result = EligibilityResult(
            decision=EligibilityDecision.ELIGIBLE,
            confidence=0.95,
            reasons=["no_attachments", "quick_check_safe"],
            next_step="GoldenLookup",
            allows_golden_lookup=True,
            safety_checks={"is_safe": True, "risk_level": "low"}
        )
        
        assert result.decision == EligibilityDecision.ELIGIBLE
        assert result.confidence == 0.95
        assert len(result.reasons) == 2
        assert result.next_step == "GoldenLookup"
        assert result.allows_golden_lookup is True
    
    def test_eligibility_result_serialization(self):
        """Test that EligibilityResult can be serialized for logging."""
        result = EligibilityResult(
            decision=EligibilityDecision.NOT_ELIGIBLE,
            confidence=0.88,
            reasons=["has_attachments"],
            next_step="ClassifyDomain",
            allows_golden_lookup=False
        )
        
        # Should be serializable to dict for structured logging
        result_dict = result.to_dict()
        assert result_dict["decision"] == "NOT_ELIGIBLE"
        assert result_dict["confidence"] == 0.88
        assert "has_attachments" in result_dict["reasons"]


class TestLoggingAndObservability:
    """Test structured logging and observability for golden fast-path."""
    
    async def test_rag_step_logging(self):
        """Test that RAG step logging is called correctly."""
        from app.services.golden_fast_path import GoldenFastPathService
        
        service = GoldenFastPathService()
        
        query_data = {
            "query": "Test logging query",
            "attachments": [],
            "user_id": "log_test",
            "session_id": "log_session", 
            "trace_id": "log_trace_123"
        }
        
        with patch('app.observability.rag_logging.rag_step_log') as mock_log:
            result = await service.is_eligible_for_fast_path(query_data)
            
            # Verify rag_step_log was called with correct parameters
            mock_log.assert_called()
            call_args = mock_log.call_args
            
            assert call_args[1]["step"] == 20
            assert call_args[1]["step_id"] == "RAG.golden.golden.fast.path.eligible.no.doc.or.quick.check.safe"
            assert call_args[1]["node_label"] == "GoldenFastGate"
            assert "decision" in call_args[1]
            assert "confidence" in call_args[1]
            assert call_args[1]["trace_id"] == "log_trace_123"
    
    async def test_performance_logging(self):
        """Test that performance metrics are logged correctly."""
        from app.services.golden_fast_path import GoldenFastPathService
        
        service = GoldenFastPathService()
        
        query_data = {
            "query": "Performance test query",
            "attachments": [],
            "user_id": "perf_user",
            "session_id": "perf_session",
            "trace_id": "perf_trace"
        }
        
        with patch('app.observability.rag_logging.rag_step_log') as mock_log:
            result = await service.is_eligible_for_fast_path(query_data)
            
            # Check that latency was logged
            call_args = mock_log.call_args[1]
            assert "latency_ms" in call_args
            assert isinstance(call_args["latency_ms"], float)
            assert call_args["latency_ms"] >= 0


# Test data fixtures for various query types
@pytest.fixture(scope="module")
def test_queries():
    """Test query data for various scenarios."""
    return {
        "simple_faq": {
            "query": "Cos'è l'IVA?",
            "expected_eligible": True,
            "expected_reasons": ["simple_faq", "factual_knowledge"]
        },
        "complex_analysis": {
            "query": "Analizza tutti gli aspetti fiscali di questa fusione aziendale considerando le implicazioni IVA, IRES e imposte locali",
            "expected_eligible": False,
            "expected_reasons": ["complex_analysis", "requires_detailed_processing"]
        },
        "quick_calculation": {
            "query": "Calcola IVA al 22% su 1000 euro",
            "expected_eligible": True,
            "expected_reasons": ["simple_calculation", "quick_check_safe"]
        },
        "document_dependent": {
            "query": "Verifica la conformità di questo contratto alle normative vigenti",
            "expected_eligible": False,
            "expected_reasons": ["document_dependent", "requires_context"]
        }
    }


@pytest.mark.asyncio
async def test_various_query_types(test_queries):
    """Test eligibility for various query types."""
    from app.services.golden_fast_path import GoldenFastPathService
    
    service = GoldenFastPathService()
    
    for query_type, test_data in test_queries.items():
        query_data = {
            "query": test_data["query"],
            "attachments": [],
            "user_id": f"test_user_{query_type}",
            "session_id": f"session_{query_type}",
            "trace_id": f"trace_{query_type}"
        }
        
        result = await service.is_eligible_for_fast_path(query_data)
        
        if test_data["expected_eligible"]:
            assert result.decision == EligibilityDecision.ELIGIBLE, f"Query type {query_type} should be eligible"
        else:
            assert result.decision == EligibilityDecision.NOT_ELIGIBLE, f"Query type {query_type} should not be eligible"