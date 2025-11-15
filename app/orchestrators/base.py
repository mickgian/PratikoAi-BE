from contextlib import nullcontext
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# Safe fallbacks for observability
try:
    from app.observability.rag_logging import rag_step_log, rag_step_timer
except Exception:  # pragma: no cover

    def rag_step_log(**kwargs):  # no-op in tests if import missing
        return None

    def rag_step_timer(*args, **kwargs):
        return nullcontext()


@dataclass
class ClassificationCtx:
    domain: str | None = None
    action: str | None = None
    confidence: float | None = None


@dataclass
class ProviderRoutingCtx:
    strategy: str | None = None
    max_cost_eur: float | None = None
    preferred_provider: str | None = None
    classification: ClassificationCtx | None = None
    extra: dict[str, Any] = None


@dataclass
class CacheCtx:
    kb_epoch: str | None = None
    golden_epoch: str | None = None
    ccnl_epoch: str | None = None
    parser_version: str | None = None
    doc_hashes: list[str] | None = None
