"""
Hash gate to detect duplicate content emission.

Guards against the same content delta being emitted twice
in a single stream by tracking SHA1 hashes.
"""

import hashlib
import logging
from typing import Set

logger = logging.getLogger(__name__)


class HashGate:
    """
    Detects duplicate content deltas in a single stream.
    Raises error if same sha1 appears twice (for debugging).
    """
    
    def __init__(self, stream_id: str):
        self.stream_id = stream_id
        self.seen_hashes: Set[str] = set()
        self.delta_count = 0
    
    def check_delta(self, delta: str, seq: int) -> None:
        """
        Check if this delta has been seen before.
        
        Args:
            delta: The delta content to check
            seq: Sequence number for logging
            
        Raises:
            RuntimeError: If duplicate hash detected (for debugging)
        """
        if not delta:
            return
            
        delta_hash = hashlib.sha1(delta.encode("utf-8")).hexdigest()[:12]
        self.delta_count += 1
        
        if delta_hash in self.seen_hashes:
            logger.error(
                "DUPLICATE_HASH_DETECTED stream_id=%s seq=%s hash=%s delta_count=%s delta_preview='%s'",
                self.stream_id, seq, delta_hash, self.delta_count,
                delta[:100] + ("..." if len(delta) > 100 else "")
            )
            # Raise for debugging - remove in production
            raise RuntimeError(f"Duplicate hash {delta_hash} detected in stream {self.stream_id} at seq {seq}")
        
        self.seen_hashes.add(delta_hash)
        logger.debug(
            "HASH_GATE_PASS stream_id=%s seq=%s hash=%s total_hashes=%s",
            self.stream_id, seq, delta_hash, len(self.seen_hashes)
        )