# AUTO-GENERATED ORCHESTRATOR STUBS (safe to edit below stubs)
# These functions are the functional *nodes* that mirror the Mermaid diagram.
# Implement thin coordination here (call services/factories), not core business logic.

from contextlib import nullcontext
from datetime import UTC
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from app.core.logging import logger

try:
    from app.observability.rag_logging import (
        rag_step_log,
        rag_step_timer,
    )
except Exception:  # pragma: no cover

    def rag_step_log(**kwargs):
        return None

    def rag_step_timer(*args, **kwargs):
        return nullcontext()


async def step_14__extract_facts(
    *, messages: list[Any] | None = None, ctx: dict[str, Any] | None = None, **kwargs
) -> Any:
    """RAG STEP 14 — AtomicFactsExtractor.extract Extract atomic facts
    ID: RAG.facts.atomicfactsextractor.extract.extract.atomic.facts
    Type: process | Category: facts | Node: ExtractFacts

    Extracts atomic facts from Italian professional queries including monetary amounts,
    dates, legal entities, professional categories, and geographic information.
    """
    from app.services.atomic_facts_extractor import AtomicFactsExtractor

    ctx = ctx or {}
    user_message = ctx.get("user_message", "")
    request_id = ctx.get("request_id", "unknown")

    with rag_step_timer(
        14, "RAG.facts.atomicfactsextractor.extract.extract.atomic.facts", "ExtractFacts", stage="start"
    ):
        rag_step_log(
            step=14,
            step_id="RAG.facts.atomicfactsextractor.extract.extract.atomic.facts",
            node_label="ExtractFacts",
            category="facts",
            type="process",
            processing_stage="started",
            request_id=request_id,
            user_message_length=len(user_message),
        )

        # Extract atomic facts using the service
        extractor = AtomicFactsExtractor()
        atomic_facts = extractor.extract(user_message)

        # Store in context for next steps
        result = {
            **ctx,
            "atomic_facts": atomic_facts,
            "fact_count": atomic_facts.fact_count(),
            "next_step": "canonicalize_facts",
        }

        rag_step_log(
            step=14,
            step_id="RAG.facts.atomicfactsextractor.extract.extract.atomic.facts",
            node_label="ExtractFacts",
            processing_stage="completed",
            request_id=request_id,
            fact_count=atomic_facts.fact_count(),
            extraction_time_ms=atomic_facts.extraction_time_ms,
            next_step="canonicalize_facts",
        )

    return result


async def step_16__canonicalize_facts(
    *, messages: list[Any] | None = None, ctx: dict[str, Any] | None = None, **kwargs
) -> Any:
    """RAG STEP 16 — AtomicFactsExtractor.canonicalize Normalize dates amounts rates
    ID: RAG.facts.atomicfactsextractor.canonicalize.normalize.dates.amounts.rates
    Type: process | Category: facts | Node: CanonicalizeFacts

    Validates that atomic facts from Step 14 are properly canonicalized.
    Ensures normalization of monetary amounts, dates, legal entities, and other extracted facts.
    """
    ctx = ctx or {}
    atomic_facts = ctx.get("atomic_facts")
    request_id = ctx.get("request_id", "unknown")

    with rag_step_timer(
        16,
        "RAG.facts.atomicfactsextractor.canonicalize.normalize.dates.amounts.rates",
        "CanonicalizeFacts",
        stage="start",
    ):
        rag_step_log(
            step=16,
            step_id="RAG.facts.atomicfactsextractor.canonicalize.normalize.dates.amounts.rates",
            node_label="CanonicalizeFacts",
            category="facts",
            type="process",
            processing_stage="started",
            request_id=request_id,
            fact_count=ctx.get("fact_count", 0),
        )

        # Validate that atomic facts exist and are canonicalized
        # Canonicalization happens in Step 14's extract() - this step validates the result
        canonicalization_valid = atomic_facts is not None

        # Convert atomic facts to canonical strings for search enhancement
        canonical_facts = []
        if atomic_facts and not atomic_facts.is_empty():
            canonical_facts = atomic_facts.to_canonical_strings()

        # Store validation result and canonical facts for search
        result = {
            **ctx,
            "canonicalization_valid": canonicalization_valid,
            "canonical_facts": canonical_facts,
            "next_step": "attachment_fingerprint",
        }

        rag_step_log(
            step=16,
            step_id="RAG.facts.atomicfactsextractor.canonicalize.normalize.dates.amounts.rates",
            node_label="CanonicalizeFacts",
            processing_stage="completed",
            request_id=request_id,
            canonicalization_valid=canonicalization_valid,
            canonical_facts_count=len(canonical_facts),
            canonical_facts=canonical_facts,
            next_step="attachment_fingerprint",
        )

    return result


