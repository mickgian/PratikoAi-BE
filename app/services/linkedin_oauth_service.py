"""LinkedIn OAuth service for handling authentication flow."""

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


class LinkedInOAuthService:
    """Service for handling LinkedIn OAuth authentication flow."""

    def __init__(self):
        """Initialize LinkedIn OAuth service with configuration."""
        self.oauth = OAuth()

        # Register LinkedIn OAuth client
        self.linkedin_client = self.oauth.register(
            name="linkedin",
            client_id=settings.LINKEDIN_CLIENT_ID,
            client_secret=settings.LINKEDIN_CLIENT_SECRET,
            authorize_url="https://www.linkedin.com/oauth/v2/authorization",
            access_token_url="https://www.linkedin.com/oauth/v2/accessToken",
            client_kwargs={"scope": "r_liteprofile r_emailaddress"},
        )

    def get_authorization_url(self, redirect_uri: str) -> str:
        """Generate LinkedIn OAuth authorization URL.

        Args:
            redirect_uri: The callback URL after OAuth completion

        Returns:
            str: Authorization URL for redirecting user to LinkedIn
        """
        try:
            # Build authorization URL manually
            auth_params = {
                "response_type": "code",
                "client_id": settings.LINKEDIN_CLIENT_ID,
                "redirect_uri": redirect_uri,
                "scope": "r_liteprofile r_emailaddress",
                "state": "linkedin_oauth",  # Basic state for CSRF protection
            }

            # Build query string with URL encoding
            from urllib.parse import urlencode

            query_string = urlencode(auth_params)
            authorization_url = f"https://www.linkedin.com/oauth/v2/authorization?{query_string}"

            logger.info("linkedin_oauth_authorization_url_generated", redirect_uri=redirect_uri)
            return authorization_url
        except Exception as e:
            logger.error("linkedin_oauth_authorization_url_error", error=str(e))
            raise HTTPException(status_code=500, detail="Failed to generate LinkedIn OAuth URL")

    async def handle_callback(self, code: str, state: str | None = None) -> dict:
        """Handle LinkedIn OAuth callback and create/authenticate user.

        Args:
            code: Authorization code from LinkedIn
            state: Optional state parameter for CSRF protection

        Returns:
            Dict: User data and tokens
        """
        try:
            # Exchange authorization code for access token
            token_data = await self._exchange_code_for_token(code)

            # Get user profile and email information from LinkedIn
            profile_info = await self._get_profile_info(token_data["access_token"])
            email_info = await self._get_email_info(token_data["access_token"])

            # Combine profile and email data
            user_info = {**profile_info, "email": email_info.get("emailAddress")}

            # Create or get existing user
            user = await self._create_or_get_user(user_info)

            # Generate JWT tokens
            access_token = create_access_token(data={"user_id": user.id})
            refresh_token = create_refresh_token(data={"user_id": user.id})

            # Update user's refresh token
            await database_service.update_user_refresh_token(user.id, refresh_token)

            logger.info("linkedin_oauth_callback_success", user_id=user.id, email=user.email)

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
            logger.error("linkedin_oauth_callback_error", error=str(e))
            raise HTTPException(status_code=500, detail="OAuth authentication failed")

    async def _exchange_code_for_token(self, code: str) -> dict:
        """Exchange authorization code for access token.

        Args:
            code: Authorization code from LinkedIn

        Returns:
            Dict: Token response from LinkedIn
        """
        token_url = "https://www.linkedin.com/oauth/v2/accessToken"

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.OAUTH_REDIRECT_URI,
            "client_id": settings.LINKEDIN_CLIENT_ID,
            "client_secret": settings.LINKEDIN_CLIENT_SECRET,
        }

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data, headers=headers)

            if response.status_code != 200:
                logger.error(
                    "linkedin_oauth_token_exchange_failed", status_code=response.status_code, response=response.text
                )
                raise HTTPException(status_code=400, detail="Failed to exchange code for token")

            return response.json()

    async def _get_profile_info(self, access_token: str) -> dict:
        """Get user profile information from LinkedIn using access token.

        Args:
            access_token: LinkedIn access token

        Returns:
            Dict: User profile information from LinkedIn
        """
        profile_url = "https://api.linkedin.com/v2/people/~"

        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            response = await client.get(profile_url, headers=headers)

            if response.status_code != 200:
                logger.error("linkedin_oauth_profile_failed", status_code=response.status_code, response=response.text)
                raise HTTPException(status_code=400, detail="Failed to get profile info from LinkedIn")

            profile_data = response.json()

            # Extract profile information
            first_name = profile_data.get("localizedFirstName", "")
            last_name = profile_data.get("localizedLastName", "")
            full_name = f"{first_name} {last_name}".strip()

            # Get profile picture
            profile_picture_url = ""
            if "profilePicture" in profile_data:
                display_image = profile_data["profilePicture"].get("displayImage~", {})
                if "elements" in display_image:
                    elements = display_image["elements"]
                    if elements:
                        # Get the largest image
                        largest = max(
                            elements,
                            key=lambda x: (
                                x.get("data", {})
                                .get("com.linkedin.digitalmedia.mediaartifact.StillImage", {})
                                .get("storageSize", {})
                                .get("width", 0)
                            ),
                        )
                        identifiers = largest.get("identifiers", [])
                        if identifiers:
                            profile_picture_url = identifiers[0].get("identifier", "")

            logger.info("linkedin_oauth_profile_retrieved", user_id=profile_data.get("id"))

            return {
                "id": profile_data.get("id"),
                "name": full_name,
                "first_name": first_name,
                "last_name": last_name,
                "picture": profile_picture_url,
            }

    async def _get_email_info(self, access_token: str) -> dict:
        """Get user email information from LinkedIn using access token.

        Args:
            access_token: LinkedIn access token

        Returns:
            Dict: User email information from LinkedIn
        """
        email_url = "https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))"

        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            response = await client.get(email_url, headers=headers)

            if response.status_code != 200:
                logger.error("linkedin_oauth_email_failed", status_code=response.status_code, response=response.text)
                raise HTTPException(status_code=400, detail="Failed to get email info from LinkedIn")

            email_data = response.json()

            # Extract email address
            email_address = ""
            if "elements" in email_data and email_data["elements"]:
                handle = email_data["elements"][0].get("handle~", {})
                email_address = handle.get("emailAddress", "")

            logger.info("linkedin_oauth_email_retrieved", email=email_address)

            return {"emailAddress": email_address}

    async def _create_or_get_user(self, user_info: dict) -> User:
        """Create new user or get existing user from LinkedIn OAuth data.

        Args:
            user_info: User information from LinkedIn

        Returns:
            User: The created or existing user
        """
        linkedin_user_id = user_info["id"]
        email = user_info["email"]
        name = user_info.get("name", "")
        avatar_url = user_info.get("picture", "")

        if not email:
            raise HTTPException(status_code=400, detail="Email address is required for registration")

        with Session(database_service.engine) as session:
            # First, try to find user by LinkedIn provider ID
            existing_user = session.exec(
                select(User).where(User.provider == "linkedin", User.provider_id == linkedin_user_id)
            ).first()

            if existing_user:
                # Update user info in case it changed
                existing_user.name = name
                existing_user.avatar_url = avatar_url
                existing_user.email = email  # Update email in case user changed it in LinkedIn
                session.add(existing_user)
                session.commit()
                session.refresh(existing_user)
                logger.info("linkedin_oauth_user_updated", user_id=existing_user.id, email=email)
                return existing_user

            # Check if a user with this email already exists (from email registration)
            email_user = session.exec(select(User).where(User.email == email)).first()

            if email_user:
                # Link the existing email account to LinkedIn
                if email_user.provider == "email":
                    email_user.provider = "linkedin"
                    email_user.provider_id = linkedin_user_id
                    email_user.name = name or email_user.name
                    email_user.avatar_url = avatar_url or email_user.avatar_url
                    session.add(email_user)
                    session.commit()
                    session.refresh(email_user)
                    logger.info("linkedin_oauth_user_linked", user_id=email_user.id, email=email)
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
                provider="linkedin",
                provider_id=linkedin_user_id,
                hashed_password=None,  # OAuth users don't have passwords
            )

            session.add(new_user)
            session.commit()
            session.refresh(new_user)

            logger.info("linkedin_oauth_user_created", user_id=new_user.id, email=email)
            return new_user

    def is_configured(self) -> bool:
        """Check if LinkedIn OAuth is properly configured.

        Returns:
            bool: True if LinkedIn OAuth is configured, False otherwise
        """
        return bool(settings.LINKEDIN_CLIENT_ID and settings.LINKEDIN_CLIENT_SECRET)


# Create singleton instance
linkedin_oauth_service = LinkedInOAuthService()
