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
from app.models.matching_rule import MatchingRule  # noqa: F401 — FK target for communications
from app.models.quality_analysis import ExpertProfile
from app.models.session import Session as ChatSession
from app.models.studio import Studio  # noqa: F401 — FK target for multi-tenant models
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

    async def health_check(self) -> bool:
        """Check database connection health.

        Returns:
            bool: True if database is healthy, False otherwise
        """
        try:
            with Session(self.engine) as session:
                # Execute a simple query to check connection
                session.exec(select(1)).first()
                return True
        except Exception as e:
            logger.error("database_health_check_failed", error=str(e))
            return False


# Create a singleton instance
database_service = DatabaseService()
