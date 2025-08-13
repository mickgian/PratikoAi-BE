"""Authentication and authorization endpoints for the API.

This module provides endpoints for user registration, login, session management,
and token verification.
"""

import os
import uuid
from typing import List

from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
    Request,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import logger
from app.models.session import Session
from app.models.user import User
from app.schemas.auth import (
    RefreshTokenRequest,
    SessionResponse,
    TokenResponse,
    UserCreate,
    UserResponse,
    OAuthLoginResponse,
    OAuthTokenResponse,
)
from app.services.database import DatabaseService
from app.utils.auth import (
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
    verify_token,
)
from app.utils.sanitization import (
    sanitize_email,
    sanitize_string,
    validate_password_strength,
)
from app.services.google_oauth_service import google_oauth_service
from app.services.linkedin_oauth_service import linkedin_oauth_service

router = APIRouter()
security = HTTPBearer()
db_service = DatabaseService()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """Get the current user ID from the token.

    Args:
        credentials: The HTTP authorization credentials containing the JWT token.

    Returns:
        User: The user extracted from the token.

    Raises:
        HTTPException: If the token is invalid or missing.
    """
    try:
        # Sanitize token
        token = sanitize_string(credentials.credentials)

        user_id = verify_token(token)
        if user_id is None:
            logger.error("invalid_token", token_part=token[:10] + "...")
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Verify user exists in database
        user_id_int = int(user_id)
        user = await db_service.get_user(user_id_int)
        if user is None:
            logger.error("user_not_found", user_id=user_id_int)
            raise HTTPException(
                status_code=404,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user
    except ValueError as ve:
        logger.error("token_validation_failed", error=str(ve), exc_info=True)
        raise HTTPException(
            status_code=422,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_session(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Session:
    """Get the current session ID from the token.

    Args:
        credentials: The HTTP authorization credentials containing the JWT token.

    Returns:
        Session: The session extracted from the token.

    Raises:
        HTTPException: If the token is invalid or missing.
    """
    try:
        # Sanitize token
        token = sanitize_string(credentials.credentials)

        session_id = verify_token(token)
        if session_id is None:
            logger.error("session_id_not_found", token_part=token[:10] + "...")
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Sanitize session_id before using it
        session_id = sanitize_string(session_id)

        # Verify session exists in database
        session = await db_service.get_session(session_id)
        if session is None:
            logger.error("session_not_found", session_id=session_id)
            raise HTTPException(
                status_code=404,
                detail="Session not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return session
    except ValueError as ve:
        logger.error("token_validation_failed", error=str(ve), exc_info=True)
        raise HTTPException(
            status_code=422,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/register", response_model=UserResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["register"][0])
async def register_user(request: Request, user_data: UserCreate):
    """Register a new user.

    Args:
        request: The FastAPI request object for rate limiting.
        user_data: User registration data

    Returns:
        UserResponse: The created user info
    """
    try:
        # Sanitize email
        sanitized_email = sanitize_email(user_data.email)

        # Extract and validate password
        password = user_data.password.get_secret_value()
        validate_password_strength(password)

        # Check if user exists
        if await db_service.get_user_by_email(sanitized_email):
            raise HTTPException(status_code=400, detail="Email already registered")

        # Create user
        user = await db_service.create_user(email=sanitized_email, password=User.hash_password(password))

        # Create both access and refresh tokens for new user
        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(user.id)
        
        # Store refresh token hash in database for validation and revocation
        await db_service.update_user_refresh_token(user.id, refresh_token.access_token)
        
        logger.info("user_registration_success", user_id=user.id, email=sanitized_email)

        return UserResponse(
            id=user.id, 
            email=user.email, 
            access_token=access_token.access_token,
            refresh_token=refresh_token.access_token,
            token_type="bearer",
            expires_at=access_token.expires_at
        )
    except ValueError as ve:
        logger.error("user_registration_validation_failed", error=str(ve), exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["login"][0])
async def login(
    request: Request, username: str = Form(...), password: str = Form(...), grant_type: str = Form(default="password")
):
    """Login a user.

    Args:
        request: The FastAPI request object for rate limiting.
        username: User's email
        password: User's password
        grant_type: Must be "password"

    Returns:
        TokenResponse: Access token information

    Raises:
        HTTPException: If credentials are invalid
    """
    try:
        # Sanitize inputs
        username = sanitize_string(username)
        password = sanitize_string(password)
        grant_type = sanitize_string(grant_type)

        # Verify grant type
        if grant_type != "password":
            raise HTTPException(
                status_code=400,
                detail="Unsupported grant type. Must be 'password'",
            )

        user = await db_service.get_user_by_email(username)
        if not user or not user.verify_password(password):
            raise HTTPException(
                status_code=401,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create both access and refresh tokens
        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(user.id)
        
        # Store refresh token hash in database for validation and revocation
        await db_service.update_user_refresh_token(user.id, refresh_token.access_token)
        
        logger.info("user_login_success", user_id=user.id, email=username)
        
        return TokenResponse(
            access_token=access_token.access_token, 
            refresh_token=refresh_token.access_token,
            token_type="bearer", 
            expires_at=access_token.expires_at
        )
    except ValueError as ve:
        logger.error("login_validation_failed", error=str(ve), exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))


@router.post("/session", response_model=SessionResponse)
async def create_session(user: User = Depends(get_current_user)):
    """Create a new chat session for the authenticated user.

    Args:
        user: The authenticated user

    Returns:
        SessionResponse: The session ID, name, and access token
    """
    try:
        # Generate a unique session ID
        session_id = str(uuid.uuid4())

        # Create session in database
        session = await db_service.create_session(session_id, user.id)

        # Create access token for the session
        token = create_access_token(session_id)

        logger.info(
            "session_created",
            session_id=session_id,
            user_id=user.id,
            name=session.name,
            expires_at=token.expires_at.isoformat(),
        )

        return SessionResponse(session_id=session_id, name=session.name, token=token, created_at=session.created_at)
    except ValueError as ve:
        logger.error("session_creation_validation_failed", error=str(ve), user_id=user.id, exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))


@router.patch("/session/{session_id}/name", response_model=SessionResponse)
async def update_session_name(
    session_id: str, name: str = Form(...), current_session: Session = Depends(get_current_session)
):
    """Update a session's name.

    Args:
        session_id: The ID of the session to update
        name: The new name for the session
        current_session: The current session from auth

    Returns:
        SessionResponse: The updated session information
    """
    try:
        # Sanitize inputs
        sanitized_session_id = sanitize_string(session_id)
        sanitized_name = sanitize_string(name)
        sanitized_current_session = sanitize_string(current_session.id)

        # Verify the session ID matches the authenticated session
        if sanitized_session_id != sanitized_current_session:
            raise HTTPException(status_code=403, detail="Cannot modify other sessions")

        # Update the session name
        session = await db_service.update_session_name(sanitized_session_id, sanitized_name)

        # Create a new token (not strictly necessary but maintains consistency)
        token = create_access_token(sanitized_session_id)

        return SessionResponse(session_id=sanitized_session_id, name=session.name, token=token, created_at=session.created_at)
    except ValueError as ve:
        logger.error("session_update_validation_failed", error=str(ve), session_id=session_id, exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))


@router.delete("/session/{session_id}")
async def delete_session(session_id: str, current_session: Session = Depends(get_current_session)):
    """Delete a session for the authenticated user.

    Args:
        session_id: The ID of the session to delete
        current_session: The current session from auth

    Returns:
        None
    """
    try:
        # Sanitize inputs
        sanitized_session_id = sanitize_string(session_id)
        sanitized_current_session = sanitize_string(current_session.id)

        # Verify the session ID matches the authenticated session
        if sanitized_session_id != sanitized_current_session:
            raise HTTPException(status_code=403, detail="Cannot delete other sessions")

        # Delete the session
        await db_service.delete_session(sanitized_session_id)

        logger.info("session_deleted", session_id=session_id, user_id=current_session.user_id)
    except ValueError as ve:
        logger.error("session_deletion_validation_failed", error=str(ve), session_id=session_id, exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))


@router.get("/sessions", response_model=List[SessionResponse])
async def get_user_sessions(user: User = Depends(get_current_user)):
    """Get all session IDs for the authenticated user.

    Args:
        user: The authenticated user

    Returns:
        List[SessionResponse]: List of session IDs
    """
    try:
        sessions = await db_service.get_user_sessions(user.id)
        return [
            SessionResponse(
                session_id=sanitize_string(session.id),
                name=sanitize_string(session.name),
                token=create_access_token(session.id),
                created_at=session.created_at,
            )
            for session in sessions
        ]
    except ValueError as ve:
        logger.error("get_sessions_validation_failed", user_id=user.id, error=str(ve), exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10 per minute")  # More restrictive rate limit for refresh tokens
async def refresh_access_token(request: Request, refresh_request: RefreshTokenRequest):
    """Exchange a refresh token for a new access token.
    
    This endpoint allows clients to obtain new access tokens without re-authentication.
    The refresh token must be valid and not revoked.
    
    Args:
        request: The FastAPI request object for rate limiting.
        refresh_request: Contains the refresh token to exchange.
        
    Returns:
        TokenResponse: New access token and refresh token pair.
        
    Raises:
        HTTPException: If the refresh token is invalid, expired, or revoked.
    """
    try:
        # Sanitize the refresh token
        refresh_token = sanitize_string(refresh_request.refresh_token)
        
        # Verify the refresh token and get user ID
        user_id = verify_refresh_token(refresh_token)
        if user_id is None:
            logger.warning("invalid_refresh_token", token_part=refresh_token[:10] + "...")
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Get user from database
        user = await db_service.get_user(user_id)
        if user is None:
            logger.error("user_not_found_for_refresh", user_id=user_id)
            raise HTTPException(
                status_code=404,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Verify the refresh token against the stored hash
        if not user.verify_refresh_token(refresh_token):
            logger.warning("refresh_token_hash_mismatch", user_id=user_id)
            raise HTTPException(
                status_code=401,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Create new access and refresh tokens
        new_access_token = create_access_token(str(user_id))
        new_refresh_token = create_refresh_token(user_id)
        
        # Update the stored refresh token hash
        await db_service.update_user_refresh_token(user_id, new_refresh_token.access_token)
        
        logger.info("access_token_refreshed", user_id=user_id)
        
        return TokenResponse(
            access_token=new_access_token.access_token,
            refresh_token=new_refresh_token.access_token,
            token_type="bearer",
            expires_at=new_access_token.expires_at
        )
        
    except ValueError as ve:
        logger.error("refresh_token_validation_failed", error=str(ve), exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))


@router.post("/logout")
@limiter.limit("20 per minute")  # Allow reasonable logout frequency
async def logout_user(request: Request, user: User = Depends(get_current_user)):
    """Logout a user by revoking their refresh token.
    
    This endpoint revokes the user's refresh token, effectively logging them out
    from all devices. Access tokens will remain valid until they expire (2 hours).
    
    Args:
        request: The FastAPI request object for rate limiting.
        user: The authenticated user from the access token.
        
    Returns:
        dict: Success message confirming logout.
    """
    try:
        # Revoke the user's refresh token
        success = await db_service.revoke_user_refresh_token(user.id)
        
        if not success:
            logger.error("logout_failed_user_not_found", user_id=user.id)
            raise HTTPException(status_code=404, detail="User not found")
            
        logger.info("user_logged_out", user_id=user.id, email=user.email)
        
        return {"message": "Successfully logged out"}
        
    except Exception as e:
        logger.error("logout_failed", user_id=user.id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Logout failed")


# OAuth Endpoints

@router.get("/google/login", response_model=OAuthLoginResponse)
@limiter.limit("20 per minute")
async def google_login(request: Request):
    """Initiate Google OAuth login flow.
    
    Redirects the user to Google's OAuth authorization page.
    
    Args:
        request: The FastAPI request object for rate limiting.
        
    Returns:
        dict: Authorization URL for redirecting to Google OAuth.
        
    Raises:
        HTTPException: If Google OAuth is not configured or redirect fails.
    """
    try:
        if not google_oauth_service.is_configured():
            logger.error("google_oauth_not_configured")
            raise HTTPException(
                status_code=500, 
                detail="Google OAuth is not configured. Please contact administrator."
            )
            
        # Generate authorization URL with frontend callback endpoint
        # For development, use localhost:3000, for production use the configured frontend URL
        frontend_base_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        redirect_uri = f"{frontend_base_url}/auth/callback"
        auth_url = google_oauth_service.get_authorization_url(redirect_uri)
        
        logger.info("google_oauth_login_initiated", redirect_uri=redirect_uri)
        
        return OAuthLoginResponse(authorization_url=auth_url)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("google_oauth_login_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to initiate Google OAuth")


@router.get("/google/callback")
@limiter.limit("20 per minute")
async def google_callback(request: Request, code: str, state: str = None):
    """Handle Google OAuth callback.
    
    Processes the authorization code from Google and creates or authenticates the user.
    
    Args:
        request: The FastAPI request object for rate limiting.
        code: Authorization code from Google OAuth.
        state: Optional state parameter for CSRF protection.
        
    Returns:
        TokenResponse: User authentication tokens.
        
    Raises:
        HTTPException: If OAuth callback processing fails.
    """
    try:
        if not google_oauth_service.is_configured():
            logger.error("google_oauth_not_configured")
            raise HTTPException(
                status_code=500,
                detail="Google OAuth is not configured. Please contact administrator."
            )
        
        # Sanitize inputs
        code = sanitize_string(code)
        if state:
            state = sanitize_string(state)
            
        # Handle OAuth callback
        result = await google_oauth_service.handle_callback(code, state)
        
        logger.info("google_oauth_callback_success", user_id=result["user"]["id"])
        
        # Return in the same format as regular login
        return TokenResponse(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"], 
            token_type=result["token_type"],
            expires_at=None  # Will be set by token creation
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("google_oauth_callback_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Google OAuth authentication failed")


@router.get("/linkedin/login", response_model=OAuthLoginResponse)
@limiter.limit("20 per minute")
async def linkedin_login(request: Request):
    """Initiate LinkedIn OAuth login flow.
    
    Redirects the user to LinkedIn's OAuth authorization page.
    
    Args:
        request: The FastAPI request object for rate limiting.
        
    Returns:
        dict: Authorization URL for redirecting to LinkedIn OAuth.
        
    Raises:
        HTTPException: If LinkedIn OAuth is not configured or redirect fails.
    """
    try:
        if not linkedin_oauth_service.is_configured():
            logger.error("linkedin_oauth_not_configured")
            raise HTTPException(
                status_code=500,
                detail="LinkedIn OAuth is not configured. Please contact administrator."
            )
            
        # Generate authorization URL with frontend callback endpoint
        # For development, use localhost:3000, for production use the configured frontend URL
        frontend_base_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        redirect_uri = f"{frontend_base_url}/auth/callback"
        auth_url = linkedin_oauth_service.get_authorization_url(redirect_uri)
        
        logger.info("linkedin_oauth_login_initiated", redirect_uri=redirect_uri)
        
        return OAuthLoginResponse(authorization_url=auth_url)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("linkedin_oauth_login_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to initiate LinkedIn OAuth")


@router.get("/linkedin/callback")
@limiter.limit("20 per minute")
async def linkedin_callback(request: Request, code: str, state: str = None):
    """Handle LinkedIn OAuth callback.
    
    Processes the authorization code from LinkedIn and creates or authenticates the user.
    
    Args:
        request: The FastAPI request object for rate limiting.
        code: Authorization code from LinkedIn OAuth.
        state: Optional state parameter for CSRF protection.
        
    Returns:
        TokenResponse: User authentication tokens.
        
    Raises:
        HTTPException: If OAuth callback processing fails.
    """
    try:
        if not linkedin_oauth_service.is_configured():
            logger.error("linkedin_oauth_not_configured")
            raise HTTPException(
                status_code=500,
                detail="LinkedIn OAuth is not configured. Please contact administrator."
            )
        
        # Sanitize inputs
        code = sanitize_string(code)
        if state:
            state = sanitize_string(state)
            
        # Handle OAuth callback
        result = await linkedin_oauth_service.handle_callback(code, state)
        
        logger.info("linkedin_oauth_callback_success", user_id=result["user"]["id"])
        
        # Return in the same format as regular login
        return TokenResponse(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            token_type=result["token_type"],
            expires_at=None  # Will be set by token creation
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("linkedin_oauth_callback_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="LinkedIn OAuth authentication failed")
