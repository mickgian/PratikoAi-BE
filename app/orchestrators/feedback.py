# AUTO-GENERATED ORCHESTRATOR STUBS (safe to edit below stubs)
# These functions are the functional *nodes* that mirror the Mermaid diagram.
# Implement thin coordination here (call services/factories), not core business logic.

import time
from contextlib import nullcontext
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from app.core.logging import logger

try:
    from app.observability.rag_logging import rag_step_log, rag_step_timer
except Exception:  # pragma: no cover

    def rag_step_log(**kwargs):
        return None

    def rag_step_timer(*args, **kwargs):
        return nullcontext()


async def _display_feedback_ui_options(ctx: dict[str, Any]) -> dict[str, Any]:
    """Helper function to display feedback UI options (Correct, Incomplete, Wrong).

    Handles UI element generation, configuration, and user-specific options.
    """
    from datetime import datetime, timezone

    try:
        # Extract response context
        response_id = ctx.get("response_id")
        feedback_enabled = ctx.get("feedback_enabled", True)

        # Check if feedback display should be disabled
        if not feedback_enabled:
            return {
                "feedback_ui_displayed": False,
                "feedback_enabled": False,
                "feedback_disabled_reason": "feedback_disabled",
            }

        # Check if response ID is available (required for feedback)
        if not response_id:
            return {
                "feedback_ui_displayed": False,
                "feedback_enabled": True,
                "feedback_disabled_reason": "missing_response_id",
            }

        # Determine user type and capabilities
        user_id = ctx.get("user_id")
        is_anonymous = user_id is None
        is_expert = ctx.get("expert_user", False)
        expert_trust_score = ctx.get("expert_trust_score", 0.0)

        # Configure feedback options based on user type
        if is_anonymous and not ctx.get("anonymous_feedback_allowed", True):  # Default allow anonymous
            feedback_options = []
            feedback_ui_displayed = False
            feedback_disabled_reason = "anonymous_user_not_allowed"
        elif is_anonymous and ctx.get("simplified_anonymous_feedback", False):
            # Simplified options for anonymous users (only when explicitly requested)
            feedback_options = ["correct", "incorrect"]
            feedback_ui_displayed = True
            feedback_disabled_reason = None
        else:
            # Full options for all users (including anonymous by default)
            feedback_options = ["correct", "incomplete", "wrong"]
            feedback_ui_displayed = True
            feedback_disabled_reason = None

        # Build UI configuration
        ui_config = ctx.get("ui_config", {})
        ui_config.setdefault("style", "standard")
        ui_config.setdefault("show_labels", True)
        ui_config.setdefault("show_icons", True)
        ui_config.setdefault("position", "bottom")

        # Build result with UI elements
        result = {
            "feedback_ui_displayed": feedback_ui_displayed,
            "feedback_options": feedback_options,
            "feedback_enabled": True,
            "ui_element_type": "feedback_buttons",
            "ui_config": ui_config,
            "ui_display_timestamp": datetime.now(UTC).isoformat(),
            "anonymous_user": is_anonymous,
            "response_id": response_id,
        }

        # Add expert-specific enhancements
        if is_expert:
            result.update(
                {
                    "expert_mode": True,
                    "expert_trust_score": expert_trust_score,
                    "expert_feedback_available": True,
                    "feedback_options_enhanced": {
                        "confidence_rating": True,
                        "improvement_suggestions": True,
                        "regulatory_references": True,
                    },
                }
            )
        else:
            # Preserve existing expert_feedback_available if already set in context
            if "expert_feedback_available" not in result:
                result["expert_feedback_available"] = ctx.get("expert_feedback_available", False)

        # Add Italian feedback categories if applicable
        locale = ctx.get("locale", "en_US")
        if locale.startswith("it") or ctx.get("italian_categories_available"):
            result.update(
                {
                    "italian_categories_available": True,
                    "italian_feedback_categories": {
                        "normativa_obsoleta": "La normativa citata è obsoleta o non aggiornata",
                        "interpretazione_errata": "L'interpretazione della normativa è errata",
                        "caso_mancante": "Manca la trattazione di casi specifici",
                        "calcolo_sbagliato": "I calcoli o le formule sono errati",
                        "troppo_generico": "La risposta è troppo generica, serve più specificità",
                    },
                }
            )

        # Add disabled reason if applicable
        if feedback_disabled_reason:
            result["feedback_disabled_reason"] = feedback_disabled_reason

        return result

    except Exception as e:
        # Handle UI display errors gracefully
        return {
            "feedback_ui_displayed": False,
            "feedback_enabled": False,
            "feedback_disabled_reason": "ui_display_error",
            "error": str(e),
        }


