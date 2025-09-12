"""
Consistent RAG step logging (no behavior change).
This module is optional; import it where you need explicit RAG observability.

Usage examples:
    from app.observability.rag_logging import rag_step_log, rag_step_timer

    # Point-in-time log with arbitrary attributes
    rag_step_log(29, "RAG.route.tool_type", "Tool type?",
                 decision="KBQuery", doc_present=True, trace_id=ctx.trace_id)

    # Timed block (emits latency_ms; logs ERROR on exception then re-raises)
    with rag_step_timer(27, "RAG.cache.check_response", "CheckCache",
                        cache_key=key, trace_id=ctx.trace_id):
        do_cache_lookup()
"""

from __future__ import annotations
import json
import logging
import time
from contextlib import contextmanager
from typing import Any, Dict, Optional

_logger = logging.getLogger("rag")


def _to_json_safely(obj: Any) -> str:
    """Serialize attrs dict to JSON for log readability; fallback to repr()."""
    try:
        return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        return repr(obj)


def rag_step_log(
    step: int,
    step_id: str,
    node_label: str,
    *,
    level: str = "INFO",
    **attrs: Any,
) -> None:
    """
    Emit a structured log line for a RAG step.

    Required:
      - step: human step number from docs/architecture/rag_steps.yml
      - step_id: stable ID (e.g., "RAG.route.tool_type")
      - node_label: Mermaid node label (for readability)

    Optional keyword attrs:
      trace_id, user_session, kb_epoch, golden_epoch, ccnl_epoch, parser_version,
      doc_hashes, cache_hit, decision, provider, cost_eur, latency_ms, error, etc.

    This function does not raise; it logs best-effort.
    """
    payload: Dict[str, Any] = {
        "step": int(step),
        "step_id": str(step_id),
        "node": str(node_label),
    }
    if attrs:
        payload.update(attrs)

    level_num = getattr(logging, level.upper(), logging.INFO)
    _logger.log(
        level_num,
        "RAG STEP %s (%s): %s | attrs=%s",
        payload.get("step"),
        payload.get("step_id"),
        payload.get("node"),
        _to_json_safely(payload),
    )


@contextmanager
def rag_step_timer(
    step: int,
    step_id: str,
    node_label: str,
    **attrs: Any,
):
    """
    Context manager to measure elapsed time for a RAG step section.
    On normal exit: logs INFO with latency_ms.
    On exception: logs ERROR with latency_ms and error repr, then re-raises.
    """
    t0 = time.perf_counter()
    try:
        yield
    except Exception as exc:  # log then re-raise
        dt_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        rag_step_log(
            step,
            step_id,
            node_label,
            level="ERROR",
            latency_ms=dt_ms,
            error=repr(exc),
            **attrs,
        )
        raise
    else:
        dt_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        rag_step_log(
            step,
            step_id,
            node_label,
            level="INFO",
            latency_ms=dt_ms,
            **attrs,
        )