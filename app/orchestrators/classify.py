# AUTO-GENERATED ORCHESTRATOR STUBS (safe to edit below stubs)
# These functions are the functional *nodes* that mirror the Mermaid diagram.
# Implement thin coordination here (call services/factories), not core business logic.

import math
from contextlib import nullcontext
from datetime import UTC, datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from app.observability.rag_logging import rag_step_log, rag_step_timer
except Exception:  # pragma: no cover

    def rag_step_log(**kwargs):
        return None

    def rag_step_timer(*args, **kwargs):
        return nullcontext()


async def step_12__extract_query(
    *, messages: list[Any] | None = None, ctx: dict[str, Any] | None = None, **kwargs
) -> Any:
    """RAG STEP 12 — LangGraphAgent._classify_user_query Extract user message
    ID: RAG.classify.langgraphagent.classify.user.query.extract.user.message
    Type: process | Category: classify | Node: ExtractQuery

    Extracts the latest user message from a conversation for classification.
    This orchestrator coordinates user query extraction for domain/action classification.
    """
    from datetime import datetime

    from app.core.logging import logger
    from app.schemas.chat import Message

    with rag_step_timer(
        12, "RAG.classify.langgraphagent.classify.user.query.extract.user.message", "ExtractQuery", stage="start"
    ):
        rag_step_log(
            step=12,
            step_id="RAG.classify.langgraphagent.classify.user.query.extract.user.message",
            node_label="ExtractQuery",
            category="classify",
            type="process",
            processing_stage="started",
        )

        # Extract context parameters
        context = ctx or {}
        converted_messages = messages or kwargs.get("converted_messages") or context.get("converted_messages", [])
        request_id = kwargs.get("request_id") or context.get("request_id", "unknown")

        # Initialize result structure
        result = {
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "extraction_successful": False,
            "user_message_found": False,
            "extracted_query": None,
            "latest_user_message": None,
            "user_message_count": 0,
            "message_position": None,
            "query_length": 0,
            "query_complexity": "simple",
            "original_query": None,
            "preprocessing_applied": False,
            "next_step": "DefaultPrompt",  # Default when no user message
            "ready_for_classification": False,
            "error": None,
        }

        try:
            # Step 1: Handle missing context
            if ctx is None:
                result["error"] = "Missing context for query extraction"
                logger.error("Query extraction failed: Missing context", request_id=request_id)
                rag_step_log(
                    step=12,
                    step_id="RAG.classify.langgraphagent.classify.user.query.extract.user.message",
                    node_label="ExtractQuery",
                    processing_stage="completed",
                    error="missing_context",
                    extraction_successful=False,
                    request_id=request_id,
                )
                return result

            # Step 2: Handle empty message list
            if not converted_messages:
                logger.warning("No messages provided for query extraction", request_id=request_id)
                result["extraction_successful"] = True  # Not an error, just no messages
                rag_step_log(
                    step=12,
                    step_id="RAG.classify.langgraphagent.classify.user.query.extract.user.message",
                    node_label="ExtractQuery",
                    processing_stage="completed",
                    extraction_successful=True,
                    user_message_found=False,
                    user_message_count=0,
                    next_step="DefaultPrompt",
                    request_id=request_id,
                )
                return result

            # Step 3: Find all user messages and extract the latest one
            user_messages = []
            latest_user_message = None
            latest_position = None

            for i, message in enumerate(converted_messages):
                if isinstance(message, Message) and message.role == "user":
                    user_messages.append((i, message))
                    latest_user_message = message
                    latest_position = i

            # Step 4: Analyze extraction result
            user_message_count = len(user_messages)

            if not user_messages:
                # No user messages found
                logger.warning(
                    "No user messages found in conversation",
                    total_messages=len(converted_messages),
                    request_id=request_id,
                )
                result["extraction_successful"] = True
                result["user_message_found"] = False
                result["next_step"] = "DefaultPrompt"

                rag_step_log(
                    step=12,
                    step_id="RAG.classify.langgraphagent.classify.user.query.extract.user.message",
                    node_label="ExtractQuery",
                    processing_stage="completed",
                    extraction_successful=True,
                    user_message_found=False,
                    user_message_count=0,
                    next_step="DefaultPrompt",
                    request_id=request_id,
                )
                return result

            # Step 5: Process the extracted user message
            original_content = latest_user_message.content
            processed_content = await _preprocess_query(original_content)
            preprocessing_applied = original_content != processed_content

            # Step 6: Analyze query characteristics
            query_length = len(processed_content)
            query_complexity = _analyze_query_complexity(processed_content)

            # Step 7: Build successful result
            result.update(
                {
                    "extraction_successful": True,
                    "user_message_found": True,
                    "extracted_query": processed_content,
                    "latest_user_message": latest_user_message,
                    "user_message_count": user_message_count,
                    "message_position": latest_position,
                    "query_length": query_length,
                    "query_complexity": query_complexity,
                    "original_query": original_content,
                    "preprocessing_applied": preprocessing_applied,
                    "next_step": "ClassifyDomain",
                    "ready_for_classification": True,
                }
            )

            logger.info(
                "User query extraction completed successfully",
                user_message_count=user_message_count,
                query_length=query_length,
                query_complexity=query_complexity,
                preprocessing_applied=preprocessing_applied,
                request_id=request_id,
                extra={
                    "extraction_event": "query_extracted",
                    "user_message_count": user_message_count,
                    "query_length": query_length,
                    "complexity": query_complexity,
                },
            )

            rag_step_log(
                step=12,
                step_id="RAG.classify.langgraphagent.classify.user.query.extract.user.message",
                node_label="ExtractQuery",
                processing_stage="completed",
                extraction_successful=True,
                user_message_found=True,
                user_message_count=user_message_count,
                query_length=query_length,
                query_complexity=query_complexity,
                next_step="ClassifyDomain",
                ready_for_classification=True,
                request_id=request_id,
            )

            return result

        except Exception as e:
            # Handle extraction errors
            result["error"] = f"Query extraction error: {str(e)}"

            logger.error("User query extraction failed", error=str(e), request_id=request_id, exc_info=True)

            rag_step_log(
                step=12,
                step_id="RAG.classify.langgraphagent.classify.user.query.extract.user.message",
                node_label="ExtractQuery",
                processing_stage="completed",
                error=str(e),
                extraction_successful=False,
                request_id=request_id,
            )

            return result