async def step_18__query_sig(*, messages: list[Any] | None = None, ctx: dict[str, Any] | None = None, **kwargs) -> Any:
    """RAG STEP 18 — QuerySignature.compute Hash from canonical facts
    ID: RAG.facts.querysignature.compute.hash.from.canonical.facts
    Type: process | Category: facts | Node: QuerySig

    Computes a deterministic hash signature from canonicalized atomic facts.
    The hash is used for caching, deduplication, and query matching.
    """
    import hashlib
    import json

    ctx = ctx or {}
    atomic_facts = ctx.get("atomic_facts")
    request_id = ctx.get("request_id", "unknown")

    with rag_step_timer(18, "RAG.facts.querysignature.compute.hash.from.canonical.facts", "QuerySig", stage="start"):
        rag_step_log(
            step=18,
            step_id="RAG.facts.querysignature.compute.hash.from.canonical.facts",
            node_label="QuerySig",
            category="facts",
            type="process",
            processing_stage="started",
            request_id=request_id,
        )

        # Compute deterministic hash from canonical facts
        signature_data = {
            "monetary_amounts": [
                {"amount": amt.amount, "currency": amt.currency, "is_percentage": amt.is_percentage}
                for amt in (atomic_facts.monetary_amounts if atomic_facts else [])
            ],
            "dates": [
                {
                    "type": d.date_type,
                    "iso_date": d.iso_date,
                    "tax_year": d.tax_year,
                    "duration_value": d.duration_value,
                    "duration_unit": d.duration_unit,
                }
                for d in (atomic_facts.dates if atomic_facts else [])
            ],
            "legal_entities": [
                {"type": e.entity_type, "canonical": e.canonical_form, "identifier": e.identifier}
                for e in (atomic_facts.legal_entities if atomic_facts else [])
            ],
            "professional_categories": [
                {"type": c.category_type, "sector": c.sector}
                for c in (atomic_facts.professional_categories if atomic_facts else [])
            ],
            "geographic_info": [
                {"type": g.geo_type, "region": g.region, "city": g.city}
                for g in (atomic_facts.geographic_info if atomic_facts else [])
            ],
        }

        # Generate SHA256 hash
        signature_json = json.dumps(signature_data, sort_keys=True, ensure_ascii=True)
        query_signature = hashlib.sha256(signature_json.encode("utf-8")).hexdigest()

        # Store signature and route to next step
        result = {**ctx, "query_signature": query_signature, "next_step": "attach_check"}

        rag_step_log(
            step=18,
            step_id="RAG.facts.querysignature.compute.hash.from.canonical.facts",
            node_label="QuerySig",
            processing_stage="completed",
            request_id=request_id,
            query_signature=query_signature[:16] + "...",  # Log first 16 chars
            next_step="attach_check",
        )

    return result


