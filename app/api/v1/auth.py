"""Authentication and authorization endpoints for the API.

This module provides endpoints for user registration, login, session management,
token verification, password reset, email verification, and TOTP 2FA.
"""

import asyncio
import os
import secrets
import uuid
from datetime import UTC, datetime, timedelta
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
from app.models.email_verification import EmailVerification
from app.models.login_attempt import LoginAttempt
from app.models.password_reset import PasswordReset
from app.models.session import Session
from app.models.totp_device import TOTPDevice
from app.models.user import User, UserRole
from app.schemas.auth import (
    EmailOTPRequest,
    EmailVerificationRequest,
    LoginResponse,
    MessageResponse,
    OAuthLoginResponse,
    OAuthTokenResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshTokenRequest,
    ResendVerificationRequest,
    SessionResponse,
    TokenResponse,
    TOTPSetupResponse,
    TOTPVerifyRequest,
    TwoFactorBackupRequest,
    TwoFactorVerifyRequest,
    UserCreate,
    UserResponse,
)
from app.services.auth_security_service import auth_security_service
from app.services.database import DatabaseService
from app.services.email_service import email_service
from app.services.google_oauth_service import google_oauth_service
from app.services.linkedin_oauth_service import linkedin_oauth_service
from app.services.totp_service import totp_service
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
        # Support both user tokens (user_id as int) and session tokens (session_id as UUID)
        try:
            # Try parsing as user_id (integer) - original flow
            user_id_int = int(user_id)
            user = await db_service.get_user(user_id_int)
            if user is None:
                logger.error("user_not_found", user_id=user_id_int)
                raise HTTPException(
                    status_code=404,
                    detail="User not found",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except ValueError:
            # Token contains session_id (UUID string) - lookup user via session
            logger.debug("session_token_detected", session_id=user_id)
            session = await db_service.get_session(user_id)
            if session is None:
                logger.error("session_not_found", session_id=user_id)
                raise HTTPException(
                    status_code=404,
                    detail="Session not found",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Get user from session
            user = await db_service.get_user(session.user_id)
            if user is None:
                logger.error("user_not_found_from_session", user_id=session.user_id, session_id=user_id)
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


def _build_qa_role_map() -> dict[str, str]:
    """Build QA role map from environment variables."""
    role_map: dict[str, str] = {}
    stakeholder = os.getenv("STAKEHOLDER_EMAIL")
    stakeholdress = os.getenv("STAKEHOLDRESS_EMAIL")
    if stakeholder:
        role_map[stakeholder] = UserRole.ADMIN.value
    if stakeholdress:
        role_map[stakeholdress] = UserRole.SUPER_USER.value
    return role_map


def _get_qa_role(email: str) -> str | None:
    """Return an elevated role for known QA emails, or None for default."""
    from app.core.config import Environment

    if settings.ENVIRONMENT != Environment.QA:
        return None
    return _build_qa_role_map().get(email)


@router.post("/register", response_model=UserResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["register"][0])
async def register_user(request: Request, user_data: UserCreate):
    """Register a new user with email verification (P0)."""
    try:
        sanitized_email = sanitize_email(user_data.email)
        password = user_data.password.get_secret_value()
        validate_password_strength(password)

        if await db_service.get_user_by_email(sanitized_email):
            raise HTTPException(status_code=400, detail="Email already registered")

        role = _get_qa_role(sanitized_email)
        user = await db_service.create_user(email=sanitized_email, password=User.hash_password(password), role=role)

        if role is not None:
            await db_service.create_expert_profile(user.id)

        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(user.id)
        await db_service.update_user_refresh_token(user.id, refresh_token.access_token)

        logger.info("user_registration_success", user_id=user.id, email=sanitized_email)

        # P0: Create email verification token and send welcome email with verification link
        verification_token = secrets.token_urlsafe(32)
        expires_at = datetime.now(UTC) + timedelta(hours=settings.EMAIL_VERIFICATION_EXPIRE_HOURS)
        await db_service.create_email_verification(user.id, verification_token, expires_at)
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        verification_url = f"{frontend_url}/verify-email?token={verification_token}"

        # P0: Fire-and-forget welcome email WITHOUT plaintext password
        asyncio.create_task(email_service.send_welcome_email(sanitized_email, verification_url=verification_url))

        return UserResponse(
            id=user.id,
            email=user.email,
            access_token=access_token.access_token,
            refresh_token=refresh_token.access_token,
            token_type="bearer",
            expires_at=access_token.expires_at,
        )
    except ValueError as ve:
        logger.error("user_registration_validation_failed", error=str(ve), exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))


@router.post("/login", response_model=LoginResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["login"][0])
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    remember_me: bool = Form(default=False),
    grant_type: str = Form(default="password"),
):
    """Login with account lockout (P1), 2FA challenge (P2), and remember_me (P1)."""
    try:
        username = sanitize_string(username)
        password = sanitize_string(password)
        grant_type = sanitize_string(grant_type)
        ip_address = request.client.host if request.client else ""

        if grant_type != "password":
            raise HTTPException(status_code=400, detail="Unsupported grant type. Must be 'password'")

        user = await db_service.get_user_by_email(username)

        # P1: Check account lockout
        if user and auth_security_service.is_account_locked(user.account_locked_until):
            await db_service.record_login_attempt(
                user_id=user.id, email=username, ip_address=ip_address, success=False, failure_reason="account_locked"
            )
            raise HTTPException(status_code=423, detail="Account temporaneamente bloccato. Riprova più tardi.")

        # Verify credentials
        if not user or not user.verify_password(password):
            # P1/P2: Record failed attempt and check lockout threshold
            if user:
                new_count = user.failed_login_attempts + 1
                locked_until = None
                if auth_security_service.should_lock_account(new_count):
                    duration = auth_security_service.get_lockout_duration(new_count)
                    locked_until = datetime.now(UTC) + duration
                await db_service.update_failed_login_attempts(user.id, new_count, locked_until)
            await db_service.record_login_attempt(
                user_id=user.id if user else None,
                email=username,
                ip_address=ip_address,
                success=False,
                failure_reason="wrong_password",
            )
            raise HTTPException(
                status_code=401,
                detail="Email o password non corretti",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Reset failed attempts on successful password check
        if user.failed_login_attempts > 0:
            await db_service.update_failed_login_attempts(user.id, 0, None)

        # P2: If 2FA is enabled, return challenge instead of tokens
        if user.totp_enabled:
            two_factor_token = create_access_token(
                f"2fa:{user.id}",
                expires_delta=timedelta(minutes=settings.JWT_2FA_TOKEN_EXPIRE_MINUTES),
            )
            await db_service.record_login_attempt(
                user_id=user.id, email=username, ip_address=ip_address, success=False, failure_reason="2fa_pending"
            )
            return LoginResponse(
                requires_2fa=True,
                two_factor_token=two_factor_token.access_token,
            )

        # P1: Use remember_me to determine token expiry
        if remember_me:
            access_token = create_access_token(
                str(user.id), expires_delta=timedelta(hours=settings.JWT_ACCESS_TOKEN_REMEMBER_ME_HOURS)
            )
            refresh_token = create_refresh_token(
                user.id, expires_delta=timedelta(days=settings.JWT_REFRESH_TOKEN_REMEMBER_ME_DAYS)
            )
        else:
            access_token = create_access_token(str(user.id))
            refresh_token = create_refresh_token(user.id)

        await db_service.update_user_refresh_token(user.id, refresh_token.access_token)

        # P2: Record successful login
        await db_service.record_login_attempt(user_id=user.id, email=username, ip_address=ip_address, success=True)

        logger.info("user_login_success", user_id=user.id, email=username)

        return LoginResponse(
            access_token=access_token.access_token,
            refresh_token=refresh_token.access_token,
            token_type="bearer",
            expires_at=access_token.expires_at,
            requires_2fa=False,
        )
    except ValueError as ve:
        logger.error("login_validation_failed", error=str(ve), exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))


