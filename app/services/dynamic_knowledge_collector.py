"""
Dynamic Knowledge Collection System (DKCS) - Main Coordinator.

This is the main service that coordinates RSS feed monitoring, document processing,
and knowledge base integration for Italian regulatory sources.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_

from app.core.logging import logger
from app.services.rss_feed_monitor import RSSFeedMonitor, FeedHealthMonitor
from app.services.document_processor import DocumentProcessor
from app.services.knowledge_integrator import KnowledgeIntegrator
from app.models.regulatory_documents import RegulatoryDocument, FeedStatus, DocumentProcessingLog


class DynamicKnowledgeCollector:
    """Main coordinator for the Dynamic Knowledge Collection System."""
    
    def __init__(self, db_session: AsyncSession):
        """Initialize the dynamic knowledge collector.
        
        Args:
            db_session: Database session for operations
        """
        self.db = db_session
        self.rss_monitor = None
        self.document_processor = None
        self.knowledge_integrator = KnowledgeIntegrator(db_session)
        
        # Processing statistics
        self.stats = {
            'feeds_processed': 0,
            'documents_found': 0,
            'new_documents': 0,
            'updated_documents': 0,
            'errors': 0,
            'processing_time_seconds': 0
        }
    
    async def collect_and_process_updates(self) -> List[Dict[str, Any]]:
        """Main entry point for collecting and processing regulatory updates.
        
        Returns:
            List of processing results for each source
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            logger.info("dynamic_knowledge_collection_started", start_time=start_time)
            
            # Initialize services with async context managers
            async with RSSFeedMonitor() as rss_monitor, \
                      DocumentProcessor() as document_processor:
                
                self.rss_monitor = rss_monitor
                self.document_processor = document_processor
                
                # Get all Italian RSS feeds
                feeds = await rss_monitor.get_all_italian_feeds()
                
                # Process feeds in parallel
                results = await self.process_all_feeds_parallel(feeds)
                
                # Calculate total processing time
                processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                self.stats['processing_time_seconds'] = processing_time
                
                # Log summary
                logger.info(
                    "dynamic_knowledge_collection_completed",
                    processing_time_seconds=processing_time,
                    feeds_processed=self.stats['feeds_processed'],
                    new_documents=self.stats['new_documents'],
                    errors=self.stats['errors']
                )
                
                return results
                
        except Exception as e:
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            self.stats['processing_time_seconds'] = processing_time
            self.stats['errors'] += 1
            
            logger.error(
                "dynamic_knowledge_collection_failed",
                processing_time_seconds=processing_time,
                error=str(e),
                exc_info=True
            )
            
            return [{
                'success': False,
                'error': str(e),
                'source': 'system',
                'processing_time_seconds': processing_time
            }]
    
    async def process_all_feeds_parallel(
        self, 
        feeds: Dict[str, str],
        max_concurrent: int = 5
    ) -> List[Dict[str, Any]]:
        """Process multiple RSS feeds concurrently.
        
        Args:
            feeds: Dictionary mapping feed names to URLs
            max_concurrent: Maximum concurrent processing tasks
            
        Returns:
            List of processing results
        """
        results = []
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_feed_with_semaphore(feed_name: str, feed_url: str) -> Dict[str, Any]:
            async with semaphore:
                return await self.process_single_feed(feed_name, feed_url)
        
        # Create tasks for concurrent processing
        tasks = [
            asyncio.create_task(process_feed_with_semaphore(name, url))
            for name, url in feeds.items()
        ]
        
        # Wait for all tasks to complete
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle any exceptions in results
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    feed_name = list(feeds.keys())[i]
                    logger.error(
                        "feed_processing_exception",
                        feed_name=feed_name,
                        error=str(result),
                        exc_info=True
                    )
                    processed_results.append({
                        'success': False,
                        'error': str(result),
                        'source': feed_name,
                        'new_documents': []
                    })
                else:
                    processed_results.append(result)
            
            # Update statistics
            self.stats['feeds_processed'] = len(processed_results)
            self.stats['new_documents'] = sum(
                len(r.get('new_documents', [])) for r in processed_results if r.get('success')
            )
            self.stats['errors'] = sum(
                1 for r in processed_results if not r.get('success')
            )
            
            return processed_results
            
        except Exception as e:
            logger.error(
                "parallel_feed_processing_failed",
                error=str(e),
                exc_info=True
            )
            return []
    
    async def process_single_feed(self, feed_name: str, feed_url: str) -> Dict[str, Any]:
        """Process a single RSS feed.
        
        Args:
            feed_name: Name of the feed
            feed_url: URL of the RSS feed
            
        Returns:
            Processing results for this feed
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            logger.info(
                "processing_single_feed",
                feed_name=feed_name,
                feed_url=feed_url
            )
            
            # Parse RSS feed
            feed_items = await self.rss_monitor.parse_feed_with_error_handling(feed_url)
            
            if not feed_items:
                logger.warning("no_feed_items_found", feed_name=feed_name)
                return {
                    'success': True,
                    'source': feed_name,
                    'new_documents': [],
                    'message': 'No items found in feed',
                    'processing_time_seconds': (datetime.now(timezone.utc) - start_time).total_seconds()
                }
            
            # Filter for new documents
            new_documents = await self.filter_new_documents(feed_items)
            
            if not new_documents:
                logger.info("no_new_documents", feed_name=feed_name, total_items=len(feed_items))
                return {
                    'success': True,
                    'source': feed_name,
                    'new_documents': [],
                    'message': f'No new documents from {len(feed_items)} feed items',
                    'processing_time_seconds': (datetime.now(timezone.utc) - start_time).total_seconds()
                }
            
            # Process new documents
            processed_documents = await self.process_document_batch(new_documents)
            
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            logger.info(
                "single_feed_processing_completed",
                feed_name=feed_name,
                new_documents_count=len(new_documents),
                processed_count=len(processed_documents),
                processing_time_seconds=processing_time
            )
            
            return {
                'success': True,
                'source': feed_name,
                'new_documents': processed_documents,
                'feed_items_total': len(feed_items),
                'new_documents_count': len(new_documents),
                'processing_time_seconds': processing_time
            }
            
        except Exception as e:
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            logger.error(
                "single_feed_processing_failed",
                feed_name=feed_name,
                feed_url=feed_url,
                processing_time_seconds=processing_time,
                error=str(e),
                exc_info=True
            )
            
            return {
                'success': False,
                'source': feed_name,
                'error': str(e),
                'new_documents': [],
                'processing_time_seconds': processing_time
            }
    
    async def filter_new_documents(self, feed_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter feed items to find only new documents.
        
        Args:
            feed_items: List of parsed feed items
            
        Returns:
            List of new documents not yet in database
        """
        new_documents = []
        
        for item in feed_items:
            url = item.get('url', '')
            if not url:
                continue
            
            # Check if document already exists
            query = select(RegulatoryDocument.id).where(
                RegulatoryDocument.url == url
            )
            result = await self.db.execute(query)
            existing_doc = result.scalar_one_or_none()
            
            if not existing_doc:
                new_documents.append(item)
        
        return new_documents
    
    async def process_document_batch(
        self, 
        documents: List[Dict[str, Any]],
        max_concurrent: int = 3
    ) -> List[Dict[str, Any]]:
        """Process a batch of documents (extract content and integrate into knowledge base).
        
        Args:
            documents: List of document metadata from RSS feeds
            max_concurrent: Maximum concurrent document processing
            
        Returns:
            List of processing results
        """
        results = []
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_document_with_semaphore(doc: Dict[str, Any]) -> Dict[str, Any]:
            async with semaphore:
                return await self.process_single_document(doc)
        
        # Create tasks for concurrent processing
        tasks = [
            asyncio.create_task(process_document_with_semaphore(doc))
            for doc in documents
        ]
        
        # Wait for all tasks to complete
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle any exceptions in results
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    doc_url = documents[i].get('url', 'unknown')
                    logger.error(
                        "document_processing_exception",
                        document_url=doc_url,
                        error=str(result),
                        exc_info=True
                    )
                    processed_results.append({
                        'success': False,
                        'url': doc_url,
                        'error': str(result)
                    })
                else:
                    processed_results.append(result)
            
            return processed_results
            
        except Exception as e:
            logger.error(
                "document_batch_processing_failed",
                error=str(e),
                exc_info=True
            )
            return []
    
    async def process_single_document(self, document_meta: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single document (extract content and integrate into knowledge base).
        
        Args:
            document_meta: Document metadata from RSS feed
            
        Returns:
            Processing result
        """
        start_time = datetime.now(timezone.utc)
        url = document_meta.get('url', '')
        
        try:
            # Log processing start
            await self._log_processing_start(document_meta)
            
            # Extract content from document
            processed_doc = await self.document_processor.process_document(url)
            
            if not processed_doc['success'] or not processed_doc['content']:
                logger.warning(
                    "document_content_extraction_failed",
                    url=url,
                    error=processed_doc.get('processing_stats', {}).get('error', 'No content extracted')
                )
                
                await self._log_processing_error(document_meta, "Content extraction failed")
                
                return {
                    'success': False,
                    'url': url,
                    'error': 'Content extraction failed',
                    'processing_time_seconds': (datetime.now(timezone.utc) - start_time).total_seconds()
                }
            
            # Combine metadata with extracted content
            document_data = {
                **document_meta,
                'content': processed_doc['content'],
                'content_hash': processed_doc['content_hash'],
                'document_type': processed_doc['document_type'],
                'processing_stats': processed_doc['processing_stats']
            }
            
            # Integrate into knowledge base
            integration_result = await self.knowledge_integrator.update_knowledge_base(document_data)
            
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            if integration_result['success']:
                await self._log_processing_success(document_meta, processing_time)
                
                logger.info(
                    "document_processed_successfully",
                    url=url,
                    action=integration_result['action'],
                    processing_time_seconds=processing_time
                )
                
                return {
                    'success': True,
                    'url': url,
                    'action': integration_result['action'],
                    'document_id': integration_result.get('document_id'),
                    'processing_time_seconds': processing_time
                }
            else:
                await self._log_processing_error(document_meta, integration_result.get('error', 'Integration failed'))
                
                return {
                    'success': False,
                    'url': url,
                    'error': integration_result.get('error', 'Integration failed'),
                    'processing_time_seconds': processing_time
                }
                
        except Exception as e:
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            await self._log_processing_error(document_meta, str(e))
            
            logger.error(
                "document_processing_failed",
                url=url,
                processing_time_seconds=processing_time,
                error=str(e),
                exc_info=True
            )
            
            return {
                'success': False,
                'url': url,
                'error': str(e),
                'processing_time_seconds': processing_time
            }
    
    async def collect_with_resilience(self) -> List[Dict[str, Any]]:
        """Collect knowledge with resilience to feed failures.
        
        Returns:
            List of processing results with success/failure status
        """
        try:
            # This is the same as collect_and_process_updates but ensures
            # that partial failures don't stop the entire process
            return await self.collect_and_process_updates()
        except Exception as e:
            logger.error(
                "resilient_collection_failed",
                error=str(e),
                exc_info=True
            )
            return [{
                'success': False,
                'error': str(e),
                'source': 'system_resilience'
            }]
    
    async def collect_from_specific_sources(self, sources: List[str]) -> List[Dict[str, Any]]:
        """Collect from specific sources only.
        
        Args:
            sources: List of source names to collect from
            
        Returns:
            List of processing results
        """
        try:
            async with RSSFeedMonitor() as rss_monitor, \
                      DocumentProcessor() as document_processor:
                
                self.rss_monitor = rss_monitor
                self.document_processor = document_processor
                
                # Get all feeds and filter to requested sources
                all_feeds = await rss_monitor.get_all_italian_feeds()
                selected_feeds = {
                    name: url for name, url in all_feeds.items()
                    if any(source in name for source in sources)
                }
                
                if not selected_feeds:
                    logger.warning(
                        "no_matching_sources_found",
                        requested_sources=sources,
                        available_feeds=list(all_feeds.keys())
                    )
                    return []
                
                # Process selected feeds
                results = await self.process_all_feeds_parallel(selected_feeds)
                
                logger.info(
                    "specific_sources_collection_completed",
                    requested_sources=sources,
                    processed_feeds=list(selected_feeds.keys()),
                    results_count=len(results)
                )
                
                return results
                
        except Exception as e:
            logger.error(
                "specific_sources_collection_failed",
                sources=sources,
                error=str(e),
                exc_info=True
            )
            return [{
                'success': False,
                'error': str(e),
                'source': 'specific_collection'
            }]
    
    async def cleanup_old_feed_history(self, retention_days: int = 90) -> int:
        """Clean up old feed status history.
        
        Args:
            retention_days: Number of days to retain history
            
        Returns:
            Number of records deleted
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
            
            # Delete old feed status records
            delete_query = delete(FeedStatus).where(
                FeedStatus.created_at < cutoff_date
            )
            
            result = await self.db.execute(delete_query)
            deleted_count = result.rowcount
            
            await self.db.commit()
            
            logger.info(
                "feed_history_cleanup_completed",
                retention_days=retention_days,
                deleted_records=deleted_count
            )
            
            return deleted_count
            
        except Exception as e:
            await self.db.rollback()
            logger.error(
                "feed_history_cleanup_failed",
                retention_days=retention_days,
                error=str(e),
                exc_info=True
            )
            return 0
    
    async def cleanup_old_processing_logs(self, retention_days: int = 30) -> int:
        """Clean up old processing logs.
        
        Args:
            retention_days: Number of days to retain logs
            
        Returns:
            Number of records deleted
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
            
            # Delete old processing log records
            delete_query = delete(DocumentProcessingLog).where(
                DocumentProcessingLog.created_at < cutoff_date
            )
            
            result = await self.db.execute(delete_query)
            deleted_count = result.rowcount
            
            await self.db.commit()
            
            logger.info(
                "processing_logs_cleanup_completed",
                retention_days=retention_days,
                deleted_records=deleted_count
            )
            
            return deleted_count
            
        except Exception as e:
            await self.db.rollback()
            logger.error(
                "processing_logs_cleanup_failed",
                retention_days=retention_days,
                error=str(e),
                exc_info=True
            )
            return 0
    
    async def archive_old_superseded_documents(self, retention_days: int = 365) -> int:
        """Archive old superseded documents.
        
        Args:
            retention_days: Number of days to keep superseded documents
            
        Returns:
            Number of documents archived
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
            
            # Find old superseded documents
            query = select(RegulatoryDocument).where(
                and_(
                    RegulatoryDocument.status == 'superseded',
                    RegulatoryDocument.updated_at < cutoff_date
                )
            )
            
            result = await self.db.execute(query)
            old_docs = result.scalars().all()
            
            # Archive them
            archived_count = 0
            for doc in old_docs:
                doc.status = 'archived'
                doc.archived_at = datetime.now(timezone.utc)
                doc.archive_reason = f'Auto-archived after {retention_days} days'
                archived_count += 1
            
            await self.db.commit()
            
            logger.info(
                "superseded_documents_archival_completed",
                retention_days=retention_days,
                archived_documents=archived_count
            )
            
            return archived_count
            
        except Exception as e:
            await self.db.rollback()
            logger.error(
                "superseded_documents_archival_failed",
                retention_days=retention_days,
                error=str(e),
                exc_info=True
            )
            return 0
    
    async def _log_processing_start(self, document_meta: Dict[str, Any]) -> None:
        """Log the start of document processing.
        
        Args:
            document_meta: Document metadata
        """
        try:
            log_entry = DocumentProcessingLog(
                document_url=document_meta.get('url', ''),
                operation='create',
                status='processing',
                triggered_by='scheduler',
                feed_url=document_meta.get('feed_url', '')
            )
            
            self.db.add(log_entry)
            await self.db.commit()
            
        except Exception as e:
            logger.warning(
                "processing_log_creation_failed",
                url=document_meta.get('url', ''),
                error=str(e)
            )
    
    async def _log_processing_success(
        self, 
        document_meta: Dict[str, Any], 
        processing_time: float
    ) -> None:
        """Log successful document processing.
        
        Args:
            document_meta: Document metadata
            processing_time: Processing time in seconds
        """
        try:
            log_entry = DocumentProcessingLog(
                document_url=document_meta.get('url', ''),
                operation='create',
                status='success',
                processing_time_ms=processing_time * 1000,
                triggered_by='scheduler',
                feed_url=document_meta.get('feed_url', '')
            )
            
            self.db.add(log_entry)
            await self.db.commit()
            
        except Exception as e:
            logger.warning(
                "processing_success_log_failed",
                url=document_meta.get('url', ''),
                error=str(e)
            )
    
    async def _log_processing_error(
        self, 
        document_meta: Dict[str, Any], 
        error_message: str
    ) -> None:
        """Log processing error.
        
        Args:
            document_meta: Document metadata
            error_message: Error message
        """
        try:
            log_entry = DocumentProcessingLog(
                document_url=document_meta.get('url', ''),
                operation='create',
                status='failed',
                error_message=error_message,
                triggered_by='scheduler',
                feed_url=document_meta.get('feed_url', '')
            )
            
            self.db.add(log_entry)
            await self.db.commit()
            
        except Exception as e:
            logger.warning(
                "processing_error_log_failed",
                url=document_meta.get('url', ''),
                error=str(e)
            )
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get current processing statistics.
        
        Returns:
            Dictionary with processing statistics
        """
        return {
            **self.stats,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }


# Convenience function for scheduled task integration
async def collect_italian_documents_task() -> None:
    """Scheduled task function for Italian document collection.
    
    This function is called by the scheduler service every 4 hours.
    """
    db_session = None
    try:
        from app.services.database import database_service
        
        db_session = database_service.get_session_maker()
        collector = DynamicKnowledgeCollector(db_session)
        results = await collector.collect_and_process_updates()
        
        # Log summary for scheduled task
        total_new_docs = sum(len(r.get('new_documents', [])) for r in results if r.get('success'))
        successful_sources = sum(1 for r in results if r.get('success'))
        
        logger.info(
            "scheduled_italian_documents_collection_completed",
            total_sources=len(results),
            successful_sources=successful_sources,
            total_new_documents=total_new_docs
        )
        
    except Exception as e:
        logger.error(
            "scheduled_italian_documents_collection_failed",
            error=str(e),
            exc_info=True
        )
    finally:
        if db_session:
            db_session.close()