"""DEV-443: StudioEmailConfigService — CRUD + Validation for custom SMTP configs.

Handles per-studio SMTP configuration with plan-based gating (Pro/Premium only),
Fernet encryption for passwords, SSRF protection, and connection validation.
See ADR-034 for design rationale.
"""

import ipaddress
import os
import smtplib
import socket
from typing import Any

from cryptography.fernet import Fernet
from sqlalchemy import select

from app.core.logging import logger
from app.models.studio_email_config import StudioEmailConfig
from app.models.user import User
from app.services.database import database_service

ALLOWED_PORTS = {25, 465, 587}
SMTP_TIMEOUT = 10  # seconds
ELIGIBLE_PLANS = {"pro", "premium"}


class StudioEmailConfigService:
    """Service for managing per-user custom SMTP configuration."""

    def __init__(self) -> None:
        key = os.environ.get("SMTP_ENCRYPTION_KEY", "")
        if key:
            self._fernet = Fernet(key.encode() if isinstance(key, str) else key)
        else:
            self._fernet = None

    # --- Encryption helpers ---

    def _encrypt_password(self, password: str) -> str:
        """Encrypt SMTP password using Fernet."""
        if not self._fernet:
            raise RuntimeError("SMTP_ENCRYPTION_KEY non configurata")
        return self._fernet.encrypt(password.encode()).decode()

    def _decrypt_password(self, encrypted: str) -> str:
        """Decrypt SMTP password using Fernet."""
        if not self._fernet:
            raise RuntimeError("SMTP_ENCRYPTION_KEY non configurata")
        return self._fernet.decrypt(encrypted.encode()).decode()

    # --- Plan eligibility ---

    def _check_plan_eligibility(self, user: User) -> bool:
        """Check if user's billing plan allows custom email configuration."""
        return getattr(user, "billing_plan_slug", "base") in ELIGIBLE_PLANS

    # --- SSRF protection ---

    @staticmethod
    def _is_safe_host(host: str) -> bool:
        """Check if SMTP host is safe (not a private/loopback IP)."""
        try:
            addr = ipaddress.ip_address(host)
            return not (addr.is_private or addr.is_loopback or addr.is_reserved)
        except ValueError:
            # It's a hostname, not an IP — resolve and check
            try:
                resolved = socket.gethostbyname(host)
                addr = ipaddress.ip_address(resolved)
                return not (addr.is_private or addr.is_loopback or addr.is_reserved)
            except socket.gaierror:
                # Can't resolve — allow it (will fail at connection time)
                return True

    @staticmethod
    def _is_valid_port(port: int) -> bool:
        """Check if port is in the SMTP allowlist."""
        return port in ALLOWED_PORTS

    # --- CRUD ---

    async def create_or_update_config(self, user: User, data: dict[str, Any]) -> StudioEmailConfig:
        """Create or update SMTP config for a user.

        Args:
            user: The authenticated user
            data: Config data including smtp_host, smtp_port, smtp_username,
                  smtp_password, use_tls, from_email, from_name, reply_to_email

        Returns:
            The created/updated StudioEmailConfig

        Raises:
            ValueError: If plan not eligible, host unsafe, or port invalid
        """
        if not self._check_plan_eligibility(user):
            raise ValueError(
                "Il tuo piano non permette la configurazione email personalizzata. Passa al piano Pro o Premium."
            )

        host = data.get("smtp_host", "")
        port = data.get("smtp_port", 587)

        if not self._is_safe_host(host):
            raise ValueError(f"Host SMTP non valido: {host}")

        if not self._is_valid_port(port):
            raise ValueError(f"Porta SMTP non valida: {port}. Porte consentite: 25, 465, 587")

        encrypted_password = self._encrypt_password(data["smtp_password"])

        async with database_service.get_db() as db:
            query = select(StudioEmailConfig).where(StudioEmailConfig.user_id == user.id)
            result = await db.execute(query)
            existing = result.scalar_one_or_none()

            if existing:
                existing.smtp_host = host
                existing.smtp_port = port
                existing.smtp_username = data.get("smtp_username", "")
                existing.smtp_password_encrypted = encrypted_password
                existing.use_tls = data.get("use_tls", True)
                existing.from_email = data.get("from_email", "")
                existing.from_name = data.get("from_name", "")
                existing.reply_to_email = data.get("reply_to_email")
                existing.is_verified = False  # Re-verify on update
                config = existing
            else:
                config = StudioEmailConfig(
                    user_id=user.id,
                    smtp_host=host,
                    smtp_port=port,
                    smtp_username=data.get("smtp_username", ""),
                    smtp_password_encrypted=encrypted_password,
                    use_tls=data.get("use_tls", True),
                    from_email=data.get("from_email", ""),
                    from_name=data.get("from_name", ""),
                    reply_to_email=data.get("reply_to_email"),
                )
                db.add(config)

            await db.commit()

        logger.info(
            "studio_email_config_saved",
            user_id=user.id,
            smtp_host=host,
            is_update=existing is not None if "existing" in dir() else False,
        )
        return config

    async def get_config(self, user: User) -> dict[str, Any] | None:
        """Get SMTP config for a user with password redacted.

        Returns:
            Dict with config fields (password replaced by has_password flag),
            or None if no config exists.
        """
        async with database_service.get_db() as db:
            query = select(StudioEmailConfig).where(StudioEmailConfig.user_id == user.id)
            result = await db.execute(query)
            config = result.scalar_one_or_none()

        if config is None:
            return None

        return {
            "id": config.id,
            "user_id": config.user_id,
            "smtp_host": config.smtp_host,
            "smtp_port": config.smtp_port,
            "smtp_username": config.smtp_username,
            "has_password": bool(config.smtp_password_encrypted),
            "use_tls": config.use_tls,
            "from_email": config.from_email,
            "from_name": config.from_name,
            "reply_to_email": config.reply_to_email,
            "is_verified": config.is_verified,
            "is_active": config.is_active,
            "created_at": config.created_at,
            "updated_at": config.updated_at,
        }

    async def delete_config(self, user: User) -> bool:
        """Delete SMTP config for a user. Reverts to PratikoAI default.

        Returns:
            True if deleted, False if no config existed.
        """
        async with database_service.get_db() as db:
            query = select(StudioEmailConfig).where(StudioEmailConfig.user_id == user.id)
            result = await db.execute(query)
            config = result.scalar_one_or_none()

            if config is None:
                return False

            await db.delete(config)
            await db.commit()

        logger.info("studio_email_config_deleted", user_id=user.id)
        return True

    async def get_raw_config(self, user_id: int) -> StudioEmailConfig | None:
        """Get raw config (including encrypted password) for internal use only.

        Used by EmailService hybrid sending to get the full config.
        """
        async with database_service.get_db() as db:
            query = select(StudioEmailConfig).where(
                StudioEmailConfig.user_id == user_id,
                StudioEmailConfig.is_active == True,  # noqa: E712
                StudioEmailConfig.is_verified == True,  # noqa: E712
            )
            result = await db.execute(query)
            return result.scalar_one_or_none()

    # --- SMTP validation ---

    async def validate_smtp_connection(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        use_tls: bool = True,
    ) -> bool:
        """Validate SMTP connection with EHLO + STARTTLS + LOGIN handshake.

        Does NOT send any email — just verifies credentials.

        Returns:
            True if connection succeeds, False otherwise.
        """
        try:
            with smtplib.SMTP(host, port, timeout=SMTP_TIMEOUT) as server:
                server.ehlo()
                if use_tls:
                    server.starttls()
                    server.ehlo()
                server.login(username, password)
            return True
        except Exception as e:
            logger.warning(
                "smtp_validation_failed",
                host=host,
                port=port,
                error_type=type(e).__name__,
                error_message=str(e),
            )
            return False

    async def verify_config(self, user: User) -> bool:
        """Validate the stored SMTP config and mark as verified if successful.

        Returns:
            True if verification succeeded.
        """
        async with database_service.get_db() as db:
            query = select(StudioEmailConfig).where(StudioEmailConfig.user_id == user.id)
            result = await db.execute(query)
            config = result.scalar_one_or_none()

            if config is None:
                return False

            password = self._decrypt_password(config.smtp_password_encrypted)
            success = await self.validate_smtp_connection(
                host=config.smtp_host,
                port=config.smtp_port,
                username=config.smtp_username,
                password=password,
                use_tls=config.use_tls,
            )

            if success:
                config.is_verified = True
                await db.commit()
                logger.info("studio_email_config_verified", user_id=user.id)

            return success


# Global instance
studio_email_config_service = StudioEmailConfigService()
