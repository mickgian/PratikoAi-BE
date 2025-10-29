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
    domain: Optional[str] = None
    action: Optional[str] = None
    confidence: Optional[float] = None

@dataclass
class ProviderRoutingCtx:
    strategy: Optional[str] = None
    max_cost_eur: Optional[float] = None
    preferred_provider: Optional[str] = None
    classification: Optional[ClassificationCtx] = None
    extra: Dict[str, Any] = None

@dataclass
class CacheCtx:
    kb_epoch: Optional[str] = None
    golden_epoch: Optional[str] = None
    ccnl_epoch: Optional[str] = None
    parser_version: Optional[str] = None
    doc_hashes: Optional[List[str]] = None