async def step_29__pre_context_from_golden(
    *, messages: list[Any] | None = None, ctx: dict[str, Any] | None = None, **kwargs
) -> Any:
    """RAG STEP 29 — ContextBuilder.merge facts and KB docs and doc facts if present
    ID: RAG.facts.contextbuilder.merge.facts.and.kb.docs.and.doc.facts.if.present
    Type: process | Category: facts | Node: PreContextFromGolden

    Merges context when we have a golden answer but KB has newer/conflicting information.
    Combines golden answer context, KB deltas, atomic facts, and optional document facts
    into a pre-context merge before KB pre-fetching.
    """
    from app.services.context_builder_merge import ContextBuilderMerge

    ctx = ctx or {}
    request_id = ctx.get("request_id", "unknown")

    with rag_step_timer(
        29,
        "RAG.facts.contextbuilder.merge.facts.and.kb.docs.and.doc.facts.if.present",
        "PreContextFromGolden",
        stage="start",
    ):
        # Extract context components
        golden_answer = ctx.get("golden_answer", {})
        kb_deltas = ctx.get("kb_deltas", [])
        canonical_facts = ctx.get("canonical_facts", [])
        atomic_facts = ctx.get("atomic_facts")
        document_facts = ctx.get("document_facts")
        query = ctx.get("user_message", ctx.get("query", ""))

        rag_step_log(
            step=29,
            step_id="RAG.facts.contextbuilder.merge.facts.and.kb.docs.and.doc.facts.if.present",
            node_label="PreContextFromGolden",
            category="facts",
            type="process",
            processing_stage="started",
            request_id=request_id,
            has_golden_answer=bool(golden_answer),
            kb_deltas_count=len(kb_deltas),
            has_document_facts=document_facts is not None,
        )

        # Use ContextBuilderMerge service for pre-context merge
        builder = ContextBuilderMerge()

        # Prepare merge input (convert atomic_facts if needed)
        facts_list = canonical_facts if canonical_facts else []
        if atomic_facts and hasattr(atomic_facts, "get_summary"):
            # Convert AtomicFacts to list format if needed
            facts_list = [str(atomic_facts.get_summary())]

        merge_input = {
            "canonical_facts": facts_list,
            "kb_results": kb_deltas,
            "document_facts": document_facts,
            "query": query,
            "trace_id": request_id,
            "user_id": ctx.get("user_id"),
            "session_id": ctx.get("session_id"),
            "max_context_tokens": ctx.get("max_context_tokens", 1500),
        }

        # Perform pre-context merge
        merge_result = builder.merge_context(merge_input)

        # Prepare result with pre-context merge and routing
        result = {
            **ctx,  # Preserve all context fields
            "pre_context_merge": merge_result,
            "merged_context": merge_result.get("merged_context", ""),
            "context_parts": merge_result.get("context_parts", []),
            "next_step": "kb_pre_fetch",  # Routes to Step 39 per Mermaid
        }

        rag_step_log(
            step=29,
            step_id="RAG.facts.contextbuilder.merge.facts.and.kb.docs.and.doc.facts.if.present",
            node_label="PreContextFromGolden",
            processing_stage="completed",
            request_id=request_id,
            merge_completed=True,
            context_token_count=merge_result.get("token_count", 0),
            next_step="kb_pre_fetch",
        )

    return result


