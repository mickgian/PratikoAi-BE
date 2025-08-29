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
from app.core.hash_gate import HashGate

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
    
    def __init__(self, stream_id: str | None = None, enable_hash_gate: bool = False):
        """Initialize the streaming processor."""
        self.accumulated_html = ""  # Track all emitted HTML
        self.accumulated_raw = ""   # Track raw input for debugging
        self.frame_count = 0
        self.total_bytes_emitted = 0
        self.seq = 0
        self.stream_id = stream_id or f"{int(time.time()*1000)}-{os.getpid()}"
        self.hash_gate = HashGate(self.stream_id) if enable_hash_gate else None
        self.emitted_hashes = set()  # Track emitted deltas by SHA1 to prevent duplicates
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
    
    def _strip_overlap(self, accumulated: str, incoming: str) -> str:
        """Remove overlap when incoming snapshot's head overlaps our tail."""
        window = 200
        a_tail = accumulated[-window:]
        i_head = incoming[:window]
        best = 0
        m = min(len(a_tail), len(i_head))
        for k in range(1, m + 1):
            if a_tail[-k:] == i_head[:k]:
                best = k
        return incoming[best:]
    
    def _compute_delta_lcp(self, new_content: str) -> str:
        """
        Compute delta using robust Longest Common Prefix (LCP) algorithm.
        
        This prevents previously-emitted content from being replayed by ensuring
        we only emit the new tail beyond what's already been accumulated.
        
        Args:
            new_content: The new normalized HTML content
            
        Returns:
            str: Only the new content that hasn't been emitted yet
        """
        if not new_content:
            logger.debug("LCP_DELTA stream_id=%s branch=empty_new_content", self.stream_id)
            return ""

        # If nothing accumulated yet, everything is new
        if not self.accumulated_html:
            logger.debug(
                "LCP_DELTA stream_id=%s branch=empty_accumulated new_len=%s",
                self.stream_id, len(new_content)
            )
            return new_content

        # Find the longest common prefix between accumulated and new content
        lcp_len = 0
        min_len = min(len(self.accumulated_html), len(new_content))
        
        for i in range(min_len):
            if self.accumulated_html[i] == new_content[i]:
                lcp_len += 1
            else:
                break
        
        logger.debug(
            "LCP_DELTA stream_id=%s lcp_len=%s acc_len=%s new_len=%s",
            self.stream_id, lcp_len, len(self.accumulated_html), len(new_content)
        )
        
        # Case 1: new_content is exact prefix of accumulated (should not happen in normal streaming)
        if lcp_len == len(new_content):
            logger.info(
                "LCP_DELTA stream_id=%s branch=new_is_prefix_of_acc no_delta_needed",
                self.stream_id
            )
            return ""
            
        # Case 2: accumulated is exact prefix of new_content (normal continuation)  
        if lcp_len == len(self.accumulated_html):
            delta = new_content[lcp_len:]
            logger.debug(
                "LCP_DELTA stream_id=%s branch=acc_is_prefix_of_new delta_len=%s",
                self.stream_id, len(delta)
            )
            return delta
            
        # Case 3: Potential replay or divergence - be VERY strict
        # Check if new content contains any of the already-emitted content
        # This is the critical anti-replay protection
        acc_text_normalized = self._strip_tags(self.accumulated_html).lower().strip()
        new_text_normalized = self._strip_tags(new_content).lower().strip()
        
        # If normalized accumulated text appears anywhere in the new content,
        # this is likely a replay scenario - BLOCK IT
        if acc_text_normalized and acc_text_normalized in new_text_normalized:
            logger.warning(
                "LCP_DELTA stream_id=%s branch=replay_detected BLOCKING_EMISSION acc_normalized_len=%s found_in_new=True",
                self.stream_id, len(acc_text_normalized)
            )
            return ""
        
        # Case 4: Content appears to be restarting or diverged significantly
        # This is where the old logic would cause duplicates
        # Instead, we reject any content that would replay already-emitted material
        logger.warning(
            "LCP_DELTA stream_id=%s branch=divergence_detected rejecting_potential_replay acc_len=%s new_len=%s lcp_len=%s",
            self.stream_id, len(self.accumulated_html), len(new_content), lcp_len
        )
        
        # Log the divergence for debugging
        logger.debug(
            "LCP_DIVERGENCE stream_id=%s acc_head='%s' new_head='%s'",
            self.stream_id,
            self.accumulated_html[:100] + ("..." if len(self.accumulated_html) > 100 else ""),
            new_content[:100] + ("..." if len(new_content) > 100 else "")
        )
        
        # Return empty to prevent any duplication
        return ""
        
    def _compute_similarity(self, text1: str, text2: str) -> float:
        """Compute similarity ratio between two texts."""
        if not text1 or not text2:
            return 0.0
        
        # Simple character-based similarity
        matches = sum(1 for a, b in zip(text1, text2) if a == b)
        total = max(len(text1), len(text2))
        return matches / total if total > 0 else 0.0

    async def process_chunk(self, raw_chunk: str) -> Optional[str]:
        """
        Emit ONLY the new tail beyond already-emitted HTML.
        Block replay/second-start snapshots.
        """
        if not raw_chunk:
            return None

        next_seq = self.frame_count + 1

        # Append raw for deterministic normalization of the same corpus
        self.accumulated_raw += raw_chunk
        raw_chunk = raw_chunk.rstrip('\r\n')

        # Normalize the WHOLE RAW so far to get a coherent snapshot
        new_full_html = self._normalize_to_html(self.accumulated_raw)
        acc = self.accumulated_html

        # ── Guard 1: ignore shrinks so we don't starve the tail ─────────────────────
        # If snapshot shrank relative to what we've already emitted, do nothing.
        # Prevents overzealous RESTART_BLOCKED from starving output.
        if len(new_full_html) < len(acc):
            logger.info(
                "SHRINK_SNAPSHOT_IGNORED stream_id=%s acc_len=%s new_len=%s",
                self.stream_id, len(acc), len(new_full_html)
            )
            return None

        # Compute delta against what we've already emitted
        if not acc:
            delta = new_full_html
        elif new_full_html.startswith(acc):
            # Happy path: continuation
            delta = new_full_html[len(acc):]
        else:
            # Replay/divergence handling
            last_idx = new_full_html.rfind(acc)
            if last_idx != -1:
                # Keep only the tail after the last occurrence of what we've shown
                delta = new_full_html[last_idx + len(acc):]
            else:
                # "Second start" (new_full_html begins again like head) → block
                head_norm = self._norm_text(acc[:160])
                new_head_norm = self._norm_text(new_full_html[:max(160, len(head_norm))])
                if head_norm and new_head_norm.startswith(head_norm):
                    logger.warning(
                        "RESTART_BLOCKED stream_id=%s seq=%s acc_len=%s new_len=%s",
                        self.stream_id, next_seq, len(acc), len(new_full_html)
                    )
                    return None
                # Partial overlap fallback
                delta = self._strip_overlap(acc, new_full_html)

                # ── Guard 2: textual head replay trim for overlap fallback ──────────
                # If the would-be delta still looks like a replayed head, drop it.
                delta_text = self._strip_tags(delta).lower().strip()
                acc_text = self._strip_tags(acc).lower().strip()
                if acc_text and delta_text.startswith(acc_text[: min(300, len(acc_text))]):
                    logger.warning(
                        "DELTA_HEAD_REPLAY_TRIM stream_id=%s seq=%s",
                        self.stream_id, next_seq
                    )
                    return None

        # Ignore empty/whitespace-only
        if not delta or not re.search(r'\S|<[^>]+>', delta):
            return None

        # Hash-based dedup for identical delta repeats
        delta_sha1 = hashlib.sha1(delta.encode("utf-8")).hexdigest()[:12]
        if delta_sha1 in self.emitted_hashes:
            logger.warning(
                "DUP_DELTA_BLOCKED stream_id=%s seq=%s sha1=%s delta_len=%s already_emitted",
                self.stream_id, next_seq, delta_sha1, len(delta)
            )
            return None
        if self.hash_gate:
            self.hash_gate.check_delta(delta, next_seq)

        # Commit
        self.emitted_hashes.add(delta_sha1)
        self.accumulated_html = acc + delta
        self.frame_count += 1
        self.total_bytes_emitted += len(delta)
        return delta

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