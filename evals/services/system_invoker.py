"""System Invoker for evaluation framework.

This service connects the evaluation framework to the actual RAG pipeline
components, enabling real end-to-end testing of:
- Routing decisions (LLMRouterService)
- Document retrieval (KnowledgeSearchService)
- Full responses (LangGraphAgent)

The invoker uses lazy initialization to avoid loading heavy dependencies
until they're actually needed.
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger


class SystemInvoker:
    """Invokes RAG system components for evaluation testing.

    Provides a clean interface between the evaluation framework and
    the actual RAG pipeline components. Uses lazy initialization
    to defer loading expensive dependencies.

    Example:
        invoker = SystemInvoker()

        # Routing test
        routing_output = await invoker.invoke_router("Come aprire P.IVA?")

        # Retrieval test (requires db session)
        docs = await invoker.invoke_retrieval("Scadenze IVA", db_session=session)

        # Full pipeline test
        response = await invoker.invoke_response("Cos'è la Legge 104?")
    """

    def __init__(self, db_session: AsyncSession | None = None):
        """Initialize SystemInvoker.

        Args:
            db_session: Optional database session for retrieval tests.
                If not provided, retrieval will return empty results.
        """
        self._db_session = db_session
        self._router_service: Any = None
        self._kb_service: Any = None
        self._agent: Any = None
        self._model_config: Any = None

    async def _get_router(self) -> Any:
        """Lazily initialize and return the router service.

        Returns:
            LLMRouterService instance
        """
        if self._router_service is None:
            from app.core.llm.model_config import get_model_config
            from app.services.llm_router_service import LLMRouterService

            self._model_config = get_model_config()
            self._router_service = LLMRouterService(config=self._model_config)
        return self._router_service

    async def _get_kb_service(self, db_session: AsyncSession) -> Any:
        """Lazily initialize and return the knowledge search service.

        Args:
            db_session: Database session for queries

        Returns:
            KnowledgeSearchService instance
        """
        from app.services.knowledge_search_service import KnowledgeSearchService

        # Create a new service instance with the provided session
        # KB service is not cached because db_session may differ
        return KnowledgeSearchService(db_session=db_session)

    async def _get_agent(self) -> Any:
        """Lazily initialize and return the LangGraph agent.

        Returns:
            LangGraphAgent instance
        """
        if self._agent is None:
            from app.core.langgraph.graph import LangGraphAgent

            self._agent = LangGraphAgent()
        return self._agent

    async def invoke_router(
        self,
        query: str,
        history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Invoke LLMRouterService for routing tests.

        Args:
            query: User query to route
            history: Optional conversation history

        Returns:
            Dictionary with:
                - route: Routing category string (or None on error)
                - confidence: Confidence score (0.0-1.0)
                - entities: List of extracted entities
                - error: Error message if failed (optional)
        """
        if not query or not query.strip():
            return {
                "route": None,
                "confidence": 0.0,
                "entities": [],
                "error": "Empty query",
            }

        try:
            router = await self._get_router()
            decision = await router.route(query, history=history or [])

            return {
                "route": decision.route.value,
                "confidence": decision.confidence,
                "entities": [
                    {
                        "text": e.text,
                        "type": e.type,
                        "confidence": getattr(e, "confidence", 0.8),
                    }
                    for e in decision.entities
                ],
            }
        except Exception as e:
            logger.error(
                "router_invoke_error",
                error=str(e),
                error_type=type(e).__name__,
                query=query[:100] if query else "",
            )
            return {
                "route": None,
                "confidence": 0.0,
                "entities": [],
                "error": str(e),
            }

    async def invoke_retrieval(
        self,
        query: str,
        db_session: AsyncSession | None = None,
        filters: dict[str, Any] | None = None,
        max_results: int = 10,
    ) -> list[dict[str, Any]]:
        """Invoke KnowledgeSearchService for retrieval tests.

        Args:
            query: Search query
            db_session: Database session (uses internal session if not provided)
            filters: Optional search filters
            max_results: Maximum number of results

        Returns:
            List of document dictionaries with:
                - id: Document ID
                - score: Relevance score
                - title: Document title
                - content: Document content
                - source: Source identifier
            Or empty list if no session available or on error.
        """
        session = db_session or self._db_session
        if session is None:
            logger.warning(
                "retrieval_invoke_no_session",
                query=query[:100] if query else "",
                reason="No database session provided",
            )
            return []

        try:
            kb_service = await self._get_kb_service(session)

            query_data = {
                "query": query,
                "filters": filters or {},
                "max_results": max_results,
                "trace_id": str(uuid.uuid4()),
            }

            results = await kb_service.retrieve_topk(query_data)

            return [
                {
                    "id": r.id,
                    "score": r.score,
                    "title": r.title,
                    "content": r.content,
                    "source": r.source,
                    "source_url": getattr(r, "source_url", None),
                }
                for r in results
            ]
        except Exception as e:
            logger.error(
                "retrieval_invoke_error",
                error=str(e),
                error_type=type(e).__name__,
                query=query[:100] if query else "",
            )
            return []

    async def invoke_response(
        self,
        query: str,
        session_id: str | None = None,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Invoke full RAG pipeline for response tests.

        Args:
            query: User query
            session_id: Optional session ID for tracking
            user_id: Optional user ID for tracking

        Returns:
            Dictionary with:
                - text: Response text
                - citations: List of citations found in response
                - sources: Source documents used
                - error: Error message if failed (optional)
        """
        try:
            from app.schemas.chat import Message

            agent = await self._get_agent()

            # Create message for the agent
            messages = [Message(role="user", content=query)]

            # Generate response
            response_messages = await agent.get_response(
                messages=messages,
                session_id=session_id or f"eval-{uuid.uuid4()}",
                user_id=user_id or "eval-user",
            )

            # Extract assistant response
            response_text = ""
            for msg in response_messages:
                if msg.role == "assistant":
                    response_text = msg.content
                    break

            # Extract citations from response (reuse citation extraction logic)
            citations = self._extract_citations(response_text)

            return {
                "text": response_text,
                "citations": citations,
                "sources": [],  # Would be populated from retrieval step
            }
        except Exception as e:
            logger.error(
                "response_invoke_error",
                error=str(e),
                error_type=type(e).__name__,
                query=query[:100] if query else "",
            )
            return {
                "text": "",
                "citations": [],
                "sources": [],
                "error": str(e),
            }

    def _extract_citations(self, text: str) -> list[dict[str, Any]]:
        """Extract Italian legal citations from response text.

        Uses patterns from CitationGrader to identify citations.

        Args:
            text: Response text to scan

        Returns:
            List of citation dictionaries with text and optional source_id
        """
        import re

        citations = []
        seen = set()

        # Italian legal citation patterns (from CitationGrader)
        patterns = [
            r"Legge\s+\d+/\d{4}",  # Legge 104/1992
            r"L\.\s*\d+/\d{4}",  # L. 234/2021
            r"D\.Lgs\.\s*\d+/\d{4}",  # D.Lgs. 446/1997
            r"D\.L\.\s*\d+/\d{4}",  # D.L. 18/2020
            r"D\.P\.R\.\s*\d+/\d{4}",  # D.P.R. 633/1972
            r"Art\.\s*\d+",  # Art. 3
            r"Circolare\s+(?:INPS|INAIL|ADE)\s+n\.\s*\d+/\d{4}",  # Circolare INPS
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                citation_text = match.group()
                normalized = citation_text.lower().strip()
                if normalized not in seen:
                    seen.add(normalized)
                    citations.append(
                        {
                            "text": citation_text,
                            "source_id": None,
                        }
                    )

        return citations
