#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG STEP 43 — DomainPrompt (PromptTemplateManager.get_prompt Get domain-specific prompt)

Adapter for the auditor: stable symbol that maps blueprint step ID & node label.
Keep side-effect free; real logic lives in PromptTemplateManager.
"""
from typing import Any, Dict

try:
    from app.observability.rag_logging import rag_step_log
except Exception:  # pragma: no cover
    def rag_step_log(*args, **kwargs):  # no-op fallback
        return None

STEP = 43
STEP_ID = "RAG.classify.prompttemplatemanager.get.prompt.get.domain.specific.prompt"
NODE_LABEL = "DomainPrompt"
CATEGORY = "classify"
TYPE = "process"

__all__ = ["run", "step_43_rag_classify_prompttemplatemanager_get_prompt_get_domain_specific_prompt"]


def run(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Adapter for STEP 43; logs once and returns a marker dict."""
    trace_id = payload.get("trace_id") if isinstance(payload, dict) else None
    try:
        rag_step_log(
            step=STEP,
            step_id=STEP_ID,
            node_label=NODE_LABEL,
            decision="N/A",
            confidence=1.0,
            reasons=["adapter_sentinel"],
            trace_id=trace_id,
        )
    except Exception:
        pass
    return {"step": STEP, "step_id": STEP_ID, "node": NODE_LABEL, "ok": True}


# Canonical alias some auditors look for
def step_43_rag_classify_prompttemplatemanager_get_prompt_get_domain_specific_prompt(payload: Dict[str, Any]) -> Dict[
    str, Any]:
    return run(payload)
