"""DocumentIngestTool for LangGraph - RAG STEP 82.

This tool processes document attachments by extracting text, classifying documents,
and preparing them for use in the RAG pipeline. It handles various file formats
including PDF, Excel, CSV, and images with OCR capabilities.

RAG STEP 82 — DocumentIngestTool.process Process attachments
(RAG.preflight.documentingesttool.process.process.attachments)
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, field_validator

from app.core.logging import logger
from app.models.document_simple import Document, DocumentType
from app.observability.rag_logging import rag_step_log, rag_step_timer
from app.services.document_processing_service import DocumentProcessingError, DocumentProcessor


class DocumentIngestInput(BaseModel):
    """Input schema for document ingest operations."""

    attachments: list[dict[str, Any]] = Field(
        description="List of attachments to process, each containing filename, content_type, size, content, and attachment_id"
    )
    user_id: str = Field(description="User ID for tracking and audit purposes")
    session_id: str = Field(description="Session ID for conversation context")
    max_file_size: int | None = Field(
        default=10 * 1024 * 1024,  # 10MB default
        description="Maximum file size in bytes (default: 10MB)",
    )
    supported_types: list[str] | None = Field(
        default=[
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel",
            "text/csv",
            "image/jpeg",
            "image/png",
        ],
        description="List of supported MIME types",
    )

    @field_validator("attachments")
    @classmethod
    def validate_attachments(cls, v):
        if not v:
            raise ValueError("At least one attachment is required")

        required_fields = ["filename", "content_type", "size", "content", "attachment_id"]
        for attachment in v:
            for field in required_fields:
                if field not in attachment:
                    raise ValueError(f"Attachment missing required field: {field}")

        return v


class DocumentIngestTool(BaseTool):
    """Tool for processing document attachments in the RAG pipeline."""

    name: str = "DocumentIngestTool"
    description: str = """Process document attachments for text extraction and classification.

    Handles PDF, Excel, CSV, and image files with OCR support.
    Extracts text content and classifies documents for Italian business/tax contexts.

    Input should contain:
    - attachments: List of file attachments with metadata
    - user_id: User identifier for tracking
    - session_id: Session identifier for context
    """

    args_schema: type[BaseModel] = DocumentIngestInput

    def __init__(self):
        """Initialize the document ingest tool."""
        super().__init__()
        self._processor = None

    def _get_processor(self) -> DocumentProcessor:
        """Get or create document processor instance."""
        if self._processor is None:
            self._processor = DocumentProcessor()
        return self._processor

    def _validate_attachment(
        self, attachment: dict[str, Any], max_file_size: int, supported_types: list[str]
    ) -> str | None:
        """Validate a single attachment.

        Args:
            attachment: Attachment data dictionary
            max_file_size: Maximum allowed file size in bytes
            supported_types: List of supported MIME types

        Returns:
            Error message if validation fails, None if valid
        """
        # Check file size
        if attachment.get("size", 0) > max_file_size:
            return f"File size {attachment.get('size', 0)} bytes exceeds limit of {max_file_size} bytes"

        # Check content type
        content_type = attachment.get("content_type", "")
        if content_type not in supported_types:
            return f"Unsupported file type: {content_type}. Supported types: {', '.join(supported_types)}"

        # Check content exists
        if not attachment.get("content"):
            return "File content is empty"

        return None

    async def _process_single_attachment(
        self, attachment: dict[str, Any], user_id: str, session_id: str
    ) -> dict[str, Any]:
        """Process a single attachment.

        Args:
            attachment: Attachment data dictionary
            user_id: User identifier
            session_id: Session identifier

        Returns:
            Processing result dictionary
        """
        filename = attachment.get("filename", "unknown")
        attachment_id = attachment.get("attachment_id", "unknown")

        try:
            # Create Document object for processing
            # Convert user_id string to UUID if needed
            try:
                user_uuid = uuid.UUID(user_id) if user_id else None
            except ValueError:
                # If user_id is not a valid UUID, generate one or use None
                user_uuid = uuid.uuid4()

            document = Document(
                filename=filename,
                content_type=attachment.get("content_type", ""),
                size_bytes=attachment.get("size", 0),
                content=attachment.get("content", b""),
                file_hash=None,  # Will be computed if needed
                user_id=user_uuid,
                document_type=DocumentType.PDF,  # Will be updated based on content_type
            )

            processor = self._get_processor()

            # Extract text content
            rag_step_log(
                82,
                "RAG.preflight.documentingesttool.process.process.attachments",
                "DocIngest",
                attachment_id=attachment_id,
                filename=filename,
                processing_stage="text_extraction",
                user_id=user_id,
                session_id=session_id,
            )

            text_result = await processor.extract_text(document)

            # Classify document
            rag_step_log(
                82,
                "RAG.preflight.documentingesttool.process.process.attachments",
                "DocIngest",
                attachment_id=attachment_id,
                filename=filename,
                processing_stage="document_classification",
                user_id=user_id,
                session_id=session_id,
            )

            classification_result = await processor.classify_document(document, text_result.get("text", ""))

            # Success result
            result = {
                "attachment_id": attachment_id,
                "filename": filename,
                "status": "success",
                "extracted_text": text_result,
                "document_classification": classification_result,
                "processing_timestamp": datetime.utcnow().isoformat(),
                "file_size": attachment.get("size", 0),
                "content_type": attachment.get("content_type", ""),
            }

            rag_step_log(
                82,
                "RAG.preflight.documentingesttool.process.process.attachments",
                "DocIngest",
                attachment_id=attachment_id,
                filename=filename,
                processing_stage="completed",
                status="success",
                user_id=user_id,
                session_id=session_id,
                text_length=len(text_result.get("text", "")),
                document_category=classification_result.get("category", "unknown"),
                confidence=classification_result.get("confidence", 0.0),
            )

            return result

        except DocumentProcessingError as e:
            error_msg = f"Document processing failed: {str(e)}"
            logger.error(
                "document_processing_failed",
                attachment_id=attachment_id,
                filename=filename,
                error=error_msg,
                user_id=user_id,
                session_id=session_id,
            )

            rag_step_log(
                82,
                "RAG.preflight.documentingesttool.process.process.attachments",
                "DocIngest",
                attachment_id=attachment_id,
                filename=filename,
                processing_stage="failed",
                status="error",
                error=error_msg,
                user_id=user_id,
                session_id=session_id,
            )

            return {
                "attachment_id": attachment_id,
                "filename": filename,
                "status": "error",
                "error": error_msg,
                "processing_timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            error_msg = f"Unexpected error processing document: {str(e)}"
            logger.error(
                "document_ingest_unexpected_error",
                attachment_id=attachment_id,
                filename=filename,
                error=error_msg,
                user_id=user_id,
                session_id=session_id,
                exc_info=True,
            )

            rag_step_log(
                82,
                "RAG.preflight.documentingesttool.process.process.attachments",
                "DocIngest",
                attachment_id=attachment_id,
                filename=filename,
                processing_stage="failed",
                status="error",
                error=error_msg,
                user_id=user_id,
                session_id=session_id,
            )

            return {
                "attachment_id": attachment_id,
                "filename": filename,
                "status": "error",
                "error": error_msg,
                "processing_timestamp": datetime.utcnow().isoformat(),
            }

    async def _arun(
        self,
        attachments: list[dict[str, Any]],
        user_id: str,
        session_id: str,
        max_file_size: int = 10 * 1024 * 1024,
        supported_types: list[str] = None,
    ) -> dict[str, Any]:
        """Process document attachments asynchronously.

        Args:
            attachments: List of attachment dictionaries
            user_id: User identifier
            session_id: Session identifier
            max_file_size: Maximum file size in bytes
            supported_types: List of supported MIME types

        Returns:
            Processing results dictionary
        """
        if supported_types is None:
            supported_types = [
                "application/pdf",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "application/vnd.ms-excel",
                "text/csv",
                "image/jpeg",
                "image/png",
            ]

        # RAG STEP 82: Use timer for performance tracking
        with rag_step_timer(
            82,
            "RAG.preflight.documentingesttool.process.process.attachments",
            "DocIngest",
            user_id=user_id,
            session_id=session_id,
            attachment_count=len(attachments),
        ):
            # Initial logging
            rag_step_log(
                82,
                "RAG.preflight.documentingesttool.process.process.attachments",
                "DocIngest",
                user_id=user_id,
                session_id=session_id,
                attachment_count=len(attachments),
                processing_stage="started",
            )

            processed_documents = []

            for attachment in attachments:
                # Validate attachment
                validation_error = self._validate_attachment(attachment, max_file_size, supported_types)
                if validation_error:
                    rag_step_log(
                        82,
                        "RAG.preflight.documentingesttool.process.process.attachments",
                        "DocIngest",
                        attachment_id=attachment.get("attachment_id", "unknown"),
                        filename=attachment.get("filename", "unknown"),
                        processing_stage="validation_failed",
                        status="error",
                        error=validation_error,
                        user_id=user_id,
                        session_id=session_id,
                    )

                    processed_documents.append(
                        {
                            "attachment_id": attachment.get("attachment_id", "unknown"),
                            "filename": attachment.get("filename", "unknown"),
                            "status": "error",
                            "error": validation_error,
                            "processing_timestamp": datetime.utcnow().isoformat(),
                        }
                    )
                    continue

                # Process the attachment
                result = await self._process_single_attachment(attachment, user_id, session_id)
                processed_documents.append(result)

            # Final logging
            success_count = sum(1 for doc in processed_documents if doc.get("status") == "success")
            error_count = len(processed_documents) - success_count

            rag_step_log(
                82,
                "RAG.preflight.documentingesttool.process.process.attachments",
                "DocIngest",
                user_id=user_id,
                session_id=session_id,
                attachment_count=len(attachments),
                success_count=success_count,
                error_count=error_count,
                processing_stage="completed",
            )

            return {
                "processed_documents": processed_documents,
                "total_count": len(attachments),
                "success_count": success_count,
                "error_count": error_count,
                "processing_timestamp": datetime.utcnow().isoformat(),
            }

    def _run(self, **kwargs) -> str:
        """Synchronous wrapper (not recommended, use async version)."""
        # For LangChain compatibility, but document processing should be async
        import asyncio

        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(self._arun(**kwargs))
        return json.dumps(result, ensure_ascii=False, indent=2)

    async def ainvoke(self, input_data: dict[str, Any], **kwargs) -> str:
        """Async invoke method for LangChain compatibility."""
        result = await self._arun(**input_data)
        return json.dumps(result, ensure_ascii=False, indent=2)


# Create tool instance for export
document_ingest_tool = DocumentIngestTool()
