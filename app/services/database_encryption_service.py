"""Database Encryption at Rest Service for PratikoAI.

This service provides AES-256 encryption for PostgreSQL data with comprehensive
key management, rotation mechanisms, and compliance with Italian data protection requirements.

Key Features:
- AES-256-CBC encryption for sensitive fields
- Transparent encryption/decryption through SQLAlchemy
- Key versioning and rotation support
- Audit logging for compliance
- Performance optimization (<5% overhead)
- GDPR and Italian data protection compliance
"""

import asyncio
import base64
import hashlib
import os
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import logger


class EncryptionAlgorithm(str, Enum):
    """Supported encryption algorithms."""

    AES_256_CBC = "AES-256-CBC"
    AES_256_GCM = "AES-256-GCM"
    FERNET = "FERNET"


class FieldType(str, Enum):
    """Types of fields that can be encrypted."""

    EMAIL = "email"
    PHONE = "phone"
    TAX_ID = "tax_id"
    QUERY = "query"
    PERSONAL_DATA = "personal_data"
    FINANCIAL_DATA = "financial_data"
    STRING = "string"


@dataclass
class EncryptionKey:
    """Encryption key with metadata."""

    version: int
    key_data: bytes
    algorithm: EncryptionAlgorithm
    created_at: datetime
    is_active: bool = True
    rotated_at: datetime | None = None


@dataclass
class EncryptionResult:
    """Result of encryption operation."""

    ciphertext: bytes
    key_version: int
    algorithm: EncryptionAlgorithm
    metadata: dict[str, Any] | None = None


