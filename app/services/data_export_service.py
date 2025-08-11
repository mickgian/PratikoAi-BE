"""
Comprehensive Data Export Service for GDPR Article 20 Compliance.

This service handles complete user data exports with Italian market compliance,
privacy protection, and secure handling of sensitive information.
"""

import json
import csv
import zipfile
import hashlib
import asyncio
from io import StringIO, BytesIO
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID, uuid4
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from sqlalchemy.orm import selectinload
import boto3
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.logging import logger
from app.core.encryption import EncryptionService
from app.models.user import User
from app.models.subscription import Subscription, SubscriptionPlan, Invoice
from app.models.data_export import (
    DataExportRequest, ExportFormat, ExportStatus, PrivacyLevel,
    ExportAuditLog, QueryHistory, DocumentAnalysis, TaxCalculation,
    FAQInteraction, KnowledgeBaseSearch, ElectronicInvoice
)
from app.services.cache import get_redis_client
from app.services.email_service import EmailService


class ExportLimitExceeded(Exception):
    """Raised when user exceeds export rate limit"""
    pass


class ExportNotFound(Exception):
    """Raised when export request is not found"""
    pass


class ExportAccessDenied(Exception):
    """Raised when user tries to access someone else's export"""
    pass


class DataExportService:
    """
    Comprehensive data export service for GDPR Article 20 compliance.
    
    Handles complete user data collection, formatting, and secure delivery
    with Italian market compliance and privacy protection.
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.encryption = EncryptionService()
        self.redis = get_redis_client()
        self.email_service = EmailService()
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        
        # Export configuration
        self.max_exports_per_day = 5
        self.max_file_size_mb = 100
        self.export_retention_hours = 24
        self.max_download_count = 10
        
    async def create_export_request(
        self,
        user_id: UUID,
        format: ExportFormat = ExportFormat.JSON,
        options: Optional[Dict[str, Any]] = None
    ) -> DataExportRequest:
        """
        Create a new data export request with rate limiting and validation.
        
        Args:
            user_id: User requesting the export
            format: Export format (JSON, CSV, or BOTH)
            options: Additional export options
            
        Returns:
            DataExportRequest: Created export request
            
        Raises:
            ExportLimitExceeded: If user exceeds rate limit
        """
        try:
            # Check rate limiting
            recent_exports = await self._count_recent_exports(user_id, hours=24)
            if recent_exports >= self.max_exports_per_day:
                raise ExportLimitExceeded(
                    f"Massimo {self.max_exports_per_day} export al giorno raggiunti. "
                    f"Riprova tra 24 ore."
                )
            
            # Validate user exists
            user = await self._get_user(user_id)
            if not user:
                raise ValueError("Utente non trovato")
            
            # Process options
            if not options:
                options = {}
                
            # Create export request
            export_request = DataExportRequest(
                user_id=user_id,
                format=format,
                privacy_level=PrivacyLevel(options.get("privacy_level", "full")),
                include_sensitive=options.get("include_sensitive", True),
                anonymize_pii=options.get("anonymize_pii", False),
                date_from=options.get("date_from"),
                date_to=options.get("date_to"),
                
                # Italian specific options
                include_fatture=options.get("include_fatture", True),
                include_f24=options.get("include_f24", True),
                include_dichiarazioni=options.get("include_dichiarazioni", True),
                mask_codice_fiscale=options.get("mask_codice_fiscale", False),
                
                # Data categories
                include_profile=options.get("include_profile", True),
                include_queries=options.get("include_queries", True),
                include_documents=options.get("include_documents", True),
                include_calculations=options.get("include_calculations", True),
                include_subscriptions=options.get("include_subscriptions", True),
                include_invoices=options.get("include_invoices", True),
                include_usage_stats=options.get("include_usage_stats", True),
                include_faq_interactions=options.get("include_faq_interactions", True),
                include_knowledge_searches=options.get("include_knowledge_searches", True),
                
                # Security context
                request_ip=options.get("request_ip"),
                user_agent=options.get("user_agent")
            )
            
            self.db.add(export_request)
            await self.db.commit()
            await self.db.refresh(export_request)
            
            # Create audit log
            await self._create_audit_log(
                export_request.id,
                user_id,
                "requested",
                {"format": format.value, "options": options}
            )
            
            # Queue for background processing
            await self._queue_export_job(export_request.id)
            
            logger.info(
                f"Data export requested: {export_request.id} by user {user_id}, "
                f"format: {format.value}"
            )
            
            return export_request
            
        except Exception as e:
            logger.error(f"Error creating export request: {e}")
            await self.db.rollback()
            raise

    async def process_export(self, export_id: UUID) -> None:
        """
        Process a data export request asynchronously.
        
        Args:
            export_id: Export request ID to process
        """
        export_request = None
        try:
            # Get export request
            export_request = await self._get_export_request(export_id)
            if not export_request:
                raise ExportNotFound(f"Export request {export_id} not found")
            
            # Update status to processing
            export_request.status = ExportStatus.PROCESSING
            export_request.started_at = datetime.utcnow()
            await self.db.commit()
            
            # Create audit log
            await self._create_audit_log(
                export_request.id,
                export_request.user_id,
                "started"
            )
            
            # Initialize progress tracking
            progress_tracker = ExportProgressTracker(self.redis)
            await progress_tracker.update_progress(
                str(export_id), "Inizializzazione export", 1, 8
            )
            
            # Collect all user data
            await progress_tracker.update_progress(
                str(export_id), "Raccolta dati utente", 2, 8
            )
            user_data = await self._collect_user_data(export_request)
            
            # Generate export files
            await progress_tracker.update_progress(
                str(export_id), "Generazione file export", 3, 8
            )
            files = await self._generate_export_files(user_data, export_request)
            
            # Create ZIP if multiple files or large size
            await progress_tracker.update_progress(
                str(export_id), "Creazione archivio", 4, 8
            )
            final_file = await self._create_final_export_file(files, export_request)
            
            # Upload to secure storage
            await progress_tracker.update_progress(
                str(export_id), "Caricamento sicuro", 5, 8
            )
            download_url = await self._upload_export_file(final_file, export_request)
            
            # Update request status
            await progress_tracker.update_progress(
                str(export_id), "Finalizzazione", 6, 8
            )
            export_request.status = ExportStatus.COMPLETED
            export_request.completed_at = datetime.utcnow()
            export_request.download_url = download_url
            export_request.file_size_bytes = len(final_file["content"])
            await self.db.commit()
            
            # Send notification email
            await progress_tracker.update_progress(
                str(export_id), "Invio notifica", 7, 8
            )
            await self._send_export_ready_email(export_request)
            
            # Complete progress
            await progress_tracker.update_progress(
                str(export_id), "Export completato", 8, 8
            )
            
            # Create completion audit log
            await self._create_audit_log(
                export_request.id,
                export_request.user_id,
                "completed",
                {
                    "file_size_mb": round(export_request.file_size_bytes / 1024 / 1024, 2),
                    "processing_time_seconds": export_request.processing_time_seconds
                }
            )
            
            logger.info(
                f"Data export completed: {export_request.id}, "
                f"size: {export_request.file_size_bytes} bytes"
            )
            
        except Exception as e:
            logger.error(f"Error processing export {export_id}: {e}")
            
            if export_request:
                # Update status to failed
                export_request.status = ExportStatus.FAILED
                export_request.error_message = str(e)
                export_request.retry_count += 1
                await self.db.commit()
                
                # Create failure audit log
                await self._create_audit_log(
                    export_request.id,
                    export_request.user_id,
                    "failed",
                    {"error": str(e), "retry_count": export_request.retry_count}
                )
                
                # Send error notification
                await self._send_export_error_email(export_request, str(e))
            
            raise

    async def _collect_user_data(self, export_request: DataExportRequest) -> Dict[str, Any]:
        """
        Collect all user data for export based on request configuration.
        
        Args:
            export_request: Export request with configuration
            
        Returns:
            Dict containing all user data organized by category
        """
        user_id = export_request.user_id
        data = {
            "export_info": {
                "generated_at": datetime.utcnow().isoformat(),
                "format_version": "1.2",
                "export_id": str(export_request.id),
                "user_id": str(user_id),
                "date_range": {
                    "from": export_request.date_from.isoformat() if export_request.date_from else None,
                    "to": export_request.date_to.isoformat() if export_request.date_to else None
                },
                "privacy_level": export_request.privacy_level.value,
                "italian_compliance": True,
                "gdpr_article": "Article 20 - Right to data portability"
            }
        }
        
        # 1. User Profile Data
        if export_request.include_profile:
            data["profile"] = await self._collect_profile_data(user_id, export_request)
        
        # 2. Query History
        if export_request.include_queries:
            data["queries"] = await self._collect_query_history(user_id, export_request)
        
        # 3. Document Analysis Metadata
        if export_request.include_documents:
            data["documents"] = await self._collect_document_metadata(user_id, export_request)
        
        # 4. Tax Calculations
        if export_request.include_calculations:
            data["tax_calculations"] = await self._collect_tax_calculations(user_id, export_request)
        
        # 5. Subscription and Billing History
        if export_request.include_subscriptions:
            data["subscriptions"] = await self._collect_subscription_history(user_id, export_request)
        
        # 6. Invoice Data (including Italian invoices)
        if export_request.include_invoices:
            data["invoices"] = await self._collect_invoice_data(user_id, export_request)
        
        # 7. Italian Electronic Invoices (Fatture Elettroniche)
        if export_request.include_fatture:
            data["fatture_elettroniche"] = await self._collect_electronic_invoices(user_id, export_request)
        
        # 8. Usage Statistics
        if export_request.include_usage_stats:
            data["usage_statistics"] = await self._collect_usage_statistics(user_id, export_request)
        
        # 9. FAQ Interactions
        if export_request.include_faq_interactions:
            data["faq_interactions"] = await self._collect_faq_interactions(user_id, export_request)
        
        # 10. Knowledge Base Searches
        if export_request.include_knowledge_searches:
            data["knowledge_searches"] = await self._collect_knowledge_searches(user_id, export_request)
        
        # 11. Compliance and Legal Information
        data["compliance_info"] = await self._generate_compliance_info(export_request)
        
        return data

    async def _collect_profile_data(self, user_id: UUID, export_request: DataExportRequest) -> Dict[str, Any]:
        """Collect user profile data with privacy controls"""
        user = await self._get_user(user_id)
        if not user:
            return {}
        
        profile = {
            "user_id": str(user_id),
            "email": self._process_sensitive_field(user.email, export_request, "email"),
            "full_name": self._process_sensitive_field(user.full_name, export_request, "name"),
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "language": "it_IT",
            "timezone": "Europe/Rome",
            "account_status": getattr(user, 'status', 'active'),
            "subscription_status": getattr(user, 'subscription_status', None)
        }
        
        # Italian specific data
        if hasattr(user, 'is_business') and user.is_business:
            profile["business_info"] = {
                "is_business": True,
                "partita_iva": self._process_sensitive_field(
                    getattr(user, 'partita_iva', None), 
                    export_request, 
                    "partita_iva"
                )
            }
        
        if hasattr(user, 'codice_fiscale') and user.codice_fiscale:
            if export_request.mask_codice_fiscale:
                profile["codice_fiscale"] = self._mask_codice_fiscale(user.codice_fiscale)
            else:
                profile["codice_fiscale"] = self._process_sensitive_field(
                    user.codice_fiscale, 
                    export_request, 
                    "codice_fiscale"
                )
        
        # Billing address if available
        if hasattr(user, 'billing_address'):
            profile["billing_address"] = {
                "address": getattr(user, 'billing_address', None),
                "city": getattr(user, 'billing_city', None),
                "postal_code": getattr(user, 'billing_postal_code', None),
                "country": "IT"
            }
        
        return profile

    async def _collect_query_history(self, user_id: UUID, export_request: DataExportRequest) -> List[Dict[str, Any]]:
        """Collect user query history with date filtering"""
        query_conditions = [QueryHistory.user_id == user_id]
        
        if export_request.date_from:
            query_conditions.append(QueryHistory.timestamp >= export_request.date_from)
        if export_request.date_to:
            query_conditions.append(QueryHistory.timestamp <= export_request.date_to)
        
        stmt = select(QueryHistory).where(and_(*query_conditions)).order_by(desc(QueryHistory.timestamp))
        result = await self.db.execute(stmt)
        queries = result.scalars().all()
        
        return [
            {
                "id": str(q.id),
                "timestamp": q.timestamp.isoformat(),
                "query": self._process_sensitive_field(q.query, export_request, "query_text"),
                "response_cached": q.response_cached,
                "response_time_ms": q.response_time_ms,
                "tokens_used": q.tokens_used,
                "cost_cents": q.cost_cents,
                "model_used": q.model_used,
                "query_type": q.query_type,
                "italian_content": q.italian_content,
                "session_id": q.session_id
            }
            for q in queries
        ]

    async def _collect_document_metadata(self, user_id: UUID, export_request: DataExportRequest) -> List[Dict[str, Any]]:
        """Collect document metadata (no actual content for privacy)"""
        query_conditions = [DocumentAnalysis.user_id == user_id]
        
        if export_request.date_from:
            query_conditions.append(DocumentAnalysis.uploaded_at >= export_request.date_from)
        if export_request.date_to:
            query_conditions.append(DocumentAnalysis.uploaded_at <= export_request.date_to)
        
        stmt = select(DocumentAnalysis).where(and_(*query_conditions)).order_by(desc(DocumentAnalysis.uploaded_at))
        result = await self.db.execute(stmt)
        documents = result.scalars().all()
        
        return [
            {
                "id": str(d.id),
                "uploaded_at": d.uploaded_at.isoformat(),
                "filename": d.filename,
                "file_type": d.file_type,
                "file_size_bytes": d.file_size_bytes,
                "analysis_type": d.analysis_type,
                "processing_time_ms": d.processing_time_ms,
                "analysis_status": d.analysis_status,
                "entities_found": d.entities_found,
                "confidence_score": float(d.confidence_score) if d.confidence_score else None,
                "document_category": d.document_category,
                "tax_year": d.tax_year,
                "analyzed_at": d.analyzed_at.isoformat() if d.analyzed_at else None
            }
            for d in documents
        ]

    async def _collect_tax_calculations(self, user_id: UUID, export_request: DataExportRequest) -> List[Dict[str, Any]]:
        """Collect tax calculation history"""
        query_conditions = [TaxCalculation.user_id == user_id]
        
        if export_request.date_from:
            query_conditions.append(TaxCalculation.timestamp >= export_request.date_from)
        if export_request.date_to:
            query_conditions.append(TaxCalculation.timestamp <= export_request.date_to)
        
        stmt = select(TaxCalculation).where(and_(*query_conditions)).order_by(desc(TaxCalculation.timestamp))
        result = await self.db.execute(stmt)
        calculations = result.scalars().all()
        
        return [
            {
                "id": str(c.id),
                "timestamp": c.timestamp.isoformat(),
                "calculation_type": c.calculation_type,
                "input_amount": float(c.input_amount),
                "result": c.result,
                "parameters": c.parameters,
                "tax_year": c.tax_year,
                "region": c.region,
                "municipality": c.municipality,
                "session_id": c.session_id
            }
            for c in calculations
        ]

    async def _collect_subscription_history(self, user_id: UUID, export_request: DataExportRequest) -> List[Dict[str, Any]]:
        """Collect subscription and billing history"""
        stmt = select(Subscription).options(
            selectinload(Subscription.plan)
        ).where(Subscription.user_id == user_id).order_by(desc(Subscription.created_at))
        
        result = await self.db.execute(stmt)
        subscriptions = result.scalars().all()
        
        return [
            {
                "id": str(s.id),
                "plan_name": s.plan.name if s.plan else None,
                "billing_period": s.plan.billing_period.value if s.plan else None,
                "base_price_eur": float(s.plan.base_price) if s.plan else None,
                "iva_rate": float(s.plan.iva_rate) if s.plan else None,
                "status": s.status.value if hasattr(s.status, 'value') else str(s.status),
                "created_at": s.created_at.isoformat(),
                "current_period_start": s.current_period_start.isoformat() if s.current_period_start else None,
                "current_period_end": s.current_period_end.isoformat() if s.current_period_end else None,
                "trial_end": s.trial_end.isoformat() if s.trial_end else None,
                "canceled_at": s.canceled_at.isoformat() if s.canceled_at else None,
                "ended_at": s.ended_at.isoformat() if s.ended_at else None,
                "is_business": s.is_business,
                "partita_iva": s.partita_iva,
                "invoice_name": s.invoice_name
            }
            for s in subscriptions
        ]

    async def _collect_invoice_data(self, user_id: UUID, export_request: DataExportRequest) -> List[Dict[str, Any]]:
        """Collect invoice data including Italian invoices"""
        # Get user's subscriptions first
        subscription_stmt = select(Subscription.id).where(Subscription.user_id == user_id)
        subscription_result = await self.db.execute(subscription_stmt)
        subscription_ids = [row[0] for row in subscription_result.all()]
        
        if not subscription_ids:
            return []
        
        # Get invoices for user's subscriptions
        stmt = select(Invoice).where(
            Invoice.subscription_id.in_(subscription_ids)
        ).order_by(desc(Invoice.invoice_date))
        
        result = await self.db.execute(stmt)
        invoices = result.scalars().all()
        
        return [
            {
                "id": str(i.id),
                "invoice_number": i.invoice_number,
                "invoice_date": i.invoice_date.isoformat(),
                "due_date": i.due_date.isoformat() if i.due_date else None,
                "subtotal": float(i.subtotal),
                "iva_amount": float(i.iva_amount),
                "total_amount": float(i.total_amount),
                "payment_status": i.payment_status,
                "paid_at": i.paid_at.isoformat() if i.paid_at else None,
                "stripe_invoice_id": i.stripe_invoice_id,
                "has_electronic_invoice": bool(getattr(i, 'fattura_elettronica_xml', None))
            }
            for i in invoices
        ]

    async def _collect_electronic_invoices(self, user_id: UUID, export_request: DataExportRequest) -> List[Dict[str, Any]]:
        """Collect electronic invoice (fattura elettronica) history"""
        stmt = select(ElectronicInvoice).where(
            ElectronicInvoice.user_id == user_id
        ).order_by(desc(ElectronicInvoice.invoice_date))
        
        result = await self.db.execute(stmt)
        electronic_invoices = result.scalars().all()
        
        return [
            {
                "id": str(ei.id),
                "invoice_number": ei.invoice_number,
                "invoice_date": ei.invoice_date.isoformat(),
                "xml_hash": ei.xml_hash,
                "sdi_transmission_id": ei.sdi_transmission_id,
                "sdi_status": ei.sdi_status,
                "created_at": ei.created_at.isoformat(),
                "transmitted_at": ei.transmitted_at.isoformat() if ei.transmitted_at else None,
                "accepted_at": ei.accepted_at.isoformat() if ei.accepted_at else None,
                # Include XML content only if explicitly requested and sensitive data is included
                "xml_content": ei.xml_content if export_request.include_sensitive else None
            }
            for ei in electronic_invoices
        ]

    async def _collect_usage_statistics(self, user_id: UUID, export_request: DataExportRequest) -> Dict[str, Any]:
        """Collect aggregated usage statistics"""
        # Query aggregated statistics
        queries_stmt = select(
            func.count(QueryHistory.id).label('total_queries'),
            func.sum(func.case((QueryHistory.response_cached == True, 1), else_=0)).label('cached_queries'),
            func.avg(QueryHistory.response_time_ms).label('avg_response_time'),
            func.sum(QueryHistory.tokens_used).label('total_tokens'),
            func.sum(QueryHistory.cost_cents).label('total_cost_cents')
        ).where(QueryHistory.user_id == user_id)
        
        if export_request.date_from:
            queries_stmt = queries_stmt.where(QueryHistory.timestamp >= export_request.date_from)
        if export_request.date_to:
            queries_stmt = queries_stmt.where(QueryHistory.timestamp <= export_request.date_to)
        
        queries_result = await self.db.execute(queries_stmt)
        query_stats = queries_result.first()
        
        # Document statistics
        docs_stmt = select(
            func.count(DocumentAnalysis.id).label('total_documents'),
            func.avg(DocumentAnalysis.processing_time_ms).label('avg_processing_time'),
            func.avg(DocumentAnalysis.file_size_bytes).label('avg_file_size')
        ).where(DocumentAnalysis.user_id == user_id)
        
        if export_request.date_from:
            docs_stmt = docs_stmt.where(DocumentAnalysis.uploaded_at >= export_request.date_from)
        if export_request.date_to:
            docs_stmt = docs_stmt.where(DocumentAnalysis.uploaded_at <= export_request.date_to)
        
        docs_result = await self.db.execute(docs_stmt)
        doc_stats = docs_result.first()
        
        # Calculate cache hit rate
        total_queries = query_stats.total_queries or 0
        cached_queries = query_stats.cached_queries or 0
        cache_hit_rate = (cached_queries / total_queries) if total_queries > 0 else 0
        
        return {
            "query_statistics": {
                "total_queries": total_queries,
                "cached_queries": cached_queries,
                "cache_hit_rate": round(cache_hit_rate, 3),
                "average_response_time_ms": round(query_stats.avg_response_time or 0, 1),
                "total_tokens_used": query_stats.total_tokens or 0,
                "total_cost_eur": round((query_stats.total_cost_cents or 0) / 100, 2)
            },
            "document_statistics": {
                "total_documents": doc_stats.total_documents or 0,
                "average_processing_time_ms": round(doc_stats.avg_processing_time or 0, 1),
                "average_file_size_mb": round((doc_stats.avg_file_size or 0) / 1024 / 1024, 2)
            }
        }

    async def _collect_faq_interactions(self, user_id: UUID, export_request: DataExportRequest) -> List[Dict[str, Any]]:
        """Collect FAQ interaction history"""
        query_conditions = [FAQInteraction.user_id == user_id]
        
        if export_request.date_from:
            query_conditions.append(FAQInteraction.viewed_at >= export_request.date_from)
        if export_request.date_to:
            query_conditions.append(FAQInteraction.viewed_at <= export_request.date_to)
        
        stmt = select(FAQInteraction).where(and_(*query_conditions)).order_by(desc(FAQInteraction.viewed_at))
        result = await self.db.execute(stmt)
        interactions = result.scalars().all()
        
        return [
            {
                "id": str(f.id),
                "faq_id": f.faq_id,
                "question": f.question,
                "category": f.category,
                "viewed_at": f.viewed_at.isoformat(),
                "time_spent_seconds": f.time_spent_seconds,
                "helpful_rating": f.helpful_rating,
                "feedback": f.feedback,
                "italian_content": f.italian_content,
                "tax_related": f.tax_related
            }
            for f in interactions
        ]

    async def _collect_knowledge_searches(self, user_id: UUID, export_request: DataExportRequest) -> List[Dict[str, Any]]:
        """Collect knowledge base search history"""
        query_conditions = [KnowledgeBaseSearch.user_id == user_id]
        
        if export_request.date_from:
            query_conditions.append(KnowledgeBaseSearch.searched_at >= export_request.date_from)
        if export_request.date_to:
            query_conditions.append(KnowledgeBaseSearch.searched_at <= export_request.date_to)
        
        stmt = select(KnowledgeBaseSearch).where(and_(*query_conditions)).order_by(desc(KnowledgeBaseSearch.searched_at))
        result = await self.db.execute(stmt)
        searches = result.scalars().all()
        
        return [
            {
                "id": str(s.id),
                "search_query": s.search_query,
                "results_count": s.results_count,
                "clicked_result_id": s.clicked_result_id,
                "clicked_position": s.clicked_position,
                "search_filters": s.search_filters,
                "search_category": s.search_category,
                "searched_at": s.searched_at.isoformat(),
                "italian_query": s.italian_query,
                "regulatory_content": s.regulatory_content
            }
            for s in searches
        ]

    async def _generate_compliance_info(self, export_request: DataExportRequest) -> Dict[str, Any]:
        """Generate compliance and legal information"""
        return {
            "gdpr_compliance": {
                "legal_basis": "GDPR Article 20 - Right to data portability",
                "data_controller": {
                    "name": "PratikoAI SRL",
                    "address": "Via dell'Innovazione 123, 00100 Roma, IT",
                    "contact": "privacy@pratikoai.com",
                    "country": "IT"
                },
                "data_processor": "PratikoAI SRL",
                "jurisdiction": "IT",
                "italian_laws": ["Codice Privacy (D.Lgs. 196/2003)", "GDPR (Regolamento UE 2016/679)"]
            },
            "export_details": {
                "export_generated": datetime.utcnow().isoformat(),
                "retention_period": "24 ore",
                "download_expiry": export_request.expires_at.isoformat(),
                "max_downloads": export_request.max_downloads,
                "includes_personal_data": export_request.include_sensitive,
                "includes_financial_data": export_request.include_invoices or export_request.include_subscriptions,
                "anonymization_applied": export_request.anonymize_pii
            },
            "data_categories_included": {
                category: getattr(export_request, f"include_{category}")
                for category in [
                    "profile", "queries", "documents", "calculations", 
                    "subscriptions", "invoices", "usage_stats", 
                    "faq_interactions", "knowledge_searches"
                ]
            },
            "italian_specific": {
                "fatture_elettroniche": export_request.include_fatture,
                "f24_forms": export_request.include_f24,
                "dichiarazioni": export_request.include_dichiarazioni,
                "codice_fiscale_masked": export_request.mask_codice_fiscale
            }
        }

    # Helper methods continue in the next part...
    
    def _process_sensitive_field(self, value: Any, export_request: DataExportRequest, field_type: str) -> Any:
        """Process sensitive field based on privacy settings"""
        if not value:
            return value
        
        # If anonymization is requested, mask the value
        if export_request.anonymize_pii:
            if field_type == "email":
                return self._mask_email(str(value))
            elif field_type == "name":
                return "***"
            elif field_type == "codice_fiscale":
                return self._mask_codice_fiscale(str(value))
            elif field_type == "partita_iva":
                return "***" + str(value)[-4:] if len(str(value)) > 4 else "***"
            elif field_type == "query_text":
                return str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
        
        # Decrypt if needed
        if hasattr(value, 'startswith') and self.encryption.is_encrypted(value):
            return self.encryption.decrypt(value)
        
        return value
    
    def _mask_email(self, email: str) -> str:
        """Mask email address for privacy"""
        if "@" not in email:
            return "***"
        
        local, domain = email.split("@", 1)
        if len(local) <= 2:
            masked_local = "***"
        else:
            masked_local = local[0] + "***" + local[-1]
        
        return f"{masked_local}@{domain}"
    
    def _mask_codice_fiscale(self, codice_fiscale: str) -> str:
        """Mask Codice Fiscale showing only last 4 characters"""
        if len(codice_fiscale) != 16:
            return "***"
        
        return "************" + codice_fiscale[-4:]

    async def _count_recent_exports(self, user_id: UUID, hours: int = 24) -> int:
        """Count recent export requests for rate limiting"""
        since = datetime.utcnow() - timedelta(hours=hours)
        
        stmt = select(func.count(DataExportRequest.id)).where(
            and_(
                DataExportRequest.user_id == user_id,
                DataExportRequest.requested_at >= since
            )
        )
        
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def _get_user(self, user_id: UUID) -> Optional[User]:
        """Get user by ID"""
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_export_request(self, export_id: UUID) -> Optional[DataExportRequest]:
        """Get export request by ID"""
        stmt = select(DataExportRequest).where(DataExportRequest.id == export_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _create_audit_log(
        self, 
        export_request_id: UUID, 
        user_id: UUID, 
        activity_type: str, 
        activity_data: Optional[Dict] = None
    ) -> None:
        """Create audit log entry"""
        audit_log = ExportAuditLog(
            export_request_id=export_request_id,
            user_id=user_id,
            activity_type=activity_type,
            activity_data=activity_data or {}
        )
        
        self.db.add(audit_log)
        await self.db.commit()

    async def _queue_export_job(self, export_id: UUID) -> None:
        """Queue export for background processing"""
        # Add to Redis queue for background processing
        await self.redis.lpush("export_queue", str(export_id))
        logger.info(f"Queued export {export_id} for processing")

    async def _generate_export_files(
        self, 
        user_data: Dict[str, Any], 
        export_request: DataExportRequest
    ) -> Dict[str, Any]:
        """Generate export files in requested formats"""
        generator = ExportFileGenerator()
        files = {}
        
        if export_request.format in [ExportFormat.JSON, ExportFormat.BOTH]:
            json_content = await generator.generate_json_export(user_data)
            files["dati_completi.json"] = json_content
        
        if export_request.format in [ExportFormat.CSV, ExportFormat.BOTH]:
            csv_files = await generator.generate_csv_exports(user_data)
            files.update(csv_files)
        
        # Add manifest file
        manifest = await generator.generate_manifest(user_data, export_request)
        files["LEGGIMI.txt"] = manifest.encode('utf-8')
        
        return files

    async def _create_final_export_file(
        self, 
        files: Dict[str, bytes], 
        export_request: DataExportRequest
    ) -> Dict[str, Any]:
        """Create final export file (ZIP if multiple files or large size)"""
        total_size = sum(len(content) for content in files.values())
        
        # Create ZIP if multiple files or size > 10MB  
        if len(files) > 1 or total_size > 10 * 1024 * 1024:
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for filename, content in files.items():
                    zip_file.writestr(filename, content)
            
            zip_content = zip_buffer.getvalue()
            return {
                "filename": f"export_dati_{export_request.user_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.zip",
                "content": zip_content,
                "content_type": "application/zip"
            }
        else:
            # Single file
            filename, content = next(iter(files.items()))
            return {
                "filename": filename,
                "content": content,
                "content_type": "application/json" if filename.endswith('.json') else "text/csv"
            }

    async def _upload_export_file(
        self, 
        file_data: Dict[str, Any], 
        export_request: DataExportRequest
    ) -> str:
        """Upload export file to secure storage and return download URL"""
        try:
            # Generate secure filename
            secure_filename = f"exports/{export_request.user_id}/{export_request.id}/{file_data['filename']}"
            
            # Upload to S3 with expiration
            self.s3_client.put_object(
                Bucket=settings.EXPORT_S3_BUCKET,
                Key=secure_filename,
                Body=file_data['content'],
                ContentType=file_data['content_type'],
                ServerSideEncryption='AES256',
                Metadata={
                    'user_id': str(export_request.user_id),
                    'export_id': str(export_request.id),
                    'created_at': datetime.utcnow().isoformat()
                }
            )
            
            # Generate presigned URL for download (24 hour expiry)
            download_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': settings.EXPORT_S3_BUCKET,
                    'Key': secure_filename
                },
                ExpiresIn=24 * 3600  # 24 hours
            )
            
            return download_url
            
        except ClientError as e:
            logger.error(f"Error uploading export file: {e}")
            raise

    async def _send_export_ready_email(self, export_request: DataExportRequest) -> None:
        """Send email notification when export is ready"""
        user = await self._get_user(export_request.user_id)
        if not user:
            return
        
        # Calculate file size in MB
        file_size_mb = round(export_request.file_size_bytes / 1024 / 1024, 2) if export_request.file_size_bytes else 0
        
        # Format expiry date in Italian
        expiry_date = export_request.expires_at.strftime("%d/%m/%Y alle %H:%M")
        
        await self.email_service.send_email(
            to_email=user.email,
            subject="🎯 Export dati PratikoAI pronto per il download",
            template="data_export_ready",
            context={
                "user_name": user.full_name or "Utente",
                "export_format": export_request.format.value.upper(),
                "file_size_mb": file_size_mb,
                "expiry_date": expiry_date,
                "download_link": f"{settings.FRONTEND_URL}/export/download/{export_request.id}",
                "processing_time": export_request.processing_time_seconds,
                "data_categories": {
                    "profile": export_request.include_profile,
                    "queries": export_request.include_queries,
                    "documents": export_request.include_documents,
                    "calculations": export_request.include_calculations,
                    "subscriptions": export_request.include_subscriptions,
                    "invoices": export_request.include_invoices,
                    "fatture": export_request.include_fatture
                }
            }
        )

    async def _send_export_error_email(self, export_request: DataExportRequest, error_message: str) -> None:
        """Send email notification when export fails"""
        user = await self._get_user(export_request.user_id)
        if not user:
            return
        
        await self.email_service.send_email(
            to_email=user.email,
            subject="❌ Errore nell'export dati PratikoAI",
            template="data_export_error",
            context={
                "user_name": user.full_name or "Utente",
                "export_id": str(export_request.id),
                "error_message": error_message,
                "can_retry": export_request.can_retry(),
                "support_email": "support@pratikoai.com"
            }
        )


class ExportProgressTracker:
    """Track and report export progress for user feedback"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def update_progress(
        self,
        export_id: str,
        step: str,
        current: int,
        total: int
    ) -> None:
        """Update export progress in Redis"""
        key = f"export_progress:{export_id}"
        
        progress_data = {
            "step": step,
            "current": current,
            "total": total,
            "percentage": round((current / total) * 100, 1),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        await self.redis.setex(
            key,
            3600,  # 1 hour TTL
            json.dumps(progress_data)
        )
    
    async def get_progress(self, export_id: str) -> Dict[str, Any]:
        """Get current export progress"""
        key = f"export_progress:{export_id}"
        data = await self.redis.get(key)
        
        if data:
            return json.loads(data)
        
        return {
            "step": "In coda",
            "percentage": 0,
            "updated_at": datetime.utcnow().isoformat()
        }