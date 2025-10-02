"""Test RAGState conversion and compatibility."""

from app.core.langgraph.types import RAGState


class TestRAGStateConversion:
    """Test RAGState type conversion and compatibility."""

    def test_ragstate_creation_empty(self):
        """Test creating an empty RAGState."""
        state = RAGState()
        assert isinstance(state, dict)
        assert len(state) == 0

    def test_ragstate_creation_with_data(self):
        """Test creating RAGState with data."""
        data = {
            "request_id": "test-123",
            "messages": [{"role": "user", "content": "Hello"}],
            "streaming": False
        }
        state = RAGState(data)
        assert state["request_id"] == "test-123"
        assert len(state["messages"]) == 1
        assert state["streaming"] is False

    def test_ragstate_copy(self):
        """Test RAGState copy operations."""
        original = RAGState({
            "request_id": "test-123",
            "messages": [{"role": "user", "content": "Hello"}]
        })

        # Test copy method
        copied = original.copy()
        assert copied == original
        assert copied is not original

        # Modify copy shouldn't affect original
        copied["request_id"] = "test-456"
        assert original["request_id"] == "test-123"
        assert copied["request_id"] == "test-456"

    def test_ragstate_update(self):
        """Test RAGState update operations."""
        state = RAGState({"request_id": "test-123"})

        update_data = {
            "session_id": "session-456",
            "streaming": True
        }

        state.update(update_data)
        assert state["request_id"] == "test-123"
        assert state["session_id"] == "session-456"
        assert state["streaming"] is True

    def test_ragstate_optional_fields(self):
        """Test that all RAGState fields are optional."""
        # Should be able to create RAGState with any subset of fields
        minimal_state = RAGState({"request_id": "test"})
        assert "request_id" in minimal_state

        # Missing fields should not cause errors
        assert minimal_state.get("session_id") is None
        assert minimal_state.get("messages") is None

    def test_ragstate_compatibility_with_dict(self):
        """Test RAGState compatibility with dict operations."""
        state = RAGState({
            "request_id": "test-123",
            "messages": []
        })

        # Should work with dict() conversion
        as_dict = dict(state)
        assert isinstance(as_dict, dict)
        assert as_dict["request_id"] == "test-123"

        # Should work with list(state.keys())
        keys = list(state.keys())
        assert "request_id" in keys
        assert "messages" in keys