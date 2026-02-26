"""DEV-394: Tests for Feature Flag Infrastructure."""

import os
import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# Mock the database service to avoid needing a live PostgreSQL connection
if "app.services.database" not in sys.modules:
    _db_stub = ModuleType("app.services.database")
    _db_stub.database_service = MagicMock()  # type: ignore[attr-defined]
    sys.modules["app.services.database"] = _db_stub

from app.services.feature_flag_service import FeatureFlagService


class TestFeatureFlagGlobal:
    """Test global flag operations."""

    def test_global_flag_enabled(self) -> None:
        """Set and check a global flag."""
        svc = FeatureFlagService()
        svc.set_global_flag("proactive_matching", True)
        assert svc.is_enabled("proactive_matching") is True

    def test_global_flag_disabled(self) -> None:
        """Disabled global flag returns False."""
        svc = FeatureFlagService()
        svc.set_global_flag("proactive_matching", False)
        assert svc.is_enabled("proactive_matching") is False

    def test_global_flag_overwrite(self) -> None:
        """Overwriting global flag updates value."""
        svc = FeatureFlagService()
        svc.set_global_flag("new_feature", True)
        assert svc.is_enabled("new_feature") is True
        svc.set_global_flag("new_feature", False)
        assert svc.is_enabled("new_feature") is False


class TestFeatureFlagStudioOverride:
    """Test per-studio flag overrides."""

    def test_studio_override_true(self) -> None:
        """Studio flag overrides global."""
        svc = FeatureFlagService()
        studio_id = uuid4()
        svc.set_global_flag("feature_x", False)
        svc.set_studio_flag("feature_x", studio_id, True)
        assert svc.is_enabled("feature_x", studio_id) is True

    def test_studio_false_overrides_global_true(self) -> None:
        """Studio=False overrides Global=True."""
        svc = FeatureFlagService()
        studio_id = uuid4()
        svc.set_global_flag("feature_x", True)
        svc.set_studio_flag("feature_x", studio_id, False)
        assert svc.is_enabled("feature_x", studio_id) is False

    def test_no_studio_override_inherits_global(self) -> None:
        """Without studio override, global is used."""
        svc = FeatureFlagService()
        studio_id = uuid4()
        svc.set_global_flag("feature_y", True)
        assert svc.is_enabled("feature_y", studio_id) is True

    def test_studio_override_removed_inherits(self) -> None:
        """Removing studio override falls back to global."""
        svc = FeatureFlagService()
        studio_id = uuid4()
        svc.set_global_flag("feature_z", True)
        svc.set_studio_flag("feature_z", studio_id, False)
        assert svc.is_enabled("feature_z", studio_id) is False

        svc.remove_studio_flag("feature_z", studio_id)
        assert svc.is_enabled("feature_z", studio_id) is True


class TestFeatureFlagDefaults:
    """Test default behaviour for unknown flags."""

    def test_unknown_flag_returns_false(self) -> None:
        """Unknown flag name returns False (safe default)."""
        svc = FeatureFlagService()
        assert svc.is_enabled("nonexistent_flag") is False

    def test_unknown_flag_with_studio_returns_false(self) -> None:
        """Unknown flag with studio_id still returns False."""
        svc = FeatureFlagService()
        assert svc.is_enabled("nonexistent_flag", uuid4()) is False


class TestFeatureFlagEnvDefaults:
    """Test environment variable fallback."""

    def test_default_from_env(self) -> None:
        """Flag reads from env var when not set explicitly."""
        svc = FeatureFlagService()
        with patch.dict(os.environ, {"FF_MY_FLAG": "true"}):
            assert svc.is_enabled("my_flag") is True

    def test_env_false(self) -> None:
        """Env var 'false' returns False."""
        svc = FeatureFlagService()
        with patch.dict(os.environ, {"FF_MY_FLAG": "false"}):
            assert svc.is_enabled("my_flag") is False

    def test_env_not_set_returns_false(self) -> None:
        """Missing env var returns False (safe default)."""
        svc = FeatureFlagService()
        with patch.dict(os.environ, {}, clear=False):
            # Ensure FF_MISSING is not present
            os.environ.pop("FF_MISSING", None)
            assert svc.is_enabled("missing") is False

    def test_explicit_flag_overrides_env(self) -> None:
        """Explicitly set flag takes priority over env var."""
        svc = FeatureFlagService()
        svc.set_global_flag("env_flag", False)
        with patch.dict(os.environ, {"FF_ENV_FLAG": "true"}):
            assert svc.is_enabled("env_flag") is False


