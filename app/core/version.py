"""Application version management.

Reads the version from the VERSION file at the project root.
This is the single source of truth for the application version.
"""

from pathlib import Path

from app.core.config import settings


def get_version() -> str:
    """Read the application version from the VERSION file.

    Returns:
        str: The current version string (e.g., "0.2.0")
    """
    version_file = Path(__file__).parent.parent.parent / "VERSION"
    try:
        return version_file.read_text().strip()
    except FileNotFoundError:
        return "0.0.0"


def get_environment() -> str:
    """Get the current environment name.

    Returns:
        str: The current environment (development, qa, production)
    """
    return settings.ENVIRONMENT.value


__version__ = get_version()
