"""Database compatibility module.

This module provides compatibility imports for database functionality
to maintain backward compatibility with existing imports.
"""

from app.services.database import database_service


# Re-export database service functions
def get_async_session():
    """Get async database session."""
    return database_service.get_session_maker()


def get_session():
    """Get database session (sync)."""
    return database_service.get_session_maker()


# Re-export database service instance for direct access
__all__ = ["get_async_session", "get_session", "database_service"]