async def step_113__feedback_ui(
    *, messages: list[Any] | None = None, ctx: dict[str, Any] | None = None, **kwargs
) -> Any:
    """RAG STEP 113 — FeedbackUI.show_options Correct Incomplete Wrong.

    ID: RAG.feedback.feedbackui.show.options.correct.incomplete.wrong
    Type: process | Category: feedback | Node: FeedbackUI

    Thin async orchestrator that displays feedback UI options (Correct, Incomplete, Wrong).
    Takes input from collect metrics (Step 111) and routes to feedback provided (Step 114).
    Handles UI element generation, user-specific options, and configuration.

    Incoming: Collect Usage Metrics (Step 111)
    Outgoing: User Provides Feedback? (Step 114)
    """
    from datetime import datetime, timezone

    with rag_step_timer(
        113, "RAG.feedback.feedbackui.show.options.correct.incomplete.wrong", "FeedbackUI", stage="start"
    ):
        ctx = ctx or {}

        rag_step_log(
            step=113,
            step_id="RAG.feedback.feedbackui.show.options.correct.incomplete.wrong",
            node_label="FeedbackUI",
            category="feedback",
            type="process",
            request_id=ctx.get("request_id"),
            response_id=ctx.get("response_id"),
            processing_stage="started",
        )

        # Display feedback UI options
        ui_result = await _display_feedback_ui_options(ctx)

        # Preserve all context and add UI results
        result = ctx.copy()
        result.update(ui_result)

        # Add processing metadata
        result.update(
            {
                "processing_stage": "feedback_ui_ready"
                if ui_result.get("feedback_ui_displayed")
                else "feedback_disabled"
            }
        )

        rag_step_log(
            step=113,
            step_id="RAG.feedback.feedbackui.show.options.correct.incomplete.wrong",
            node_label="FeedbackUI",
            category="feedback",
            type="process",
            request_id=ctx.get("request_id"),
            response_id=ctx.get("response_id"),
            feedback_ui_displayed=result.get("feedback_ui_displayed", False),
            feedback_options_count=len(result.get("feedback_options", [])),
            ui_element_type=result.get("ui_element_type"),
            anonymous_user=result.get("anonymous_user", False),
            expert_mode=result.get("expert_mode", False),
            processing_stage="completed",
        )

        return result


async def _evaluate_feedback_presence(ctx: dict[str, Any]) -> dict[str, Any]:
    """Helper function to evaluate if user provided feedback.

    Checks various feedback formats and determines routing decision.
    """
    from datetime import datetime, timezone

    try:
        start_time = datetime.now(UTC)

        # Check for different feedback data formats (priority order)
        feedback_provided = False
        decision_reason = "no_user_feedback"
        feedback_type = None

        # 1. Expert feedback (highest priority)
        if ctx.get("expert_feedback") and ctx.get("expert_user", False):
            expert_feedback = ctx["expert_feedback"]
            if expert_feedback.get("feedback_type"):
                feedback_provided = True
                decision_reason = "expert_feedback_present"
                feedback_type = expert_feedback["feedback_type"]

        # 2. Direct user feedback
        elif ctx.get("user_feedback"):
            user_feedback = ctx["user_feedback"]
            if user_feedback.get("feedback_type") or user_feedback.get("feedback_value"):
                feedback_provided = True
                decision_reason = "user_feedback_present"
                feedback_type = user_feedback.get("feedback_type") or user_feedback.get("feedback_value")

        # 3. FAQ/General feedback data
        elif ctx.get("feedback_data"):
            feedback_data = ctx["feedback_data"]
            # Check if feedback data contains meaningful feedback indicators
            if (
                feedback_data.get("was_helpful") is not None
                or feedback_data.get("feedback_type")
                or feedback_data.get("comments")
            ):
                feedback_provided = True
                decision_reason = "feedback_data_present"
                feedback_type = feedback_data.get("feedback_type", "general")

        # Special case: UI was not displayed, so no feedback possible
        elif ctx.get("feedback_ui_displayed") is False:
            feedback_provided = False
            decision_reason = "feedback_ui_not_displayed"

        # Determine next step based on decision
        if feedback_provided:
            next_step = "feedback_type_selected"  # Route to Step 116
        else:
            next_step = "feedback_end"  # Route to Step 115

        # Calculate decision time
        end_time = datetime.now(UTC)
        decision_time_ms = int((end_time - start_time).total_seconds() * 1000)

        # Build decision result
        decision_result = {
            "feedback_provided": feedback_provided,
            "next_step": next_step,
            "decision_reason": decision_reason,
            "decision_timestamp": end_time.isoformat(),
            "decision_time_ms": decision_time_ms,
        }

        # Add feedback type if detected
        if feedback_type:
            decision_result["feedback_type"] = feedback_type

        return decision_result

    except Exception as e:
        # Handle decision evaluation errors gracefully
        return {
            "feedback_provided": False,
            "next_step": "feedback_end",
            "decision_reason": "decision_evaluation_error",
            "decision_error": str(e),
            "decision_time_ms": 0,
        }


