"""Tests for DEV-257: _extract_usage_fields provider extraction from orchestrator."""

import pytest

from app.orchestrators.metrics import _extract_usage_fields


class TestExtractUsageFieldsProviderResolution:
    """DEV-257: _extract_usage_fields must resolve provider from multiple dict formats."""

    def test_provider_from_kwargs_string(self):
        """Provider passed as string kwarg is used directly."""
        result = _extract_usage_fields(
            kwargs={"provider": "openai"},
            _ctx={"user_id": "1", "session_id": "s1"},
            llm_dict={},
        )
        # provider is at index 2
        assert result[2] == "openai"

    def test_provider_from_ctx_with_selected_key(self):
        """Provider dict with 'selected' key resolves correctly."""
        result = _extract_usage_fields(
            kwargs={},
            _ctx={
                "user_id": "1",
                "session_id": "s1",
                "provider": {"selected": "anthropic", "strategy": "cost_optimized"},
            },
            llm_dict={},
        )
        assert result[2] == "anthropic"

    def test_provider_from_ctx_with_provider_type_key(self):
        """DEV-257: Provider dict with 'provider_type' (from CheapProvider) resolves correctly."""
        result = _extract_usage_fields(
            kwargs={},
            _ctx={
                "user_id": "1",
                "session_id": "s1",
                "provider": {
                    "strategy": "CHEAP",
                    "provider_type": "openai",
                    "model": "gpt-4o",
                    "cost_per_token": 0.00001,
                },
            },
            llm_dict={},
        )
        assert result[2] == "openai"

    def test_provider_prefers_selected_over_provider_type(self):
        """When both 'selected' and 'provider_type' exist, prefer 'selected'."""
        result = _extract_usage_fields(
            kwargs={},
            _ctx={
                "user_id": "1",
                "session_id": "s1",
                "provider": {"selected": "anthropic", "provider_type": "openai"},
            },
            llm_dict={},
        )
        assert result[2] == "anthropic"

    def test_provider_falls_back_to_name(self):
        """Falls back to 'name' when both 'selected' and 'provider_type' are absent."""
        result = _extract_usage_fields(
            kwargs={},
            _ctx={
                "user_id": "1",
                "session_id": "s1",
                "provider": {"name": "openai", "model": "gpt-4o"},
            },
            llm_dict={},
        )
        assert result[2] == "openai"

    def test_provider_none_when_dict_has_no_known_keys(self):
        """Provider is None when dict has no recognized keys."""
        result = _extract_usage_fields(
            kwargs={},
            _ctx={
                "user_id": "1",
                "session_id": "s1",
                "provider": {"strategy": "CHEAP", "cost_per_token": 0.00001},
            },
            llm_dict={},
        )
        assert result[2] is None
