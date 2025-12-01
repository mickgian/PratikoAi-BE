"""Chat history service for saving and retrieving conversation history.

This service manages persistent storage of chat messages in PostgreSQL,
enabling multi-device sync and GDPR-compliant data management.
"""

import uuid
from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.database import get_db
from app.schemas.chat import Message


class ChatHistoryService:
    """Service for managing chat history persistence in PostgreSQL."""

    @staticmethod
    async def save_chat_interaction(
        user_id: int,
        session_id: str,
        user_query: str,
        ai_response: str,
        *,
        db: AsyncSession | None = None,
        model_used: str | None = None,
        tokens_used: int | None = None,
        cost_cents: int | None = None,
        response_time_ms: int | None = None,
        response_cached: bool = False,
        conversation_id: str | None = None,
        query_type: str | None = None,
        italian_content: bool = True,
    ) -> str:
        """Save a chat interaction (user query + AI response) to query_history table.

        Args:
            user_id: ID of the user who sent the query
            session_id: ID of the chat session
            user_query: The user's question/message
            ai_response: The AI's response
            db: Optional database session (for testing/dependency injection)
            model_used: Name of the LLM model used (e.g., 'gpt-4-turbo')
            tokens_used: Total tokens consumed (prompt + completion)
            cost_cents: Cost in cents (for billing/analytics)
            response_time_ms: Response latency in milliseconds
            response_cached: Whether response was served from cache
            conversation_id: UUID linking related queries in a conversation
            query_type: Type of query (e.g., 'tax_question', 'legal_question')
            italian_content: Whether query/response contains Italian text

        Returns:
            str: The UUID of the created query_history record

        Raises:
            Exception: If database save fails
        """
        try:
            record_id = str(uuid.uuid4())
            timestamp = datetime.utcnow()

            query = text("""
                INSERT INTO query_history (
                    id, user_id, query, response, response_cached,
                    response_time_ms, tokens_used, cost_cents, model_used,
                    session_id, conversation_id, query_type, italian_content,
                    timestamp, created_at
                ) VALUES (
                    :id, :user_id, :query, :response, :response_cached,
                    :response_time_ms, :tokens_used, :cost_cents, :model_used,
                    :session_id, :conversation_id, :query_type, :italian_content,
                    :timestamp, :created_at
                )
            """)

            params = {
                "id": record_id,
                "user_id": user_id,
                "query": user_query,
                "response": ai_response,
                "response_cached": response_cached,
                "response_time_ms": response_time_ms,
                "tokens_used": tokens_used,
                "cost_cents": cost_cents,
                "model_used": model_used,
                "session_id": session_id,
                "conversation_id": conversation_id,
                "query_type": query_type,
                "italian_content": italian_content,
                "timestamp": timestamp,
                "created_at": timestamp,
            }

            if db is not None:
                # Use provided session (for testing)
                await db.execute(query, params)
                await db.commit()
            else:
                # Use dependency injection for production
                async for db in get_db():
                    await db.execute(query, params)
                    await db.commit()

            logger.info(
                "chat_history_saved",
                record_id=record_id,
                user_id=user_id,
                session_id=session_id,
                query_length=len(user_query),
                response_length=len(ai_response),
                model_used=model_used,
                tokens_used=tokens_used,
            )

            return record_id

        except Exception as e:
            logger.error(
                "chat_history_save_failed",
                error=str(e),
                user_id=user_id,
                session_id=session_id,
                exc_info=True,
            )
            raise

    @staticmethod
    async def get_session_history(
        user_id: int,
        session_id: str,
        limit: int = 100,
        offset: int = 0,
        *,
        db: AsyncSession | None = None,
    ) -> list[dict]:
        """Retrieve chat history for a specific session.

        Args:
            user_id: ID of the user (for authorization)
            session_id: ID of the chat session
            limit: Maximum number of messages to return (default: 100)
            offset: Number of messages to skip (for pagination)
            db: Optional database session (for testing/dependency injection)

        Returns:
            list[dict]: List of chat messages with metadata

        Example:
            [
                {
                    "id": "uuid",
                    "query": "What is IVA in Italy?",
                    "response": "IVA (Imposta sul Valore Aggiunto) is...",
                    "timestamp": "2025-11-29T12:00:00",
                    "model_used": "gpt-4-turbo",
                    "tokens_used": 350,
                }
            ]
        """
        try:
            query = text("""
                SELECT
                    id, query, response, timestamp,
                    model_used, tokens_used, cost_cents,
                    response_cached, response_time_ms
                FROM query_history
                WHERE user_id = :user_id AND session_id = :session_id
                ORDER BY timestamp ASC
                LIMIT :limit OFFSET :offset
            """)

            params = {
                "user_id": user_id,
                "session_id": session_id,
                "limit": limit,
                "offset": offset,
            }

            if db is not None:
                # Use provided session (for testing)
                result = await db.execute(query, params)
                rows = result.fetchall()
            else:
                # Use dependency injection for production
                async for db in get_db():
                    result = await db.execute(query, params)
                    rows = result.fetchall()

            return [
                {
                    "id": str(row[0]),
                    "query": row[1],
                    "response": row[2],
                    "timestamp": row[3].isoformat() if row[3] else None,
                    "model_used": row[4],
                    "tokens_used": row[5],
                    "cost_cents": row[6],
                    "response_cached": row[7],
                    "response_time_ms": row[8],
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(
                "chat_history_retrieval_failed",
                error=str(e),
                session_id=session_id,
                exc_info=True,
            )
            raise

    @staticmethod
    async def get_user_history(
        user_id: int,
        limit: int = 100,
        offset: int = 0,
        *,
        db: AsyncSession | None = None,
    ) -> list[dict]:
        """Retrieve all chat history for a user (across all sessions).

        Args:
            user_id: ID of the user
            limit: Maximum number of messages to return
            offset: Number of messages to skip
            db: Optional database session (for testing/dependency injection)

        Returns:
            list[dict]: List of chat messages with session information
        """
        try:
            query = text("""
                SELECT
                    id, session_id, query, response, timestamp,
                    model_used, tokens_used, cost_cents
                FROM query_history
                WHERE user_id = :user_id
                ORDER BY timestamp DESC
                LIMIT :limit OFFSET :offset
            """)

            params = {
                "user_id": user_id,
                "limit": limit,
                "offset": offset,
            }

            if db is not None:
                # Use provided session (for testing)
                result = await db.execute(query, params)
                rows = result.fetchall()
            else:
                # Use dependency injection for production
                async for db in get_db():
                    result = await db.execute(query, params)
                    rows = result.fetchall()

            return [
                {
                    "id": str(row[0]),
                    "session_id": row[1],
                    "query": row[2],
                    "response": row[3],
                    "timestamp": row[4].isoformat() if row[4] else None,
                    "model_used": row[5],
                    "tokens_used": row[6],
                    "cost_cents": row[7],
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(
                "user_history_retrieval_failed",
                error=str(e),
                user_id=user_id,
                exc_info=True,
            )
            raise

    @staticmethod
    async def delete_user_history(user_id: int, *, db: AsyncSession | None = None) -> int:
        """Delete all chat history for a user (GDPR Right to Erasure).

        Args:
            user_id: ID of the user whose history should be deleted
            db: Optional database session (for testing/dependency injection)

        Returns:
            int: Number of records deleted
        """
        try:
            query = text("DELETE FROM query_history WHERE user_id = :user_id")
            params = {"user_id": user_id}

            if db is not None:
                # Use provided session (for testing)
                result = await db.execute(query, params)
                await db.commit()
                deleted_count = result.rowcount
            else:
                # Use dependency injection for production
                async for db in get_db():
                    result = await db.execute(query, params)
                    await db.commit()
                    deleted_count = result.rowcount

            logger.info(
                "chat_history_deleted",
                user_id=user_id,
                deleted_count=deleted_count,
            )

            return deleted_count

        except Exception as e:
            logger.error(
                "chat_history_deletion_failed",
                error=str(e),
                user_id=user_id,
                exc_info=True,
            )
            raise

    @staticmethod
    async def get_user_sessions(user_id: int, *, db: AsyncSession | None = None) -> list[dict]:
        """Retrieve list of sessions for a user.

        Args:
            user_id: ID of the user
            db: Optional database session (for testing/dependency injection)

        Returns:
            list[dict]: List of sessions with metadata

        Example:
            [
                {
                    "session_id": "session-123",
                    "message_count": 5,
                    "last_message_at": "2025-11-29T12:00:00",
                    "first_message_at": "2025-11-29T11:00:00",
                }
            ]
        """
        try:
            query = text("""
                SELECT
                    session_id,
                    COUNT(*) as message_count,
                    MAX(timestamp) as last_message_at,
                    MIN(timestamp) as first_message_at
                FROM query_history
                WHERE user_id = :user_id
                GROUP BY session_id
                ORDER BY MAX(timestamp) DESC
            """)

            params = {"user_id": user_id}

            if db is not None:
                # Use provided session (for testing)
                result = await db.execute(query, params)
                rows = result.fetchall()
            else:
                # Use dependency injection for production
                async for db in get_db():
                    result = await db.execute(query, params)
                    rows = result.fetchall()

            return [
                {
                    "session_id": row[0],
                    "message_count": row[1],
                    "last_message_at": row[2].isoformat() if row[2] else None,
                    "first_message_at": row[3].isoformat() if row[3] else None,
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(
                "user_sessions_retrieval_failed",
                error=str(e),
                user_id=user_id,
                exc_info=True,
            )
            raise

    @staticmethod
    async def delete_session(user_id: int, session_id: str, *, db: AsyncSession | None = None) -> int:
        """Delete a specific chat session.

        Args:
            user_id: ID of the user (for authorization)
            session_id: ID of the session to delete
            db: Optional database session (for testing/dependency injection)

        Returns:
            int: Number of records deleted
        """
        try:
            query = text("DELETE FROM query_history WHERE user_id = :user_id AND session_id = :session_id")
            params = {"user_id": user_id, "session_id": session_id}

            if db is not None:
                # Use provided session (for testing)
                result = await db.execute(query, params)
                await db.commit()
                deleted_count = result.rowcount
            else:
                # Use dependency injection for production
                async for db in get_db():
                    result = await db.execute(query, params)
                    await db.commit()
                    deleted_count = result.rowcount

            logger.info(
                "session_deleted",
                user_id=user_id,
                session_id=session_id,
                deleted_count=deleted_count,
            )

            return deleted_count

        except Exception as e:
            logger.error(
                "session_deletion_failed",
                error=str(e),
                user_id=user_id,
                session_id=session_id,
                exc_info=True,
            )
            raise


# Singleton instance
chat_history_service = ChatHistoryService()