def _convert_attachments_to_doc_facts(attachments: list[dict] | None) -> list[str]:
    """Convert resolved attachments to document_facts format for context building.

    This helper bridges the gap between AttachmentResolver output and ContextBuilder input.
    The attachments from DEV-007 contain extracted_text and extracted_data which
    need to be formatted as document_facts strings for ContextBuilderMerge.

    DEV-007 Issue 11 Security (per @severino):
    - Applies prompt injection protection to prevent malicious document content
    - Applies MANDATORY PII anonymization before sending to LLM (GDPR compliance)

    Args:
        attachments: List of resolved attachment dicts from AttachmentResolver.
            Each dict may contain: id, filename, extracted_text, extracted_data,
            document_category, mime_type, file_size, processing_status, is_expired.

    Returns:
        List of formatted document fact strings for ContextBuilderMerge.
    """
    from app.core.privacy.anonymizer import PIIAnonymizer
    from app.utils.sanitization import sanitize_document_content

    if not attachments:
        return []

    # Initialize anonymizer once for all attachments
    anonymizer = PIIAnonymizer()

    doc_facts = []
    for att in attachments:
        filename = att.get("filename", "unknown")
        extracted_text = att.get("extracted_text")
        extracted_data = att.get("extracted_data")

        # Build fact parts starting with filename header
        fact_parts = [f"[Documento: {filename}]"]

        # DEV-007 Issue 10 FIX: ALWAYS include extracted_text first (the actual document content)
        # The previous logic used "elif" which skipped extracted_text when extracted_data existed
        if extracted_text:
            # DEV-007 Issue 11: Apply security measures before including in context
            # Step 1: Sanitize to prevent prompt injection attacks
            text = sanitize_document_content(extracted_text)

            # Step 2: MANDATORY PII anonymization (GDPR compliance per @severino)
            anonymization_result = anonymizer.anonymize_text(text)
            text = anonymization_result.anonymized_text

            if anonymization_result.pii_matches:
                logger.info(
                    "document_pii_anonymized",
                    filename=filename,
                    pii_count=len(anonymization_result.pii_matches),
                    pii_types=[m.pii_type.value for m in anonymization_result.pii_matches],
                )

            # Step 3: Truncate to limit context size (8000 chars for deep analysis)
            text = text[:8000] if len(text) > 8000 else text
            fact_parts.append(text)

        # THEN add extracted_data fields as additional metadata (skip redundant document_type)
        if extracted_data and isinstance(extracted_data, dict) and len(extracted_data) > 0:
            for key, value in extracted_data.items():
                # Skip document_type as it's redundant with filename context
                if value and key not in ("document_type",):
                    # Apply sanitization and anonymization to extracted_data values too
                    value_str = str(value)
                    value_str = sanitize_document_content(value_str)
                    anon_result = anonymizer.anonymize_text(value_str)
                    fact_parts.append(f"{key}: {anon_result.anonymized_text}")
        elif extracted_data and not isinstance(extracted_data, dict):
            # Apply sanitization and anonymization to non-dict extracted_data
            data_str = str(extracted_data)
            data_str = sanitize_document_content(data_str)
            anon_result = anonymizer.anonymize_text(data_str)
            fact_parts.append(anon_result.anonymized_text)

        # Only add if we have more than just the header
        if len(fact_parts) > 1:
            doc_facts.append("\n".join(fact_parts))

    return doc_facts


