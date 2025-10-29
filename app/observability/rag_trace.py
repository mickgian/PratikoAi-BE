"""
Per-request RAG step tracing for development debugging.

This module provides request-scoped logging that captures only RAG step logs
into dedicated per-request files, making it easy to trace through all 135 steps
for a specific user question without log noise.

Usage:
    from app.observability.rag_trace import rag_trace_context

    with rag_trace_context(request_id=str(session.id), user_query="What is 2+2?"):
        result = await agent.get_response(...)

This creates a trace file: logs/rag_traces/trace_{session_id}_{timestamp}.jsonl
containing only RAG STEP logs for that specific request.

Features:
- Only enabled in development and staging environments
- Automatic cleanup of old traces
- Thread-safe handler management
- Zero impact on existing daily logs
- Pretty-printed JSON format for human readability (2-space indentation)
"""

import json
import logging
import re
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from app.core.config import Environment, settings

# Only enable per-request tracing in these environments
# Note: PREPROD does NOT get traces (mirrors production)
TRACE_ENABLED_ENVIRONMENTS = {
    Environment.DEVELOPMENT,
    Environment.QA,
}


class RAGTraceHandler(logging.Handler):
    """
    Custom logging handler that captures only RAG step logs to a request-specific file.

    Filters for logs from the "rag" logger and writes them to a dedicated JSONL file
    for the duration of a single request.
    """

    def __init__(self, trace_file: Path, request_id: str):
        """
        Initialize the RAG trace handler.

        Args:
            trace_file: Path to the trace file where logs will be written
            request_id: Unique identifier for this request (typically session.id)
        """
        super().__init__()
        self.trace_file = trace_file
        self.request_id = request_id
        self.steps_logged = 0
        self.file_handle = None

        # Ensure trace directory exists
        trace_file.parent.mkdir(parents=True, exist_ok=True)

        # Open file for writing
        try:
            self.file_handle = open(trace_file, "w", encoding="utf-8")
        except Exception as e:
            # If we can't create the trace file, log error but don't crash
            logging.getLogger(__name__).error(
                f"Failed to create RAG trace file {trace_file}: {e}"
            )

    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a log record to the trace file.

        Only processes records from the "rag" logger (RAG step logs).
        """
        if not self.file_handle:
            return

        # Filter: only log records from the "rag" logger
        if record.name != "rag":
            return

        try:
            # Check log entry fields for actual error indicators and upgrade log level
            level = record.levelname

            if level == "INFO" and hasattr(record, "extra"):
                extra = record.extra if hasattr(record, "extra") else {}
                # Look for error indicators in extra fields
                if extra.get("error") and extra.get("error") not in ["", None]:
                    level = "ERROR"
                elif any(extra.get(key) == "failed" for key in ["processing_stage", "status"]):
                    level = "ERROR"
                elif extra.get("classification_event") == "rule_based_classification_failed":
                    level = "ERROR"
                elif "failed" in str(extra.get("processing_stage", "")).lower():
                    level = "ERROR"

            # Build log entry matching the daily log format
            log_entry = {
                "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
                "level": level,  # Use upgraded level if error detected
                "message": record.getMessage(),
                "module": record.module,
                "function": record.funcName,
                "filename": record.pathname,
                "line": record.lineno,
                "environment": settings.ENVIRONMENT.value,
            }

            # Add any extra fields from the record
            if hasattr(record, "extra"):
                log_entry.update(record.extra)

            # Serialize to JSON with indentation for human readability
            json_line = json.dumps(log_entry, ensure_ascii=False, indent=2)

            # Write as formatted JSON with separator for readability
            self.file_handle.write(json_line + "\n")
            self.file_handle.flush()  # Ensure immediate write
            self.steps_logged += 1

        except Exception as e:
            # If logging fails, continue without crashing
            self.handleError(record)

    def close(self) -> None:
        """Close the trace file handle."""
        if self.file_handle:
            try:
                self.file_handle.close()
            except Exception:
                pass
            self.file_handle = None
        super().close()


def _get_trace_filename(request_id: str) -> Path:
    """
    Generate a trace filename for a given request.

    Format: trace_{request_id}_{timestamp}.jsonl

    Args:
        request_id: Unique request identifier (session.id)

    Returns:
        Path to the trace file
    """
    # Use ISO format timestamp for sortability
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")

    # Sanitize request_id to remove problematic characters
    safe_request_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in request_id)

    # Truncate if too long (keep first 32 chars of request_id)
    if len(safe_request_id) > 32:
        safe_request_id = safe_request_id[:32]

    filename = f"trace_{safe_request_id}_{timestamp}.jsonl"
    return settings.LOG_DIR / "rag_traces" / filename


def _write_trace_header(file_handle, request_id: str, user_query: str) -> None:
    """
    Write metadata header and placeholder summary at start of trace file.

    Args:
        file_handle: Open file handle
        request_id: Request identifier
        user_query: User's question that triggered this trace
    """
    try:
        # Write summary placeholder
        summary_placeholder = """/*
================================================================================
                       RAG EXECUTION FLOW SUMMARY
================================================================================
(Analysis will appear here after execution completes)
================================================================================
*/

