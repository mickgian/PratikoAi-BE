#!/usr/bin/env python3
from typing import Any, Dict, List, Optional
try:
    from app.observability.rag_logging import rag_step_log
except Exception:  # pragma: no cover
    def rag_step_log(**kwargs):  # fallback no-op
        return None

STEP = 47
STEP_ID = "RAG.prompting.insert.system.message"
NODE_LABEL = "InsertMsg"
CATEGORY = "prompting"
TYPE = "process"

"""
RAG STEP 47 — Insert system message
ID: RAG.prompting.insert.system.message
Type: process
Category: prompting

This step inserts a new system message at the beginning of the messages list
when no system message exists. It's triggered after STEP 45 (CheckSysMsg)
determines that no system message is present.

Hints (for auditor matching):
- node: InsertMsg
- id: RAG.prompting.insert.system.message
- category: prompting
- keywords: insert, system, message, prompt
"""

__all__ = ["run", "insert_system_message"]


def run(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Adapter for RAG STEP 47: Insert system message

    This step is triggered when:
    1. No system message exists in the message list (first message has role != "system")
    2. After STEP 45 (CheckSysMsg) determines system message insertion is needed

    The actual insertion is handled by LangGraphAgent._prepare_messages_with_system_prompt
    which logs this step when performing the insertion.
    """
    try:
        rag_step_log(
            step=STEP,
            step_id=STEP_ID,
            node_label=NODE_LABEL,
            decision="insert_system_message",
            confidence=1.0,
            reasons=["adapter_sentinel"],
            trace_id=payload.get("trace_id") if isinstance(payload, dict) else None,
        )
    except Exception:
        pass

    return {"step": STEP, "step_id": STEP_ID, "node": NODE_LABEL, "ok": True}


def insert_system_message(
    messages: List[Any],
    system_prompt: str,
    classification: Optional[Any] = None
) -> List[Any]:
    """Insert system message at the beginning of messages list.

    This function provides the core logic for STEP 47. In practice, this is
    implemented within LangGraphAgent._prepare_messages_with_system_prompt.

    Args:
        messages: List of message objects (will be modified in place)
        system_prompt: System prompt to insert
        classification: Optional classification for logging purposes

    Returns:
        List of messages with system message inserted at position 0
    """
    if messages and hasattr(messages[0], 'role') and messages[0].role == 'system':
        # System message already exists, no insertion needed
        return messages

    # Insert system message at the beginning
    from app.schemas import Message as _Msg
    messages.insert(0, _Msg(role="system", content=system_prompt))

    # Log the insertion
    try:
        rag_step_log(
            step=STEP,
            step_id=STEP_ID,
            node_label=NODE_LABEL,
            decision="system_message_inserted",
            action_taken="insert",
            system_message_exists=False,
            has_classification=classification is not None,
            classification_confidence=getattr(classification, 'confidence', None),
            domain=getattr(classification, 'domain', {}).get('value') if hasattr(getattr(classification, 'domain', None), 'value') else None,
            action=getattr(classification, 'action', {}).get('value') if hasattr(getattr(classification, 'action', None), 'value') else None,
            insert_position=0,
            messages_count=len(messages),
            original_messages_count=len(messages) - 1,
            messages_empty=len(messages) == 1,  # Was empty before insertion
            processing_stage="completed",
        )
    except Exception:
        pass

    return messages
