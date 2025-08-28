"""
Enhanced streaming processor that ensures pure HTML output with deduplication.

This module provides a robust streaming processor that:
- Converts all content to HTML (no markdown ever sent to frontend)
- Prevents duplicate content through smart deduplication
- Emits only delta chunks (new content only)
- Provides comprehensive DEBUG logging
"""

import re
import json
import logging
import hashlib
import time
import os
from typing import Optional, AsyncGenerator
import markdown2

logger = logging.getLogger(__name__)


class EnhancedStreamingProcessor:
    """
    Processes streaming LLM tokens to ensure pure HTML output with no duplication.
    
    Key features:
    - Always converts markdown to HTML before emitting
    - Tracks accumulated content to prevent duplicates
    - Emits only deltas (new content) never full replays
    - Comprehensive logging for debugging
    """
    
    def __init__(self, stream_id: str | None = None):
        """Initialize the streaming processor."""
        self.accumulated_html = ""  # Track all emitted HTML
        self.accumulated_raw = ""   # Track raw input for debugging
        self.frame_count = 0
        self.total_bytes_emitted = 0
        self.seq = 0
        self.stream_id = stream_id or f"{int(time.time()*1000)}-{os.getpid()}"
        self.markdown_converter = markdown2.Markdown(
            extras=[
                "tables",
                "fenced-code-blocks",
                "strike",
                "target-blank-links",
            ]
        )
        
    # (Optional) We no longer branch on format; conversion is always applied.
    def _detect_format(self, text: str) -> str:
        # Keep only for logging parity; not used for branching.
        return "mixed"
    
    def _normalize_to_html(self, text: str) -> str:
        """
        Always convert the entire accumulated RAW buffer to HTML.
        markdown2 preserves existing HTML, so mixed content is safe.
        """
        if not text:
            return ""
        html = self.markdown_converter.convert(text)
        # Optional: unwrap single paragraph to keep deltas smaller.
        if html.startswith('<p>') and html.endswith('</p>') and html.count('<p>') == 1:
            html = html[3:-4]
        return html.rstrip('\n\r')

    # Helpers for robust duplicate detection
    def _strip_tags(self, s: str) -> str:
        return re.sub(r'<[^>]*>', '', s or '')

    def _norm_text(self, s: str) -> str:
        # Lowercase + collapse whitespace for resilient matching
        return re.sub(r'\s+', ' ', self._strip_tags(s)).strip().lower()
    
    def _compute_delta(self, new_content: str) -> str:
        """
        Compute the delta between accumulated and new content.
        """
        if not new_content:
            return ""

        # If accumulated is empty, everything is new
        if not self.accumulated_html:
            return new_content

        # Check if new content is already in accumulated (duplicate)
        if new_content in self.accumulated_html:
            logger.debug(
                f"Duplicate content detected, skipping {len(new_content)} bytes"
            )
            return ""

        # Check if accumulated is prefix of new content (continuation)
        if new_content.startswith(self.accumulated_html):
            delta = new_content[len(self.accumulated_html):]
        # Check for overlap - new content might contain accumulated somewhere
        elif self.accumulated_html in new_content:
            last_idx = new_content.rfind(self.accumulated_html)
            delta = new_content[last_idx + len(self.accumulated_html):]
        else:
            # No clear relationship - this might be a format switch or provider replay.
            logger.warning(
                "Content discontinuity detected - accumulated=%sB, new=%sB",
                len(self.accumulated_html), len(new_content)
            )
            delta = new_content

        # 🔐 Second-start guard: if delta seems to re-begin from the head, trim it.
        head = self.accumulated_html[:120]  # first 120 chars of emitted HTML
        head_norm = self._norm_text(head)
        delta_norm = self._norm_text(delta)
        pos = delta_norm.find(head_norm)
        if pos != -1:
            # Map approximately to raw index by searching in tagless views
            raw_pos = self._strip_tags(delta).lower().find(self._strip_tags(head).lower())
            if raw_pos != -1:
                logger.warning(
                    "Second-start detected in delta; trimming duplicate restart "
                    "(head_len=%s, delta_len=%s, cut_at=%s)",
                    len(head), len(delta), raw_pos
                )
                delta = delta[:raw_pos]
        return delta
    
    async def process_chunk(self, raw_chunk: str) -> Optional[str]:
        """
        Process a raw chunk from LLM and return HTML delta if any.
        
        Args:
            raw_chunk: Raw text chunk from LLM
            
        Returns:
            HTML delta to emit, or None if nothing new
        """
        if not raw_chunk:
            return None
        
        # Accumulate raw input for debugging
        self.accumulated_raw += raw_chunk
        
        # Strip trailing newlines from chunk
        raw_chunk = raw_chunk.rstrip('\r\n')
        
        # Always normalize entire RAW buffer to HTML
        format_type = self._detect_format(self.accumulated_raw)  # for logging only
        normalized_html = self._normalize_to_html(self.accumulated_raw)
        
        # Compute delta
        delta = self._compute_delta(normalized_html)
        
        if delta:
            # Skip whitespace-only deltas unless they contain HTML tags
            if not re.search(r'\S|<[^>]+>', delta):
                return None
            
            # Update accumulated HTML
            self.accumulated_html = normalized_html
            self.frame_count += 1
            self.total_bytes_emitted += len(delta)
            
            # Log at DEBUG level
            raw_preview = raw_chunk[:50] + "..." if len(raw_chunk) > 50 else raw_chunk
            logger.debug(
                f"Streaming chunk processed - format: {format_type}, delta: {len(delta)} bytes, "
                f"total: {len(self.accumulated_html)} bytes, frame: {self.frame_count}, "
                f"raw: '{raw_preview}'"
            )
            
            return delta
        
        return None
    
    def format_sse_frame(self, content: str | None = None, done: bool = False) -> str:
        """
        Format content as SSE frame.
        
        Args:
            content: HTML content to send (None for done frame)
            done: Whether this is the final frame
            
        Returns:
            SSE-formatted frame
        """
        self.seq += 1
        payload = {
            "done": bool(done),
            "seq": self.seq,
            "stream_id": self.stream_id,
            "acc_len": len(self.accumulated_html),
            "raw_len": len(self.accumulated_raw),
        }
        if content is not None:
            payload["content"] = content
            payload["sha1"] = hashlib.sha1(content.encode("utf-8")).hexdigest()[:12]
        frame = f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        logger.debug("EMIT seq=%s sha1=%s done=%s acc=%s raw=%s",
                     payload.get("seq"), payload.get("sha1"),
                     payload["done"], payload["acc_len"], payload["raw_len"])
        return frame
    
    def get_stats(self) -> dict:
        """
        Get streaming statistics for logging.
        
        Returns:
            Dictionary with stats
        """
        return {
            "total_frames": self.frame_count,
            "total_bytes_emitted": self.total_bytes_emitted,
            "accumulated_html_length": len(self.accumulated_html),
            "accumulated_raw_length": len(self.accumulated_raw)
        }
    
    def finalize(self) -> None:
        """
        Finalize streaming and log statistics.
        """
        stats = self.get_stats()
        logger.info(
            f"Streaming completed - frames: {stats['total_frames']}, "
            f"bytes: {stats['total_bytes_emitted']}, "
            f"html_length: {stats['accumulated_html_length']}, "
            f"raw_length: {stats['accumulated_raw_length']}"
        )


async def create_enhanced_stream(
    original_stream: AsyncGenerator[str, None],
    session_id: str
) -> AsyncGenerator[str, None]:
    """
    Wrap an original stream to ensure pure HTML output with no duplication.
    
    Args:
        original_stream: Original token stream from LLM
        session_id: Session ID for logging
        
    Yields:
        SSE frames with HTML-only content
    """
    processor = EnhancedStreamingProcessor(stream_id=session_id)
    
    try:
        # Process each chunk from original stream
        async for chunk in original_stream:
            html_delta = await processor.process_chunk(chunk)
            if html_delta:
                # Emit SSE frame with HTML delta
                yield processor.format_sse_frame(content=html_delta, done=False)
        
        # Send final done frame
        yield processor.format_sse_frame(done=True)
        
        # Log final stats
        processor.finalize()
        
    except Exception as e:
        stats = processor.get_stats()
        logger.error(
            f"Stream processing error - session: {session_id}, error: {str(e)}, "
            f"stats: frames={stats['total_frames']}, bytes={stats['total_bytes_emitted']}"
        )
        # Send error frame
        yield processor.format_sse_frame(done=True)
        raise