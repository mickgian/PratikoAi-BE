"""This file contains the database service for the application."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import (
    List,
    Optional,
    cast,
)

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError as SAIntegrityError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.pool import QueuePool
from sqlmodel import (
    Session,
    SQLModel,
    create_engine,
    select,
)

from app.core.config import (
    Environment,
    settings,
)
from app.core.logging import logger
from app.models.database import AsyncSessionLocal
from app.models.email_verification import EmailVerification
from app.models.login_attempt import LoginAttempt
from app.models.matching_rule import MatchingRule  # noqa: F401 — FK target for communications
from app.models.password_reset import PasswordReset
from app.models.quality_analysis import ExpertProfile
from app.models.session import Session as ChatSession
from app.models.studio import Studio  # noqa: F401 — FK target for multi-tenant models
from app.models.totp_device import TOTPDevice
from app.models.user import User
from app.utils.account_code import generate_account_code


class DatabaseService:
    """Service class for database operations.

    This class handles all database operations for Users, Sessions, and Messages.
    It uses SQLModel for ORM operations and maintains a connection pool.
    """

    def __init__(self):
        """Initialize database service with connection pool."""
        try:
            # Configure environment-specific database connection pool settings
            pool_size = settings.POSTGRES_POOL_SIZE
            max_overflow = settings.POSTGRES_MAX_OVERFLOW

            # Create engine with appropriate pool configuration
            self.engine = create_engine(
                settings.POSTGRES_URL,
                pool_pre_ping=True,
                poolclass=QueuePool,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_timeout=30,  # Connection timeout (seconds)
                pool_recycle=1800,  # Recycle connections after 30 minutes
            )

            # Create tables (only if they don't exist)
            SQLModel.metadata.create_all(self.engine)

            logger.info(
                "database_initialized",
                environment=settings.ENVIRONMENT.value,
                pool_size=pool_size,
                max_overflow=max_overflow,
            )
        except SQLAlchemyError as e:
            logger.error("database_initialization_error", error=str(e), environment=settings.ENVIRONMENT.value)
            # In production, don't raise - allow app to start even with DB issues
            if settings.ENVIRONMENT != Environment.PRODUCTION:
                raise

    async def create_user(self, email: str, password: str, role: str | None = None) -> User:
        """Create a new user with a unique account_code.

        Generates a human-readable account code ({3_letters}{hundreds}{2_random}-{sequence})
        from the email for Langfuse analytics. Retries up to 3 times on uniqueness collisions.

        Args:
            email: User's email address
            password: Hashed password
            role: Optional role override (defaults to UserRole.REGULAR_USER)

        Returns:
            User: The created user
        """
        max_retries = 3
        for attempt in range(max_retries):
            account_code = generate_account_code(email=email, sequence=attempt + 1)
            try:
                with Session(self.engine) as session:
                    user = User(email=email, hashed_password=password, account_code=account_code)
                    if role:
                        user.role = role
                    session.add(user)
                    session.commit()
                    session.refresh(user)
                    logger.info("user_created", email=email, account_code=account_code)
                    return user
            except SAIntegrityError as e:
                if "account_code" in str(e).lower() and attempt < max_retries - 1:
                    logger.warning(
                        "account_code_collision_retry",
                        email=email,
                        attempt=attempt + 1,
                        account_code=account_code,
                    )
                    continue
                raise
        raise RuntimeError(f"Impossibile generare account_code unico dopo {max_retries} tentativi")

    async def create_expert_profile(self, user_id: int) -> ExpertProfile:
        """Create an ExpertProfile for a user with sensible defaults.

        Used when a QA elevated-role user registers so the expert-feedback
        endpoints work immediately (empty arrays instead of NULL).

        Args:
            user_id: The ID of the user to create a profile for

        Returns:
            ExpertProfile: The created expert profile
        """
        with Session(self.engine) as session:
            profile = ExpertProfile(
                user_id=user_id,
                is_verified=True,
                is_active=True,
                credentials=[],
                credential_types=[],
                specializations=[],
            )
            session.add(profile)
            session.commit()
            session.refresh(profile)
            logger.info("expert_profile_created", user_id=user_id, profile_id=str(profile.id))
            return profile

    async def get_user(self, user_id: int) -> User | None:
        """Get a user by ID.

        Args:
            user_id: The ID of the user to retrieve

        Returns:
            Optional[User]: The user if found, None otherwise
        """
        with Session(self.engine) as session:
            user = session.get(User, user_id)
            return cast(User | None, user)

    async def get_user_by_email(self, email: str) -> User | None:
        """Get a user by email.

        Args:
            email: The email of the user to retrieve

        Returns:
            Optional[User]: The user if found, None otherwise
        """
        with Session(self.engine) as session:
            statement = select(User).where(User.email == email)
            user = session.exec(statement).first()
            return cast(User | None, user)

    async def delete_user_by_email(self, email: str) -> bool:
        """Delete a user by email.

        Args:
            email: The email of the user to delete

        Returns:
            bool: True if deletion was successful, False if user not found
        """
        with Session(self.engine) as session:
            user = session.exec(select(User).where(User.email == email)).first()
            if not user:
                return False

            session.delete(user)
            session.commit()
            logger.info("user_deleted", email=email)
            return True

    async def create_session(self, session_id: str, user_id: int, name: str = "") -> ChatSession:
        """Create a new chat session.

        Args:
            session_id: The ID for the new session
            user_id: The ID of the user who owns the session
            name: Optional name for the session (defaults to empty string)

        Returns:
            ChatSession: The created session
        """
        with Session(self.engine) as session:
            chat_session = ChatSession(id=session_id, user_id=user_id, name=name)
            session.add(chat_session)
            session.commit()
            session.refresh(chat_session)
            logger.info("session_created", session_id=session_id, user_id=user_id, name=name)
            return chat_session

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session by ID.

        Args:
            session_id: The ID of the session to delete

        Returns:
            bool: True if deletion was successful, False if session not found
        """
        with Session(self.engine) as session:
            chat_session = session.get(ChatSession, session_id)
            if not chat_session:
                return False

            session.delete(chat_session)
            session.commit()
            logger.info("session_deleted", session_id=session_id)
            return True

    async def get_session(self, session_id: str) -> ChatSession | None:
        """Get a session by ID.

        Args:
            session_id: The ID of the session to retrieve

        Returns:
            Optional[ChatSession]: The session if found, None otherwise
        """
        with Session(self.engine) as session:
            chat_session = session.get(ChatSession, session_id)
            return cast(ChatSession | None, chat_session)

    async def get_user_sessions(self, user_id: int) -> list[ChatSession]:
        """Get all sessions for a user.

        Args:
            user_id: The ID of the user

        Returns:
            List[ChatSession]: List of user's sessions
        """
        with Session(self.engine) as session:
            statement = select(ChatSession).where(ChatSession.user_id == user_id).order_by(ChatSession.created_at)
            sessions = session.exec(statement).all()
            return cast(list[ChatSession], sessions)

    async def update_session_name(self, session_id: str, name: str) -> ChatSession:
        """Update a session's name.

        Args:
            session_id: The ID of the session to update
            name: The new name for the session

        Returns:
            ChatSession: The updated session

        Raises:
            HTTPException: If session is not found
        """
        with Session(self.engine) as session:
            chat_session = session.get(ChatSession, session_id)
            if not chat_session:
                raise HTTPException(status_code=404, detail="Session not found")

            chat_session.name = name
            session.add(chat_session)
            session.commit()
            session.refresh(chat_session)
            logger.info("session_name_updated", session_id=session_id, name=name)
            return cast(ChatSession, chat_session)

    def get_session_maker(self):
        """Get a session maker for creating database sessions.

        Returns:
            Session: A SQLModel session maker
        """
        return Session(self.engine)

    @asynccontextmanager
    async def get_db(self) -> AsyncIterator[AsyncSession]:
        """Get an async database session as a context manager.

        Yields an async session from the shared AsyncSessionLocal factory.
        The session is automatically closed when the context exits.

        Usage:
            async with database_service.get_db() as db:
                db.add(entity)
                await db.commit()

        Yields:
            AsyncSession: Async database session
        """
        async with AsyncSessionLocal() as session:
            try:
                yield session
            finally:
                await session.close()

    async def update_user_refresh_token(self, user_id: int, refresh_token: str) -> bool:
        """Update a user's refresh token hash.

        Args:
            user_id: The ID of the user to update
            refresh_token: The new refresh token to hash and store

        Returns:
            bool: True if update was successful, False if user not found
        """
        with Session(self.engine) as session:
            user = session.get(User, user_id)
            if not user:
                return False

            user.set_refresh_token_hash(refresh_token)
            session.add(user)
            session.commit()
            logger.info("user_refresh_token_updated", user_id=user_id)
            return True

    async def revoke_user_refresh_token(self, user_id: int) -> bool:
        """Revoke a user's refresh token by clearing the hash.

        Args:
            user_id: The ID of the user whose refresh token to revoke

        Returns:
            bool: True if revocation was successful, False if user not found
        """
        with Session(self.engine) as session:
            user = session.get(User, user_id)
            if not user:
                return False

            user.revoke_refresh_token()
            session.add(user)
            session.commit()
            logger.info("user_refresh_token_revoked", user_id=user_id)
            return True

    # --- P0: Email Verification ---

    async def create_email_verification(self, user_id: int, token: str, expires_at) -> EmailVerification:
        """Create an email verification token."""
        with Session(self.engine) as session:
            verification = EmailVerification(user_id=user_id, token=token, expires_at=expires_at)
            session.add(verification)
            session.commit()
            session.refresh(verification)
            return verification

    async def get_email_verification_by_token(self, token: str) -> EmailVerification | None:
        """Get email verification by token."""
        with Session(self.engine) as session:
            stmt = select(EmailVerification).where(EmailVerification.token == token)
            return cast(EmailVerification | None, session.exec(stmt).first())

    async def mark_email_verification_used(self, verification_id: int) -> None:
        """Mark an email verification token as used."""
        with Session(self.engine) as session:
            verification = session.get(EmailVerification, verification_id)
            if verification:
                verification.used = True
                session.add(verification)
                session.commit()

    async def mark_user_email_verified(self, user_id: int) -> None:
        """Set user's email_verified flag to True."""
        with Session(self.engine) as session:
            user = session.get(User, user_id)
            if user:
                user.email_verified = True
                session.add(user)
                session.commit()

    # --- P0: Password Reset ---

    async def create_password_reset_token(self, user_id: int, token_hash: str, expires_at) -> PasswordReset:
        """Create a password reset token."""
        with Session(self.engine) as session:
            reset = PasswordReset(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
            session.add(reset)
            session.commit()
            session.refresh(reset)
            return reset

    async def get_password_reset_by_token(self, token: str) -> PasswordReset | None:
        """Get password reset by comparing token against stored hashes.

        Since we store bcrypt hashes, we need to check all recent unused tokens.
        """
        with Session(self.engine) as session:
            stmt = select(PasswordReset).where(
                PasswordReset.used == False,  # noqa: E712
            )
            resets = session.exec(stmt).all()
            for reset in resets:
                if User.hash_password.__func__ is not None:
                    # Compare the raw token against the bcrypt hash
                    import bcrypt as bcrypt_lib

                    try:
                        if bcrypt_lib.checkpw(token.encode("utf-8")[:72], reset.token_hash.encode("utf-8")):
                            return cast(PasswordReset, reset)
                    except (ValueError, TypeError):
                        continue
            return None

    async def mark_password_reset_used(self, reset_id: int) -> None:
        """Mark a password reset token as used."""
        with Session(self.engine) as session:
            reset = session.get(PasswordReset, reset_id)
            if reset:
                reset.used = True
                session.add(reset)
                session.commit()

    async def update_user_password(self, user_id: int, hashed_password: str) -> None:
        """Update a user's password hash."""
        with Session(self.engine) as session:
            user = session.get(User, user_id)
            if user:
                user.hashed_password = hashed_password
                session.add(user)
                session.commit()

    # --- P1: Account Lockout ---

    async def update_failed_login_attempts(self, user_id: int, count: int, locked_until: object | None = None) -> None:
        """Update failed login attempt count and optional lockout time."""
        with Session(self.engine) as session:
            user = session.get(User, user_id)
            if user:
                user.failed_login_attempts = count
                user.account_locked_until = locked_until
                session.add(user)
                session.commit()

    # --- P2: Login Attempt Logging ---

    async def record_login_attempt(
        self,
        *,
        user_id: int | None,
        email: str,
        ip_address: str = "",
        success: bool = False,
        failure_reason: str | None = None,
    ) -> LoginAttempt:
        """Record a login attempt for audit trail."""
        with Session(self.engine) as session:
            attempt = LoginAttempt(
                user_id=user_id,
                email=email,
                ip_address=ip_address,
                success=success,
                failure_reason=failure_reason,
            )
            session.add(attempt)
            session.commit()
            session.refresh(attempt)
            return attempt

    # --- P2: TOTP 2FA ---

    async def create_totp_device(self, *, user_id: int, secret_encrypted: str, backup_codes_hash: str) -> TOTPDevice:
        """Create a TOTP device for a user."""
        with Session(self.engine) as session:
            device = TOTPDevice(
                user_id=user_id,
                secret_encrypted=secret_encrypted,
                backup_codes_hash=backup_codes_hash,
            )
            session.add(device)
            session.commit()
            session.refresh(device)
            return device

    async def get_totp_device(self, user_id: int) -> TOTPDevice | None:
        """Get the confirmed TOTP device for a user."""
        with Session(self.engine) as session:
            stmt = select(TOTPDevice).where(TOTPDevice.user_id == user_id)
            return cast(TOTPDevice | None, session.exec(stmt).first())

    async def confirm_totp_device(self, device_id: int, user_id: int) -> None:
        """Confirm a TOTP device and enable 2FA on the user."""
        with Session(self.engine) as session:
            device = session.get(TOTPDevice, device_id)
            if device:
                device.confirmed = True
                session.add(device)

            user = session.get(User, user_id)
            if user:
                user.totp_enabled = True
                session.add(user)

            session.commit()

    async def update_totp_backup_codes(self, device_id: int, backup_codes_json: str) -> None:
        """Update the backup codes for a TOTP device."""
        with Session(self.engine) as session:
            device = session.get(TOTPDevice, device_id)
            if device:
                device.backup_codes_hash = backup_codes_json
                session.add(device)
                session.commit()

    async def delete_totp_device(self, user_id: int) -> None:
        """Delete TOTP device and disable 2FA for a user."""
        with Session(self.engine) as session:
            stmt = select(TOTPDevice).where(TOTPDevice.user_id == user_id)
            device = session.exec(stmt).first()
            if device:
                session.delete(device)

            user = session.get(User, user_id)
            if user:
                user.totp_enabled = False
                session.add(user)

            session.commit()

    async def health_check(self) -> bool:
        """Check database connection health."""
        try:
            with Session(self.engine) as session:
                session.exec(select(1)).first()
                return True
        except Exception as e:
            logger.error("database_health_check_failed", error=str(e))
            return False


# Create a singleton instance
database_service = DatabaseService()