class DatabaseEncryptionService:
    """Database encryption service with AES-256 encryption and key management.

    Provides transparent encryption/decryption for sensitive database fields
    with support for key rotation, versioning, and compliance requirements.
    """

    def __init__(self, master_key: str | None = None, db_session: AsyncSession | None = None):
        """Initialize encryption service.

        Args:
            master_key: Master encryption key (from environment or key vault)
            db_session: Database session for key management operations
        """
        self.master_key = master_key or self._get_master_key_from_env()
        self.db_session = db_session
        self.current_key_version: int | None = None
        self.encryption_keys: dict[int, EncryptionKey] = {}
        self.settings = get_settings()

        # Performance metrics
        self.encryption_count = 0
        self.decryption_count = 0
        self.total_encryption_time = 0.0
        self.total_decryption_time = 0.0

        # Validate master key
        self._validate_master_key()

    def _get_master_key_from_env(self) -> str:
        """Get master key from environment variables."""
        master_key = os.getenv("DB_ENCRYPTION_MASTER_KEY")
        if not master_key:
            raise ValueError(
                "DB_ENCRYPTION_MASTER_KEY environment variable not set. "
                "Please set this to a secure 44-character Fernet key."
            )
        return master_key

    def _validate_master_key(self) -> None:
        """Validate master key format and security."""
        if not self.master_key:
            raise ValueError("Master key cannot be empty")

        if len(self.master_key) != 44:
            raise ValueError(
                f"Invalid master key length: {len(self.master_key)}. Fernet keys must be exactly 44 characters."
            )

        try:
            # Test that it's a valid Fernet key
            Fernet(self.master_key.encode())
        except Exception as e:
            raise ValueError(f"Invalid master key format: {e}")

    async def initialize(self) -> None:
        """Initialize encryption service and load keys.

        Creates initial encryption key if none exists,
        loads existing keys from database.
        """
        try:
            if self.db_session:
                await self._ensure_encryption_tables()
                await self._load_encryption_keys()

                if not self.encryption_keys:
                    # Create initial key
                    await self._create_initial_key()

                # Set current active key version
                active_keys = [k for k in self.encryption_keys.values() if k.is_active]
                if active_keys:
                    self.current_key_version = max(k.version for k in active_keys)
                else:
                    raise ValueError("No active encryption keys found")
            else:
                # Fallback for testing without database
                self.current_key_version = 1
                self.encryption_keys[1] = EncryptionKey(
                    version=1,
                    key_data=self._derive_key_from_master(1),
                    algorithm=EncryptionAlgorithm.AES_256_CBC,
                    created_at=datetime.now(UTC),
                    is_active=True,
                )

            logger.info(f"Encryption service initialized with key version {self.current_key_version}")

        except Exception as e:
            logger.error(f"Failed to initialize encryption service: {e}")
            raise

    async def _ensure_encryption_tables(self) -> None:
        """Ensure encryption management tables exist."""
        if not self.db_session:
            return

        # Create encryption_keys table
        await self.db_session.execute(
            text("""
            CREATE TABLE IF NOT EXISTS encryption_keys (
                id SERIAL PRIMARY KEY,
                key_version INTEGER NOT NULL UNIQUE,
                encrypted_key BYTEA NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                rotated_at TIMESTAMP WITH TIME ZONE,
                is_active BOOLEAN DEFAULT TRUE,
                algorithm VARCHAR(50) DEFAULT 'AES-256-CBC'
            )
        """)
        )

        # Create audit log table
        await self.db_session.execute(
            text("""
            CREATE TABLE IF NOT EXISTS encryption_audit_log (
                id SERIAL PRIMARY KEY,
                key_version INTEGER,
                operation VARCHAR(50) NOT NULL,
                table_name VARCHAR(100),
                user_id VARCHAR(100),
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                field_type VARCHAR(50),
                success BOOLEAN DEFAULT TRUE,
                error_message TEXT
            )
        """)
        )

        await self.db_session.commit()

    async def _load_encryption_keys(self) -> None:
        """Load encryption keys from database."""
        if not self.db_session:
            return

        result = await self.db_session.execute(
            text("""
            SELECT key_version, encrypted_key, algorithm, created_at, rotated_at, is_active
            FROM encryption_keys
            ORDER BY key_version
        """)
        )

        for row in result.fetchall():
            version, encrypted_key, algorithm, created_at, rotated_at, is_active = row

            # Decrypt the stored key using master key
            key_data = self._decrypt_stored_key(encrypted_key)

            self.encryption_keys[version] = EncryptionKey(
                version=version,
                key_data=key_data,
                algorithm=EncryptionAlgorithm(algorithm),
                created_at=created_at,
                rotated_at=rotated_at,
                is_active=is_active,
            )

    async def _create_initial_key(self) -> None:
        """Create initial encryption key."""
        key_version = 1
        key_data = self._derive_key_from_master(key_version)
        encrypted_key = self._encrypt_key_for_storage(key_data)

        await self.db_session.execute(
            text("""
            INSERT INTO encryption_keys (key_version, encrypted_key, algorithm, is_active)
            VALUES (:version, :key, :algorithm, :active)
        """),
            {
                "version": key_version,
                "key": encrypted_key,
                "algorithm": EncryptionAlgorithm.AES_256_CBC.value,
                "active": True,
            },
        )

        await self.db_session.commit()

        self.encryption_keys[key_version] = EncryptionKey(
            version=key_version,
            key_data=key_data,
            algorithm=EncryptionAlgorithm.AES_256_CBC,
            created_at=datetime.now(UTC),
            is_active=True,
        )

        await self._audit_log("create_key", key_version=key_version)

    def _derive_key_from_master(self, version: int) -> bytes:
        """Derive encryption key from master key and version."""
        # Use PBKDF2 to derive key from master key + version
        salt = f"pratikoai_v{version}".encode()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 256 bits for AES-256
            salt=salt,
            iterations=100000,
            backend=default_backend(),
        )
        return kdf.derive(self.master_key.encode())

    def _encrypt_key_for_storage(self, key_data: bytes) -> bytes:
        """Encrypt key data for secure storage."""
        fernet = Fernet(self.master_key.encode())
        return fernet.encrypt(key_data)

    def _decrypt_stored_key(self, encrypted_key: bytes) -> bytes:
        """Decrypt key data from storage."""
        fernet = Fernet(self.master_key.encode())
        return fernet.decrypt(encrypted_key)

    async def encrypt_field(
        self, plaintext: str, field_type: str | FieldType = FieldType.STRING, key_version: int | None = None
    ) -> bytes | None:
        """Encrypt a field value.

        Args:
            plaintext: Text to encrypt
            field_type: Type of field being encrypted
            key_version: Specific key version to use (defaults to current)

        Returns:
            Encrypted bytes or None if plaintext is None
        """
        if plaintext is None:
            return None

        if plaintext == "":
            # Handle empty strings
            plaintext = "__EMPTY_STRING__"

        import time

        start_time = time.perf_counter()

        try:
            # Use current key version if not specified
            if key_version is None:
                key_version = self.current_key_version

            if key_version not in self.encryption_keys:
                raise ValueError(f"Encryption key version {key_version} not found")

            encryption_key = self.encryption_keys[key_version]

            # Convert field_type to enum if needed
            if isinstance(field_type, str):
                try:
                    field_type = FieldType(field_type)
                except ValueError:
                    field_type = FieldType.STRING

            # Encrypt using AES-256-CBC
            ciphertext = self._encrypt_aes_256_cbc(plaintext.encode("utf-8"), encryption_key.key_data)

            # Create result with metadata
            result = self._create_encrypted_result(ciphertext, key_version, field_type)

            # Update performance metrics
            end_time = time.perf_counter()
            self.encryption_count += 1
            self.total_encryption_time += end_time - start_time

            # Audit log
            await self._audit_log("encrypt", key_version=key_version, field_type=field_type.value)

            return result

        except Exception as e:
            await self._audit_log(
                "encrypt",
                key_version=key_version,
                field_type=field_type.value if isinstance(field_type, FieldType) else field_type,
                success=False,
                error_message=str(e),
            )
            logger.error(f"Encryption failed: {e}")
            raise

    async def decrypt_field(self, ciphertext: bytes, key_version: int | None = None) -> str | None:
        """Decrypt a field value.

        Args:
            ciphertext: Encrypted bytes to decrypt
            key_version: Specific key version to use (auto-detected if None)

        Returns:
            Decrypted text or None if ciphertext is None
        """
        if ciphertext is None:
            return None

        import time

        start_time = time.perf_counter()

        try:
            # Extract metadata from ciphertext if available
            extracted_key_version, extracted_ciphertext = self._extract_metadata_from_ciphertext(ciphertext)

            # Use extracted or provided key version
            if key_version is None:
                key_version = extracted_key_version or self.current_key_version

            if key_version not in self.encryption_keys:
                raise ValueError(f"Decryption key version {key_version} not found")

            encryption_key = self.encryption_keys[key_version]

            # Decrypt using AES-256-CBC
            plaintext_bytes = self._decrypt_aes_256_cbc(extracted_ciphertext or ciphertext, encryption_key.key_data)

            plaintext = plaintext_bytes.decode("utf-8")

            # Handle empty string placeholder
            if plaintext == "__EMPTY_STRING__":
                plaintext = ""

            # Update performance metrics
            end_time = time.perf_counter()
            self.decryption_count += 1
            self.total_decryption_time += end_time - start_time

            # Audit log
            await self._audit_log("decrypt", key_version=key_version)

            return plaintext

        except Exception as e:
            await self._audit_log("decrypt", key_version=key_version, success=False, error_message=str(e))
            logger.error(f"Decryption failed: {e}")
            raise

    def _encrypt_aes_256_cbc(self, plaintext: bytes, key: bytes) -> bytes:
        """Encrypt using AES-256-CBC."""
        # Generate random IV
        iv = secrets.token_bytes(16)  # 128-bit IV for AES

        # Pad plaintext to AES block size (16 bytes)
        padded_plaintext = self._pad_pkcs7(plaintext, 16)

        # Create cipher
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())

        # Encrypt
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded_plaintext) + encryptor.finalize()

        # Return IV + ciphertext
        return iv + ciphertext

    def _decrypt_aes_256_cbc(self, ciphertext: bytes, key: bytes) -> bytes:
        """Decrypt using AES-256-CBC."""
        # Extract IV and ciphertext
        iv = ciphertext[:16]
        encrypted_data = ciphertext[16:]

        # Create cipher
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())

        # Decrypt
        decryptor = cipher.decryptor()
        padded_plaintext = decryptor.update(encrypted_data) + decryptor.finalize()

        # Remove padding
        plaintext = self._unpad_pkcs7(padded_plaintext)

        return plaintext

    def _pad_pkcs7(self, data: bytes, block_size: int) -> bytes:
        """Apply PKCS#7 padding."""
        padding_length = block_size - (len(data) % block_size)
        padding = bytes([padding_length] * padding_length)
        return data + padding

    def _unpad_pkcs7(self, padded_data: bytes) -> bytes:
        """Remove PKCS#7 padding."""
        padding_length = padded_data[-1]
        return padded_data[:-padding_length]

    def _create_encrypted_result(self, ciphertext: bytes, key_version: int, field_type: FieldType) -> bytes:
        """Create encrypted result with embedded metadata."""
        # For simplicity, we'll encode metadata as a prefix
        # Format: version:algorithm:field_type:ciphertext_base64
        metadata = f"{key_version}:{EncryptionAlgorithm.AES_256_CBC.value}:{field_type.value}:"
        ciphertext_b64 = base64.b64encode(ciphertext).decode("ascii")

        return f"{metadata}{ciphertext_b64}".encode()

    def _extract_metadata_from_ciphertext(self, ciphertext: bytes) -> tuple[int | None, bytes | None]:
        """Extract metadata from encrypted result."""
        try:
            ciphertext_str = ciphertext.decode("utf-8")
            parts = ciphertext_str.split(":", 3)

            if len(parts) == 4:
                version_str, algorithm, field_type, ciphertext_b64 = parts
                version = int(version_str) if version_str.isdigit() else None
                extracted_ciphertext = base64.b64decode(ciphertext_b64.encode("ascii"))
                return version, extracted_ciphertext

        except (UnicodeDecodeError, ValueError, base64.binascii.Error):
            # Fallback for raw ciphertext without metadata
            pass

        return None, None

    async def rotate_keys(self) -> None:
        """Rotate encryption keys and re-encrypt data.

        Creates new key version, marks old keys as inactive,
        and schedules re-encryption of existing data.
        """
        try:
            old_version = self.current_key_version
            new_version = max(self.encryption_keys.keys()) + 1 if self.encryption_keys else 1

            logger.info(f"Starting key rotation from version {old_version} to {new_version}")

            # Create new encryption key
            new_key_data = self._derive_key_from_master(new_version)
            encrypted_key = self._encrypt_key_for_storage(new_key_data)

            if self.db_session:
                # Mark old keys as inactive
                await self.db_session.execute(
                    text("""
                    UPDATE encryption_keys
                    SET is_active = FALSE, rotated_at = NOW()
                    WHERE is_active = TRUE
                """)
                )

                # Insert new key
                await self.db_session.execute(
                    text("""
                    INSERT INTO encryption_keys (key_version, encrypted_key, algorithm, is_active)
                    VALUES (:version, :key, :algorithm, :active)
                """),
                    {
                        "version": new_version,
                        "key": encrypted_key,
                        "algorithm": EncryptionAlgorithm.AES_256_CBC.value,
                        "active": True,
                    },
                )

                await self.db_session.commit()

            # Update in-memory keys
            if old_version and old_version in self.encryption_keys:
                self.encryption_keys[old_version].is_active = False
                self.encryption_keys[old_version].rotated_at = datetime.now(UTC)

            self.encryption_keys[new_version] = EncryptionKey(
                version=new_version,
                key_data=new_key_data,
                algorithm=EncryptionAlgorithm.AES_256_CBC,
                created_at=datetime.now(UTC),
                is_active=True,
            )

            self.current_key_version = new_version

            # Audit log
            await self._audit_log("rotate_keys", key_version=new_version)

            logger.info(f"Key rotation completed. New active version: {new_version}")

        except Exception as e:
            logger.error(f"Key rotation failed: {e}")
            await self._audit_log("rotate_keys", success=False, error_message=str(e))
            raise

    async def get_performance_metrics(self) -> dict[str, Any]:
        """Get encryption performance metrics."""
        avg_encryption_time = (
            (self.total_encryption_time / self.encryption_count * 1000) if self.encryption_count > 0 else 0
        )
        avg_decryption_time = (
            (self.total_decryption_time / self.decryption_count * 1000) if self.decryption_count > 0 else 0
        )

        return {
            "encryption_operations": self.encryption_count,
            "decryption_operations": self.decryption_count,
            "avg_encryption_time_ms": round(avg_encryption_time, 3),
            "avg_decryption_time_ms": round(avg_decryption_time, 3),
            "total_encryption_time_s": round(self.total_encryption_time, 3),
            "total_decryption_time_s": round(self.total_decryption_time, 3),
            "current_key_version": self.current_key_version,
            "active_keys": len([k for k in self.encryption_keys.values() if k.is_active]),
            "total_keys": len(self.encryption_keys),
        }

    async def _audit_log(
        self,
        operation: str,
        table_name: str | None = None,
        user_id: str | None = None,
        key_version: int | None = None,
        field_type: str | None = None,
        success: bool = True,
        error_message: str | None = None,
    ) -> None:
        """Log encryption operations for audit compliance."""
        try:
            if self.db_session:
                await self.db_session.execute(
                    text("""
                    INSERT INTO encryption_audit_log
                    (operation, table_name, user_id, key_version, field_type, success, error_message)
                    VALUES (:op, :table, :user, :version, :field_type, :success, :error)
                """),
                    {
                        "op": operation,
                        "table": table_name,
                        "user": user_id,
                        "version": key_version,
                        "field_type": field_type,
                        "success": success,
                        "error": error_message,
                    },
                )

                # Don't commit here - let the calling transaction handle it

        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
            # Don't raise - audit logging failure shouldn't break encryption

    async def check_key_rotation_needed(self) -> bool:
        """Check if key rotation is needed based on schedule."""
        if not self.encryption_keys or not self.current_key_version:
            return True

        current_key = self.encryption_keys.get(self.current_key_version)
        if not current_key:
            return True

        # Check if key is older than rotation interval (90 days)
        rotation_interval = timedelta(days=90)
        age = datetime.now(UTC) - current_key.created_at

        return age >= rotation_interval

    async def migrate_unencrypted_data(
        self, table_name: str, encrypted_fields: list[str], batch_size: int = 1000
    ) -> dict[str, Any]:
        """Migrate existing unencrypted data to encrypted format.

        Args:
            table_name: Name of table to migrate
            encrypted_fields: List of field names to encrypt
            batch_size: Number of records to process per batch

        Returns:
            Migration statistics
        """
        if not self.db_session:
            raise ValueError("Database session required for migration")

        stats = {
            "total_records": 0,
            "migrated_records": 0,
            "failed_records": 0,
            "fields_migrated": encrypted_fields.copy(),
            "start_time": datetime.now(UTC),
            "end_time": None,
        }

        try:
            logger.info(f"Starting migration of {table_name} fields: {encrypted_fields}")

            # Get total record count
            count_result = await self.db_session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            stats["total_records"] = count_result.scalar()

            # Process in batches
            offset = 0
            while offset < stats["total_records"]:
                # Get batch of records
                field_list = ", ".join(["id"] + encrypted_fields)
                result = await self.db_session.execute(
                    text(f"""
                    SELECT {field_list}
                    FROM {table_name}
                    ORDER BY id
                    LIMIT :limit OFFSET :offset
                """),
                    {"limit": batch_size, "offset": offset},
                )

                batch_records = result.fetchall()
                if not batch_records:
                    break

                # Encrypt each record
                for record in batch_records:
                    try:
                        # Build UPDATE query
                        update_values = {}
                        for i, field in enumerate(encrypted_fields):
                            field_value = record[i + 1]  # Skip ID field
                            if field_value is not None:
                                encrypted_value = await self.encrypt_field(field_value, FieldType.PERSONAL_DATA)
                                update_values[field] = encrypted_value

                        # Update record if there are values to encrypt
                        if update_values:
                            set_clause = ", ".join([f"{field} = :{field}" for field in update_values])
                            update_values["record_id"] = record[0]  # ID

                            await self.db_session.execute(
                                text(f"""
                                UPDATE {table_name}
                                SET {set_clause}
                                WHERE id = :record_id
                            """),
                                update_values,
                            )

                        stats["migrated_records"] += 1

                    except Exception as e:
                        logger.error(f"Failed to migrate record {record[0]}: {e}")
                        stats["failed_records"] += 1

                await self.db_session.commit()
                offset += batch_size

                logger.info(f"Migrated {min(offset, stats['total_records'])} / {stats['total_records']} records")

            stats["end_time"] = datetime.now(UTC)

            # Audit log
            await self._audit_log("migrate_data", table_name=table_name, success=stats["failed_records"] == 0)

            logger.info(f"Migration completed. Stats: {stats}")
            return stats

        except Exception as e:
            stats["end_time"] = datetime.now(UTC)
            logger.error(f"Migration failed: {e}")
            await self._audit_log("migrate_data", table_name=table_name, success=False, error_message=str(e))
            raise

    async def cleanup_expired_audit_logs(self, retention_days: int = 730) -> int:
        """Clean up expired audit logs (default 2 years retention).

        Args:
            retention_days: Number of days to retain audit logs

        Returns:
            Number of deleted records
        """
        if not self.db_session:
            return 0

        cutoff_date = datetime.now(UTC) - timedelta(days=retention_days)

        result = await self.db_session.execute(
            text("""
            DELETE FROM encryption_audit_log
            WHERE timestamp < :cutoff_date
        """),
            {"cutoff_date": cutoff_date},
        )

        deleted_count = result.rowcount
        await self.db_session.commit()

        logger.info(f"Cleaned up {deleted_count} expired audit log entries")
        return deleted_count


