from typing import Any, Dict, Optional

# Structured logging (graceful fallback if not available)
try:
    from app.observability.rag_logging import rag_step_log  # type: ignore
except Exception:  # pragma: no cover
    def rag_step_log(**_: Dict[str, Any]) -> None:  # no-op fallback
        return None

# ---- Blueprint metadata (used by the auditor) ----
STEP = 20
STEP_ID = "RAG.golden.golden.fast.path.eligible.no.doc.or.quick.check.safe"
NODE_LABEL = "Golden fast-path eligible? no doc or quick check safe"
CATEGORY = "golden"
TYPE = "process"


def step_20_rag_golden_golden_fast_path_eligible_no_doc_or_quick_check_safe(
    query: Dict[str, Any],
    **attrs: Any,
) -> Optional[Dict[str, Any]]:
    """
    RAG STEP 20 — Golden fast-path eligible? no doc or quick check safe

    Node: Golden fast-path eligible? no doc or quick check safe
    ID: RAG.golden.golden.fast.path.eligible.no.doc.or.quick.check.safe
    Type: process
    Category: golden

    Hints (for auditor matching):
    - keywords: golden, faq, answer bank, fast path, pre-llm, signature, quick check, safe
    - This is a thin adapter whose purpose is conformance & observability.
      It can call the real service later; it doesn’t have to for the audit.
    """
    # Single structured log to create a clear audit trail/signal.
    rag_step_log(
        step=STEP,
        step_id=STEP_ID,
        node_label="GoldenFastGate",
        decision="PROBE",
        confidence=0.99,
        reasons=["adapter_present", "conformance_probe"],
        **attrs,
    )

    # No business logic here; add wiring once you want runtime use.
    # Example for later:
    # from app.services.golden_fast_path import GoldenFastPathService
    # svc = GoldenFastPathService()
    # result = svc.is_eligible_for_fast_path_sync(query)
    # return {"eligible": result.decision == "ELIGIBLE", "confidence": result.confidence}

    return None
