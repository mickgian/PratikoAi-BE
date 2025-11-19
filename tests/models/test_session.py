"""Tests for Session model."""

from datetime import datetime

import pytest

from app.models.session import Session


class TestSessionModel:
    """Test Session model."""

    def test_session_creation(self):
        """Test creating a Session instance."""
        session = Session(id="session-123", user_id=1, name="Test Session")

        assert session.id == "session-123"
        assert session.user_id == 1
        assert session.name == "Test Session"

    def test_session_default_name(self):
        """Test Session with default name."""
        session = Session(id="session-456", user_id=2)

        assert session.id == "session-456"
        assert session.user_id == 2
        assert session.name == ""

    def test_session_fields_exist(self):
        """Test Session has all required fields."""
        session = Session(id="test", user_id=1)

        assert hasattr(session, "id")
        assert hasattr(session, "user_id")
        assert hasattr(session, "name")
        assert hasattr(session, "created_at")

    def test_session_is_table(self):
        """Test Session is a SQLModel table."""
        from sqlmodel import SQLModel

        assert issubclass(Session, SQLModel)

    def test_session_with_empty_name(self):
        """Test Session with explicitly empty name."""
        session = Session(id="session-789", user_id=3, name="")

        assert session.name == ""

    def test_session_with_long_name(self):
        """Test Session with long name."""
        long_name = "A" * 200
        session = Session(id="session-long", user_id=4, name=long_name)

        assert session.name == long_name
        assert len(session.name) == 200

    def test_session_user_id_integer(self):
        """Test Session user_id is integer."""
        session = Session(id="test", user_id=999)
        assert isinstance(session.user_id, int)

    def test_session_id_string(self):
        """Test Session id is string."""
        session = Session(id="uuid-string", user_id=1)
        assert isinstance(session.id, str)
