"""Release notes API endpoints.

Provides version info, release notes listing, and seen tracking.
Public endpoints for version/listing, authenticated for seen tracking.
"""

from fastapi import APIRouter, Depends, Path, Query

from app.api.v1.auth import get_current_user
from app.core.version import get_environment
from app.core.version import get_version as app_get_version
from app.models.user import User
from app.schemas.release_notes import (
    MarkSeenResponse,
    ReleaseNotePublicResponse,
    ReleaseNoteResponse,
    ReleaseNotesListResponse,
    VersionResponse,
)
from app.services.release_notes_service import release_notes_service

router = APIRouter(prefix="/release-notes", tags=["release-notes"])


@router.get("/version", response_model=VersionResponse)
async def get_version() -> VersionResponse:
    """Get current application version and environment."""
    return VersionResponse(
        version=app_get_version(),
        environment=get_environment(),
    )


@router.get("", response_model=ReleaseNotesListResponse)
async def get_release_notes(
    page: int = Query(default=1, ge=1, description="Numero pagina"),
    page_size: int = Query(default=10, ge=1, le=50, description="Elementi per pagina"),
) -> ReleaseNotesListResponse:
    """Get paginated list of release notes (public, user-facing only)."""
    items, total = await release_notes_service.list_release_notes(page=page, page_size=page_size)
    return ReleaseNotesListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/latest", response_model=ReleaseNotePublicResponse | None)
async def get_latest_release_note() -> ReleaseNotePublicResponse | None:
    """Get the most recent release note (public, user-facing only)."""
    return await release_notes_service.get_latest()


@router.get("/unseen", response_model=ReleaseNoteResponse | None)
async def get_unseen_release_note(
    current_user: User = Depends(get_current_user),
) -> ReleaseNoteResponse | None:
    """Get the latest release note the user hasn't seen yet."""
    return await release_notes_service.get_unseen_for_user(user_id=current_user.id)


@router.post("/{version}/seen", response_model=MarkSeenResponse)
async def mark_release_note_seen(
    version: str = Path(pattern=r"^\d+\.\d+\.\d+$", max_length=20),
    current_user: User = Depends(get_current_user),
) -> MarkSeenResponse:
    """Mark a release note as seen by the current user."""
    success = await release_notes_service.mark_seen(user_id=current_user.id, version=version)
    if success:
        return MarkSeenResponse(success=True, message_it="Nota di rilascio segnata come vista.")
    return MarkSeenResponse(success=False, message_it="Versione non trovata.")
