"""
Fake implementations and mocks for testing.

Provides deterministic fake services that return predictable values
without external dependencies.
"""

from typing import Any, Dict, Optional, List
from unittest.mock import AsyncMock, MagicMock


class FakeOrchestrator:
    """Base fake orchestrator that returns deterministic dicts."""

    def __init__(self, return_value: Dict[str, Any]):
        self.return_value = return_value
        self.call_count = 0
        self.call_args_list: List[Dict] = []

    async def __call__(self, *args, **kwargs):
        self.call_count += 1
        self.call_args_list.append(kwargs)
        return self.return_value.copy()


class FakeCacheService:
    """Fake cache service for testing."""

    def __init__(self, hit: bool = False, cached_response: Optional[Dict] = None):
        self.hit = hit
        self.cached_response = cached_response or {"content": "cached", "cached_at": "2025-01-01"}
        self.get_calls = 0
        self.set_calls = 0

    async def get(self, key: str) -> Optional[Dict]:
        self.get_calls += 1
        return self.cached_response if self.hit else None

    async def set(self, key: str, value: Dict, ttl: int = 3600) -> None:
        self.set_calls += 1


class FakeProviderFactory:
    """Fake provider factory for testing."""

    def __init__(self, provider_name: str = "anthropic", model: str = "claude-3-5-sonnet-20241022"):
        self.provider_name = provider_name
        self.model = model
        self.create_calls = 0

    def create_provider(self, provider_config: Dict) -> Dict:
        self.create_calls += 1
        return {
            "name": self.provider_name,
            "model": self.model,
            "api_key": "fake-key-123",
            "config": provider_config
        }


class FakeUsageTracker:
    """Fake usage tracker for testing."""

    def __init__(self):
        self.tracked_requests: List[Dict] = []

    async def track(self, request_id: str, metrics: Dict) -> None:
        self.tracked_requests.append({"request_id": request_id, **metrics})


class FakeSSEWriter:
    """Fake SSE writer for streaming tests."""

    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.written_chunks: List[str] = []
        self.done_sent = False

    async def write_chunk(self, chunk: str) -> None:
        if self.should_fail and len(self.written_chunks) >= 2:
            raise ConnectionError("Stream disconnect")
        self.written_chunks.append(chunk)

    async def write_done(self) -> None:
        self.done_sent = True


# Orchestrator fakes for common scenarios

def fake_validate_request_orch(valid: bool = True) -> FakeOrchestrator:
    """Fake for step_1__validate_request orchestrator."""
    return FakeOrchestrator({
        "request_valid": valid,
        "validation_errors": [] if valid else ["Invalid request format"]
    })


def fake_privacy_check_orch(enabled: bool = True) -> FakeOrchestrator:
    """Fake for step_6__privacy_check orchestrator."""
    return FakeOrchestrator({
        "privacy_enabled": enabled,
        "anonymize_required": enabled
    })


def fake_cache_check_orch(hit: bool = False) -> FakeOrchestrator:
    """Fake for step_59__check_cache orchestrator."""
    if hit:
        return FakeOrchestrator({
            "cache_hit": True,
            "cached_response": {
                "content": "Cached answer",
                "model": "claude-3-5-sonnet-20241022",
                "cached_at": "2025-01-01T00:00:00Z"
            }
        })
    return FakeOrchestrator({"cache_hit": False})


def fake_llm_call_orch(success: bool = True, has_tools: bool = False) -> FakeOrchestrator:
    """Fake for step_64__llm_call orchestrator."""
    if success:
        response = {
            "content": "LLM response" if not has_tools else "",
            "model": "claude-3-5-sonnet-20241022",
            "usage": {"input_tokens": 100, "output_tokens": 50}
        }
        if has_tools:
            response["tool_calls"] = [
                {"name": "kb_search", "args": {"query": "test query"}}
            ]
        return FakeOrchestrator({
            "llm_success": True,
            "response": response
        })
    return FakeOrchestrator({
        "llm_success": False,
        "error": "LLM API error",
        "status_code": 500
    })


def fake_provider_select_orch(provider: str = "anthropic") -> FakeOrchestrator:
    """Fake for step_48__select_provider orchestrator."""
    return FakeOrchestrator({
        "provider_selected": True,
        "provider": {
            "name": provider,
            "model": "claude-3-5-sonnet-20241022" if provider == "anthropic" else "gpt-4",
            "strategy": "BEST"
        }
    })


def fake_cost_estimate_orch(cost: float = 0.015, within_budget: bool = True) -> FakeOrchestrator:
    """Fake for step_55__estimate_cost orchestrator."""
    return FakeOrchestrator({
        "cost_estimate": cost,
        "within_budget": within_budget,
        "budget_limit": 0.50
    })


def fake_golden_lookup_orch(match_found: bool = False, high_confidence: bool = False) -> FakeOrchestrator:
    """Fake for step_24__golden_lookup orchestrator."""
    if match_found:
        return FakeOrchestrator({
            "match_found": True,
            "high_confidence_match": high_confidence,
            "similarity_score": 0.95 if high_confidence else 0.75,
            "faq_id": "faq-123",
            "answer": "Golden answer text"
        })
    return FakeOrchestrator({"match_found": False})


def fake_stream_setup_orch() -> FakeOrchestrator:
    """Fake for step_105__stream_setup orchestrator."""
    return FakeOrchestrator({
        "sse_ready": True,
        "generator_created": True
    })


def fake_tool_execution_orch(tool_type: str = "kb") -> FakeOrchestrator:
    """Fake for tool execution orchestrators (steps 80-83)."""
    results = {
        "kb": {"documents": [{"title": "KB Doc 1", "content": "Knowledge base result"}]},
        "ccnl": {"agreements": [{"name": "Agreement A", "terms": "Terms text"}]},
        "doc": {"processed": True, "document_id": "doc-123"},
        "faq": {"faqs": [{"question": "Q1", "answer": "A1"}]}
    }
    return FakeOrchestrator({
        "tool_success": True,
        "tool_type": tool_type,
        "results": results.get(tool_type, {})
    })


# Mock factory functions

def mock_orchestrator_async(return_value: Dict[str, Any]) -> AsyncMock:
    """Create async mock orchestrator that returns a specific value."""
    mock = AsyncMock()
    mock.return_value = return_value
    return mock


def mock_service(methods: Dict[str, Any]) -> MagicMock:
    """Create mock service with specified method return values."""
    mock = MagicMock()
    for method_name, return_value in methods.items():
        getattr(mock, method_name).return_value = return_value
    return mock
