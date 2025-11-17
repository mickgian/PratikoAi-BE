"""Request signing system for enhanced API security."""

import hashlib
import hmac
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from fastapi import HTTPException, Request

from app.core.config import settings
from app.core.logging import logger


class RequestSigner:
    """Handles request signing and verification for API security."""

    def __init__(self):
        """Initialize request signer."""
        self.signature_version = "v1"
        self.timestamp_tolerance_seconds = 300  # 5 minutes
        self.signature_header = "X-NormoAI-Signature"
        self.timestamp_header = "X-NormoAI-Timestamp"

    def generate_signature(self, method: str, path: str, body: bytes, timestamp: str, secret_key: str) -> str:
        """Generate HMAC signature for request.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: Request path
            body: Request body bytes
            timestamp: Unix timestamp string
            secret_key: Secret key for signing

        Returns:
            Base64 encoded signature
        """
        try:
            # Create canonical string
            canonical_string = f"{method}\n{path}\n{timestamp}\n"

            # Add body hash if present
            if body:
                body_hash = hashlib.sha256(body).hexdigest()
                canonical_string += body_hash

            # Generate HMAC signature
            signature = hmac.new(
                secret_key.encode("utf-8"), canonical_string.encode("utf-8"), hashlib.sha256
            ).hexdigest()

            logger.debug(
                "request_signature_generated",
                method=method,
                path=path,
                timestamp=timestamp,
                signature_prefix=signature[:8] + "...",
            )

            return f"{self.signature_version}={signature}"

        except Exception as e:
            logger.error("signature_generation_failed", method=method, path=path, error=str(e), exc_info=True)
            raise ValueError(f"Signature generation failed: {str(e)}")

    def verify_signature(
        self, method: str, path: str, body: bytes, timestamp: str, signature: str, secret_key: str
    ) -> bool:
        """Verify request signature.

        Args:
            method: HTTP method
            path: Request path
            body: Request body bytes
            timestamp: Timestamp from request
            signature: Signature from request
            secret_key: Secret key for verification

        Returns:
            True if signature is valid
        """
        try:
            # Check timestamp validity
            if not self._is_timestamp_valid(timestamp):
                logger.warning(
                    "signature_verification_failed_timestamp",
                    timestamp=timestamp,
                    current_time=datetime.utcnow().isoformat(),
                )
                return False

            # Generate expected signature
            expected_signature = self.generate_signature(method, path, body, timestamp, secret_key)

            # Compare signatures (constant time comparison)
            is_valid = hmac.compare_digest(signature, expected_signature)

            if is_valid:
                logger.debug("signature_verified_successfully", method=method, path=path, timestamp=timestamp)
            else:
                logger.warning(
                    "signature_verification_failed",
                    method=method,
                    path=path,
                    timestamp=timestamp,
                    expected_prefix=expected_signature[:12] + "...",
                    received_prefix=signature[:12] + "...",
                )

            return is_valid

        except Exception as e:
            logger.error("signature_verification_error", method=method, path=path, error=str(e), exc_info=True)
            return False

    def _is_timestamp_valid(self, timestamp_str: str) -> bool:
        """Check if timestamp is within acceptable range.

        Args:
            timestamp_str: Unix timestamp string

        Returns:
            True if timestamp is valid
        """
        try:
            timestamp = int(timestamp_str)
            current_time = int(datetime.utcnow().timestamp())

            # Check if timestamp is within tolerance
            time_diff = abs(current_time - timestamp)

            return time_diff <= self.timestamp_tolerance_seconds

        except (ValueError, TypeError):
            return False

    async def sign_outgoing_request(
        self, method: str, url: str, body: bytes | None = None, secret_key: str | None = None
    ) -> dict[str, str]:
        """Sign an outgoing request with headers.

        Args:
            method: HTTP method
            url: Full URL
            body: Request body bytes
            secret_key: Secret key (uses default if not provided)

        Returns:
            Dictionary of headers to add to request
        """
        try:
            # Extract path from URL
            from urllib.parse import urlparse

            parsed_url = urlparse(url)
            path = parsed_url.path + ("?" + parsed_url.query if parsed_url.query else "")

            # Use default secret if not provided
            if secret_key is None:
                secret_key = settings.JWT_SECRET_KEY

            # Generate timestamp
            timestamp = str(int(datetime.utcnow().timestamp()))

            # Generate signature
            signature = self.generate_signature(method, path, body or b"", timestamp, secret_key)

            headers = {self.signature_header: signature, self.timestamp_header: timestamp}

            logger.debug("outgoing_request_signed", method=method, path=path, timestamp=timestamp)

            return headers

        except Exception as e:
            logger.error("outgoing_request_signing_failed", method=method, url=url, error=str(e), exc_info=True)
            return {}

    def create_webhook_signature(self, payload: bytes, secret: str) -> str:
        """Create signature for webhook payloads (like Stripe).

        Args:
            payload: Webhook payload bytes
            secret: Webhook secret

        Returns:
            Signature string
        """
        try:
            signature = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()

            return f"sha256={signature}"

        except Exception as e:
            logger.error("webhook_signature_creation_failed", error=str(e), exc_info=True)
            raise ValueError(f"Webhook signature creation failed: {str(e)}")

    def verify_webhook_signature(self, payload: bytes, signature_header: str, secret: str) -> bool:
        """Verify webhook signature.

        Args:
            payload: Webhook payload bytes
            signature_header: Signature from header
            secret: Webhook secret

        Returns:
            True if signature is valid
        """
        try:
            expected_signature = self.create_webhook_signature(payload, secret)

            # Handle multiple signatures (some webhooks send multiple)
            signatures = signature_header.split(",")

            for sig in signatures:
                sig = sig.strip()
                if hmac.compare_digest(sig, expected_signature):
                    logger.debug("webhook_signature_verified_successfully")
                    return True

            logger.warning(
                "webhook_signature_verification_failed",
                expected_prefix=expected_signature[:12] + "...",
                received_signatures=[s.strip()[:12] + "..." for s in signatures],
            )

            return False

        except Exception as e:
            logger.error("webhook_signature_verification_error", error=str(e), exc_info=True)
            return False


# Global instance
request_signer = RequestSigner()


async def verify_request_signature(request: Request) -> bool:
    """FastAPI dependency for request signature verification.

    Args:
        request: FastAPI request object

    Returns:
        True if signature is valid

    Raises:
        HTTPException: If signature is invalid or missing
    """
    try:
        # Get required headers
        signature = request.headers.get(request_signer.signature_header)
        timestamp = request.headers.get(request_signer.timestamp_header)

        if not signature or not timestamp:
            logger.warning(
                "missing_signature_headers",
                has_signature=bool(signature),
                has_timestamp=bool(timestamp),
                path=str(request.url.path),
            )
            raise HTTPException(status_code=401, detail="Missing signature headers")

        # Get request body
        body = await request.body()

        # Verify signature
        is_valid = request_signer.verify_signature(
            method=request.method,
            path=str(request.url.path),
            body=body,
            timestamp=timestamp,
            signature=signature,
            secret_key=settings.JWT_SECRET_KEY,
        )

        if not is_valid:
            logger.warning(
                "request_signature_invalid",
                method=request.method,
                path=str(request.url.path),
                client_ip=request.client.host if request.client else "unknown",
            )
            raise HTTPException(status_code=401, detail="Invalid request signature")

        logger.debug("request_signature_verified", method=request.method, path=str(request.url.path))

        return True

    except HTTPException:
        raise
    except Exception as e:
        logger.error("signature_verification_dependency_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Signature verification failed")
