"""
Integration tests for Domain-Action Classification system.

Tests the full integration with the chat service to ensure the classification
system works correctly in production scenarios.
"""

import os
import pytest
import asyncio
from unittest.mock import patch

from app.core.langgraph.graph import LangGraphAgent
from app.schemas.chat import Message
from app.core.config import settings


class TestClassificationIntegration:
    """Test suite for classification integration with chat service."""
    
    @pytest.fixture
    def agent(self):
        """Create agent with classification enabled by default."""
        return LangGraphAgent()
    
    @pytest.mark.asyncio
    async def test_classification_with_tax_calculation(self, agent):
        """Test classification for tax calculation query."""
        messages = [
            Message(role='user', content='Calcola IVA al 22% su fattura da 1000 euro')
        ]
        
        # Mock the LLM response to avoid external API calls
        mock_response = {
            'messages': [
                {'role': 'user', 'content': 'Calcola IVA al 22% su fattura da 1000 euro'},
                {'role': 'assistant', 'content': 'Il calcolo dell\'IVA al 22% su una fattura da 1.000 euro è: 1.000 € × 22% = 220 €. Il totale comprensivo di IVA è quindi 1.220 €.'}
            ]
        }
        
        with patch.object(agent._graph, 'ainvoke', return_value=mock_response):
            result = await agent.get_response(messages, 'test_session', 'test_user')
            
            # Verify response structure
            assert isinstance(result, list)
            assert len(result) >= 2
            
            # Check that classification was performed
            assert agent._current_classification is not None
            assert agent._current_classification.domain.value == 'tax'
            assert agent._current_classification.action.value == 'calculation_request'
            assert agent._current_classification.confidence > 0.3
    
    @pytest.mark.asyncio
    async def test_classification_with_legal_document(self, agent):
        """Test classification for legal document generation query."""
        messages = [
            Message(role='user', content='Scrivi un ricorso al TAR per diniego autorizzazione')
        ]
        
        mock_response = {
            'messages': [
                {'role': 'user', 'content': 'Scrivi un ricorso al TAR per diniego autorizzazione'},
                {'role': 'assistant', 'content': 'Ecco un modello di ricorso al TAR...'}
            ]
        }
        
        with patch.object(agent._graph, 'ainvoke', return_value=mock_response):
            result = await agent.get_response(messages, 'test_session', 'test_user')
            
            assert agent._current_classification is not None
            assert agent._current_classification.domain.value == 'legal'
            assert agent._current_classification.action.value == 'document_generation'
            assert agent._current_classification.sub_domain == 'amministrativo'
    
    @pytest.mark.asyncio
    async def test_classification_with_low_confidence_fallback(self, agent):
        """Test fallback to default prompt for low confidence classification."""
        messages = [
            Message(role='user', content='Ciao, come stai?')  # Generic greeting
        ]
        
        mock_response = {
            'messages': [
                {'role': 'user', 'content': 'Ciao, come stai?'},
                {'role': 'assistant', 'content': 'Ciao! Sto bene, grazie. Come posso aiutarti?'}
            ]
        }
        
        with patch.object(agent._graph, 'ainvoke', return_value=mock_response):
            result = await agent.get_response(messages, 'test_session', 'test_user')
            
            # Should still classify but might have lower confidence
            assert agent._current_classification is not None
            # For generic greeting, might classify as information_request with low confidence
    
    
    def test_classification_metrics_tracking(self, agent):
        """Test that classification metrics are properly tracked."""
        # This would require checking Prometheus metrics
        # For now, we just verify the metrics functions exist and can be called
        from app.core.monitoring.metrics import track_classification_usage
        
        # Should not raise an exception
        track_classification_usage(
            domain="tax",
            action="calculation_request",
            confidence=0.85,
            fallback_used=False,
            prompt_used=True
        )
    
    @pytest.mark.asyncio
    async def test_multiple_classification_types(self, agent):
        """Test different types of queries to verify classification accuracy."""
        test_cases = [
            ("Posso dedurre il costo dell'amministratore?", "business", "compliance_check"),
            ("Conviene il regime forfettario?", "tax", "strategic_advice"),
            ("Analizza questo bilancio", "accounting", "document_analysis"),
            ("Calcola TFR dopo 5 anni", "labor", "calculation_request"),
            ("Cos'è il reverse charge?", "tax", "information_request"),
        ]
        
        for query, expected_domain, expected_action in test_cases:
            messages = [Message(role='user', content=query)]
            
            mock_response = {
                'messages': [
                    {'role': 'user', 'content': query},
                    {'role': 'assistant', 'content': 'Risposta professionale...'}
                ]
            }
            
            with patch.object(agent._graph, 'ainvoke', return_value=mock_response):
                await agent.get_response(messages, 'test_session', 'test_user')
                
                assert agent._current_classification is not None
                assert agent._current_classification.domain.value == expected_domain
                assert agent._current_classification.action.value == expected_action


if __name__ == "__main__":
    # Run a simple manual test
    async def manual_test():
        print("Running manual classification integration test...")
        
        agent = LangGraphAgent()
        messages = [
            Message(role='user', content='Calcola IVA al 22% su fattura da 1000 euro')
        ]
        
        try:
            # Perform classification without full LLM call
            classification = await agent._classify_user_query(messages)
            
            if classification:
                print(f"✅ Classification successful!")
                print(f"   Domain: {classification.domain.value}")
                print(f"   Action: {classification.action.value}")
                print(f"   Confidence: {classification.confidence:.3f}")
                print(f"   Sub-domain: {classification.sub_domain}")
            else:
                print("❌ Classification failed")
                
        except Exception as e:
            print(f"❌ Test failed: {str(e)}")
    
    asyncio.run(manual_test())