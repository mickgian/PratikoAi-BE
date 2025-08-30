"""
SSE write helper with detailed logging.

This module logs exactly what is written to the client socket
to help trace duplicate content issues.
"""

import json
import logging
from fastapi.responses import Response

logger = logging.getLogger(__name__)


def write_sse(response, frame: str) -> str:
    """
    Log an SSE frame that will be written to the response.
    
    Args:
        response: The response object (can be None for generator context)
        frame: The SSE frame string to write
        
    Returns:
        The same frame for yielding in the generator
    """
    # Try to parse payload for logging
    try:
        line = frame.strip()
        if line.startswith("data:"):
            payload = json.loads(line[len("data:"):].strip())
            logger.debug("SOCKET_WRITE seq=%s sha1=%s done=%s acc=%s raw=%s",
                         payload.get("seq"), payload.get("sha1"), payload.get("done"),
                         payload.get("acc_len"), payload.get("raw_len"))
        else:
            logger.debug("SOCKET_WRITE raw_frame_len=%d", len(frame))
    except Exception:
        logger.debug("SOCKET_WRITE raw_frame_len=%d (unparsed)", len(frame))
    
    # For streaming response, we return the frame for yielding
    return frame