async def _preprocess_query(query_text: str) -> str:
    """Preprocess and normalize query text."""
    if not query_text:
        return ""

    # Remove leading/trailing whitespace and normalize internal whitespace
    processed = " ".join(query_text.strip().split())

    return processed


def _analyze_query_complexity(query_text: str) -> str:
    """Analyze query complexity based on length and content."""
    if not query_text:
        return "simple"

    length = len(query_text)

    if length < 50:
        return "simple"
    elif length < 150:
        return "medium"
    else:
        return "complex"


async def step_31__classify_domain(
    *, messages: list[Any] | None = None, ctx: dict[str, Any] | None = None, **kwargs
) -> Any:
    """RAG STEP 31 — DomainActionClassifier.classify Rule-based classification
    ID: RAG.classify.domainactionclassifier.classify.rule.based.classification
    Type: process | Category: classify | Node: ClassifyDomain

    Performs rule-based classification using the DomainActionClassifier service.
    This orchestrator coordinates domain/action classification with fallback handling.
    """
    from datetime import datetime

    from app.core.logging import logger
    from app.services.domain_action_classifier import DomainActionClassifier

    with rag_step_timer(
        31, "RAG.classify.domainactionclassifier.classify.rule.based.classification", "ClassifyDomain", stage="start"
    ):
        # Extract context parameters
        user_query = kwargs.get("user_query") or (ctx or {}).get("user_query", "")
        classification_service = kwargs.get("classification_service") or (ctx or {}).get("classification_service")

        # Initialize classification data
        classification = None
        domain = None
        action = None
        confidence = 0.0
        fallback_used = False
        error = None

        try:
            if not user_query:
                error = "No user query provided"
                raise ValueError(error)

            # Create classifier if not provided
            if not classification_service:
                classification_service = DomainActionClassifier()

            # Perform classification
            classification = await classification_service.classify(user_query)

            # Extract classification details
            domain = classification.domain.value if classification.domain else None
            action = classification.action.value if classification.action else None
            confidence = classification.confidence
            fallback_used = classification.fallback_used

        except Exception as e:
            error = str(e)

        # Create classification result
        classification_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "classification": classification,
            "domain": domain,
            "action": action,
            "confidence": confidence,
            "fallback_used": fallback_used,
            "query_length": len(user_query) if user_query else 0,
            "error": error,
        }

        # Log classification result
        if error:
            log_message = f"Rule-based classification failed: {error}"
            logger.error(
                log_message,
                extra={
                    "classification_event": "rule_based_classification_failed",
                    "error": error,
                    "query_length": len(user_query) if user_query else 0,
                },
            )
        elif fallback_used:
            log_message = "Rule-based classification used LLM fallback"
            logger.warning(
                log_message,
                extra={
                    "classification_event": "rule_based_classification",
                    "domain": domain,
                    "action": action,
                    "confidence": confidence,
                    "fallback_used": True,
                    "query_length": len(user_query),
                },
            )
        else:
            log_message = f"Rule-based classification completed: {domain}/{action}"
            logger.info(
                log_message,
                extra={
                    "classification_event": "rule_based_classification",
                    "domain": domain,
                    "action": action,
                    "confidence": confidence,
                    "fallback_used": False,
                    "query_length": len(user_query),
                },
            )

        # RAG step logging
        rag_step_log(
            step=31,
            step_id="RAG.classify.domainactionclassifier.classify.rule.based.classification",
            node_label="ClassifyDomain",
            category="classify",
            type="process",
            classification_event="rule_based_classification_failed" if error else "rule_based_classification",
            domain=domain,
            action=action,
            confidence=confidence,
            fallback_used=fallback_used,
            query_length=len(user_query) if user_query else 0,
            error=error,
            processing_stage="completed",
        )

        return classification_data


