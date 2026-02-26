"""Release notes service layer.

Business logic for release notes CRUD and user seen tracking.
"""

from sqlalchemy import func, select
from sqlalchemy.exc import ProgrammingError

from app.core.logging import logger
from app.models.database import AsyncSessionLocal
from app.models.release_note import ReleaseNote, UserReleaseNoteSeen
from app.schemas.release_notes import ReleaseNotePublicResponse, ReleaseNoteResponse


class ReleaseNotesService:
    """Service for release notes operations."""

    async def list_release_notes(
        self, page: int = 1, page_size: int = 10
    ) -> tuple[list[ReleaseNotePublicResponse], int]:
        """List release notes with pagination, newest first.

        Returns public-facing response without technical notes.

        Args:
            page: Page number (1-based)
            page_size: Items per page

        Returns:
            Tuple of (items, total_count)
        """
        try:
            async with AsyncSessionLocal() as db:
                count_query = select(func.count(ReleaseNote.id))
                count_result = await db.execute(count_query)
                total = count_result.scalar_one()

                offset = (page - 1) * page_size
                query = select(ReleaseNote).order_by(ReleaseNote.released_at.desc()).offset(offset).limit(page_size)  # type: ignore[union-attr]
                result = await db.execute(query)
                notes = result.scalars().all()

                items = [
                    ReleaseNotePublicResponse(
                        version=note.version,
                        released_at=note.released_at,
                        user_notes=note.user_notes,
                    )
                    for note in notes
                ]

                return items, total
        except ProgrammingError:
            logger.warning("release_notes_table_missing", operation="list_release_notes")
            return [], 0

    async def get_latest(self) -> ReleaseNotePublicResponse | None:
        """Get the most recent release note (public, no technical notes).

        Returns:
            The latest release note or None if none exist.
        """
        try:
            async with AsyncSessionLocal() as db:
                query = select(ReleaseNote).order_by(ReleaseNote.released_at.desc()).limit(1)  # type: ignore[union-attr]
                result = await db.execute(query)
                note = result.scalar_one_or_none()

                if note is None:
                    return None

                return ReleaseNotePublicResponse(
                    version=note.version,
                    released_at=note.released_at,
                    user_notes=note.user_notes,
                )
        except ProgrammingError:
            logger.warning("release_notes_table_missing", operation="get_latest")
            return None

    async def get_unseen_for_user(self, user_id: int) -> ReleaseNoteResponse | None:
        """Get the latest release note the user hasn't seen.

        Args:
            user_id: The authenticated user's ID

        Returns:
            The latest unseen release note, or None if all seen.
        """
        try:
            async with AsyncSessionLocal() as db:
                subquery = select(UserReleaseNoteSeen.release_note_id).where(UserReleaseNoteSeen.user_id == user_id)
                query = (
                    select(ReleaseNote)
                    .where(ReleaseNote.id.notin_(subquery))  # type: ignore[union-attr]
                    .order_by(ReleaseNote.released_at.desc())  # type: ignore[union-attr]
                    .limit(1)
                )
                result = await db.execute(query)
                note = result.scalar_one_or_none()

                if note is None:
                    return None

                return ReleaseNoteResponse(
                    version=note.version,
                    released_at=note.released_at,
                    user_notes=note.user_notes,
                    technical_notes=note.technical_notes,
                )
        except ProgrammingError:
            logger.warning("release_notes_table_missing", operation="get_unseen_for_user")
            return None

    async def list_release_notes_full(
        self, page: int = 1, page_size: int = 10
    ) -> tuple[list[ReleaseNoteResponse], int]:
        """List release notes with pagination, newest first (full, with technical_notes).

        For authenticated QA/admin use. Returns technical_notes alongside user_notes.

        Args:
            page: Page number (1-based)
            page_size: Items per page

        Returns:
            Tuple of (items, total_count)
        """
        try:
            async with AsyncSessionLocal() as db:
                count_query = select(func.count(ReleaseNote.id))
                count_result = await db.execute(count_query)
                total = count_result.scalar_one()

                offset = (page - 1) * page_size
                query = select(ReleaseNote).order_by(ReleaseNote.released_at.desc()).offset(offset).limit(page_size)  # type: ignore[union-attr]
                result = await db.execute(query)
                notes = result.scalars().all()

                items = [
                    ReleaseNoteResponse(
                        version=note.version,
                        released_at=note.released_at,
                        user_notes=note.user_notes,
                        technical_notes=note.technical_notes,
                    )
                    for note in notes
                ]

                return items, total
        except ProgrammingError:
            logger.warning("release_notes_table_missing", operation="list_release_notes_full")
            return [], 0

    async def update_user_notes(self, version: str, user_notes: str) -> bool:
        """Update the user-facing notes for a specific version.

        Used in QA to edit production-preview notes before deploying.

        Args:
            version: The version string (e.g. "0.2.0")
            user_notes: The new user-facing notes text

        Returns:
            True if version found and updated, False if version not found.
        """
        try:
            async with AsyncSessionLocal() as db:
                query = select(ReleaseNote).where(ReleaseNote.version == version)
                result = await db.execute(query)
                note = result.scalar_one_or_none()

                if note is None:
                    logger.warning(
                        "update_user_notes_version_not_found",
                        version=version,
                    )
                    return False

                note.user_notes = user_notes.strip()
                await db.commit()
                await db.refresh(note)

                logger.info(
                    "user_notes_updated",
                    version=version,
                )
                return True
        except ProgrammingError:
            logger.warning("release_notes_table_missing", operation="update_user_notes")
            return False

    async def mark_seen(self, user_id: int, version: str) -> bool:
        """Mark a release note as seen by a user.

        Idempotent: if already marked, returns True without duplicating.

        Args:
            user_id: The authenticated user's ID
            version: The version string to mark as seen

        Returns:
            True if the version exists (and is now marked), False otherwise.
        """
        try:
            async with AsyncSessionLocal() as db:
                note_query = select(ReleaseNote).where(ReleaseNote.version == version)
                note_result = await db.execute(note_query)
                note = note_result.scalar_one_or_none()

                if note is None:
                    logger.warning(
                        "mark_seen_version_not_found",
                        user_id=user_id,
                        version=version,
                    )
                    return False

                seen_query = select(UserReleaseNoteSeen).where(
                    UserReleaseNoteSeen.user_id == user_id,
                    UserReleaseNoteSeen.release_note_id == note.id,
                )
                seen_result = await db.execute(seen_query)
                existing = seen_result.scalar_one_or_none()

                if existing is not None:
                    return True

                seen_record = UserReleaseNoteSeen(
                    user_id=user_id,
                    release_note_id=note.id,
                )
                db.add(seen_record)
                await db.commit()

                logger.info(
                    "release_note_marked_seen",
                    user_id=user_id,
                    version=version,
                )
                return True
        except ProgrammingError:
            logger.warning("release_notes_table_missing", operation="mark_seen")
            return False


release_notes_service = ReleaseNotesService()
