"""Document Upload and Processing API Endpoints.

FastAPI endpoints for drag & drop document upload functionality with Italian
tax document processing, secure storage, and AI analysis capabilities.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.core.logging import logger
from app.models.database import get_db
from app.models.document import DOCUMENT_CONFIG, Document, DocumentAnalysis, DocumentType, ProcessingStatus
from app.models.user import User
from app.services.document_processing_service import DocumentProcessingError, DocumentProcessor
from app.services.document_uploader import DocumentUploader, UploadValidationError
from app.services.italian_document_analyzer import ItalianDocumentAnalyzer
from app.services.secure_document_storage import SecureDocumentStorage

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=dict[str, Any])
async def upload_documents(
    files: list[UploadFile] = File(..., description="Documents to upload (max 5 files, 10MB each)"),
    analysis_query: str | None = Form(None, description="Optional analysis question"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload and process documents with drag & drop functionality.

    Supports PDF, Excel (.xlsx, .xls), and CSV files for Italian tax document analysis.
    """
    # DEV-007: Log upload request for debugging
    logger.info(
        "document_upload_request",
        user_id=str(current_user.id),
        file_count=len(files),
        filenames=[f.filename for f in files],
    )

    document_uploader = DocumentUploader()
    secure_storage = SecureDocumentStorage()

    try:
        # Validate upload limits
        document_uploader.validate_upload_limits(files)

        uploaded_documents = []
        processing_errors = []

        for file in files:
            try:
                # Validate individual file
                validation_result = await document_uploader.validate_file(file)

                # Create document record
                document = Document(
                    user_id=current_user.id,
                    original_filename=validation_result["original_filename"],
                    filename=validation_result["safe_filename"],
                    file_type=validation_result["file_type"].value,
                    file_size=validation_result["file_size"],
                    mime_type=validation_result["mime_type"],
                    file_hash=validation_result["file_hash"],
                    processing_status=ProcessingStatus.UPLOADED.value,
                    upload_ip="127.0.0.1",  # Would extract from request
                    virus_scan_status="clean" if validation_result["virus_scan"]["clean"] else "infected",
                    virus_scan_result=str(validation_result["virus_scan"]["threats"])
                    if validation_result["virus_scan"]["threats"]
                    else None,
                )

                # Save document to database
                db.add(document)
                await db.flush()  # Get the document ID

                # Store file securely
                file_content = await file.read()
                storage_result = await secure_storage.store_document(document, file_content)

                if storage_result["success"]:
                    document.processing_started_at = datetime.utcnow()

                    # DEV-007 Issue 8: Process document SYNCHRONOUSLY (not in background)
                    # This ensures document is ready when user sends chat message
                    processor = DocumentProcessor()

                    try:
                        # Update status to EXTRACTING
                        document.processing_status = ProcessingStatus.EXTRACTING.value
                        await db.commit()

                        # Extract text
                        text_result = await processor.extract_text(document)
                        if text_result["success"]:
                            document.extracted_text = text_result["text"]

                            # Update status to ANALYZING
                            document.processing_status = ProcessingStatus.ANALYZING.value
                            await db.commit()

                            # Extract structured data
                            structured_result = await processor.extract_structured_data(document)
                            if structured_result["success"]:
                                document.extracted_data = structured_result["data"]

                            # Classify document
                            classification = await processor.classify_document(document)
                            document.document_category = classification["category"]
                            document.document_confidence = classification["confidence"]

                            # Mark as COMPLETED
                            document.processing_status = ProcessingStatus.COMPLETED.value
                            document.processing_completed_at = datetime.utcnow()
                            document.processing_duration_seconds = int(
                                (document.processing_completed_at - document.processing_started_at).total_seconds()
                            )

                            logger.info(
                                "document_processing_completed",
                                document_id=str(document.id),
                                filename=document.original_filename,
                                duration_seconds=document.processing_duration_seconds,
                            )
                        else:
                            document.processing_status = ProcessingStatus.FAILED.value
                            document.error_message = text_result.get("error", "Text extraction failed")
                            logger.warning(
                                "document_text_extraction_failed",
                                document_id=str(document.id),
                                error=document.error_message,
                            )

                    except Exception as proc_error:
                        logger.error(
                            "document_processing_error",
                            document_id=str(document.id),
                            error=str(proc_error),
                            exc_info=True,
                        )
                        document.processing_status = ProcessingStatus.FAILED.value
                        document.error_message = str(proc_error)

                    uploaded_documents.append(
                        {
                            "id": str(document.id),
                            "original_filename": document.original_filename,
                            "file_type": document.file_type,
                            "file_size": document.file_size,
                            "file_size_mb": round(document.file_size / (1024 * 1024), 2),
                            "status": document.processing_status,
                            "document_category": document.document_category,
                            "upload_timestamp": document.upload_timestamp.isoformat(),
                            "expires_at": document.expires_at.isoformat(),
                        }
                    )

                else:
                    processing_errors.append(
                        {
                            "filename": file.filename,
                            "error": f"Storage failed: {storage_result.get('error', 'Unknown error')}",
                        }
                    )

            except UploadValidationError as e:
                processing_errors.append({"filename": file.filename, "error": str(e)})
                continue

            except Exception as e:
                logger.error(f"Document upload failed for {file.filename}: {str(e)}")
                processing_errors.append({"filename": file.filename, "error": f"Upload failed: {str(e)}"})
                continue

        # Commit all successful uploads
        await db.commit()

        response = {
            "success": len(uploaded_documents) > 0,
            "uploaded_documents": uploaded_documents,
            "total_uploaded": len(uploaded_documents),
            "errors": processing_errors,
            "message": f"Caricati ed elaborati {len(uploaded_documents)} documenti su {len(files)}."
            if uploaded_documents
            else "Nessun documento caricato con successo.",
        }

        # DEV-007: Log response for debugging
        logger.info(
            "document_upload_response",
            success=response["success"],
            total_uploaded=response["total_uploaded"],
            error_count=len(processing_errors),
        )

        return response

    except Exception as e:
        await db.rollback()
        logger.error(f"Document upload endpoint failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Errore durante il caricamento: {str(e)}")