async def step_114__feedback_provided(
    *, messages: list[Any] | None = None, ctx: dict[str, Any] | None = None, **kwargs
) -> Any:
    """RAG STEP 114 — User provides feedback?

    ID: RAG.feedback.user.provides.feedback
    Type: decision | Category: feedback | Node: FeedbackProvided

    Decision orchestrator that determines if user provided feedback.
    Routes to Step 115 (No feedback) or Step 116 (Feedback type selected).
    Handles various feedback formats: user_feedback, expert_feedback, feedback_data.

    Incoming: FeedbackUI.show_options (Step 113)
    Outgoing: No feedback (Step 115) OR Feedback type selected (Step 116)
    """
    with rag_step_timer(114, "RAG.feedback.user.provides.feedback", "FeedbackProvided", stage="start"):
        ctx = ctx or {}

        rag_step_log(
            step=114,
            step_id="RAG.feedback.user.provides.feedback",
            node_label="FeedbackProvided",
            category="feedback",
            type="decision",
            request_id=ctx.get("request_id"),
            response_id=ctx.get("response_id"),
            processing_stage="started",
        )

        # Evaluate feedback presence and make routing decision
        decision_result = await _evaluate_feedback_presence(ctx)

        # Preserve all context and add decision results
        result = ctx.copy()
        result.update(decision_result)

        # Add processing metadata
        result.update({"processing_stage": "feedback_decision_completed"})

        rag_step_log(
            step=114,
            step_id="RAG.feedback.user.provides.feedback",
            node_label="FeedbackProvided",
            category="feedback",
            type="decision",
            request_id=ctx.get("request_id"),
            response_id=ctx.get("response_id"),
            feedback_provided=result.get("feedback_provided", False),
            decision_reason=result.get("decision_reason"),
            feedback_type=result.get("feedback_type"),
            next_step=result.get("next_step"),
            decision_time_ms=result.get("decision_time_ms", 0),
            processing_stage="completed",
        )

        return result


