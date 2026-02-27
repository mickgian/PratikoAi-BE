"""AttachmentResolver Service for DEV-007 File Attachment Feature.

This service resolves uploaded document IDs to their content and metadata
for use in the RAG pipeline. It validates ownership and handles missing/expired
documents gracefully.

DEV-007 Issue 4: Added wait-for-processing feature (OpenAI-style pattern).
When documents are still being processed, the resolver will poll and wait
for up to 60 seconds before timing out.

Usage:
    attachment_resolver = AttachmentResolver()
    attachments = await attachment_resolver.resolve_attachments(
        db=db_session,
        attachment_ids=[uuid1, uuid2],
        user_id=current_user.id,
    )
"""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger

# Use the proper database table model
from app.models.document import Document, ProcessingStatus

# Maximum number of attachments allowed per request
MAX_ATTACHMENTS = 5

# DEV-007 Issue 4: Wait-for-processing configuration (OpenAI-style)
# OpenAI uses 60 seconds timeout for file processing wait
PROCESSING_WAIT_TIMEOUT_SECONDS = 60
PROCESSING_POLL_INTERVAL_SECONDS = 2


class AttachmentResolverError(Exception):
    """Base exception for attachment resolver errors."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class AttachmentNotFoundError(AttachmentResolverError):
    """Raised when an attachment cannot be found."""

    def __init__(self, attachment_id: UUID):
        self.attachment_id = attachment_id
        message = f"Documento non trovato: {attachment_id}"
        super().__init__(message)


class AttachmentOwnershipError(AttachmentResolverError):
    """Raised when user doesn't own the attachment."""

    def __init__(self, attachment_id: UUID, user_id: int):  # DEV-007 Issue 7: int to match Document.user_id
        self.attachment_id = attachment_id
        self.user_id = user_id
        message = f"Accesso non autorizzato al documento: {attachment_id}"
        super().__init__(message)


class AttachmentProcessingError(AttachmentResolverError):
    """Raised when attachment processing failed or timed out (DEV-007 Issue 4)."""

    def __init__(self, attachment_id: UUID, message: str):
        self.attachment_id = attachment_id
        super().__init__(message)


