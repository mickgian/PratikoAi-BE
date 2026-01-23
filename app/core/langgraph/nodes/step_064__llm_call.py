"""Node wrapper for Step 64: LLM Call.

DEV-214: Enhanced with unified JSON output parsing for reasoning traces
and sources with hierarchy.

DEV-222: Integrates LLMOrchestrator for complexity-based model routing
and cost tracking.

DEV-226: Integrates TreeOfThoughtsReasoner for complex/multi_domain queries.
Uses ToT for multi-hypothesis reasoning with source-weighted scoring.

DEV-238: Integrates detailed reasoning trace logging with mandatory context fields.

DEV-244: Removed VERDETTO format support - using unified clean format.
"""

import json
import re
import time
from typing import TYPE_CHECKING, Any

from app.core.langgraph.node_utils import mirror, ns
from app.core.langgraph.types import RAGState
from app.core.logging import logger
from app.observability.rag_logging import (
    rag_step_log_compat as rag_step_log,
)
from app.observability.rag_logging import (
    rag_step_timer_compat as rag_step_timer,
)
from app.orchestrators.providers import step_64__llmcall
from app.services.reasoning_trace_logger import (
    log_reasoning_trace_failed,
    log_reasoning_trace_recorded,
    log_tot_hypothesis_evaluated,
)

# DEV-196: Lazy imports to avoid database connection during module load
if TYPE_CHECKING:
    from app.services.llm_orchestrator import LLMOrchestrator
    from app.services.premium_model_selector import PremiumModelSelector
    from app.services.tree_of_thoughts_reasoner import ToTResult, TreeOfThoughtsReasoner

STEP = 64

# DEV-222: Cached orchestrator instance
_orchestrator_instance: "LLMOrchestrator | None" = None


def get_llm_orchestrator() -> "LLMOrchestrator":
    """Get or create LLMOrchestrator instance.

    DEV-222: Uses lazy initialization to avoid circular imports
    and database connection during module load.

    Returns:
        LLMOrchestrator singleton instance
    """
    global _orchestrator_instance
    if _orchestrator_instance is None:
        from app.services.llm_orchestrator import get_llm_orchestrator as _get_orchestrator

        _orchestrator_instance = _get_orchestrator()
    return _orchestrator_instance


async def _classify_query_complexity(state: RAGState) -> tuple[str, dict]:
    """Classify query complexity before LLM call.

    DEV-222: Uses LLMOrchestrator to determine if query is SIMPLE, COMPLEX,
    or MULTI_DOMAIN. Returns complexity and context for logging.

    Args:
        state: RAG state with user query and context

    Returns:
        Tuple of (complexity string, context dict for logging)
    """
    from app.services.llm_orchestrator import ComplexityContext, QueryComplexity

    try:
        orchestrator = get_llm_orchestrator()

        # Extract user query from messages
        messages = state.get("messages", [])
        user_message = state.get("user_message", "")

        # Get the last user message if not explicitly set
        if not user_message and messages:
            for msg in reversed(messages):
                if isinstance(msg, dict) and msg.get("role") == "user":
                    user_message = msg.get("content", "")
                    break

        # Build complexity context
        detected_domains = state.get("detected_domains", [])
        has_history = len(messages) > 1
        has_documents = bool(state.get("kb_sources_metadata"))

        context = ComplexityContext(
            domains=detected_domains,
            has_history=has_history,
            has_documents=has_documents,
        )

        # Classify complexity
        complexity = await orchestrator.classify_complexity(user_message, context)

        complexity_context = {
            "complexity": complexity.value,
            "domains": detected_domains,
            "has_history": has_history,
            "has_documents": has_documents,
        }

        logger.info(
            "step64_complexity_classified",
            complexity=complexity.value,
            query_preview=user_message[:100] if user_message else "",
            domains=detected_domains,
            request_id=state.get("request_id"),
        )

        return complexity.value, complexity_context

    except Exception as e:
        # Fallback to SIMPLE on classification error
        logger.warning(
            "step64_complexity_classification_failed",
            error=str(e),
            request_id=state.get("request_id"),
        )
        return "simple", {"complexity": "simple", "fallback": True, "error": str(e)}


# DEV-226: Cached TreeOfThoughtsReasoner instance
_tot_reasoner_instance: "TreeOfThoughtsReasoner | None" = None


