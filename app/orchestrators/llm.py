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

async def step_36__llmbetter(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 36 — LLM better than rule-based?
    ID: RAG.llm.llm.better.than.rule.based
    Type: decision | Category: llm | Node: LLMBetter

    Compares LLM classification results with rule-based classification to determine
    which approach provided better results. Decision based on confidence scores,
    classification accuracy, and improvement thresholds.
    """
    from app.core.logging import logger
    from datetime import datetime, timezone

    with rag_step_timer(36, 'RAG.llm.llm.better.than.rule.based', 'LLMBetter', stage="start"):
        # Extract context parameters
        request_id = kwargs.get('request_id') or (ctx or {}).get('request_id', 'unknown')
        rule_based_classification = kwargs.get('rule_based_classification') or (ctx or {}).get('rule_based_classification')
        llm_classification = kwargs.get('llm_classification') or (ctx or {}).get('llm_classification')
        min_improvement_threshold = kwargs.get('min_improvement_threshold') or (ctx or {}).get('min_improvement_threshold', 0.05)

        # Initialize decision variables
        llm_better = False
        rule_confidence = 0.0
        llm_confidence = 0.0
        confidence_improvement = 0.0
        decision_reason = None
        classification_changed = False
        error = None

        rag_step_log(
            step=36,
            step_id='RAG.llm.llm.better.than.rule.based',
            node_label='LLMBetter',
            category='llm',
            type='decision',
            processing_stage='started',
            request_id=request_id
        )

        try:
            # Extract confidence scores
            if rule_based_classification:
                rule_confidence = rule_based_classification.get('confidence', 0.0)

            if llm_classification:
                llm_confidence = llm_classification.get('confidence', 0.0)

            # Check if we have any classification data
            if not rule_based_classification and not llm_classification:
                error = 'No classification data available for comparison'
                decision_reason = 'error'
                raise ValueError(error)

            # Handle missing rule-based classification
            if not rule_based_classification:
                llm_better = True
                decision_reason = 'no_rule_based_available'
                confidence_improvement = llm_confidence

            # Handle missing LLM classification
            elif not llm_classification:
                llm_better = False
                decision_reason = 'no_llm_available'
                confidence_improvement = -rule_confidence

            # Compare both classifications
            else:
                confidence_improvement = llm_confidence - rule_confidence

                # Check if classifications are different
                rule_domain = rule_based_classification.get('domain')
                rule_action = rule_based_classification.get('action')
                llm_domain = llm_classification.get('domain')
                llm_action = llm_classification.get('action')

                classification_changed = (rule_domain != llm_domain) or (rule_action != llm_action)

                # Decision logic
                if confidence_improvement > min_improvement_threshold:
                    llm_better = True
                    if classification_changed:
                        decision_reason = 'llm_different_classification_higher_confidence'
                    else:
                        decision_reason = 'llm_higher_confidence'

                elif confidence_improvement < -min_improvement_threshold:
                    llm_better = False
                    decision_reason = 'rule_based_higher_confidence'

                elif abs(confidence_improvement) <= min_improvement_threshold:
                    # Small or no improvement - prefer rule-based for consistency
                    llm_better = False
                    if confidence_improvement == 0.0:
                        decision_reason = 'equal_confidence_prefer_rule_based'
                    else:
                        decision_reason = 'improvement_below_threshold'

            # Log decision
            if llm_better:
                logger.info(
                    f"LLM classification better than rule-based: confidence improvement {confidence_improvement:.3f}",
                    extra={
                        'request_id': request_id,
                        'decision': 'use_llm',
                        'rule_confidence': rule_confidence,
                        'llm_confidence': llm_confidence,
                        'confidence_improvement': confidence_improvement,
                        'classification_changed': classification_changed,
                        'decision_reason': decision_reason
                    }
                )
            else:
                logger.info(
                    f"Rule-based classification better than LLM: confidence improvement {confidence_improvement:.3f}",
                    extra={
                        'request_id': request_id,
                        'decision': 'use_rule_based',
                        'rule_confidence': rule_confidence,
                        'llm_confidence': llm_confidence,
                        'confidence_improvement': confidence_improvement,
                        'classification_changed': classification_changed,
                        'decision_reason': decision_reason
                    }
                )

        except Exception as e:
            error = str(e)
            llm_better = False
            decision_reason = 'error'
            logger.error(
                f"Error in LLM vs rule-based comparison: {error}",
                extra={
                    'request_id': request_id,
                    'error': error,
                    'step': 36
                }
            )

        # Build result
        result = {
            'llm_better': llm_better,
            'rule_confidence': rule_confidence,
            'llm_confidence': llm_confidence,
            'confidence_improvement': confidence_improvement,
            'decision_reason': decision_reason,
            'classification_changed': classification_changed,
            'request_id': request_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'error': error
        }

        rag_step_log(
            step=36,
            step_id='RAG.llm.llm.better.than.rule.based',
            node_label='LLMBetter',
            category='llm',
            type='decision',
            processing_stage='completed',
            request_id=request_id,
            decision_result=llm_better,
            confidence_improvement=confidence_improvement
        )

        return result

async def step_37__use_llm(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 37 — Use LLM classification
    ID: RAG.llm.use.llm.classification
    Type: process | Category: llm | Node: UseLLM

    Applies LLM classification results as the final classification when Step 36
    determines LLM is better than rule-based classification. Thin orchestration
    that preserves existing behavior while adding coordination and observability.
    """
    from app.core.logging import logger
    from datetime import datetime, timezone

    with rag_step_timer(37, 'RAG.llm.use.llm.classification', 'UseLLM', stage="start"):
        # Extract context parameters
        request_id = kwargs.get('request_id') or (ctx or {}).get('request_id', 'unknown')
        llm_classification = kwargs.get('llm_classification') or (ctx or {}).get('llm_classification')

        # Initialize result variables
        classification_applied = False
        final_classification = None
        classification_source = 'error'
        confidence_level = None
        error = None
        metrics = {}

        rag_step_log(
            step=37,
            step_id='RAG.llm.use.llm.classification',
            node_label='UseLLM',
            category='llm',
            type='process',
            processing_stage='started',
            request_id=request_id
        )

        try:
            # Validate LLM classification data
            if not llm_classification:
                error = 'No LLM classification available to apply'
                raise ValueError(error)

            # Validate required fields
            domain = llm_classification.get('domain')
            action = llm_classification.get('action')
            confidence = llm_classification.get('confidence')

            if not domain or not action or confidence is None:
                error = f'Invalid LLM classification data: missing domain={domain}, action={action}, confidence={confidence}'
                raise ValueError(error)

            # Apply LLM classification as final result
            final_classification = dict(llm_classification)  # Create copy to preserve original
            classification_applied = True
            classification_source = 'llm'

            # Determine confidence level for monitoring
            if confidence >= 0.8:
                confidence_level = 'high'
            elif confidence >= 0.6:
                confidence_level = 'medium'
            else:
                confidence_level = 'low'
                # Log warning for low confidence
                logger.warning(
                    f"Low confidence LLM classification applied: {confidence:.3f}",
                    extra={
                        'request_id': request_id,
                        'confidence': confidence,
                        'domain': domain,
                        'action': action,
                        'confidence_level': confidence_level
                    }
                )

            # Track metrics for monitoring
            metrics = {
                'classification_method': 'llm',
                'confidence_score': confidence,
                'domain': domain,
                'action': action,
                'confidence_level': confidence_level,
                'application_timestamp': datetime.now(timezone.utc).isoformat()
            }

            # Log successful application
            logger.info(
                f"Applying LLM classification as final result: {domain}/{action} (confidence: {confidence:.3f})",
                extra={
                    'request_id': request_id,
                    'classification_source': classification_source,
                    'domain': domain,
                    'action': action,
                    'confidence': confidence,
                    'confidence_level': confidence_level,
                    'fallback_used': llm_classification.get('fallback_used', False)
                }
            )

        except Exception as e:
            error = str(e)
            classification_applied = False
            final_classification = None
            classification_source = 'error'

            logger.error(
                f"Error applying LLM classification: {error}",
                extra={
                    'request_id': request_id,
                    'error': error,
                    'step': 37
                }
            )

        # Build result preserving behavior while adding coordination metadata
        result = {
            'classification_applied': classification_applied,
            'final_classification': final_classification,
            'classification_source': classification_source,
            'confidence_level': confidence_level,
            'metrics': metrics,
            'request_id': request_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'error': error
        }

        rag_step_log(
            step=37,
            step_id='RAG.llm.use.llm.classification',
            node_label='UseLLM',
            category='llm',
            type='process',
            processing_stage='completed',
            request_id=request_id,
            classification_applied=classification_applied,
            classification_source=classification_source,
            confidence_level=confidence_level
        )

        return result

def step_67__llmsuccess(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 67 — LLM call successful?
    ID: RAG.llm.llm.call.successful
    Type: decision | Category: llm | Node: LLMSuccess

    TODO: Implement orchestration so this node *changes/validates control flow/data*
    according to Mermaid — not logs-only. Call into existing services/factories here.
    """
    with rag_step_timer(67, 'RAG.llm.llm.call.successful', 'LLMSuccess', stage="start"):
        rag_step_log(step=67, step_id='RAG.llm.llm.call.successful', node_label='LLMSuccess',
                     category='llm', type='decision', stub=True, processing_stage="started")
        # TODO: call real service/factory here and return its output
        result = kwargs.get("result")  # placeholder
        rag_step_log(step=67, step_id='RAG.llm.llm.call.successful', node_label='LLMSuccess',
                     processing_stage="completed")
        return result
