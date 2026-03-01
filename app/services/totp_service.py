"""TOTP 2FA service for generating and verifying authenticator codes (P2)."""

import hashlib
import json
import secrets

import pyotp

from app.core.logging import logger


class TOTPService:
    """Service for TOTP-based two-factor authentication."""

    ISSUER_NAME = "PratikoAI"
    BACKUP_CODE_COUNT = 8

    def generate_secret(self) -> str:
        """Generate a new TOTP secret (base32-encoded, 32 chars)."""
        return pyotp.random_base32()

    def get_provisioning_uri(self, secret: str, email: str) -> str:
        """Generate a provisioning URI for QR code scanning.

        Args:
            secret: The TOTP secret (base32)
            email: User's email for display in the authenticator app

        Returns:
            otpauth:// URI for QR code generation
        """
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=email, issuer_name=self.ISSUER_NAME)

    def verify_code(self, secret: str, code: str) -> bool:
        """Verify a TOTP code against the secret.

        Allows a 30-second window of tolerance (valid_window=1).

        Args:
            secret: The TOTP secret (base32)
            code: The 6-digit code from the authenticator app

        Returns:
            True if the code is valid
        """
        if not code or len(code) != 6 or not code.isdigit():
            return False
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=1)

    def generate_backup_codes(self, count: int | None = None) -> list[str]:
        """Generate one-time backup codes for account recovery.

        Format: xxxx-xxxx (lowercase alphanumeric).

        Returns:
            List of backup code strings
        """
        n = count or self.BACKUP_CODE_COUNT
        codes = []
        for _ in range(n):
            raw = secrets.token_hex(4)  # 8 hex chars
            codes.append(f"{raw[:4]}-{raw[4:]}")
        return codes

    def generate_email_otp(self) -> str:
        """Generate a 6-digit OTP code for email-based fallback 2FA."""
        return f"{secrets.randbelow(1000000):06d}"

    def hash_backup_codes(self, codes: list[str]) -> str:
        """Serialize backup codes for storage.

        Stores as JSON so individual codes can be verified and consumed.

        Args:
            codes: List of backup code strings

        Returns:
            JSON-serialized string of codes
        """
        return json.dumps(sorted(codes))

    def verify_backup_code(self, code: str, codes_json: str) -> bool:
        """Verify a backup code against the stored list.

        Args:
            code: The backup code to verify
            codes_json: JSON-serialized list of remaining backup codes

        Returns:
            True if the code is in the list
        """
        try:
            codes = json.loads(codes_json)
            return code in codes
        except (json.JSONDecodeError, TypeError):
            logger.error("backup_code_verify_invalid_json")
            return False

    def consume_backup_code(self, code: str, codes_json: str) -> str | None:
        """Remove a used backup code and return updated JSON.

        Args:
            code: The backup code that was used
            codes_json: JSON-serialized list of remaining backup codes

        Returns:
            Updated JSON string with the code removed, or None on error
        """
        try:
            codes = json.loads(codes_json)
            if code in codes:
                codes.remove(code)
                return json.dumps(sorted(codes))
            return None
        except (json.JSONDecodeError, TypeError):
            logger.error("backup_code_consume_invalid_json")
            return None


# Global instance
totp_service = TOTPService()