# --- P0: Email Verification ---


@router.post("/verify-email", response_model=MessageResponse)
@limiter.limit("10 per hour")
async def verify_email(request: Request, data: EmailVerificationRequest):
    """Verify user email address with token (P0)."""
    token = sanitize_string(data.token)
    verification = await db_service.get_email_verification_by_token(token)

    if not verification or verification.used:
        raise HTTPException(status_code=400, detail="Token di verifica non valido o già utilizzato")

    if verification.is_expired():
        raise HTTPException(status_code=400, detail="Il token di verifica è scaduto")

    await db_service.mark_user_email_verified(verification.user_id)
    await db_service.mark_email_verification_used(verification.id)

    logger.info("email_verified", user_id=verification.user_id)
    return MessageResponse(message="Email verificata con successo")


@router.post("/resend-verification", response_model=MessageResponse)
@limiter.limit("3 per hour")
async def resend_verification(request: Request, data: ResendVerificationRequest):
    """Resend email verification link (P0)."""
    sanitized_email = sanitize_email(data.email)
    user = await db_service.get_user_by_email(sanitized_email)

    # Always return success to prevent user enumeration
    if not user or user.email_verified:
        return MessageResponse(message="Se l'email è registrata, riceverai un link di verifica.")

    verification_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(hours=settings.EMAIL_VERIFICATION_EXPIRE_HOURS)
    await db_service.create_email_verification(user.id, verification_token, expires_at)
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    verification_url = f"{frontend_url}/verify-email?token={verification_token}"

    asyncio.create_task(email_service.send_email_verification(sanitized_email, verification_url))

    return MessageResponse(message="Se l'email è registrata, riceverai un link di verifica.")