async def _finalize_feedback_pipeline(ctx: dict[str, Any]) -> dict[str, Any]:
    """Helper function to finalize the feedback pipeline completion.

    Handles various completion scenarios and cleanup operations.
    """
    from datetime import datetime, timezone

    try:
        start_time = datetime.now(UTC)

        # Determine completion reason based on context
        completion_reason = "no_feedback"  # Default

        # Check different completion scenarios (priority order)
        if ctx.get("golden_approval_status") == "rejected":
            completion_reason = "golden_approval_rejected"
        elif ctx.get("decision_reason") == "feedback_ui_not_displayed" or ctx.get("feedback_ui_displayed") is False:
            completion_reason = "feedback_ui_not_available"
        elif ctx.get("expert_feedback_processed"):
            completion_reason = "expert_feedback_processed"
        elif ctx.get("feedback_processing_error"):
            completion_reason = "error_recovery"
        elif ctx.get("decision_reason") == "anonymous_user_timeout":
            completion_reason = "anonymous_user_timeout"
        elif ctx.get("decision_reason") == "session_timeout":
            completion_reason = "session_timeout"

        # Calculate pipeline timing metrics
        processing_start = ctx.get("processing_start_time")
        if processing_start:
            if isinstance(processing_start, str):
                from datetime import datetime

                processing_start = datetime.fromisoformat(processing_start.replace("Z", "+00:00"))
            total_pipeline_time_ms = int((start_time - processing_start).total_seconds() * 1000)
        else:
            total_pipeline_time_ms = 0

        # Calculate completion processing time
        end_time = datetime.now(UTC)
        completion_time_ms = int((end_time - start_time).total_seconds() * 1000)

        # Build completion result
        completion_result = {
            "feedback_pipeline_completed": True,
            "completion_reason": completion_reason,
            "completion_timestamp": end_time.isoformat(),
            "completion_time_ms": completion_time_ms,
            "processing_stage": "feedback_pipeline_ended",
        }

        # Add metrics finalization
        completion_result.update({"final_metrics_collected": True, "total_pipeline_time_ms": total_pipeline_time_ms})

        # Preserve specific error details if present
        if ctx.get("error_details"):
            completion_result["error_details"] = ctx["error_details"]

        if ctx.get("rejection_reason"):
            completion_result["rejection_reason"] = ctx["rejection_reason"]

        return completion_result

    except Exception as e:
        # Handle completion processing errors gracefully
        return {
            "feedback_pipeline_completed": True,
            "completion_reason": "completion_error",
            "completion_error": str(e),
            "processing_stage": "feedback_pipeline_ended",
            "completion_time_ms": 0,
        }


async def step_115__feedback_end(
    *, messages: list[Any] | None = None, ctx: dict[str, Any] | None = None, **kwargs
) -> Any:
    """RAG STEP 115 — No feedback.

    ID: RAG.feedback.no.feedback
    Type: process | Category: feedback | Node: FeedbackEnd

    Process orchestrator that handles feedback pipeline completion.
    Finalizes the no-feedback scenario and performs cleanup operations.
    Can be reached from Step 114 (no feedback) or Golden approval rejection.

    Incoming: User provides feedback? (Step 114) OR Golden approval rejected
    Outgoing: End of feedback flow (terminal node)
    """
    with rag_step_timer(115, "RAG.feedback.no.feedback", "FeedbackEnd", stage="start"):
        ctx = ctx or {}

        rag_step_log(
            step=115,
            step_id="RAG.feedback.no.feedback",
            node_label="FeedbackEnd",
            category="feedback",
            type="process",
            request_id=ctx.get("request_id"),
            response_id=ctx.get("response_id"),
            processing_stage="started",
        )

        # Finalize feedback pipeline completion
        completion_result = await _finalize_feedback_pipeline(ctx)

        # Preserve all context and add completion results
        result = ctx.copy()
        result.update(completion_result)

        rag_step_log(
            step=115,
            step_id="RAG.feedback.no.feedback",
            node_label="FeedbackEnd",
            category="feedback",
            type="process",
            request_id=ctx.get("request_id"),
            response_id=ctx.get("response_id"),
            feedback_pipeline_completed=result.get("feedback_pipeline_completed", False),
            completion_reason=result.get("completion_reason"),
            completion_time_ms=result.get("completion_time_ms", 0),
            total_pipeline_time_ms=result.get("total_pipeline_time_ms", 0),
            session_duration_ms=ctx.get("session_duration_ms"),
            processing_stage="completed",
        )

        return result


