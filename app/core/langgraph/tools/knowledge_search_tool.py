"""
Knowledge Search Tool for LangGraph.

This tool enables the LLM to search the knowledge base on demand for relevant
information using hybrid BM25 + vector + recency search.
"""

import json
from typing import Dict, List, Any, Optional
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from app.services.knowledge_search_service import KnowledgeSearchService, SearchMode
from app.core.logging import logger


class KnowledgeSearchInput(BaseModel):
    """Input schema for knowledge search queries."""
    query: str = Field(
        description="The search query to find relevant knowledge base articles"
    )
    max_results: Optional[int] = Field(
        default=10,
        description="Maximum number of results to return (default: 10)"
    )
    category: Optional[str] = Field(
        default=None,
        description="Filter by knowledge category (e.g., 'labor_law', 'tax', 'hr', 'payroll')"
    )
    search_mode: Optional[str] = Field(
        default="hybrid",
        description="Search mode: 'hybrid' (default), 'bm25_only', or 'vector_only'"
    )


class KnowledgeSearchTool(BaseTool):
    """LangGraph tool for searching the knowledge base on demand."""

    name: str = "KnowledgeSearchTool"
    description: str = """
    Search the knowledge base to find relevant information about:
    - Italian labor law and regulations
    - Tax and payroll information
    - HR policies and procedures
    - Employment contracts and agreements
    - Benefits and compensation
    - Leave and time-off policies
    - Compliance and legal requirements

    Use this tool when you need to retrieve specific information from the knowledge base
    that is not already in the conversation context. The tool uses hybrid search combining
    keyword matching (BM25), semantic search (vectors), and recency boost.

    Provide a clear, specific query for best results.
    """

    def __init__(self):
        super().__init__()
        # Initialize service lazily to avoid Pydantic field issues
        self._search_service = None

    @property
    def search_service(self):
        if self._search_service is None:
            # Service will be initialized with db_session when needed
            pass
        return self._search_service

    def _run(self, **kwargs) -> str:
        """Execute knowledge search (synchronous version)."""
        # This shouldn't be called in async context, but provide fallback
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.arun(**kwargs))
        except RuntimeError:
            # Create new event loop if none exists
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.arun(**kwargs))
            finally:
                loop.close()

    async def _arun(
        self,
        query: str,
        max_results: Optional[int] = 10,
        category: Optional[str] = None,
        search_mode: Optional[str] = "hybrid",
        **kwargs
    ) -> str:
        """Execute knowledge search asynchronously."""
        import time
        start_time = time.time()

        try:
            logger.info(
                "knowledge_search_initiated",
                query=query,
                max_results=max_results,
                category=category,
                search_mode=search_mode
            )

            # Validate search mode
            try:
                mode = SearchMode(search_mode)
            except ValueError:
                mode = SearchMode.HYBRID

            # Prepare query data
            query_data = {
                "query": query,
                "max_results": max_results,
                "search_mode": mode.value,
                "filters": {}
            }

            # Add category filter if provided
            if category:
                query_data["filters"]["category"] = category

            # Add db_session and vector_service from kwargs if available
            if "db_session" in kwargs:
                query_data["db_session"] = kwargs["db_session"]
            if "vector_service" in kwargs:
                query_data["vector_service"] = kwargs["vector_service"]

            # Execute search using convenience function
            from app.services.knowledge_search_service import retrieve_knowledge_topk

            results = await retrieve_knowledge_topk(query_data)

            # Format results for LLM consumption
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "title": result.title,
                    "content": result.content,
                    "category": result.category,
                    "source": result.source,
                    "relevance_score": result.score,
                    "updated_at": result.updated_at.isoformat() if result.updated_at else None
                })

            response = {
                "success": True,
                "query": query,
                "results": formatted_results,
                "total_found": len(formatted_results),
                "search_mode": search_mode,
                "filters": query_data.get("filters", {})
            }

            duration_seconds = time.time() - start_time

            logger.info(
                "knowledge_search_completed",
                query=query,
                result_count=len(formatted_results),
                duration_seconds=duration_seconds
            )

            return json.dumps(response, indent=2)

        except Exception as e:
            duration_seconds = time.time() - start_time

            logger.error(
                "knowledge_search_failed",
                query=query,
                error=str(e),
                duration_seconds=duration_seconds,
                exc_info=True
            )

            return json.dumps({
                "success": False,
                "error": f"Knowledge search failed: {str(e)}",
                "message": "Si è verificato un errore durante la ricerca nella knowledge base. Riprova con una query diversa."
            })


# Create tool instance
knowledge_search_tool = KnowledgeSearchTool()