class AttachmentResolver:
    """Service for resolving uploaded document IDs to attachment data.

    This service:
    1. Validates that attachment IDs exist
    2. Validates user ownership of attachments
    3. Waits for document processing if not complete (DEV-007 Issue 4)
    4. Returns document content and metadata for RAG pipeline

    Attributes:
        max_attachments: Maximum number of attachments allowed (default: 5)
        processing_wait_timeout_seconds: Max seconds to wait for processing (default: 60)
        processing_poll_interval_seconds: Seconds between polling checks (default: 2)
    """

    def __init__(
        self,
        max_attachments: int = MAX_ATTACHMENTS,
        processing_wait_timeout_seconds: int = PROCESSING_WAIT_TIMEOUT_SECONDS,
        processing_poll_interval_seconds: int = PROCESSING_POLL_INTERVAL_SECONDS,
    ):
        """Initialize the attachment resolver.

        Args:
            max_attachments: Maximum number of attachments allowed per request
            processing_wait_timeout_seconds: Max seconds to wait for processing
            processing_poll_interval_seconds: Seconds between polling checks
        """
        self.max_attachments = max_attachments
        self.processing_wait_timeout_seconds = processing_wait_timeout_seconds
        self.processing_poll_interval_seconds = processing_poll_interval_seconds

    async def resolve_attachments(
        self,
        db: AsyncSession,
        attachment_ids: list[UUID],
        user_id: int,  # DEV-007 Issue 7: int to match Document.user_id
    ) -> list[dict[str, Any]]:
        """Resolve attachment IDs to their content and metadata.

        Args:
            db: Async database session
            attachment_ids: List of document UUIDs to resolve
            user_id: UUID of the user requesting the attachments

        Returns:
            List of attachment dictionaries containing:
                - id: Document ID (string)
                - filename: Original filename
                - extracted_text: Extracted text content
                - extracted_data: Structured data (if available)
                - document_category: Document classification
                - mime_type: MIME type
                - file_size: File size in bytes
                - processing_status: Current processing status
                - is_expired: Whether document has expired
                - warning: Optional warning message

        Raises:
            AttachmentResolverError: If attachment limit exceeded or database error
            AttachmentNotFoundError: If attachment doesn't exist
            AttachmentOwnershipError: If user doesn't own the attachment
        """
        # Handle empty list
        if not attachment_ids:
            return []

        # Check attachment limit
        if len(attachment_ids) > self.max_attachments:
            raise AttachmentResolverError(
                f"Numero massimo di allegati superato: limite {self.max_attachments}, richiesti {len(attachment_ids)}"
            )

        resolved_attachments = []

        try:
            for attachment_id in attachment_ids:
                attachment = await self._resolve_single_attachment(
                    db=db,
                    attachment_id=attachment_id,
                    user_id=user_id,
                )
                resolved_attachments.append(attachment)

        except (AttachmentNotFoundError, AttachmentOwnershipError, AttachmentProcessingError):
            # Re-raise specific errors
            raise
        except Exception as e:
            logger.error(
                "attachment_resolution_failed",
                error=str(e),
                user_id=str(user_id),
                attachment_count=len(attachment_ids),
                exc_info=True,
            )
            raise AttachmentResolverError(f"Errore durante il recupero degli allegati: {str(e)}")

        return resolved_attachments

    async def _resolve_single_attachment(
        self,
        db: AsyncSession,
        attachment_id: UUID,
        user_id: int,  # DEV-007 Issue 7: int to match Document.user_id
    ) -> dict[str, Any]:
        """Resolve a single attachment ID, waiting for processing if needed.

        DEV-007 Issue 4: Now waits for document processing to complete using
        the OpenAI-style pattern (poll with timeout).

        Args:
            db: Async database session
            attachment_id: Document UUID to resolve
            user_id: UUID of the user requesting the attachment

        Returns:
            Attachment dictionary with content and metadata

        Raises:
            AttachmentNotFoundError: If attachment doesn't exist
            AttachmentOwnershipError: If user doesn't own the attachment
            AttachmentProcessingError: If processing failed or timed out
        """
        # Fetch document from database
        document = await self._fetch_document(db, attachment_id)

        # Check if document exists
        if document is None:
            logger.warning(
                "attachment_not_found",
                attachment_id=str(attachment_id),
                user_id=str(user_id),
            )
            raise AttachmentNotFoundError(attachment_id)

        # Check ownership
        if document.user_id != user_id:
            logger.warning(
                "attachment_ownership_denied",
                attachment_id=str(attachment_id),
                document_owner=str(document.user_id),
                requesting_user=str(user_id),
            )
            raise AttachmentOwnershipError(attachment_id, user_id)

        # DEV-007 Issue 4: Wait for processing if not complete (OpenAI-style pattern)
        # Processing statuses that indicate work in progress
        processing_in_progress_statuses = (
            ProcessingStatus.UPLOADED.value,
            ProcessingStatus.VALIDATING.value,
            ProcessingStatus.PROCESSING.value,
            ProcessingStatus.EXTRACTING.value,
            ProcessingStatus.ANALYZING.value,
        )

        if document.processing_status in processing_in_progress_statuses:
            logger.info(
                "attachment_still_processing",
                attachment_id=str(attachment_id),
                status=document.processing_status,
                user_id=str(user_id),
            )
            # Wait for processing to complete
            document = await self._wait_for_processing(db, attachment_id)

            if document is None:
                raise AttachmentProcessingError(
                    attachment_id, "Elaborazione documento scaduta. Riprova tra qualche secondo."
                )

        # Check for failed processing
        if document.processing_status == ProcessingStatus.FAILED.value:
            error_msg = getattr(document, "error_message", None) or "errore sconosciuto"
            raise AttachmentProcessingError(attachment_id, f"Elaborazione documento fallita: {error_msg}")

        # Check expiration
        is_expired = document.is_expired if hasattr(document, "is_expired") else False
        if document.expires_at:
            # Handle both naive (database) and aware datetime comparison
            now = datetime.now(UTC)
            expires_at = document.expires_at
            if expires_at.tzinfo is None:
                # Database datetime is naive, assume UTC
                expires_at = expires_at.replace(tzinfo=UTC)
            if now > expires_at:
                is_expired = True

        # Build attachment data
        attachment_data: dict[str, Any] = {
            "id": str(document.id),
            "filename": document.original_filename or document.filename,
            "extracted_text": document.extracted_text,
            "extracted_data": document.extracted_data,
            "document_category": document.document_category,
            "mime_type": document.mime_type,
            "file_size": document.file_size,
            "processing_status": document.processing_status,
            "is_expired": is_expired,
        }

        # Add warning for expired documents
        if is_expired:
            attachment_data["warning"] = "Documento scaduto. Il contenuto potrebbe non essere disponibile."

        logger.info(
            "attachment_resolved",
            attachment_id=str(attachment_id),
            user_id=str(user_id),
            filename=document.filename,
            document_category=document.document_category,
            processing_status=document.processing_status,
            is_expired=is_expired,
        )

        return attachment_data

    async def _fetch_document(
        self,
        db: AsyncSession,
        attachment_id: UUID,
    ) -> Document | None:
        """Fetch document from database.

        This method is separated to allow easy mocking in tests.

        Args:
            db: Async database session
            attachment_id: Document UUID to fetch

        Returns:
            Document object or None if not found
        """
        query = select(Document).where(
            and_(
                Document.id == attachment_id,
                Document.is_deleted == False,  # noqa: E712
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def _wait_for_processing(
        self,
        db: AsyncSession,
        document_id: UUID,
    ) -> Document | None:
        """Wait for document processing to complete (DEV-007 Issue 4).

        Implements OpenAI-style wait pattern: poll database at regular intervals
        until processing completes or timeout is reached.

        Args:
            db: Async database session
            document_id: Document UUID to wait for

        Returns:
            Document if processing completed, None if timeout reached
        """
        deadline = datetime.now(UTC) + timedelta(seconds=self.processing_wait_timeout_seconds)

        while datetime.now(UTC) < deadline:
            # Fetch fresh document state from database
            document = await self._fetch_document(db, document_id)

            if document is None:
                logger.warning(
                    "document_disappeared_during_wait",
                    document_id=str(document_id),
                )
                return None

            status = document.processing_status

            # Terminal states - return immediately
            if status == ProcessingStatus.COMPLETED.value:
                logger.info(
                    "document_processing_completed",
                    document_id=str(document_id),
                    wait_time_seconds=(
                        self.processing_wait_timeout_seconds - (deadline - datetime.now(UTC)).total_seconds()
                    ),
                )
                return document
            elif status == ProcessingStatus.FAILED.value:
                logger.warning(
                    "document_processing_failed",
                    document_id=str(document_id),
                    error_message=getattr(document, "error_message", None),
                )
                return document  # Return with failed status for error handling

            # Still processing - wait and retry
            seconds_remaining = (deadline - datetime.now(UTC)).total_seconds()
            logger.info(
                "waiting_for_document_processing",
                document_id=str(document_id),
                status=status,
                seconds_remaining=int(seconds_remaining),
            )
            await asyncio.sleep(self.processing_poll_interval_seconds)

        # Timeout reached
        logger.warning(
            "document_processing_timeout",
            document_id=str(document_id),
            timeout_seconds=self.processing_wait_timeout_seconds,
        )
        return None


# Singleton instance for convenience
attachment_resolver = AttachmentResolver()