async def _determine_feedback_routing(ctx: dict[str, Any]) -> dict[str, Any]:
    """Helper function to determine feedback routing based on context.

    Routes feedback to appropriate processing endpoints based on feedback type and context.
    """
    from datetime import datetime, timezone

    try:
        start_time = datetime.now(UTC)

        # Default routing decision
        routing_decision = "expert_feedback"
        next_step = "expert_feedback_collector"  # Step 119
        routing_reason = "default_routing"

        # Priority 1: Expert user/feedback (highest priority)
        if ctx.get("expert_user") and ctx.get("expert_feedback"):
            routing_decision = "expert_feedback"
            next_step = "expert_feedback_collector"  # Step 119
            routing_reason = "expert_user_priority"

        # Priority 2: Explicit feedback type
        elif ctx.get("feedback_type") == "faq":
            routing_decision = "faq_feedback"
            next_step = "faq_feedback_endpoint"  # Step 117
            routing_reason = "feedback_type_faq"

        elif ctx.get("feedback_type") == "knowledge":
            routing_decision = "knowledge_feedback"
            next_step = "knowledge_feedback_endpoint"  # Step 118
            routing_reason = "feedback_type_knowledge"

        elif ctx.get("feedback_type") == "expert":
            routing_decision = "expert_feedback"
            next_step = "expert_feedback_collector"  # Step 119
            routing_reason = "feedback_type_expert"

        # Priority 3: Contextual detection
        elif ctx.get("expert_user"):
            routing_decision = "expert_feedback"
            next_step = "expert_feedback_collector"  # Step 119
            routing_reason = "expert_user_detected"

        elif ctx.get("golden_response") or ctx.get("golden_match_id"):
            routing_decision = "faq_feedback"
            next_step = "faq_feedback_endpoint"  # Step 117
            routing_reason = "golden_response_detected"

        elif ctx.get("kb_context") or ctx.get("kb_doc_id"):
            routing_decision = "knowledge_feedback"
            next_step = "knowledge_feedback_endpoint"  # Step 118
            routing_reason = "kb_context_detected"

        # Handle invalid/unknown feedback types
        elif ctx.get("feedback_type") and ctx["feedback_type"] not in ["faq", "knowledge", "expert"]:
            routing_decision = "expert_feedback"
            next_step = "expert_feedback_collector"  # Step 119
            routing_reason = "invalid_type_fallback"

        # Calculate routing time
        end_time = datetime.now(UTC)
        routing_time_ms = int((end_time - start_time).total_seconds() * 1000)

        # Build routing result
        routing_result = {
            "feedback_routing_decision": routing_decision,
            "next_step": next_step,
            "routing_reason": routing_reason,
            "routing_timestamp": end_time.isoformat(),
            "routing_time_ms": routing_time_ms,
        }

        return routing_result

    except Exception as e:
        # Handle routing evaluation errors gracefully
        return {
            "feedback_routing_decision": "expert_feedback",
            "next_step": "expert_feedback_collector",
            "routing_reason": "routing_error_fallback",
            "routing_error": str(e),
            "routing_time_ms": 0,
        }


async def step_116__feedback_type_sel(
    *, messages: list[Any] | None = None, ctx: dict[str, Any] | None = None, **kwargs
) -> Any:
    """RAG STEP 116 — Feedback type selected.

    ID: RAG.feedback.feedback.type.selected
    Type: process | Category: feedback | Node: FeedbackTypeSel

    Process orchestrator that routes feedback to appropriate processing endpoints.
    Routes to Step 117 (FAQ), Step 118 (KB), or Step 119 (Expert) based on feedback type.
    Handles priority-based routing with expert feedback taking precedence.

    Incoming: User provides feedback? (Step 114) - Yes path
    Outgoing: FAQ feedback (Step 117) OR KB feedback (Step 118) OR Expert feedback (Step 119)
    """
    with rag_step_timer(116, "RAG.feedback.feedback.type.selected", "FeedbackTypeSel", stage="start"):
        ctx = ctx or {}

        rag_step_log(
            step=116,
            step_id="RAG.feedback.feedback.type.selected",
            node_label="FeedbackTypeSel",
            category="feedback",
            type="process",
            request_id=ctx.get("request_id"),
            response_id=ctx.get("response_id"),
            processing_stage="started",
        )

        # Determine feedback routing based on context
        routing_result = await _determine_feedback_routing(ctx)

        # Preserve all context and add routing results
        result = ctx.copy()
        result.update(routing_result)

        # Add processing metadata
        result.update({"processing_stage": "feedback_routing_completed"})

        rag_step_log(
            step=116,
            step_id="RAG.feedback.feedback.type.selected",
            node_label="FeedbackTypeSel",
            category="feedback",
            type="process",
            request_id=ctx.get("request_id"),
            response_id=ctx.get("response_id"),
            routing_decision=result.get("feedback_routing_decision"),
            routing_reason=result.get("routing_reason"),
            next_step=result.get("next_step"),
            routing_time_ms=result.get("routing_time_ms", 0),
            processing_stage="completed",
        )

        return result


