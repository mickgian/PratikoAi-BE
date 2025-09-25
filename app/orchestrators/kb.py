"""KB orchestrator module for RAG steps related to Knowledge Base operations."""

# AUTO-GENERATED ORCHESTRATOR STUBS (safe to edit below stubs)
# These functions are the functional *nodes* that mirror the Mermaid diagram.
# Implement thin coordination here (call services/factories), not core business logic.

from contextlib import nullcontext
from typing import Any, Dict, List, Optional

try:
    from app.observability.rag_logging import rag_step_log, rag_step_timer
except Exception:  # pragma: no cover
    def rag_step_log(**kwargs):
        """Fallback logging function when observability module unavailable."""
        return None
    def rag_step_timer(*args, **kwargs):
        """Fallback timer function when observability module unavailable."""
        return nullcontext()

async def step_26__kbcontext_check(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """RAG STEP 26 — KnowledgeSearch.context_topk fetch recent KB for changes.

    ID: RAG.kb.knowledgesearch.context.topk.fetch.recent.kb.for.changes
    Type: process | Category: kb | Node: KBContextCheck

    Thin async orchestrator that fetches recent KB changes when high-confidence Golden match occurs.
    Uses KnowledgeSearchService to check for newer KB articles that might override Golden Set.
    Routes to Step 27 (KBDelta) for freshness/conflict evaluation.
    """
    ctx = ctx or {}
    request_id = ctx.get('request_id', 'unknown')

    with rag_step_timer(26, 'RAG.kb.knowledgesearch.context.topk.fetch.recent.kb.for.changes', 'KBContextCheck',
                       request_id=request_id, stage="start"):
        rag_step_log(step=26, step_id='RAG.kb.knowledgesearch.context.topk.fetch.recent.kb.for.changes', node_label='KBContextCheck',
                     category='kb', type='process', request_id=request_id, processing_stage="started")

        # Extract golden match and query for KB search
        golden_match = ctx.get('golden_match', {})
        user_query = ctx.get('user_query', golden_match.get('question', ''))
        golden_updated = golden_match.get('updated_at')

        # Fetch recent KB changes
        try:
            from app.services.knowledge_search_service import KnowledgeSearchService
            # In production, db_session and vector_service would be properly injected
            kb_service = KnowledgeSearchService(
                db_session=None,  # Would be injected via dependency injection
                vector_service=None  # Would be injected via dependency injection
            )

            # Parse golden timestamp for recency comparison
            from datetime import datetime, timezone, timedelta
            if golden_updated:
                if isinstance(golden_updated, str):
                    golden_dt = datetime.fromisoformat(golden_updated.replace('Z', '+00:00'))
                else:
                    golden_dt = golden_updated
            else:
                # Default to 14 days ago if no timestamp
                golden_dt = datetime.now(timezone.utc) - timedelta(days=14)

            # Fetch recent KB articles (last 14 days by default)
            query_data = {
                'query': user_query,
                'since_date': golden_dt - timedelta(days=14),
                'max_results': 10
            }
            recent_kb_results = await kb_service.fetch_recent_kb_for_changes(query_data)

            # Convert results to dicts for context
            kb_context_items = []
            for result in recent_kb_results:
                # Handle both dict and object responses
                if isinstance(result, dict):
                    kb_context_items.append({
                        'id': result.get('id'),
                        'title': result.get('title'),
                        'content': result.get('content'),
                        'updated_at': result.get('updated_at'),
                        'tags': result.get('tags', []),
                        'score': result.get('score', 0.0)
                    })
                else:
                    # Handle object attributes
                    kb_context_items.append({
                        'id': getattr(result, 'id', None),
                        'title': getattr(result, 'title', None),
                        'content': getattr(result, 'content', None),
                        'updated_at': getattr(result, 'updated_at', None),
                        'tags': getattr(result, 'tags', []),
                        'score': getattr(result, 'score', 0.0)
                    })

            has_recent_changes = len(kb_context_items) > 0

            rag_step_log(
                step=26,
                step_id='RAG.kb.knowledgesearch.context.topk.fetch.recent.kb.for.changes',
                node_label='KBContextCheck',
                request_id=request_id,
                query=user_query[:100] if user_query else '',
                has_recent_changes=has_recent_changes,
                recent_changes_count=len(kb_context_items),
                golden_updated=str(golden_updated) if golden_updated else None,
                processing_stage="completed"
            )

        except Exception as e:
            rag_step_log(
                step=26,
                step_id='RAG.kb.knowledgesearch.context.topk.fetch.recent.kb.for.changes',
                node_label='KBContextCheck',
                request_id=request_id,
                error=str(e),
                processing_stage="error"
            )
            # On error, proceed without KB context
            kb_context_items = []
            has_recent_changes = False

        # Build result with KB context
        result = {
            **ctx,
            'kb_context': {
                'recent_changes': kb_context_items,
                'has_recent_changes': has_recent_changes,
                'updated_at': kb_context_items[0].get('updated_at') if kb_context_items else None,
                'tags': list(set(tag for item in kb_context_items for tag in item.get('tags', [])))
            },
            'kb_recent_changes': kb_context_items,  # Legacy field for compatibility
            'has_recent_changes': has_recent_changes,
            'kb_metadata': {
                'search_query': user_query,
                'recent_changes_count': len(kb_context_items),
                'golden_updated': str(golden_updated) if golden_updated else None
            },
            'kb_fetch_metadata': {  # Add for test compatibility
                'search_query': user_query,
                'recent_changes_count': len(kb_context_items),
                'golden_updated': str(golden_updated) if golden_updated else None
            },
            'next_step': 'kb_delta_check',  # Routes to Step 27
            'request_id': request_id
        }

        return result

async def step_80__kbquery_tool(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """RAG STEP 80 — KnowledgeSearchTool.search KB on demand.

    ID: RAG.kb.knowledgesearchtool.search.kb.on.demand
    Type: process | Category: kb | Node: KBQueryTool

    Thin async orchestrator that executes on-demand knowledge base search when the LLM calls
    the KnowledgeSearchTool. Uses KnowledgeSearchService for hybrid BM25 + vector + recency search.
    Routes to Step 99 (ToolResults).
    """
    ctx = ctx or {}
    request_id = ctx.get('request_id', 'unknown')

    with rag_step_timer(80, 'RAG.kb.knowledgesearchtool.search.kb.on.demand', 'KBQueryTool',
                       request_id=request_id, stage="start"):
        rag_step_log(step=80, step_id='RAG.kb.knowledgesearchtool.search.kb.on.demand', node_label='KBQueryTool',
                     category='kb', type='process', request_id=request_id, processing_stage="started")

        # Extract query from tool arguments
        tool_args = ctx.get('tool_args', {})
        query = tool_args.get('query', '')
        tool_call_id = ctx.get('tool_call_id')

        # Prepare search query data
        query_data = {
            'query': query,
            'canonical_facts': ctx.get('canonical_facts', []),
            'user_id': ctx.get('user_id'),
            'session_id': ctx.get('session_id'),
            'trace_id': request_id,
            'db_session': ctx.get('db_session'),
            'vector_service': ctx.get('vector_service'),
            'max_results': ctx.get('max_results', 10)
        }

        # Execute knowledge search using service
        try:
            from app.services.knowledge_search_service import retrieve_knowledge_topk

            kb_results = await retrieve_knowledge_topk(query_data)

            # Convert results to dict format for tool response
            search_results = [
                {
                    'id': r.id,
                    'title': r.title,
                    'content': r.content,
                    'score': r.score,
                    'category': r.category,
                    'source': r.source
                }
                for r in kb_results
            ] if kb_results else []

            result_count = len(search_results)

            rag_step_log(
                step=80,
                step_id='RAG.kb.knowledgesearchtool.search.kb.on.demand',
                node_label='KBQueryTool',
                request_id=request_id,
                query=query,
                result_count=result_count,
                processing_stage="completed"
            )

        except Exception as e:
            rag_step_log(
                step=80,
                step_id='RAG.kb.knowledgesearchtool.search.kb.on.demand',
                node_label='KBQueryTool',
                request_id=request_id,
                error=str(e),
                processing_stage="error"
            )
            search_results = []
            result_count = 0

        # Build result with preserved context
        result = {
            **ctx,
            'kb_results': search_results,
            'search_results': search_results,  # Alias for compatibility
            'query': query,
            'search_query': query,
            'result_count': result_count,
            'search_metadata': {
                'query': query,
                'result_count': result_count,
                'tool_call_id': tool_call_id
            },
            'tool_call_id': tool_call_id,
            'next_step': 'tool_results',  # Routes to Step 99 per Mermaid
            'request_id': request_id
        }

        return result

async def _process_knowledge_feedback(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Helper function to process knowledge feedback submission.

    Handles feedback submission for knowledge base items and prepares routing to expert feedback collector.
    """
    import time
    from uuid import uuid4

    # Extract feedback data from context
    feedback_data = ctx.get('feedback_data', {})
    user_id = ctx.get('user_id')
    session_id = ctx.get('session_id')

    # Start timing
    start_time = time.time()

    # Process feedback submission
    feedback_submitted = False
    feedback_id = None
    error_type = None
    error_message = None

    try:
        # Validate required feedback data
        if not feedback_data:
            error_type = 'missing_feedback_data'
            error_message = 'No feedback data provided'
        elif feedback_data.get('knowledge_item_id', 0) <= 0:
            error_type = 'invalid_knowledge_item'
            error_message = 'Invalid or missing knowledge item ID'
        else:
            # Simulate successful feedback submission
            # In real implementation, this would call the knowledge feedback service
            feedback_id = str(uuid4())
            feedback_submitted = True

    except Exception as e:
        error_type = 'submission_error'
        error_message = str(e)

    # Calculate processing time
    processing_time = (time.time() - start_time) * 1000

    # Detect expert feedback context for priority handling
    expert_feedback_detected = bool(ctx.get('expert_user') and ctx.get('expert_feedback'))
    feedback_priority = 'high' if expert_feedback_detected else 'normal'

    # Build result with routing information
    result = {
        # Knowledge feedback results
        'knowledge_feedback_submitted': feedback_submitted,
        'feedback_id': feedback_id,
        'knowledge_item_id': feedback_data.get('knowledge_item_id'),
        'feedback_rating': feedback_data.get('rating'),
        'feedback_type': feedback_data.get('feedback_type'),
        'submission_status': 'success' if feedback_submitted else 'error',

        # Performance tracking
        'feedback_submission_time_ms': processing_time,

        # Expert feedback detection
        'expert_feedback_detected': expert_feedback_detected,
        'feedback_priority': feedback_priority,

        # Error handling
        'error_type': error_type,
        'error_message': error_message,

        # Routing to Step 119 (ExpertFeedbackCollector) per Mermaid
        'next_step': 'expert_feedback_collector',
    }

    return result


async def step_118__knowledge_feedback(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """RAG STEP 118 — POST /api/v1/knowledge/feedback.

    Process orchestrator that handles knowledge feedback submission and routes to expert feedback collector.
    Routes to Step 119 (ExpertFeedbackCollector) per Mermaid diagram.

    ID: RAG.kb.post.api.v1.knowledge.feedback
    Type: process | Category: kb | Node: KnowledgeFeedback
    """
    if ctx is None:
        ctx = {}

    with rag_step_timer(118, 'RAG.kb.post.api.v1.knowledge.feedback', 'KnowledgeFeedback', stage="start"):
        rag_step_log(
            step=118,
            step_id='RAG.kb.post.api.v1.knowledge.feedback',
            node_label='KnowledgeFeedback',
            category='kb',
            type='process',
            processing_stage="started",
            knowledge_item_id=ctx.get('feedback_data', {}).get('knowledge_item_id'),
            feedback_type=ctx.get('feedback_data', {}).get('feedback_type'),
            user_id=ctx.get('user_id'),
            session_id=ctx.get('session_id')
        )

        try:
            # Process knowledge feedback submission
            feedback_result = await _process_knowledge_feedback(ctx)

            # Preserve all existing context and add feedback results
            result = {**ctx, **feedback_result}

            rag_step_log(
                step=118,
                step_id='RAG.kb.post.api.v1.knowledge.feedback',
                node_label='KnowledgeFeedback',
                processing_stage="completed",
                knowledge_feedback_submitted=result['knowledge_feedback_submitted'],
                feedback_id=result.get('feedback_id'),
                feedback_rating=result.get('feedback_rating'),
                feedback_type=result.get('feedback_type'),
                expert_feedback_detected=result.get('expert_feedback_detected'),
                next_step=result['next_step'],
                submission_status=result['submission_status']
            )

            return result

        except Exception as e:
            # Handle unexpected errors gracefully
            error_result = {
                **ctx,
                'knowledge_feedback_submitted': False,
                'error_type': 'processing_error',
                'error_message': str(e),
                'next_step': 'expert_feedback_collector',
                'submission_status': 'error'
            }

            rag_step_log(
                step=118,
                step_id='RAG.kb.post.api.v1.knowledge.feedback',
                node_label='KnowledgeFeedback',
                processing_stage="error",
                error_type=error_result['error_type'],
                error_message=error_result['error_message'],
                next_step=error_result['next_step']
            )

            return error_result

def step_132__rssmonitor(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """RAG STEP 132 — RSS Monitor.

    ID: RAG.kb.rss.monitor
    Type: process | Category: kb | Node: RSSMonitor

    TODO: Implement orchestration so this node *changes/validates control flow/data*
    according to Mermaid — not logs-only. Call into existing services/factories here.
    """
    with rag_step_timer(132, 'RAG.kb.rss.monitor', 'RSSMonitor', stage="start"):
        rag_step_log(step=132, step_id='RAG.kb.rss.monitor', node_label='RSSMonitor',
                     category='kb', type='process', stub=True, processing_stage="started")
        # TODO: call real service/factory here and return its output
        result = kwargs.get("result")  # placeholder
        rag_step_log(step=132, step_id='RAG.kb.rss.monitor', node_label='RSSMonitor',
                     processing_stage="completed")
        return result
