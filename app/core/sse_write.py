"""
SSE write helper with sampled logging.

This module tracks SSE frames written to client sockets with intelligent sampling
to reduce log noise while preserving visibility into streaming behavior.
"""

import json
import logging
import threading
from typing import Dict, Optional
from collections import defaultdict
from fastapi.responses import Response

logger = logging.getLogger(__name__)

# Thread-safe tracking for sampled logging
_write_stats_lock = threading.Lock()
_write_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {
    "count": 0,
    "total_bytes": 0,
    "first_chunk_logged": False
})


def write_sse(response, frame: str, request_id: Optional[str] = None) -> str:
    """
    Log an SSE frame with sampling to reduce log noise.

    Logs only the first 5 chunks per request at DEBUG level, then aggregates
    stats for a summary log at the end of the request.

    Args:
        response: The response object (can be None for generator context)
        frame: The SSE frame string to write
        request_id: Optional request identifier for tracking (defaults to "unknown")

    Returns:
        The same frame for yielding in the generator
    """
    req_id = request_id or "unknown"
    frame_len = len(frame)

    with _write_stats_lock:
        stats = _write_stats[req_id]
        stats["count"] += 1
        stats["total_bytes"] += frame_len
        write_count = stats["count"]

    # Log only first 5 chunks at DEBUG level
    if write_count <= 5:
        try:
            line = frame.strip()
            if line.startswith("data:"):
                payload = json.loads(line[len("data:"):].strip())
                logger.debug("SOCKET_WRITE [%s] chunk=%d seq=%s sha1=%s done=%s acc=%s raw=%s",
                             req_id, write_count,
                             payload.get("seq"), payload.get("sha1"), payload.get("done"),
                             payload.get("acc_len"), payload.get("raw_len"))
            else:
                logger.debug("SOCKET_WRITE [%s] chunk=%d raw_frame_len=%d",
                             req_id, write_count, frame_len)
        except Exception:
            logger.debug("SOCKET_WRITE [%s] chunk=%d raw_frame_len=%d (unparsed)",
                         req_id, write_count, frame_len)

    # For streaming response, we return the frame for yielding
    return frame


def log_sse_summary(request_id: Optional[str] = None) -> None:
    """
    Log aggregated statistics for SSE writes of a request.

    Should be called at the end of a streaming request to provide
    summary metrics without cluttering logs.

    Args:
        request_id: Request identifier to summarize (defaults to "unknown")
    """
    req_id = request_id or "unknown"

    with _write_stats_lock:
        if req_id not in _write_stats:
            return

        stats = _write_stats[req_id]
        total_chunks = stats["count"]
        total_bytes = stats["total_bytes"]

        # Clean up stats after logging
        del _write_stats[req_id]

    if total_chunks > 0:
        avg_chunk_size = total_bytes / total_chunks
        logger.info(
            "SSE_SUMMARY request_id=%s total_chunks=%d total_bytes=%d avg_chunk_size=%.1f",
            req_id, total_chunks, total_bytes, avg_chunk_size
        )