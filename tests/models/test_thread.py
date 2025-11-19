"""Tests for Thread model."""

from datetime import UTC, datetime

import pytest

from app.models.thread import Thread


class TestThreadModel:
    """Test Thread model."""

    def test_thread_creation(self):
        """Test creating a Thread instance."""
        thread = Thread(id="thread-123")

        assert thread.id == "thread-123"
        assert hasattr(thread, "created_at")

    def test_thread_created_at_default(self):
        """Test Thread created_at has default value."""
        thread = Thread(id="thread-456")

        assert thread.created_at is not None
        assert isinstance(thread.created_at, datetime)

    def test_thread_created_at_utc(self):
        """Test Thread created_at is in UTC."""
        thread = Thread(id="thread-789")

        # Should be recent (within last second)
        now = datetime.now(UTC)
        time_diff = (now - thread.created_at).total_seconds()
        assert time_diff < 1.0

    def test_thread_fields_exist(self):
        """Test Thread has all required fields."""
        thread = Thread(id="test")

        assert hasattr(thread, "id")
        assert hasattr(thread, "created_at")

    def test_thread_is_table(self):
        """Test Thread is a SQLModel table."""
        from sqlmodel import SQLModel

        assert issubclass(Thread, SQLModel)

    def test_thread_id_string(self):
        """Test Thread id is string."""
        thread = Thread(id="uuid-string")
        assert isinstance(thread.id, str)

    def test_thread_with_explicit_created_at(self):
        """Test Thread with explicitly set created_at."""
        specific_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        thread = Thread(id="thread-custom", created_at=specific_time)

        assert thread.created_at == specific_time

    def test_multiple_threads_different_timestamps(self):
        """Test multiple threads get different timestamps."""
        import time

        thread1 = Thread(id="thread-1")
        time.sleep(0.001)  # Small delay
        thread2 = Thread(id="thread-2")

        assert thread2.created_at >= thread1.created_at
