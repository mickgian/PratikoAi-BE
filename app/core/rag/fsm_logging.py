"""FSM (Finite State Machine) decision logging for RAG workflow.

This module provides structured JSON logging for:
- FSM state transitions
- Guard evaluations
- Decision points
- Violations and anomalies
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from app.core.logging import logger


def log_gate_decision(
    state: str,
    needs_retrieval: bool,
    reasons: List[str],
    query: Optional[str] = None
) -> None:
    """Log a retrieval gate decision (S034a).

    Args:
        state: FSM state (usually "S034a")
        needs_retrieval: Whether retrieval is needed
        reasons: List of reasons for the decision
        query: Optional query text (truncated in logs for privacy)
    """
    log_data = {
        "event": "gate_decision",
        "state": state,
        "needs_retrieval": needs_retrieval,
        "reasons": reasons,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    if query:
        # Truncate query for logging (privacy)
        log_data["query_preview"] = query[:100] + ("..." if len(query) > 100 else "")

    logger.info(log_data)


def log_golden_check(
    state: str,
    confidence: float,
    kb_epoch: int,
    golden_epoch: int,
    serve: bool,
    reason: Optional[str] = None
) -> None:
    """Log a Golden fast-path eligibility check (S027).

    Args:
        state: FSM state (usually "S027")
        confidence: Confidence score of the Golden match
        kb_epoch: Current knowledge base epoch
        golden_epoch: Epoch when Golden answer was created
        serve: Whether Golden answer will be served
        reason: Optional reason for the decision
    """
    logger.info({
        "event": "golden_check",
        "state": state,
        "confidence": confidence,
        "kb_epoch": kb_epoch,
        "golden_epoch": golden_epoch,
        "serve": serve,
        "reason": reason or ("epoch_mismatch" if kb_epoch > golden_epoch else "ok"),
        "timestamp": datetime.now(timezone.utc).isoformat()
    })


def log_fsm_violation(
    state: str,
    actual_next: str,
    expected_next: str,
    guard_eval: Optional[Dict[str, Any]] = None,
    severity: str = "error"
) -> None:
    """Log an FSM transition violation.

    This logs when the system takes an unexpected transition
    that violates the FSM specification.

    Args:
        state: Current FSM state
        actual_next: Actual next state taken
        expected_next: Expected next state according to FSM
        guard_eval: Optional dictionary of guard evaluations
        severity: Severity level ("error", "warning", "info")
    """
    log_data = {
        "event": "fsm_violation",
        "state": state,
        "actual_next": actual_next,
        "expected_next": expected_next,
        "guard_eval": guard_eval or {},
        "severity": severity,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    if severity == "error":
        logger.error(log_data)
    elif severity == "warning":
        logger.warning(log_data)
    else:
        logger.info(log_data)


def log_fsm_transition(
    from_state: str,
    to_state: str,
    guard: Optional[str] = None,
    guard_result: Optional[bool] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """Log a successful FSM state transition.

    Args:
        from_state: Source state
        to_state: Destination state
        guard: Name of the guard condition (if any)
        guard_result: Result of guard evaluation (if applicable)
        metadata: Additional metadata about the transition
    """
    log_data = {
        "event": "fsm_transition",
        "from_state": from_state,
        "to_state": to_state,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    if guard:
        log_data["guard"] = guard
        if guard_result is not None:
            log_data["guard_result"] = guard_result

    if metadata:
        log_data["metadata"] = metadata

    logger.debug(log_data)


def log_cache_decision(
    state: str,
    cache_key: str,
    hit: bool,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """Log a cache hit/miss decision.

    Args:
        state: FSM state where cache was checked
        cache_key: Cache key (truncated)
        hit: Whether cache was hit
        metadata: Additional metadata (epochs, provider, etc.)
    """
    logger.info({
        "event": "cache_decision",
        "state": state,
        "cache_key": cache_key[:16] + "...",  # Truncate for readability
        "hit": hit,
        "metadata": metadata or {},
        "timestamp": datetime.now(timezone.utc).isoformat()
    })


def log_policy_violation(
    policy: str,
    violation_type: str,
    details: Dict[str, Any],
    severity: str = "warning"
) -> None:
    """Log a policy violation.

    Args:
        policy: Name of the violated policy
        violation_type: Type of violation
        details: Details about the violation
        severity: Severity level
    """
    log_data = {
        "event": "policy_violation",
        "policy": policy,
        "violation_type": violation_type,
        "details": details,
        "severity": severity,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    if severity == "error":
        logger.error(log_data)
    elif severity == "warning":
        logger.warning(log_data)
    else:
        logger.info(log_data)
