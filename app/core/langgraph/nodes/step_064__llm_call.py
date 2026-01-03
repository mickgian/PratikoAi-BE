"""Node wrapper for Step 64: LLM Call.

DEV-196: Integrates PremiumModelSelector, SynthesisPromptBuilder, and
VerdettoOperativoParser for TECHNICAL_RESEARCH route queries.

DEV-214: Enhanced with unified JSON output parsing for reasoning traces,
sources with hierarchy, and suggested actions.

DEV-222: Integrates LLMOrchestrator for complexity-based model routing
and cost tracking.
"""

import json
import re
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

# DEV-196: Lazy imports to avoid database connection during module load
if TYPE_CHECKING:
    from app.services.llm_orchestrator import LLMOrchestrator
    from app.services.premium_model_selector import PremiumModelSelector
    from app.services.synthesis_prompt_builder import SynthesisPromptBuilder

STEP = 64

# Routes that should use premium model and verdetto parsing
SYNTHESIS_ROUTES = {"technical_research"}

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

    DEV-214: Extracts structured response with reasoning, answer, sources, actions.

    Args:
        content: LLM response content

    Returns:
        Parsed dict with reasoning, answer, sources, actions
        None if parsing fails
    """
    if not content:
        return None

    parsed = _extract_json_from_content(content)

    if parsed is None:
        return None

    # Validate that it has at least one expected field
    expected_fields = {"reasoning", "answer", "sources_cited", "suggested_actions"}
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
        "suggested_actions": [],
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

    DEV-214: Extracts and stores reasoning, sources, and actions from JSON response.
    Falls back to text extraction if JSON parsing fails.

    Args:
        content: LLM response content
        state: RAG state to update with parsed fields

    Returns:
        The answer text to use for display (from JSON or raw content)
    """
    # Try unified JSON parsing
    parsed = _parse_unified_response(content)

    if parsed:
        # Store reasoning trace
        state["reasoning_type"] = "cot"
        state["reasoning_trace"] = parsed.get("reasoning")

        # Store suggested actions for Step 100 validation
        state["suggested_actions"] = parsed.get("suggested_actions", [])
        state["actions_source"] = "unified_llm"

        # Store and validate sources with hierarchy
        sources = parsed.get("sources_cited", [])
        state["sources_cited"] = _apply_source_hierarchy(sources)

        # Use answer for display
        answer = parsed.get("answer", content)

        logger.info(
            "step64_unified_response_parsed",
            has_reasoning=parsed.get("reasoning") is not None,
            sources_count=len(sources),
            actions_count=len(parsed.get("suggested_actions", [])),
            request_id=state.get("request_id"),
        )

        return answer
    else:
        # Fallback: mark for action regeneration
        state["actions_source"] = "fallback_needed"
        state["reasoning_type"] = None
        state["reasoning_trace"] = None
        state["sources_cited"] = []
        state["suggested_actions"] = []

        logger.warning(
            "step64_json_parse_failed",
            content_length=len(content) if content else 0,
            content_preview=content[:200] if content else "",
            request_id=state.get("request_id"),
        )

        return content


async def node_step_64(state: RAGState) -> RAGState:
    """Node wrapper for Step 64: LLM Call.

    DEV-214: Enhanced with unified JSON output parsing.
    DEV-222: Integrates LLMOrchestrator for complexity classification and cost tracking.
    """
    rag_step_log(STEP, "enter", provider=state.get("provider", {}).get("selected"))
    with rag_step_timer(STEP):
        # DEV-222: Classify query complexity before LLM call
        complexity, complexity_context = await _classify_query_complexity(state)

        # Store complexity in state for analytics and model selection
        state["query_complexity"] = complexity
        state["complexity_context"] = complexity_context

        logger.info(
            "step64_pre_llm_complexity",
            complexity=complexity,
            request_id=state.get("request_id"),
        )

        # Call orchestrator with business inputs only
        # DEV-222: Include complexity in context for model routing
        ctx = dict(state)
        ctx["query_complexity"] = complexity
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

    rag_step_log(
        STEP,
        "exit",
        llm_success=llm.get("success"),
        actions_source=state.get("actions_source"),
        reasoning_type=state.get("reasoning_type"),
        query_complexity=state.get("query_complexity"),
        model_used=state.get("model_used"),
    )
    return state