async def step_32__calc_scores(
    *, messages: list[Any] | None = None, ctx: dict[str, Any] | None = None, **kwargs
) -> Any:
    """RAG STEP 32 — Calculate domain and action scores Match Italian keywords
    ID: RAG.classify.calculate.domain.and.action.scores.match.italian.keywords
    Type: process | Category: classify | Node: CalcScores

    Calculates domain and action scores using Italian keyword matching.
    This orchestrator coordinates score calculation with confidence threshold detection.
    """
    from datetime import datetime

    from app.core.logging import logger
    from app.services.domain_action_classifier import DomainActionClassifier

    with rag_step_timer(
        32, "RAG.classify.calculate.domain.and.action.scores.match.italian.keywords", "CalcScores", stage="start"
    ):
        # Extract context parameters
        user_query = kwargs.get("user_query") or (ctx or {}).get("user_query", "")
        classification_service = kwargs.get("classification_service") or (ctx or {}).get("classification_service")

        # Initialize scores data
        domain_scores = None
        action_scores = None
        best_domain = None
        best_action = None
        domain_confidence = 0.0
        action_confidence = 0.0
        error = None

        try:
            if not user_query:
                error = "No user query provided"
                raise ValueError(error)

            # Create classifier if not provided
            if not classification_service:
                classification_service = DomainActionClassifier()

            # Normalize query for scoring (lowercase)
            normalized_query = user_query.lower()

            # Calculate domain and action scores
            domain_scores = classification_service._calculate_domain_scores(normalized_query)
            action_scores = classification_service._calculate_action_scores(normalized_query)

            # Find best domain and action
            if domain_scores:
                best_domain = max(domain_scores.items(), key=lambda x: x[1])[0]
                domain_confidence = domain_scores[best_domain]

            if action_scores:
                best_action = max(action_scores.items(), key=lambda x: x[1])[0]
                action_confidence = action_scores[best_action]

        except Exception as e:
            error = str(e)

        # Create scores result
        scores_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "domain_scores": domain_scores,
            "action_scores": action_scores,
            "best_domain": best_domain,
            "best_action": best_action,
            "domain_confidence": domain_confidence,
            "action_confidence": action_confidence,
            "query_length": len(user_query) if user_query else 0,
            "error": error,
        }

        # Log scores result
        if error:
            log_message = f"Score calculation failed: {error}"
            logger.error(
                log_message,
                extra={
                    "scoring_event": "scores_calculation_failed",
                    "error": error,
                    "query_length": len(user_query) if user_query else 0,
                },
            )
        elif domain_confidence < 0.5 or action_confidence < 0.5:
            log_message = "Low confidence scores detected"
            logger.warning(
                log_message,
                extra={
                    "scoring_event": "low_confidence_scores",
                    "best_domain": best_domain.value if best_domain else None,
                    "best_action": best_action.value if best_action else None,
                    "domain_confidence": domain_confidence,
                    "action_confidence": action_confidence,
                    "query_length": len(user_query),
                },
            )
        else:
            log_message = f"Domain/action scores calculated: {best_domain.value if best_domain else None}/{best_action.value if best_action else None}"
            logger.info(
                log_message,
                extra={
                    "scoring_event": "scores_calculated",
                    "best_domain": best_domain.value if best_domain else None,
                    "best_action": best_action.value if best_action else None,
                    "domain_confidence": domain_confidence,
                    "action_confidence": action_confidence,
                    "query_length": len(user_query),
                },
            )

        # RAG step logging
        rag_step_log(
            step=32,
            step_id="RAG.classify.calculate.domain.and.action.scores.match.italian.keywords",
            node_label="CalcScores",
            category="classify",
            type="process",
            scoring_event="scores_calculation_failed" if error else "scores_calculated",
            best_domain=best_domain.value if best_domain else None,
            best_action=best_action.value if best_action else None,
            domain_confidence=domain_confidence,
            action_confidence=action_confidence,
            query_length=len(user_query) if user_query else 0,
            error=error,
            processing_stage="completed",
        )

        return scores_data


