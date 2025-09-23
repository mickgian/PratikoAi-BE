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

def step_14__extract_facts(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 14 — AtomicFactsExtractor.extract Extract atomic facts
    ID: RAG.facts.atomicfactsextractor.extract.extract.atomic.facts
    Type: process | Category: facts | Node: ExtractFacts

    TODO: Implement orchestration so this node *changes/validates control flow/data*
    according to Mermaid — not logs-only. Call into existing services/factories here.
    """
    with rag_step_timer(14, 'RAG.facts.atomicfactsextractor.extract.extract.atomic.facts', 'ExtractFacts', stage="start"):
        rag_step_log(step=14, step_id='RAG.facts.atomicfactsextractor.extract.extract.atomic.facts', node_label='ExtractFacts',
                     category='facts', type='process', stub=True, processing_stage="started")
        # TODO: call real service/factory here and return its output
        result = kwargs.get("result")  # placeholder
        rag_step_log(step=14, step_id='RAG.facts.atomicfactsextractor.extract.extract.atomic.facts', node_label='ExtractFacts',
                     processing_stage="completed")
        return result

def step_16__canonicalize_facts(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 16 — AtomicFactsExtractor.canonicalize Normalize dates amounts rates
    ID: RAG.facts.atomicfactsextractor.canonicalize.normalize.dates.amounts.rates
    Type: process | Category: facts | Node: CanonicalizeFacts

    TODO: Implement orchestration so this node *changes/validates control flow/data*
    according to Mermaid — not logs-only. Call into existing services/factories here.
    """
    with rag_step_timer(16, 'RAG.facts.atomicfactsextractor.canonicalize.normalize.dates.amounts.rates', 'CanonicalizeFacts', stage="start"):
        rag_step_log(step=16, step_id='RAG.facts.atomicfactsextractor.canonicalize.normalize.dates.amounts.rates', node_label='CanonicalizeFacts',
                     category='facts', type='process', stub=True, processing_stage="started")
        # TODO: call real service/factory here and return its output
        result = kwargs.get("result")  # placeholder
        rag_step_log(step=16, step_id='RAG.facts.atomicfactsextractor.canonicalize.normalize.dates.amounts.rates', node_label='CanonicalizeFacts',
                     processing_stage="completed")
        return result

def step_18__query_sig(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 18 — QuerySignature.compute Hash from canonical facts
    ID: RAG.facts.querysignature.compute.hash.from.canonical.facts
    Type: process | Category: facts | Node: QuerySig

    TODO: Implement orchestration so this node *changes/validates control flow/data*
    according to Mermaid — not logs-only. Call into existing services/factories here.
    """
    with rag_step_timer(18, 'RAG.facts.querysignature.compute.hash.from.canonical.facts', 'QuerySig', stage="start"):
        rag_step_log(step=18, step_id='RAG.facts.querysignature.compute.hash.from.canonical.facts', node_label='QuerySig',
                     category='facts', type='process', stub=True, processing_stage="started")
        # TODO: call real service/factory here and return its output
        result = kwargs.get("result")  # placeholder
        rag_step_log(step=18, step_id='RAG.facts.querysignature.compute.hash.from.canonical.facts', node_label='QuerySig',
                     processing_stage="completed")
        return result

def step_29__pre_context_from_golden(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 29 — ContextBuilder.merge facts and KB docs and doc facts if present
    ID: RAG.facts.contextbuilder.merge.facts.and.kb.docs.and.doc.facts.if.present
    Type: process | Category: facts | Node: PreContextFromGolden

    TODO: Implement orchestration so this node *changes/validates control flow/data*
    according to Mermaid — not logs-only. Call into existing services/factories here.
    """
    with rag_step_timer(29, 'RAG.facts.contextbuilder.merge.facts.and.kb.docs.and.doc.facts.if.present', 'PreContextFromGolden', stage="start"):
        rag_step_log(step=29, step_id='RAG.facts.contextbuilder.merge.facts.and.kb.docs.and.doc.facts.if.present', node_label='PreContextFromGolden',
                     category='facts', type='process', stub=True, processing_stage="started")
        # TODO: call real service/factory here and return its output
        result = kwargs.get("result")  # placeholder
        rag_step_log(step=29, step_id='RAG.facts.contextbuilder.merge.facts.and.kb.docs.and.doc.facts.if.present', node_label='PreContextFromGolden',
                     processing_stage="completed")
        return result

async def step_40__build_context(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 40 — ContextBuilder.merge facts and KB docs and optional doc facts
    ID: RAG.facts.contextbuilder.merge.facts.and.kb.docs.and.optional.doc.facts
    Type: process | Category: facts | Node: BuildContext

    Performs context merging by combining canonical facts, KB search results, and
    optional document facts into unified context for LLM processing. Thin orchestration
    that preserves existing ContextBuilderMerge behavior.
    """
    from app.core.logging import logger
    from app.services.context_builder_merge import ContextBuilderMerge
    from datetime import datetime, timezone

    with rag_step_timer(40, 'RAG.facts.contextbuilder.merge.facts.and.kb.docs.and.optional.doc.facts', 'BuildContext', stage="start"):
        # Extract context parameters
        request_id = kwargs.get('request_id') or (ctx or {}).get('request_id', 'unknown')
        canonical_facts = kwargs.get('canonical_facts') or (ctx or {}).get('canonical_facts', [])
        kb_results = kwargs.get('kb_results') or (ctx or {}).get('knowledge_items', [])  # From Step 39
        document_facts = kwargs.get('document_facts') or (ctx or {}).get('document_facts', [])
        query = kwargs.get('query') or (ctx or {}).get('user_message', '') or (ctx or {}).get('search_query', '')
        user_id = kwargs.get('user_id') or (ctx or {}).get('user_id')
        session_id = kwargs.get('session_id') or (ctx or {}).get('session_id')
        trace_id = kwargs.get('trace_id') or (ctx or {}).get('trace_id')

        # Context configuration parameters
        max_context_tokens = kwargs.get('max_context_tokens') or (ctx or {}).get('max_context_tokens', 1500)
        priority_weights = kwargs.get('priority_weights') or (ctx or {}).get('priority_weights', {})

        # Initialize result variables
        context_merged = False
        merged_context = ""
        context_parts = []
        token_count = 0
        source_distribution = {"facts": 0, "kb_docs": 0, "document_facts": 0}
        context_quality_score = 0.0
        error = None

        rag_step_log(
            step=40,
            step_id='RAG.facts.contextbuilder.merge.facts.and.kb.docs.and.optional.doc.facts',
            node_label='BuildContext',
            category='facts',
            type='process',
            processing_stage='started',
            request_id=request_id,
            facts_count=len(canonical_facts),
            kb_results_count=len(kb_results),
            document_facts_count=len(document_facts) if document_facts else 0,
            max_context_tokens=max_context_tokens
        )

        try:
            # TODO: In real implementation, inject ContextBuilderMerge via dependency injection
            # For thin orchestrator pattern, we'll receive the service as a parameter
            context_builder_service = kwargs.get('context_builder_service')

            if not context_builder_service:
                # Fallback: create service instance (for production use)
                context_builder_service = ContextBuilderMerge()

            # Prepare context data for the service
            context_data = {
                'canonical_facts': canonical_facts,
                'kb_results': kb_results,
                'document_facts': document_facts,
                'query': query,
                'user_id': user_id,
                'session_id': session_id,
                'trace_id': trace_id,
                'max_context_tokens': max_context_tokens,
                'priority_weights': priority_weights
            }

            # Perform the context merging
            merge_result = context_builder_service.merge_context(context_data)
            context_merged = True

            # Extract results
            merged_context = merge_result.get('merged_context', '')
            context_parts = merge_result.get('context_parts', [])
            token_count = merge_result.get('token_count', 0)
            source_distribution = merge_result.get('source_distribution', {"facts": 0, "kb_docs": 0, "document_facts": 0})
            context_quality_score = merge_result.get('context_quality_score', 0.0)

            # Log successful context merging
            logger.info(
                f"Context merging completed: {token_count} tokens from {len(context_parts)} parts",
                extra={
                    'request_id': request_id,
                    'query': query[:100] if query else '',
                    'token_count': token_count,
                    'max_context_tokens': max_context_tokens,
                    'source_distribution': source_distribution,
                    'context_quality_score': context_quality_score,
                    'deduplication_applied': merge_result.get('deduplication_applied', False),
                    'content_truncated': merge_result.get('content_truncated', False)
                }
            )

        except Exception as e:
            error = str(e)
            context_merged = False
            merged_context = ""
            context_parts = []
            token_count = 0
            source_distribution = {"facts": 0, "kb_docs": 0, "document_facts": 0}
            context_quality_score = 0.0

            logger.error(
                f"Error in context merging: {error}",
                extra={
                    'request_id': request_id,
                    'error': error,
                    'step': 40,
                    'query': query[:100] if query else ''
                }
            )

        # Build result preserving behavior while adding coordination metadata
        result = {
            'context_merged': context_merged,
            'merged_context': merged_context,
            'context_parts': context_parts,
            'token_count': token_count,
            'source_distribution': source_distribution,
            'context_quality_score': context_quality_score,
            'canonical_facts': canonical_facts,
            'kb_results': kb_results,
            'document_facts': document_facts,
            'query': query,
            'user_id': user_id,
            'session_id': session_id,
            'trace_id': trace_id,
            'request_id': request_id,
            'max_context_tokens': max_context_tokens,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'error': error
        }

        rag_step_log(
            step=40,
            step_id='RAG.facts.contextbuilder.merge.facts.and.kb.docs.and.optional.doc.facts',
            node_label='BuildContext',
            category='facts',
            type='process',
            processing_stage='completed',
            request_id=request_id,
            context_merged=context_merged,
            token_count=token_count,
            source_distribution=source_distribution,
            context_quality_score=context_quality_score
        )

        return result

def step_49__route_strategy(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
    """
    RAG STEP 49 — LLMFactory.get_optimal_provider Apply routing strategy
    ID: RAG.facts.llmfactory.get.optimal.provider.apply.routing.strategy
    Type: process | Category: facts | Node: RouteStrategy

    Applies the routing strategy using LLMFactory to select the optimal provider.
    Receives context from Step 48 (SelectProvider) and prepares for Step 50 (StrategyType).

    Incoming: SelectProvider (Step 48)
    Outgoing: StrategyType (Step 50)
    """
    from app.core.llm.factory import get_llm_factory, RoutingStrategy
    from app.core.logging import logger
    from datetime import datetime

    with rag_step_timer(49, 'RAG.facts.llmfactory.get.optimal.provider.apply.routing.strategy', 'RouteStrategy', stage="start"):
        # Merge ctx and kwargs for parameter extraction
        params = {}
        if ctx:
            params.update(ctx)
        params.update(kwargs)

        # Extract required parameters
        messages = params.get('messages', messages)
        if not messages:
            error_msg = 'Missing required parameter: messages'
            logger.error(f"STEP 49: {error_msg}")
            rag_step_log(
                step=49,
                step_id='RAG.facts.llmfactory.get.optimal.provider.apply.routing.strategy',
                node_label='RouteStrategy',
                category='facts',
                type='process',
                error=error_msg,
                routing_applied=False,
                processing_stage="failed"
            )
            return {
                'routing_applied': False,
                'error': error_msg,
                'provider': None,
                'timestamp': datetime.utcnow().isoformat()
            }

        # Extract routing parameters
        routing_strategy = params.get('routing_strategy', RoutingStrategy.COST_OPTIMIZED)
        max_cost_eur = params.get('max_cost_eur')
        preferred_provider = params.get('preferred_provider')
        fallback_provider = params.get('fallback_provider')

        # Additional context
        user_id = params.get('user_id')
        session_id = params.get('session_id')

        try:
            # Get the LLM factory and apply routing strategy
            factory = get_llm_factory()
            provider = factory.get_optimal_provider(
                messages=messages,
                strategy=routing_strategy,
                max_cost_eur=max_cost_eur,
                preferred_provider=preferred_provider
            )

            # Extract provider details
            provider_type = provider.provider_type.value if hasattr(provider.provider_type, 'value') else str(provider.provider_type)
            model = getattr(provider, 'model', 'unknown')

            logger.info(
                f"STEP 49: Routing strategy applied successfully",
                extra={
                    'step': 49,
                    'routing_strategy': routing_strategy.value if hasattr(routing_strategy, 'value') else str(routing_strategy),
                    'provider_type': provider_type,
                    'model': model,
                    'max_cost_eur': max_cost_eur
                }
            )

            rag_step_log(
                step=49,
                step_id='RAG.facts.llmfactory.get.optimal.provider.apply.routing.strategy',
                node_label='RouteStrategy',
                category='facts',
                type='process',
                routing_applied=True,
                routing_strategy=routing_strategy.value if hasattr(routing_strategy, 'value') else str(routing_strategy),
                provider_type=provider_type,
                model=model,
                max_cost_eur=max_cost_eur,
                preferred_provider=preferred_provider,
                user_id=user_id,
                session_id=session_id,
                processing_stage="started"
            )

            # Prepare result for Step 50 (StrategyType decision)
            result = {
                'routing_applied': True,
                'ready_for_decision': True,
                'provider': provider,
                'routing_strategy': routing_strategy,
                'provider_type': provider_type,
                'model': model,
                'max_cost_eur': max_cost_eur,
                'preferred_provider': preferred_provider,
                'fallback_provider': fallback_provider,
                'messages': messages,
                'user_id': user_id,
                'session_id': session_id,
                'timestamp': datetime.utcnow().isoformat()
            }

            rag_step_log(
                step=49,
                step_id='RAG.facts.llmfactory.get.optimal.provider.apply.routing.strategy',
                node_label='RouteStrategy',
                category='facts',
                type='process',
                routing_applied=True,
                ready_for_decision=True,
                routing_strategy=routing_strategy.value if hasattr(routing_strategy, 'value') else str(routing_strategy),
                provider_type=provider_type,
                model=model,
                processing_stage="completed"
            )

            return result

        except Exception as e:
            error_msg = str(e)
            logger.error(
                f"STEP 49: Failed to apply routing strategy",
                extra={
                    'step': 49,
                    'error': error_msg,
                    'routing_strategy': routing_strategy.value if hasattr(routing_strategy, 'value') else str(routing_strategy)
                }
            )

            rag_step_log(
                step=49,
                step_id='RAG.facts.llmfactory.get.optimal.provider.apply.routing.strategy',
                node_label='RouteStrategy',
                category='facts',
                type='process',
                error=error_msg,
                routing_applied=False,
                processing_stage="failed"
            )

            return {
                'routing_applied': False,
                'error': error_msg,
                'provider': None,
                'routing_strategy': routing_strategy,
                'messages': messages,
                'timestamp': datetime.utcnow().isoformat()
            }

async def step_95__extract_doc_facts(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 95 — Extractor.extract Structured fields
    ID: RAG.facts.extractor.extract.structured.fields
    Type: process | Category: facts | Node: ExtractDocFacts

    Extracts structured facts from parsed documents.
    Converts document-specific fields into normalized atomic facts.
    """
    ctx = ctx or {}
    parsed_docs = ctx.get('parsed_docs', [])
    request_id = ctx.get('request_id', 'unknown')

    with rag_step_timer(95, 'RAG.facts.extractor.extract.structured.fields', 'ExtractDocFacts', stage="start"):
        rag_step_log(
            step=95,
            step_id='RAG.facts.extractor.extract.structured.fields',
            node_label='ExtractDocFacts',
            category='facts',
            type='process',
            processing_stage="started",
            request_id=request_id,
            document_count=len(parsed_docs)
        )

        all_facts = []

        for doc in parsed_docs:
            doc_facts = []

            # Extract from extracted_fields (from specific parsers)
            if 'extracted_fields' in doc and doc.get('parsed_successfully'):
                fields = doc['extracted_fields']
                doc_type = doc.get('document_type', 'unknown')

                for key, value in fields.items():
                    if value:
                        fact = {
                            'type': 'document_field',
                            'field_name': key,
                            'value': str(value),
                            'document_type': doc_type,
                            'source_file': doc.get('filename', 'unknown')
                        }
                        doc_facts.append(fact)

            # Extract from extracted_text (from generic OCR)
            elif 'extracted_text' in doc and doc.get('parsed_successfully'):
                text = doc['extracted_text']
                doc_type = doc.get('document_type', 'unknown')

                # Create a fact for the full text content
                fact = {
                    'type': 'document_text',
                    'value': text[:500] if len(text) > 500 else text,  # Limit length
                    'full_text_length': len(text),
                    'document_type': doc_type,
                    'source_file': doc.get('filename', 'unknown')
                }
                doc_facts.append(fact)

            all_facts.extend(doc_facts)

        result = {
            'extraction_completed': True,
            'facts': all_facts,
            'facts_count': len(all_facts),
            'document_count': len(parsed_docs),
            'request_id': request_id,
            'next_step': 'store_blob'
        }

        rag_step_log(
            step=95,
            step_id='RAG.facts.extractor.extract.structured.fields',
            node_label='ExtractDocFacts',
            category='facts',
            type='process',
            processing_stage="completed",
            request_id=request_id,
            extraction_completed=True,
            facts_count=len(all_facts),
            document_count=len(parsed_docs)
        )

        return result

def step_98__to_tool_results(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 98 — Convert to ToolMessage facts and spans
    ID: RAG.facts.convert.to.toolmessage.facts.and.spans
    Type: process | Category: facts | Node: ToToolResults

    TODO: Implement orchestration so this node *changes/validates control flow/data*
    according to Mermaid — not logs-only. Call into existing services/factories here.
    """
    with rag_step_timer(98, 'RAG.facts.convert.to.toolmessage.facts.and.spans', 'ToToolResults', stage="start"):
        rag_step_log(step=98, step_id='RAG.facts.convert.to.toolmessage.facts.and.spans', node_label='ToToolResults',
                     category='facts', type='process', stub=True, processing_stage="started")
        # TODO: call real service/factory here and return its output
        result = kwargs.get("result")  # placeholder
        rag_step_log(step=98, step_id='RAG.facts.convert.to.toolmessage.facts.and.spans', node_label='ToToolResults',
                     processing_stage="completed")
        return result
