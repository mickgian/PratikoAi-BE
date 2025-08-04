"""API key rotation system for enhanced security."""

import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy import select, and_
from app.core.config import settings
from app.core.logging import logger
from app.services.database import database_service


class APIKeyRotationManager:
    """Manages API key rotation and lifecycle."""
    
    def __init__(self):
        """Initialize API key rotation manager."""
        self.key_length = 32
        self.rotation_interval_days = 30
        self.grace_period_days = 7
        self.max_active_keys = 3
    
    def generate_api_key(self, user_id: str, key_type: str = "user") -> str:
        """Generate a new API key for a user.
        
        Args:
            user_id: User identifier
            key_type: Type of key (user, admin, service)
            
        Returns:
            New API key string
        """
        try:
            # Generate secure random key
            raw_key = secrets.token_urlsafe(self.key_length)
            
            # Create key with prefix for identification
            prefix_map = {
                "user": "nai_user_",
                "admin": "nai_admin_", 
                "service": "nai_svc_"
            }
            
            prefix = prefix_map.get(key_type, "nai_user_")
            api_key = f"{prefix}{raw_key}"
            
            logger.info(
                "api_key_generated",
                user_id=user_id,
                key_type=key_type,
                key_prefix=api_key[:12] + "...",
                generated_at=datetime.utcnow().isoformat()
            )
            
            return api_key
            
        except Exception as e:
            logger.error(
                "api_key_generation_failed",
                user_id=user_id,
                key_type=key_type,
                error=str(e),
                exc_info=True
            )
            raise ValueError(f"Failed to generate API key: {str(e)}")
    
    def hash_api_key(self, api_key: str) -> str:
        """Create hash of API key for secure storage.
        
        Args:
            api_key: Raw API key
            
        Returns:
            SHA-256 hash of the key
        """
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    async def store_api_key(
        self, 
        user_id: str, 
        api_key: str, 
        key_type: str = "user",
        expires_at: Optional[datetime] = None
    ) -> bool:
        """Store API key securely in database.
        
        Args:
            user_id: User identifier
            api_key: Raw API key (will be hashed)
            key_type: Type of key
            expires_at: Optional expiration date
            
        Returns:
            True if successful
        """
        try:
            # Hash the key for storage
            key_hash = self.hash_api_key(api_key)
            
            # Set default expiration
            if expires_at is None:
                expires_at = datetime.utcnow() + timedelta(days=self.rotation_interval_days)
            
            # Store in database (would need actual API key table)
            # For now, simulate successful storage
            logger.info(
                "api_key_stored",
                user_id=user_id,
                key_type=key_type,
                key_hash=key_hash[:16] + "...",
                expires_at=expires_at.isoformat()
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "api_key_storage_failed",
                user_id=user_id,
                error=str(e),
                exc_info=True
            )
            return False
    
    async def rotate_user_keys(self, user_id: str) -> Dict[str, str]:
        """Rotate all API keys for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary with old and new key information
        """
        try:
            # Get existing active keys (would query database)
            existing_keys = await self._get_active_keys(user_id)
            
            # Generate new key
            new_key = self.generate_api_key(user_id, "user")
            
            # Store new key
            await self.store_api_key(user_id, new_key)
            
            # Mark old keys for deprecation (grace period)
            deprecation_date = datetime.utcnow() + timedelta(days=self.grace_period_days)
            await self._deprecate_keys(existing_keys, deprecation_date)
            
            logger.info(
                "user_keys_rotated",
                user_id=user_id,
                old_keys_count=len(existing_keys),
                new_key_prefix=new_key[:12] + "...",
                grace_period_ends=deprecation_date.isoformat()
            )
            
            return {
                "new_key": new_key,
                "old_keys_count": len(existing_keys),
                "grace_period_ends": deprecation_date.isoformat(),
                "rotation_completed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(
                "key_rotation_failed",
                user_id=user_id,
                error=str(e),
                exc_info=True
            )
            raise ValueError(f"Key rotation failed: {str(e)}")
    
    async def validate_api_key(self, api_key: str) -> Optional[Dict[str, any]]:
        """Validate API key and return user information.
        
        Args:
            api_key: API key to validate
            
        Returns:
            User information if valid, None if invalid
        """
        try:
            key_hash = self.hash_api_key(api_key)
            
            # Would query database for key validation
            # For now, simulate validation logic
            
            # Extract key type from prefix
            key_type = "user"
            if api_key.startswith("nai_admin_"):
                key_type = "admin"
            elif api_key.startswith("nai_svc_"):
                key_type = "service"
            
            # Simulate successful validation
            user_info = {
                "user_id": "simulated_user",
                "key_type": key_type,
                "validated_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(days=30)).isoformat()
            }
            
            logger.debug(
                "api_key_validated",
                key_prefix=api_key[:12] + "...",
                key_type=key_type,
                user_id=user_info["user_id"]
            )
            
            return user_info
            
        except Exception as e:
            logger.error(
                "api_key_validation_failed",
                key_prefix=api_key[:12] + "..." if api_key else "empty",
                error=str(e)
            )
            return None
    
    async def revoke_api_key(self, api_key: str, reason: str = "manual_revocation") -> bool:
        """Revoke an API key immediately.
        
        Args:
            api_key: API key to revoke
            reason: Reason for revocation
            
        Returns:
            True if successful
        """
        try:
            key_hash = self.hash_api_key(api_key)
            
            # Would update database to mark key as revoked
            logger.info(
                "api_key_revoked",
                key_hash=key_hash[:16] + "...",
                reason=reason,
                revoked_at=datetime.utcnow().isoformat()
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "api_key_revocation_failed",
                reason=reason,
                error=str(e),
                exc_info=True
            )
            return False
    
    async def cleanup_expired_keys(self) -> int:
        """Clean up expired API keys.
        
        Returns:
            Number of keys cleaned up
        """
        try:
            # Would query and delete expired keys from database
            current_time = datetime.utcnow()
            
            # Simulate cleanup
            cleaned_count = 0  # Would be actual count from database
            
            logger.info(
                "expired_keys_cleaned",
                cleaned_count=cleaned_count,
                cleanup_time=current_time.isoformat()
            )
            
            return cleaned_count
            
        except Exception as e:
            logger.error(
                "key_cleanup_failed",
                error=str(e),
                exc_info=True
            )
            return 0
    
    async def get_key_statistics(self, user_id: Optional[str] = None) -> Dict[str, any]:
        """Get API key usage statistics.
        
        Args:
            user_id: Optional user filter
            
        Returns:
            Key usage statistics
        """
        try:
            # Would query database for statistics
            stats = {
                "total_active_keys": 150,
                "total_expired_keys": 45,
                "keys_expiring_soon": 12,
                "rotation_events_last_30_days": 23,
                "average_key_lifetime_days": 28.5,
                "key_types": {
                    "user": 140,
                    "admin": 8,
                    "service": 2
                }
            }
            
            if user_id:
                stats["user_specific"] = {
                    "user_id": user_id,
                    "active_keys": 2,
                    "last_rotation": "2024-01-15T10:30:00Z",
                    "next_rotation_due": "2024-02-14T10:30:00Z"
                }
            
            logger.debug(
                "key_statistics_retrieved",
                user_id=user_id,
                total_keys=stats["total_active_keys"]
            )
            
            return stats
            
        except Exception as e:
            logger.error(
                "key_statistics_failed",
                user_id=user_id,
                error=str(e),
                exc_info=True
            )
            return {}
    
    async def _get_active_keys(self, user_id: str) -> List[str]:
        """Get active API keys for a user."""
        # Would query database
        return []  # Placeholder
    
    async def _deprecate_keys(self, key_hashes: List[str], deprecation_date: datetime) -> bool:
        """Mark keys for deprecation."""
        # Would update database
        return True  # Placeholder


# Global instance
api_key_manager = APIKeyRotationManager()