# --- P0: Password Reset ---


@router.post("/password-reset/request", response_model=MessageResponse)
@limiter.limit("5 per hour")
async def request_password_reset(request: Request, data: PasswordResetRequest):
    """Request a password reset email (P0). Always returns success to prevent enumeration."""
    sanitized_email = sanitize_email(data.email)
    user = await db_service.get_user_by_email(sanitized_email)

    if user:
        reset_token = secrets.token_urlsafe(32)
        token_hash = User.hash_password(reset_token)
        token_prefix = PasswordReset.compute_prefix(reset_token)
        expires_at = datetime.now(UTC) + timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES)
        await db_service.create_password_reset_token(user.id, token_hash, expires_at, token_prefix=token_prefix)

        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        reset_url = f"{frontend_url}/reset-password?token={reset_token}"
        asyncio.create_task(email_service.send_password_reset_email(sanitized_email, reset_url))

        logger.info("password_reset_requested", user_id=user.id)

    # Always return same message to prevent user enumeration
    return MessageResponse(message="Se l'email è registrata, riceverai un link per reimpostare la password.")


@router.post("/password-reset/confirm", response_model=MessageResponse)
@limiter.limit("10 per hour")
async def confirm_password_reset(request: Request, data: PasswordResetConfirm):
    """Confirm password reset with token and new password (P0)."""
    token = sanitize_string(data.token)
    new_password = data.new_password.get_secret_value()
    validate_password_strength(new_password)

    reset = await db_service.get_password_reset_by_token(token)
    if not reset or reset.used:
        raise HTTPException(status_code=400, detail="Token di reset non valido o già utilizzato")

    if reset.is_expired():
        raise HTTPException(status_code=400, detail="Il token di reset è scaduto")

    hashed = User.hash_password(new_password)
    await db_service.update_user_password(reset.user_id, hashed)
    await db_service.mark_password_reset_used(reset.id)

    logger.info("password_reset_confirmed", user_id=reset.user_id)
    return MessageResponse(message="Password reimpostata con successo")


# --- P2: TOTP 2FA ---


@router.post("/2fa/setup", response_model=TOTPSetupResponse)
async def setup_2fa(user: User = Depends(get_current_user)):
    """Initiate TOTP 2FA setup (P2). Returns secret, QR URI, and backup codes."""
    if user.totp_enabled:
        raise HTTPException(status_code=400, detail="L'autenticazione a due fattori è già attiva")

    secret = totp_service.generate_secret()
    provisioning_uri = totp_service.get_provisioning_uri(secret, user.email)
    backup_codes = totp_service.generate_backup_codes()
    backup_codes_json = totp_service.serialize_backup_codes(backup_codes)

    encrypted_secret = totp_service.encrypt_secret(secret, settings.TOTP_ENCRYPTION_KEY)
    await db_service.create_totp_device(
        user_id=user.id, secret_encrypted=encrypted_secret, backup_codes_json=backup_codes_json
    )

    logger.info("2fa_setup_initiated", user_id=user.id)
    return TOTPSetupResponse(secret=secret, provisioning_uri=provisioning_uri, backup_codes=backup_codes)


