"""
GDPR Compliant Document Cleanup Service.

This service handles automatic cleanup of uploaded documents according to GDPR
requirements, including data retention policies, user deletion requests, and
automated purging of expired documents.
"""

import asyncio
import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
import logging

from sqlalchemy import select, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.models.document_simple import Document, DocumentStatus
from app.models.user import User
from app.services.secure_document_storage import SecureDocumentStorage


class GDPRDocumentCleanup:
  """Service for GDPR compliant document cleanup and data retention management"""
  
  def __init__(self, db: AsyncSession):
    self.db = db
    self.settings = get_settings()
    self.storage = SecureDocumentStorage()
    self.logger = logging.getLogger(__name__)
    
    # GDPR retention periods (configurable via environment)
    self.default_retention_days = self.settings.PRIVACY_DATA_RETENTION_DAYS
    self.processing_timeout_hours = 24  # Failed processing documents cleanup
    self.temp_file_timeout_hours = 2    # Temporary files cleanup
    
  async def cleanup_expired_documents(self) -> Dict[str, Any]:
    """
    Clean up documents that have exceeded their retention period.
    
    Returns:
      Dictionary with cleanup statistics
    """
    self.logger.info("Starting GDPR document cleanup process")
    
    cleanup_stats = {
      'expired_documents': 0,
      'failed_processing': 0,
      'temp_files_cleaned': 0,
      'storage_freed_mb': 0,
      'errors': []
    }
    
    try:
      # 1. Clean up expired documents
      expired_stats = await self._cleanup_retention_expired_documents()
      cleanup_stats.update(expired_stats)
      
      # 2. Clean up failed processing documents
      failed_stats = await self._cleanup_failed_processing_documents()
      cleanup_stats['failed_processing'] = failed_stats['cleaned_count']
      cleanup_stats['storage_freed_mb'] += failed_stats['storage_freed_mb']
      
      # 3. Clean up temporary files
      temp_stats = await self._cleanup_temporary_files()
      cleanup_stats['temp_files_cleaned'] = temp_stats['cleaned_count']
      cleanup_stats['storage_freed_mb'] += temp_stats['storage_freed_mb']
      
      # 4. Optimize storage
      await self._optimize_storage()
      
      self.logger.info(f"GDPR cleanup completed: {cleanup_stats}")
      
    except Exception as e:
      error_msg = f"GDPR cleanup failed: {e}"
      self.logger.error(error_msg)
      cleanup_stats['errors'].append(error_msg)
    
    return cleanup_stats
  
  async def _cleanup_retention_expired_documents(self) -> Dict[str, Any]:
    """Clean up documents that have exceeded retention period"""
    cutoff_date = datetime.utcnow() - timedelta(days=self.default_retention_days)
    
    # Find expired documents
    query = select(Document).where(
      and_(
        Document.created_at < cutoff_date,
        Document.status != DocumentStatus.DELETED
      )
    )
    
    result = await self.db.execute(query)
    expired_documents = result.scalars().all()
    
    cleaned_count = 0
    storage_freed_mb = 0
    errors = []
    
    for document in expired_documents:
      try:
        # Delete physical files
        file_size_mb = await self._delete_document_files(document)
        storage_freed_mb += file_size_mb
        
        # Update document status
        document.status = DocumentStatus.DELETED
        document.deleted_at = datetime.utcnow()
        document.deletion_reason = "GDPR_RETENTION_EXPIRED"
        
        cleaned_count += 1
        
        self.logger.info(f"Deleted expired document {document.id} (age: {(datetime.utcnow() - document.created_at).days} days)")
        
      except Exception as e:
        error_msg = f"Failed to delete document {document.id}: {e}"
        self.logger.error(error_msg)
        errors.append(error_msg)
    
    await self.db.commit()
    
    return {
      'expired_documents': cleaned_count,
      'storage_freed_mb': storage_freed_mb,
      'errors': errors
    }
  
  async def _cleanup_failed_processing_documents(self) -> Dict[str, Any]:
    """Clean up documents that failed processing and are stale"""
    cutoff_date = datetime.utcnow() - timedelta(hours=self.processing_timeout_hours)
    
    # Find failed processing documents
    query = select(Document).where(
      and_(
        Document.status == DocumentStatus.FAILED,
        Document.created_at < cutoff_date
      )
    )
    
    result = await self.db.execute(query)
    failed_documents = result.scalars().all()
    
    cleaned_count = 0
    storage_freed_mb = 0
    
    for document in failed_documents:
      try:
        file_size_mb = await self._delete_document_files(document)
        storage_freed_mb += file_size_mb
        
        document.status = DocumentStatus.DELETED
        document.deleted_at = datetime.utcnow()
        document.deletion_reason = "FAILED_PROCESSING_TIMEOUT"
        
        cleaned_count += 1
        
      except Exception as e:
        self.logger.error(f"Failed to clean up failed document {document.id}: {e}")
    
    await self.db.commit()
    
    return {
      'cleaned_count': cleaned_count,
      'storage_freed_mb': storage_freed_mb
    }
  
  async def _cleanup_temporary_files(self) -> Dict[str, Any]:
    """Clean up temporary files that are no longer needed"""
    temp_dirs = [
      Path(self.storage.storage_path) / "temp",
      Path(self.storage.storage_path) / "processing",
      Path("/tmp/pratiko_uploads"),  # System temp directory
    ]
    
    cleaned_count = 0
    storage_freed_mb = 0
    cutoff_time = datetime.utcnow() - timedelta(hours=self.temp_file_timeout_hours)
    
    for temp_dir in temp_dirs:
      if not temp_dir.exists():
        continue
        
      try:
        for file_path in temp_dir.rglob("*"):
          if file_path.is_file():
            # Check file age
            file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            
            if file_mtime < cutoff_time:
              file_size_mb = file_path.stat().st_size / (1024 * 1024)
              file_path.unlink()
              storage_freed_mb += file_size_mb
              cleaned_count += 1
              
        # Remove empty directories
        for dir_path in temp_dir.rglob("*"):
          if dir_path.is_dir() and not any(dir_path.iterdir()):
            dir_path.rmdir()
            
      except Exception as e:
        self.logger.error(f"Failed to clean temp directory {temp_dir}: {e}")
    
    return {
      'cleaned_count': cleaned_count,
      'storage_freed_mb': storage_freed_mb
    }
  
  async def delete_user_documents(self, user_id: UUID, reason: str = "USER_REQUEST") -> Dict[str, Any]:
    """
    Delete all documents for a specific user (GDPR Article 17 - Right to erasure).
    
    Args:
      user_id: User ID to delete documents for
      reason: Reason for deletion
      
    Returns:
      Dictionary with deletion statistics
    """
    self.logger.info(f"Starting user document deletion for user {user_id}, reason: {reason}")
    
    # Find all documents for the user
    query = select(Document).where(
      and_(
        Document.user_id == user_id,
        Document.status != DocumentStatus.DELETED
      )
    )
    
    result = await self.db.execute(query)
    user_documents = result.scalars().all()
    
    deleted_count = 0
    storage_freed_mb = 0
    errors = []
    
    for document in user_documents:
      try:
        # Delete physical files
        file_size_mb = await self._delete_document_files(document)
        storage_freed_mb += file_size_mb
        
        # Update document status
        document.status = DocumentStatus.DELETED
        document.deleted_at = datetime.utcnow()
        document.deletion_reason = reason
        
        deleted_count += 1
        
      except Exception as e:
        error_msg = f"Failed to delete user document {document.id}: {e}"
        self.logger.error(error_msg)
        errors.append(error_msg)
    
    await self.db.commit()
    
    stats = {
      'user_id': str(user_id),
      'deleted_documents': deleted_count,
      'storage_freed_mb': storage_freed_mb,
      'deletion_reason': reason,
      'errors': errors
    }
    
    self.logger.info(f"User document deletion completed: {stats}")
    return stats
  
  async def _delete_document_files(self, document: Document) -> float:
    """
    Delete physical files for a document.
    
    Args:
      document: Document model instance
      
    Returns:
      Size of deleted files in MB
    """
    storage_freed_mb = 0.0
    
    if document.storage_path:
      try:
        file_path = Path(document.storage_path)
        if file_path.exists():
          storage_freed_mb = file_path.stat().st_size / (1024 * 1024)
          
          # Secure deletion (overwrite before delete)
          await self._secure_delete_file(file_path)
          
          # Delete any related files (thumbnails, previews, etc.)
          await self._delete_related_files(document)
          
      except Exception as e:
        self.logger.error(f"Failed to delete file {document.storage_path}: {e}")
        raise
    
    return storage_freed_mb
  
  async def _secure_delete_file(self, file_path: Path) -> None:
    """
    Securely delete a file by overwriting it before deletion.
    
    Args:
      file_path: Path to file to delete
    """
    if not file_path.exists():
      return
    
    file_size = file_path.stat().st_size
    
    # Overwrite file with random data (GDPR secure deletion)
    with open(file_path, 'wb') as f:
      # Write random bytes
      import secrets
      chunk_size = 8192
      for _ in range(0, file_size, chunk_size):
        write_size = min(chunk_size, file_size - f.tell())
        f.write(secrets.token_bytes(write_size))
    
    # Delete the file
    file_path.unlink()
  
  async def _delete_related_files(self, document: Document) -> None:
    """Delete any related files (thumbnails, previews, etc.)"""
    base_path = Path(document.storage_path).parent
    document_name = Path(document.storage_path).stem
    
    # Look for related files with the same base name
    related_patterns = [
      f"{document_name}_thumb.*",
      f"{document_name}_preview.*",
      f"{document_name}_processed.*",
    ]
    
    for pattern in related_patterns:
      for related_file in base_path.glob(pattern):
        try:
          await self._secure_delete_file(related_file)
        except Exception as e:
          self.logger.error(f"Failed to delete related file {related_file}: {e}")
  
  async def _optimize_storage(self) -> None:
    """Optimize storage by removing empty directories"""
    storage_path = Path(self.storage.storage_path)
    
    # Remove empty directories
    for dir_path in storage_path.rglob("*"):
      if dir_path.is_dir():
        try:
          if not any(dir_path.iterdir()):
            dir_path.rmdir()
        except OSError:
          # Directory not empty or other error, skip
          pass
  
  async def get_retention_status(self, user_id: Optional[UUID] = None) -> Dict[str, Any]:
    """
    Get document retention status and statistics.
    
    Args:
      user_id: Optional user ID to filter by
      
    Returns:
      Dictionary with retention statistics
    """
    base_query = select(Document)
    
    if user_id:
      base_query = base_query.where(Document.user_id == user_id)
    
    # Total documents
    total_result = await self.db.execute(base_query)
    total_documents = len(total_result.scalars().all())
    
    # Documents by status
    status_query = base_query.group_by(Document.status)
    status_result = await self.db.execute(status_query)
    
    # Expired documents
    cutoff_date = datetime.utcnow() - timedelta(days=self.default_retention_days)
    expired_query = base_query.where(
      and_(
        Document.created_at < cutoff_date,
        Document.status != DocumentStatus.DELETED
      )
    )
    expired_result = await self.db.execute(expired_query)
    expired_documents = len(expired_result.scalars().all())
    
    # Approaching expiry (within 30 days)
    warning_date = datetime.utcnow() - timedelta(days=self.default_retention_days - 30)
    warning_query = base_query.where(
      and_(
        Document.created_at < warning_date,
        Document.created_at >= cutoff_date,
        Document.status != DocumentStatus.DELETED
      )
    )
    warning_result = await self.db.execute(warning_query)
    approaching_expiry = len(warning_result.scalars().all())
    
    return {
      'total_documents': total_documents,
      'expired_documents': expired_documents,
      'approaching_expiry': approaching_expiry,
      'retention_period_days': self.default_retention_days,
      'next_cleanup_due': (datetime.utcnow() + timedelta(days=1)).isoformat(),
      'user_id': str(user_id) if user_id else None
    }
  
  async def schedule_document_deletion(self, document_id: UUID, deletion_date: datetime, reason: str) -> bool:
    """
    Schedule a document for deletion at a specific date.
    
    Args:
      document_id: Document ID to schedule for deletion
      deletion_date: When to delete the document
      reason: Reason for scheduled deletion
      
    Returns:
      True if scheduled successfully
    """
    try:
      query = select(Document).where(Document.id == document_id)
      result = await self.db.execute(query)
      document = result.scalar_one_or_none()
      
      if not document:
        return False
      
      # Add to scheduled deletions (you'd need a separate table for this)
      document.scheduled_deletion_date = deletion_date
      document.scheduled_deletion_reason = reason
      
      await self.db.commit()
      
      self.logger.info(f"Scheduled document {document_id} for deletion on {deletion_date}")
      return True
      
    except Exception as e:
      self.logger.error(f"Failed to schedule document deletion: {e}")
      return False


async def run_gdpr_cleanup() -> Dict[str, Any]:
  """
  Standalone function to run GDPR cleanup.
  Can be called from cron jobs or background tasks.
  """
  async with get_db() as db:
    cleanup_service = GDPRDocumentCleanup(db)
    return await cleanup_service.cleanup_expired_documents()


# Background task for automatic cleanup
async def gdpr_cleanup_task():
  """Background task that runs GDPR cleanup periodically"""
  while True:
    try:
      stats = await run_gdpr_cleanup()
      logging.info(f"Automated GDPR cleanup completed: {stats}")
    except Exception as e:
      logging.error(f"Automated GDPR cleanup failed: {e}")
    
    # Wait 24 hours before next cleanup
    await asyncio.sleep(24 * 60 * 60)