async def step_33__confidence_check(
    *, messages: list[Any] | None = None, ctx: dict[str, Any] | None = None, **kwargs
) -> Any:
    """RAG STEP 33 — Confidence at least threshold?
    ID: RAG.classify.confidence.at.least.threshold
    Type: decision | Category: classify | Node: ConfidenceCheck

    Performs confidence threshold check on classification results.
    This orchestrator validates if classification confidence meets minimum threshold.
    """
    from datetime import datetime

    from app.core.logging import logger

    with rag_step_timer(33, "RAG.classify.confidence.at.least.threshold", "ConfidenceCheck", stage="start"):
        # Extract context parameters
        classification = kwargs.get("classification") or (ctx or {}).get("classification")
        scores_data = kwargs.get("scores_data") or (ctx or {}).get("scores_data")
        confidence_threshold = kwargs.get("confidence_threshold") or (ctx or {}).get("confidence_threshold", 0.6)

        # Initialize confidence data
        confidence_met = False
        confidence_value = 0.0
        domain = None
        action = None
        fallback_used = False
        error = None

        try:
            # Extract confidence from classification or scores data
            if classification:
                confidence_value = classification.get("confidence", 0.0)
                domain = classification.get("domain")
                action = classification.get("action")
                fallback_used = classification.get("fallback_used", False)
            elif scores_data:
                # Use domain confidence as primary when classification missing
                confidence_value = scores_data.get("domain_confidence", 0.0)
                best_domain = scores_data.get("best_domain")
                best_action = scores_data.get("best_action")
                domain = (
                    best_domain.value if hasattr(best_domain, "value") else str(best_domain) if best_domain else None
                )
                action = (
                    best_action.value if hasattr(best_action, "value") else str(best_action) if best_action else None
                )
            else:
                error = "No classification data provided"
                raise ValueError(error)

            # Check if confidence meets threshold
            confidence_met = confidence_value >= confidence_threshold

        except Exception as e:
            error = str(e)

        # Create confidence result
        confidence_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "confidence_met": confidence_met,
            "confidence_value": confidence_value,
            "threshold": confidence_threshold,
            "domain": domain,
            "action": action,
            "fallback_used": fallback_used,
            "error": error,
        }

        # Log confidence result
        if error:
            log_message = f"Confidence check failed: {error}"
            logger.error(
                log_message,
                extra={
                    "confidence_event": "confidence_check_failed",
                    "error": error,
                    "threshold": confidence_threshold,
                },
            )
        elif not confidence_met:
            log_message = f"Confidence threshold not met: {confidence_value:.3f} < {confidence_threshold}"
            logger.warning(
                log_message,
                extra={
                    "confidence_event": "threshold_not_met",
                    "confidence_value": confidence_value,
                    "threshold": confidence_threshold,
                    "domain": domain,
                    "action": action,
                    "fallback_used": fallback_used,
                },
            )
        else:
            log_message = f"Confidence threshold met: {confidence_value:.3f} >= {confidence_threshold}"
            logger.info(
                log_message,
                extra={
                    "confidence_event": "threshold_met",
                    "confidence_value": confidence_value,
                    "threshold": confidence_threshold,
                    "domain": domain,
                    "action": action,
                    "fallback_used": fallback_used,
                },
            )

        # RAG step logging
        rag_step_log(
            step=33,
            step_id="RAG.classify.confidence.at.least.threshold",
            node_label="ConfidenceCheck",
            category="classify",
            type="decision",
            confidence_event="confidence_check_failed"
            if error
            else ("threshold_met" if confidence_met else "threshold_not_met"),
            confidence_met=confidence_met,
            confidence_value=confidence_value,
            threshold=confidence_threshold,
            domain=domain,
            action=action,
            fallback_used=fallback_used,
            error=error,
            processing_stage="completed",
        )

        return confidence_data


def step_35__llmfallback(*, messages: list[Any] | None = None, ctx: dict[str, Any] | None = None, **kwargs) -> Any:
    """RAG STEP 35 — DomainActionClassifier._llm_fallback Use LLM classification
    ID: RAG.classify.domainactionclassifier.llm.fallback.use.llm.classification
    Type: process | Category: classify | Node: LLMFallback

    TODO: Implement orchestration so this node *changes/validates control flow/data*
    according to Mermaid — not logs-only. Call into existing services/factories here.
    """
    with rag_step_timer(
        35, "RAG.classify.domainactionclassifier.llm.fallback.use.llm.classification", "LLMFallback", stage="start"
    ):
        rag_step_log(
            step=35,
            step_id="RAG.classify.domainactionclassifier.llm.fallback.use.llm.classification",
            node_label="LLMFallback",
            category="classify",
            type="process",
            stub=True,
            processing_stage="started",
        )
        # TODO: call real service/factory here and return its output
        result = kwargs.get("result")  # placeholder
        rag_step_log(
            step=35,
            step_id="RAG.classify.domainactionclassifier.llm.fallback.use.llm.classification",
            node_label="LLMFallback",
            processing_stage="completed",
        )
        return result


