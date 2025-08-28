"""
Guard to prevent double iteration of streams.

This module provides protection against accidentally iterating
a stream twice, which could cause duplicate content.
"""

from typing import AsyncGenerator, TypeVar

T = TypeVar('T')


class SinglePassStream:
    """
    Wraps an async generator to ensure it's only iterated once.
    Raises RuntimeError if iteration is attempted twice.
    """
    
    def __init__(self, agen: AsyncGenerator[T, None]):
        self._agen = agen
        self._used = False
    
    def __aiter__(self):
        if self._used:
            raise RuntimeError("original_stream iterated twice - this would cause duplication!")
        self._used = True
        return self._agen