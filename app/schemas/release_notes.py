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


class ReleaseNotesFullListResponse(BaseModel):
    """Paginated list of release notes (full, with technical_notes for QA)."""

    items: list[ReleaseNoteResponse]
    total: int
    page: int
    page_size: int


class UpdateUserNotesRequest(BaseModel):
    """Request to update user-facing notes for a release version."""

    user_notes: str = Field(
        min_length=1,
        description="Note per gli utenti (in italiano) - non può essere vuoto",
    )

    @classmethod
    def model_validate(cls, *args, **kwargs):  # type: ignore[override]
        instance = super().model_validate(*args, **kwargs)
        if not instance.user_notes.strip():
            raise ValueError("user_notes non può contenere solo spazi")
        return instance

    def model_post_init(self, __context: object) -> None:
        if not self.user_notes.strip():
            raise ValueError("user_notes non può contenere solo spazi")


class MarkSeenResponse(BaseModel):
    """Response after marking a release note as seen."""

    success: bool
    message_it: str = ""