async def step_42__class_confidence(
    *, messages: list[Any] | None = None, ctx: dict[str, Any] | None = None, **kwargs
) -> Any:
    """RAG STEP 42 — Classification exists and confidence at least 0.6?
    ID: RAG.classify.classification.exists.and.confidence.at.least.0.6
    Type: decision | Category: classify | Node: ClassConfidence

    Checks for classification existence and 0.6 confidence threshold.
    This orchestrator validates both classification presence and sufficient confidence.
    """
    from datetime import datetime

    from app.core.logging import logger
    from app.services.domain_action_classifier import DomainActionClassification

    with rag_step_timer(
        42, "RAG.classify.classification.exists.and.confidence.at.least.0.6", "ClassConfidence", stage="start"
    ):
        # Extract context parameters
        classification = kwargs.get("classification") or (ctx or {}).get("classification")

        # Initialize classification check data
        classification_exists = False
        confidence_sufficient = False
        confidence_value = 0.0
        threshold = 0.6  # Fixed threshold as per step specification
        domain = None
        action = None
        fallback_used = False
        reasoning = None

        # Check if classification exists and extract details
        if classification:
            classification_exists = True

            # Handle both DomainActionClassification objects and dict format
            if isinstance(classification, DomainActionClassification):
                confidence_value = classification.confidence
                domain = classification.domain.value if classification.domain else None
                action = classification.action.value if classification.action else None
                fallback_used = classification.fallback_used
                reasoning = classification.reasoning
            elif isinstance(classification, dict):
                confidence_value = classification.get("confidence", 0.0)
                domain_obj = classification.get("domain")
                action_obj = classification.get("action")
                domain = domain_obj.value if hasattr(domain_obj, "value") else str(domain_obj) if domain_obj else None
                action = action_obj.value if hasattr(action_obj, "value") else str(action_obj) if action_obj else None
                fallback_used = classification.get("fallback_used", False)
                reasoning = classification.get("reasoning")

            # Check if confidence meets threshold
            confidence_sufficient = confidence_value >= threshold

        # Create classification check result
        class_confidence_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "classification_exists": classification_exists,
            "confidence_sufficient": confidence_sufficient,
            "confidence_value": confidence_value,
            "threshold": threshold,
            "domain": domain,
            "action": action,
            "fallback_used": fallback_used,
            "reasoning": reasoning,
        }

        # Log classification check result
        if not classification_exists:
            log_message = "No classification provided"
            logger.warning(log_message, extra={"classification_event": "no_classification", "threshold": threshold})
        elif not confidence_sufficient:
            log_message = f"Classification exists but insufficient confidence: {confidence_value:.3f} < {threshold}"
            logger.warning(
                log_message,
                extra={
                    "classification_event": "exists_confidence_insufficient",
                    "confidence_value": confidence_value,
                    "threshold": threshold,
                    "domain": domain,
                    "action": action,
                    "fallback_used": fallback_used,
                },
            )
        else:
            log_message = f"Classification exists with sufficient confidence: {confidence_value:.3f} >= {threshold}"
            logger.info(
                log_message,
                extra={
                    "classification_event": "exists_confidence_sufficient",
                    "confidence_value": confidence_value,
                    "threshold": threshold,
                    "domain": domain,
                    "action": action,
                    "fallback_used": fallback_used,
                },
            )

        # RAG step logging
        rag_step_log(
            step=42,
            step_id="RAG.classify.classification.exists.and.confidence.at.least.0.6",
            node_label="ClassConfidence",
            category="classify",
            type="decision",
            classification_event=(
                "no_classification"
                if not classification_exists
                else "exists_confidence_insufficient"
                if not confidence_sufficient
                else "exists_confidence_sufficient"
            ),
            classification_exists=classification_exists,
            confidence_sufficient=confidence_sufficient,
            confidence_value=confidence_value,
            threshold=threshold,
            domain=domain,
            action=action,
            fallback_used=fallback_used,
            processing_stage="completed",
        )

        return class_confidence_data