"""
        file_handle.write(summary_placeholder)

        # Write request metadata header
        header = {
            "trace_type": "rag_request",
            "session_id": request_id,
            "user_query": user_query[:200] if user_query else "N/A",  # Truncate long queries
            "timestamp_start": datetime.now(timezone.utc).isoformat(),
            "environment": settings.ENVIRONMENT.value,
        }
        file_handle.write(json.dumps(header, ensure_ascii=False, indent=2) + "\n")
        file_handle.flush()
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to write trace header: {e}")


def _parse_diagram_flow() -> Tuple[Dict[str, List[Tuple[Optional[str], str]]], Dict[str, str], Set[str], Set[str]]:
    """
    Parse pratikoai_rag_hybrid.mmd to extract expected step transitions, descriptions, and classifications.

    Returns:
        Tuple of (flow_map, step_descriptions, canonical_steps, internal_steps):
        - flow_map: Dictionary mapping step IDs to list of (condition, next_step) tuples
          Example: {"S001": [(None, "S002")], "S003": [("Yes", "S004"), ("No", "S005")]}
        - step_descriptions: Dictionary mapping step IDs to their descriptions
          Example: {"S001": "User submits query", "S002": "Validate request"}
        - canonical_steps: Set of step IDs marked as Canonical Nodes (runtime boundaries)
          Example: {"S002", "S003", "S006", "S009", ...}
        - internal_steps: Set of step IDs marked as Internal Steps (pure transforms)
          Example: {"S001", "S004", "S005", "S007", ...}
    """
    # Get project root (4 levels up from this file: app/observability/rag_trace.py)
    project_root = Path(__file__).parent.parent.parent
    diagram_path = project_root / "docs/architecture/diagrams/pratikoai_rag_hybrid.mmd"
    flow_map: Dict[str, List[Tuple[Optional[str], str]]] = {}
    step_descriptions: Dict[str, str] = {}
    canonical_steps: Set[str] = set()
    internal_steps: Set[str] = set()

    try:
        # Check if diagram file exists before trying to open it
        if not diagram_path.exists():
            logging.getLogger(__name__).error(
                f"Diagram file not found at {diagram_path}. "
                f"Trace summaries will have no descriptions. "
                f"Check that docs/ directory is mounted in Docker or included in build."
            )
            return flow_map, step_descriptions, canonical_steps, internal_steps

        with open(diagram_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Special case: Match Start node with embedded S001
        # Pattern: Start([S001 · Description]) --> S002
        start_pattern = r'Start\(\[(S\d+)\s*·\s*([^\]]+)\]\)\s*-->\s*(S\d+)'
        start_match = re.search(start_pattern, content)
        if start_match:
            start_step = start_match.group(1)  # S001
            start_desc = start_match.group(2).strip()  # Description
            next_step = start_match.group(3)  # S002
            flow_map[start_step] = [(None, next_step)]
            step_descriptions[start_step] = start_desc

        # Match regular nodes with descriptions
        # Pattern: S001[S001 · Description] or S001{S001 · Description}
        node_pattern = r'(S\d+)[\[\{](S\d+)\s*·\s*([^\]\}]+)[\]\}]'
        for match in re.finditer(node_pattern, content):
            step_id = match.group(2)  # S002, S003, etc.
            description = match.group(3).strip()
            # Clean up HTML tags like <br/>
            description = re.sub(r'<br\s*/?>', ' ', description)
            step_descriptions[step_id] = description

        # Match edges: S001 --> S003 or S003 -->|Yes| S004
        # Also match edges involving database nodes: S059 --> RedisCache or RedisCache --> S062
        edge_pattern = r'(S\d+|[\w]+)\s*-->\s*(?:\|([^|]+)\|)?\s*(S\d+|[\w]+)'

        for match in re.finditer(edge_pattern, content):
            from_node = match.group(1)
            condition = match.group(2).strip() if match.group(2) else None
            to_node = match.group(3)

            # Only store edges involving at least one S### step
            if from_node.startswith('S') or to_node.startswith('S'):
                if from_node not in flow_map:
                    flow_map[from_node] = []
                flow_map[from_node].append((condition, to_node))

        # Parse step classifications (Canonical vs Internal)
        # Pattern: class S001,S002,S003 canonicalNode
        canonical_pattern = r'class\s+([\w,]+)\s+canonicalNode'
        canonical_match = re.search(canonical_pattern, content)
        if canonical_match:
            step_list = canonical_match.group(1)
            # Split by comma and filter for S### pattern
            for step in step_list.split(','):
                step = step.strip()
                if re.match(r'S\d+', step):
                    canonical_steps.add(step)

        # Pattern: class Start,S001,S004 internalNode
        internal_pattern = r'class\s+([\w,]+)\s+internalNode'
        internal_match = re.search(internal_pattern, content)
        if internal_match:
            step_list = internal_match.group(1)
            # Split by comma and filter for S### pattern
            for step in step_list.split(','):
                step = step.strip()
                if re.match(r'S\d+', step):
                    internal_steps.add(step)

        # Log success for debugging
        logging.getLogger(__name__).debug(
            f"Successfully parsed diagram: {len(flow_map)} transitions, {len(step_descriptions)} descriptions, "
            f"{len(canonical_steps)} canonical nodes, {len(internal_steps)} internal steps"
        )

    except Exception as e:
        logging.getLogger(__name__).error(
            f"Failed to parse diagram flow from {diagram_path}: {type(e).__name__}: {e}",
            exc_info=True
        )

    return flow_map, step_descriptions, canonical_steps, internal_steps


def _find_path_between_steps(
    from_step: str,
    to_step: str,
    flow_map: Dict[str, List[Tuple[Optional[str], str]]],
    max_depth: int = 50
) -> Optional[List[str]]:
    """
    Find the path between two steps in the flow diagram using BFS.

    Args:
        from_step: Starting step ID (e.g., "S059")
        to_step: Destination step ID (e.g., "S062")
        flow_map: Diagram flow map
        max_depth: Maximum path length to search

    Returns:
        List of intermediate step IDs (excluding from_step and to_step), or None if no path found
        Example: If path is S059→S060→S061→S062, returns ["S060", "S061"]
    """
    from collections import deque

    # BFS to find shortest path
    queue = deque([(from_step, [])])
    visited = {from_step}

    while queue and len(visited) <= max_depth:
        current, path = queue.popleft()

        # Get next steps from flow map
        next_steps = flow_map.get(current, [])

        for _, next_step in next_steps:
            if next_step == to_step:
                # Found the path
                return path

            if next_step not in visited:
                visited.add(next_step)
                queue.append((next_step, path + [next_step]))

    return None


def _is_internal_only_path(
    intermediate_steps: List[str],
    internal_steps: Set[str]
) -> bool:
    """
    Check if all steps in the path are Internal steps (or database nodes).

    Args:
        intermediate_steps: List of step IDs/node names between from→to
        internal_steps: Set of step IDs marked as Internal

    Returns:
        True if all intermediate steps are Internal or database nodes, False otherwise
    """
    for step in intermediate_steps:
        # Allow database nodes (don't start with 'S') and Internal steps
        if step.startswith('S') and step not in internal_steps:
            # It's a Canonical step, not allowed
            return False
    return True


def _analyze_trace_execution(trace_file_path: Path) -> Tuple[List[str], List[Tuple[str, str]], Dict[str, float]]:
    """
    Analyze trace file to extract actual step execution sequence and timing data.

    Args:
        trace_file_path: Path to the trace file

    Returns:
        Tuple of (step_sequence, transitions, step_timings):
        - step_sequence: List of step IDs in execution order ["S001", "S004", ...]
        - transitions: List of (from_step, to_step) tuples [("S001", "S004"), ...]
        - step_timings: Dict mapping step IDs to latency in ms {"S008": 1.19, ...}
    """
    step_sequence: List[str] = []
    step_timings: Dict[str, float] = {}
    active_wrappers: Set[str] = set()  # Track steps currently inside .enter/.exit
    steps_with_enter_logs: Set[str] = set()  # Track which steps have .enter logs
    steps_counted_via_orchestrator: Set[str] = set()  # Track steps already counted via orchestrator logs
    reached_end_step = False  # Track when S112 (END) is reached

    # PASS 1: Scan file to identify which steps have .enter logs
    # This prevents double-counting when orchestrator logs appear before .enter logs
    try:
        with open(trace_file_path, "r", encoding="utf-8") as f:
            for line in f:
                if 'RAG STEP' in line and '.enter' in line:
                    step_match = re.search(r'RAG STEP (\d+)', line)
                    if step_match:
                        step_num = int(step_match.group(1))
                        step_id = f"S{step_num:03d}"
                        steps_with_enter_logs.add(step_id)
    except Exception as e:
        logging.getLogger(__name__).warning(f"Pass 1 scan failed: {e}")

    # PASS 2: Analyze execution sequence
    try:
        with open(trace_file_path, "r", encoding="utf-8") as f:
            in_comment = False
            json_buffer = []

            for line in f:
                # Skip comment block
                if line.strip().startswith("/*"):
                    in_comment = True
                    continue
                if in_comment:
                    if line.strip().endswith("*/"):
                        in_comment = False
                    continue

                # Skip empty lines
                if not line.strip():
                    continue

                # Accumulate lines for multi-line JSON objects
                json_buffer.append(line)

                # Check if we have a complete JSON object (ends with })
                if line.strip() == "}":
                    try:
                        # Join buffered lines and parse as JSON
                        json_text = "".join(json_buffer)
                        log_entry = json.loads(json_text)

                        # Clear buffer for next object
                        json_buffer = []

                        # Extract step number from RAG STEP logs
                        message = log_entry.get("message", "")
                        step_match = re.search(r'RAG STEP (\d+)', message)

                        if step_match:
                            step_num = int(step_match.group(1))
                            step_id = f"S{step_num:03d}"

                            # Filter duplicates caused by enter/exit logging
                            # Node wrappers log: step_XXX.enter → [inner steps] → step_XXX.exit → step_XXX (summary)
                            # We only want to count ONCE per node execution

                            # Check if this is a node wrapper log (has .enter/.exit/no suffix)
                            is_node_enter = ".enter" in message
                            is_node_exit = ".exit" in message
                            is_node_summary = re.search(r'step_\d+\s*\|', message) and not is_node_enter and not is_node_exit

                            # Track node wrapper state for stateful filtering
                            if is_node_enter:
                                active_wrappers.add(step_id)
                            elif is_node_exit:
                                active_wrappers.discard(step_id)

                            # For orchestrator logs (without .enter/.exit pattern), parse attributes
                            attrs_match = re.search(r'attrs=(\{.*\})', message)
                            is_timing_log = False
                            has_processing_stage = False
                            processing_stage_value = None

                            if attrs_match:
                                try:
                                    attrs = json.loads(attrs_match.group(1))

                                    # Check if this is a timing/metric log
                                    # Timing logs have "latency_ms" + "stage" (NOT "processing_stage")
                                    # These are emitted AFTER orchestrator completes for metrics
                                    has_latency = "latency_ms" in attrs
                                    has_stage = "stage" in attrs
                                    has_processing_stage = "processing_stage" in attrs
                                    processing_stage_value = attrs.get("processing_stage")

                                    # Timing log = has both latency_ms and stage, but NOT processing_stage
                                    is_timing_log = has_latency and has_stage and not has_processing_stage
                                except (json.JSONDecodeError, ValueError):
                                    pass

                            # Decision: Count if it's an "entry" to the step
                            # HYBRID STRATEGY: Count BOTH node wrappers AND orchestrator-only steps
                            # 1. Node wrapper .enter logs (for graph nodes like S008, S011, S034, etc.)
                            # 2. Orchestrator logs with ANY processing_stage (for orchestrator-only steps like S001-S007, S014-S019)
                            #    BUT only if no .enter log exists for that step (to avoid double-counting)
                            should_count = False
                            if is_node_enter:
                                # Node wrapper entry - always count
                                should_count = True
                            elif not is_node_exit and not is_node_summary and not is_timing_log:
                                # This is an orchestrator log (no .enter/.exit pattern)
                                # Count FIRST occurrence with ANY processing_stage value if:
                                # 1. It has processing_stage (any value: started, completed, decision, received)
                                # 2. No .enter log exists for this step (orchestrator-only step)
                                # 3. Not already counted via orchestrator log (first occurrence only)
                                if has_processing_stage:
                                    if step_id not in steps_with_enter_logs and step_id not in steps_counted_via_orchestrator:
                                        should_count = True
                                        steps_counted_via_orchestrator.add(step_id)

                            # Add to sequence if we should count it and it's not a duplicate
                            # BUT stop counting after S112 (END step) - anything after is orphaned logging
                            if should_count and not reached_end_step:
                                if not step_sequence or step_sequence[-1] != step_id:
                                    step_sequence.append(step_id)

                                    # Check if this is S112 (END step)
                                    if step_id == "S112":
                                        reached_end_step = True

                            # Extract timing data from attrs JSON in message
                            # Message format: "RAG STEP X (...): ... | attrs={...}"
                            attrs_match = re.search(r'attrs=(\{.*\})', message)
                            if attrs_match:
                                try:
                                    attrs = json.loads(attrs_match.group(1))
                                    latency_ms = attrs.get("latency_ms")
                                    if latency_ms is not None:
                                        # Store or accumulate timing for this step
                                        if step_id in step_timings:
                                            step_timings[step_id] += float(latency_ms)
                                        else:
                                            step_timings[step_id] = float(latency_ms)
                                except (json.JSONDecodeError, ValueError):
                                    pass

                    except json.JSONDecodeError:
                        # Clear buffer and continue
                        json_buffer = []
                        continue

    except Exception as e:
        logging.getLogger(__name__).warning(f"Failed to analyze trace: {e}")

    # Build transitions from sequence
    transitions = []
    for i in range(len(step_sequence) - 1):
        transitions.append((step_sequence[i], step_sequence[i+1]))

    return step_sequence, transitions, step_timings


def _generate_flow_summary(
    step_sequence: List[str],
    transitions: List[Tuple[str, str]],
    expected_flow: Dict[str, List[Tuple[Optional[str], str]]],
    step_timings: Dict[str, float],
    step_descriptions: Dict[str, str],
    canonical_steps: Set[str],
    internal_steps: Set[str]
) -> str:
    """
    Generate human-readable flow summary with conformance checking, timing data, and step descriptions.

    Args:
        step_sequence: Actual execution sequence
        transitions: Actual transitions
        expected_flow: Expected flow from diagram
        step_timings: Dict mapping step IDs to latency in ms
        step_descriptions: Dict mapping step IDs to their descriptions
        canonical_steps: Set of Canonical Node step IDs
        internal_steps: Set of Internal Step IDs

    Returns:
        Formatted summary string with colors, timing info, and descriptions
    """
    lines = []
    lines.append("=" * 80)
    lines.append("RAG EXECUTION FLOW SUMMARY".center(80))
    lines.append("=" * 80)
    lines.append("")

    # Overall stats
    total_steps_executed = len(step_sequence)
    total_transitions = len(transitions)

    # Calculate total execution time
    total_time_ms = sum(step_timings.values())
    total_time_s = total_time_ms / 1000.0
    avg_step_ms = total_time_ms / total_steps_executed if total_steps_executed > 0 else 0

    # Check conformance (including transitions that skip only Internal steps)
    conforming_transitions = 0
    non_conforming = []

    for from_step, to_step in transitions:
        expected_nexts = expected_flow.get(from_step, [])
        expected_steps = [next_step for _, next_step in expected_nexts]

        if to_step in expected_steps:
            # Direct match
            conforming_transitions += 1
        else:
            # Check if it's a valid Canonical→Canonical transition via Internal steps
            intermediate_path = _find_path_between_steps(from_step, to_step, expected_flow)
            if intermediate_path is not None and _is_internal_only_path(intermediate_path, internal_steps):
                # Valid transition via internal steps
                conforming_transitions += 1
            else:
                # Non-conforming transition
                non_conforming.append((from_step, to_step, expected_steps))

    conformance_pct = (
        round(100 * conforming_transitions / total_transitions)
        if total_transitions > 0 else 100
    )

    lines.append(f"Steps Executed: {total_steps_executed}")
    lines.append(f"Transitions: {total_transitions}")
    lines.append(f"Total Execution Time: {total_time_ms:,.2f}ms ({total_time_s:.2f}s)")
    lines.append(f"Average Step Duration: {avg_step_ms:.2f}ms")
    lines.append(f"Flow Conformance: {conformance_pct}% ({conforming_transitions}/{total_transitions} match diagram)")
    lines.append("")

    # Show all transition details with timing
    lines.append("TRANSITION ANALYSIS:")
    lines.append("-" * 80)

    for i, (from_step, to_step) in enumerate(transitions):
        expected_nexts = expected_flow.get(from_step, [])
        expected_steps = [next_step for _, next_step in expected_nexts]

        # Get step descriptions (truncate to 25 chars for readability)
        from_desc = step_descriptions.get(from_step, "")[:25]
        to_desc = step_descriptions.get(to_step, "")[:25]

        # Determine step type labels
        from_type = "(INTERNAL)" if from_step in internal_steps else "(CANONICAL)" if from_step in canonical_steps else ""
        to_type = "(INTERNAL)" if to_step in internal_steps else "(CANONICAL)" if to_step in canonical_steps else ""

        # Format step labels with type and descriptions
        # Format: S036 (INTERNAL) (LLM better than rule-base)
        from_label = f"{from_step} {from_type} ({from_desc})" if from_desc else f"{from_step} {from_type}"
        to_label = f"{to_step} {to_type} ({to_desc})" if to_desc else f"{to_step} {to_type}"

        # Clean up extra spaces
        from_label = from_label.replace("  ", " ").strip()
        to_label = to_label.replace("  ", " ").strip()

        # Get timing for the destination step
        timing_str = f" {step_timings.get(to_step, 0.0):.2f}ms" if to_step in step_timings else ""

        # Add annotation for final step (S112)
        end_annotation = "  ← Last transition" if to_step == "S112" else ""

        if to_step in expected_steps:
            # Direct match - expected transition
            condition = next((cond for cond, step in expected_nexts if step == to_step), None)
            cond_str = f" [{condition}]" if condition else ""
            lines.append(f"✅ {from_label} → {to_label}{cond_str} {timing_str}{end_annotation}")
        else:
            # Not a direct match - check if it's a valid Canonical→Canonical transition
            # that skips only Internal steps
            intermediate_path = _find_path_between_steps(from_step, to_step, expected_flow)

            if intermediate_path is not None and _is_internal_only_path(intermediate_path, internal_steps):
                # Valid transition - skipped only Internal steps
                internal_names = ", ".join(intermediate_path)
                lines.append(f"✅ {from_label} → {to_label} (via internal: {internal_names}) {timing_str}{end_annotation}")
            else:
                # Invalid transition
                expected_str = ", ".join(expected_steps) if expected_steps else "END"
                lines.append(f"❌ {from_label} → {to_label} (Expected: {expected_str}) {timing_str}{end_annotation}")

    # Add performance insights section
    if step_timings:
        lines.append("")
        lines.append("PERFORMANCE INSIGHTS:")
        lines.append("-" * 80)

        # Sort steps by timing (slowest first)
        sorted_timings = sorted(step_timings.items(), key=lambda x: x[1], reverse=True)

        lines.append("Top 15 Slowest Steps:")
        for i, (step_id, latency_ms) in enumerate(sorted_timings[:15], 1):
            # Get description
            desc = step_descriptions.get(step_id, "")
            desc_str = f" ({desc[:40]})" if desc else ""
            # Format with padding for alignment
            lines.append(f"  {i}. {step_id}{desc_str}: {latency_ms:,.2f}ms")

    lines.append("")
    lines.append("=" * 80)
    lines.append("")

    return "\n".join(lines)


def _write_trace_footer(
    file_handle, request_id: str, start_time: float, steps_logged: int
) -> None:
    """
    Write completion metadata as last line of trace file.

    Args:
        file_handle: Open file handle
        request_id: Request identifier
        start_time: Timestamp when tracing started (from time.time())
        steps_logged: Number of RAG step logs captured
    """
    try:
        duration_ms = round((time.time() - start_time) * 1000.0, 2)
        footer = {
            "trace_type": "rag_request_complete",
            "session_id": request_id,
            "timestamp_end": datetime.now(timezone.utc).isoformat(),
            "duration_ms": duration_ms,
            "steps_logged": steps_logged,
        }
        file_handle.write(json.dumps(footer, ensure_ascii=False, indent=2) + "\n")
        file_handle.flush()
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to write trace footer: {e}")


@contextmanager
def rag_trace_context(request_id: str, user_query: Optional[str] = None):
    """
    Context manager for per-request RAG step tracing.

    Creates a dedicated log file for this request containing only RAG step logs.
    Automatically attaches and detaches a custom handler from the "rag" logger.

    Only active in development and staging environments. In production/test,
    this is a no-op context manager that yields immediately.

    Args:
        request_id: Unique identifier for this request (typically session.id)
        user_query: User's question (for metadata header)

    Yields:
        None

    Example:
        with rag_trace_context(str(session.id), "What is 2+2?"):
            result = await agent.get_response(messages, session.id)

    This creates: logs/rag_traces/trace_{session_id}_{timestamp}.jsonl
    """
    # Gate: Only enable in development and staging
    if settings.ENVIRONMENT not in TRACE_ENABLED_ENVIRONMENTS:
        # No-op in production/test
        yield
        return

    # Get the "rag" logger that all RAG steps log to
    rag_logger = logging.getLogger("rag")

    # Generate trace filename
    trace_file = _get_trace_filename(request_id)

    # Create and configure handler
    handler = None
    start_time = time.time()

    try:
        handler = RAGTraceHandler(trace_file, request_id)
        handler.setLevel(logging.DEBUG)  # Capture all RAG step logs

        # Write metadata header
        if handler.file_handle:
            _write_trace_header(handler.file_handle, request_id, user_query or "N/A")

        # Attach handler to rag logger
        rag_logger.addHandler(handler)

        # Yield control to the request processing
        yield

    finally:
        # Clean up: detach handler and close file
        if handler:
            # Write metadata footer
            if handler.file_handle:
                _write_trace_footer(
                    handler.file_handle, request_id, start_time, handler.steps_logged
                )

            # Detach from logger
            rag_logger.removeHandler(handler)

            # Close file
            handler.close()

            # Generate and replace summary placeholder after trace completes
            if handler.steps_logged > 0:
                try:
                    # Parse expected flow, descriptions, and step classifications from diagram
                    expected_flow, step_descriptions, canonical_steps, internal_steps = _parse_diagram_flow()

                    # Analyze actual execution (now includes timing data)
                    step_sequence, transitions, step_timings = _analyze_trace_execution(trace_file)

                    # Generate summary with timing info, descriptions, and step classifications
                    summary = _generate_flow_summary(
                        step_sequence, transitions, expected_flow, step_timings, step_descriptions,
                        canonical_steps, internal_steps
                    )

                    # Replace placeholder with actual summary
                    # Read existing content
                    with open(trace_file, "r", encoding="utf-8") as f:
                        existing_content = f.read()

                    # Find and replace the placeholder summary
                    placeholder_start = existing_content.find("/*\n================")
                    placeholder_end = existing_content.find("*/\n\n", placeholder_start) + 4

                    if placeholder_start != -1 and placeholder_end > placeholder_start:
                        # Replace placeholder with actual summary
                        new_content = (
                            existing_content[:placeholder_start] +
                            "/*\n" + summary + "*/\n\n" +
                            existing_content[placeholder_end:]
                        )

                        # Write updated content
                        with open(trace_file, "w", encoding="utf-8") as f:
                            f.write(new_content)

                except Exception as e:
                    logging.getLogger(__name__).warning(
                        f"Failed to generate flow summary for {trace_file.name}: {e}"
                    )

                # Log summary (to daily logs, not trace file)
                logging.getLogger(__name__).info(
                    f"RAG trace completed: {trace_file.name} "
                    f"({handler.steps_logged} steps logged)"
                )
