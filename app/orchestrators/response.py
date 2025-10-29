# AUTO-GENERATED ORCHESTRATOR STUBS (safe to edit below stubs)
# These functions are the functional *nodes* that mirror the Mermaid diagram.
# Implement thin coordination here (call services/factories), not core business logic.

from contextlib import nullcontext
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

try:
    from app.observability.rag_logging import rag_step_log, rag_step_timer
except Exception:  # pragma: no cover
    def rag_step_log(**kwargs): return None
    def rag_step_timer(*args, **kwargs): return nullcontext()

async def step_8__init_agent(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """RAG STEP 8 — LangGraphAgent.get_response Initialize workflow
    ID: RAG.response.langgraphagent.get.response.initialize.workflow
    Type: process | Category: response | Node: InitAgent

    Initializes the LangGraph workflow with processed messages and context.
    This orchestrator coordinates the handoff to the main RAG processing pipeline.
    """
    from app.core.logging import logger
    from app.core.langgraph.graph import LangGraphAgent
    from datetime import datetime, timezone

    with rag_step_timer(8, 'RAG.response.langgraphagent.get.response.initialize.workflow', 'InitAgent', stage="start"):
        rag_step_log(step=8, step_id='RAG.response.langgraphagent.get.response.initialize.workflow', node_label='InitAgent',
                     category='response', type='process', processing_stage="started")

        # Extract context parameters
        context = ctx or {}
        validated_request = kwargs.get('validated_request') or context.get('validated_request')
        session = kwargs.get('session') or context.get('session')
        user = kwargs.get('user') or context.get('user')
        request_metadata = kwargs.get('request_metadata') or context.get('request_metadata', {})
        request_id = request_metadata.get('request_id', 'unknown')

        # Use passed messages or extract from validated request
        processed_messages = messages
        if not processed_messages and validated_request:
            processed_messages = validated_request.get('messages', [])

        # Initialize result structure
        result = {
            'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'workflow_initialized': False,
            'agent_ready': False,
            'processed_messages': processed_messages,
            'session': session,
            'user': user,
            'next_step': 'ProcessMessages',
            'ready_for_processing': False,
            'workflow_context': {},
            'error': None
        }

        try:
            # Step 1: Validate required data
            if not processed_messages:
                result['error'] = 'Missing processed messages for workflow initialization'
                logger.error("Workflow initialization failed: Missing messages", request_id=request_id)
                rag_step_log(step=8, step_id='RAG.response.langgraphagent.get.response.initialize.workflow',
                           node_label='InitAgent', processing_stage="completed", error="missing_messages",
                           workflow_initialized=False, request_id=request_id)
                return result

            if not session:
                result['error'] = 'Missing session for workflow initialization'
                logger.error("Workflow initialization failed: Missing session", request_id=request_id)
                rag_step_log(step=8, step_id='RAG.response.langgraphagent.get.response.initialize.workflow',
                           node_label='InitAgent', processing_stage="completed", error="missing_session",
                           workflow_initialized=False, request_id=request_id)
                return result

            # Step 2: Initialize workflow context
            workflow_context = {
                'session_id': session.id,
                'user_id': session.user_id,
                'message_count': len(processed_messages),
                'request_id': request_id,
                'privacy_processed': context.get('privacy_enabled', False),
                'gdpr_logged': context.get('gdpr_logged', False),
                'workflow_stage': 'initialized'
            }

            # Step 3: Initialize LangGraph agent
            agent = LangGraphAgent()

            # Step 4: Mark workflow as ready
            result['workflow_initialized'] = True
            result['agent_ready'] = True
            result['ready_for_processing'] = True
            result['workflow_context'] = workflow_context

            session_id = session.id
            user_id = session.user_id

            logger.info(
                "RAG workflow initialized successfully",
                session_id=session_id,
                user_id=user_id,
                request_id=request_id,
                message_count=len(processed_messages),
                privacy_processed=workflow_context['privacy_processed'],
                extra={
                    'workflow_event': 'initialized',
                    'agent_ready': True,
                    'message_count': len(processed_messages)
                }
            )

            rag_step_log(
                step=8,
                step_id='RAG.response.langgraphagent.get.response.initialize.workflow',
                node_label='InitAgent',
                processing_stage="completed",
                workflow_initialized=True,
                agent_ready=True,
                ready_for_processing=True,
                message_count=len(processed_messages),
                next_step='ProcessMessages',
                session_id=session_id,
                user_id=user_id,
                request_id=request_id,
                privacy_processed=workflow_context['privacy_processed']
            )

            return result

        except Exception as e:
            # Handle workflow initialization errors
            result['error'] = f'Workflow initialization error: {str(e)}'

            session_id = session.id if session else 'unknown'
            user_id = session.user_id if session else 'unknown'

            logger.error(
                "RAG workflow initialization failed",
                error=str(e),
                session_id=session_id,
                user_id=user_id,
                request_id=request_id,
                exc_info=True
            )

            rag_step_log(
                step=8,
                step_id='RAG.response.langgraphagent.get.response.initialize.workflow',
                node_label='InitAgent',
                processing_stage="completed",
                error=str(e),
                workflow_initialized=False,
                agent_ready=False,
                session_id=session_id,
                user_id=user_id,
                request_id=request_id
            )

            return result

async def step_30__return_complete(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """RAG STEP 30 — Return ChatResponse.

    ID: RAG.response.return.chatresponse
    Type: process | Category: response | Node: ReturnComplete

    Thin async orchestrator that formats responses into ChatResponse structure with proper
    messages and metadata. Handles both Golden Set responses (Step 28) and LLM responses
    (StreamCheck→No). Routes to CollectMetrics (Step 111) per Mermaid diagram.
    """
    ctx = ctx or {}
    request_id = ctx.get('request_id', 'unknown')

    with rag_step_timer(30, 'RAG.response.return.chatresponse', 'ReturnComplete',
                       request_id=request_id, stage="start"):
        rag_step_log(step=30, step_id='RAG.response.return.chatresponse', node_label='ReturnComplete',
                     category='response', type='process', request_id=request_id, processing_stage="started")

        try:
            # Format ChatResponse using helper function
            chat_response_result = await _format_chat_response(ctx)

            # Build result with preserved context and ChatResponse
            result = {
                **ctx,
                'chat_response': chat_response_result['chat_response'],
                'chat_response_prepared': chat_response_result['success'],
                'response_formatting_metadata': chat_response_result['formatting_metadata'],
                'previous_step': ctx.get('rag_step'),
                'next_step': 111,
                'next_step_id': 'RAG.metrics.collect.usage.metrics',
                'route_to': 'CollectMetrics',
                'response_completion_metadata': {
                    'completed_at': datetime.now(timezone.utc).isoformat(),
                    'response_delivered': True,
                    'formatted_for_delivery': True
                },
                'request_id': request_id
            }

            # Add error info if formatting failed
            if not chat_response_result['success']:
                result['error'] = chat_response_result['error']

            rag_step_log(
                step=30,
                step_id='RAG.response.return.chatresponse',
                node_label='ReturnComplete',
                request_id=request_id,
                chat_response_prepared=chat_response_result['success'],
                message_count=len(chat_response_result['chat_response'].get('messages', [])),
                response_type=chat_response_result['formatting_metadata'].get('response_type'),
                source_step=ctx.get('rag_step'),
                next_step=111,
                route_to='CollectMetrics',
                processing_stage="completed"
            )

            return result

        except Exception as e:
            rag_step_log(
                step=30,
                step_id='RAG.response.return.chatresponse',
                node_label='ReturnComplete',
                request_id=request_id,
                error=str(e),
                processing_stage="error"
            )
            # On error, still route to CollectMetrics with error context
            return await _handle_return_complete_error(ctx, str(e))


async def _format_chat_response(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Format context data into proper ChatResponse structure.

    Handles various input formats from ServeGolden, StreamCheck, and other sources.
    """
    try:
        # Extract messages from various possible sources
        messages = _extract_messages_from_context(ctx)

        # Build response metadata
        response_metadata = _build_response_metadata(ctx)

        # Create ChatResponse structure
        chat_response = {
            'messages': messages,
            'metadata': response_metadata
        }

        # Create formatting metadata
        formatting_metadata = {
            'formatted_at': datetime.now(timezone.utc).isoformat(),
            'response_type': 'chat_response',
            'message_count': len(messages),
            'source_step': ctx.get('rag_step'),
            'metadata_fields': list(response_metadata.keys())
        }

        return {
            'success': True,
            'chat_response': chat_response,
            'formatting_metadata': formatting_metadata
        }

    except Exception as e:
        # Return minimal response on error
        return {
            'success': False,
            'error': str(e),
            'chat_response': {
                'messages': [{'role': 'assistant', 'content': 'Response formatting error occurred.'}],
                'metadata': {'source': 'error', 'formatted_at': datetime.now(timezone.utc).isoformat()}
            },
            'formatting_metadata': {
                'formatted_at': datetime.now(timezone.utc).isoformat(),
                'response_type': 'error_response',
                'message_count': 1,
                'error': str(e)
            }
        }


def _extract_messages_from_context(ctx: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract and format messages from context in priority order."""
    # Priority 1: Direct messages field
    if ctx.get('messages'):
        messages = ctx['messages']
        if isinstance(messages, list) and messages:
            return _normalize_messages(messages)

    # Priority 2: Processed messages (from StreamCheck path)
    if ctx.get('processed_messages'):
        messages = ctx['processed_messages']
        if isinstance(messages, list) and messages:
            return _normalize_messages(messages)

    # Priority 3: Response field (from ServeGolden path)
    if ctx.get('response'):
        response_data = ctx['response']
        if isinstance(response_data, dict) and response_data.get('answer'):
            # Create messages from golden answer
            messages = []
            # Add user question if available
            if ctx.get('query') or response_data.get('question'):
                question = ctx.get('query') or response_data.get('question')
                messages.append({'role': 'user', 'content': question})
            # Add assistant answer
            messages.append({'role': 'assistant', 'content': response_data['answer']})
            return messages
        elif isinstance(response_data, str):
            return [{'role': 'assistant', 'content': response_data}]

    # Priority 4: Direct response string
    if ctx.get('response') and isinstance(ctx['response'], str):
        return [{'role': 'assistant', 'content': ctx['response']}]

    # Fallback: Create minimal message structure
    return [{'role': 'assistant', 'content': 'Response delivered successfully.'}]


def _normalize_messages(messages: List[Any]) -> List[Dict[str, Any]]:
    """Normalize messages to proper format with role and content."""
    normalized = []

    for msg in messages:
        if isinstance(msg, dict):
            # Already in dict format - ensure required fields
            role = msg.get('role', 'assistant')
            content = str(msg.get('content', ''))
            if content.strip():
                normalized.append({'role': role, 'content': content})
        else:
            # Handle other message types (e.g., LangChain messages)
            if hasattr(msg, 'type') and hasattr(msg, 'content'):
                role = 'user' if msg.type == 'human' else 'assistant'
                content = str(msg.content)
                if content.strip():
                    normalized.append({'role': role, 'content': content})

    return normalized if normalized else [{'role': 'assistant', 'content': 'Message normalization completed.'}]


def _build_response_metadata(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Build response metadata from context."""
    metadata = {}

    # Add timestamp
    metadata['formatted_at'] = datetime.now(timezone.utc).isoformat()

    # Extract source information
    if ctx.get('response_metadata'):
        # From ServeGolden or other sources
        source_metadata = ctx['response_metadata']
        if isinstance(source_metadata, dict):
            metadata.update(source_metadata)

    # Extract LLM metadata
    if ctx.get('llm_metadata'):
        llm_metadata = ctx['llm_metadata']
        if isinstance(llm_metadata, dict):
            # Map LLM metadata to response metadata fields
            if 'provider' in llm_metadata:
                metadata['provider'] = llm_metadata['provider']
            if 'model' in llm_metadata:
                metadata['model_used'] = llm_metadata['model']
            if 'cost_eur' in llm_metadata:
                metadata['cost_eur'] = llm_metadata['cost_eur']
            if 'processing_time_ms' in llm_metadata:
                metadata['processing_time_ms'] = llm_metadata['processing_time_ms']

    # Add routing strategy if available
    if ctx.get('strategy'):
        metadata['strategy'] = ctx['strategy']
    elif ctx.get('route_strategy'):
        metadata['strategy'] = ctx['route_strategy']
    else:
        metadata['strategy'] = 'standard'

    # Determine source if not already set
    if 'source' not in metadata:
        if ctx.get('bypassed_llm') or ctx.get('response_metadata', {}).get('bypassed_llm'):
            metadata['source'] = 'golden_set'
        elif ctx.get('cached_response'):
            metadata['source'] = 'cache'
        elif ctx.get('llm_metadata'):
            metadata['source'] = 'llm'
        else:
            metadata['source'] = 'processed'

    # Ensure required fields have defaults
    if 'model_used' not in metadata:
        metadata['model_used'] = ctx.get('model', 'unknown')
    if 'provider' not in metadata:
        metadata['provider'] = ctx.get('provider', 'unknown')

    return metadata


async def _handle_return_complete_error(ctx: Dict[str, Any], error_msg: str) -> Dict[str, Any]:
    """Handle errors in ChatResponse formatting with graceful fallback."""
    return {
        **ctx,
        'chat_response': {
            'messages': [{'role': 'assistant', 'content': 'An error occurred while formatting the response.'}],
            'metadata': {
                'source': 'error',
                'error': error_msg,
                'formatted_at': datetime.now(timezone.utc).isoformat(),
                'model_used': 'unknown',
                'provider': 'unknown',
                'strategy': 'error_fallback'
            }
        },
        'chat_response_prepared': False,
        'error': error_msg,
        'next_step': 111,
        'next_step_id': 'RAG.metrics.collect.usage.metrics',
        'route_to': 'CollectMetrics',
        'previous_step': ctx.get('rag_step'),
        'response_completion_metadata': {
            'completed_at': datetime.now(timezone.utc).isoformat(),
            'response_delivered': False,
            'error_handled': True
        },
        'request_id': ctx.get('request_id', 'unknown')
    }

async def step_75__tool_check(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """RAG STEP 75 — Response has tool_calls?
    ID: RAG.response.response.has.tool.calls
    Type: process | Category: response | Node: ToolCheck

    Decision step that checks if the LLM response contains tool calls.
    Routes to tool call conversion (Step 76) if present, or simple message conversion (Step 77) if not.
    """
    from app.core.logging import logger
    from datetime import datetime, timezone

    ctx = ctx or {}

    # Extract context parameters
    llm_response = kwargs.get('llm_response') or ctx.get('llm_response')
    provider = kwargs.get('provider') or ctx.get('provider')
    model = kwargs.get('model') or ctx.get('model')
    request_id = ctx.get('request_id', 'unknown')

    # Initialize decision variables
    has_tool_calls = False
    tool_calls = []
    tool_call_count = 0
    tool_names = []
    next_step = None

    # Log decision start
    rag_step_log(
        step=75,
        step_id='RAG.response.response.has.tool.calls',
        node_label='ToolCheck',
        category='response',
        type='process',
        processing_stage='started',
        request_id=request_id,
        has_response=llm_response is not None
    )

    try:
        # Core decision logic: Check if response has tool calls
        # Matches existing logic from graph.py:742
        # if response.tool_calls:
        if llm_response and llm_response.tool_calls:
            has_tool_calls = True
            tool_calls = llm_response.tool_calls
            tool_call_count = len(tool_calls)
            tool_names = [tc.get('name') if isinstance(tc, dict) else tc.name for tc in tool_calls]
            next_step = 'convert_with_tool_calls'  # Route to Step 76

            logger.info(
                "response_has_tool_calls",
                extra={
                    'request_id': request_id,
                    'step': 75,
                    'tool_call_count': tool_call_count,
                    'tool_names': tool_names,
                    'next_step': next_step
                }
            )
        else:
            # No tool calls - simple message
            has_tool_calls = False
            tool_calls = []
            tool_call_count = 0
            tool_names = []
            next_step = 'convert_simple_message'  # Route to Step 77

            logger.info(
                "response_no_tool_calls",
                extra={
                    'request_id': request_id,
                    'step': 75,
                    'has_tool_calls': False,
                    'next_step': next_step
                }
            )

    except Exception as e:
        # Error in decision logic - default to simple message
        error_message = str(e)
        has_tool_calls = False
        next_step = 'convert_simple_message'

        logger.error(
            "step_75_decision_error",
            extra={
                'request_id': request_id,
                'step': 75,
                'error': error_message
            }
        )

    # Log decision completion
    rag_step_log(
        step=75,
        step_id='RAG.response.response.has.tool.calls',
        node_label='ToolCheck',
        processing_stage='completed',
        request_id=request_id,
        has_tool_calls=has_tool_calls,
        decision='with_tools' if has_tool_calls else 'simple_message',
        tool_call_count=tool_call_count,
        tool_names=tool_names,
        next_step=next_step
    )

    # Build orchestration result
    result = {
        'has_tool_calls': has_tool_calls,
        'tool_calls': tool_calls,
        'tool_call_count': tool_call_count,
        'tool_names': tool_names,
        'next_step': next_step,
        'llm_response': llm_response,
        'provider': provider,
        'model': model,
        'request_id': request_id,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }

    return result

async def step_101__final_response(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """RAG STEP 101 — Return to chat node for final response

    Thin async orchestrator that serves as a convergence point where all response paths
    (ToolResults, SimpleAIMsg, ToolErr) merge before final message processing.
    Routes all incoming responses to ProcessMessages (Step 102) per Mermaid flow.

    Incoming: ToolResults, SimpleAIMsg, ToolErr
    Outgoing: ProcessMsg (Step 102)
    """
    with rag_step_timer(101, 'RAG.response.return.to.chat.node.for.final.response', 'FinalResponse', stage="start"):
        ctx = ctx or {}

        rag_step_log(
            step=101,
            step_id='RAG.response.return.to.chat.node.for.final.response',
            node_label='FinalResponse',
            category='response',
            type='process',
            request_id=ctx.get('request_id'),
            response_source=ctx.get('response_source'),
            processing_stage="started"
        )

        # Step 101 is a convergence point - preserve all context and route to ProcessMessages
        result = ctx.copy()

        # Add final response stage metadata
        result.update({
            'processing_stage': 'final_response',
            'next_step': 'process_messages',
            'final_response_timestamp': datetime.now(timezone.utc).isoformat()
        })

        # Preserve response source information for downstream processing
        response_source = ctx.get('response_source', 'unknown')

        rag_step_log(
            step=101,
            step_id='RAG.response.return.to.chat.node.for.final.response',
            node_label='FinalResponse',
            request_id=ctx.get('request_id'),
            response_source=response_source,
            convergence_point=True,
            next_step='process_messages',
            processing_stage="completed"
        )

        return result

async def step_102__process_msg(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """RAG STEP 102 — LangGraphAgent.__process_messages Convert to dict

    Thin async orchestrator that converts LangChain BaseMessage objects to dictionary format
    using the existing LangGraphAgent.__process_messages logic. Filters to keep only user and
    assistant messages with content. Routes to LogComplete (Step 103) per Mermaid flow.

    Incoming: FinalResponse (Step 101), ReturnCached (Step 66)
    Outgoing: LogComplete (Step 103)
    """
    with rag_step_timer(102, 'RAG.response.langgraphagent.process.messages.convert.to.dict', 'ProcessMsg', stage="start"):
        ctx = ctx or {}
        conversation_messages = ctx.get('messages', [])

        rag_step_log(
            step=102,
            step_id='RAG.response.langgraphagent.process.messages.convert.to.dict',
            node_label='ProcessMsg',
            category='response',
            type='process',
            request_id=ctx.get('request_id'),
            original_message_count=len(conversation_messages),
            processing_stage="started"
        )

        # Convert messages using the same logic as LangGraphAgent.__process_messages
        processed_messages = _process_messages_to_dict(conversation_messages)

        # Preserve all context and add processing metadata
        result = ctx.copy()
        result.update({
            'processed_messages': processed_messages,
            'processing_stage': 'message_processing',
            'next_step': 'log_completion',
            'original_message_count': len(conversation_messages),
            'processed_message_count': len(processed_messages),
            'message_processing_timestamp': datetime.now(timezone.utc).isoformat()
        })

        rag_step_log(
            step=102,
            step_id='RAG.response.langgraphagent.process.messages.convert.to.dict',
            node_label='ProcessMsg',
            request_id=ctx.get('request_id'),
            original_message_count=len(conversation_messages),
            processed_message_count=len(processed_messages),
            next_step='log_completion',
            processing_stage="completed"
        )

        return result


def _process_messages_to_dict(messages):
    """Convert LangChain BaseMessage objects to dictionary format.
    Mirrors the logic from LangGraphAgent.__process_messages.

    Filters to keep only assistant and user messages with content.
    """
    try:
        from langchain_core.messages import convert_to_openai_messages
        from app.schemas.chat import Message

        # Convert to OpenAI format
        openai_style_messages = convert_to_openai_messages(messages)

        # Filter and convert to dict format (same logic as __process_messages)
        processed = []
        for message in openai_style_messages:
            if (message.get("role") in ["assistant", "user"] and
                message.get("content") and
                str(message.get("content")).strip()):
                processed.append({
                    'role': message["role"],
                    'content': str(message["content"])
                })

        return processed

    except Exception:
        # Fallback: simple dict conversion if imports fail
        processed = []
        for msg in messages:
            if hasattr(msg, 'type') and msg.type in ['human', 'ai']:
                role = 'user' if msg.type == 'human' else 'assistant'
                content = getattr(msg, 'content', '')
                if content and str(content).strip():
                    processed.append({
                        'role': role,
                        'content': str(content)
                    })
        return processed


def _prepare_final_response(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare the final response for delivery to user."""
    final_response = {}

    # Extract response content
    response = ctx.get('response', '')
    if not response and ctx.get('messages'):
        # Extract response from last assistant message if not directly provided
        for msg in reversed(ctx.get('messages', [])):
            if isinstance(msg, dict) and msg.get('role') == 'assistant':
                response = msg.get('content', '')
                break

    final_response['response'] = response

    # Extract messages
    messages = ctx.get('messages', [])
    if not messages and response:
        # Create minimal message structure if missing
        messages = [{'role': 'assistant', 'content': response}]

    final_response['messages'] = messages

    return final_response


def _validate_response_delivery(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Validate response delivery requirements and return status metadata."""
    status = {}

    # Check response type
    response_type = ctx.get('response_type', 'text')
    status['response_type'] = response_type

    # Check if streaming response
    if ctx.get('streaming_response') or ctx.get('streaming_completed'):
        status['streaming_response'] = True
        status['streaming_completed'] = ctx.get('streaming_completed', True)
        if ctx.get('chunks_sent'):
            status['chunks_sent'] = ctx.get('chunks_sent')
        if ctx.get('total_bytes'):
            status['total_bytes'] = ctx.get('total_bytes')

    # Check error handling
    if ctx.get('error'):
        status['error'] = ctx.get('error')
        status['success'] = ctx.get('success', False)

    # Check if metrics were collected
    if ctx.get('metrics_collected'):
        status['metrics_collected'] = True

    # Include performance metadata if available
    performance_fields = [
        'response_time_ms', 'total_tokens', 'cost', 'cache_hit',
        'provider', 'model', 'health_score'
    ]
    for field in performance_fields:
        if ctx.get(field) is not None:
            status[field] = ctx.get(field)

    # Include feedback metadata if available
    feedback_fields = [
        'feedback_enabled', 'feedback_options', 'expert_feedback_available'
    ]
    for field in feedback_fields:
        if ctx.get(field) is not None:
            status[field] = ctx.get(field)

    return status


async def step_112__end(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """RAG STEP 112 — Return response to user.

    Final step in the RAG pipeline that delivers the complete response to the user.
    Takes processed data and metrics from CollectMetrics (Step 111) and creates the final response output.
    This is a terminating step (startEnd type) that completes the RAG processing pipeline.

    Incoming: CollectMetrics (Step 111)
    Outgoing: Final response to user (pipeline termination)
    """
    with rag_step_timer(112, 'RAG.response.return.response.to.user', 'End', stage="start"):
        ctx = ctx or {}

        rag_step_log(
            step=112,
            step_id='RAG.response.return.response.to.user',
            node_label='End',
            category='response',
            type='startEnd',
            request_id=ctx.get('request_id'),
            processing_stage="started"
        )

        # Finalize response delivery
        final_response = _prepare_final_response(ctx)
        delivery_status = _validate_response_delivery(ctx)

        # Preserve all context and add completion metadata
        result = ctx.copy()

        # Add final response metadata
        result.update({
            'response_delivered': True,
            'final_step': True,
            'processing_stage': 'completed',
            'completion_timestamp': datetime.now(timezone.utc).isoformat()
        })

        # Ensure response and messages are properly set
        if 'response' not in result or not result['response']:
            result['response'] = final_response.get('response', '')

        if 'messages' not in result or not result['messages']:
            result['messages'] = final_response.get('messages', [])

        # Add delivery status metadata
        result.update(delivery_status)

        rag_step_log(
            step=112,
            step_id='RAG.response.return.response.to.user',
            node_label='End',
            request_id=ctx.get('request_id'),
            response_delivered=True,
            final_step=True,
            response_type=result.get('response_type', 'text'),
            user_id=result.get('user_id'),
            session_id=result.get('session_id'),
            processing_stage="completed"
        )

        return result