def _get_tot_reasoner() -> "TreeOfThoughtsReasoner":
    """Get or create TreeOfThoughtsReasoner instance.

    DEV-226: Uses lazy initialization to avoid circular imports.

    Returns:
        TreeOfThoughtsReasoner singleton instance
    """
    global _tot_reasoner_instance
    if _tot_reasoner_instance is None:
        from app.services.tree_of_thoughts_reasoner import (
            get_tree_of_thoughts_reasoner,
        )

        _tot_reasoner_instance = get_tree_of_thoughts_reasoner()
    return _tot_reasoner_instance


async def _use_tree_of_thoughts(
    state: RAGState,
    complexity: str,
) -> "ToTResult":
    """Execute Tree of Thoughts reasoning for complex queries.

    DEV-226: Uses TreeOfThoughtsReasoner for multi-hypothesis reasoning
    with source-weighted scoring for complex and multi_domain queries.

    Args:
        state: RAG state with query and KB sources
        complexity: Query complexity ("complex" or "multi_domain")

    Returns:
        ToTResult with selected hypothesis and reasoning trace
    """
    from app.services.tree_of_thoughts_reasoner import ToTResult

    # Get user query
    user_message = state.get("user_message", "")
    if not user_message:
        messages = state.get("messages", [])
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("role") == "user":
                user_message = msg.get("content", "")
                break

    # Get KB sources
    kb_sources = state.get("kb_sources_metadata", [])

    # Get domains for multi-domain queries
    domains = state.get("detected_domains", [])

    # Get reasoner and execute
    reasoner = _get_tot_reasoner()

    logger.info(
        "step64_tot_reasoning_started",
        complexity=complexity,
        query_preview=user_message[:100] if user_message else "",
        num_sources=len(kb_sources),
        domains=domains,
        request_id=state.get("request_id"),
    )

    result = await reasoner.reason(
        query=user_message,
        kb_sources=kb_sources,
        complexity=complexity,
        domains=domains if complexity == "multi_domain" else None,
    )

    logger.info(
        "step64_tot_reasoning_completed",
        selected_hypothesis_id=result.selected_hypothesis.id,
        confidence=result.selected_hypothesis.confidence,
        latency_ms=result.total_latency_ms,
        request_id=state.get("request_id"),
    )

    return result


# DEV-214: Italian legal source hierarchy (highest to lowest authority)
SOURCE_HIERARCHY = {
    "legge": 1,  # Legge (Law)
    "decreto": 2,  # Decreto Legislativo / DPR / D.Lgs
    "circolare": 3,  # Circolare AdE
    "interpello": 4,  # Interpello / Risposta
    "prassi": 5,  # Other prassi
    "unknown": 99,
}