async def step_40__build_context(
    *, messages: list[Any] | None = None, ctx: dict[str, Any] | None = None, **kwargs
) -> Any:
    """RAG STEP 40 — ContextBuilder.merge facts and KB docs and optional doc facts
    ID: RAG.facts.contextbuilder.merge.facts.and.kb.docs.and.optional.doc.facts
    Type: process | Category: facts | Node: BuildContext

    Performs context merging by combining canonical facts, KB search results, and
    optional document facts into unified context for LLM processing. Thin orchestration
    that preserves existing ContextBuilderMerge behavior.

    DEV-007 Issue 9: Uses query_composition from Step 31 to select adaptive priority weights.
    """
    from datetime import (
        datetime,
        timezone,
    )

    from app.services.context_builder_merge import (
        ContextBuilderMerge,
        get_composition_priority_weights,
    )

    with rag_step_timer(
        40, "RAG.facts.contextbuilder.merge.facts.and.kb.docs.and.optional.doc.facts", "BuildContext", stage="start"
    ):
        # Extract context parameters
        request_id = kwargs.get("request_id") or (ctx or {}).get("request_id", "unknown")
        canonical_facts = kwargs.get("canonical_facts") or (ctx or {}).get("canonical_facts", [])
        # Try multiple locations for KB results: kb_results kwarg, knowledge_items, or kb_docs from RAGState
        kb_results = (
            kwargs.get("kb_results") or (ctx or {}).get("knowledge_items", []) or (ctx or {}).get("kb_docs", [])
        )  # From Step 39
        document_facts = kwargs.get("document_facts") or (ctx or {}).get("document_facts", [])

        # DEV-007: Convert chat attachments to document_facts if present
        # This bridges AttachmentResolver output -> ContextBuilder input
        attachments = kwargs.get("attachments") or (ctx or {}).get("attachments", [])
        if attachments and not document_facts:
            document_facts = _convert_attachments_to_doc_facts(attachments)
            logger.info(
                "attachments_converted_to_doc_facts",
                attachment_count=len(attachments),
                doc_facts_count=len(document_facts),
                request_id=request_id,
            )

        query = kwargs.get("query") or (ctx or {}).get("user_message", "") or (ctx or {}).get("search_query", "")
        user_id = kwargs.get("user_id") or (ctx or {}).get("user_id")
        session_id = kwargs.get("session_id") or (ctx or {}).get("session_id")
        trace_id = kwargs.get("trace_id") or (ctx or {}).get("trace_id")

        # Context configuration parameters
        # DYNAMIC TOKEN BUDGET: Calculate optimal budget based on content size
        # - Base: 3500 tokens (efficient for most queries)
        # - Scales: +500 token increments based on search results
        # - Max: 8000 tokens (for large aggregation queries)
        max_context_tokens_from_ctx = kwargs.get("max_context_tokens") or (ctx or {}).get("max_context_tokens")

        if not max_context_tokens_from_ctx:
            # Import context builder to use its budget calculation method
            from app.services.context_builder_merge import ContextBuilderMerge

            builder = ContextBuilderMerge()

            # Calculate optimal budget dynamically based on search results
            max_context_tokens = builder.calculate_optimal_budget(kb_results)

            logger.info(
                "dynamic_token_budget_applied",
                query_preview=query[:80] if query else "(empty)",
                kb_results_count=len(kb_results),
                calculated_budget=max_context_tokens,
                base_budget=builder.default_max_tokens,
                max_possible=builder.max_budget_limit,
                reason="automatic_scaling_based_on_content",
            )
        else:
            max_context_tokens = max_context_tokens_from_ctx
            logger.info(
                "manual_token_budget_used", manual_budget=max_context_tokens, source="explicit_context_parameter"
            )

        # DEV-007 Issue 9: Get priority weights based on query composition
        # query_composition comes from Step 31 (ClassifyDomain)
        query_composition = kwargs.get("query_composition") or (ctx or {}).get("query_composition")
        priority_weights = kwargs.get("priority_weights") or (ctx or {}).get("priority_weights", {})

        # If no explicit priority_weights provided, use composition-based weights
        if not priority_weights and query_composition:
            priority_weights = get_composition_priority_weights(query_composition)
            logger.info(
                "composition_priority_weights_applied",
                query_composition=query_composition,
                priority_weights=priority_weights,
                has_attachments=bool(attachments),
                doc_facts_count=len(document_facts) if document_facts else 0,
                request_id=request_id,
            )

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
            step_id="RAG.facts.contextbuilder.merge.facts.and.kb.docs.and.optional.doc.facts",
            node_label="BuildContext",
            category="facts",
            type="process",
            processing_stage="started",
            request_id=request_id,
            facts_count=len(canonical_facts),
            kb_results_count=len(kb_results),
            document_facts_count=len(document_facts) if document_facts else 0,
            max_context_tokens=max_context_tokens,
        )

        try:
            # TODO: In real implementation, inject ContextBuilderMerge via dependency injection
            # For thin orchestrator pattern, we'll receive the service as a parameter
            context_builder_service = kwargs.get("context_builder_service")

            if not context_builder_service:
                # Fallback: create service instance (for production use)
                context_builder_service = ContextBuilderMerge()

            # Prepare context data for the service
            context_data = {
                "canonical_facts": canonical_facts,
                "kb_results": kb_results,
                "document_facts": document_facts,
                "query": query,
                "user_id": user_id,
                "session_id": session_id,
                "trace_id": trace_id,
                "max_context_tokens": max_context_tokens,
                "priority_weights": priority_weights,
            }

            # Perform the context merging
            merge_result = context_builder_service.merge_context(context_data)
            context_merged = True

            # Extract results
            merged_context = merge_result.get("merged_context", "")
            context_parts = merge_result.get("context_parts", [])
            token_count = merge_result.get("token_count", 0)
            source_distribution = merge_result.get(
                "source_distribution", {"facts": 0, "kb_docs": 0, "document_facts": 0}
            )
            context_quality_score = merge_result.get("context_quality_score", 0.0)

            # Log successful context merging
            logger.info(
                f"Context merging completed: {token_count} tokens from {len(context_parts)} parts",
                extra={
                    "request_id": request_id,
                    "query": query[:100] if query else "",
                    "token_count": token_count,
                    "max_context_tokens": max_context_tokens,
                    "source_distribution": source_distribution,
                    "context_quality_score": context_quality_score,
                    "deduplication_applied": merge_result.get("deduplication_applied", False),
                    "content_truncated": merge_result.get("content_truncated", False),
                },
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
                extra={"request_id": request_id, "error": error, "step": 40, "query": query[:100] if query else ""},
            )

        # Build result preserving behavior while adding coordination metadata
        result = {
            "context_merged": context_merged,
            "merged_context": merged_context,
            "context_parts": context_parts,
            "token_count": token_count,
            "source_distribution": source_distribution,
            "context_quality_score": context_quality_score,
            "canonical_facts": canonical_facts,
            "kb_results": kb_results,
            "document_facts": document_facts,
            "query": query,
            "user_id": user_id,
            "session_id": session_id,
            "trace_id": trace_id,
            "request_id": request_id,
            "max_context_tokens": max_context_tokens,
            "query_composition": query_composition,  # DEV-007 Issue 9
            "priority_weights": priority_weights,  # DEV-007 Issue 9
            "timestamp": datetime.now(UTC).isoformat(),
            "error": error,
        }

        rag_step_log(
            step=40,
            step_id="RAG.facts.contextbuilder.merge.facts.and.kb.docs.and.optional.doc.facts",
            node_label="BuildContext",
            category="facts",
            type="process",
            processing_stage="completed",
            request_id=request_id,
            context_merged=context_merged,
            token_count=token_count,
            source_distribution=source_distribution,
            query_composition=query_composition,  # DEV-007 Issue 9
            context_quality_score=context_quality_score,
        )

        return result