@router.post("/2fa/confirm", response_model=MessageResponse)
async def confirm_2fa(data: TOTPVerifyRequest, user: User = Depends(get_current_user)):
    """Confirm 2FA setup by verifying a TOTP code (P2)."""
    device = await db_service.get_totp_device(user.id)
    if not device:
        raise HTTPException(status_code=400, detail="Nessun dispositivo 2FA trovato. Esegui prima il setup.")

    plaintext_secret = totp_service.decrypt_secret(device.secret_encrypted, settings.TOTP_ENCRYPTION_KEY)
    if not totp_service.verify_code(plaintext_secret, data.code):
        raise HTTPException(status_code=400, detail="Codice non valido. Riprova.")

    await db_service.confirm_totp_device(device.id, user.id)
    logger.info("2fa_setup_confirmed", user_id=user.id)
    return MessageResponse(message="Autenticazione a due fattori attivata con successo")


@router.post("/2fa/verify", response_model=LoginResponse)
@limiter.limit("10 per minute")
async def verify_2fa(request: Request, data: TwoFactorVerifyRequest):
    """Complete login by verifying TOTP code (P2)."""
    subject = verify_token(data.two_factor_token)
    if not subject or not str(subject).startswith("2fa:"):
        raise HTTPException(status_code=401, detail="Token 2FA non valido o scaduto")

    user_id = int(str(subject).split(":", 1)[1])
    user = await db_service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato")

    device = await db_service.get_totp_device(user_id)
    if not device:
        raise HTTPException(status_code=400, detail="Dispositivo 2FA non configurato")

    plaintext_secret = totp_service.decrypt_secret(device.secret_encrypted, settings.TOTP_ENCRYPTION_KEY)
    if not totp_service.verify_code(plaintext_secret, data.code):
        raise HTTPException(status_code=401, detail="Codice 2FA non valido")

    access_token = create_access_token(str(user_id))
    refresh_token = create_refresh_token(user_id)
    await db_service.update_user_refresh_token(user_id, refresh_token.access_token)

    ip_address = request.client.host if request.client else ""
    await db_service.record_login_attempt(user_id=user_id, email=user.email, ip_address=ip_address, success=True)

    logger.info("2fa_login_complete", user_id=user_id)
    return LoginResponse(
        access_token=access_token.access_token,
        refresh_token=refresh_token.access_token,
        token_type="bearer",
        expires_at=access_token.expires_at,
        requires_2fa=False,
    )


@router.post("/2fa/email-otp", response_model=MessageResponse)
@limiter.limit("3 per hour")
async def send_email_otp(request: Request, data: EmailOTPRequest):
    """Send email OTP as 2FA fallback (P2)."""
    subject = verify_token(data.two_factor_token)
    if not subject or not str(subject).startswith("2fa:"):
        raise HTTPException(status_code=401, detail="Token 2FA non valido o scaduto")

    user_id = int(str(subject).split(":", 1)[1])
    user = await db_service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato")

    otp_code = totp_service.generate_email_otp()
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.EMAIL_OTP_EXPIRE_MINUTES)

    await db_service.create_email_verification(user_id, f"otp:{otp_code}", expires_at)
    asyncio.create_task(email_service.send_2fa_otp_email(user.email, otp_code))

    logger.info("2fa_email_otp_sent", user_id=user_id)
    return MessageResponse(message="Codice di verifica inviato alla tua email")


@router.post("/2fa/verify-email-otp", response_model=LoginResponse)
@limiter.limit("10 per minute")
async def verify_email_otp(request: Request, data: TwoFactorVerifyRequest):
    """Verify email OTP for 2FA fallback (P2)."""
    subject = verify_token(data.two_factor_token)
    if not subject or not str(subject).startswith("2fa:"):
        raise HTTPException(status_code=401, detail="Token 2FA non valido o scaduto")

    user_id = int(str(subject).split(":", 1)[1])
    otp_token = f"otp:{data.code}"
    verification = await db_service.get_email_verification_by_token(otp_token)

    if not verification or verification.used or verification.user_id != user_id:
        raise HTTPException(status_code=401, detail="Codice OTP non valido")

    if verification.is_expired():
        raise HTTPException(status_code=401, detail="Codice OTP scaduto")

    await db_service.mark_email_verification_used(verification.id)

    user = await db_service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato")

    access_token = create_access_token(str(user_id))
    refresh_token = create_refresh_token(user_id)
    await db_service.update_user_refresh_token(user_id, refresh_token.access_token)

    ip_address = request.client.host if request.client else ""
    await db_service.record_login_attempt(user_id=user_id, email=user.email, ip_address=ip_address, success=True)

    logger.info("2fa_email_otp_verified", user_id=user_id)
    return LoginResponse(
        access_token=access_token.access_token,
        refresh_token=refresh_token.access_token,
        token_type="bearer",
        expires_at=access_token.expires_at,
        requires_2fa=False,
    )


