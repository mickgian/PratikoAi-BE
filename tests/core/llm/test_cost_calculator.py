"""Tests for cost calculator functionality."""

import pytest
from typing import Dict

from app.core.llm.cost_calculator import (
    CostCalculator,
    QueryComplexity,
    CostEstimate,
)
from app.core.llm.base import LLMModelTier
from app.schemas.chat import Message
from tests.core.llm.test_base import MockLLMProvider


class TestCostCalculator:
    """Test cases for the cost calculator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = CostCalculator()

    def test_classify_simple_query(self):
        """Test classification of simple queries."""
        messages = [Message(role="user", content="What is 2+2?")]
        complexity = self.calculator.classify_query_complexity(messages)
        assert complexity == QueryComplexity.SIMPLE

    def test_classify_moderate_query(self):
        """Test classification of moderate queries."""
        messages = [Message(role="user", content="How to calculate income tax in Italy?")]
        complexity = self.calculator.classify_query_complexity(messages)
        assert complexity == QueryComplexity.MODERATE

    def test_classify_complex_query(self):
        """Test classification of complex queries."""
        messages = [
            Message(role="user", content="Please analyze the tax implications of this business structure and compare different options available in Italy")
        ]
        complexity = self.calculator.classify_query_complexity(messages)
        assert complexity == QueryComplexity.COMPLEX

    def test_classify_advanced_query(self):
        """Test classification of advanced queries."""
        messages = [
            Message(role="user", content="I need a comprehensive legal analysis of the new Italian tax reform and its implications for multinational corporations operating in the EU market")
        ]
        complexity = self.calculator.classify_query_complexity(messages)
        assert complexity == QueryComplexity.ADVANCED

    def test_classify_empty_messages(self):
        """Test classification with empty messages."""
        messages = []
        complexity = self.calculator.classify_query_complexity(messages)
        assert complexity == QueryComplexity.SIMPLE

    def test_estimate_output_tokens_simple(self):
        """Test output token estimation for simple queries."""
        input_tokens = 100
        complexity = QueryComplexity.SIMPLE
        
        output_tokens, confidence = self.calculator.estimate_output_tokens(input_tokens, complexity)
        
        assert output_tokens == 30  # 100 * 0.3
        assert confidence == 0.9

    def test_estimate_output_tokens_advanced(self):
        """Test output token estimation for advanced queries."""
        input_tokens = 100
        complexity = QueryComplexity.ADVANCED
        
        output_tokens, confidence = self.calculator.estimate_output_tokens(input_tokens, complexity)
        
        assert output_tokens == 200  # 100 * 2.0
        assert confidence == 0.6

    def test_estimate_output_tokens_bounds(self):
        """Test output token estimation respects bounds."""
        # Test minimum bound
        input_tokens = 1
        complexity = QueryComplexity.SIMPLE
        
        output_tokens, _ = self.calculator.estimate_output_tokens(input_tokens, complexity)
        assert output_tokens >= 10  # Minimum tokens
        
        # Test maximum bound
        input_tokens = 10000
        complexity = QueryComplexity.ADVANCED
        
        output_tokens, _ = self.calculator.estimate_output_tokens(input_tokens, complexity)
        assert output_tokens <= 4000  # Maximum tokens

    def test_calculate_cost_estimate(self):
        """Test cost estimation calculation."""
        provider = MockLLMProvider(api_key="test-key")
        messages = [Message(role="user", content="What is tax?")]
        
        estimate = self.calculator.calculate_cost_estimate(provider, messages)
        
        assert isinstance(estimate, CostEstimate)
        assert estimate.provider == "openai"
        assert estimate.model == "mock-model"
        assert estimate.total_cost_eur > 0
        assert 0.5 <= estimate.confidence <= 1.0

    def test_find_optimal_provider_single(self):
        """Test finding optimal provider with single option."""
        provider = MockLLMProvider(api_key="test-key")
        messages = [Message(role="user", content="Hello")]
        
        optimal_provider, estimate = self.calculator.find_optimal_provider([provider], messages)
        
        assert optimal_provider == provider
        assert estimate.provider == "openai"

    def test_find_optimal_provider_cost_constraint(self):
        """Test finding optimal provider with cost constraints."""
        # Create provider with high cost
        expensive_provider = MockLLMProvider(api_key="test-key", model="expensive-model")
        expensive_provider.supported_models["expensive-model"].input_cost_per_1k_tokens = 1.0
        
        # Create provider with low cost
        cheap_provider = MockLLMProvider(api_key="test-key", model="cheap-model")
        cheap_provider.supported_models = {
            "cheap-model": MockLLMProvider("", "").supported_models["mock-model"]
        }
        
        messages = [Message(role="user", content="Hello")]
        providers = [expensive_provider, cheap_provider]
        
        optimal_provider, estimate = self.calculator.find_optimal_provider(
            providers, messages, max_cost_eur=0.01
        )
        
        # Should choose the cheaper provider
        assert optimal_provider.model == "cheap-model"

    def test_find_optimal_provider_tier_constraint(self):
        """Test finding optimal provider with tier constraints."""
        basic_provider = MockLLMProvider(api_key="test-key", model="basic-model")
        basic_provider.supported_models["basic-model"].tier = LLMModelTier.BASIC
        
        advanced_provider = MockLLMProvider(api_key="test-key", model="advanced-model")
        advanced_provider.supported_models = {
            "advanced-model": MockLLMProvider("", "").supported_models["mock-model"]
        }
        advanced_provider.supported_models["advanced-model"].tier = LLMModelTier.ADVANCED
        
        messages = [Message(role="user", content="Hello")]
        providers = [basic_provider, advanced_provider]
        
        optimal_provider, estimate = self.calculator.find_optimal_provider(
            providers, messages, min_tier=LLMModelTier.ADVANCED
        )
        
        # Should choose the advanced provider
        assert optimal_provider.model == "advanced-model"

    def test_find_optimal_provider_no_providers(self):
        """Test finding optimal provider with no providers."""
        messages = [Message(role="user", content="Hello")]
        
        with pytest.raises(ValueError, match="No providers available"):
            self.calculator.find_optimal_provider([], messages)

    def test_get_cost_tier(self):
        """Test cost tier classification."""
        assert self.calculator.get_cost_tier(0.0005) == "low"
        assert self.calculator.get_cost_tier(0.003) == "medium"
        assert self.calculator.get_cost_tier(0.025) == "high"

    def test_should_use_cache_low_cost(self):
        """Test cache recommendation for low cost queries."""
        estimate = CostEstimate(
            input_tokens=100,
            estimated_output_tokens=50,
            total_cost_eur=0.0005,  # Low cost
            provider="test",
            model="test",
            confidence=0.9
        )
        
        # Should only cache if high hit probability
        assert self.calculator.should_use_cache(estimate, 0.6) is True
        assert self.calculator.should_use_cache(estimate, 0.3) is False

    def test_should_use_cache_high_cost(self):
        """Test cache recommendation for high cost queries."""
        estimate = CostEstimate(
            input_tokens=1000,
            estimated_output_tokens=500,
            total_cost_eur=0.025,  # High cost
            provider="test",
            model="test",
            confidence=0.9
        )
        
        # Should always cache expensive queries
        assert self.calculator.should_use_cache(estimate, 0.1) is True
        assert self.calculator.should_use_cache(estimate, 0.9) is True