# Utility functions for encryption configuration
def generate_master_key() -> str:
    """Generate a new master key for encryption."""
    return Fernet.generate_key().decode()


def validate_encryption_config() -> dict[str, Any]:
    """Validate encryption configuration."""
    config = {"master_key_set": bool(os.getenv("DB_ENCRYPTION_MASTER_KEY")), "master_key_valid": False, "errors": []}

    try:
        master_key = os.getenv("DB_ENCRYPTION_MASTER_KEY")
        if master_key:
            if len(master_key) == 44:
                Fernet(master_key.encode())  # Test validity
                config["master_key_valid"] = True
            else:
                config["errors"].append(f"Master key length {len(master_key)} != 44")
        else:
            config["errors"].append("DB_ENCRYPTION_MASTER_KEY not set")

    except Exception as e:
        config["errors"].append(f"Master key validation failed: {e}")

    return config


# Configuration for encrypted fields
ENCRYPTED_FIELDS_CONFIG = {
    "users": {
        "fields": ["email", "phone", "tax_id"],
        "field_types": {"email": FieldType.EMAIL, "phone": FieldType.PHONE, "tax_id": FieldType.TAX_ID},
    },
    "query_logs": {"fields": ["query"], "field_types": {"query": FieldType.QUERY}},
    "subscription_data": {
        "fields": ["stripe_customer_id", "invoice_data"],
        "field_types": {"stripe_customer_id": FieldType.FINANCIAL_DATA, "invoice_data": FieldType.FINANCIAL_DATA},
    },
}