async def _process_feedback_rejection(ctx: dict[str, Any]) -> dict[str, Any]:
    """Helper function to process feedback rejection and generate rejection metadata.

    Args:
        ctx: Context containing trust validation data and expert feedback

    Returns:
        Dict containing rejection processing results and metadata
    """
    from datetime import datetime, timezone

    # Initialize rejection result
    rejection_result = {
        "rejection_timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "feedback_rejected": True,
        "expert_feedback_outcome": "rejected",
        "pipeline_terminated": True,
        "termination_reason": "expert_feedback_rejected",
        "error": None,
    }

    # Extract trust validation data
    expert_validation = ctx.get("expert_validation", {})
    expert_feedback = ctx.get("expert_feedback", {})
    trust_score_decision = ctx.get("trust_score_decision")
    trust_score = expert_validation.get("trust_score")

    # Validate context data availability
    if not expert_validation or trust_score_decision is None:
        rejection_result.update(
            {
                "rejection_reason": "context_validation_error",
                "error": "missing_trust_validation_data",
                "trust_score": trust_score or 0.0,
            }
        )
        return rejection_result

    # Process rejection based on trust score evaluation
    if trust_score_decision is False and trust_score is not None:
        # Standard rejection due to insufficient trust score
        rejection_result.update(
            {
                "rejection_reason": "insufficient_trust_score",
                "trust_score": trust_score,
                "threshold_met": False,
                "feedback_type_processed": expert_feedback.get("feedback_type", "unknown"),
            }
        )
    else:
        # Context validation error - malformed data
        rejection_result.update(
            {
                "rejection_reason": "context_validation_error",
                "trust_score": trust_score or 0.0,
                "error": "invalid_trust_decision_data",
            }
        )

    return rejection_result


async def step_122__feedback_rejected(
    *, messages: list[Any] | None = None, ctx: dict[str, Any] | None = None, **kwargs
) -> Any:
    """RAG STEP 122 — Feedback rejected
    ID: RAG.feedback.feedback.rejected
    Type: error | Category: feedback | Node: FeedbackRejected

    Error orchestrator that handles rejection of expert feedback due to insufficient trust scores
    from Step 121 (TrustScoreOK). Processes feedback rejection, logs rejection reasons, and
    terminates the feedback pipeline. Implements thin orchestration pattern with no business
    logic, focusing on rejection coordination and outcome tracking per Mermaid diagram.
    """
    with rag_step_timer(122, "RAG.feedback.feedback.rejected", "FeedbackRejected", stage="start"):
        rag_step_log(
            step=122,
            step_id="RAG.feedback.feedback.rejected",
            node_label="FeedbackRejected",
            category="feedback",
            type="error",
            processing_stage="started",
        )

        # Extract context parameters
        context = ctx or {}
        request_id = kwargs.get("request_id") or context.get("request_id", "unknown")

        try:
            # Process feedback rejection using helper function
            rejection_data = await _process_feedback_rejection(context)

            # Preserve all context data while adding rejection metadata
            result = {**context}
            result.update(rejection_data)
            result["request_id"] = request_id

            # Log rejection details
            rag_step_log(
                step=122,
                step_id="RAG.feedback.feedback.rejected",
                node_label="FeedbackRejected",
                category="feedback",
                type="error",
                feedback_rejected=rejection_data["feedback_rejected"],
                rejection_reason=rejection_data["rejection_reason"],
                trust_score=rejection_data.get("trust_score"),
                expert_feedback_outcome=rejection_data["expert_feedback_outcome"],
                pipeline_terminated=rejection_data["pipeline_terminated"],
                request_id=request_id,
                processing_stage="completed",
            )

            return result

        except Exception as e:
            # Handle unexpected errors gracefully
            error_result = {**context}
            from datetime import datetime, timezone

            error_result.update(
                {
                    "feedback_rejected": True,
                    "rejection_reason": "processing_error",
                    "expert_feedback_outcome": "rejected",
                    "pipeline_terminated": True,
                    "termination_reason": "error_during_rejection_processing",
                    "error": f"rejection_processing_error: {str(e)}",
                    "rejection_timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                    "request_id": request_id,
                }
            )

            rag_step_log(
                step=122,
                step_id="RAG.feedback.feedback.rejected",
                node_label="FeedbackRejected",
                category="feedback",
                type="error",
                error=str(e),
                feedback_rejected=True,
                rejection_reason="processing_error",
                request_id=request_id,
                processing_stage="error",
            )

            return error_result


