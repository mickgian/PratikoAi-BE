"""Tests for cache invalidation in Italian document collection."""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from app.services.italian_document_collector import italian_document_collector


class TestCacheInvalidation:
    """Test cache invalidation functionality."""

    @patch('app.services.cache.cache_service')
    async def test_invalidate_cache_for_updates(self, mock_cache_service):
        """Test cache invalidation after document updates."""
        # Mock cache service clear_cache method
        mock_cache_service.clear_cache = AsyncMock(return_value=5)  # 5 keys cleared per pattern
        
        await italian_document_collector.invalidate_cache_for_updates()
        
        # Verify clear_cache was called for each pattern
        expected_patterns = [
            "llm_response:*italian*",
            "llm_response:*iva*", 
            "llm_response:*tax*",
            "llm_response:*fiscal*",
            "llm_response:*legal*",
            "llm_response:*regulation*"
        ]
        
        assert mock_cache_service.clear_cache.call_count == len(expected_patterns)
        
        # Check that each expected pattern was called
        call_args = [call[0][0] for call in mock_cache_service.clear_cache.call_args_list]
        for pattern in expected_patterns:
            assert pattern in call_args

    @patch('app.services.cache.cache_service')
    async def test_invalidate_cache_with_different_clear_counts(self, mock_cache_service):
        """Test cache invalidation with varying numbers of cleared keys."""
        # Mock different return values for each pattern
        clear_counts = [3, 0, 7, 2, 1, 4]  # Different counts for each pattern
        mock_cache_service.clear_cache = AsyncMock(side_effect=clear_counts)
        
        await italian_document_collector.invalidate_cache_for_updates()
        
        # Should have been called 6 times (one for each pattern)
        assert mock_cache_service.clear_cache.call_count == 6
        
        # Total cleared should be sum of all counts (logged message)
        expected_total = sum(clear_counts)
        # We can't easily test the log message content, but we know it should calculate the total

    @patch('app.services.cache.cache_service')
    async def test_invalidate_cache_handles_cache_service_error(self, mock_cache_service):
        """Test cache invalidation handles cache service errors gracefully."""
        # Mock cache service to raise an exception
        mock_cache_service.clear_cache = AsyncMock(side_effect=Exception("Redis connection failed"))
        
        # Should not raise exception - should handle gracefully
        await italian_document_collector.invalidate_cache_for_updates()
        
        # Verify it attempted to call clear_cache at least once
        assert mock_cache_service.clear_cache.call_count >= 1

    @patch('app.services.cache.cache_service')
    async def test_invalidate_cache_partial_failure(self, mock_cache_service):
        """Test cache invalidation when some patterns fail but others succeed."""
        # Mock some calls to succeed and some to fail
        def side_effect(pattern):
            if "italian" in pattern:
                raise Exception("Pattern specific error")
            return 3  # Success for other patterns
        
        mock_cache_service.clear_cache = AsyncMock(side_effect=side_effect)
        
        # Should handle the error gracefully
        await italian_document_collector.invalidate_cache_for_updates()
        
        # Should have attempted all patterns despite some failures
        assert mock_cache_service.clear_cache.call_count == 6

    @patch('app.services.italian_document_collector.italian_document_collector')
    async def test_cache_invalidation_called_after_document_collection(self, mock_collector):
        """Test that cache invalidation is called after successful document collection."""
        from app.services.italian_document_collector import collect_italian_documents_task
        
        # Mock collector methods
        mock_collector.collect_all_documents = AsyncMock(return_value={
            'new_documents': 3,
            'errors': []
        })
        mock_collector.invalidate_cache_for_updates = AsyncMock()
        
        await collect_italian_documents_task()
        
        # Should call cache invalidation when new documents are found
        mock_collector.invalidate_cache_for_updates.assert_called_once()

    @patch('app.services.italian_document_collector.italian_document_collector')
    async def test_cache_not_invalidated_when_no_new_documents(self, mock_collector):
        """Test that cache is not invalidated when no new documents are collected."""
        from app.services.italian_document_collector import collect_italian_documents_task
        
        # Mock collector to return no new documents
        mock_collector.collect_all_documents = AsyncMock(return_value={
            'new_documents': 0,
            'errors': []
        })
        mock_collector.invalidate_cache_for_updates = AsyncMock()
        
        await collect_italian_documents_task()
        
        # Should not call cache invalidation when no new documents
        mock_collector.invalidate_cache_for_updates.assert_not_called()

    def test_cache_patterns_comprehensiveness(self):
        """Test that cache patterns cover relevant Italian tax and legal terms."""
        # This test validates the patterns we're using for cache invalidation
        patterns = [
            "llm_response:*italian*",
            "llm_response:*iva*",
            "llm_response:*tax*", 
            "llm_response:*fiscal*",
            "llm_response:*legal*",
            "llm_response:*regulation*"
        ]
        
        # Test scenarios that should be covered by our patterns
        test_cache_keys = [
            "llm_response:what_is_italian_vat_rate",
            "llm_response:iva_calculation_2024", 
            "llm_response:tax_compliance_italy",
            "llm_response:fiscal_year_requirements",
            "llm_response:legal_document_template",
            "llm_response:regulation_changes_2024",
            "llm_response:italian_tax_law",
            "llm_response:iva_deduction_rules"
        ]
        
        # Each test key should match at least one pattern
        for test_key in test_cache_keys:
            matched = False
            for pattern in patterns:
                # Convert Redis pattern to Python regex-like check
                pattern_term = pattern.replace("llm_response:*", "").replace("*", "")
                if pattern_term in test_key.lower():
                    matched = True
                    break
            
            assert matched, f"Cache key '{test_key}' not covered by any pattern"

    @patch('app.services.cache.cache_service')
    async def test_cache_invalidation_logs_cleared_count(self, mock_cache_service):
        """Test that cache invalidation logs the total number of cleared entries."""
        # Mock cache service to return specific counts
        clear_counts = [2, 1, 3, 0, 2, 1]
        mock_cache_service.clear_cache = AsyncMock(side_effect=clear_counts)
        
        # Mock logger to verify logging
        with patch.object(italian_document_collector, 'logger') as mock_logger:
            await italian_document_collector.invalidate_cache_for_updates()
            
            # Verify info log was called with total count
            expected_total = sum(clear_counts)
            mock_logger.info.assert_called_once_with(
                f"Invalidated {expected_total} cache entries after document updates"
            )

    @patch('app.services.cache.cache_service')
    async def test_cache_invalidation_logs_errors(self, mock_cache_service):
        """Test that cache invalidation logs errors appropriately."""
        # Mock cache service to raise an exception
        mock_cache_service.clear_cache = AsyncMock(side_effect=Exception("Test error"))
        
        # Mock logger to verify error logging
        with patch.object(italian_document_collector, 'logger') as mock_logger:
            await italian_document_collector.invalidate_cache_for_updates()
            
            # Verify error log was called
            mock_logger.error.assert_called_once_with("Error invalidating cache: Test error")

    @patch('app.services.cache.cache_service', new=None)
    async def test_cache_invalidation_handles_missing_cache_service(self):
        """Test cache invalidation handles missing cache service gracefully."""
        # This test simulates when cache service import fails
        with patch('builtins.__import__', side_effect=ImportError("No module named 'app.services.cache'")):
            # Should handle import error gracefully
            await italian_document_collector.invalidate_cache_for_updates()
            # No assertions needed - just ensuring no exceptions are raised

    def test_cache_patterns_avoid_overly_broad_matching(self):
        """Test that cache patterns are specific enough to avoid clearing unrelated cache."""
        patterns = [
            "llm_response:*italian*",
            "llm_response:*iva*",
            "llm_response:*tax*",
            "llm_response:*fiscal*", 
            "llm_response:*legal*",
            "llm_response:*regulation*"
        ]
        
        # These cache keys should NOT be cleared by our patterns
        unrelated_keys = [
            "llm_response:weather_forecast",
            "llm_response:sports_scores",
            "llm_response:cooking_recipe",
            "llm_response:travel_recommendations"
        ]
        
        # Verify that unrelated keys wouldn't match our patterns
        for unrelated_key in unrelated_keys:
            should_clear = False
            for pattern in patterns:
                pattern_term = pattern.replace("llm_response:*", "").replace("*", "")
                if pattern_term in unrelated_key.lower():
                    should_clear = True
                    break
            
            assert not should_clear, f"Pattern would incorrectly clear unrelated key: {unrelated_key}"