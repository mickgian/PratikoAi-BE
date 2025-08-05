"""
Encryption Key Rotation System for PratikoAI.

This module provides automated key rotation capabilities with comprehensive
data re-encryption, audit logging, and rollback procedures to maintain
security while ensuring zero data loss.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from sqlalchemy import text, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.services.database_encryption_service import DatabaseEncryptionService, ENCRYPTED_FIELDS_CONFIG
from app.core.logging import logger
from app.core.config import get_settings


class RotationStatus(str, Enum):
    """Key rotation status values."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class RotationPriority(str, Enum):
    """Key rotation priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    EMERGENCY = "emergency"


@dataclass
class RotationPlan:
    """Plan for key rotation operation."""
    rotation_id: str
    old_key_version: int
    new_key_version: int
    tables_to_rotate: List[str]
    estimated_records: int
    estimated_duration_minutes: int
    priority: RotationPriority
    scheduled_start: datetime
    created_at: datetime


@dataclass
class RotationProgress:
    """Progress tracking for key rotation."""
    rotation_id: str
    status: RotationStatus
    current_table: Optional[str]
    tables_completed: int
    total_tables: int
    records_processed: int
    total_records: int
    errors_encountered: int
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    last_checkpoint: Optional[datetime]


@dataclass
class RotationResult:
    """Result of key rotation operation."""
    rotation_id: str
    success: bool
    old_key_version: int
    new_key_version: int
    tables_rotated: List[str]
    total_records_processed: int
    total_errors: int
    duration_seconds: float
    rollback_performed: bool
    error_details: Optional[str]


class EncryptionKeyRotationService:
    """
    Service for managing encryption key rotation with zero data loss.
    
    Features:
    - Automated quarterly key rotation
    - Batch processing with checkpoints
    - Comprehensive audit logging
    - Emergency rollback procedures
    - Performance monitoring
    - GDPR compliance tracking
    """
    
    def __init__(
        self,
        db_session: AsyncSession,
        encryption_service: DatabaseEncryptionService,
        batch_size: int = 1000,
        max_retry_attempts: int = 3
    ):
        """
        Initialize key rotation service.
        
        Args:
            db_session: Database session for operations
            encryption_service: Encryption service instance
            batch_size: Number of records to process per batch
            max_retry_attempts: Maximum retry attempts for failed operations
        """
        self.db = db_session
        self.encryption_service = encryption_service
        self.batch_size = batch_size
        self.max_retry_attempts = max_retry_attempts
        self.settings = get_settings()
        
        # Current rotation state
        self.current_rotation: Optional[RotationProgress] = None
        self.rotation_history: List[RotationResult] = []
        
        # Performance metrics
        self.performance_metrics = {
            "total_rotations": 0,
            "successful_rotations": 0,
            "failed_rotations": 0,
            "total_records_rotated": 0,
            "avg_rotation_time_hours": 0.0,
            "last_rotation_date": None
        }
    
    async def create_rotation_plan(
        self,
        priority: RotationPriority = RotationPriority.NORMAL,
        scheduled_start: Optional[datetime] = None,
        tables_override: Optional[List[str]] = None
    ) -> RotationPlan:
        """
        Create a rotation plan with impact analysis.
        
        Args:
            priority: Rotation priority level
            scheduled_start: When to start rotation (defaults to now)
            tables_override: Specific tables to rotate (defaults to all encrypted tables)
            
        Returns:
            RotationPlan with detailed planning information
        """
        if scheduled_start is None:
            scheduled_start = datetime.now(timezone.utc)
        
        # Get current active key version
        old_key_version = self.encryption_service.current_key_version
        new_key_version = old_key_version + 1 if old_key_version else 1
        
        # Determine tables to rotate
        if tables_override:
            tables_to_rotate = tables_override
        else:
            tables_to_rotate = list(ENCRYPTED_FIELDS_CONFIG.keys())
        
        # Estimate total records
        total_records = 0
        for table_name in tables_to_rotate:
            try:
                result = await self.db.execute(
                    text(f"SELECT COUNT(*) FROM {table_name}")
                )
                count = result.scalar() or 0
                total_records += count
            except SQLAlchemyError as e:
                logger.warning(f"Could not count records in {table_name}: {e}")
        
        # Estimate duration (rough calculation based on batch size and processing time)
        estimated_minutes = max(
            int((total_records / self.batch_size) * 0.1),  # 0.1 minutes per batch
            5  # Minimum 5 minutes
        )
        
        # Generate rotation ID
        rotation_id = f"rotation_{new_key_version}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        
        plan = RotationPlan(
            rotation_id=rotation_id,
            old_key_version=old_key_version,
            new_key_version=new_key_version,
            tables_to_rotate=tables_to_rotate,
            estimated_records=total_records,
            estimated_duration_minutes=estimated_minutes,
            priority=priority,
            scheduled_start=scheduled_start,
            created_at=datetime.now(timezone.utc)
        )
        
        logger.info(f"Created rotation plan {rotation_id}: {len(tables_to_rotate)} tables, {total_records} records")
        return plan
    
    async def execute_rotation_plan(self, plan: RotationPlan) -> RotationResult:
        """
        Execute a key rotation plan with comprehensive error handling.
        
        Args:
            plan: Rotation plan to execute
            
        Returns:
            RotationResult with operation details and success status
        """
        start_time = datetime.now(timezone.utc)
        
        # Initialize progress tracking
        self.current_rotation = RotationProgress(
            rotation_id=plan.rotation_id,
            status=RotationStatus.IN_PROGRESS,
            current_table=None,
            tables_completed=0,
            total_tables=len(plan.tables_to_rotate),
            records_processed=0,
            total_records=plan.estimated_records,
            errors_encountered=0,
            start_time=start_time,
            end_time=None,
            last_checkpoint=start_time
        )
        
        logger.info(f"Starting key rotation {plan.rotation_id}")
        
        try:
            # Step 1: Create new encryption key
            await self._create_new_encryption_key(plan.new_key_version)
            
            # Step 2: Process each table
            tables_rotated = []
            total_errors = 0
            
            for table_name in plan.tables_to_rotate:
                self.current_rotation.current_table = table_name
                
                try:
                    records_rotated, errors = await self._rotate_table_data(
                        table_name,
                        plan.old_key_version,
                        plan.new_key_version
                    )
                    
                    tables_rotated.append(table_name)
                    self.current_rotation.records_processed += records_rotated
                    self.current_rotation.errors_encountered += errors
                    total_errors += errors
                    
                    logger.info(
                        f"Rotated {records_rotated} records in {table_name} "
                        f"({errors} errors)"
                    )
                    
                except Exception as e:
                    logger.error(f"Failed to rotate table {table_name}: {e}")
                    self.current_rotation.errors_encountered += 1
                    total_errors += 1
                    
                    # Decide whether to continue or abort
                    if self.current_rotation.errors_encountered > 5:
                        raise Exception(f"Too many table rotation failures: {e}")
                
                self.current_rotation.tables_completed += 1
                self.current_rotation.last_checkpoint = datetime.now(timezone.utc)
            
            # Step 3: Activate new key and deactivate old key
            await self._finalize_key_rotation(plan.old_key_version, plan.new_key_version)
            
            # Step 4: Update progress and create result
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            
            self.current_rotation.status = RotationStatus.COMPLETED
            self.current_rotation.end_time = end_time
            
            result = RotationResult(
                rotation_id=plan.rotation_id,
                success=True,
                old_key_version=plan.old_key_version,
                new_key_version=plan.new_key_version,
                tables_rotated=tables_rotated,
                total_records_processed=self.current_rotation.records_processed,
                total_errors=total_errors,
                duration_seconds=duration,
                rollback_performed=False,
                error_details=None
            )
            
            # Log completion
            await self._log_rotation_completion(result)
            
            logger.info(
                f"Key rotation {plan.rotation_id} completed successfully: "
                f"{len(tables_rotated)} tables, {result.total_records_processed} records, "
                f"{duration:.1f}s"
            )
            
            return result
            
        except Exception as e:
            # Handle rotation failure
            logger.error(f"Key rotation {plan.rotation_id} failed: {e}")
            
            # Attempt rollback
            rollback_success = await self._rollback_rotation(
                plan.rotation_id,
                plan.old_key_version,
                plan.new_key_version
            )
            
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            
            self.current_rotation.status = RotationStatus.FAILED
            self.current_rotation.end_time = end_time
            
            result = RotationResult(
                rotation_id=plan.rotation_id,
                success=False,
                old_key_version=plan.old_key_version,
                new_key_version=plan.new_key_version,
                tables_rotated=[],
                total_records_processed=self.current_rotation.records_processed,
                total_errors=self.current_rotation.errors_encountered,
                duration_seconds=duration,
                rollback_performed=rollback_success,
                error_details=str(e)
            )
            
            await self._log_rotation_failure(result)
            return result
        
        finally:
            # Clean up current rotation state
            self.current_rotation = None
    
    async def _create_new_encryption_key(self, new_key_version: int) -> None:
        """Create new encryption key version."""
        try:
            # This will create the new key and add it to the encryption service
            old_version = self.encryption_service.current_key_version
            await self.encryption_service.rotate_keys()
            
            # Verify new key was created
            if self.encryption_service.current_key_version != new_key_version:
                raise Exception(
                    f"Expected new key version {new_key_version}, "
                    f"got {self.encryption_service.current_key_version}"
                )
            
            logger.info(f"Created new encryption key version {new_key_version}")
            
        except Exception as e:
            logger.error(f"Failed to create new encryption key: {e}")
            raise
    
    async def _rotate_table_data(
        self,
        table_name: str,
        old_key_version: int,
        new_key_version: int
    ) -> Tuple[int, int]:
        """
        Rotate encryption keys for all encrypted fields in a table.
        
        Args:
            table_name: Name of table to rotate
            old_key_version: Old key version
            new_key_version: New key version
            
        Returns:
            Tuple of (records_processed, errors_encountered)
        """
        if table_name not in ENCRYPTED_FIELDS_CONFIG:
            logger.warning(f"No encryption configuration found for table {table_name}")
            return 0, 0
        
        config = ENCRYPTED_FIELDS_CONFIG[table_name]
        encrypted_fields = config["fields"]
        
        if not encrypted_fields:
            logger.info(f"No encrypted fields in table {table_name}")
            return 0, 0
        
        # Get total record count
        count_result = await self.db.execute(
            text(f"SELECT COUNT(*) FROM {table_name}")
        )
        total_records = count_result.scalar() or 0
        
        if total_records == 0:
            logger.info(f"No records to rotate in table {table_name}")
            return 0, 0
        
        records_processed = 0
        errors_encountered = 0
        
        # Process in batches
        offset = 0
        while offset < total_records:
            try:
                # Get batch of records
                field_list = ", ".join(["id"] + encrypted_fields)
                result = await self.db.execute(text(f"""
                    SELECT {field_list}
                    FROM {table_name}
                    ORDER BY id
                    LIMIT :limit OFFSET :offset
                """), {"limit": self.batch_size, "offset": offset})
                
                batch_records = result.fetchall()
                if not batch_records:
                    break
                
                # Re-encrypt each record
                for record in batch_records:
                    try:
                        await self._rotate_record_encryption(
                            table_name,
                            record,
                            encrypted_fields,
                            old_key_version,
                            new_key_version
                        )
                        records_processed += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to rotate record {record[0]} in {table_name}: {e}")
                        errors_encountered += 1
                
                # Commit batch
                await self.db.commit()
                
                # Update progress
                offset += self.batch_size
                
                # Log progress periodically
                if offset % (self.batch_size * 10) == 0:
                    progress_pct = (offset / total_records) * 100
                    logger.info(
                        f"Table {table_name}: {offset}/{total_records} records "
                        f"({progress_pct:.1f}%)"
                    )
                
            except Exception as e:
                logger.error(f"Batch processing failed for {table_name} at offset {offset}: {e}")
                errors_encountered += 1
                await self.db.rollback()
                
                # Skip problematic batch and continue
                offset += self.batch_size
        
        logger.info(
            f"Completed table {table_name}: {records_processed} records processed, "
            f"{errors_encountered} errors"
        )
        
        return records_processed, errors_encountered
    
    async def _rotate_record_encryption(
        self,
        table_name: str,
        record: Any,
        encrypted_fields: List[str],
        old_key_version: int,
        new_key_version: int
    ) -> None:
        """Re-encrypt a single record with new key version."""
        record_id = record[0]  # First field is always ID
        
        # Build update query
        update_values = {"record_id": record_id}
        set_clauses = []
        
        for i, field_name in enumerate(encrypted_fields):
            field_value = record[i + 1]  # Skip ID field
            
            if field_value is not None:
                try:
                    # Decrypt with old key
                    decrypted_value = await self.encryption_service.decrypt_field(
                        field_value if isinstance(field_value, bytes) else field_value.encode(),
                        old_key_version
                    )
                    
                    # Re-encrypt with new key
                    encrypted_value = await self.encryption_service.encrypt_field(
                        decrypted_value,
                        field_type=ENCRYPTED_FIELDS_CONFIG[table_name]["field_types"].get(
                            field_name, "string"
                        )
                    )
                    
                    update_values[field_name] = encrypted_value
                    set_clauses.append(f"{field_name} = :{field_name}")
                    
                except Exception as e:
                    logger.error(f"Failed to re-encrypt {field_name} for record {record_id}: {e}")
                    raise
        
        # Update record if there are encrypted fields
        if set_clauses:
            update_query = f"""
                UPDATE {table_name}
                SET {', '.join(set_clauses)}
                WHERE id = :record_id
            """
            await self.db.execute(text(update_query), update_values)
    
    async def _finalize_key_rotation(self, old_key_version: int, new_key_version: int) -> None:
        """Finalize key rotation by updating key status."""
        try:
            # Mark old key as inactive
            await self.db.execute(text("""
                UPDATE encryption_keys
                SET is_active = FALSE, rotated_at = NOW()
                WHERE key_version = :old_version
            """), {"old_version": old_key_version})
            
            # Ensure new key is active
            await self.db.execute(text("""
                UPDATE encryption_keys
                SET is_active = TRUE
                WHERE key_version = :new_version
            """), {"new_version": new_key_version})
            
            await self.db.commit()
            
            logger.info(f"Finalized key rotation: {old_key_version} -> {new_key_version}")
            
        except Exception as e:
            logger.error(f"Failed to finalize key rotation: {e}")
            raise
    
    async def _rollback_rotation(
        self,
        rotation_id: str,
        old_key_version: int,
        new_key_version: int
    ) -> bool:
        """
        Rollback failed key rotation.
        
        Args:
            rotation_id: ID of failed rotation
            old_key_version: Old key version to restore
            new_key_version: New key version to deactivate
            
        Returns:
            True if rollback successful, False otherwise
        """
        try:
            logger.info(f"Starting rollback for rotation {rotation_id}")
            
            # Reactivate old key
            await self.db.execute(text("""
                UPDATE encryption_keys
                SET is_active = TRUE, rotated_at = NULL
                WHERE key_version = :old_version
            """), {"old_version": old_key_version})
            
            # Deactivate new key
            await self.db.execute(text("""
                UPDATE encryption_keys
                SET is_active = FALSE
                WHERE key_version = :new_version
            """), {"new_version": new_key_version})
            
            await self.db.commit()
            
            # Update encryption service state
            self.encryption_service.current_key_version = old_key_version
            if new_key_version in self.encryption_service.encryption_keys:
                self.encryption_service.encryption_keys[new_key_version].is_active = False
            if old_key_version in self.encryption_service.encryption_keys:
                self.encryption_service.encryption_keys[old_key_version].is_active = True
            
            logger.info(f"Rollback completed for rotation {rotation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Rollback failed for rotation {rotation_id}: {e}")
            return False
    
    async def _log_rotation_completion(self, result: RotationResult) -> None:
        """Log successful rotation completion."""
        await self.encryption_service._audit_log(
            operation="key_rotation_completed",
            key_version=result.new_key_version,
            success=True,
            error_message=f"Rotated {result.total_records_processed} records in {result.duration_seconds:.1f}s"
        )
    
    async def _log_rotation_failure(self, result: RotationResult) -> None:
        """Log rotation failure."""
        await self.encryption_service._audit_log(
            operation="key_rotation_failed",
            key_version=result.new_key_version,
            success=False,
            error_message=result.error_details
        )
    
    async def check_rotation_needed(self) -> bool:
        """
        Check if key rotation is needed based on schedule and policies.
        
        Returns:
            True if rotation is needed, False otherwise
        """
        return await self.encryption_service.check_key_rotation_needed()
    
    async def get_rotation_schedule(self) -> Dict[str, Any]:
        """
        Get current key rotation schedule and status.
        
        Returns:
            Dict with rotation schedule information
        """
        # Get current key info
        current_key = None
        if self.encryption_service.current_key_version:
            current_key = self.encryption_service.encryption_keys.get(
                self.encryption_service.current_key_version
            )
        
        # Calculate next rotation date
        next_rotation = None
        if current_key:
            next_rotation = current_key.created_at + timedelta(days=90)  # Quarterly
        
        # Check if rotation is overdue
        now = datetime.now(timezone.utc)
        is_overdue = next_rotation and now > next_rotation
        
        return {
            "current_key_version": self.encryption_service.current_key_version,
            "key_created_at": current_key.created_at.isoformat() if current_key else None,
            "next_rotation_due": next_rotation.isoformat() if next_rotation else None,
            "rotation_overdue": is_overdue,
            "days_until_rotation": (next_rotation - now).days if next_rotation and not is_overdue else 0,
            "rotation_interval_days": 90,
            "current_rotation_active": self.current_rotation is not None,
            "total_encrypted_tables": len(ENCRYPTED_FIELDS_CONFIG)
        }
    
    async def emergency_rotation(self, reason: str) -> RotationResult:
        """
        Perform emergency key rotation immediately.
        
        Args:
            reason: Reason for emergency rotation
            
        Returns:
            RotationResult with operation details
        """
        logger.warning(f"Emergency key rotation initiated: {reason}")
        
        # Create high-priority rotation plan
        plan = await self.create_rotation_plan(
            priority=RotationPriority.EMERGENCY,
            scheduled_start=datetime.now(timezone.utc)
        )
        
        # Execute immediately
        result = await self.execute_rotation_plan(plan)
        
        # Log emergency rotation
        await self.encryption_service._audit_log(
            operation="emergency_key_rotation",
            key_version=result.new_key_version,
            success=result.success,
            error_message=f"Emergency rotation: {reason}"
        )
        
        return result


# Utility functions for key rotation management

async def schedule_automatic_rotation(
    db_session: AsyncSession,
    encryption_service: DatabaseEncryptionService
) -> None:
    """Schedule automatic key rotation based on policy."""
    rotation_service = EncryptionKeyRotationService(db_session, encryption_service)
    
    if await rotation_service.check_rotation_needed():
        logger.info("Automatic key rotation needed, creating plan...")
        
        plan = await rotation_service.create_rotation_plan(
            priority=RotationPriority.NORMAL
        )
        
        result = await rotation_service.execute_rotation_plan(plan)
        
        if result.success:
            logger.info(f"Automatic key rotation completed: {result.rotation_id}")
        else:
            logger.error(f"Automatic key rotation failed: {result.error_details}")


async def get_rotation_status(
    db_session: AsyncSession,
    encryption_service: DatabaseEncryptionService
) -> Dict[str, Any]:
    """Get current rotation status and metrics."""
    rotation_service = EncryptionKeyRotationService(db_session, encryption_service)
    
    schedule_info = await rotation_service.get_rotation_schedule()
    
    # Get rotation history from audit logs
    result = await db_session.execute(text("""
        SELECT 
            COUNT(*) as total_rotations,
            COUNT(*) FILTER (WHERE success = true) as successful_rotations,
            MAX(timestamp) as last_rotation
        FROM encryption_audit_log
        WHERE operation LIKE '%rotation%'
    """))
    
    stats = result.fetchone()
    
    return {
        "schedule": schedule_info,
        "statistics": {
            "total_rotations": stats[0] if stats else 0,
            "successful_rotations": stats[1] if stats else 0,
            "last_rotation": stats[2].isoformat() if stats and stats[2] else None
        },
        "current_rotation": rotation_service.current_rotation.__dict__ if rotation_service.current_rotation else None
    }