class TestFeatureFlagValidation:
    """Test input validation."""

    def test_empty_flag_name_rejected(self) -> None:
        """Empty flag name raises ValueError."""
        svc = FeatureFlagService()
        with pytest.raises(ValueError, match="Nome flag obbligatorio"):
            svc.is_enabled("")

    def test_whitespace_flag_name_rejected(self) -> None:
        """Whitespace-only flag name raises ValueError."""
        svc = FeatureFlagService()
        with pytest.raises(ValueError, match="Nome flag obbligatorio"):
            svc.is_enabled("   ")

    def test_special_chars_rejected(self) -> None:
        """Flag name with invalid characters raises ValueError."""
        svc = FeatureFlagService()
        with pytest.raises(ValueError, match="caratteri non validi"):
            svc.is_enabled("flag with spaces!")

    def test_valid_flag_name_chars(self) -> None:
        """Flag name with [a-z0-9_-] is accepted."""
        svc = FeatureFlagService()
        svc.set_global_flag("valid-flag_name-123", True)
        assert svc.is_enabled("valid-flag_name-123") is True


class TestFeatureFlagListing:
    """Test listing all flags."""

    def test_list_flags_empty(self) -> None:
        """Empty service returns empty list."""
        svc = FeatureFlagService()
        assert svc.list_flags() == {}

    def test_list_flags_with_global(self) -> None:
        """List includes global flags."""
        svc = FeatureFlagService()
        svc.set_global_flag("flag_a", True)
        svc.set_global_flag("flag_b", False)
        flags = svc.list_flags()
        assert "flag_a" in flags
        assert "flag_b" in flags
        assert flags["flag_a"]["global"] is True
        assert flags["flag_b"]["global"] is False

    def test_list_flags_with_studio_overrides(self) -> None:
        """List includes studio overrides."""
        svc = FeatureFlagService()
        studio_id = uuid4()
        svc.set_global_flag("flag_c", True)
        svc.set_studio_flag("flag_c", studio_id, False)
        flags = svc.list_flags()
        assert "flag_c" in flags
        assert str(studio_id) in flags["flag_c"]["studio_overrides"]


class TestFeatureFlagPercentageRollout:
    """Test percentage-based rollout."""

    def test_percentage_rollout_consistent(self) -> None:
        """Same studio_id always gets same result for same flag."""
        svc = FeatureFlagService()
        studio_id = uuid4()
        svc.set_global_flag("rollout_flag", True)
        svc.set_percentage_rollout("rollout_flag", 50)

        # Same studio should get the same result across calls
        result1 = svc.is_enabled("rollout_flag", studio_id)
        result2 = svc.is_enabled("rollout_flag", studio_id)
        assert result1 == result2

    def test_percentage_rollout_100_all_enabled(self) -> None:
        """100% rollout enables for all studios."""
        svc = FeatureFlagService()
        svc.set_global_flag("full_rollout", True)
        svc.set_percentage_rollout("full_rollout", 100)

        for _ in range(10):
            assert svc.is_enabled("full_rollout", uuid4()) is True

    def test_percentage_rollout_0_all_disabled(self) -> None:
        """0% rollout disables for all studios."""
        svc = FeatureFlagService()
        svc.set_global_flag("no_rollout", True)
        svc.set_percentage_rollout("no_rollout", 0)

        for _ in range(10):
            assert svc.is_enabled("no_rollout", uuid4()) is False


class TestFeatureFlagAudit:
    """Test audit logging of flag changes."""

    def test_flag_changes_audited(self) -> None:
        """Changes are recorded in audit log."""
        svc = FeatureFlagService()
        svc.set_global_flag("audited_flag", True)
        svc.set_global_flag("audited_flag", False)

        audit = svc.get_audit_log("audited_flag")
        assert len(audit) == 2
        assert audit[0]["value"] is True
        assert audit[1]["value"] is False

    def test_studio_flag_changes_audited(self) -> None:
        """Studio flag changes are audited."""
        svc = FeatureFlagService()
        studio_id = uuid4()
        svc.set_studio_flag("studio_flag", studio_id, True)

        audit = svc.get_audit_log("studio_flag")
        assert len(audit) == 1
        assert audit[0]["studio_id"] == str(studio_id)
