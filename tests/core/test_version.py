"""Tests for version utility module.

TDD: Tests written FIRST before implementation.
Tests version reading from VERSION file and environment detection.
"""

from pathlib import Path
from unittest.mock import patch

import pytest


class TestGetVersion:
    """Tests for get_version()."""

    def test_reads_version_from_file(self, tmp_path: Path):
        """Should read the version string from the VERSION file."""
        from app.core.version import get_version

        version = get_version()
        # VERSION file exists at project root with a valid semver string
        assert version
        assert len(version.split(".")) == 3

    def test_returns_fallback_when_file_missing(self):
        """Should return '0.0.0' when VERSION file does not exist."""
        from app.core.version import get_version

        with patch.object(Path, "read_text", side_effect=FileNotFoundError):
            result = get_version()
            assert result == "0.0.0"

    def test_strips_whitespace(self, tmp_path: Path):
        """Should strip trailing newlines/whitespace from version."""
        from app.core.version import get_version

        version = get_version()
        assert version == version.strip()
        assert "\n" not in version


class TestGetEnvironment:
    """Tests for get_environment()."""

    def test_returns_environment_string(self):
        """Should return the current environment as a string."""
        from app.core.version import get_environment

        env = get_environment()
        assert env in ("development", "qa", "production")


class TestModuleLevelVersion:
    """Tests for __version__ module attribute."""

    def test_version_attribute_exists(self):
        """Should expose __version__ at module level."""
        from app.core.version import __version__

        assert __version__
        assert isinstance(__version__, str)
