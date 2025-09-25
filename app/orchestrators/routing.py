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

async def step_79__tool_type(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """RAG STEP 79 — Tool type?

    ID: RAG.routing.tool.type
    Type: decision | Category: routing | Node: ToolType

    Thin async orchestrator that determines tool type based on tool name for routing.
    Makes routing decisions to appropriate tool-specific steps: Knowledge→80, CCNL→81,
    Document→82, FAQ→83. Routes from ExecuteTools (Step 78) per Mermaid diagram.
    """
    ctx = ctx or {}
    request_id = ctx.get('request_id', 'unknown')

    with rag_step_timer(79, 'RAG.routing.tool.type', 'ToolType',
                       request_id=request_id, stage="start"):
        rag_step_log(step=79, step_id='RAG.routing.tool.type', node_label='ToolType',
                     category='routing', type='decision', request_id=request_id, processing_stage="started")

        try:
            # Determine tool type and routing using helper function
            routing_decision = await _determine_tool_type_and_routing(ctx)

            # Build result with preserved context and routing decision
            result = {
                **ctx,
                'tool_type': routing_decision['tool_type'],
                'tool_name': routing_decision['tool_name'],
                'tool_type_detected': routing_decision['detected'],
                'routing_decision': routing_decision['decision'],
                'next_step': routing_decision['next_step'],
                'next_step_id': routing_decision['next_step_id'],
                'route_to': routing_decision['route_to'],
                'previous_step': ctx.get('rag_step'),
                'tool_routing_metadata': routing_decision['metadata'],
                'request_id': request_id
            }

            # Add tool-specific parameters for next step
            if routing_decision['tool_type'] == 'Knowledge':
                result['knowledge_search_params'] = _build_knowledge_search_params(ctx)
            elif routing_decision['tool_type'] == 'CCNL':
                result['ccnl_query_params'] = _build_ccnl_query_params(ctx)
            elif routing_decision['tool_type'] == 'Document':
                result['document_ingest_params'] = _build_document_ingest_params(ctx)
            elif routing_decision['tool_type'] == 'FAQ':
                result['faq_query_params'] = _build_faq_query_params(ctx)

            # Add error context if detection failed
            if not routing_decision['detected']:
                result['error'] = routing_decision.get('error', 'Tool type detection failed')

            rag_step_log(
                step=79,
                step_id='RAG.routing.tool.type',
                node_label='ToolType',
                request_id=request_id,
                tool_type=routing_decision['tool_type'],
                tool_name=routing_decision['tool_name'],
                tool_type_detected=routing_decision['detected'],
                routing_decision=routing_decision['decision'],
                next_step=routing_decision['next_step'],
                route_to=routing_decision['route_to'],
                processing_stage="completed"
            )

            return result

        except Exception as e:
            rag_step_log(
                step=79,
                step_id='RAG.routing.tool.type',
                node_label='ToolType',
                request_id=request_id,
                error=str(e),
                processing_stage="error"
            )
            # On error, default to unknown tool type with error routing
            return await _handle_tool_type_error(ctx, str(e))


async def _determine_tool_type_and_routing(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Determine tool type and routing destination based on tool call context.

    Maps tool names to types and determines appropriate next steps per Mermaid diagram.
    """
    try:
        # Extract tool information from context
        tool_call = ctx.get('current_tool_call')
        if not tool_call:
            # Try to get from tool_calls list if current_tool_call is missing
            tool_calls = ctx.get('tool_calls', [])
            if tool_calls:
                tool_call = tool_calls[0]  # Use first tool call as fallback

        if not tool_call or not isinstance(tool_call, dict):
            return {
                'tool_type': 'Unknown',
                'tool_name': 'none',
                'detected': False,
                'decision': 'missing_context',
                'next_step': 999,  # Error step or default handling
                'next_step_id': 'RAG.error.tool.type.detection.failed',
                'route_to': 'ErrorHandling',
                'metadata': {'error': 'Missing tool call context'},
                'error': 'Missing tool call context'
            }

        tool_name = tool_call.get('name', '')
        if not tool_name:
            return {
                'tool_type': 'Unknown',
                'tool_name': 'empty',
                'detected': False,
                'decision': 'missing_tool_name',
                'next_step': 999,
                'next_step_id': 'RAG.error.tool.name.missing',
                'route_to': 'ErrorHandling',
                'metadata': {'error': 'Missing tool name'},
                'error': 'Missing tool name'
            }

        # Map tool names to types and routing destinations
        tool_type_mappings = {
            # Knowledge tools → Step 80 (KBQueryTool)
            'KnowledgeSearchTool': {
                'type': 'Knowledge',
                'next_step': 80,
                'next_step_id': 'RAG.knowledge.knowledgesearchtool.search.kb.on.demand',
                'route_to': 'KBQueryTool'
            },
            # CCNL tools → Step 81 (CCNLQuery)
            'ccnl_query': {
                'type': 'CCNL',
                'next_step': 81,
                'next_step_id': 'RAG.knowledge.ccnltool.ccnl.query.query.labor.agreements',
                'route_to': 'CCNLQuery'
            },
            # Document tools → Step 82 (DocIngest)
            'DocumentIngestTool': {
                'type': 'Document',
                'next_step': 82,
                'next_step_id': 'RAG.docs.documentingesttool.process.process.attachments',
                'route_to': 'DocIngest'
            },
            # FAQ tools → Step 83 (FAQQuery)
            'FAQTool': {
                'type': 'FAQ',
                'next_step': 83,
                'next_step_id': 'RAG.golden.faqtool.faq.query.query.golden.set',
                'route_to': 'FAQQuery'
            }
        }

        # Determine tool type and routing
        if tool_name in tool_type_mappings:
            mapping = tool_type_mappings[tool_name]
            return {
                'tool_type': mapping['type'],
                'tool_name': tool_name,
                'detected': True,
                'decision': f'route_to_{mapping["type"].lower()}',
                'next_step': mapping['next_step'],
                'next_step_id': mapping['next_step_id'],
                'route_to': mapping['route_to'],
                'metadata': {
                    'tool_args': tool_call.get('args', {}),
                    'tool_id': tool_call.get('id'),
                    'detection_method': 'name_mapping'
                }
            }
        else:
            # Unknown tool type
            return {
                'tool_type': 'Unknown',
                'tool_name': tool_name,
                'detected': False,
                'decision': 'unknown_tool',
                'next_step': 999,  # Default error handling
                'next_step_id': 'RAG.error.unknown.tool.type',
                'route_to': 'ErrorHandling',
                'metadata': {
                    'tool_args': tool_call.get('args', {}),
                    'tool_id': tool_call.get('id'),
                    'unknown_tool_name': tool_name
                }
            }

    except Exception as e:
        return {
            'tool_type': 'Unknown',
            'tool_name': 'error',
            'detected': False,
            'decision': 'detection_error',
            'next_step': 999,
            'next_step_id': 'RAG.error.tool.detection.exception',
            'route_to': 'ErrorHandling',
            'metadata': {'exception': str(e)},
            'error': str(e)
        }


def _build_knowledge_search_params(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Build parameters for Knowledge Search tool routing."""
    tool_call = ctx.get('current_tool_call', {})
    args = tool_call.get('args', {})

    return {
        'query': args.get('query', ''),
        'max_results': args.get('max_results', 5),
        'include_metadata': args.get('include_metadata', True),
        'search_type': 'knowledge_base',
        'tool_call_id': tool_call.get('id')
    }


def _build_ccnl_query_params(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Build parameters for CCNL query tool routing."""
    tool_call = ctx.get('current_tool_call', {})
    args = tool_call.get('args', {})

    return {
        'query': args.get('query', ''),
        'ccnl_type': args.get('ccnl_type', ''),
        'date_context': args.get('date_context'),
        'search_scope': args.get('search_scope', 'full'),
        'tool_call_id': tool_call.get('id')
    }


def _build_document_ingest_params(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Build parameters for Document Ingest tool routing."""
    tool_call = ctx.get('current_tool_call', {})
    args = tool_call.get('args', {})

    return {
        'attachments': args.get('attachments', []),
        'processing_options': args.get('processing_options', {}),
        'extract_text': args.get('extract_text', True),
        'detect_type': args.get('detect_type', True),
        'tool_call_id': tool_call.get('id')
    }


def _build_faq_query_params(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Build parameters for FAQ query tool routing."""
    tool_call = ctx.get('current_tool_call', {})
    args = tool_call.get('args', {})

    return {
        'query': args.get('query', ''),
        'max_results': args.get('max_results', 3),
        'min_confidence': args.get('min_confidence', 'medium'),
        'include_outdated': args.get('include_outdated', False),
        'tool_call_id': tool_call.get('id')
    }


async def _handle_tool_type_error(ctx: Dict[str, Any], error_msg: str) -> Dict[str, Any]:
    """Handle errors in tool type detection with graceful fallback."""
    return {
        **ctx,
        'tool_type': 'Unknown',
        'tool_name': 'error',
        'tool_type_detected': False,
        'routing_decision': 'error_fallback',
        'error': error_msg,
        'next_step': 999,  # Error handling step
        'next_step_id': 'RAG.error.tool.type.detection.failed',
        'route_to': 'ErrorHandling',
        'previous_step': ctx.get('rag_step'),
        'tool_routing_metadata': {
            'error': error_msg,
            'fallback_applied': True,
            'detection_failed': True
        },
        'request_id': ctx.get('request_id', 'unknown')
    }
