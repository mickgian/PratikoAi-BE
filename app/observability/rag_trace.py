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
- JSONL format for easy parsing
"""

import json
import logging
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

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
            # Build log entry matching the daily log format
            log_entry = {
                "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
                "level": record.levelname,
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

            # Write as JSONL (one JSON object per line)
            self.file_handle.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
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
    Write metadata header as first line of trace file.

    Args:
        file_handle: Open file handle
        request_id: Request identifier
        user_query: User's question that triggered this trace
    """
    try:
        header = {
            "trace_type": "rag_request",
            "session_id": request_id,
            "user_query": user_query[:200] if user_query else "N/A",  # Truncate long queries
            "timestamp_start": datetime.now(timezone.utc).isoformat(),
            "environment": settings.ENVIRONMENT.value,
        }
        file_handle.write(json.dumps(header, ensure_ascii=False) + "\n")
        file_handle.flush()
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to write trace header: {e}")


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
        file_handle.write(json.dumps(footer, ensure_ascii=False) + "\n")
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

            # Log summary (to daily logs, not trace file)
            if handler.steps_logged > 0:
                logging.getLogger(__name__).info(
                    f"RAG trace completed: {trace_file.name} "
                    f"({handler.steps_logged} steps logged)"
                )