async def step_35__llm_fallback(*, ctx: dict[str, Any] | None = None, **kwargs) -> Any:
    """RAG STEP 35 — DomainActionClassifier._llm_fallback Use LLM classification
    ID: RAG.classify.domainactionclassifier.llm.fallback.use.llm.classification
    Type: process | Category: classify | Node: LLMFallback

    Provides LLM fallback classification when rule-based classification has low confidence.
    This orchestrator coordinates LLM classification fallback for improved accuracy.
    """
    from datetime import datetime

    from app.core.logging import logger
    from app.services.domain_action_classifier import DomainActionClassifier

    with rag_step_timer(
        35, "RAG.classify.domainactionclassifier.llm.fallback.use.llm.classification", "LLMFallback", stage="start"
    ):
        rag_step_log(
            step=35,
            step_id="RAG.classify.domainactionclassifier.llm.fallback.use.llm.classification",
            node_label="LLMFallback",
            category="classify",
            type="process",
            processing_stage="started",
        )

        # Extract context parameters
        context = ctx or {}
        user_query = kwargs.get("user_query") or context.get("user_query")
        rule_based_classification = kwargs.get("rule_based_classification") or context.get("rule_based_classification")
        rule_based_confidence = kwargs.get("rule_based_confidence") or context.get("rule_based_confidence", 0.0)
        request_id = kwargs.get("request_id") or context.get("request_id", "unknown")

        # Initialize result structure
        result = {
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "llm_fallback_successful": False,
            "llm_classification": None,
            "rule_based_classification": rule_based_classification,
            "llm_fallback_used": True,
            "classification_method": "llm_fallback",
            "improved_confidence": False,
            "fallback_to_rule_based": False,
            "preprocessing_applied": False,
            "original_query": None,
            "next_step": "LLMBetter",
            "ready_for_comparison": False,
            "confidence_analysis": {},
            "service_error": None,
            "error": None,
            "request_id": request_id,
        }

        try:
            # Step 1: Validate context
            if ctx is None:
                result["error"] = "Missing context for LLM fallback"
                logger.error("LLM fallback failed: Missing context", request_id=request_id)
                rag_step_log(
                    step=35,
                    step_id="RAG.classify.domainactionclassifier.llm.fallback.use.llm.classification",
                    node_label="LLMFallback",
                    processing_stage="completed",
                    error="missing_context",
                    llm_fallback_successful=False,
                    request_id=request_id,
                )
                return result

            # Step 2: Validate user query
            if not user_query:
                result["error"] = "Missing user_query in context"
                logger.warning("LLM fallback failed: No user query provided", request_id=request_id)
                rag_step_log(
                    step=35,
                    step_id="RAG.classify.domainactionclassifier.llm.fallback.use.llm.classification",
                    node_label="LLMFallback",
                    processing_stage="completed",
                    error="missing_query",
                    llm_fallback_successful=False,
                    request_id=request_id,
                )
                return result

            # Step 3: Preprocess query if needed
            original_query = user_query
            processed_query = user_query.strip()
            preprocessing_applied = processed_query != user_query

            if preprocessing_applied:
                result["preprocessing_applied"] = True
                result["original_query"] = original_query
                logger.debug(
                    "Query preprocessing applied",
                    original_length=len(original_query),
                    processed_length=len(processed_query),
                    request_id=request_id,
                )

            # Step 4: Attempt LLM classification
            try:
                classifier = kwargs.get("classifier") or DomainActionClassifier()
                llm_classification = await classifier._llm_fallback_classification(processed_query)

                if llm_classification:
                    # LLM classification successful
                    result["llm_fallback_successful"] = True
                    result["llm_classification"] = llm_classification
                    result["ready_for_comparison"] = True

                    # Analyze confidence improvement
                    llm_confidence = llm_classification.confidence
                    confidence_improvement = llm_confidence - rule_based_confidence
                    significant_improvement = confidence_improvement >= 0.1

                    result["improved_confidence"] = significant_improvement
                    result["confidence_analysis"] = {
                        "rule_based_confidence": rule_based_confidence,
                        "llm_confidence": llm_confidence,
                        "improvement": confidence_improvement,
                        "significant_improvement": significant_improvement,
                    }

                    logger.info(
                        "LLM fallback classification completed successfully",
                        llm_domain=llm_classification.domain.value,
                        llm_action=llm_classification.action.value,
                        llm_confidence=llm_confidence,
                        confidence_improvement=confidence_improvement,
                        request_id=request_id,
                    )

                else:
                    # LLM classification failed, fall back to rule-based
                    result["llm_fallback_successful"] = False
                    result["fallback_to_rule_based"] = True
                    result["classification_method"] = "rule_based_fallback"
                    result["llm_classification"] = rule_based_classification
                    result["next_step"] = "UseRuleBased"

                    logger.warning(
                        "LLM classification returned None, falling back to rule-based", request_id=request_id
                    )

            except Exception as e:
                # Service exception, fall back to rule-based
                result["llm_fallback_successful"] = False
                result["fallback_to_rule_based"] = True
                result["classification_method"] = "rule_based_fallback"
                result["llm_classification"] = rule_based_classification
                result["service_error"] = str(e)
                result["next_step"] = "UseRuleBased"

                logger.error(
                    "LLM classification service error, falling back to rule-based", error=str(e), request_id=request_id
                )

        except Exception as e:
            # Unexpected error
            result["error"] = f"Unexpected error in LLM fallback: {str(e)}"
            logger.error(
                "Unexpected error in LLM fallback orchestrator", error=str(e), request_id=request_id, exc_info=True
            )

        # Final logging
        rag_step_log(
            step=35,
            step_id="RAG.classify.domainactionclassifier.llm.fallback.use.llm.classification",
            node_label="LLMFallback",
            category="classify",
            type="process",
            llm_fallback_successful=result["llm_fallback_successful"],
            classification_method=result["classification_method"],
            improved_confidence=result.get("improved_confidence", False),
            fallback_to_rule_based=result["fallback_to_rule_based"],
            preprocessing_applied=result["preprocessing_applied"],
            next_step=result["next_step"],
            ready_for_comparison=result["ready_for_comparison"],
            request_id=request_id,
            processing_stage="completed",
        )

        return result


