"""Release note models for versioning system.

Stores release notes with dual content: technical (for QA) and user-facing (for production).
Tracks which users have seen each release note for the one-time popup.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Text, UniqueConstraint, func
from sqlmodel import Field, SQLModel


class ReleaseNote(SQLModel, table=True):  # type: ignore[call-arg]
    """Release note for a specific version.

    Stores dual content:
    - technical_notes: Full commit details for QA/internal use
    - user_notes: User-friendly summary in Italian for production
    """

    __tablename__ = "release_notes"

    id: int | None = Field(default=None, primary_key=True)
    version: str = Field(max_length=20, unique=True, index=True)
    user_notes: str = Field(sa_column=Column(Text, nullable=False))
    technical_notes: str = Field(sa_column=Column(Text, nullable=False))
    released_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), index=True),
    )  # type: ignore[assignment]
    created_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )  # type: ignore[assignment]


class UserReleaseNoteSeen(SQLModel, table=True):  # type: ignore[call-arg]
    """Tracks which users have seen which release notes.

    Used for the one-time popup that shows new release notes
    when a user first visits after a new release.

    Note: Platform-wide (no studio_id) since release notes apply to all tenants.
    """

    __tablename__ = "user_release_note_seen"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    release_note_id: int = Field(index=True, foreign_key="release_notes.id")
    seen_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )  # type: ignore[assignment]

    __table_args__ = (UniqueConstraint("user_id", "release_note_id", name="uq_user_release_note"),)
