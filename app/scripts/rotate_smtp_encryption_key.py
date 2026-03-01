"""DEV-449: SMTP encryption key rotation script.

Re-encrypts all stored SMTP passwords when the Fernet key is rotated.
Accepts old key + new key, decrypts with old, re-encrypts with new,
updates in-place within a single transaction.
Logs count of re-encrypted records (never logs passwords).
"""

import logging

from cryptography.fernet import Fernet
from sqlalchemy import select

from app.models.studio_email_config import StudioEmailConfig
from app.services.database import database_service

logger = logging.getLogger(__name__)


async def rotate_encryption_key(old_key: str, new_key: str) -> int:
    """Re-encrypt all SMTP passwords from old_key to new_key.

    Args:
        old_key: The current Fernet key (base64-encoded)
        new_key: The new Fernet key (base64-encoded)

    Returns:
        Number of records re-encrypted

    Raises:
        Exception: If any decryption fails (transaction is rolled back)
    """
    old_fernet = Fernet(old_key.encode())
    new_fernet = Fernet(new_key.encode())

    async with database_service.get_db() as db:
        query = select(StudioEmailConfig)
        result = await db.execute(query)
        configs = result.scalars().all()

        if not configs:
            logger.info("rotate_smtp_key_no_records")
            await db.commit()
            return 0

        for config in configs:
            # Decrypt with old key — will raise if old_key is wrong
            plaintext = old_fernet.decrypt(config.smtp_password_encrypted.encode()).decode()
            # Re-encrypt with new key
            config.smtp_password_encrypted = new_fernet.encrypt(plaintext.encode()).decode()

        await db.commit()

    count = len(configs)
    logger.info("rotate_smtp_key_completed count=%d", count)
    return count
