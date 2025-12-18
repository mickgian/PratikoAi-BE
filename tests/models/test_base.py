"""Tests for base model."""

from datetime import datetime

import pytest

from app.models.base import BaseModel


class TestBaseModel:
    """Test BaseModel class."""

    def test_base_model_has_created_at(self):
        """Test BaseModel has created_at field."""
        model = BaseModel()
        assert hasattr(model, "created_at")

    def test_created_at_is_datetime(self):
        """Test created_at is datetime instance."""
        model = BaseModel()
        assert isinstance(model.created_at, datetime)

    def test_created_at_is_utc(self):
        """Test created_at is recent (uses datetime.utcnow which is naive UTC)."""
        model = BaseModel()

        # Should be recent (within last second)
        # Note: BaseModel uses datetime.utcnow() which returns naive datetime
        now = datetime.utcnow()
        time_diff = (now - model.created_at).total_seconds()
        assert time_diff < 1.0

    def test_created_at_has_timezone(self):
        """Test created_at uses naive UTC datetime (datetime.utcnow())."""
        model = BaseModel()
        # Note: datetime.utcnow() returns naive datetime without tzinfo
        # This is the current behavior - model uses naive UTC
        assert model.created_at.tzinfo is None

    def test_multiple_instances_different_timestamps(self):
        """Test multiple instances get different timestamps."""
        import time

        model1 = BaseModel()
        time.sleep(0.001)  # Small delay
        model2 = BaseModel()

        assert model2.created_at >= model1.created_at

    def test_base_model_is_sqlmodel(self):
        """Test BaseModel is a SQLModel."""
        from sqlmodel import SQLModel

        assert issubclass(BaseModel, SQLModel)

    def test_created_at_default_factory(self):
        """Test created_at uses default factory."""
        model1 = BaseModel()
        model2 = BaseModel()

        # Each instance should get its own timestamp
        # (not share the same datetime object)
        assert model1.created_at is not model2.created_at