def step_49__route_strategy(
    *, messages: list[Any] | None = None, ctx: dict[str, Any] | None = None, **kwargs
) -> dict[str, Any]:
    """RAG STEP 49 — LLMFactory.get_optimal_provider Apply routing strategy
    ID: RAG.facts.llmfactory.get.optimal.provider.apply.routing.strategy
    Type: process | Category: facts | Node: RouteStrategy

    Applies the routing strategy using LLMFactory to select the optimal provider.
    Receives context from Step 48 (SelectProvider) and prepares for Step 50 (StrategyType).

    Incoming: SelectProvider (Step 48)
    Outgoing: StrategyType (Step 50)
    """
    from datetime import datetime

    from app.core.llm.factory import (
        RoutingStrategy,
        get_llm_factory,
    )

    with rag_step_timer(
        49, "RAG.facts.llmfactory.get.optimal.provider.apply.routing.strategy", "RouteStrategy", stage="start"
    ):
        # Merge ctx and kwargs for parameter extraction
        params = {}
        if ctx:
            params.update(ctx)
        params.update(kwargs)

        # Extract required parameters
        messages = params.get("messages", messages)
        if not messages:
            error_msg = "Missing required parameter: messages"
            logger.error(f"STEP 49: {error_msg}")
            rag_step_log(
                step=49,
                step_id="RAG.facts.llmfactory.get.optimal.provider.apply.routing.strategy",
                node_label="RouteStrategy",
                category="facts",
                type="process",
                error=error_msg,
                routing_applied=False,
                processing_stage="failed",
            )
            return {
                "routing_applied": False,
                "error": error_msg,
                "provider": None,
                "timestamp": datetime.utcnow().isoformat(),
            }

        # Extract routing parameters
        routing_strategy = params.get("routing_strategy", RoutingStrategy.COST_OPTIMIZED)
        max_cost_eur = params.get("max_cost_eur")
        preferred_provider = params.get("preferred_provider")
        fallback_provider = params.get("fallback_provider")

        # Additional context
        user_id = params.get("user_id")
        session_id = params.get("session_id")

        try:
            # Convert dict messages to Message objects if needed
            from app.schemas.chat import Message

            if messages and isinstance(messages[0], dict):
                messages = [Message.model_validate(msg) for msg in messages]

            # Get the LLM factory and apply routing strategy
            factory = get_llm_factory()
            provider = factory.get_optimal_provider(
                messages=messages,
                strategy=routing_strategy,
                max_cost_eur=max_cost_eur,
                preferred_provider=preferred_provider,
            )

            # Extract provider details
            provider_type = (
                provider.provider_type.value
                if hasattr(provider.provider_type, "value")
                else str(provider.provider_type)
            )
            model = getattr(provider, "model", "unknown")

            logger.info(
                "STEP 49: Routing strategy applied successfully",
                extra={
                    "step": 49,
                    "routing_strategy": (
                        routing_strategy.value if hasattr(routing_strategy, "value") else str(routing_strategy)
                    ),
                    "provider_type": provider_type,
                    "model": model,
                    "max_cost_eur": max_cost_eur,
                },
            )

            rag_step_log(
                step=49,
                step_id="RAG.facts.llmfactory.get.optimal.provider.apply.routing.strategy",
                node_label="RouteStrategy",
                category="facts",
                type="process",
                routing_applied=True,
                routing_strategy=(
                    routing_strategy.value if hasattr(routing_strategy, "value") else str(routing_strategy)
                ),
                provider_type=provider_type,
                model=model,
                max_cost_eur=max_cost_eur,
                preferred_provider=preferred_provider,
                user_id=user_id,
                session_id=session_id,
                processing_stage="started",
            )

            # Prepare result for Step 50 (StrategyType decision)
            result = {
                "routing_applied": True,
                "ready_for_decision": True,
                "provider": provider,
                "routing_strategy": routing_strategy,
                "provider_type": provider_type,
                "model": model,
                "max_cost_eur": max_cost_eur,
                "preferred_provider": preferred_provider,
                "fallback_provider": fallback_provider,
                "messages": messages,
                "user_id": user_id,
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat(),
            }

            rag_step_log(
                step=49,
                step_id="RAG.facts.llmfactory.get.optimal.provider.apply.routing.strategy",
                node_label="RouteStrategy",
                category="facts",
                type="process",
                routing_applied=True,
                ready_for_decision=True,
                routing_strategy=(
                    routing_strategy.value if hasattr(routing_strategy, "value") else str(routing_strategy)
                ),
                provider_type=provider_type,
                model=model,
                processing_stage="completed",
            )

            return result

        except Exception as e:
            error_msg = str(e)
            logger.error(
                "STEP 49: Failed to apply routing strategy",
                extra={
                    "step": 49,
                    "error": error_msg,
                    "routing_strategy": (
                        routing_strategy.value if hasattr(routing_strategy, "value") else str(routing_strategy)
                    ),
                },
            )

            rag_step_log(
                step=49,
                step_id="RAG.facts.llmfactory.get.optimal.provider.apply.routing.strategy",
                node_label="RouteStrategy",
                category="facts",
                type="process",
                error=error_msg,
                routing_applied=False,
                processing_stage="failed",
            )

            return {
                "routing_applied": False,
                "error": error_msg,
                "provider": None,
                "routing_strategy": routing_strategy,
                "messages": messages,
                "timestamp": datetime.utcnow().isoformat(),
            }


