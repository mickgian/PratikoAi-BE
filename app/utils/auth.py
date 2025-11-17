"""This file contains the authentication utilities for the application."""

import re
from datetime import (
    UTC,
    datetime,
    timedelta,
)
from typing import Optional

from jose import (
    JWTError,
    jwt,
)

from app.core.config import settings
from app.core.logging import logger
from app.schemas.auth import Token
from app.utils.sanitization import sanitize_string


def create_access_token(thread_id: str, expires_delta: timedelta | None = None) -> Token:
    """Create a new access token for a thread.

    Creates a JWT access token with a 2-hour expiration time by default.
    Used for authenticating API requests.

    Args:
        thread_id: The unique thread ID for the conversation.
        expires_delta: Optional expiration time delta. If not provided, defaults to 2 hours.

    Returns:
        Token: The generated access token with expiration timestamp.
    """
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        # Access tokens expire in 2 hours for improved security
        expire = datetime.now(UTC) + timedelta(hours=settings.JWT_ACCESS_TOKEN_EXPIRE_HOURS)

    to_encode = {
        "sub": thread_id,
        "exp": expire,
        "iat": datetime.now(UTC),
        "jti": sanitize_string(f"{thread_id}-{datetime.now(UTC).timestamp()}"),  # Add unique token identifier
    }

    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    logger.info("access_token_created", thread_id=thread_id, expires_at=expire.isoformat())

    return Token(access_token=encoded_jwt, expires_at=expire)


def create_refresh_token(user_id: int, expires_delta: timedelta | None = None) -> Token:
    """Create a new refresh token for a user.

    Creates a JWT refresh token with a 7-day expiration time by default.
    Used for obtaining new access tokens without re-authentication.

    Args:
        user_id: The unique user ID.
        expires_delta: Optional expiration time delta. If not provided, defaults to 7 days.

    Returns:
        Token: The generated refresh token with expiration timestamp.
    """
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        # Refresh tokens expire in 7 days for good user experience
        expire = datetime.now(UTC) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "refresh",  # Mark this as a refresh token
        "jti": sanitize_string(f"refresh-{user_id}-{datetime.now(UTC).timestamp()}"),  # Unique token identifier
    }

    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    logger.info("refresh_token_created", user_id=user_id, expires_at=expire.isoformat())

    return Token(access_token=encoded_jwt, expires_at=expire)


def verify_token(token: str) -> str | None:
    """Verify a JWT access token and return the thread ID.

    Verifies the token signature, expiration, and format.
    Only accepts access tokens (not refresh tokens).

    Args:
        token: The JWT token to verify.

    Returns:
        Optional[str]: The thread ID if token is valid, None otherwise.

    Raises:
        ValueError: If the token format is invalid
    """
    if not token or not isinstance(token, str):
        logger.warning("token_invalid_format")
        raise ValueError("Token must be a non-empty string")

    # Basic format validation before attempting decode
    # JWT tokens consist of 3 base64url-encoded segments separated by dots
    if not re.match(r"^[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+$", token):
        logger.warning("token_suspicious_format")
        raise ValueError("Token format is invalid - expected JWT format")

    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

        # Ensure this is not a refresh token
        token_type = payload.get("type")
        if token_type == "refresh":
            logger.warning("refresh_token_used_as_access_token")
            return None

        thread_id: str = payload.get("sub")
        if thread_id is None:
            logger.warning("token_missing_thread_id")
            return None

        logger.info("access_token_verified", thread_id=thread_id)
        return thread_id

    except JWTError as e:
        logger.error("access_token_verification_failed", error=str(e))
        return None


def verify_refresh_token(token: str) -> int | None:
    """Verify a JWT refresh token and return the user ID.

    Verifies the token signature, expiration, and ensures it's a refresh token.
    Used for validating refresh tokens when requesting new access tokens.

    Args:
        token: The JWT refresh token to verify.

    Returns:
        Optional[int]: The user ID if refresh token is valid, None otherwise.

    Raises:
        ValueError: If the token format is invalid
    """
    if not token or not isinstance(token, str):
        logger.warning("refresh_token_invalid_format")
        raise ValueError("Token must be a non-empty string")

    # Basic format validation before attempting decode
    # JWT tokens consist of 3 base64url-encoded segments separated by dots
    if not re.match(r"^[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+$", token):
        logger.warning("refresh_token_suspicious_format")
        raise ValueError("Token format is invalid - expected JWT format")

    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

        # Ensure this is a refresh token
        token_type = payload.get("type")
        if token_type != "refresh":
            logger.warning("access_token_used_as_refresh_token")
            return None

        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            logger.warning("refresh_token_missing_user_id")
            return None

        try:
            user_id = int(user_id_str)
        except ValueError:
            logger.warning("refresh_token_invalid_user_id", user_id_str=user_id_str)
            return None

        logger.info("refresh_token_verified", user_id=user_id)
        return user_id

    except JWTError as e:
        logger.error("refresh_token_verification_failed", error=str(e))
        return None
