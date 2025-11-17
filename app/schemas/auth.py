"""This file contains the authentication schema for the application."""

import re
from datetime import datetime
from typing import Optional

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    SecretStr,
    field_validator,
)


class Token(BaseModel):
    """Token model for authentication.

    Attributes:
        access_token: The JWT access token.
        token_type: The type of token (always "bearer").
        expires_at: The token expiration timestamp.
    """

    access_token: str = Field(..., description="The JWT access token")
    token_type: str = Field(default="bearer", description="The type of token")
    expires_at: datetime = Field(..., description="The token expiration timestamp")


class TokenResponse(BaseModel):
    """Response model for login endpoint.

    Attributes:
        access_token: The JWT access token
        refresh_token: The JWT refresh token for obtaining new access tokens
        token_type: The type of token (always "bearer")
        expires_at: When the access token expires
    """

    access_token: str = Field(..., description="The JWT access token")
    refresh_token: str = Field(..., description="The JWT refresh token for obtaining new access tokens")
    token_type: str = Field(default="bearer", description="The type of token")
    expires_at: datetime = Field(..., description="When the access token expires")


class RefreshTokenRequest(BaseModel):
    """Request model for refresh token endpoint.

    Attributes:
        refresh_token: The refresh token to exchange for a new access token
    """

    refresh_token: str = Field(..., description="The refresh token to exchange for a new access token")


class UserCreate(BaseModel):
    """Request model for user registration.

    Attributes:
        email: User's email address
        password: User's password
    """

    email: EmailStr = Field(..., description="User's email address")
    password: SecretStr = Field(..., description="User's password", min_length=8, max_length=64)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: SecretStr) -> SecretStr:
        """Validate password strength.

        Args:
            v: The password to validate

        Returns:
            SecretStr: The validated password

        Raises:
            ValueError: If the password is not strong enough
        """
        password = v.get_secret_value()

        # Check for common password requirements
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")

        if not re.search(r"[A-Z]", password):
            raise ValueError("Password must contain at least one uppercase letter")

        if not re.search(r"[a-z]", password):
            raise ValueError("Password must contain at least one lowercase letter")

        if not re.search(r"[0-9]", password):
            raise ValueError("Password must contain at least one number")

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValueError("Password must contain at least one special character")

        return v


class UserResponse(BaseModel):
    """Response model for user operations.

    Attributes:
        id: User's ID
        email: User's email address
        access_token: The JWT access token
        refresh_token: The JWT refresh token for obtaining new access tokens
        token_type: The type of token (always "bearer")
        expires_at: When the access token expires
    """

    id: int = Field(..., description="User's ID")
    email: str = Field(..., description="User's email address")
    access_token: str = Field(..., description="The JWT access token")
    refresh_token: str = Field(..., description="The JWT refresh token for obtaining new access tokens")
    token_type: str = Field(default="bearer", description="The type of token")
    expires_at: datetime = Field(..., description="When the access token expires")


class SessionResponse(BaseModel):
    """Response model for session creation.

    Attributes:
        session_id: The unique identifier for the chat session
        name: Name of the session (defaults to empty string)
        token: The authentication token for the session
        created_at: When the session was created
    """

    session_id: str = Field(..., description="The unique identifier for the chat session")
    name: str = Field(default="", description="Name of the session", max_length=100)
    token: Token = Field(..., description="The authentication token for the session")
    created_at: datetime = Field(..., description="When the session was created")

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        """Sanitize the session name.

        Args:
            v: The name to sanitize

        Returns:
            str: The sanitized name
        """
        # Remove only dangerous HTML/script characters, keep apostrophes and quotes for natural text
        sanitized = re.sub(r"[<>{}[\]()]", "", v)
        # Decode HTML entities - may need multiple passes for double-encoded entities
        import html

        # First pass - decode standard entities
        sanitized = html.unescape(sanitized)
        # Second pass - handle cases like &amp;#x27; -> &#x27; -> '
        sanitized = html.unescape(sanitized)
        return sanitized


# OAuth-specific schema models


class OAuthLoginResponse(BaseModel):
    """Response model for OAuth login initiation.

    Attributes:
        authorization_url: The URL to redirect the user to for OAuth authorization
    """

    authorization_url: str = Field(..., description="The URL to redirect the user to for OAuth authorization")


class OAuthUserInfo(BaseModel):
    """User information from OAuth provider.

    Attributes:
        id: User's ID in the application
        email: User's email address
        name: User's full name from OAuth provider
        avatar_url: URL to user's profile picture
        provider: Authentication provider ('google' or 'linkedin')
    """

    id: int = Field(..., description="User's ID in the application")
    email: str = Field(..., description="User's email address")
    name: str | None = Field(None, description="User's full name from OAuth provider")
    avatar_url: str | None = Field(None, description="URL to user's profile picture")
    provider: str = Field(..., description="Authentication provider ('email', 'google', or 'linkedin')")


class OAuthTokenResponse(BaseModel):
    """Response model for OAuth authentication completion.

    Attributes:
        user: User information from OAuth provider
        access_token: The JWT access token
        refresh_token: The JWT refresh token for obtaining new access tokens
        token_type: The type of token (always "bearer")
    """

    user: OAuthUserInfo = Field(..., description="User information from OAuth provider")
    access_token: str = Field(..., description="The JWT access token")
    refresh_token: str = Field(..., description="The JWT refresh token for obtaining new access tokens")
    token_type: str = Field(default="bearer", description="The type of token")


class EnhancedUserResponse(BaseModel):
    """Enhanced user response model that includes OAuth provider information.

    This extends the basic UserResponse with OAuth-specific fields.

    Attributes:
        id: User's ID
        email: User's email address
        name: User's full name (from OAuth or manual registration)
        avatar_url: URL to user's profile picture (from OAuth)
        provider: Authentication provider ('email', 'google', or 'linkedin')
        access_token: The JWT access token
        refresh_token: The JWT refresh token
        token_type: The type of token (always "bearer")
        expires_at: When the access token expires
    """

    id: int = Field(..., description="User's ID")
    email: str = Field(..., description="User's email address")
    name: str | None = Field(None, description="User's full name")
    avatar_url: str | None = Field(None, description="URL to user's profile picture")
    provider: str = Field(default="email", description="Authentication provider")
    access_token: str = Field(..., description="The JWT access token")
    refresh_token: str = Field(..., description="The JWT refresh token")
    token_type: str = Field(default="bearer", description="The type of token")
    expires_at: datetime = Field(..., description="When the access token expires")