async def step_43__domain_prompt(
    *, messages: list[Any] | None = None, ctx: dict[str, Any] | None = None, **kwargs
) -> Any:
    """RAG STEP 43 — PromptTemplateManager.get_prompt Get domain-specific prompt
    ID: RAG.classify.prompttemplatemanager.get.prompt.get.domain.specific.prompt
    Type: process | Category: classify | Node: DomainPrompt

    Generates domain-specific prompts when classification confidence is high enough.
    This thin orchestrator wraps PromptTemplateManager.get_prompt() business logic.
    """
    from datetime import datetime

    from app.core.logging import logger
    from app.services.domain_action_classifier import DomainActionClassification
    from app.services.domain_prompt_templates import PromptTemplateManager

    # Extract context parameters
    ctx = ctx or {}
    classification = kwargs.get("classification") or ctx.get("classification")
    prompt_template_manager = kwargs.get("prompt_template_manager") or ctx.get("prompt_template_manager")
    user_query = kwargs.get("user_query") or ctx.get("user_query", "")
    prompt_context = kwargs.get("prompt_context") or ctx.get("prompt_context")
    request_id = ctx.get("request_id", "unknown")

    # Initialize orchestration result
    domain_prompt = None
    prompt_generated = False
    error_occurred = False
    error_message = None
    domain = None
    action = None
    document_type = None
    prompt_length = 0

    try:
        # Validate inputs
        if not classification:
            raise ValueError("Classification is required for domain prompt generation")

        if not isinstance(classification, DomainActionClassification):
            raise TypeError(f"Expected DomainActionClassification, got {type(classification)}")

        # Create PromptTemplateManager if not provided
        if not prompt_template_manager:
            prompt_template_manager = PromptTemplateManager()

        # Extract classification details
        domain = classification.domain.value if classification.domain else None
        action = classification.action.value if classification.action else None
        document_type = classification.document_type

        # Log the orchestration start (separate from internal PromptTemplateManager logging)
        rag_step_log(
            step=43,
            step_id="RAG.classify.prompttemplatemanager.get.prompt.get.domain.specific.prompt",
            node_label="DomainPrompt",
            category="classify",
            type="process",
            processing_stage="started",
            request_id=request_id,
            domain=domain,
            action=action,
            user_query=user_query[:100] if user_query else "",
            has_context=bool(prompt_context),
            document_type=document_type,
        )

        # Call the actual business logic (PromptTemplateManager.get_prompt)
        # This will also log its own RAG Step 43 logs internally
        domain_prompt = prompt_template_manager.get_prompt(
            domain=classification.domain,
            action=classification.action,
            query=user_query,
            context=prompt_context,
            document_type=document_type,
        )

        # Validate the generated prompt
        if domain_prompt and isinstance(domain_prompt, str) and len(domain_prompt) > 0:
            prompt_generated = True
            prompt_length = len(domain_prompt)
        else:
            raise ValueError("Generated prompt is empty or invalid")

    except Exception as e:
        error_occurred = True
        error_message = str(e)

        logger.error(
            f"Failed to generate domain prompt: {error_message}",
            extra={
                "request_id": request_id,
                "step": 43,
                "error": error_message,
                "domain": domain,
                "action": action,
                "classification_available": classification is not None,
            },
        )

        # Provide fallback prompt (empty string to trigger downstream default handling)
        domain_prompt = ""
        prompt_generated = False

    # Log orchestration completion
    rag_step_log(
        step=43,
        step_id="RAG.classify.prompttemplatemanager.get.prompt.get.domain.specific.prompt",
        node_label="DomainPrompt",
        processing_stage="completed",
        request_id=request_id,
        prompt_generated=prompt_generated,
        error_occurred=error_occurred,
        error_message=error_message,
        domain=domain,
        action=action,
        document_type=document_type,
        prompt_length=prompt_length,
        orchestration_result="success" if prompt_generated else "fallback",
    )

    # Build orchestration result (thin wrapper preserving behavior)
    result = {
        "domain_prompt": domain_prompt,
        "prompt_generated": prompt_generated,
        "domain": domain,
        "action": action,
        "document_type": document_type,
        "prompt_length": prompt_length,
        "error_occurred": error_occurred,
        "error_message": error_message,
        "request_id": request_id,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    # For backward compatibility, also return the prompt directly if accessed as string
    result["__str__"] = lambda: domain_prompt

    return result


def step_88__doc_classify(*, messages: list[Any] | None = None, ctx: dict[str, Any] | None = None, **kwargs) -> Any:
    """RAG STEP 88 — DocClassifier.classify Detect document type
    ID: RAG.classify.docclassifier.classify.detect.document.type
    Type: process | Category: classify | Node: DocClassify

    TODO: Implement orchestration so this node *changes/validates control flow/data*
    according to Mermaid — not logs-only. Call into existing services/factories here.
    """
    with rag_step_timer(88, "RAG.classify.docclassifier.classify.detect.document.type", "DocClassify", stage="start"):
        rag_step_log(
            step=88,
            step_id="RAG.classify.docclassifier.classify.detect.document.type",
            node_label="DocClassify",
            category="classify",
            type="process",
            stub=True,
            processing_stage="started",
        )
        # TODO: call real service/factory here and return its output
        result = kwargs.get("result")  # placeholder
        rag_step_log(
            step=88,
            step_id="RAG.classify.docclassifier.classify.detect.document.type",
            node_label="DocClassify",
            processing_stage="completed",
        )
        return result


async def _evaluate_trust_score_decision(ctx: dict[str, Any]) -> dict[str, Any]:
    """Helper function to evaluate trust score against 0.7 threshold and determine routing.

    Args:
        ctx: Context containing expert validation data with trust score

    Returns:
        Dict containing trust score decision and routing information
    """
    # Extract trust score from expert validation
    expert_validation = ctx.get("expert_validation", {})
    trust_score = expert_validation.get("trust_score")

    # Initialize decision result
    decision_result = {
        "decision_timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "trust_score": trust_score,
        "threshold": 0.7,
        "error": None,
    }

    # Validate trust score
    if trust_score is None:
        decision_result.update(
            {
                "trust_score_decision": False,
                "next_step": "FeedbackRejected",
                "routing_decision": "reject_feedback",
                "threshold_met": False,
                "error": "missing_trust_score",
            }
        )
        return decision_result

    # Validate trust score is a valid number
    try:
        trust_score_float = float(trust_score)
        if not (0 <= trust_score_float <= 1) or math.isnan(trust_score_float) or math.isinf(trust_score_float):
            raise ValueError("Trust score out of valid range")
    except (ValueError, TypeError):
        decision_result.update(
            {
                "trust_score_decision": False,
                "next_step": "FeedbackRejected",
                "routing_decision": "reject_feedback",
                "threshold_met": False,
                "error": "invalid_trust_score",
            }
        )
        return decision_result

    # Make trust score decision (>= 0.7 threshold per Mermaid)
    trust_score_decision = trust_score_float >= 0.7

    if trust_score_decision:
        # Trust score meets threshold - route to CreateFeedbackRec (Step 123)
        decision_result.update(
            {
                "trust_score_decision": True,
                "next_step": "CreateFeedbackRec",
                "routing_decision": "proceed_with_feedback",
                "threshold_met": True,
            }
        )
    else:
        # Trust score below threshold - route to FeedbackRejected (Step 122)
        decision_result.update(
            {
                "trust_score_decision": False,
                "next_step": "FeedbackRejected",
                "routing_decision": "reject_feedback",
                "threshold_met": False,
            }
        )

    return decision_result


async def step_121__trust_score_ok(
    *, messages: list[Any] | None = None, ctx: dict[str, Any] | None = None, **kwargs
) -> Any:
    """RAG STEP 121 — Trust score at least 0.7?
    ID: RAG.classify.trust.score.at.least.0.7
    Type: decision | Category: classify | Node: TrustScoreOK

    Decision orchestrator that evaluates trust scores from Step 120 (ValidateExpert) against
    0.7 threshold and routes to either Step 122 (FeedbackRejected) or Step 123 (CreateFeedbackRec).
    Implements thin orchestration pattern with no business logic, focusing on decision
    coordination and routing per Mermaid diagram.
    """
    with rag_step_timer(121, "RAG.classify.trust.score.at.least.0.7", "TrustScoreOK", stage="start"):
        rag_step_log(
            step=121,
            step_id="RAG.classify.trust.score.at.least.0.7",
            node_label="TrustScoreOK",
            category="classify",
            type="decision",
            processing_stage="started",
        )

        # Extract context parameters
        context = ctx or {}
        request_id = kwargs.get("request_id") or context.get("request_id", "unknown")

        try:
            # Evaluate trust score decision using helper function
            decision_data = await _evaluate_trust_score_decision(context)

            # Preserve all context data while adding decision metadata
            result = {**context}
            result.update(decision_data)
            result["request_id"] = request_id

            # Log decision details
            rag_step_log(
                step=121,
                step_id="RAG.classify.trust.score.at.least.0.7",
                node_label="TrustScoreOK",
                category="classify",
                type="decision",
                trust_score=decision_data["trust_score"],
                trust_score_decision=decision_data["trust_score_decision"],
                next_step=decision_data["next_step"],
                threshold_met=decision_data["threshold_met"],
                routing_decision=decision_data["routing_decision"],
                request_id=request_id,
                processing_stage="completed",
            )

            return result

        except Exception as e:
            # Handle unexpected errors gracefully - default to rejection
            error_result = {**context}
            error_result.update(
                {
                    "trust_score_decision": False,
                    "next_step": "FeedbackRejected",
                    "routing_decision": "reject_feedback",
                    "threshold_met": False,
                    "error": f"trust_score_evaluation_error: {str(e)}",
                    "decision_timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                    "request_id": request_id,
                }
            )

            rag_step_log(
                step=121,
                step_id="RAG.classify.trust.score.at.least.0.7",
                node_label="TrustScoreOK",
                category="classify",
                type="decision",
                error=str(e),
                trust_score_decision=False,
                next_step="FeedbackRejected",
                request_id=request_id,
                processing_stage="error",
            )

            return error_result
