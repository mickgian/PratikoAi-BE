"""Secure Document Storage Service with GDPR Compliance.

Handles encrypted storage, retrieval, and GDPR-compliant deletion of uploaded
documents with comprehensive audit logging and automatic cleanup.
"""

import base64
import hashlib
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, BinaryIO, Dict, Optional
from uuid import UUID, uuid4

from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.config import get_settings
from app.core.logging import logger
from app.models.document_simple import Document


class SecureDocumentStorage:
    """Secure encrypted storage for uploaded documents with GDPR compliance"""

    def __init__(self):
        self.settings = get_settings()
        self.storage_path = Path("/tmp/secure_document_storage")  # Would be configurable
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Initialize encryption
        self._encryption_key = self._derive_encryption_key()
        self._cipher = Fernet(self._encryption_key)

    async def store_document(self, document: Document, content: bytes) -> dict[str, Any]:
        """Store document with encryption and security measures.

        Args:
          document: Document model instance
          content: Raw document content bytes

        Returns:
          Dictionary with storage results
        """
        try:
            # Generate storage filename
            storage_filename = f"{document.id}_{document.filename}"
            storage_file_path = self.storage_path / storage_filename

            # Encrypt content
            encrypted_content = self._encrypt_content(content)

            # Write encrypted content to storage
            with open(storage_file_path, "wb") as f:
                f.write(encrypted_content)

            # Set restrictive file permissions (owner read/write only)
            os.chmod(storage_file_path, 0o600)

            # Generate encryption key ID for tracking
            key_id = hashlib.sha256(self._encryption_key).hexdigest()[:16]

            # Log storage event
            logger.info(
                "document_stored_securely",
                document_id=str(document.id),
                filename=document.filename,
                encrypted_size=len(encrypted_content),
                storage_path=str(storage_file_path),
            )

            return {
                "success": True,
                "storage_path": str(storage_file_path),
                "encrypted": True,
                "encryption_key_id": key_id,
                "storage_size": len(encrypted_content),
                "stored_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Document storage failed: {str(e)}")
            return {"success": False, "error": str(e)}

    async def retrieve_document(self, document_id: UUID) -> dict[str, Any]:
        """Retrieve and decrypt stored document.

        Args:
          document_id: UUID of document to retrieve

        Returns:
          Dictionary with decrypted content and metadata
        """
        try:
            # Find storage file
            storage_files = list(self.storage_path.glob(f"{document_id}_*"))
            if not storage_files:
                return {"success": False, "error": "Document not found in storage"}

            storage_file_path = storage_files[0]

            # Read encrypted content
            with open(storage_file_path, "rb") as f:
                encrypted_content = f.read()

            # Decrypt content
            decrypted_content = self._decrypt_content(encrypted_content)

            # Log retrieval event
            logger.info("document_retrieved", document_id=str(document_id), decrypted_size=len(decrypted_content))

            return {
                "success": True,
                "content": decrypted_content,
                "decrypted": True,
                "retrieved_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Document retrieval failed: {str(e)}")
            return {"success": False, "error": str(e)}

    async def cleanup_expired_documents(self) -> dict[str, Any]:
        """Clean up expired documents according to GDPR requirements.

        Returns:
          Dictionary with cleanup statistics
        """
        try:
            cleanup_count = 0
            storage_freed = 0

            # Get current time
            current_time = datetime.utcnow()

            # Scan storage directory for files
            for storage_file in self.storage_path.glob("*"):
                try:
                    # Extract document ID from filename
                    filename_parts = storage_file.name.split("_", 1)
                    if len(filename_parts) < 2:
                        continue

                    document_id_str = filename_parts[0]

                    # This would normally query the database to check expiration
                    # For now, simulate by checking file modification time
                    file_stat = storage_file.stat()
                    file_age = current_time - datetime.fromtimestamp(file_stat.st_mtime)

                    # If file is older than 48 hours, consider it expired
                    if file_age > timedelta(hours=48):
                        file_size = file_stat.st_size

                        # Secure deletion
                        await self._secure_delete_file(storage_file)

                        cleanup_count += 1
                        storage_freed += file_size

                        logger.info(
                            "expired_document_cleaned",
                            document_id=document_id_str,
                            file_size=file_size,
                            age_hours=file_age.total_seconds() / 3600,
                        )

                except Exception as file_error:
                    logger.error(f"Failed to process file {storage_file}: {str(file_error)}")
                    continue

            logger.info(
                "document_cleanup_completed", documents_cleaned=cleanup_count, storage_freed_bytes=storage_freed
            )

            return {
                "success": True,
                "documents_cleaned": cleanup_count,
                "storage_freed": storage_freed,
                "cleanup_time": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Document cleanup failed: {str(e)}")
            return {"success": False, "error": str(e)}

    async def gdpr_delete_document(self, document_id: UUID, user_id: UUID, reason: str) -> dict[str, Any]:
        """GDPR-compliant document deletion with audit trail.

        Args:
          document_id: Document to delete
          user_id: User requesting deletion
          reason: Reason for deletion

        Returns:
          Dictionary with deletion confirmation
        """
        try:
            # Find storage file
            storage_files = list(self.storage_path.glob(f"{document_id}_*"))
            if not storage_files:
                return {
                    "success": True,  # Already deleted
                    "message": "Document not found - may already be deleted",
                }

            storage_file_path = storage_files[0]
            file_size = storage_file_path.stat().st_size

            # Secure deletion with overwriting
            await self._secure_delete_file(storage_file_path, overwrite_passes=3)

            # Log GDPR deletion event
            logger.info(
                "gdpr_document_deleted",
                document_id=str(document_id),
                user_id=str(user_id),
                reason=reason,
                file_size=file_size,
                deletion_method="secure_overwrite",
                deleted_at=datetime.utcnow().isoformat(),
            )

            return {
                "success": True,
                "document_id": str(document_id),
                "deletion_method": "secure_overwrite",
                "audit_logged": True,
                "gdpr_compliant": True,
                "deleted_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"GDPR document deletion failed: {str(e)}")
            return {"success": False, "error": str(e)}

    def _derive_encryption_key(self) -> bytes:
        """Derive encryption key from settings"""
        # In production, use proper key management service
        password = self.settings.JWT_SECRET_KEY.encode("utf-8")
        salt = b"pratiko_ai_document_storage_salt"  # Should be random and stored securely

        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000, backend=default_backend())

        key = base64.urlsafe_b64encode(kdf.derive(password))
        return key

    def _encrypt_content(self, content: bytes) -> bytes:
        """Encrypt document content"""
        try:
            return self._cipher.encrypt(content)
        except Exception as e:
            logger.error(f"Content encryption failed: {str(e)}")
            raise

    def _decrypt_content(self, encrypted_content: bytes) -> bytes:
        """Decrypt document content"""
        try:
            return self._cipher.decrypt(encrypted_content)
        except Exception as e:
            logger.error(f"Content decryption failed: {str(e)}")
            raise

    async def _secure_delete_file(self, file_path: Path, overwrite_passes: int = 1) -> None:
        """Securely delete file with overwriting to prevent recovery.

        Args:
          file_path: Path to file to delete
          overwrite_passes: Number of overwrite passes
        """
        try:
            if not file_path.exists():
                return

            file_size = file_path.stat().st_size

            # Overwrite file content multiple times
            with open(file_path, "rb+") as f:
                for _pass_num in range(overwrite_passes):
                    f.seek(0)
                    # Overwrite with random data
                    f.write(os.urandom(file_size))
                    f.flush()
                    os.fsync(f.fileno())  # Force write to disk

            # Finally delete the file
            file_path.unlink()

            logger.debug("file_securely_deleted", file_path=str(file_path), overwrite_passes=overwrite_passes)

        except Exception as e:
            logger.error(f"Secure file deletion failed: {str(e)}")
            raise

    def get_storage_stats(self) -> dict[str, Any]:
        """Get storage statistics"""
        try:
            total_files = 0
            total_size = 0

            for storage_file in self.storage_path.glob("*"):
                if storage_file.is_file():
                    total_files += 1
                    total_size += storage_file.stat().st_size

            return {
                "total_files": total_files,
                "total_size_bytes": total_size,
                "total_size_mb": total_size / (1024 * 1024),
                "storage_path": str(self.storage_path),
            }

        except Exception as e:
            logger.error(f"Failed to get storage stats: {str(e)}")
            return {"error": str(e)}
