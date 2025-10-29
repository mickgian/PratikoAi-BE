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

async def step_104__stream_check(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """RAG STEP 104 — Streaming requested?

    Thin async orchestrator that determines if the client requested streaming response format.
    Checks request parameters, HTTP headers, and client preferences to make routing decision.
    Routes to StreamSetup (Step 105) for streaming or ReturnComplete (Step 112) for regular responses.

    Incoming: LogComplete (Step 103)
    Outgoing: StreamSetup (Step 105) [Yes] | ReturnComplete (Step 112) [No]
    """
    with rag_step_timer(104, 'RAG.streaming.streaming.requested', 'StreamCheck', stage="start"):
        ctx = ctx or {}

        rag_step_log(
            step=104,
            step_id='RAG.streaming.streaming.requested',
            node_label='StreamCheck',
            category='streaming',
            type='decision',
            request_id=ctx.get('request_id'),
            processing_stage="started"
        )

        # Determine if streaming is requested
        streaming_decision = _determine_streaming_preference(ctx)
        streaming_requested = streaming_decision['requested']
        decision_source = streaming_decision['source']

        # Preserve all context and add decision metadata
        result = ctx.copy()

        # Add streaming decision results
        result.update({
            'streaming_requested': streaming_requested,
            'decision': 'yes' if streaming_requested else 'no',
            'decision_source': decision_source,
            'processing_stage': 'streaming_decision',
            'decision_timestamp': datetime.now(timezone.utc).isoformat()
        })

        # Configure routing based on decision
        if streaming_requested:
            result['next_step'] = 'stream_setup'
            result['stream_configuration'] = _configure_streaming_options(ctx)
        else:
            result['next_step'] = 'return_complete'
            result['response_format'] = 'json'
            if decision_source == 'default':
                result['default_used'] = True

        rag_step_log(
            step=104,
            step_id='RAG.streaming.streaming.requested',
            node_label='StreamCheck',
            request_id=ctx.get('request_id'),
            streaming_requested=streaming_requested,
            decision=result['decision'],
            decision_source=decision_source,
            next_step=result['next_step'],
            processing_stage="completed"
        )

        return result


def _determine_streaming_preference(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Determine if streaming is requested based on various sources.

    Priority order:
    1. Streaming state (set by get_stream_response)
    2. Request data 'stream' parameter
    3. HTTP Accept header
    4. Default to non-streaming
    """
    # Check if streaming was explicitly requested in state (e.g. from get_stream_response)
    streaming_state = ctx.get('streaming', {})
    if 'requested' in streaming_state:
        return {
            'requested': streaming_state['requested'],
            'source': 'state'
        }

    request_data = ctx.get('request_data', {})
    http_headers = ctx.get('http_headers', {})

    # Check explicit stream parameter
    stream_param = request_data.get('stream')
    if stream_param is not None:
        streaming_requested = _parse_stream_value(stream_param)
        return {
            'requested': streaming_requested,
            'source': 'stream_parameter'
        }

    # Check HTTP Accept header
    accept_header = http_headers.get('Accept', '').lower()
    if 'text/event-stream' in accept_header:
        return {
            'requested': True,
            'source': 'http_headers'
        }

    # Default to non-streaming
    return {
        'requested': False,
        'source': 'default'
    }


def _parse_stream_value(stream_value) -> bool:
    """Parse various stream value formats to boolean."""
    if isinstance(stream_value, bool):
        return stream_value

    if isinstance(stream_value, (int, float)):
        return bool(stream_value)

    if isinstance(stream_value, str):
        lower_val = stream_value.lower().strip()
        if lower_val in ('true', '1', 'yes', 'on'):
            return True
        elif lower_val in ('false', '0', 'no', 'off'):
            return False

    # Default to False for invalid/unknown values
    return False


def _configure_streaming_options(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Configure streaming options when streaming is requested."""
    request_data = ctx.get('request_data', {})
    stream_options = request_data.get('stream_options', {})

    # Default streaming configuration
    config = {
        'media_type': 'text/event-stream',
        'chunk_size': stream_options.get('chunk_size', 1024),
        'include_usage': stream_options.get('include_usage', False),
        'include_metadata': stream_options.get('include_metadata', True)
    }

    return config

async def step_105__stream_setup(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """RAG STEP 105 — ChatbotController.chat_stream Setup SSE.

    Thin async orchestrator that sets up Server-Sent Events (SSE) streaming infrastructure
    for real-time response delivery. Configures SSE headers, streaming context, and prepares
    for async generator creation. Routes to AsyncGen (Step 106) per Mermaid flow.

    Incoming: StreamCheck (Step 104) [when streaming requested]
    Outgoing: AsyncGen (Step 106)
    """
    with rag_step_timer(105, 'RAG.streaming.chatbotcontroller.chat.stream.setup.sse', 'StreamSetup', stage="start"):
        ctx = ctx or {}

        rag_step_log(
            step=105,
            step_id='RAG.streaming.chatbotcontroller.chat.stream.setup.sse',
            node_label='StreamSetup',
            category='streaming',
            type='process',
            request_id=ctx.get('request_id'),
            streaming_requested=ctx.get('streaming_requested', True),
            processing_stage="started"
        )

        # Configure SSE headers and streaming setup
        sse_headers = _configure_sse_headers(ctx)
        stream_context = _prepare_stream_context(ctx)

        # Preserve all context and add streaming setup metadata
        result = ctx.copy()

        # Add streaming setup results
        result.update({
            'sse_headers': sse_headers,
            'stream_context': stream_context,
            'streaming_setup': 'configured',
            'processing_stage': 'streaming_setup',
            'next_step': 'create_async_generator',
            'setup_timestamp': datetime.now(timezone.utc).isoformat()
        })

        # Add validation warnings if needed
        validation_warnings = _validate_streaming_requirements(ctx)
        if validation_warnings:
            result['validation_warnings'] = validation_warnings

        rag_step_log(
            step=105,
            step_id='RAG.streaming.chatbotcontroller.chat.stream.setup.sse',
            node_label='StreamSetup',
            request_id=ctx.get('request_id'),
            streaming_setup='configured',
            headers_configured=len(sse_headers),
            stream_context_prepared=bool(stream_context),
            next_step='create_async_generator',
            processing_stage="completed"
        )

        return result


def _configure_sse_headers(ctx: Dict[str, Any]) -> Dict[str, str]:
    """Configure Server-Sent Events headers for streaming response."""
    stream_config = ctx.get('stream_configuration', {})

    # Base SSE headers
    headers = {
        'Content-Type': stream_config.get('media_type', 'text/event-stream'),
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Cache-Control',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS'
    }

    # Add compression headers if enabled
    if stream_config.get('enable_compression'):
        headers['Content-Encoding'] = 'gzip'

    # Add custom headers from stream configuration
    custom_headers = stream_config.get('custom_headers', {})
    headers.update(custom_headers)

    # Handle CORS if specified
    if ctx.get('client_origin'):
        headers['Access-Control-Allow-Origin'] = ctx['client_origin']

    return headers


def _prepare_stream_context(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare streaming context for async generator creation."""
    processed_messages = ctx.get('processed_messages', [])
    session_data = ctx.get('session_data', {})
    response_metadata = ctx.get('response_metadata', {})

    stream_context = {
        'messages': processed_messages,
        'session_id': session_data.get('id'),
        'user_id': session_data.get('user_id'),
        'provider': response_metadata.get('provider'),
        'model': response_metadata.get('model'),
        'streaming_enabled': True
    }

    # Add stream configuration settings
    stream_config = ctx.get('stream_configuration', {})
    stream_context.update({
        'chunk_size': stream_config.get('chunk_size', 1024),
        'include_usage': stream_config.get('include_usage', False),
        'include_metadata': stream_config.get('include_metadata', True),
        'heartbeat_interval': stream_config.get('heartbeat_interval', 30),
        'connection_timeout': stream_config.get('connection_timeout', 300)
    })

    return stream_context


def _validate_streaming_requirements(ctx: Dict[str, Any]) -> List[str]:
    """Validate streaming setup requirements and return warnings."""
    warnings = []

    # Check if streaming was actually requested
    if not ctx.get('streaming_requested', True):
        warnings.append("Streaming setup called but streaming_requested is False")

    # Check if messages are available
    processed_messages = ctx.get('processed_messages', [])
    if not processed_messages:
        warnings.append("No processed messages available for streaming")

    # Check if session data is available
    session_data = ctx.get('session_data', {})
    if not session_data.get('id'):
        warnings.append("No session ID available for streaming context")

    return warnings

async def step_108__write_sse(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """RAG STEP 108 — write_sse Format chunks.

    Thin async orchestrator that formats streaming chunks into SSE format using write_sse.
    Takes protected stream data from SinglePass (Step 107) and prepares for StreamingResponse (Step 109).
    Formats async generator chunks into proper Server-Sent Events format for browser consumption.

    Incoming: SinglePass (Step 107) [when stream protected]
    Outgoing: StreamingResponse (Step 109)
    """
    with rag_step_timer(108, 'RAG.streaming.write.sse.format.chunks', 'WriteSSE', stage="start"):
        ctx = ctx or {}

        rag_step_log(
            step=108,
            step_id='RAG.streaming.write.sse.format.chunks',
            node_label='WriteSSE',
            category='streaming',
            type='process',
            request_id=ctx.get('request_id'),
            processing_stage="started"
        )

        # Format stream chunks with SSE formatting
        sse_formatted_stream = _create_sse_formatted_generator(ctx)
        format_config = _prepare_sse_format_configuration(ctx)

        # Preserve all context and add formatting metadata
        result = ctx.copy()

        # Add SSE formatting results
        result.update({
            'sse_formatted_stream': sse_formatted_stream,
            'format_config': format_config,
            'chunks_formatted': True,
            'processing_stage': 'sse_formatted',
            'next_step': 'streaming_response',
            'formatting_timestamp': datetime.now(timezone.utc).isoformat()
        })

        # Add validation warnings if needed
        validation_warnings = _validate_sse_format_requirements(ctx)
        if validation_warnings:
            result['validation_warnings'] = validation_warnings

        rag_step_log(
            step=108,
            step_id='RAG.streaming.write.sse.format.chunks',
            node_label='WriteSSE',
            request_id=ctx.get('request_id'),
            chunks_formatted=True,
            format_configured=bool(format_config),
            next_step='streaming_response',
            processing_stage="completed"
        )

        return result


def _create_sse_formatted_generator(ctx: Dict[str, Any]) -> Any:
    """Create SSE-formatted generator using write_sse function."""
    from app.core.sse_write import write_sse

    wrapped_stream = ctx.get('wrapped_stream')

    if wrapped_stream is None:
        # Create a placeholder generator if none exists
        async def placeholder_generator():
            yield write_sse(None, "data: No stream available for SSE formatting\n\n")
        return placeholder_generator()

    async def sse_formatted_generator():
        """Generator that formats chunks using write_sse."""
        try:
            async for chunk in wrapped_stream:
                if chunk:
                    # Use write_sse to format the chunk properly
                    if isinstance(chunk, dict):
                        # Handle structured chunk data
                        content = chunk.get('content', str(chunk))
                        formatted_chunk = write_sse(None, f"data: {content}\n\n")
                    elif isinstance(chunk, str):
                        # Handle string chunks
                        if chunk == "[DONE]":
                            formatted_chunk = write_sse(None, "data: [DONE]\n\n")
                        else:
                            formatted_chunk = write_sse(None, f"data: {chunk}\n\n")
                    else:
                        # Handle other chunk types
                        formatted_chunk = write_sse(None, f"data: {str(chunk)}\n\n")

                    yield formatted_chunk
        except Exception as e:
            # Error handling in generator
            error_chunk = write_sse(None, f"data: Stream error: {str(e)}\n\n")
            yield error_chunk

    return sse_formatted_generator()


def _prepare_sse_format_configuration(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare configuration for SSE formatting."""
    protection_config = ctx.get('protection_config', {})
    sse_format_config = ctx.get('sse_format_config', {})
    formatting_options = ctx.get('formatting_options', {})
    format_options = ctx.get('format_options', {})

    # Base SSE format configuration
    config = {
        'sse_format': True,
        'session_id': protection_config.get('session_id'),
        'user_id': protection_config.get('user_id'),
        'provider': protection_config.get('provider', 'default'),
        'model': protection_config.get('model', 'default'),
        'streaming_enabled': protection_config.get('streaming_enabled', True)
    }

    # Add formatting parameters
    config.update({
        'chunk_size': protection_config.get('chunk_size', 1024),
        'include_usage': protection_config.get('include_usage', False),
        'include_metadata': protection_config.get('include_metadata', True),
        'format': protection_config.get('format', 'sse'),
        'compression': protection_config.get('compression', False)
    })

    # Add SSE-specific settings
    config.update({
        'event_type': sse_format_config.get('event_type', 'message'),
        'retry_interval': sse_format_config.get('retry_interval', 3000),
        'include_id': sse_format_config.get('include_id', False),
        'buffer_size': protection_config.get('buffer_size', 1024)
    })

    # Add formatting options if available
    if formatting_options:
        config.update({
            'pretty_json': formatting_options.get('pretty_json', False),
            'escape_newlines': formatting_options.get('escape_newlines', True),
            'max_chunk_size': formatting_options.get('max_chunk_size', 4096)
        })

    # Add format options if available
    if format_options:
        config.update({
            'json_format': format_options.get('json_format', False),
            'include_timestamps': format_options.get('include_timestamps', False)
        })

    # Add error handling and timeout settings
    config.update({
        'error_handling': protection_config.get('error_handling', 'standard'),
        'timeout_ms': protection_config.get('timeout_ms', 30000),
        'chunk_delimiter': protection_config.get('chunk_delimiter', '\n\n')
    })

    return config


def _validate_sse_format_requirements(ctx: Dict[str, Any]) -> List[str]:
    """Validate SSE formatting requirements and return warnings."""
    warnings = []

    # Check if wrapped stream is available
    wrapped_stream = ctx.get('wrapped_stream')
    if wrapped_stream is None:
        warnings.append("No wrapped stream available for SSE formatting")

    # Check if stream was protected
    stream_protected = ctx.get('stream_protected', False)
    if not stream_protected:
        warnings.append("stream not protected but SSE formatting requested")

    # Check protection configuration
    protection_config = ctx.get('protection_config', {})
    if not protection_config:
        warnings.append("No protection configuration available for SSE formatting")

    # Check session context
    session_id = protection_config.get('session_id')
    if not session_id:
        warnings.append("No session ID available for SSE formatting context")

    # Check if streaming is properly enabled
    streaming_enabled = protection_config.get('streaming_enabled')
    if streaming_enabled is False:
        warnings.append("Streaming not enabled but SSE formatting requested")

    return warnings


def _create_streaming_response(ctx: Dict[str, Any]) -> Any:
    """Create FastAPI StreamingResponse with SSE-formatted stream."""
    try:
        from fastapi.responses import StreamingResponse
    except ImportError:
        # Fallback if FastAPI not available
        class MockStreamingResponse:
            def __init__(self, content, media_type=None, headers=None):
                self.content = content
                self.media_type = media_type or 'text/event-stream'
                self.headers = headers or {}
        StreamingResponse = MockStreamingResponse

    # Get SSE-formatted stream
    sse_stream = ctx.get('sse_formatted_stream')
    if sse_stream is None:
        # Create empty stream if none available
        async def empty_stream():
            yield "data: [EMPTY]\n\n"
        sse_stream = empty_stream()

    # Prepare headers
    headers = ctx.get('sse_headers', {})
    default_headers = {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive'
    }
    response_headers = {**default_headers, **headers}

    # Get media type from format config
    format_config = ctx.get('format_config', {})
    media_type = format_config.get('media_type', 'text/event-stream')

    # Create StreamingResponse
    return StreamingResponse(
        content=sse_stream,
        media_type=media_type,
        headers=response_headers
    )


def _prepare_response_configuration(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare StreamingResponse configuration."""
    config = {}

    # Include format configuration
    format_config = ctx.get('format_config', {})
    config.update(format_config)

    # Add response-specific configuration
    response_options = ctx.get('response_options', {})
    config.update(response_options)

    # Set media type
    config['media_type'] = config.get('media_type', 'text/event-stream')

    # Configure headers
    sse_headers = ctx.get('sse_headers', {})
    if sse_headers:
        config['headers'] = sse_headers

    # Add response parameters
    response_parameters = ctx.get('response_parameters', {})
    if response_parameters:
        config.update(response_parameters)

    return config


def _validate_response_requirements(ctx: Dict[str, Any]) -> List[str]:
    """Validate StreamingResponse requirements and return warnings."""
    warnings = []

    # Check if SSE formatted stream is available
    sse_stream = ctx.get('sse_formatted_stream')
    if sse_stream is None:
        warnings.append("No SSE formatted stream available for StreamingResponse")

    # Check if chunks were formatted
    chunks_formatted = ctx.get('chunks_formatted')
    if chunks_formatted is False:
        warnings.append("Stream chunks not formatted but StreamingResponse requested")

    # Check format configuration
    format_config = ctx.get('format_config', {})
    if not format_config:
        warnings.append("No format configuration available for StreamingResponse")

    # Check session context
    session_id = format_config.get('session_id')
    if not session_id:
        warnings.append("No session ID available for StreamingResponse context")

    return warnings


async def step_109__stream_response(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """RAG STEP 109 — StreamingResponse Send chunks.

    Thin async orchestrator that creates FastAPI StreamingResponse with SSE-formatted chunks.
    Takes SSE-formatted stream from WriteSSE (Step 108) and creates browser-compatible StreamingResponse.
    Routes to SendDone (Step 110) with complete streaming response ready for delivery.

    Incoming: WriteSSE (Step 108)
    Outgoing: SendDone (Step 110)
    """
    with rag_step_timer(109, 'RAG.streaming.streamingresponse.send.chunks', 'StreamResponse', stage="start"):
        ctx = ctx or {}

        rag_step_log(
            step=109,
            step_id='RAG.streaming.streamingresponse.send.chunks',
            node_label='StreamResponse',
            category='streaming',
            type='process',
            request_id=ctx.get('request_id'),
            processing_stage="started"
        )

        # Create StreamingResponse with SSE-formatted chunks
        streaming_response = _create_streaming_response(ctx)
        response_config = _prepare_response_configuration(ctx)

        # Preserve all context and add response metadata
        result = ctx.copy()

        # Add StreamingResponse results
        result.update({
            'streaming_response': streaming_response,
            'response_config': response_config,
            'response_created': True,
            'processing_stage': 'response_created',
            'next_step': 'send_done',
            'response_timestamp': datetime.now(timezone.utc).isoformat()
        })

        # Add validation warnings if needed
        validation_warnings = _validate_response_requirements(ctx)
        if validation_warnings:
            result['validation_warnings'] = validation_warnings

        rag_step_log(
            step=109,
            step_id='RAG.streaming.streamingresponse.send.chunks',
            node_label='StreamResponse',
            request_id=ctx.get('request_id'),
            response_created=True,
            response_configured=bool(response_config),
            next_step='send_done',
            processing_stage="completed"
        )

        return result
