"""Google OAuth service for handling authentication flow."""

import logging
from typing import Dict, Optional

import httpx
from authlib.integrations.starlette_client import OAuth
from fastapi import HTTPException
from sqlmodel import Session, select

from app.core.config import settings
from app.models.user import User
from app.services.database import database_service
from app.utils.auth import create_access_token, create_refresh_token

logger = logging.getLogger(__name__)


class GoogleOAuthService:
    """Service for handling Google OAuth authentication flow."""

    def __init__(self):
        """Initialize Google OAuth service with configuration."""
        self.oauth = OAuth()

        # Register Google OAuth client
        self.google_client = self.oauth.register(
            name="google",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            authorize_url="https://accounts.google.com/o/oauth2/auth",
            access_token_url="https://oauth2.googleapis.com/token",
            userinfo_endpoint="https://www.googleapis.com/oauth2/v2/userinfo",
            client_kwargs={"scope": "openid email profile"},
        )

    def get_authorization_url(self, redirect_uri: str) -> str:
        """Generate Google OAuth authorization URL.

        Args:
            redirect_uri: The callback URL after OAuth completion

        Returns:
            str: Authorization URL for redirecting user to Google
        """
        try:
            # Build authorization URL manually since authlib's authorize_redirect is for ASGI apps
            auth_params = {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "redirect_uri": redirect_uri,
                "scope": "openid email profile",
                "response_type": "code",
                "access_type": "offline",
                "prompt": "consent",
            }

            # Build query string with URL encoding
            from urllib.parse import urlencode

            query_string = urlencode(auth_params)
            authorization_url = f"https://accounts.google.com/o/oauth2/auth?{query_string}"

            logger.info("google_oauth_authorization_url_generated", redirect_uri=redirect_uri)
            return authorization_url
        except Exception as e:
            logger.error("google_oauth_authorization_url_error", error=str(e))
            raise HTTPException(status_code=500, detail="Failed to generate Google OAuth URL")

    async def handle_callback(self, code: str, state: str | None = None) -> dict:
        """Handle Google OAuth callback and create/authenticate user.

        Args:
            code: Authorization code from Google
            state: Optional state parameter for CSRF protection

        Returns:
            Dict: User data and tokens
        """
        try:
            # Exchange authorization code for access token
            token_data = await self._exchange_code_for_token(code)

            # Get user information from Google
            user_info = await self._get_user_info(token_data["access_token"])

            # Create or get existing user
            user = await self._create_or_get_user(user_info)

            # Generate JWT tokens
            access_token = create_access_token(data={"user_id": user.id})
            refresh_token = create_refresh_token(data={"user_id": user.id})

            # Update user's refresh token
            await database_service.update_user_refresh_token(user.id, refresh_token)

            logger.info("google_oauth_callback_success", user_id=user.id, email=user.email)

            return {
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "avatar_url": user.avatar_url,
                    "provider": user.provider,
                },
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error("google_oauth_callback_error", error=str(e))
            raise HTTPException(status_code=500, detail="OAuth authentication failed")

    async def _exchange_code_for_token(self, code: str) -> dict:
        """Exchange authorization code for access token.

        Args:
            code: Authorization code from Google

        Returns:
            Dict: Token response from Google
        """
        token_url = "https://oauth2.googleapis.com/token"

        data = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": settings.OAUTH_REDIRECT_URI,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data)

            if response.status_code != 200:
                logger.error(
                    "google_oauth_token_exchange_failed", status_code=response.status_code, response=response.text
                )
                raise HTTPException(status_code=400, detail="Failed to exchange code for token")

            return response.json()

    async def _get_user_info(self, access_token: str) -> dict:
        """Get user information from Google using access token.

        Args:
            access_token: Google access token

        Returns:
            Dict: User information from Google
        """
        userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"

        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            response = await client.get(userinfo_url, headers=headers)

            if response.status_code != 200:
                logger.error("google_oauth_userinfo_failed", status_code=response.status_code, response=response.text)
                raise HTTPException(status_code=400, detail="Failed to get user info from Google")

            user_info = response.json()
            logger.info("google_oauth_userinfo_retrieved", user_id=user_info.get("id"))

            return user_info

    async def _create_or_get_user(self, user_info: dict) -> User:
        """Create new user or get existing user from Google OAuth data.

        Args:
            user_info: User information from Google

        Returns:
            User: The created or existing user
        """
        google_user_id = user_info["id"]
        email = user_info["email"]
        name = user_info.get("name", "")
        avatar_url = user_info.get("picture", "")

        with Session(database_service.engine) as session:
            # First, try to find user by Google provider ID
            existing_user = session.exec(
                select(User).where(User.provider == "google", User.provider_id == google_user_id)
            ).first()

            if existing_user:
                # Update user info in case it changed
                existing_user.name = name
                existing_user.avatar_url = avatar_url
                existing_user.email = email  # Update email in case user changed it in Google
                session.add(existing_user)
                session.commit()
                session.refresh(existing_user)
                logger.info("google_oauth_user_updated", user_id=existing_user.id, email=email)
                return existing_user

            # Check if a user with this email already exists (from email registration)
            email_user = session.exec(select(User).where(User.email == email)).first()

            if email_user:
                # Link the existing email account to Google
                if email_user.provider == "email":
                    email_user.provider = "google"
                    email_user.provider_id = google_user_id
                    email_user.name = name or email_user.name
                    email_user.avatar_url = avatar_url or email_user.avatar_url
                    session.add(email_user)
                    session.commit()
                    session.refresh(email_user)
                    logger.info("google_oauth_user_linked", user_id=email_user.id, email=email)
                    return email_user
                else:
                    # User already exists with different OAuth provider
                    raise HTTPException(
                        status_code=409,
                        detail=f"An account with email {email} already exists with a different provider",
                    )

            # Create new user
            new_user = User(
                email=email,
                name=name,
                avatar_url=avatar_url,
                provider="google",
                provider_id=google_user_id,
                hashed_password=None,  # OAuth users don't have passwords
            )

            session.add(new_user)
            session.commit()
            session.refresh(new_user)

            logger.info("google_oauth_user_created", user_id=new_user.id, email=email)
            return new_user

    def is_configured(self) -> bool:
        """Check if Google OAuth is properly configured.

        Returns:
            bool: True if Google OAuth is configured, False otherwise
        """
        return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)


# Create singleton instance
google_oauth_service = GoogleOAuthService()