async def step_95__extract_doc_facts(
    *, messages: list[Any] | None = None, ctx: dict[str, Any] | None = None, **kwargs
) -> Any:
    """RAG STEP 95 — Extractor.extract Structured fields
    ID: RAG.facts.extractor.extract.structured.fields
    Type: process | Category: facts | Node: ExtractDocFacts

    Extracts structured facts from parsed documents.
    Converts document-specific fields into normalized atomic facts.
    """
    ctx = ctx or {}
    parsed_docs = ctx.get("parsed_docs", [])
    request_id = ctx.get("request_id", "unknown")

    with rag_step_timer(95, "RAG.facts.extractor.extract.structured.fields", "ExtractDocFacts", stage="start"):
        rag_step_log(
            step=95,
            step_id="RAG.facts.extractor.extract.structured.fields",
            node_label="ExtractDocFacts",
            category="facts",
            type="process",
            processing_stage="started",
            request_id=request_id,
            document_count=len(parsed_docs),
        )

        all_facts = []

        for doc in parsed_docs:
            doc_facts = []

            # Extract from extracted_fields (from specific parsers)
            if "extracted_fields" in doc and doc.get("parsed_successfully"):
                fields = doc["extracted_fields"]
                doc_type = doc.get("document_type", "unknown")

                for key, value in fields.items():
                    if value:
                        fact = {
                            "type": "document_field",
                            "field_name": key,
                            "value": str(value),
                            "document_type": doc_type,
                            "source_file": doc.get("filename", "unknown"),
                        }
                        doc_facts.append(fact)

            # Extract from extracted_text (from generic OCR)
            elif "extracted_text" in doc and doc.get("parsed_successfully"):
                text = doc["extracted_text"]
                doc_type = doc.get("document_type", "unknown")

                # Create a fact for the full text content
                fact = {
                    "type": "document_text",
                    "value": text[:500] if len(text) > 500 else text,  # Limit length
                    "full_text_length": len(text),
                    "document_type": doc_type,
                    "source_file": doc.get("filename", "unknown"),
                }
                doc_facts.append(fact)

            all_facts.extend(doc_facts)

        result = {
            "extraction_completed": True,
            "facts": all_facts,
            "facts_count": len(all_facts),
            "document_count": len(parsed_docs),
            "request_id": request_id,
            "next_step": "store_blob",
        }

        rag_step_log(
            step=95,
            step_id="RAG.facts.extractor.extract.structured.fields",
            node_label="ExtractDocFacts",
            category="facts",
            type="process",
            processing_stage="completed",
            request_id=request_id,
            extraction_completed=True,
            facts_count=len(all_facts),
            document_count=len(parsed_docs),
        )

        return result