@router.get("/", response_model=dict[str, Any])
async def get_user_documents(
    skip: int = 0,
    limit: int = 20,
    status: str | None = None,
    document_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get user's uploaded documents with filtering options."""
    try:
        # Build query
        query = select(Document).where(and_(Document.user_id == current_user.id, Document.is_deleted is False))

        # Apply filters
        if status:
            query = query.where(Document.processing_status == status)

        if document_type:
            query = query.where(Document.file_type == document_type)

        # Order by upload time (newest first)
        query = query.order_by(Document.upload_timestamp.desc())

        # Apply pagination
        query = query.offset(skip).limit(limit)

        # Execute query
        result = await db.execute(query)
        documents = result.scalars().all()

        # Get total count
        count_query = select(Document).where(and_(Document.user_id == current_user.id, Document.is_deleted is False))
        if status:
            count_query = count_query.where(Document.processing_status == status)
        if document_type:
            count_query = count_query.where(Document.file_type == document_type)

        total_result = await db.execute(count_query)
        total_count = len(total_result.scalars().all())

        # Serialize documents
        document_list = []
        for doc in documents:
            document_list.append(
                {
                    "id": str(doc.id),
                    "original_filename": doc.original_filename,
                    "file_type": doc.file_type,
                    "file_size": doc.file_size,
                    "file_size_mb": round(doc.file_size / (1024 * 1024), 2),
                    "processing_status": doc.processing_status,
                    "document_category": doc.document_category,
                    "document_confidence": doc.document_confidence,
                    "upload_timestamp": doc.upload_timestamp.isoformat(),
                    "processing_completed_at": doc.processing_completed_at.isoformat()
                    if doc.processing_completed_at
                    else None,
                    "expires_at": doc.expires_at.isoformat(),
                    "is_expired": doc.is_expired,
                    "analysis_count": doc.analysis_count,
                    "last_analyzed_at": doc.last_analyzed_at.isoformat() if doc.last_analyzed_at else None,
                    "error_message": doc.error_message,
                }
            )

        return {
            "documents": document_list,
            "total": total_count,
            "skip": skip,
            "limit": limit,
            "has_next": skip + limit < total_count,
        }

    except Exception as e:
        logger.error(f"Get documents failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Errore nel recupero documenti: {str(e)}")


@router.get("/{document_id}", response_model=dict[str, Any])
async def get_document_details(
    document_id: UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Get detailed information about a specific document."""
    try:
        # Get document
        document = await get_user_document(db, document_id, current_user.id)

        # Get analyses for this document
        analyses_result = await db.execute(
            select(DocumentAnalysis)
            .where(DocumentAnalysis.document_id == document_id)
            .order_by(DocumentAnalysis.requested_at.desc())
        )
        analyses = analyses_result.scalars().all()

        # Serialize document with full details
        document_data = document.to_dict(include_content=True)

        # Add analyses
        document_data["analyses"] = [analysis.to_dict() for analysis in analyses]

        return {"document": document_data, "total_analyses": len(analyses)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get document details failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Errore nel recupero dettagli: {str(e)}")


@router.post("/{document_id}/analyze", response_model=dict[str, Any])
async def analyze_document(
    document_id: UUID,
    query: str = Form(..., description="Domanda di analisi per il documento"),
    analysis_type: str = Form(
        "general", description="Tipo di analisi (general, compliance_check, financial_analysis)"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Analyze document with AI using specific query."""
    try:
        # Get document
        document = await get_user_document(db, document_id, current_user.id)

        if document.processing_status != ProcessingStatus.COMPLETED.value:
            raise HTTPException(
                status_code=400, detail="Il documento deve essere completamente elaborato prima dell'analisi"
            )

        if not document.extracted_data:
            raise HTTPException(status_code=400, detail="Nessun dato strutturato disponibile per l'analisi")

        # Create analysis record
        analysis = DocumentAnalysis(
            document_id=document_id,
            user_id=current_user.id,
            query=query,
            analysis_type=analysis_type,
            requested_at=datetime.utcnow(),
        )

        db.add(analysis)
        await db.flush()  # Get analysis ID

        # Perform AI analysis
        analyzer = ItalianDocumentAnalyzer()
        analysis_result = await analyzer.analyze_document(
            document_data=document.extracted_data,
            query=query,
            analysis_type=analysis_type,
            document_category=document.document_category,
            extracted_text=document.extracted_text,
        )

        if analysis_result["success"]:
            # Update analysis with results
            analysis.completed_at = datetime.utcnow()
            analysis.duration_seconds = int((analysis.completed_at - analysis.requested_at).total_seconds())
            analysis.analysis_result = analysis_result["analysis"]
            analysis.ai_response = analysis_result["response"]
            analysis.confidence_score = analysis_result["confidence_score"]
            analysis.llm_model = "gpt-4o-mini"  # Would get from settings

            # Update document analytics
            document.analysis_count += 1
            document.last_analyzed_at = datetime.utcnow()

            await db.commit()

            return {
                "success": True,
                "analysis_id": str(analysis.id),
                "analysis_type": analysis_type,
                "query": query,
                "response": analysis.ai_response,
                "confidence_score": analysis.confidence_score,
                "duration_seconds": analysis.duration_seconds,
                "completed_at": analysis.completed_at.isoformat(),
                "structured_analysis": analysis.analysis_result,
            }

        else:
            # Update analysis with error
            analysis.completed_at = datetime.utcnow()
            analysis.duration_seconds = int((analysis.completed_at - analysis.requested_at).total_seconds())
            analysis.ai_response = f"Errore durante l'analisi: {analysis_result.get('error', 'Errore sconosciuto')}"

            await db.commit()

            raise HTTPException(
                status_code=500, detail=f"Analisi fallita: {analysis_result.get('error', 'Errore sconosciuto')}"
            )

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Document analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Errore durante l'analisi: {str(e)}")


@router.delete("/{document_id}")
async def delete_document(
    document_id: UUID,
    reason: str = Form("user_request", description="Motivo della cancellazione"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete document with GDPR compliance."""
    try:
        # Get document
        document = await get_user_document(db, document_id, current_user.id)

        # Perform GDPR-compliant deletion
        secure_storage = SecureDocumentStorage()
        deletion_result = await secure_storage.gdpr_delete_document(
            document_id=document_id, user_id=current_user.id, reason=reason
        )

        if deletion_result["success"]:
            # Mark document as deleted in database
            document.is_deleted = True
            document.deleted_at = datetime.utcnow()

            await db.commit()

            logger.info(
                "document_deleted_by_user",
                document_id=str(document_id),
                user_id=str(current_user.id),
                filename=document.original_filename,
                reason=reason,
            )

            return {
                "success": True,
                "message": "Documento eliminato in modo sicuro",
                "document_id": str(document_id),
                "gdpr_compliant": True,
                "deleted_at": document.deleted_at.isoformat(),
            }

        else:
            raise HTTPException(
                status_code=500,
                detail=f"Errore durante l'eliminazione: {deletion_result.get('error', 'Errore sconosciuto')}",
            )

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Document deletion failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Errore durante l'eliminazione: {str(e)}")


@router.get("/config/upload-limits", response_model=dict[str, Any])
async def get_upload_configuration():
    """Get upload limits and supported file types for frontend."""
    return {
        "max_file_size_mb": DOCUMENT_CONFIG["MAX_FILE_SIZE_MB"],
        "max_files_per_upload": DOCUMENT_CONFIG["MAX_FILES_PER_UPLOAD"],
        "supported_file_types": {
            "PDF": {
                "extensions": [".pdf"],
                "mime_types": ["application/pdf"],
                "description": "Documenti fiscali (fatture, F24, dichiarazioni) e legali (citazioni, ricorsi, contratti)",
            },
            "Excel": {
                "extensions": [".xlsx", ".xls"],
                "mime_types": [
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "application/vnd.ms-excel",
                ],
                "description": "Bilanci, registri IVA, contabilità aziendale",
            },
            "CSV": {
                "extensions": [".csv"],
                "mime_types": ["text/csv"],
                "description": "Registri IVA, estratti conto, dati contabili",
            },
        },
        "processing_timeout_seconds": DOCUMENT_CONFIG["PROCESSING_TIMEOUT_SECONDS"],
        "default_expiration_hours": DOCUMENT_CONFIG["DEFAULT_EXPIRATION_HOURS"],
        "italian_text": {
            "drop_zone_text": "Trascina qui i tuoi documenti fiscali e legali (PDF, Excel, CSV)",
            "or_browse": "oppure seleziona i file",
            "max_size_text": f"Massimo {DOCUMENT_CONFIG['MAX_FILE_SIZE_MB']}MB per file, fino a {DOCUMENT_CONFIG['MAX_FILES_PER_UPLOAD']} file",
            "supported_formats": "Formati supportati: fatture elettroniche, F24, bilanci, citazioni, contratti, ricorsi",
            "processing_time": "I documenti verranno elaborati automaticamente e conservati per 48 ore",
        },
    }


# Helper Functions


async def get_user_document(db: AsyncSession, document_id: UUID, user_id: UUID) -> Document:
    """Get document owned by user or raise 404."""
    result = await db.execute(
        select(Document).where(
            and_(Document.id == document_id, Document.user_id == user_id, Document.is_deleted is False)
        )
    )

    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Documento non trovato")

    return document


async def process_document_background(document_id: UUID, analysis_query: str | None):
    """Background task for document processing."""
    from app.core.database import async_session

    async with async_session() as db:
        try:
            # Get document
            result = await db.execute(select(Document).where(Document.id == document_id))
            document = result.scalar_one_or_none()

            if not document:
                logger.error(f"Document {document_id} not found for background processing")
                return

            processor = DocumentProcessor()

            # Update status
            document.processing_status = ProcessingStatus.EXTRACTING.value
            await db.commit()

            # Extract text
            text_result = await processor.extract_text(document)
            if text_result["success"]:
                document.extracted_text = text_result["text"]

                # Extract structured data
                document.processing_status = ProcessingStatus.ANALYZING.value
                await db.commit()

                structured_result = await processor.extract_structured_data(document)
                if structured_result["success"]:
                    document.extracted_data = structured_result["data"]

                    # Classify document
                    classification = await processor.classify_document(document)
                    document.document_category = classification["category"]
                    document.document_confidence = classification["confidence"]

                    # Complete processing
                    document.processing_status = ProcessingStatus.COMPLETED.value
                    document.processing_completed_at = datetime.utcnow()
                    document.processing_duration_seconds = int(
                        (document.processing_completed_at - document.processing_started_at).total_seconds()
                    )

                    # If analysis query provided, run initial analysis
                    if analysis_query:
                        analyzer = ItalianDocumentAnalyzer()
                        analysis_result = await analyzer.analyze_document(
                            document_data=document.extracted_data,
                            query=analysis_query,
                            analysis_type="general",
                            document_category=document.document_category,
                            extracted_text=document.extracted_text,
                        )

                        if analysis_result["success"]:
                            # Create analysis record
                            analysis = DocumentAnalysis(
                                document_id=document.id,
                                user_id=document.user_id,
                                query=analysis_query,
                                analysis_type="general",
                                requested_at=document.processing_started_at,
                                completed_at=document.processing_completed_at,
                                duration_seconds=document.processing_duration_seconds,
                                analysis_result=analysis_result["analysis"],
                                ai_response=analysis_result["response"],
                                confidence_score=analysis_result["confidence_score"],
                                llm_model="gpt-4o-mini",
                            )

                            db.add(analysis)
                            document.analysis_count = 1
                            document.last_analyzed_at = document.processing_completed_at

                else:
                    document.processing_status = ProcessingStatus.FAILED.value
                    document.error_message = structured_result.get("error", "Structured data extraction failed")

            else:
                document.processing_status = ProcessingStatus.FAILED.value
                document.error_message = text_result.get("error", "Text extraction failed")

            await db.commit()

            logger.info(
                "document_background_processing_completed",
                document_id=str(document_id),
                status=document.processing_status,
                duration_seconds=document.processing_duration_seconds,
            )

        except Exception as e:
            logger.error(f"Background document processing failed: {str(e)}")

            # Update document status to failed
            try:
                document.processing_status = ProcessingStatus.FAILED.value
                document.error_message = str(e)
                await db.commit()
            except Exception:
                pass
