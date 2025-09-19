# AUTO-GENERATED ORCHESTRATOR STUBS (safe to edit below stubs)
# These functions are the functional *nodes* that mirror the Mermaid diagram.
# Implement thin coordination here (call services/factories), not core business logic.

from contextlib import nullcontext
from typing import Any, Dict, List, Optional

try:
    from app.observability.rag_logging import rag_step_log, rag_step_timer
except Exception:  # pragma: no cover
    def rag_step_log(**kwargs): return None
    def rag_step_timer(*args, **kwargs): return nullcontext()

def step_15__default_prompt(*, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 15 — Continue without classification
    ID: RAG.prompting.continue.without.classification
    Type: process | Category: prompting | Node: DefaultPrompt

    TODO: Implement orchestration so this node *changes/validates control flow/data*
    according to Mermaid — not logs-only. Call into existing services/factories here.
    """
    with rag_step_timer(15, 'RAG.prompting.continue.without.classification', 'DefaultPrompt', stage="start"):
        rag_step_log(step=15, step_id='RAG.prompting.continue.without.classification', node_label='DefaultPrompt',
                     category='prompting', type='process', stub=True, processing_stage="started")
        # TODO: call real service/factory here and return its output
        result = kwargs.get("result")  # placeholder
        rag_step_log(step=15, step_id='RAG.prompting.continue.without.classification', node_label='DefaultPrompt',
                     processing_stage="completed")
        return result

def step_41__select_prompt(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 41 — LangGraphAgent._get_system_prompt Select appropriate prompt
    ID: RAG.prompting.langgraphagent.get.system.prompt.select.appropriate.prompt
    Type: process | Category: prompting | Node: SelectPrompt

    TODO: Implement orchestration so this node *changes/validates control flow/data*
    according to Mermaid — not logs-only. Call into existing services/factories here.
    """
    with rag_step_timer(41, 'RAG.prompting.langgraphagent.get.system.prompt.select.appropriate.prompt', 'SelectPrompt', stage="start"):
        rag_step_log(step=41, step_id='RAG.prompting.langgraphagent.get.system.prompt.select.appropriate.prompt', node_label='SelectPrompt',
                     category='prompting', type='process', stub=True, processing_stage="started")
        # TODO: call real service/factory here and return its output
        result = kwargs.get("result")  # placeholder
        rag_step_log(step=41, step_id='RAG.prompting.langgraphagent.get.system.prompt.select.appropriate.prompt', node_label='SelectPrompt',
                     processing_stage="completed")
        return result

def step_44__default_sys_prompt(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 44 — Use default SYSTEM_PROMPT
    ID: RAG.prompting.use.default.system.prompt
    Type: process | Category: prompting | Node: DefaultSysPrompt

    Uses the default SYSTEM_PROMPT when:
    1. No classification is available, OR
    2. Classification confidence is below threshold

    This is the orchestrator that coordinates returning the default system prompt.
    """
    from app.core.prompts import SYSTEM_PROMPT
    from app.core.config import settings

    # Extract parameters from context
    classification = kwargs.get('classification') or (ctx or {}).get('classification')
    user_query = kwargs.get('user_query') or (ctx or {}).get('user_query', "")
    trigger_reason = kwargs.get('trigger_reason') or (ctx or {}).get('trigger_reason', "unknown")

    # Extract latest user query from messages if not provided
    if not user_query and messages:
        for m in reversed(messages or []):
            if getattr(m, "role", None) == "user":
                user_query = getattr(m, "content", "") or ""
                break

    # Classification context
    conf = getattr(classification, 'confidence', None) if hasattr(classification, 'confidence') else classification.get('confidence') if isinstance(classification, dict) else None
    domain = getattr(classification, 'domain', None) if hasattr(classification, 'domain') else classification.get('domain') if isinstance(classification, dict) else None
    action = getattr(classification, 'action', None) if hasattr(classification, 'action') else classification.get('action') if isinstance(classification, dict) else None
    threshold = getattr(settings, "CLASSIFICATION_CONFIDENCE_THRESHOLD", 0.6)

    # Convert domain enum to string if needed
    if hasattr(domain, 'value'):
        domain = domain.value
    if hasattr(action, 'value'):
        action = action.value

    with rag_step_timer(44, 'RAG.prompting.use.default.system.prompt', 'DefaultSysPrompt', stage="start"):
        rag_step_log(
            step=44,
            step_id='RAG.prompting.use.default.system.prompt',
            node_label='DefaultSysPrompt',
            category='prompting',
            type='process',
            processing_stage="started",
            trigger_reason=trigger_reason,
            classification_available=classification is not None,
            classification_confidence=conf,
            confidence_threshold=threshold
        )

        # Step 44 logic: Return default SYSTEM_PROMPT
        prompt = SYSTEM_PROMPT

        # Determine specific trigger reason if not provided
        if trigger_reason == "unknown":
            if not classification:
                trigger_reason = "no_classification"
            elif conf is not None and conf < threshold:
                trigger_reason = "low_confidence"
            else:
                trigger_reason = "default_fallback"

        # Create reasons list for logging
        reasons = []
        if not classification:
            reasons.append("no_classification_available")
        elif conf is not None and conf < threshold:
            reasons.append(f"confidence_{conf}_below_threshold_{threshold}")
        else:
            reasons.append("default_fallback")

        # Determine decision type
        decision = "no_classification" if not classification else "low_confidence"

        rag_step_log(
            step=44,
            step_id='RAG.prompting.use.default.system.prompt',
            node_label='DefaultSysPrompt',
            trigger_reason=trigger_reason,
            prompt_type="default",
            classification_available=classification is not None,
            classification_confidence=conf,
            confidence_threshold=threshold,
            domain=domain,
            action=action,
            user_query=user_query,
            prompt_length=len(prompt) if prompt else 0,
            processing_stage="completed",
            reasons=reasons,
            confidence=conf if conf is not None else 1.0,
            decision=decision
        )

        return prompt

def step_45__check_sys_msg(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 45 — System message exists?
    ID: RAG.prompting.system.message.exists
    Type: decision | Category: prompting | Node: CheckSysMsg

    Checks whether a system message exists in the conversation and determines routing:
    - If no system message exists -> route to Step 47 (InsertMsg)
    - If system message exists AND has classification -> route to Step 46 (ReplaceMsg)
    - If system message exists BUT no classification -> keep existing (no routing)

    This is the orchestrator that coordinates the system message existence decision logic.
    """
    if messages is None:
        messages = []

    # Extract parameters from context
    classification = kwargs.get('classification') or (ctx or {}).get('classification')
    system_prompt = kwargs.get('system_prompt') or (ctx or {}).get('system_prompt')

    # Check system message existence
    original_count = len(messages)
    messages_empty = (original_count == 0)
    system_exists = bool(messages and getattr(messages[0], "role", None) == "system")

    # Extract classification details for logging
    has_classification = classification is not None
    conf = getattr(classification, 'confidence', None) if hasattr(classification, 'confidence') else classification.get('confidence') if isinstance(classification, dict) else None
    domain = getattr(classification, 'domain', None) if hasattr(classification, 'domain') else classification.get('domain') if isinstance(classification, dict) else None
    action = getattr(classification, 'action', None) if hasattr(classification, 'action') else classification.get('action') if isinstance(classification, dict) else None

    # Convert domain enum to string if needed
    if hasattr(domain, 'value'):
        domain = domain.value
    if hasattr(action, 'value'):
        action = action.value

    with rag_step_timer(45, 'RAG.prompting.system.message.exists', 'CheckSysMsg', stage="start"):
        rag_step_log(
            step=45,
            step_id='RAG.prompting.system.message.exists',
            node_label='CheckSysMsg',
            category='prompting',
            type='decision',
            processing_stage="started",
            system_message_exists=system_exists,
            messages_empty=messages_empty,
            has_classification=has_classification
        )

        # Step 45 decision logic
        if not system_exists:
            # Route to Step 47 (InsertMsg)
            decision = "system_message_not_exists"
            action_taken = "insert"
            next_step = 47
            route_to = "InsertMsg"
        elif has_classification:
            # Route to Step 46 (ReplaceMsg)
            decision = "system_message_exists"
            action_taken = "replace"
            next_step = 46
            route_to = "ReplaceMsg"
        else:
            # Keep existing system message (no routing)
            decision = "system_message_exists"
            action_taken = "keep"
            next_step = None
            route_to = None

        # Log the decision
        rag_step_log(
            step=45,
            step_id='RAG.prompting.system.message.exists',
            node_label='CheckSysMsg',
            decision=decision,
            action_taken=action_taken,
            system_message_exists=system_exists,
            messages_empty=messages_empty,
            original_messages_count=original_count,
            messages_count=len(messages),
            insert_position=0 if not system_exists else None,
            has_classification=has_classification,
            classification_confidence=conf,
            domain=domain,
            action=action,
            next_step=next_step,
            route_to=route_to,
            processing_stage="completed"
        )

        # Return decision result for routing
        return {
            "system_exists": system_exists,
            "has_classification": has_classification,
            "action": action_taken,
            "next_step": next_step,
            "route_to": route_to,
            "decision": decision
        }

def step_46__replace_msg(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 46 — Replace system message
    ID: RAG.prompting.replace.system.message
    Type: process | Category: prompting | Node: ReplaceMsg

    Replaces existing system message with new system prompt when:
    1. System message already exists in messages[0]
    2. Classification is available (indicating domain-specific prompt needed)

    This is the orchestrator that coordinates the replacement logic.
    """
    from app.schemas.chat import Message

    if messages is None:
        messages = []

    # Extract parameters from context
    new_system_prompt = kwargs.get('new_system_prompt') or (ctx or {}).get('new_system_prompt')
    classification = kwargs.get('classification') or (ctx or {}).get('classification')

    # Check preconditions for Step 46
    system_exists = bool(messages and getattr(messages[0], "role", None) == "system")
    has_classification = classification is not None

    with rag_step_timer(46, 'RAG.prompting.replace.system.message', 'ReplaceMsg', stage="start"):
        rag_step_log(
            step=46,
            step_id='RAG.prompting.replace.system.message',
            node_label='ReplaceMsg',
            category='prompting',
            type='process',
            processing_stage="started",
            system_message_exists=system_exists,
            has_classification=has_classification,
            preconditions_met=system_exists and has_classification
        )

        # Step 46 logic: Replace system message if conditions are met
        if system_exists and has_classification and new_system_prompt:
            # Store original content for logging
            original_content = getattr(messages[0], 'content', '')
            original_length = len(original_content)

            # Replace the system message
            messages[0] = Message(role="system", content=new_system_prompt)

            # Extract classification details for logging
            conf = getattr(classification, 'confidence', None) if hasattr(classification, 'confidence') else classification.get('confidence') if isinstance(classification, dict) else None
            domain = getattr(classification, 'domain', None) if hasattr(classification, 'domain') else classification.get('domain') if isinstance(classification, dict) else None
            action = getattr(classification, 'action', None) if hasattr(classification, 'action') else classification.get('action') if isinstance(classification, dict) else None

            # Convert domain enum to string if needed
            if hasattr(domain, 'value'):
                domain = domain.value
            if hasattr(action, 'value'):
                action = action.value

            rag_step_log(
                step=46,
                step_id='RAG.prompting.replace.system.message',
                node_label='ReplaceMsg',
                decision="system_message_replaced",
                action_taken="replace",
                original_system_content_length=original_length,
                new_system_content_length=len(new_system_prompt),
                has_classification=True,
                classification_confidence=conf,
                domain=domain,
                action=action,
                processing_stage="completed"
            )

            return messages
        else:
            # Conditions not met - no replacement
            reason = []
            if not system_exists:
                reason.append("no_system_message")
            if not has_classification:
                reason.append("no_classification")
            if not new_system_prompt:
                reason.append("no_new_prompt")

            rag_step_log(
                step=46,
                step_id='RAG.prompting.replace.system.message',
                node_label='ReplaceMsg',
                decision="no_replacement",
                action_taken="skip",
                skip_reason="|".join(reason),
                system_message_exists=system_exists,
                has_classification=has_classification,
                new_prompt_provided=bool(new_system_prompt),
                processing_stage="completed"
            )

            return messages

def step_47__insert_msg(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 47 — Insert system message
    ID: RAG.prompting.insert.system.message
    Type: process | Category: prompting | Node: InsertMsg

    Inserts system message at position 0 when:
    1. No system message exists in messages
    2. System prompt is provided

    This is the orchestrator that coordinates the insertion logic.
    """
    from app.schemas.chat import Message

    if messages is None:
        messages = []

    # Extract parameters from context
    system_prompt = kwargs.get('system_prompt') or (ctx or {}).get('system_prompt')
    classification = kwargs.get('classification') or (ctx or {}).get('classification')

    # Check preconditions for Step 47
    system_exists = bool(messages and getattr(messages[0], "role", None) == "system")
    has_classification = classification is not None
    messages_empty = len(messages) == 0

    with rag_step_timer(47, 'RAG.prompting.insert.system.message', 'InsertMsg', stage="start"):
        rag_step_log(
            step=47,
            step_id='RAG.prompting.insert.system.message',
            node_label='InsertMsg',
            category='prompting',
            type='process',
            processing_stage="started",
            system_message_exists=system_exists,
            has_classification=has_classification,
            messages_empty=messages_empty,
            preconditions_met=not system_exists and system_prompt is not None
        )

        # Step 47 logic: Insert system message if conditions are met
        if not system_exists and system_prompt:
            # Store original count for logging
            original_count = len(messages)

            # Insert system message at position 0
            messages.insert(0, Message(role="system", content=system_prompt))

            # Extract classification details for logging
            conf = getattr(classification, 'confidence', None) if hasattr(classification, 'confidence') else classification.get('confidence') if isinstance(classification, dict) else None
            domain = getattr(classification, 'domain', None) if hasattr(classification, 'domain') else classification.get('domain') if isinstance(classification, dict) else None
            action = getattr(classification, 'action', None) if hasattr(classification, 'action') else classification.get('action') if isinstance(classification, dict) else None

            # Convert domain enum to string if needed
            if hasattr(domain, 'value'):
                domain = domain.value
            if hasattr(action, 'value'):
                action = action.value

            rag_step_log(
                step=47,
                step_id='RAG.prompting.insert.system.message',
                node_label='InsertMsg',
                decision="system_message_inserted",
                action_taken="insert",
                system_message_exists=False,
                messages_empty=messages_empty,
                original_messages_count=original_count,
                messages_count=len(messages),
                insert_position=0,
                has_classification=has_classification,
                classification_confidence=conf,
                domain=domain,
                action=action,
                system_content_length=len(system_prompt),
                processing_stage="completed"
            )

            return messages
        else:
            # Conditions not met - no insertion
            reason = []
            if system_exists:
                reason.append("system_message_exists")
            if not system_prompt:
                reason.append("no_system_prompt")

            rag_step_log(
                step=47,
                step_id='RAG.prompting.insert.system.message',
                node_label='InsertMsg',
                decision="no_insertion",
                action_taken="skip",
                skip_reason="|".join(reason),
                system_message_exists=system_exists,
                messages_empty=messages_empty,
                system_prompt_provided=bool(system_prompt),
                processing_stage="completed"
            )

            return messages
