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

async def step_20__golden_fast_gate(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """RAG STEP 20 — Golden fast-path eligible? no doc or quick check safe.

    ID: RAG.golden.golden.fast.path.eligible.no.doc.or.quick.check.safe
    Type: process | Category: golden | Node: GoldenFastGate

    Thin async orchestrator that determines if query is eligible for golden fast-path processing.
    Evaluates query complexity, golden eligibility scores, and context to decide routing.
    Routes to Step 24 (GoldenLookup) if eligible, Step 31 (ClassifyDomain) if not.
    Receives input from Step 19 (no attachments) or Step 22 (no doc dependency).
    """
    ctx = ctx or {}
    request_id = ctx.get('request_id', 'unknown')

    with rag_step_timer(20, 'RAG.golden.golden.fast.path.eligible.no.doc.or.quick.check.safe', 'GoldenFastGate',
                       request_id=request_id, stage="start"):
        rag_step_log(step=20, step_id='RAG.golden.golden.fast.path.eligible.no.doc.or.quick.check.safe', node_label='GoldenFastGate',
                     category='golden', type='process', request_id=request_id, processing_stage="started")

        try:
            # Extract eligibility data from context
            eligibility_result = await _check_golden_fast_path_eligibility(ctx)

            # Build result with preserved context and eligibility decision
            result = {
                **ctx,
                'golden_fast_path_eligible': eligibility_result['eligible'],
                'eligibility_reason': eligibility_result['reason'],
                'next_step': eligibility_result['next_step'],
                'next_step_id': eligibility_result['next_step_id'],
                'route_to': eligibility_result['route_to'],
                'previous_step': ctx.get('rag_step'),
                'request_id': request_id
            }

            # Add golden lookup params if eligible
            if eligibility_result['eligible']:
                result['golden_lookup_params'] = {
                    'query_signature': ctx.get('query_signature'),
                    'canonical_facts': ctx.get('canonical_facts', []),
                    'confidence_scores': ctx.get('confidence_scores', {})
                }
            else:
                result['classification_context'] = {
                    'query_complexity': ctx.get('confidence_scores', {}).get('query_complexity', 0.0),
                    'golden_eligible': ctx.get('confidence_scores', {}).get('golden_eligible', 0.0)
                }
                # Also add query_complexity directly for test compatibility
                result['query_complexity'] = ctx.get('confidence_scores', {}).get('query_complexity', 0.0)

            rag_step_log(
                step=20,
                step_id='RAG.golden.golden.fast.path.eligible.no.doc.or.quick.check.safe',
                node_label='GoldenFastGate',
                request_id=request_id,
                golden_fast_path_eligible=eligibility_result['eligible'],
                eligibility_reason=eligibility_result['reason'],
                next_step=eligibility_result['next_step'],
                route_to=eligibility_result['route_to'],
                processing_stage="completed"
            )

            return result

        except Exception as e:
            rag_step_log(
                step=20,
                step_id='RAG.golden.golden.fast.path.eligible.no.doc.or.quick.check.safe',
                node_label='GoldenFastGate',
                request_id=request_id,
                error=str(e),
                processing_stage="error"
            )
            # On error, default to not eligible and route to classification
            return await _handle_golden_fast_gate_error(ctx, str(e))


async def _check_golden_fast_path_eligibility(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Helper function to determine golden fast-path eligibility based on query complexity and context.

    Eligibility criteria:
    1. From Step 22 with no doc dependency -> always eligible
    2. From Step 19 with no attachments -> check confidence scores
    3. Query complexity <= 0.7 (simple to moderately complex)
    4. Golden eligible score >= 0.5 (reasonable golden match potential)
    """
    previous_step = ctx.get('rag_step')

    # Special case: From Step 22 with no document dependency -> always eligible
    if previous_step == 22 and ctx.get('doc_dependent') is False:
        return {
            'eligible': True,
            'reason': 'no_document_dependency',
            'next_step': 24,
            'next_step_id': 'RAG.golden.goldenset.match.by.signature.or.semantic',
            'route_to': 'GoldenLookup'
        }

    # Extract confidence scores for other cases
    confidence_scores = ctx.get('confidence_scores', {})
    query_complexity = confidence_scores.get('query_complexity', 1.0)  # Default to complex
    golden_eligible = confidence_scores.get('golden_eligible', 0.0)    # Default to not eligible

    # Check eligibility thresholds
    COMPLEXITY_THRESHOLD = 0.7
    GOLDEN_ELIGIBLE_THRESHOLD = 0.5

    # Determine eligibility based on thresholds
    complexity_ok = query_complexity <= COMPLEXITY_THRESHOLD
    golden_score_ok = golden_eligible >= GOLDEN_ELIGIBLE_THRESHOLD

    # Check context-specific eligibility reasons
    if not confidence_scores:  # Missing eligibility data
        return {
            'eligible': False,
            'reason': 'missing_eligibility_data',
            'next_step': 31,
            'next_step_id': 'RAG.classify.domainactionclassifier.classify.rule.based.classification',
            'route_to': 'ClassifyDomain'
        }

    if not complexity_ok:  # Query too complex
        return {
            'eligible': False,
            'reason': 'query_too_complex',
            'next_step': 31,
            'next_step_id': 'RAG.classify.domainactionclassifier.classify.rule.based.classification',
            'route_to': 'ClassifyDomain'
        }

    if not golden_score_ok:  # Low golden eligibility
        return {
            'eligible': False,
            'reason': 'low_golden_eligibility',
            'next_step': 31,
            'next_step_id': 'RAG.classify.domainactionclassifier.classify.rule.based.classification',
            'route_to': 'ClassifyDomain'
        }

    # Determine specific eligibility reason based on path
    if previous_step == 19:
        # From Step 19: no attachments present
        eligibility_reason = 'simple_query_no_attachments'
    else:
        # Generic case
        eligibility_reason = 'threshold_criteria_met'

    # Eligible for golden fast-path
    return {
        'eligible': True,
        'reason': eligibility_reason,
        'next_step': 24,
        'next_step_id': 'RAG.golden.goldenset.match.by.signature.or.semantic',
        'route_to': 'GoldenLookup'
    }


async def _handle_golden_fast_gate_error(ctx: Dict[str, Any], error_msg: str) -> Dict[str, Any]:
    """Helper function to handle errors in golden fast gate processing.

    Defaults to not eligible and routes to classification for safe fallback.
    """
    return {
        **ctx,
        'golden_fast_path_eligible': False,
        'eligibility_reason': f'error_occurred: {error_msg}',
        'next_step': 31,
        'next_step_id': 'RAG.classify.domainactionclassifier.classify.rule.based.classification',
        'route_to': 'ClassifyDomain',
        'error': error_msg,
        'previous_step': ctx.get('rag_step'),
        'request_id': ctx.get('request_id', 'unknown')
    }

async def step_23__require_doc_ingest(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 23 — PlannerHint.require_doc_ingest_first ingest then Golden and KB
    ID: RAG.golden.plannerhint.require.doc.ingest.first.ingest.then.golden.and.kb
    Type: process | Category: golden | Node: RequireDocIngest

    This step sets planning hints when documents need to be ingested before proceeding
    with Golden Set and KB queries. It coordinates the document-first workflow by setting
    flags that defer Golden Set lookup and KB search until document processing completes.
    Routes to Step 31 (ClassifyDomain) to continue the workflow.
    """
    ctx = ctx or {}
    request_id = ctx.get('request_id', 'unknown')

    with rag_step_timer(23, 'RAG.golden.plannerhint.require.doc.ingest.first.ingest.then.golden.and.kb', 'RequireDocIngest',
                       request_id=request_id, stage="start"):
        rag_step_log(
            step=23,
            step_id='RAG.golden.plannerhint.require.doc.ingest.first.ingest.then.golden.and.kb',
            node_label='RequireDocIngest',
            category='golden',
            type='process',
            request_id=request_id,
            processing_stage="started"
        )

        # Extract context
        user_query = ctx.get('user_query', '')
        extracted_docs = ctx.get('extracted_docs', [])
        document_count = ctx.get('document_count', len(extracted_docs))

        # Set planning hints for document-first workflow
        # These flags tell downstream steps to defer Golden Set and KB queries
        # until documents are fully processed
        requires_doc_ingest_first = True
        defer_golden_lookup = True
        defer_kb_search = True
        planning_hint = 'doc_ingest_before_golden_kb'

        # Build processing metadata for coordination
        processing_metadata = {
            'requires_doc_ingest': True,
            'workflow': 'doc_first_then_golden_kb',
            'document_count': document_count,
            'planning_stage': 'pre_classification'
        }

        rag_step_log(
            step=23,
            step_id='RAG.golden.plannerhint.require.doc.ingest.first.ingest.then.golden.and.kb',
            node_label='RequireDocIngest',
            request_id=request_id,
            planning_hint=planning_hint,
            document_count=document_count,
            requires_doc_ingest_first=requires_doc_ingest_first,
            processing_stage="completed"
        )

        # Build result with planning hints and preserved context
        result = {
            **ctx,
            'requires_doc_ingest_first': requires_doc_ingest_first,
            'defer_golden_lookup': defer_golden_lookup,
            'defer_kb_search': defer_kb_search,
            'planning_hint': planning_hint,
            'processing_metadata': processing_metadata,
            'next_step': 'classify_domain',  # Routes to Step 31 per Mermaid
            'request_id': request_id
        }

        return result

async def step_25__golden_hit(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 25 — High confidence match? score at least 0.90
    ID: RAG.golden.high.confidence.match.score.at.least.0.90
    Type: process | Category: golden | Node: GoldenHit

    Thin async orchestrator that checks if Golden Set match has high confidence (≥0.90).
    Evaluates the golden_match from context and determines if confidence threshold is met.
    Routes to Step 26 (KBContextCheck) if high confidence, Step 23 if not.
    """
    ctx = ctx or {}
    request_id = ctx.get('request_id', 'unknown')

    with rag_step_timer(25, 'RAG.golden.high.confidence.match.score.at.least.0.90', 'GoldenHit',
                       request_id=request_id, stage="start"):
        rag_step_log(step=25, step_id='RAG.golden.high.confidence.match.score.at.least.0.90', node_label='GoldenHit',
                     category='golden', type='process', request_id=request_id, processing_stage="started")

        # Extract golden match from context
        golden_match = ctx.get('golden_match', {})
        # Support both 'confidence' and 'similarity_score' fields
        confidence = golden_match.get('confidence') or golden_match.get('similarity_score', 0.0)
        faq_id = golden_match.get('faq_id', 'unknown')

        # Check if confidence meets threshold
        HIGH_CONFIDENCE_THRESHOLD = 0.90
        is_high_confidence = confidence >= HIGH_CONFIDENCE_THRESHOLD

        rag_step_log(
            step=25,
            step_id='RAG.golden.high.confidence.match.score.at.least.0.90',
            node_label='GoldenHit',
            request_id=request_id,
            confidence=confidence,
            threshold=HIGH_CONFIDENCE_THRESHOLD,
            is_high_confidence=is_high_confidence,
            faq_id=faq_id,
            processing_stage="completed"
        )

        # Build result with preserved context
        result = {
            **ctx,
            'is_high_confidence': is_high_confidence,
            'high_confidence_match': is_high_confidence,  # Add for test compatibility
            'confidence': confidence,
            'threshold': HIGH_CONFIDENCE_THRESHOLD,
            'decision_metadata': {
                'step': 'golden_hit',
                'confidence': confidence,
                'threshold': HIGH_CONFIDENCE_THRESHOLD,
                'is_high_confidence': is_high_confidence,
                'faq_id': faq_id
            },
            'next_step': 'kb_context_check' if is_high_confidence else 'require_doc_ingest',
            'request_id': request_id
        }

        return result

async def step_27__kbdelta(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 27 — KB newer than Golden as of or conflicting tags?
    ID: RAG.golden.kb.newer.than.golden.as.of.or.conflicting.tags
    Type: process | Category: golden | Node: KBDelta

    Thin async orchestrator that checks if KB is newer than Golden Set or has conflicting tags.
    Compares kb_context timestamps and tags with golden_match metadata to determine precedence.
    Routes to Step 36 (LLMBetter) if KB is newer/conflicts, Step 28 (ServeGolden) otherwise.
    """
    ctx = ctx or {}
    request_id = ctx.get('request_id', 'unknown')

    with rag_step_timer(27, 'RAG.golden.kb.newer.than.golden.as.of.or.conflicting.tags', 'KBDelta',
                       request_id=request_id, stage="start"):
        rag_step_log(step=27, step_id='RAG.golden.kb.newer.than.golden.as.of.or.conflicting.tags', node_label='KBDelta',
                     category='golden', type='process', request_id=request_id, processing_stage="started")

        # Extract golden match and KB context
        golden_match = ctx.get('golden_match', {})
        kb_context = ctx.get('kb_context', {})

        # Get timestamps
        golden_updated = golden_match.get('updated_at')
        kb_updated = kb_context.get('updated_at')

        # Check if KB is newer
        kb_is_newer = False
        if kb_updated and golden_updated:
            try:
                from datetime import datetime
                if isinstance(kb_updated, str):
                    kb_dt = datetime.fromisoformat(kb_updated.replace('Z', '+00:00'))
                else:
                    kb_dt = kb_updated

                if isinstance(golden_updated, str):
                    golden_dt = datetime.fromisoformat(golden_updated.replace('Z', '+00:00'))
                else:
                    golden_dt = golden_updated

                kb_is_newer = kb_dt > golden_dt
            except Exception as e:
                rag_step_log(
                    step=27,
                    step_id='RAG.golden.kb.newer.than.golden.as.of.or.conflicting.tags',
                    node_label='KBDelta',
                    request_id=request_id,
                    error=f"Error comparing timestamps: {str(e)}",
                    processing_stage="warning"
                )

        # Check for conflicting tags
        golden_tags = set(golden_match.get('tags', []))
        kb_tags = set(kb_context.get('tags', []))
        has_conflicting_tags = bool(golden_tags & kb_tags)  # Intersection indicates conflict

        # Determine if KB should take precedence
        kb_takes_precedence = kb_is_newer or has_conflicting_tags

        rag_step_log(
            step=27,
            step_id='RAG.golden.kb.newer.than.golden.as.of.or.conflicting.tags',
            node_label='KBDelta',
            request_id=request_id,
            kb_is_newer=kb_is_newer,
            has_conflicting_tags=has_conflicting_tags,
            kb_takes_precedence=kb_takes_precedence,
            golden_updated=str(golden_updated) if golden_updated else None,
            kb_updated=str(kb_updated) if kb_updated else None,
            processing_stage="completed"
        )

        # Build result with preserved context
        result = {
            **ctx,
            'kb_is_newer': kb_is_newer,
            'has_conflicting_tags': has_conflicting_tags,
            'kb_takes_precedence': kb_takes_precedence,
            'kb_has_delta': kb_takes_precedence,  # Add for test compatibility
            'delta_metadata': {
                'kb_updated': str(kb_updated) if kb_updated else None,
                'golden_updated': str(golden_updated) if golden_updated else None,
                'kb_is_newer': kb_is_newer,
                'has_conflicting_tags': has_conflicting_tags,
                'conflicting_tags': list(golden_tags & kb_tags) if has_conflicting_tags else []
            },
            'next_step': 'llm_better' if kb_takes_precedence else 'serve_golden',
            'request_id': request_id
        }

        return result

async def step_28__serve_golden(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 28 — Serve Golden answer with citations
    ID: RAG.golden.serve.golden.answer.with.citations
    Type: process | Category: golden | Node: ServeGolden

    Thin async orchestrator that formats Golden Set match into response with proper citations.
    Creates ChatResponse with Golden answer, citations, and metadata for high-confidence FAQ matches.
    Routes to ReturnComplete to bypass LLM processing.
    """
    ctx = ctx or {}
    request_id = ctx.get('request_id', 'unknown')

    with rag_step_timer(28, 'RAG.golden.serve.golden.answer.with.citations', 'ServeGolden',
                       request_id=request_id, stage="start"):
        rag_step_log(step=28, step_id='RAG.golden.serve.golden.answer.with.citations', node_label='ServeGolden',
                     category='golden', type='process', request_id=request_id, processing_stage="started")

        # Extract golden match from context
        golden_match = ctx.get('golden_match', {})
        faq_id = golden_match.get('faq_id', 'unknown')
        answer = golden_match.get('answer', '')
        question = golden_match.get('question', '')
        confidence = golden_match.get('confidence', 0.0)
        metadata = golden_match.get('metadata', {})
        updated_at = golden_match.get('updated_at')

        # Format citations
        citations = [{
            'source': 'Golden Set FAQ',
            'faq_id': faq_id,
            'question': question,
            'confidence': confidence,
            'updated_at': updated_at,
            'regulatory_refs': metadata.get('regulatory_refs', []),
            'tags': metadata.get('tags', []),
            'category': metadata.get('category')
        }]

        # Build response metadata
        response_metadata = {
            'source': 'golden_set',
            'source_type': 'golden_set',  # Add source_type for test compatibility
            'bypassed_llm': True,
            'confidence': 'high' if confidence >= 0.90 else 'medium',  # Match test expectation
            'category': golden_match.get('category'),  # Add category from golden_match
            'faq_id': faq_id,
            'served_at': ctx.get('timestamp', 'unknown')
        }

        # Create serving metadata
        serving_metadata = {
            'bypassed_llm': True,
            'source': 'golden_set',  # Add source field for test
            'served_from': 'golden_set',
            'confidence': confidence,
            'latency_ms': ctx.get('latency_ms', 0),
            'served_at': ctx.get('timestamp', 'unknown')  # Add served_at for timing metadata
        }

        rag_step_log(
            step=28,
            step_id='RAG.golden.serve.golden.answer.with.citations',
            node_label='ServeGolden',
            request_id=request_id,
            faq_id=faq_id,
            confidence=confidence,
            answer_length=len(answer),
            citations_count=len(citations),
            processing_stage="completed"
        )

        # Build result with formatted response
        result = {
            **ctx,
            'response': {
                'answer': answer,
                'citations': citations
            },
            'response_metadata': response_metadata,
            'serving_metadata': serving_metadata,
            'bypassed_llm': True,
            'next_step': 'return_complete',
            'request_id': request_id
        }

        return result

async def step_60__resolve_epochs(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 60 — EpochStamps.resolve kb_epoch golden_epoch ccnl_epoch parser_version
    ID: RAG.golden.epochstamps.resolve.kb.epoch.golden.epoch.ccnl.epoch.parser.version
    Type: process | Category: golden | Node: ResolveEpochs

    Thin async orchestrator that resolves version epochs from various data sources.
    Extracts kb_epoch, golden_epoch, ccnl_epoch, and parser_version for cache invalidation.
    Routes to Step 61 (GenHash) with resolved epochs for cache key generation.
    """
    ctx = ctx or {}
    request_id = ctx.get('request_id', 'unknown')

    with rag_step_timer(60, 'RAG.golden.epochstamps.resolve.kb.epoch.golden.epoch.ccnl.epoch.parser.version', 'ResolveEpochs',
                       request_id=request_id, stage="start"):
        rag_step_log(step=60, step_id='RAG.golden.epochstamps.resolve.kb.epoch.golden.epoch.ccnl.epoch.parser.version', node_label='ResolveEpochs',
                     category='golden', type='process', request_id=request_id, processing_stage="started")

        # Extract epoch timestamps from context
        kb_epoch = ctx.get('kb_last_updated') or ctx.get('kb_epoch')
        golden_epoch = ctx.get('golden_last_updated') or ctx.get('golden_epoch')
        ccnl_epoch = ctx.get('ccnl_last_updated') or ctx.get('ccnl_epoch')
        parser_version = ctx.get('parser_version')

        # Convert timestamps to epoch format if needed
        def to_epoch_str(timestamp):
            if timestamp is None:
                return None
            if isinstance(timestamp, (int, float)):
                return str(int(timestamp))
            if isinstance(timestamp, str):
                return timestamp
            try:
                # Try to convert datetime to epoch
                from datetime import datetime
                if hasattr(timestamp, 'timestamp'):
                    return str(int(timestamp.timestamp()))
            except Exception:
                pass
            return str(timestamp)

        kb_epoch = to_epoch_str(kb_epoch)
        golden_epoch = to_epoch_str(golden_epoch)
        ccnl_epoch = to_epoch_str(ccnl_epoch)
        parser_version = str(parser_version) if parser_version else None

        # Track which epochs were resolved
        epochs_resolved = []
        if kb_epoch:
            epochs_resolved.append('kb')
        if golden_epoch:
            epochs_resolved.append('golden')
        if ccnl_epoch:
            epochs_resolved.append('ccnl')
        if parser_version:
            epochs_resolved.append('parser')

        rag_step_log(
            step=60,
            step_id='RAG.golden.epochstamps.resolve.kb.epoch.golden.epoch.ccnl.epoch.parser.version',
            node_label='ResolveEpochs',
            request_id=request_id,
            kb_epoch=kb_epoch,
            golden_epoch=golden_epoch,
            ccnl_epoch=ccnl_epoch,
            parser_version=parser_version,
            epochs_resolved=epochs_resolved,
            processing_stage="completed"
        )

        # Build result with resolved epochs
        result = {
            **ctx,
            'kb_epoch': kb_epoch,
            'golden_epoch': golden_epoch,
            'ccnl_epoch': ccnl_epoch,
            'parser_version': parser_version,
            'epoch_resolution_metadata': {
                'epochs_resolved': epochs_resolved,
                'epochs_count': len(epochs_resolved),  # Add count for test
                'kb_epoch': kb_epoch,
                'golden_epoch': golden_epoch,
                'ccnl_epoch': ccnl_epoch,
                'parser_version': parser_version,
                'resolved_at': ctx.get('timestamp', 'unknown')  # Add for test expectation
            },
            'next_step': 'gen_hash',
            'request_id': request_id
        }

        return result

async def step_83__faqquery(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 83 — FAQTool.faq_query Query Golden Set
    ID: RAG.golden.faqtool.faq.query.query.golden.set
    Type: process | Category: golden | Node: FAQQuery

    Thin async orchestrator that executes on-demand FAQ queries when the LLM calls the FAQTool.
    Uses SemanticFAQMatcher and IntelligentFAQService for semantic FAQ matching with confidence
    scoring. Routes to Step 99 (ToolResults).
    """
    ctx = ctx or {}
    request_id = ctx.get('request_id', 'unknown')

    with rag_step_timer(83, 'RAG.golden.faqtool.faq.query.query.golden.set', 'FAQQuery',
                       request_id=request_id, stage="start"):
        rag_step_log(step=83, step_id='RAG.golden.faqtool.faq.query.query.golden.set', node_label='FAQQuery',
                     category='golden', type='process', request_id=request_id, processing_stage="started")

        # Extract tool arguments
        tool_args = ctx.get('tool_args', {})
        tool_call_id = ctx.get('tool_call_id')
        query = tool_args.get('query', '')
        max_results = tool_args.get('max_results', 3)
        min_confidence = tool_args.get('min_confidence', 'medium')

        # Execute FAQ query using FAQTool
        try:
            from app.core.langgraph.tools.faq_tool import faq_tool

            # Call the FAQTool with the arguments
            faq_response = await faq_tool._arun(
                query=query,
                max_results=max_results,
                min_confidence=min_confidence,
                include_outdated=tool_args.get('include_outdated', False)
            )

            # Parse the JSON response
            import json
            try:
                faq_result = json.loads(faq_response) if isinstance(faq_response, str) else faq_response
            except (json.JSONDecodeError, TypeError):
                faq_result = {'success': False, 'error': 'Failed to parse FAQ response', 'raw_response': str(faq_response)}

            success = faq_result.get('success', False)
            match_count = faq_result.get('match_count', 0)

            rag_step_log(
                step=83,
                step_id='RAG.golden.faqtool.faq.query.query.golden.set',
                node_label='FAQQuery',
                request_id=request_id,
                query=query[:100] if query else '',
                match_count=match_count,
                min_confidence=min_confidence,
                success=success,
                processing_stage="completed"
            )

        except Exception as e:
            rag_step_log(
                step=83,
                step_id='RAG.golden.faqtool.faq.query.query.golden.set',
                node_label='FAQQuery',
                request_id=request_id,
                error=str(e),
                processing_stage="error"
            )
            faq_result = {
                'success': False,
                'error': str(e),
                'matches': [],
                'match_count': 0,
                'message': 'Si è verificato un errore durante la query FAQ.'
            }

        # Build result with preserved context
        result = {
            **ctx,
            'faq_results': faq_result,
            'query_result': faq_result,  # Alias for compatibility
            'matches': faq_result.get('matches', []),
            'match_count': faq_result.get('match_count', 0),
            'query_metadata': {
                'query': query,
                'max_results': max_results,
                'min_confidence': min_confidence,
                'include_outdated': tool_args.get('include_outdated', False),
                'tool_call_id': tool_call_id
            },
            'tool_call_id': tool_call_id,
            'next_step': 'tool_results',  # Routes to Step 99 per Mermaid (FAQQuery → ToolResults)
            'request_id': request_id
        }

        return result

async def step_117__faqfeedback(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """RAG STEP 117 — POST /api/v1/faq/feedback.

    ID: RAG.golden.post.api.v1.faq.feedback
    Type: process | Category: golden | Node: FAQFeedback

    Thin async orchestrator that processes FAQ feedback submissions.
    Uses IntelligentFAQService to collect feedback on FAQ responses.
    Routes to ExpertFeedbackCollector (Step 119) for further processing.
    """
    ctx = ctx or {}
    request_id = ctx.get('request_id', 'unknown')

    with rag_step_timer(117, 'RAG.golden.post.api.v1.faq.feedback', 'FAQFeedback',
                       request_id=request_id, stage="start"):
        rag_step_log(step=117, step_id='RAG.golden.post.api.v1.faq.feedback', node_label='FAQFeedback',
                     category='golden', type='process', request_id=request_id, processing_stage="started")

        # Extract feedback data from context
        feedback_data = ctx.get('feedback_data', {})
        usage_log_id = feedback_data.get('usage_log_id')
        was_helpful = feedback_data.get('was_helpful')
        followup_needed = feedback_data.get('followup_needed', False)
        comments = feedback_data.get('comments')

        # Process feedback using IntelligentFAQService
        feedback_result = {}
        try:
            from app.services.intelligent_faq_service import IntelligentFAQService
            from datetime import datetime, timezone

            # In production, db_session would be properly injected
            faq_service = IntelligentFAQService(db_session=None)

            success = await faq_service.collect_feedback(
                usage_log_id=usage_log_id,
                was_helpful=was_helpful,
                followup_needed=followup_needed,
                comments=comments
            )

            feedback_result = {
                'success': success,
                'usage_log_id': usage_log_id,
                'submitted_at': datetime.now(timezone.utc).isoformat()
            }

            if not success:
                feedback_result['error'] = 'Usage log not found or feedback could not be recorded'

            rag_step_log(
                step=117,
                step_id='RAG.golden.post.api.v1.faq.feedback',
                node_label='FAQFeedback',
                request_id=request_id,
                usage_log_id=usage_log_id,
                was_helpful=was_helpful,
                followup_needed=followup_needed,
                success=success,
                processing_stage="completed"
            )

        except Exception as e:
            rag_step_log(
                step=117,
                step_id='RAG.golden.post.api.v1.faq.feedback',
                node_label='FAQFeedback',
                request_id=request_id,
                error=str(e),
                processing_stage="error"
            )
            feedback_result = {
                'success': False,
                'error': str(e),
                'usage_log_id': usage_log_id
            }

        # Build result with preserved context
        result = {
            **ctx,
            'feedback_result': feedback_result,
            'feedback_type': 'faq',  # Identify as FAQ feedback for routing
            'followup_needed': followup_needed,  # Expose for expert collector
            'feedback_metadata': {
                'feedback_type': 'faq',
                'was_helpful': was_helpful,
                'followup_needed': followup_needed,
                'submitted_at': feedback_result.get('submitted_at')
            },
            'next_step': 'expert_feedback_collector',  # Routes to Step 119 per Mermaid
            'request_id': request_id
        }

        return result

async def step_127__golden_candidate(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 127 — GoldenSetUpdater.propose_candidate from expert feedback
    ID: RAG.golden.goldensetupdater.propose.candidate.from.expert.feedback
    Type: process | Category: golden | Node: GoldenCandidate

    Thin async orchestrator that proposes a new FAQ candidate for the Golden Set
    based on expert feedback. Creates a FAQCandidate from expert's improved answer
    and routes to GoldenApproval (Step 128) for approval decision.
    """
    ctx = ctx or {}
    request_id = ctx.get('request_id', 'unknown')

    with rag_step_timer(127, 'RAG.golden.goldensetupdater.propose.candidate.from.expert.feedback', 'GoldenCandidate',
                       request_id=request_id, stage="start"):
        rag_step_log(step=127, step_id='RAG.golden.goldensetupdater.propose.candidate.from.expert.feedback',
                     node_label='GoldenCandidate',
                     category='golden', type='process', request_id=request_id, processing_stage="started")

        # Extract expert feedback data
        expert_feedback = ctx.get('expert_feedback', {})
        query_text = expert_feedback.get('query_text', '')
        expert_answer = expert_feedback.get('expert_answer', '')
        category = expert_feedback.get('category', 'generale')
        regulatory_refs = expert_feedback.get('regulatory_references', [])
        confidence_score = expert_feedback.get('confidence_score', 0.0)
        frequency = expert_feedback.get('frequency', 1)

        expert_id = ctx.get('expert_id')
        trust_score = ctx.get('trust_score', 0.0)

        # Create FAQ candidate from expert feedback
        try:
            from datetime import datetime, timezone
            from decimal import Decimal

            # Calculate priority score based on confidence, trust, and frequency
            # Priority = (confidence × trust × frequency) × 100
            priority_score = Decimal(str(confidence_score * trust_score * frequency * 100))

            # Quality score derived from expert confidence and trust
            quality_score = (confidence_score + trust_score) / 2.0

            # Build FAQ candidate data structure
            faq_candidate = {
                'question': query_text,
                'answer': expert_answer,
                'category': category,
                'regulatory_references': regulatory_refs,
                'priority_score': float(priority_score),
                'quality_score': quality_score,
                'source': 'expert_feedback',
                'expert_id': expert_id,
                'confidence_score': confidence_score,
                'frequency': frequency
            }

            # Add candidate metadata for tracking
            candidate_metadata = {
                'proposed_at': datetime.now(timezone.utc).isoformat(),
                'source': 'expert_feedback',
                'expert_id': expert_id,
                'candidate_id': f"candidate_{expert_feedback.get('id', 'unknown')}",
                'trust_score': trust_score,
                'expert_confidence': confidence_score
            }

            rag_step_log(
                step=127,
                step_id='RAG.golden.goldensetupdater.propose.candidate.from.expert.feedback',
                node_label='GoldenCandidate',
                request_id=request_id,
                candidate_id=candidate_metadata['candidate_id'],
                priority_score=float(priority_score),
                quality_score=quality_score,
                expert_confidence=confidence_score,
                category=category,
                processing_stage="completed"
            )

        except Exception as e:
            rag_step_log(
                step=127,
                step_id='RAG.golden.goldensetupdater.propose.candidate.from.expert.feedback',
                node_label='GoldenCandidate',
                request_id=request_id,
                error=str(e),
                processing_stage="error"
            )
            # On error, still route to next step with error context
            faq_candidate = {'error': str(e)}
            candidate_metadata = {'error': str(e)}

        # Build result with preserved context
        result = {
            **ctx,
            'faq_candidate': faq_candidate,
            'candidate_metadata': candidate_metadata,
            'next_step': 'golden_approval',  # Routes to Step 128 per Mermaid
            'request_id': request_id
        }

        return result

async def step_128__golden_approval(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 128 — Auto threshold met or manual approval?
    ID: RAG.golden.auto.threshold.met.or.manual.approval
    Type: decision | Category: golden | Node: GoldenApproval

    Thin async orchestrator that decides if FAQ candidate meets auto-approval threshold
    or needs manual review. Routes to PublishGolden (Step 129) if approved, or
    FeedbackEnd (Step 115) if rejected/needs review.
    """
    ctx = ctx or {}
    request_id = ctx.get('request_id', 'unknown')

    with rag_step_timer(128, 'RAG.golden.auto.threshold.met.or.manual.approval', 'GoldenApproval',
                       request_id=request_id, stage="start"):
        rag_step_log(step=128, step_id='RAG.golden.auto.threshold.met.or.manual.approval',
                     node_label='GoldenApproval',
                     category='golden', type='decision', request_id=request_id, processing_stage="started")

        # Extract candidate data
        faq_candidate = ctx.get('faq_candidate', {})
        candidate_metadata = ctx.get('candidate_metadata', {})

        # Get quality score and trust score
        quality_score = faq_candidate.get('quality_score', 0.0)
        trust_score = ctx.get('trust_score', 0.0)

        # Decision logic based on thresholds
        try:
            from datetime import datetime, timezone

            # Import thresholds from config
            from app.models.faq_automation import FAQ_AUTOMATION_CONFIG
            auto_approve_threshold = FAQ_AUTOMATION_CONFIG['generation']['auto_approve_threshold']  # 0.95
            quality_threshold = FAQ_AUTOMATION_CONFIG['generation']['quality_threshold']  # 0.85

            # Validate quality score exists
            if not quality_score or not isinstance(quality_score, (int, float)):
                approval_decision = 'rejected'
                rejection_reason = 'missing_quality_score'
                next_step = 'feedback_end'

            # Auto-approve if quality score meets threshold
            elif quality_score >= auto_approve_threshold:
                approval_decision = 'auto_approved'
                approval_reason = 'quality_threshold_met'
                next_step = 'publish_golden'
                rejection_reason = None

            # Reject if quality is too low
            elif quality_score < quality_threshold:
                approval_decision = 'rejected'
                rejection_reason = 'quality_below_threshold'
                next_step = 'feedback_end'
                approval_reason = None

            # Borderline cases require manual review (for now, treat as rejected)
            else:
                approval_decision = 'manual_review_required'
                rejection_reason = 'quality_requires_manual_review'
                next_step = 'feedback_end'  # For now, route to feedback_end
                approval_reason = None

            # Add approval metadata
            approval_metadata = {
                'decided_at': datetime.now(timezone.utc).isoformat(),
                'decision': approval_decision,
                'quality_score': quality_score,
                'trust_score': trust_score,
                'threshold_used': auto_approve_threshold,
                'candidate_id': candidate_metadata.get('candidate_id')
            }

            rag_step_log(
                step=128,
                step_id='RAG.golden.auto.threshold.met.or.manual.approval',
                node_label='GoldenApproval',
                request_id=request_id,
                approval_decision=approval_decision,
                quality_score=quality_score,
                trust_score=trust_score,
                threshold=auto_approve_threshold,
                next_step=next_step,
                processing_stage="completed"
            )

        except Exception as e:
            rag_step_log(
                step=128,
                step_id='RAG.golden.auto.threshold.met.or.manual.approval',
                node_label='GoldenApproval',
                request_id=request_id,
                error=str(e),
                processing_stage="error"
            )
            # On error, reject for safety
            approval_decision = 'rejected'
            rejection_reason = f'error: {str(e)}'
            next_step = 'feedback_end'
            approval_metadata = {'error': str(e)}
            approval_reason = None

        # Build result with preserved context
        result = {
            **ctx,
            'approval_decision': approval_decision,
            'approval_metadata': approval_metadata,
            'next_step': next_step,
            'request_id': request_id
        }

        # Add reason based on decision
        if approval_decision == 'auto_approved' and approval_reason:
            result['approval_reason'] = approval_reason
        if rejection_reason:
            result['rejection_reason'] = rejection_reason

        return result

async def step_129__publish_golden(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 129 — GoldenSet.publish_or_update versioned entry
    ID: RAG.golden.goldenset.publish.or.update.versioned.entry
    Type: process | Category: golden | Node: PublishGolden

    Thin async orchestrator that publishes or updates an approved FAQ entry in the
    Golden Set database with versioning. Routes to InvalidateFAQCache (Step 130)
    and VectorReindex (Step 131) for downstream updates.
    """
    ctx = ctx or {}
    request_id = ctx.get('request_id', 'unknown')

    with rag_step_timer(129, 'RAG.golden.goldenset.publish.or.update.versioned.entry', 'PublishGolden',
                       request_id=request_id, stage="start"):
        rag_step_log(step=129, step_id='RAG.golden.goldenset.publish.or.update.versioned.entry',
                     node_label='PublishGolden',
                     category='golden', type='process', request_id=request_id, processing_stage="started")

        # Extract FAQ candidate data
        faq_candidate = ctx.get('faq_candidate', {})
        candidate_metadata = ctx.get('candidate_metadata', {})

        question = faq_candidate.get('question', '')
        answer = faq_candidate.get('answer', '')
        category = faq_candidate.get('category', 'generale')
        tags = faq_candidate.get('tags', [])
        regulatory_refs = faq_candidate.get('regulatory_references', [])
        existing_faq_id = faq_candidate.get('existing_faq_id')

        # Publish or update FAQ entry
        try:
            from datetime import datetime, timezone
            from app.services.intelligent_faq_service import create_faq_entry, update_faq_entry
            from app.models.faq import UpdateSensitivity

            db_session = ctx.get('db_session')  # Would be injected via dependency injection

            # Determine if this is a new entry or an update
            if existing_faq_id:
                # Update existing FAQ with versioning
                faq_entry = await update_faq_entry(
                    db=db_session,
                    faq_id=existing_faq_id,
                    question=question,
                    answer=answer,
                    tags=tags,
                    change_reason=f"Expert feedback improvement (candidate: {candidate_metadata.get('candidate_id')})"
                )
                operation = 'updated'
            else:
                # Create new FAQ entry
                faq_entry = await create_faq_entry(
                    db=db_session,
                    question=question,
                    answer=answer,
                    category=category,
                    tags=tags,
                    update_sensitivity=UpdateSensitivity.MEDIUM
                )
                operation = 'created'

            # Build published FAQ data
            published_faq = {
                'id': faq_entry.id if hasattr(faq_entry, 'id') else 'faq_published',
                'question': faq_entry.question if hasattr(faq_entry, 'question') else question,
                'answer': faq_entry.answer if hasattr(faq_entry, 'answer') else answer,
                'category': faq_entry.category if hasattr(faq_entry, 'category') else category,
                'version': faq_entry.version if hasattr(faq_entry, 'version') else 1,
                'tags': faq_entry.tags if hasattr(faq_entry, 'tags') else tags,
                'regulatory_refs': regulatory_refs
            }

            # Add publication metadata
            publication_metadata = {
                'published_at': datetime.now(timezone.utc).isoformat(),
                'faq_id': published_faq['id'],
                'operation': operation,
                'candidate_id': candidate_metadata.get('candidate_id'),
                'version': published_faq['version']
            }

            rag_step_log(
                step=129,
                step_id='RAG.golden.goldenset.publish.or.update.versioned.entry',
                node_label='PublishGolden',
                request_id=request_id,
                faq_id=published_faq['id'],
                operation=operation,
                version=published_faq['version'],
                category=category,
                processing_stage="completed"
            )

        except Exception as e:
            rag_step_log(
                step=129,
                step_id='RAG.golden.goldenset.publish.or.update.versioned.entry',
                node_label='PublishGolden',
                request_id=request_id,
                error=str(e),
                processing_stage="error"
            )
            # On error, still route to next step with error context
            published_faq = {'error': str(e)}
            publication_metadata = {'error': str(e)}
            operation = 'error'

        # Build result with preserved context
        result = {
            **ctx,
            'published_faq': published_faq,
            'publication_metadata': publication_metadata,
            'operation': operation,
            'next_step': 'invalidate_faq_cache',  # Routes to Step 130 per Mermaid
            'request_id': request_id
        }

        return result

async def step_131__vector_reindex(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 131 — VectorIndex.upsert_faq update embeddings
    ID: RAG.golden.vectorindex.upsert.faq.update.embeddings
    Type: process | Category: golden | Node: VectorReindex

    Thin async orchestrator that updates vector embeddings for published/updated FAQ entries.
    Uses EmbeddingManager.update_pinecone_embeddings to upsert FAQ content and metadata into
    vector index. Provides indexing metadata for observability.
    """
    ctx = ctx or {}
    request_id = ctx.get('request_id', 'unknown')

    with rag_step_timer(131, 'RAG.golden.vectorindex.upsert.faq.update.embeddings', 'VectorReindex',
                       request_id=request_id, stage="start"):
        rag_step_log(step=131, step_id='RAG.golden.vectorindex.upsert.faq.update.embeddings', node_label='VectorReindex',
                     category='golden', type='process', request_id=request_id, processing_stage="started")

        # Extract FAQ data
        published_faq = ctx.get('published_faq', {})
        publication_metadata = ctx.get('publication_metadata', {})
        faq_id = published_faq.get('id')

        if not faq_id:
            from datetime import datetime, timezone
            rag_step_log(step=131, step_id='RAG.golden.vectorindex.upsert.faq.update.embeddings', node_label='VectorReindex',
                        request_id=request_id, error="No FAQ ID found", processing_stage="error")

            # Build result with error
            result = {
                **ctx,
                'vector_index_metadata': {
                    'success': False,
                    'error': 'No FAQ ID found in published_faq',
                    'indexed_at': datetime.now(timezone.utc).isoformat()
                },
                'request_id': request_id
            }
            return result

        try:
            # Import here to avoid circular imports
            from datetime import datetime, timezone
            from app.services.embedding_management import EmbeddingManager

            embedding_manager = EmbeddingManager()

            # Prepare FAQ content for embedding
            faq_content = f"{published_faq.get('question', '')} {published_faq.get('answer', '')}".strip()

            embedding_items = [{
                'id': faq_id,
                'content': faq_content,
                'metadata': {
                    'faq_id': faq_id,
                    'category': published_faq.get('category'),
                    'version': published_faq.get('version', 1),
                    'operation': publication_metadata.get('operation', 'unknown'),
                    'regulatory_references': published_faq.get('regulatory_references', []),
                    'quality_score': published_faq.get('quality_score'),
                    'updated_at': publication_metadata.get('published_at'),
                    'source_type': 'faq'
                }
            }]

            # Update embeddings in vector index
            rag_step_log(step=131, step_id='RAG.golden.vectorindex.upsert.faq.update.embeddings', node_label='VectorReindex',
                        request_id=request_id, faq_id=faq_id, processing_stage="updating_embeddings")

            batch_result = await embedding_manager.update_pinecone_embeddings(
                items=embedding_items,
                source_type='faq'
            )

            # Create indexing metadata
            vector_metadata = {
                'faq_id': faq_id,
                'embeddings_updated': batch_result.successful,
                'total_items': batch_result.total_items,
                'failed_items': batch_result.failed,
                'processing_time': batch_result.processing_time_seconds,
                'version': published_faq.get('version', 1),
                'operation': publication_metadata.get('operation', 'unknown'),
                'success': batch_result.successful > 0 and batch_result.failed == 0,
                'indexed_at': datetime.now(timezone.utc).isoformat()
            }

            rag_step_log(step=131, step_id='RAG.golden.vectorindex.upsert.faq.update.embeddings', node_label='VectorReindex',
                        request_id=request_id, faq_id=faq_id, embeddings_updated=batch_result.successful,
                        processing_stage="completed")

        except Exception as e:
            from datetime import datetime, timezone
            rag_step_log(step=131, step_id='RAG.golden.vectorindex.upsert.faq.update.embeddings', node_label='VectorReindex',
                        request_id=request_id, faq_id=faq_id, error=str(e), processing_stage="error")

            vector_metadata = {
                'faq_id': faq_id,
                'success': False,
                'error': str(e),
                'indexed_at': datetime.now(timezone.utc).isoformat()
            }

        # Build result with preserved context
        result = {
            **ctx,
            'vector_index_metadata': vector_metadata,
            'request_id': request_id
        }

        return result

async def step_135__golden_rules(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 135 — GoldenSetUpdater.auto_rule_eval new or obsolete candidates
    ID: RAG.golden.goldensetupdater.auto.rule.eval.new.or.obsolete.candidates
    Type: process | Category: golden | Node: GoldenRules

    Thin async orchestrator that evaluates knowledge base content to automatically identify
    new FAQ candidates or obsolete ones that need updates. Uses FAQ automation services
    to apply rule-based evaluation criteria. Routes to GoldenCandidate (Step 127).
    """
    ctx = ctx or {}
    request_id = ctx.get('request_id', 'unknown')

    with rag_step_timer(135, 'RAG.golden.goldensetupdater.auto.rule.eval.new.or.obsolete.candidates', 'GoldenRules',
                       request_id=request_id, stage="start"):
        rag_step_log(step=135, step_id='RAG.golden.goldensetupdater.auto.rule.eval.new.or.obsolete.candidates', node_label='GoldenRules',
                     category='golden', type='process', request_id=request_id, processing_stage="started")

        # Extract knowledge updates and evaluation rules
        knowledge_updates = ctx.get('knowledge_updates', [])
        evaluation_rules = ctx.get('evaluation_rules', {})

        if not knowledge_updates:
            from datetime import datetime, timezone
            rag_step_log(step=135, step_id='RAG.golden.goldensetupdater.auto.rule.eval.new.or.obsolete.candidates', node_label='GoldenRules',
                        request_id=request_id, error="No knowledge updates to process", processing_stage="error")

            # Build result with no candidates
            result = {
                **ctx,
                'candidate_evaluation': {
                    'new_candidates': [],
                    'obsolete_candidates': [],
                    'candidates_generated': 0,
                    'obsolete_identified': 0,
                    'success': True,
                    'evaluated_at': datetime.now(timezone.utc).isoformat()
                },
                'next_step': 'golden_candidate',
                'request_id': request_id
            }
            return result

        try:
            # Import here to avoid circular imports
            from datetime import datetime, timezone

            # Apply rule-based evaluation to knowledge updates
            evaluation_results = await evaluate_knowledge_for_candidates(
                knowledge_updates, evaluation_rules, None
            )

            # Create evaluation metadata
            candidate_evaluation = {
                'new_candidates': evaluation_results.get('new_candidates', []),
                'obsolete_candidates': evaluation_results.get('obsolete_candidates', []),
                'candidates_generated': len(evaluation_results.get('new_candidates', [])),
                'obsolete_identified': len(evaluation_results.get('obsolete_candidates', [])),
                'total_processed': len(knowledge_updates),
                'filtered_out': evaluation_results.get('filtered_out', 0),
                'processing_time': evaluation_results.get('processing_time_seconds', 0.0),
                'success': True,
                'evaluated_at': datetime.now(timezone.utc).isoformat(),
                'evaluation_rules_applied': evaluation_rules
            }

            rag_step_log(step=135, step_id='RAG.golden.goldensetupdater.auto.rule.eval.new.or.obsolete.candidates', node_label='GoldenRules',
                        request_id=request_id, candidates_generated=candidate_evaluation['candidates_generated'],
                        obsolete_identified=candidate_evaluation['obsolete_identified'], processing_stage="completed")

        except Exception as e:
            from datetime import datetime, timezone
            rag_step_log(step=135, step_id='RAG.golden.goldensetupdater.auto.rule.eval.new.or.obsolete.candidates', node_label='GoldenRules',
                        request_id=request_id, error=str(e), processing_stage="error")

            candidate_evaluation = {
                'new_candidates': [],
                'obsolete_candidates': [],
                'candidates_generated': 0,
                'obsolete_identified': 0,
                'success': False,
                'error': str(e),
                'evaluated_at': datetime.now(timezone.utc).isoformat()
            }

        # Build result with preserved context
        result = {
            **ctx,
            'candidate_evaluation': candidate_evaluation,
            'next_step': 'golden_candidate',  # Routes to Step 127 per Mermaid
            'request_id': request_id
        }

        return result


async def evaluate_knowledge_for_candidates(knowledge_updates, evaluation_rules, faq_generator):
    """
    Helper function to evaluate knowledge updates for FAQ candidate generation.

    This function applies rule-based logic to determine which knowledge updates
    should become FAQ candidates and which existing candidates are obsolete.
    """
    import time
    from datetime import datetime, timezone, timedelta

    start_time = time.time()
    new_candidates = []
    obsolete_candidates = []
    filtered_out = 0

    # Default evaluation rules
    min_content_length = evaluation_rules.get('min_content_length', 100)
    priority_categories = evaluation_rules.get('priority_categories', [])
    min_priority_score = evaluation_rules.get('min_priority_score', 0.6)
    recency_threshold_days = evaluation_rules.get('recency_threshold_days', 30)

    for update in knowledge_updates:
        content = update.get('content', '')
        category = update.get('category', '')

        # Rule 1: Content length threshold
        if len(content) < min_content_length:
            filtered_out += 1
            continue

        # Rule 2: Priority category boost
        priority_score = 0.5  # Base score
        if category in priority_categories:
            priority_score += 0.3

        # Rule 3: Recency boost
        published_date = update.get('published_date')
        days_old = 0  # Default for scoring calculation
        if published_date:
            try:
                if 'T' in published_date:
                    pub_date = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
                else:
                    # Handle date-only format
                    pub_date = datetime.strptime(published_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                days_old = (datetime.now(timezone.utc) - pub_date).days
                if days_old <= recency_threshold_days:
                    priority_score += 0.2
            except Exception as e:
                # For debugging: log the error and continue
                pass

        # Rule 4: Priority keyword boost
        priority_keywords = evaluation_rules.get('priority_keywords', [])
        for keyword in priority_keywords:
            if keyword.lower() in content.lower():
                priority_score += 0.1
                break

        # Rule 5: Apply minimum priority threshold
        if priority_score < min_priority_score:
            filtered_out += 1
            continue

        # Generate candidate if passes all rules
        candidate = {
            'id': f"candidate_{update['id']}",
            'knowledge_source_id': update['id'],
            'proposed_question': f"What are the key points about {update.get('title', 'this topic')}?",
            'priority_score': min(priority_score, 1.0),
            'confidence': 0.8,  # Default confidence
            'category': category,
            'content_preview': content[:200] + '...' if len(content) > 200 else content,
            'evaluation_criteria_met': {
                'content_length': len(content),
                'priority_category': category in priority_categories,
                'recent_content': days_old <= recency_threshold_days if published_date else False,
                'priority_score': priority_score
            }
        }
        new_candidates.append(candidate)

        # Check for obsolete candidates (simplified logic)
        if update.get('supersedes_content_id'):
            obsolete_candidates.append({
                'knowledge_source_id': update['supersedes_content_id'],
                'reason': 'Superseded by new content',
                'replacement_candidate_id': candidate['id']
            })

    processing_time = time.time() - start_time

    return {
        'new_candidates': new_candidates,
        'obsolete_candidates': obsolete_candidates,
        'filtered_out': filtered_out,
        'processing_time_seconds': processing_time
    }