async def step_123__create_feedback_rec(
    *, messages: list[Any] | None = None, ctx: dict[str, Any] | None = None, **kwargs
) -> Any:
    """RAG STEP 123 — Create ExpertFeedback record
    ID: RAG.feedback.create.expertfeedback.record
    Type: process | Category: feedback | Node: CreateFeedbackRec

    Process orchestrator that creates ExpertFeedback records for validated experts.
    Receives input from Step 121 (TrustScoreOK) when trust score >= 0.7,
    coordinates feedback record creation using ExpertFeedbackCollector service,
    and routes to Step 124 (UpdateExpertMetrics).

    Implements thin orchestration pattern with no business logic,
    focusing on service coordination and context preservation.
    """
    start_time = time.time()

    with rag_step_timer(123, "RAG.feedback.create.expertfeedback.record", "CreateFeedbackRec", stage="start"):
        rag_step_log(
            step=123,
            step_id="RAG.feedback.create.expertfeedback.record",
            node_label="CreateFeedbackRec",
            category="feedback",
            type="process",
            processing_stage="started",
        )

        try:
            # Use helper function to create feedback record
            result = await _create_expert_feedback_record(ctx or {})

            rag_step_log(
                step=123,
                step_id="RAG.feedback.create.expertfeedback.record",
                node_label="CreateFeedbackRec",
                processing_stage="completed",
                attrs={
                    "success": result.get("success", False),
                    "feedback_id": result.get("feedback_id"),
                    "expert_trust_score": result.get("expert_trust_score"),
                    "processing_time_ms": result.get("processing_metadata", {}).get("step_123_duration_ms"),
                },
            )

            return result

        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            logger.error(f"RAG STEP 123 failed: {e}")

            # Return error result with preserved context
            error_result = await _handle_feedback_creation_error(ctx or {}, str(e), processing_time)

            rag_step_log(
                step=123,
                step_id="RAG.feedback.create.expertfeedback.record",
                node_label="CreateFeedbackRec",
                processing_stage="error",
                attrs={
                    "error_type": error_result.get("error_type"),
                    "error_message": error_result.get("error_message"),
                    "processing_time_ms": processing_time,
                },
            )

            return error_result


