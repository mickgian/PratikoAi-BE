"""Release notes schemas for API request/response models.

All user-facing text in Italian.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class VersionResponse(BaseModel):
    """Current application version info."""

    version: str = Field(description="Versione corrente dell'applicazione")
    environment: str = Field(description="Ambiente corrente (development, qa, production)")


class ReleaseNotePublicResponse(BaseModel):
    """Public release note response (user-facing only, no technical details)."""

    model_config = ConfigDict(from_attributes=True)

    version: str
    released_at: datetime | None = None
    user_notes: str = Field(description="Note per gli utenti (in italiano)")


class ReleaseNoteResponse(BaseModel):
    """Full release note response (includes technical notes for authenticated users)."""

    model_config = ConfigDict(from_attributes=True)

    version: str
    released_at: datetime | None = None
    user_notes: str = Field(description="Note per gli utenti (in italiano)")
    technical_notes: str = Field(description="Note tecniche per il team interno")


class ReleaseNotesListResponse(BaseModel):
    """Paginated list of release notes (public, user-facing only)."""

    items: list[ReleaseNotePublicResponse]
    total: int
    page: int
    page_size: int


class MarkSeenResponse(BaseModel):
    """Response after marking a release note as seen."""

    success: bool
    message_it: str = ""
