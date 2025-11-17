"""Unit tests for hardened cache key generation."""

import pytest

from app.services.cache import CacheService


class TestHardenedCacheKey:
    """Test suite for hardened cache key generation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.cache = CacheService()

    def test_cache_key_stable_with_same_inputs(self):
        """Test that cache key is stable with identical inputs."""
        key1 = self.cache._generate_hardened_response_key(
            query_signature="abc123",
            doc_hashes=["doc1", "doc2"],
            epochs={"kb_epoch": 100, "golden_epoch": 95},
            prompt_version="v1.0",
            provider="openai",
            model="gpt-4o-mini",
            temperature=0.2,
            tools_used=True,
        )

        key2 = self.cache._generate_hardened_response_key(
            query_signature="abc123",
            doc_hashes=["doc1", "doc2"],
            epochs={"kb_epoch": 100, "golden_epoch": 95},
            prompt_version="v1.0",
            provider="openai",
            model="gpt-4o-mini",
            temperature=0.2,
            tools_used=True,
        )

        assert key1 == key2

    def test_cache_key_changes_with_query_signature(self):
        """Test that cache key changes when query signature changes."""
        key1 = self.cache._generate_hardened_response_key(
            query_signature="abc123",
            doc_hashes=None,
            epochs={},
            prompt_version="v1.0",
            provider="openai",
            model="gpt-4o-mini",
            temperature=0.2,
            tools_used=False,
        )

        key2 = self.cache._generate_hardened_response_key(
            query_signature="xyz789",  # Different
            doc_hashes=None,
            epochs={},
            prompt_version="v1.0",
            provider="openai",
            model="gpt-4o-mini",
            temperature=0.2,
            tools_used=False,
        )

        assert key1 != key2

    def test_cache_key_changes_with_kb_epoch(self):
        """Test that cache key changes when kb_epoch changes."""
        key1 = self.cache._generate_hardened_response_key(
            query_signature="abc123",
            doc_hashes=None,
            epochs={"kb_epoch": 100},
            prompt_version="v1.0",
            provider="openai",
            model="gpt-4o-mini",
            temperature=0.2,
            tools_used=False,
        )

        key2 = self.cache._generate_hardened_response_key(
            query_signature="abc123",
            doc_hashes=None,
            epochs={"kb_epoch": 101},  # Different
            prompt_version="v1.0",
            provider="openai",
            model="gpt-4o-mini",
            temperature=0.2,
            tools_used=False,
        )

        assert key1 != key2

    def test_cache_key_changes_with_doc_hashes(self):
        """Test that cache key changes when document hashes change."""
        key1 = self.cache._generate_hardened_response_key(
            query_signature="abc123",
            doc_hashes=["doc1"],
            epochs={},
            prompt_version="v1.0",
            provider="openai",
            model="gpt-4o-mini",
            temperature=0.2,
            tools_used=False,
        )

        key2 = self.cache._generate_hardened_response_key(
            query_signature="abc123",
            doc_hashes=["doc1", "doc2"],  # Different
            epochs={},
            prompt_version="v1.0",
            provider="openai",
            model="gpt-4o-mini",
            temperature=0.2,
            tools_used=False,
        )

        assert key1 != key2

    def test_cache_key_changes_with_provider(self):
        """Test that cache key changes when provider changes."""
        key1 = self.cache._generate_hardened_response_key(
            query_signature="abc123",
            doc_hashes=None,
            epochs={},
            prompt_version="v1.0",
            provider="openai",
            model="gpt-4o-mini",
            temperature=0.2,
            tools_used=False,
        )

        key2 = self.cache._generate_hardened_response_key(
            query_signature="abc123",
            doc_hashes=None,
            epochs={},
            prompt_version="v1.0",
            provider="anthropic",  # Different
            model="gpt-4o-mini",
            temperature=0.2,
            tools_used=False,
        )

        assert key1 != key2

    def test_cache_key_changes_with_model(self):
        """Test that cache key changes when model changes."""
        key1 = self.cache._generate_hardened_response_key(
            query_signature="abc123",
            doc_hashes=None,
            epochs={},
            prompt_version="v1.0",
            provider="openai",
            model="gpt-4o-mini",
            temperature=0.2,
            tools_used=False,
        )

        key2 = self.cache._generate_hardened_response_key(
            query_signature="abc123",
            doc_hashes=None,
            epochs={},
            prompt_version="v1.0",
            provider="openai",
            model="gpt-4o",  # Different
            temperature=0.2,
            tools_used=False,
        )

        assert key1 != key2

    def test_cache_key_changes_with_temperature(self):
        """Test that cache key changes when temperature changes."""
        key1 = self.cache._generate_hardened_response_key(
            query_signature="abc123",
            doc_hashes=None,
            epochs={},
            prompt_version="v1.0",
            provider="openai",
            model="gpt-4o-mini",
            temperature=0.2,
            tools_used=False,
        )

        key2 = self.cache._generate_hardened_response_key(
            query_signature="abc123",
            doc_hashes=None,
            epochs={},
            prompt_version="v1.0",
            provider="openai",
            model="gpt-4o-mini",
            temperature=0.5,  # Different
            tools_used=False,
        )

        assert key1 != key2

    def test_cache_key_changes_with_tools_used(self):
        """Test that cache key changes when tools_used flag changes."""
        key1 = self.cache._generate_hardened_response_key(
            query_signature="abc123",
            doc_hashes=None,
            epochs={},
            prompt_version="v1.0",
            provider="openai",
            model="gpt-4o-mini",
            temperature=0.2,
            tools_used=False,
        )

        key2 = self.cache._generate_hardened_response_key(
            query_signature="abc123",
            doc_hashes=None,
            epochs={},
            prompt_version="v1.0",
            provider="openai",
            model="gpt-4o-mini",
            temperature=0.2,
            tools_used=True,  # Different
        )

        assert key1 != key2

    def test_cache_key_changes_with_prompt_version(self):
        """Test that cache key changes when prompt version changes."""
        key1 = self.cache._generate_hardened_response_key(
            query_signature="abc123",
            doc_hashes=None,
            epochs={},
            prompt_version="v1.0",
            provider="openai",
            model="gpt-4o-mini",
            temperature=0.2,
            tools_used=False,
        )

        key2 = self.cache._generate_hardened_response_key(
            query_signature="abc123",
            doc_hashes=None,
            epochs={},
            prompt_version="v1.1",  # Different
            provider="openai",
            model="gpt-4o-mini",
            temperature=0.2,
            tools_used=False,
        )

        assert key1 != key2

    def test_cache_key_doc_hash_order_independent(self):
        """Test that cache key is independent of document hash order."""
        key1 = self.cache._generate_hardened_response_key(
            query_signature="abc123",
            doc_hashes=["doc1", "doc2", "doc3"],
            epochs={},
            prompt_version="v1.0",
            provider="openai",
            model="gpt-4o-mini",
            temperature=0.2,
            tools_used=False,
        )

        key2 = self.cache._generate_hardened_response_key(
            query_signature="abc123",
            doc_hashes=["doc3", "doc1", "doc2"],  # Different order
            epochs={},
            prompt_version="v1.0",
            provider="openai",
            model="gpt-4o-mini",
            temperature=0.2,
            tools_used=False,
        )

        # Should be the same because docs are sorted
        assert key1 == key2

    def test_cache_key_none_doc_hashes(self):
        """Test that None and empty list for doc_hashes are handled."""
        key1 = self.cache._generate_hardened_response_key(
            query_signature="abc123",
            doc_hashes=None,
            epochs={},
            prompt_version="v1.0",
            provider="openai",
            model="gpt-4o-mini",
            temperature=0.2,
            tools_used=False,
        )

        key2 = self.cache._generate_hardened_response_key(
            query_signature="abc123",
            doc_hashes=[],
            epochs={},
            prompt_version="v1.0",
            provider="openai",
            model="gpt-4o-mini",
            temperature=0.2,
            tools_used=False,
        )

        # Should be the same
        assert key1 == key2

    def test_cache_key_is_sha256(self):
        """Test that cache key is a SHA-256 hash (64 hex chars)."""
        key = self.cache._generate_hardened_response_key(
            query_signature="abc123",
            doc_hashes=None,
            epochs={},
            prompt_version="v1.0",
            provider="openai",
            model="gpt-4o-mini",
            temperature=0.2,
            tools_used=False,
        )

        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)

    def test_cache_key_with_all_epochs(self):
        """Test cache key with all epoch types."""
        key1 = self.cache._generate_hardened_response_key(
            query_signature="abc123",
            doc_hashes=None,
            epochs={"kb_epoch": 100, "golden_epoch": 95, "ccnl_epoch": 50, "parser_version": 3},
            prompt_version="v1.0",
            provider="openai",
            model="gpt-4o-mini",
            temperature=0.2,
            tools_used=False,
        )

        key2 = self.cache._generate_hardened_response_key(
            query_signature="abc123",
            doc_hashes=None,
            epochs={
                "kb_epoch": 100,
                "golden_epoch": 95,
                "ccnl_epoch": 51,  # Different
                "parser_version": 3,
            },
            prompt_version="v1.0",
            provider="openai",
            model="gpt-4o-mini",
            temperature=0.2,
            tools_used=False,
        )

        assert key1 != key2
