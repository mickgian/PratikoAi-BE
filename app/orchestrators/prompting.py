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

async def step_15__default_prompt(*, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 15 — Continue without classification
    ID: RAG.prompting.continue.without.classification
    Type: process | Category: prompting | Node: DefaultPrompt

    Bypasses classification and sets up default prompting strategy.
    This orchestrator coordinates default prompt setup when classification fails or is skipped.
    """
    from app.core.logging import logger
    from app.core.prompts import SYSTEM_PROMPT
    from datetime import datetime, timezone

    with rag_step_timer(15, 'RAG.prompting.continue.without.classification', 'DefaultPrompt', stage="start"):
        rag_step_log(step=15, step_id='RAG.prompting.continue.without.classification', node_label='DefaultPrompt',
                     category='prompting', type='process', processing_stage="started")

        # Extract context parameters
        context = ctx or {}
        user_query = kwargs.get('user_query') or context.get('user_query', '')
        request_id = kwargs.get('request_id') or context.get('request_id', 'unknown')
        classification_attempted = context.get('classification_attempted', False)
        classification_successful = context.get('classification_successful', False)

        # Initialize result structure
        result = {
            'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'default_prompt_applied': False,
            'classification_bypassed': False,
            'prompt_strategy': 'default',
            'system_prompt': None,
            'prompt_context': {},
            'query_analysis': {},
            'next_step': 'SelectPrompt',
            'ready_for_prompt_selection': False,
            'bypass_reason': None,
            'routing_decision': 'default_workflow',
            'prompt_type': 'system',
            'prompt_source': 'default',
            'error': None
        }

        try:
            # Step 1: Handle missing context
            if ctx is None:
                result['error'] = 'Missing context for default prompt setup'
                logger.error("Default prompt setup failed: Missing context", request_id=request_id)
                rag_step_log(step=15, step_id='RAG.prompting.continue.without.classification',
                           node_label='DefaultPrompt', processing_stage="completed", error="missing_context",
                           default_prompt_applied=False, request_id=request_id)
                return result

            # Step 2: Determine bypass reason
            if not classification_attempted:
                bypass_reason = 'no_classification_attempted'
            elif not classification_successful:
                bypass_reason = 'classification_failed'
            else:
                bypass_reason = 'classification_bypass_requested'

            # Step 3: Handle empty or minimal context
            if not user_query and not context:
                logger.warning("Minimal context provided for default prompt setup", request_id=request_id)

            # Step 4: Analyze user query characteristics
            query_analysis = await _analyze_user_query(user_query)

            # Step 5: Select appropriate system prompt
            system_prompt = await _get_default_system_prompt(query_analysis, context)

            # Step 6: Build prompt context for downstream processing
            prompt_context = {
                'strategy': 'default_prompting',
                'classification_bypassed': True,
                'bypass_reason': bypass_reason,
                'user_query': user_query,
                'query_complexity': query_analysis.get('complexity', 'simple'),
                'message_count': len(context.get('user_messages', [])),
                'session_context': context.get('session_context', {}),
                'workflow_mode': context.get('workflow_mode', 'standard')
            }

            # Step 7: Build successful result
            result.update({
                'default_prompt_applied': True,
                'classification_bypassed': True,
                'system_prompt': system_prompt,
                'prompt_context': prompt_context,
                'query_analysis': query_analysis,
                'ready_for_prompt_selection': True,
                'bypass_reason': bypass_reason
            })

            logger.info(
                "Default prompt setup completed successfully",
                bypass_reason=bypass_reason,
                query_complexity=query_analysis.get('complexity', 'simple'),
                query_length=query_analysis.get('length', 0),
                request_id=request_id,
                extra={
                    'prompting_event': 'default_prompt_applied',
                    'bypass_reason': bypass_reason,
                    'strategy': 'default_prompting',
                    'query_complexity': query_analysis.get('complexity', 'simple')
                }
            )

            rag_step_log(
                step=15,
                step_id='RAG.prompting.continue.without.classification',
                node_label='DefaultPrompt',
                processing_stage="completed",
                default_prompt_applied=True,
                classification_bypassed=True,
                prompt_strategy='default',
                bypass_reason=bypass_reason,
                next_step='SelectPrompt',
                ready_for_prompt_selection=True,
                request_id=request_id
            )

            return result

        except Exception as e:
            # Handle prompt setup errors
            result['error'] = f'Default prompt setup error: {str(e)}'

            logger.error(
                "Default prompt setup failed",
                error=str(e),
                request_id=request_id,
                exc_info=True
            )

            rag_step_log(
                step=15,
                step_id='RAG.prompting.continue.without.classification',
                node_label='DefaultPrompt',
                processing_stage="completed",
                error=str(e),
                default_prompt_applied=False,
                request_id=request_id
            )

            return result


async def _analyze_user_query(user_query: str) -> Dict[str, Any]:
    """Analyze user query characteristics for prompt selection."""
    if not user_query:
        return {
            'length': 0,
            'complexity': 'simple',
            'type': 'unknown',
            'requires_context': False
        }

    length = len(user_query)

    # Determine complexity based on length and content
    if length < 50:
        complexity = 'simple'
    elif length < 150:
        complexity = 'medium'
    else:
        complexity = 'complex'

    # Basic query type detection
    query_lower = user_query.lower()
    if any(word in query_lower for word in ['calculate', 'compute', 'math']):
        query_type = 'calculation'
    elif any(word in query_lower for word in ['explain', 'what is', 'how to']):
        query_type = 'informational'
    elif any(word in query_lower for word in ['help', 'assist', 'support']):
        query_type = 'assistance'
    else:
        query_type = 'general'

    # Determine if query likely requires additional context
    requires_context = length > 100 or any(word in query_lower for word in ['specific', 'detail', 'explain more'])

    return {
        'length': length,
        'complexity': complexity,
        'type': query_type,
        'requires_context': requires_context
    }


async def _get_default_system_prompt(query_analysis: Dict[str, Any], context: Dict[str, Any]) -> str:
    """Get appropriate default system prompt based on query analysis."""
    from app.core.prompts import SYSTEM_PROMPT

    # For now, use the standard system prompt
    # Future enhancement: could select different prompts based on query characteristics
    return SYSTEM_PROMPT

async def step_41__select_prompt(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 41 — LangGraphAgent._get_system_prompt Select appropriate prompt
    ID: RAG.prompting.langgraphagent.get.system.prompt.select.appropriate.prompt
    Type: process | Category: prompting | Node: SelectPrompt

    Selects the appropriate system prompt based on domain-action classification confidence.
    Routes to domain-specific prompts for high-confidence classifications or falls back
    to default prompts. Thin orchestration that preserves existing prompt selection behavior.
    """
    from app.core.logging import logger
    from app.core.config import get_settings
    from app.core.prompts import SYSTEM_PROMPT
    from datetime import datetime, timezone

    settings = get_settings()

    # Extract context parameters
    request_id = kwargs.get('request_id') or (ctx or {}).get('request_id', 'unknown')
    classification = kwargs.get('classification') or (ctx or {}).get('classification')
    prompt_template_manager = kwargs.get('prompt_template_manager') or (ctx or {}).get('prompt_template_manager')

    # Extract user query from messages
    user_query = ""
    for m in reversed(messages or []):
        if getattr(m, "role", None) == "user":
            user_query = getattr(m, "content", "") or ""
            break

    # Classification context
    conf = classification.confidence if classification else None
    domain = classification.domain.value if classification else None
    action = classification.action.value if classification else None
    threshold = getattr(settings, "CLASSIFICATION_CONFIDENCE_THRESHOLD", 0.6)

    # Initialize result variables
    prompt_selected = False
    selected_prompt = ""
    prompt_type = "default"
    selection_reason = "unknown"
    error = None
    confidence_meets_threshold = False

    # STEP 41 timing (positional 3 args)
    with rag_step_timer(
        41,
        "RAG.prompting.langgraphagent.get.system.prompt.select.appropriate.prompt",
        "SelectPrompt",
        classification_confidence=conf,
        domain=domain,
    ):
        rag_step_log(
            step=41,
            step_id='RAG.prompting.langgraphagent.get.system.prompt.select.appropriate.prompt',
            node_label='SelectPrompt',
            category='prompting',
            type='process',
            processing_stage='started',
            request_id=request_id,
            classification_available=classification is not None,
            classification_confidence=conf,
            confidence_threshold=threshold,
            user_query=user_query[:100] if user_query else ''
        )

        try:
            # STEP 42: classification exists & threshold decision
            if not classification:
                rag_step_log(
                    step=42,
                    step_id="RAG.classify.classification.exists.and.confidence.at.least.0.6",
                    node_label="ClassConfidence",
                    classification_exists=False,
                    classification_confidence=None,
                    confidence_threshold=threshold,
                    decision_outcome="use_default_prompt",
                    reason="classification_not_available",
                    user_query=user_query,
                    domain=None,
                    action=None,
                )

                # STEP 44: Use orchestrator for default (no classification)
                prompt = step_44__default_sys_prompt(
                    messages=messages,
                    ctx={
                        'classification': None,
                        'user_query': user_query,
                        'trigger_reason': 'no_classification'
                    }
                )

                prompt_selected = True
                selected_prompt = prompt
                prompt_type = "default"
                selection_reason = "no_classification_available"
                confidence_meets_threshold = False  # not applicable -> False

            else:
                meets = (conf or 0.0) >= threshold
                confidence_meets_threshold = meets

                rag_step_log(
                    step=42,
                    step_id="RAG.classify.classification.exists.and.confidence.at.least.0.6",
                    node_label="ClassConfidence",
                    classification_exists=True,
                    classification_confidence=conf,
                    confidence_threshold=threshold,
                    decision_outcome="use_domain_prompt" if meets else "use_default_prompt",
                    user_query=user_query,
                    domain=domain,
                    action=action,
                )

                if not meets:
                    # STEP 44: Use orchestrator for default (low confidence)
                    prompt = step_44__default_sys_prompt(
                        messages=messages,
                        ctx={
                            'classification': classification,
                            'user_query': user_query,
                            'trigger_reason': 'low_confidence'
                        }
                    )

                    prompt_selected = True
                    selected_prompt = prompt
                    prompt_type = "default"
                    selection_reason = "low_confidence"

                else:
                    # Domain prompt path (may fail)
                    try:
                        # STEP 43: Get domain-specific prompt via orchestrator
                        from app.orchestrators.classify import step_43__domain_prompt

                        domain_prompt_result = await step_43__domain_prompt(
                            messages=messages,
                            ctx={
                                'classification': classification,
                                'prompt_template_manager': prompt_template_manager,
                                'user_query': user_query,
                                'prompt_context': None,
                                'request_id': request_id
                            }
                        )

                        # Extract the generated prompt
                        if domain_prompt_result and domain_prompt_result.get('prompt_generated'):
                            domain_prompt = domain_prompt_result.get('domain_prompt', '')
                        else:
                            # Step 43 failed to generate prompt
                            raise Exception(
                                domain_prompt_result.get('error_message', 'Domain prompt generation failed')
                            )

                        prompt_selected = True
                        selected_prompt = domain_prompt
                        prompt_type = "domain_specific"
                        selection_reason = "confidence_meets_threshold"

                    except Exception as e:
                        # Fallback to default
                        selected_prompt = SYSTEM_PROMPT
                        prompt_selected = True
                        prompt_type = "default"
                        selection_reason = "domain_prompt_error_fallback"
                        error = str(e)

                        logger.error(
                            f"Domain prompt generation failed, falling back to default: {error}",
                            extra={
                                'request_id': request_id,
                                'error': error,
                                'step': 41,
                                'domain': domain,
                                'action': action,
                                'classification_confidence': conf
                            }
                        )

                        # STEP 44: default due to error
                        rag_step_log(
                            step=44,
                            step_id="RAG.prompting.use.default.system.prompt",
                            node_label="DefaultSysPrompt",
                            trigger_reason="error_fallback",
                            prompt_type="default",
                            classification_available=True,
                            classification_confidence=conf,
                            confidence_threshold=threshold,
                            domain=domain,
                            action=action,
                            user_query=user_query,
                            prompt_length=len(selected_prompt) if selected_prompt else 0,
                            processing_stage="completed",
                            reasons=["domain_prompt_generation_failed"],
                            confidence=conf,
                            decision="error_fallback",
                        )

        except Exception as e:
            error = str(e)
            prompt_selected = False
            selected_prompt = SYSTEM_PROMPT  # Emergency fallback
            prompt_type = "default"
            selection_reason = "orchestrator_error_fallback"

            logger.error(
                f"Error in prompt selection orchestrator: {error}",
                extra={
                    'request_id': request_id,
                    'error': error,
                    'step': 41,
                    'user_query': user_query[:100] if user_query else ''
                }
            )

        # Build result preserving behavior while adding coordination metadata
        result = {
            'prompt_selected': prompt_selected,
            'selected_prompt': selected_prompt,
            'prompt_type': prompt_type,
            'selection_reason': selection_reason,
            'classification_available': classification is not None,
            'classification_confidence': conf,
            'confidence_meets_threshold': confidence_meets_threshold,
            'confidence_threshold': threshold,
            'domain': domain,
            'action': action,
            'user_query': user_query,
            'request_id': request_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'error': error
        }

        # STEP 41: final selection log
        rag_step_log(
            step=41,
            step_id="RAG.prompting.langgraphagent.get.system.prompt.select.appropriate.prompt",
            node_label="SelectPrompt",
            classification_confidence=conf,
            classification_available=classification is not None,
            confidence_below_threshold=classification is not None and not confidence_meets_threshold,
            confidence_threshold=threshold,
            reason=selection_reason,
            prompt_type=prompt_type,
            domain=domain,
            action=action,
            user_query=user_query,
            processing_stage='completed',
            request_id=request_id,
            prompt_selected=prompt_selected,
            error_occurred=error is not None
        )

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