def _extract_json_from_content(content: str) -> dict | None:
    """Extract JSON from response that may contain markdown code blocks.

    DEV-214: Handles multiple JSON formats:
    - ```json ... ``` markdown blocks
    - Raw JSON objects
    - JSON with surrounding text

    Args:
        content: LLM response content

    Returns:
        Parsed dict if valid JSON found, None otherwise
    """
    if not content:
        return None

    # Try 1: Extract from markdown ```json ... ``` block
    json_block_pattern = r"```json\s*\n?(.*?)\n?```"
    match = re.search(json_block_pattern, content, re.DOTALL | re.IGNORECASE)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try 2: Extract from ``` ... ``` block (without json specifier)
    code_block_pattern = r"```\s*\n?(.*?)\n?```"
    match = re.search(code_block_pattern, content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try 3: Find JSON object in content (starts with { ends with })
    # Use greedy matching to find the largest JSON object
    json_object_pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
    matches = re.findall(json_object_pattern, content, re.DOTALL)
    for potential_json in reversed(matches):  # Try largest matches first
        try:
            return json.loads(potential_json)
        except json.JSONDecodeError:
            continue

    # Try 4: Raw JSON parsing of entire content
    try:
        return json.loads(content.strip())
    except json.JSONDecodeError:
        pass

    return None


def _parse_unified_response(content: str) -> dict | None:
    """Parse unified JSON response from LLM.

    DEV-214: Extracts structured response with reasoning, answer, and sources.

    Args:
        content: LLM response content

    Returns:
        Parsed dict with reasoning, answer, sources.
        None if parsing fails.
    """
    if not content:
        return None

    parsed = _extract_json_from_content(content)

    if parsed is None:
        return None

    # Validate that it has at least one expected field
    expected_fields = {"reasoning", "answer", "sources_cited"}
    if not any(field in parsed for field in expected_fields):
        return None

    return parsed


def _fallback_to_text(content: str, state: RAGState) -> dict:
    """Fallback parsing when JSON extraction fails.

    DEV-214: Returns minimal valid response with answer only.

    Args:
        content: LLM response content
        state: Current RAG state (for logging context)

    Returns:
        Dict with answer and empty optional fields
    """
    logger.info(
        "step64_fallback_to_text",
        content_length=len(content) if content else 0,
        request_id=state.get("request_id"),
    )

    return {
        "reasoning": None,
        "answer": content or "",
        "sources_cited": [],
    }


def _apply_source_hierarchy(sources: list[dict]) -> list[dict]:
    """Sort sources by Italian legal hierarchy and add hierarchy_rank.

    DEV-214: Italian legal source hierarchy (highest to lowest authority):
    1. Legge (L., Legge)
    2. Decreto (D.Lgs., DPR, Decreto)
    3. Circolare (Circolare AdE)
    4. Interpello (Interpello, Risposta)
    5. Other/Unknown

    Args:
        sources: List of source dicts from LLM response

    Returns:
        Sorted sources with hierarchy_rank added, highest authority first
    """
    if not sources:
        return []

    for source in sources:
        ref = source.get("ref", "").lower()

        # Determine hierarchy rank based on reference text
        if "legge" in ref or ref.startswith("l.") or " l. " in ref:
            source["hierarchy_rank"] = SOURCE_HIERARCHY["legge"]
        elif any(term in ref for term in ["decreto", "d.lgs", "dpr", "d.l."]):
            source["hierarchy_rank"] = SOURCE_HIERARCHY["decreto"]
        elif "circolare" in ref:
            source["hierarchy_rank"] = SOURCE_HIERARCHY["circolare"]
        elif any(term in ref for term in ["interpello", "risposta"]):
            source["hierarchy_rank"] = SOURCE_HIERARCHY["interpello"]
        elif any(term in ref for term in ["prassi", "risoluzione"]):
            source["hierarchy_rank"] = SOURCE_HIERARCHY["prassi"]
        else:
            source["hierarchy_rank"] = SOURCE_HIERARCHY["unknown"]

    # Sort by hierarchy rank (lowest number = highest authority)
    return sorted(sources, key=lambda s: s.get("hierarchy_rank", 99))


def _deanonymize_response(content: str, deanonymization_map: dict[str, str]) -> str:
    """Restore original PII values in LLM response.

    DEV-007 PII: Reverse the anonymization applied to document content.
    Sorts placeholders by length descending to avoid partial replacements.

    Args:
        content: LLM response text with PII placeholders
        deanonymization_map: Dict mapping placeholder -> original value

    Returns:
        Response text with original PII values restored
    """
    if not deanonymization_map or not content:
        return content

    result = content
    # Sort by length descending to avoid partial replacements
    # e.g., [NOME_ABC123] should be replaced before [NOME_ABC]
    for placeholder, original in sorted(
        deanonymization_map.items(),
        key=lambda x: len(x[0]),
        reverse=True,
    ):
        result = result.replace(placeholder, original)

    return result


def _merge(d: dict[str, Any], patch: dict[str, Any]) -> None:
    """Recursively merge patch into d (additive)."""
    for k, v in (patch or {}).items():
        if isinstance(v, dict):
            d.setdefault(k, {})
            if isinstance(d[k], dict):
                _merge(d[k], v)
            else:
                d[k] = v
        else:
            d[k] = v


def _process_unified_response(content: str, state: RAGState) -> str:
    """Process LLM response with unified JSON parsing.

    DEV-214: Extracts and stores reasoning and sources from JSON response.
    Falls back to text extraction if JSON parsing fails.

    DEV-226: Preserves ToT reasoning_type if already set (from TreeOfThoughtsReasoner).

    Args:
        content: LLM response content
        state: RAG state to update with parsed fields

    Returns:
        The answer text to use for display (from JSON or raw content)
    """
    # Try unified JSON parsing
    parsed = _parse_unified_response(content)

    if parsed:
        # DEV-226: Preserve ToT reasoning if already set, otherwise use CoT
        if state.get("reasoning_type") != "tot":
            state["reasoning_type"] = "cot"
            state["reasoning_trace"] = parsed.get("reasoning")
        # If ToT, reasoning_trace is already set by _use_tree_of_thoughts

        # Store and validate sources with hierarchy
        sources = parsed.get("sources_cited", [])
        state["sources_cited"] = _apply_source_hierarchy(sources)

        # Use answer for display
        answer = parsed.get("answer", content)

        # DEV-245 Phase 5.1: Filter out unauthorized disclaimers
        # LLM sometimes ignores prompt instructions and includes "consulta un esperto"
        # This is a safety net to catch those cases and remove them
        from app.services.disclaimer_filter import DisclaimerFilter

        answer, removed_disclaimers = DisclaimerFilter.filter_response(answer)
        if removed_disclaimers:
            logger.info(
                "step64_disclaimers_filtered",
                removed_count=len(removed_disclaimers),
                request_id=state.get("request_id"),
            )

        logger.info(
            "step64_unified_response_parsed",
            has_reasoning=parsed.get("reasoning") is not None,
            sources_count=len(sources),
            request_id=state.get("request_id"),
        )

        return answer
    else:
        # Fallback: JSON parsing failed
        # DEV-226: Preserve ToT reasoning_type if already set
        if state.get("reasoning_type") != "tot":
            state["reasoning_type"] = None
            state["reasoning_trace"] = None
        state["sources_cited"] = []

        logger.warning(
            "step64_json_parse_failed",
            content_length=len(content) if content else 0,
            content_preview=content[:200] if content else "",
            request_id=state.get("request_id"),
        )

        # DEV-238: Log reasoning trace parse failure with mandatory context
        log_reasoning_trace_failed(
            state=state,
            error_type="JSONParseError",
            error_message="Failed to extract unified JSON response",
            content_sample=content[:500] if content else "",
        )

        # DEV-245 Phase 5.1: Filter out unauthorized disclaimers (fallback branch)
        from app.services.disclaimer_filter import DisclaimerFilter

        filtered_content, removed_disclaimers = DisclaimerFilter.filter_response(content)
        if removed_disclaimers:
            logger.info(
                "step64_disclaimers_filtered_fallback",
                removed_count=len(removed_disclaimers),
                request_id=state.get("request_id"),
            )

        return filtered_content


def _check_kb_empty_and_inject_warning(state: RAGState) -> bool:
    """Check if KB returned empty/irrelevant results and inject warning.

    DEV-242: When KB returns no relevant documents, the LLM tends to hallucinate
    from training data. This check detects empty KB and injects a strong warning
    into the context to force the LLM to respond with "Non ho trovato".

    Args:
        state: RAG state with kb_sources_metadata

    Returns:
        True if KB is empty/irrelevant and warning was injected
    """
    kb_sources = state.get("kb_sources_metadata", [])
    # DEV-242 Phase 10: Read from "context" key (where Step 40 stores KB)
    # Fall back to "kb_context" for backward compatibility
    kb_context = state.get("context", "") or state.get("kb_context", "")

    # Check if KB is empty
    is_kb_empty = len(kb_sources) == 0

    # Check if KB context is too short (just headers/navigation)
    is_kb_context_minimal = len(kb_context.strip()) < 200

    # If KB has sources but context is minimal, treat as effectively empty
    kb_effectively_empty = is_kb_empty or (is_kb_context_minimal and len(kb_sources) <= 1)

    if kb_effectively_empty:
        # Extract user query for logging
        user_message = state.get("user_message", "")
        if not user_message:
            messages = state.get("messages", [])
            for msg in reversed(messages):
                if isinstance(msg, dict) and msg.get("role") == "user":
                    user_message = msg.get("content", "")
                    break

        # DEV-242: Inject critical KB-empty warning by prepending to kb_context
        # This ensures the warning flows through the existing prompt system
        kb_empty_warning = """
⚠️⚠️⚠️ ATTENZIONE CRITICA - KNOWLEDGE BASE VUOTA ⚠️⚠️⚠️

La Knowledge Base NON ha restituito documenti rilevanti per questa query.

REGOLE OBBLIGATORIE CHE DEVI SEGUIRE:
1. NON inventare NESSUNA informazione, data, articolo di legge o riferimento normativo
2. NON usare conoscenze di training per rispondere su questo argomento
3. RISPONDI SOLO con: "Non ho trovato documenti ufficiali su [argomento della query] nel database di PratikoAI."
4. Puoi suggerire all'utente di riformulare la domanda con termini diversi

⛔ RISPOSTA VIETATA: Inventare date, scadenze, o dettagli normativi non presenti nel contesto.

--- FINE AVVERTIMENTO KB VUOTA ---

"""
        # Prepend warning to kb_context
        state["kb_context"] = kb_empty_warning + (kb_context or "Nessun documento trovato.")
        state["kb_empty_warning"] = kb_empty_warning  # Also store for logging

        # DEV-242 Phase 10: DO NOT overwrite state["context"] - it contains good KB chunks!
        # The warning is stored in kb_context and kb_empty_warning for logging purposes only.
        # Overwriting context destroys the KB retrieval results that Step 40 built.

        logger.warning(
            "step64_kb_empty_warning_injected",
            is_kb_empty=is_kb_empty,
            is_kb_context_minimal=is_kb_context_minimal,
            kb_sources_count=len(kb_sources),
            kb_context_length=len(kb_context),
            user_query=user_message[:100] if user_message else "",
            request_id=state.get("request_id"),
        )

        return True

    return False


async def node_step_64(state: RAGState) -> RAGState:
    """Node wrapper for Step 64: LLM Call.

    DEV-214: Enhanced with unified JSON output parsing.
    DEV-222: Integrates LLMOrchestrator for complexity classification and cost tracking.
    DEV-226: Integrates TreeOfThoughtsReasoner for complex/multi_domain queries.
    DEV-238: Integrates detailed reasoning trace logging with mandatory context fields.
    DEV-242: Integrates KB-empty detection and hallucination prevention.
    """
    # DEV-238: Start timing for reasoning trace logging
    step_start_time = time.perf_counter()

    rag_step_log(STEP, "enter", provider=state.get("provider", {}).get("selected"))
    with rag_step_timer(STEP):
        # DEV-242 FIX: KB-empty check now runs in Step 40 (before prompt construction)
        # Only run here as fallback if Step 40 didn't set kb_was_empty
        kb_empty = state.get("kb_was_empty", False)
        if not kb_empty and "kb_was_empty" not in state:
            # Fallback: run check here if Step 40 path wasn't executed
            kb_empty = _check_kb_empty_and_inject_warning(state)
            state["kb_was_empty"] = kb_empty

        # DEV-222: Classify query complexity before LLM call
        complexity, complexity_context = await _classify_query_complexity(state)

        # Store complexity in state for analytics and model selection
        state["query_complexity"] = complexity
        state["complexity_context"] = complexity_context

        logger.info(
            "step64_pre_llm_complexity",
            complexity=complexity,
            kb_empty=kb_empty,
            request_id=state.get("request_id"),
        )

        # DEV-226: Use Tree of Thoughts for complex/multi_domain queries
        tot_used = False
        if complexity in ("complex", "multi_domain"):
            try:
                tot_result = await _use_tree_of_thoughts(state, complexity)

                # Store ToT results in state
                state["reasoning_type"] = "tot"
                state["reasoning_trace"] = tot_result.reasoning_trace
                state["tot_analysis"] = {
                    "selected_hypothesis_id": tot_result.selected_hypothesis.id,
                    "selected_confidence": tot_result.selected_hypothesis.confidence,
                    "source_weight_score": tot_result.selected_hypothesis.source_weight_score,
                    "total_hypotheses": len(tot_result.all_hypotheses),
                    "complexity_used": tot_result.complexity_used,
                    "latency_ms": tot_result.total_latency_ms,
                }
                tot_used = True

                # DEV-238: Log each ToT hypothesis evaluation with mandatory context
                for hypothesis in tot_result.all_hypotheses:
                    is_selected = hypothesis.id == tot_result.selected_hypothesis.id
                    log_tot_hypothesis_evaluated(
                        state=state,
                        hypothesis_id=hypothesis.id,
                        probability=hypothesis.confidence,
                        source_weight_score=hypothesis.source_weight_score,
                        selected=is_selected,
                    )

                logger.info(
                    "step64_tot_results_stored",
                    hypothesis_id=tot_result.selected_hypothesis.id,
                    confidence=tot_result.selected_hypothesis.confidence,
                    request_id=state.get("request_id"),
                )

            except Exception as e:
                # DEV-226: Fall back to CoT on ToT failure
                logger.warning(
                    "step64_tot_failed_fallback_to_cot",
                    error=str(e),
                    error_type=type(e).__name__,
                    complexity=complexity,
                    request_id=state.get("request_id"),
                )
                # Mark as CoT fallback
                state["reasoning_type"] = "cot"
                state["tot_fallback"] = True
                state["tot_error"] = str(e)

        # DEV-245: Use LLMOrchestrator.generate_response() for proper model routing
        # This ensures gpt-4o is used instead of gpt-4o-mini from env default
        from app.services.llm_orchestrator import QueryComplexity as QC

        # Extract user query from messages
        user_message = state.get("user_message", "")
        if not user_message:
            messages_list = state.get("messages", [])
            for msg in reversed(messages_list):
                if isinstance(msg, dict) and msg.get("role") == "user":
                    user_message = msg.get("content", "")
                    break

        # Get KB context and metadata
        kb_context = state.get("context", "") or state.get("kb_context", "")
        kb_sources_metadata = state.get("kb_sources_metadata", [])

        # Convert complexity string to enum
        complexity_map = {
            "simple": QC.SIMPLE,
            "complex": QC.COMPLEX,
            "multi_domain": QC.MULTI_DOMAIN,
        }
        complexity_enum = complexity_map.get(complexity, QC.SIMPLE)

        try:
            # Use LLMOrchestrator for response generation with proper model
            # DEV-245 FIX: Pass web_sources_metadata for Parallel Hybrid RAG
            orchestrator = get_llm_orchestrator()
            unified_response = await orchestrator.generate_response(
                query=user_message,
                kb_context=kb_context,
                kb_sources_metadata=kb_sources_metadata,
                complexity=complexity_enum,
                conversation_history=state.get("messages", []),
                web_sources_metadata=state.get("web_sources_metadata", []),
            )

            # Map UnifiedResponse to expected result format
            res = {
                "llm_call_successful": True,
                "response": {"content": unified_response.answer},
                "llm_response": {"content": unified_response.answer},
                "model": unified_response.model_used,
                "provider": "openai",
                "tokens_used": {
                    "input": unified_response.tokens_input,
                    "output": unified_response.tokens_output,
                },
                "cost_estimate": unified_response.cost_euros,
                "response_time_ms": unified_response.latency_ms,
            }

            # Store sources from orchestrator
            if unified_response.sources_cited:
                state["sources_cited"] = unified_response.sources_cited

            logger.info(
                "step64_orchestrator_response",
                model=unified_response.model_used,
                complexity=complexity,
                tokens_input=unified_response.tokens_input,
                tokens_output=unified_response.tokens_output,
                cost_euros=unified_response.cost_euros,
                latency_ms=unified_response.latency_ms,
                request_id=state.get("request_id"),
            )

        except Exception as orchestrator_error:
            # DEV-245: Fallback to old path if orchestrator fails
            logger.warning(
                "step64_orchestrator_fallback",
                error=str(orchestrator_error),
                error_type=type(orchestrator_error).__name__,
                request_id=state.get("request_id"),
            )
            # Fall back to old orchestrator call
            ctx = dict(state)
            ctx["query_complexity"] = complexity
            ctx["tot_used"] = tot_used
            res = await step_64__llmcall(messages=state.get("messages"), ctx=ctx)

        # Map orchestrator outputs to canonical state keys (additive)
        llm = ns(state, "llm")
        decisions = state.setdefault("decisions", {})

        # DEV-007 PII: Get deanonymization map for document content restoration
        privacy = state.get("privacy") or {}
        deanonymization_map = privacy.get("document_deanonymization_map", {})

        # DEV-007 DIAGNOSTIC: Log deanonymization_map state for debugging PII placeholder issues
        logger.info(
            "step64_deanonymization_map_check",
            has_map=bool(deanonymization_map),
            map_size=len(deanonymization_map) if deanonymization_map else 0,
            privacy_state_exists=bool(privacy),
            privacy_keys=list(privacy.keys()) if privacy else [],
            placeholder_samples=list(deanonymization_map.keys())[:3] if deanonymization_map else [],
            request_id=state.get("request_id"),
            session_id=state.get("session_id"),
        )

        # Map fields with name translation if needed
        if "llm_request" in res:
            llm["request"] = res["llm_request"]

        # Always set llm["success"]
        if "error" in res and res["error"] not in ["", None]:
            llm["error"] = res["error"]
            llm["success"] = False
            # Track error type for retryability check
            if "error_type" in res:
                llm["error_type"] = res["error_type"]
        elif "llm_call_successful" in res:
            # Explicitly check for llm_call_successful from orchestrator
            llm["success"] = res["llm_call_successful"]
            if "response" in res or "llm_response" in res:
                response = res.get("response", res.get("llm_response"))
                llm["response"] = response
                mirror(state, "llm_response", response)

                # FIX: Add assistant message to messages list for checkpointer persistence
                # Handle both LLMResponse objects and dict formats
                content = None
                if isinstance(response, dict):
                    content = response.get("content")
                elif hasattr(response, "content"):
                    content = response.content

                if content:
                    # DEV-007 PII: De-anonymize response before returning to user
                    if deanonymization_map:
                        content = _deanonymize_response(content, deanonymization_map)

                        logger.info(
                            "document_pii_deanonymization_applied",
                            placeholders_restored=len(deanonymization_map),
                            request_id=state.get("request_id"),
                        )
                        # Clear the map after use (data minimization)
                        privacy["document_deanonymization_map"] = {}
                        state["privacy"] = privacy

                    # DEV-214: Process unified JSON response
                    display_content = _process_unified_response(content, state)

                    # FIX: Update llm["response"] for streaming to use processed content
                    if isinstance(response, dict):
                        response["content"] = display_content
                    else:
                        # For LLMResponse objects, create updated dict
                        llm["response"] = {
                            "content": display_content,
                            "model": getattr(response, "model", None),
                            "usage": getattr(response, "usage", None),
                        }
                    mirror(state, "llm_response", llm["response"])

                    state.setdefault("messages", []).append({"role": "assistant", "content": display_content})

        elif "response" in res or "llm_response" in res:
            response = res.get("response", res.get("llm_response"))
            llm["response"] = response
            llm["success"] = True
            mirror(state, "llm_response", response)

            # FIX: Add assistant message to messages list for checkpointer persistence
            # Handle both LLMResponse objects and dict formats
            content = None
            if isinstance(response, dict):
                content = response.get("content")
            elif hasattr(response, "content"):
                content = response.content

            if content:
                # DEV-007 PII: De-anonymize response before returning to user
                if deanonymization_map:
                    content = _deanonymize_response(content, deanonymization_map)

                    logger.info(
                        "document_pii_deanonymization_applied",
                        placeholders_restored=len(deanonymization_map),
                        request_id=state.get("request_id"),
                    )
                    # Clear the map after use (data minimization)
                    privacy["document_deanonymization_map"] = {}
                    state["privacy"] = privacy

                # DEV-214: Process unified JSON response
                display_content = _process_unified_response(content, state)

                # FIX: Update llm["response"] for streaming to use processed content
                if isinstance(response, dict):
                    response["content"] = display_content
                else:
                    # For LLMResponse objects, create updated dict
                    llm["response"] = {
                        "content": display_content,
                        "model": getattr(response, "model", None),
                        "usage": getattr(response, "usage", None),
                    }
                mirror(state, "llm_response", llm["response"])

                state.setdefault("messages", []).append({"role": "assistant", "content": display_content})

        elif "llm_success" in res:
            llm["success"] = res["llm_success"]
        else:
            llm.setdefault("success", False)

        # Merge any extra structured data
        _merge(llm, res.get("llm_extra", {}))
        _merge(decisions, res.get("decisions", {}))

        # DEV-222: Track LLM costs in state
        tokens_used = res.get("tokens_used")
        cost_estimate = res.get("cost_estimate")

        if tokens_used is not None:
            llm["tokens_used"] = tokens_used
        if cost_estimate is not None:
            llm["cost_estimate"] = cost_estimate

        # Store model used for cost analytics
        model_used = res.get("model")
        if model_used:
            llm["model_used"] = model_used
            state["model_used"] = model_used

        # Log cost tracking info
        logger.info(
            "step64_cost_tracking",
            complexity=complexity,
            model_used=model_used,
            tokens_used=tokens_used,
            cost_estimate=cost_estimate,
            request_id=state.get("request_id"),
        )

    # DEV-238: Log reasoning trace with all mandatory context fields
    step_elapsed_ms = (time.perf_counter() - step_start_time) * 1000
    if state.get("reasoning_trace") is not None:
        log_reasoning_trace_recorded(state, elapsed_ms=step_elapsed_ms)

    rag_step_log(
        STEP,
        "exit",
        llm_success=llm.get("success"),
        reasoning_type=state.get("reasoning_type"),
        query_complexity=state.get("query_complexity"),
        model_used=state.get("model_used"),
    )
    return state