async def step_98__to_tool_results(
    *, messages: list[Any] | None = None, ctx: dict[str, Any] | None = None, **kwargs
) -> Any:
    """RAG STEP 98 — Convert to ToolMessage facts and spans
    ID: RAG.facts.convert.to.toolmessage.facts.and.spans
    Type: process | Category: facts | Node: ToToolResults

    Converts extracted document facts and provenance into ToolMessage format
    for returning to the LLM tool caller. Formats facts and metadata into
    structured tool response.
    """
    import json

    from langchain_core.messages import ToolMessage

    ctx = ctx or {}
    facts = ctx.get("facts", [])
    ledger_entries = ctx.get("ledger_entries", [])
    tool_call_id = ctx.get("tool_call_id", "unknown")
    request_id = ctx.get("request_id", "unknown")

    with rag_step_timer(98, "RAG.facts.convert.to.toolmessage.facts.and.spans", "ToToolResults", stage="start"):
        rag_step_log(
            step=98,
            step_id="RAG.facts.convert.to.toolmessage.facts.and.spans",
            node_label="ToToolResults",
            category="facts",
            type="process",
            processing_stage="started",
            request_id=request_id,
            facts_count=len(facts),
            ledger_count=len(ledger_entries),
        )

        # Format facts into readable content
        content_parts = []

        if facts:
            content_parts.append("Extracted Document Facts:")
            for fact in facts:
                fact_type = fact.get("type", "unknown")
                if fact_type == "document_field":
                    field_name = fact.get("field_name", "unknown")
                    value = fact.get("value", "")
                    doc_type = fact.get("document_type", "unknown")
                    content_parts.append(f"- {field_name}: {value} (from {doc_type})")
                elif fact_type == "document_text":
                    value = fact.get("value", "")
                    doc_type = fact.get("document_type", "unknown")
                    content_parts.append(f"- Text content from {doc_type}: {value}")

        # Add provenance summary if available
        if ledger_entries:
            content_parts.append("\nDocument Provenance:")
            for entry in ledger_entries:
                filename = entry.get("filename", "unknown")
                blob_id = entry.get("blob_id", "unknown")
                content_parts.append(f"- Processed: {filename} (ID: {blob_id[:16]}...)")

        # Create formatted content
        tool_message_content = "\n".join(content_parts) if content_parts else "No facts extracted"

        # Create ToolMessage
        tool_message = ToolMessage(content=tool_message_content, tool_call_id=tool_call_id)

        result = {
            **ctx,  # Preserve all context fields
            "tool_message": tool_message,
            "tool_message_content": tool_message_content,
            "conversion_successful": True,
            "facts_count": len(facts),
            "next_step": "tool_results",  # Routes to Step 99 per Mermaid
        }

        rag_step_log(
            step=98,
            step_id="RAG.facts.convert.to.toolmessage.facts.and.spans",
            node_label="ToToolResults",
            category="facts",
            type="process",
            processing_stage="completed",
            request_id=request_id,
            conversion_successful=True,
            facts_count=len(facts),
            tool_message_length=len(tool_message_content),
            next_step="tool_results",
        )

    return result
