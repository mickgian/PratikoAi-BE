"""Node wrapper for Step 64: LLM Call.

DEV-196: Integrates PremiumModelSelector, SynthesisPromptBuilder, and
VerdettoOperativoParser for TECHNICAL_RESEARCH route queries.
"""

from typing import TYPE_CHECKING, Any, Dict

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
    from app.services.premium_model_selector import PremiumModelSelector
    from app.services.synthesis_prompt_builder import SynthesisPromptBuilder
    from app.services.verdetto_parser import VerdettoOperativoParser

STEP = 64

# Routes that should use premium model and verdetto parsing
SYNTHESIS_ROUTES = {"technical_research"}


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


def _parse_verdetto(content: str, state: RAGState) -> dict[str, Any] | None:
    """Parse Verdetto Operativo from LLM response for TECHNICAL_RESEARCH.

    DEV-196: Uses VerdettoOperativoParser to extract structured verdetto
    sections from synthesis response.

    Args:
        content: LLM response content
        state: Current RAG state with routing decision

    Returns:
        Parsed synthesis dict with verdetto, or None if not applicable
    """
    routing = state.get("routing_decision", {})
    route = routing.get("route", "")

    # Only parse verdetto for synthesis routes
    if route not in SYNTHESIS_ROUTES:
        return None

    if not content:
        return None

    try:
        # Lazy import
        from app.services.verdetto_parser import VerdettoOperativoParser

        parser = VerdettoOperativoParser()
        result = parser.parse(content)

        # Convert to serializable dict
        parsed = {
            "answer_text": result.answer_text,
            "raw_response": result.raw_response,
            "parse_successful": result.parse_successful,
        }

        if result.verdetto:
            parsed["verdetto"] = {
                "azione_consigliata": result.verdetto.azione_consigliata,
                "analisi_rischio": result.verdetto.analisi_rischio,
                "scadenza": result.verdetto.scadenza,
                "documentazione": result.verdetto.documentazione,
                "indice_fonti": [
                    {
                        "numero": f.numero,
                        "data": f.data,
                        "ente": f.ente,
                        "tipo": f.tipo,
                        "riferimento": f.riferimento,
                    }
                    for f in result.verdetto.indice_fonti
                ],
            }

        logger.info(
            "step64_verdetto_parsed",
            has_verdetto=result.verdetto is not None,
            parse_successful=result.parse_successful,
            request_id=state.get("request_id"),
        )

        return parsed

    except Exception as e:
        logger.warning(
            "step64_verdetto_parse_error",
            error=str(e),
            request_id=state.get("request_id"),
        )
        return None


async def node_step_64(state: RAGState) -> RAGState:
    """Node wrapper for Step 64: LLM Call."""
    rag_step_log(STEP, "enter", provider=state.get("provider", {}).get("selected"))
    with rag_step_timer(STEP):
        # Call orchestrator with business inputs only
        res = await step_64__llmcall(messages=state.get("messages"), ctx=dict(state))

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

                        # FIX: Update llm["response"] for streaming to use de-anonymized content
                        if isinstance(response, dict):
                            response["content"] = content
                        else:
                            # For LLMResponse objects, create updated dict
                            llm["response"] = {
                                "content": content,
                                "model": getattr(response, "model", None),
                                "usage": getattr(response, "usage", None),
                            }
                        mirror(state, "llm_response", llm["response"])

                        logger.info(
                            "document_pii_deanonymization_applied",
                            placeholders_restored=len(deanonymization_map),
                            request_id=state.get("request_id"),
                        )
                        # Clear the map after use (data minimization)
                        privacy["document_deanonymization_map"] = {}
                        state["privacy"] = privacy
                    state.setdefault("messages", []).append({"role": "assistant", "content": content})

                    # DEV-196: Parse Verdetto Operativo for TECHNICAL_RESEARCH
                    parsed_synthesis = _parse_verdetto(content, state)
                    if parsed_synthesis:
                        state["parsed_synthesis"] = parsed_synthesis
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

                    # FIX: Update llm["response"] for streaming to use de-anonymized content
                    if isinstance(response, dict):
                        response["content"] = content
                    else:
                        # For LLMResponse objects, create updated dict
                        llm["response"] = {
                            "content": content,
                            "model": getattr(response, "model", None),
                            "usage": getattr(response, "usage", None),
                        }
                    mirror(state, "llm_response", llm["response"])

                    logger.info(
                        "document_pii_deanonymization_applied",
                        placeholders_restored=len(deanonymization_map),
                        request_id=state.get("request_id"),
                    )
                    # Clear the map after use (data minimization)
                    privacy["document_deanonymization_map"] = {}
                    state["privacy"] = privacy
                state.setdefault("messages", []).append({"role": "assistant", "content": content})

                # DEV-196: Parse Verdetto Operativo for TECHNICAL_RESEARCH
                parsed_synthesis = _parse_verdetto(content, state)
                if parsed_synthesis:
                    state["parsed_synthesis"] = parsed_synthesis
        elif "llm_success" in res:
            llm["success"] = res["llm_success"]
        else:
            llm.setdefault("success", False)

        # Merge any extra structured data
        _merge(llm, res.get("llm_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", llm_success=llm.get("success"))
    return state