@router.post("/2fa/backup", response_model=LoginResponse)
@limiter.limit("5 per hour")
async def use_backup_code(request: Request, data: TwoFactorBackupRequest):
    """Verify a backup code for 2FA recovery (P2)."""
    subject = verify_token(data.two_factor_token)
    if not subject or not str(subject).startswith("2fa:"):
        raise HTTPException(status_code=401, detail="Token 2FA non valido o scaduto")

    user_id = int(str(subject).split(":", 1)[1])
    device = await db_service.get_totp_device(user_id)
    if not device or not device.backup_codes_json:
        raise HTTPException(status_code=400, detail="Nessun codice di backup disponibile")

    if not totp_service.verify_backup_code(data.backup_code, device.backup_codes_json):
        raise HTTPException(status_code=401, detail="Codice di backup non valido")

    updated_codes = totp_service.consume_backup_code(data.backup_code, device.backup_codes_json)
    if updated_codes is not None:
        await db_service.update_totp_backup_codes(device.id, updated_codes)

    user = await db_service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato")

    access_token = create_access_token(str(user_id))
    refresh_token = create_refresh_token(user_id)
    await db_service.update_user_refresh_token(user_id, refresh_token.access_token)

    logger.info("2fa_backup_code_used", user_id=user_id)
    return LoginResponse(
        access_token=access_token.access_token,
        refresh_token=refresh_token.access_token,
        token_type="bearer",
        expires_at=access_token.expires_at,
        requires_2fa=False,
    )


@router.delete("/2fa", response_model=MessageResponse)
async def disable_2fa(data: TOTPVerifyRequest, user: User = Depends(get_current_user)):
    """Disable 2FA (requires current TOTP code for security) (P2)."""
    device = await db_service.get_totp_device(user.id)
    if not device:
        raise HTTPException(status_code=400, detail="2FA non è attivo")

    plaintext_secret = totp_service.decrypt_secret(device.secret_encrypted, settings.TOTP_ENCRYPTION_KEY)
    if not totp_service.verify_code(plaintext_secret, data.code):
        raise HTTPException(status_code=401, detail="Codice non valido")

    await db_service.delete_totp_device(user.id)
    logger.info("2fa_disabled", user_id=user.id)
    return MessageResponse(message="Autenticazione a due fattori disattivata")


@router.post("/session", response_model=SessionResponse)
async def create_session(user: User = Depends(get_current_user)):
    """Create a new chat session with concurrent session limit (P3)."""
    try:
        # P3: Enforce concurrent session limit
        existing_sessions = await db_service.get_user_sessions(user.id)
        if auth_security_service.exceeds_session_limit(len(existing_sessions)):
            raise HTTPException(
                status_code=429,
                detail=f"Limite di {auth_security_service.max_sessions} sessioni simultanee raggiunto. "
                "Chiudi una sessione esistente.",
            )

        session_id = str(uuid.uuid4())
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

        return SessionResponse(
            session_id=sanitized_session_id, name=session.name, token=token, created_at=session.created_at
        )
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


@router.get("/sessions", response_model=list[SessionResponse])
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
            expires_at=new_access_token.expires_at,
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
                status_code=500, detail="Google OAuth is not configured. Please contact administrator."
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
                status_code=500, detail="Google OAuth is not configured. Please contact administrator."
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
            expires_at=None,  # Will be set by token creation
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
                status_code=500, detail="LinkedIn OAuth is not configured. Please contact administrator."
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
                status_code=500, detail="LinkedIn OAuth is not configured. Please contact administrator."
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
            expires_at=None,  # Will be set by token creation
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("linkedin_oauth_callback_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="LinkedIn OAuth authentication failed")