async def _create_expert_feedback_record(ctx: dict[str, Any]) -> dict[str, Any]:
    """Helper function to create expert feedback record using ExpertFeedbackCollector service.
    Handles expert feedback collection and preparation for Step 124.
    """
    start_time = time.time()

    try:
        # Validate required context data from Step 121
        if not ctx.get("query_id") or not ctx.get("expert_id"):
            raise ValueError("Missing required context data: query_id or expert_id")

        if not ctx.get("feedback_data"):
            raise ValueError("Missing required context data: feedback_data")

        # Extract feedback data from context
        feedback_data = ctx["feedback_data"]

        # Prepare feedback collection request
        collection_request = {
            "query_id": ctx["query_id"],
            "expert_id": ctx["expert_id"],
            "feedback_type": feedback_data.get("feedback_type"),
            "category": feedback_data.get("category"),
            "query_text": feedback_data.get("query_text", ""),
            "original_answer": feedback_data.get("original_answer", ""),
            "expert_answer": feedback_data.get("expert_answer"),
            "improvement_suggestions": feedback_data.get("improvement_suggestions", []),
            "regulatory_references": feedback_data.get("regulatory_references", []),
            "confidence_score": feedback_data.get("confidence_score", 0.0),
            "time_spent_seconds": feedback_data.get("time_spent_seconds", 0),
            "complexity_rating": feedback_data.get("complexity_rating"),
        }

        # Use ExpertFeedbackCollector service for business logic
        # Note: In real implementation, this would use dependency injection
        from app.services.database import database_service
        from app.services.expert_feedback_collector import ExpertFeedbackCollector

        # Create service instance (in production, use dependency injection)
        db_session = database_service.get_session_maker()
        collector = ExpertFeedbackCollector(db=db_session)

        # Delegate business logic to service
        collection_result = await collector.collect_feedback(collection_request)

        processing_time = (time.time() - start_time) * 1000

        if collection_result.get("success"):
            # Prepare successful result with routing for Step 124
            result = {
                "success": True,
                "step": 123,
                "step_id": "RAG.feedback.create.expertfeedback.record",
                "node_label": "CreateFeedbackRec",
                "feedback_record_created": True,
                "feedback_id": collection_result.get("feedback_id"),
                "feedback_type": collection_result.get("feedback_type"),
                "italian_category": collection_result.get("category"),
                "expert_trust_score": collection_result.get("expert_trust_score"),
                "action_taken": collection_result.get("action_taken"),
                # Context preservation
                "query_id": ctx["query_id"],
                "expert_id": ctx["expert_id"],
                "context_preserved": True,
                # Routing metadata for Step 124 (UpdateExpertMetrics)
                "next_step": 124,
                "next_step_id": "RAG.metrics.update.expert.metrics",
                "route_to": "UpdateExpertMetrics",
                # Data prepared for Step 124
                "expert_metrics_update": {
                    "expert_id": ctx["expert_id"],
                    "feedback_created": True,
                    "feedback_record_id": collection_result.get("feedback_id"),
                    "feedback_type": collection_result.get("feedback_type"),
                    "processing_time_ms": collection_result.get("processing_time_ms"),
                    "trust_score_at_creation": collection_result.get("expert_trust_score"),
                    "feedback_metadata": {
                        "category": collection_result.get("category"),
                        "confidence_score": feedback_data.get("confidence_score"),
                        "time_spent_seconds": feedback_data.get("time_spent_seconds"),
                    },
                },
                # Pipeline context preservation
                "pipeline_context": {
                    "step_121_trust_validation": ctx.get("trust_validation_result", {}),
                    "step_123_feedback_creation": {
                        "success": True,
                        "feedback_id": collection_result.get("feedback_id"),
                        "processing_time_ms": collection_result.get("processing_time_ms"),
                    },
                },
                # Processing metadata
                "processing_metadata": {
                    "step_123_duration_ms": processing_time,
                    "feedback_collection_time_ms": collection_result.get("processing_time_ms"),
                    "timestamp": datetime.utcnow().isoformat(),
                },
                # Behavioral verification
                "orchestration_pattern": "thin",
                "business_logic_delegation": {"service": "ExpertFeedbackCollector", "method": "collect_feedback"},
                "observability": {"structured_logging": True, "timing_tracked": True},
                # Mermaid flow compliance
                "mermaid_flow_compliance": True,
                "previous_step": ctx.get("rag_step", 121),
                "previous_node": "TrustScoreOK",
                "current_node": "CreateFeedbackRec",
                "next_node": "UpdateExpertMetrics",
                "previous_step_decision": ctx.get("processing_metadata", {}).get(
                    "decision_outcome", "trust_score_acceptable"
                ),
            }

            # Include expert answer if provided
            if collection_result.get("expert_answer"):
                result["expert_answer"] = collection_result["expert_answer"]

            return result

        else:
            # Handle service error
            return await _handle_feedback_creation_error(
                ctx,
                collection_result.get("error", "Unknown service error"),
                processing_time,
                error_type="service_error",
            )

    except ValueError as ve:
        processing_time = (time.time() - start_time) * 1000
        return await _handle_feedback_creation_error(ctx, str(ve), processing_time, error_type="validation_error")

    except Exception as e:
        processing_time = (time.time() - start_time) * 1000
        return await _handle_feedback_creation_error(ctx, str(e), processing_time, error_type="service_error")


async def _handle_feedback_creation_error(
    ctx: dict[str, Any], error_message: str, processing_time: float, error_type: str = "unknown_error"
) -> dict[str, Any]:
    """Handle feedback creation errors with graceful fallback and context preservation."""
    return {
        "success": False,
        "step": 123,
        "step_id": "RAG.feedback.create.expertfeedback.record",
        "node_label": "CreateFeedbackRec",
        "error_type": error_type,
        "error_message": error_message,
        "error_handled_gracefully": True,
        # Context preservation despite errors
        "query_id": ctx.get("query_id"),
        "expert_id": ctx.get("expert_id"),
        "context_preserved": True,
        # Processing metadata
        "processing_metadata": {
            "step_123_duration_ms": processing_time,
            "error_timestamp": datetime.utcnow().isoformat(),
            "error_stage": "feedback_creation",
        },
        # Pipeline context preservation
        "pipeline_context": ctx.get("pipeline_context", {}),
        "previous_step": ctx.get("rag_step", 121),
        # Behavioral verification
        "orchestration_pattern": "thin",
        "observability": {"structured_logging": True, "timing_tracked": True},
    }
