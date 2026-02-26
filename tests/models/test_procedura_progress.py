"""DEV-306: Tests for ProceduraProgress SQLModel."""

import sys
from datetime import UTC, datetime
from types import ModuleType
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

if "app.services.database" not in sys.modules:
    _db_stub = ModuleType("app.services.database")
    _db_stub.database_service = MagicMock()  # type: ignore[attr-defined]
    sys.modules["app.services.database"] = _db_stub

from app.models.procedura_progress import ProceduraProgress


class TestProceduraProgressCreation:
    """Test ProceduraProgress model creation and field defaults."""

    def test_progress_creation_valid(self) -> None:
        """Valid progress with all required fields."""
        studio_id = uuid4()
        procedura_id = uuid4()
        progress = ProceduraProgress(
            user_id=1,
            studio_id=studio_id,
            procedura_id=procedura_id,
            current_step=0,
        )

        assert progress.user_id == 1
        assert progress.studio_id == studio_id
        assert progress.procedura_id == procedura_id
        assert progress.current_step == 0
        assert progress.id is not None  # uuid4 auto-generated

    def test_progress_fk_constraints(self) -> None:
        """Required FKs: user_id, studio_id, procedura_id."""
        studio_id = uuid4()
        procedura_id = uuid4()
        progress = ProceduraProgress(
            user_id=10,
            studio_id=studio_id,
            procedura_id=procedura_id,
            current_step=3,
        )
        assert progress.user_id == 10
        assert progress.studio_id == studio_id
        assert progress.procedura_id == procedura_id


class TestProceduraProgressSteps:
    """Test step tracking and JSONB completed_steps."""

    def test_completed_steps_default_empty(self) -> None:
        """completed_steps defaults to empty list."""
        progress = ProceduraProgress(
            user_id=1,
            studio_id=uuid4(),
            procedura_id=uuid4(),
            current_step=0,
        )
        assert progress.completed_steps == []

    def test_completed_steps_jsonb(self) -> None:
        """JSONB completed_steps holds array of step numbers."""
        progress = ProceduraProgress(
            user_id=1,
            studio_id=uuid4(),
            procedura_id=uuid4(),
            current_step=3,
            completed_steps=[0, 1, 2],
        )
        assert progress.completed_steps == [0, 1, 2]
        assert len(progress.completed_steps) == 3

    def test_progress_resume(self) -> None:
        """current_step tracks where the user left off."""
        progress = ProceduraProgress(
            user_id=1,
            studio_id=uuid4(),
            procedura_id=uuid4(),
            current_step=5,
            completed_steps=[0, 1, 2, 3, 4],
        )
        assert progress.current_step == 5
        assert 4 in progress.completed_steps


class TestProceduraProgressClientOptional:
    """Test optional client association."""

    def test_client_optional_default_none(self) -> None:
        """client_id defaults to None."""
        progress = ProceduraProgress(
            user_id=1,
            studio_id=uuid4(),
            procedura_id=uuid4(),
            current_step=0,
        )
        assert progress.client_id is None

    def test_client_optional_set(self) -> None:
        """client_id can be set for client-specific procedures."""
        progress = ProceduraProgress(
            user_id=1,
            studio_id=uuid4(),
            procedura_id=uuid4(),
            client_id=42,
            current_step=0,
        )
        assert progress.client_id == 42


class TestProceduraProgressCompletion:
    """Test completion tracking."""

    def test_completed_at_default_none(self) -> None:
        """completed_at defaults to None."""
        progress = ProceduraProgress(
            user_id=1,
            studio_id=uuid4(),
            procedura_id=uuid4(),
            current_step=0,
        )
        assert progress.completed_at is None

    def test_completed_at_set(self) -> None:
        """completed_at can be set when procedure is finished."""
        now = datetime.now(tz=UTC)
        progress = ProceduraProgress(
            user_id=1,
            studio_id=uuid4(),
            procedura_id=uuid4(),
            current_step=5,
            completed_steps=[0, 1, 2, 3, 4],
            completed_at=now,
        )
        assert progress.completed_at == now

    def test_is_completed_property(self) -> None:
        """is_completed returns True when completed_at is set."""
        progress = ProceduraProgress(
            user_id=1,
            studio_id=uuid4(),
            procedura_id=uuid4(),
            current_step=0,
        )
        assert progress.is_completed is False

        progress.completed_at = datetime.now(tz=UTC)
        assert progress.is_completed is True


class TestProceduraProgressNotes:
    """Test notes field."""

    def test_notes_default_none(self) -> None:
        """Notes defaults to None."""
        progress = ProceduraProgress(
            user_id=1,
            studio_id=uuid4(),
            procedura_id=uuid4(),
            current_step=0,
        )
        assert progress.notes is None

    def test_notes_set(self) -> None:
        """Notes can be set."""
        progress = ProceduraProgress(
            user_id=1,
            studio_id=uuid4(),
            procedura_id=uuid4(),
            current_step=0,
            notes="Manca documento di identità",
        )
        assert progress.notes == "Manca documento di identità"


class TestProceduraProgressRepr:
    """Test __repr__ output."""

    def test_repr(self) -> None:
        """__repr__ includes user_id and current_step."""
        progress = ProceduraProgress(
            user_id=7,
            studio_id=uuid4(),
            procedura_id=uuid4(),
            current_step=3,
        )
        r = repr(progress)
        assert "7" in r
        assert "3" in r
